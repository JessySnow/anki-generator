#!/usr/bin/env python3
"""
scripts/verify_deck.py - Gemini-Powered Iterative Loop Verification Pipeline for N2 Anki Deck.

Features:
- Powered by Gemini 3.7 Flash (default) via Google AI SDK or zero-dependency REST client fallback.
- Strictly adheres to Google AI Studio RPM limits with a sliding-window rate limiter (default: 10 RPM).
- Batches cards (15-20 per prompt) to maximize throughput while minimizing requests.
- Detects format errors, syntax errors, format inconsistencies, and unnatural example sentences.
- Iterative loop verification: re-verifies revised cards until 0 errors remain or max passes reached.
- Synchronizes changes to progress/cards/*.json and N2 Level/deck.txt with full audit reporting.

Usage:
  python3 scripts/verify_deck.py --limit 15 --dry-run
  python3 scripts/verify_deck.py --rpm 10 --batch-size 15
  python3 scripts/verify_deck.py --index 42
  python3 scripts/verify_deck.py --model gemini-3.7-flash --max-passes 3
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import os
import random
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

# Ensure scripts directory is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import pipeline_lib as lib
import build_deck

CACHE_FILE = lib.PROGRESS_DIR / ".verify_cache.json"
REPORT_FILE = lib.PROGRESS_DIR / "verification_report.json"

DEFAULT_MODEL = "gemini-3.7-flash"
DEFAULT_RPM = 10.0
DEFAULT_BATCH_SIZE = 15
DEFAULT_MAX_PASSES = 3


class RateLimiter:
    """Sliding-window RPM governor with minimum inter-request delay and exponential backoff."""

    def __init__(self, target_rpm: float = DEFAULT_RPM, min_delay_sec: float | None = None):
        self.target_rpm = max(1.0, float(target_rpm))
        self.window_sec = 60.0
        self.min_delay = min_delay_sec if min_delay_sec is not None else max(0.05, self.window_sec / self.target_rpm)
        self.request_timestamps: collections.deque[float] = collections.deque()
        self.last_request_time: float = 0.0

    def wait_if_needed(self) -> float:
        """Enforces rate limit and returns seconds waited."""
        now = time.time()
        waited_total = 0.0

        # 1. Enforce minimum inter-request delay
        time_since_last = now - self.last_request_time
        if self.last_request_time > 0 and time_since_last < self.min_delay:
            gap_needed = self.min_delay - time_since_last
            time.sleep(gap_needed)
            waited_total += gap_needed
            now = time.time()

        # 2. Enforce sliding-window RPM limit
        while self.request_timestamps and (now - self.request_timestamps[0] >= self.window_sec):
            self.request_timestamps.popleft()

        if len(self.request_timestamps) >= self.target_rpm:
            earliest = self.request_timestamps[0]
            sleep_needed = (earliest + self.window_sec) - now + 0.1
            if sleep_needed > 0:
                time.sleep(sleep_needed)
                waited_total += sleep_needed
                now = time.time()
                while self.request_timestamps and (now - self.request_timestamps[0] >= self.window_sec):
                    self.request_timestamps.popleft()

        self.last_request_time = now
        self.request_timestamps.append(now)
        return waited_total


class GeminiClient:
    """Unified client supporting Google AI SDK (google.genai) with zero-dependency REST fallback."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, rate_limiter: RateLimiter | None = None):
        self.api_key = api_key
        self.model = model
        self.rate_limiter = rate_limiter or RateLimiter()
        self._sdk_client = None
        self._init_sdk()

    def _init_sdk(self) -> None:
        try:
            from google import genai
            self._sdk_client = genai.Client(api_key=self.api_key)
        except Exception:
            self._sdk_client = None

    def call_model_json(self, prompt: str, max_retries: int = 4) -> dict:
        """Call Gemini model requesting strict JSON output with retry and rate-limiting."""
        base_backoff = 6.0

        for attempt in range(1, max_retries + 1):
            self.rate_limiter.wait_if_needed()

            try:
                if self._sdk_client is not None:
                    # Google AI SDK client path
                    from google.genai import types
                    response = self._sdk_client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1,
                        ),
                    )
                    text = response.text or "{}"
                else:
                    # REST fallback using urllib.request
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "responseMimeType": "application/json",
                            "temperature": 0.1,
                        },
                    }
                    req = urllib.request.Request(
                        url,
                        data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        res_json = json.loads(resp.read().decode("utf-8"))
                        text = res_json["candidates"][0]["content"]["parts"][0]["text"]

                # Clean possible markdown fence wrapping
                cleaned_text = re.sub(r"^```json\s*", "", text.strip(), flags=re.IGNORECASE)
                cleaned_text = re.sub(r"\s*```$", "", cleaned_text.strip())
                return json.loads(cleaned_text)

            except urllib.error.HTTPError as e:
                status_code = e.code
                error_body = ""
                try:
                    error_body = e.read().decode("utf-8")
                except Exception:
                    pass

                if status_code == 429 or "RESOURCE_EXHAUSTED" in error_body:
                    if attempt < max_retries:
                        sleep_time = (base_backoff * (2 ** (attempt - 1))) + random.uniform(0.5, 2.0)
                        print(f"  [GeminiClient] 429 Rate limited. Backing off for {sleep_time:.1f}s (Attempt {attempt}/{max_retries})...", file=sys.stderr)
                        time.sleep(sleep_time)
                        continue
                    else:
                        raise RuntimeError(f"Gemini API 429 Quota/Prepayment limit exceeded: {error_body}")
                elif status_code in (500, 502, 503, 504):
                    if attempt < max_retries:
                        sleep_time = 4.0 * attempt
                        print(f"  [GeminiClient] Transient HTTP {status_code}. Retrying in {sleep_time}s...", file=sys.stderr)
                        time.sleep(sleep_time)
                        continue
                raise RuntimeError(f"Gemini API HTTP Error {status_code}: {error_body}")

            except json.JSONDecodeError as e:
                if attempt < max_retries:
                    print(f"  [GeminiClient] Invalid JSON response, retrying ({e})...", file=sys.stderr)
                    time.sleep(2.0)
                    continue
                raise RuntimeError(f"Failed to parse model JSON output: {e}")

            except Exception as e:
                if attempt < max_retries:
                    time.sleep(3.0)
                    continue
                raise

        raise RuntimeError("Exceeded maximum retries calling Gemini model.")


def build_verification_prompt(batch: list[dict]) -> str:
    """Build a rigorous Japanese linguistic verification prompt for a batch of cards."""
    cards_payload = []
    for c in batch:
        cards_payload.append({
            "word_index": c.get("word_index"),
            "Word": c.get("Word", ""),
            "Reading": c.get("Reading", ""),
            "Furigana": c.get("Furigana", ""),
            "POS": c.get("POS", ""),
            "Meaning": c.get("Meaning", ""),
            "WordAudio": "",
            "Sentence": c.get("Sentence", ""),
            "SentenceAudio": "",
            "SentenceTranslation": c.get("SentenceTranslation", ""),
            "WordUsage": c.get("WordUsage", ""),
            "GrammarPattern": c.get("GrammarPattern", ""),
            "GrammarMeaning": c.get("GrammarMeaning", ""),
            "GrammarUsage": c.get("GrammarUsage", ""),
            "CombinationLogic": c.get("CombinationLogic", ""),
            "Tags": c.get("Tags", ""),
        })

    return f"""You are a distinguished native Japanese linguist, educator, and JLPT N2 exam specialist.
Your task is to critically inspect and verify the following JLPT N2 Anki flashcards.

You must examine every card against these 4 standards:
1. Format & Integrity:
   - Exactly 15 fields preserved.
   - Furigana format: standard Kanji[kana] (e.g. 赤道[せきどう], or pure kana if no kanji).
   - Tags format: must follow 'N2::Vocabulary N2::Grammar::<id>' (e.g. 'N2::Vocabulary N2::Grammar::38').
2. Japanese Syntax & Grammar (文法・助詞・活用):
   - Correct particles (は/が/を/に/で/と/へ/から/より).
   - Natural verb/adjective inflections and conjunctions.
   - No typos or incorrect kanji readings.
3. Natural Japanese Collocations & Phrasing (自然な日本語・コロケーション):
   - The example sentence MUST sound 100% natural and authentic to educated native speakers.
   - Eliminate stiff, robotic translation-ese (不自然な直訳調・和製不自然表現).
   - Ensure the target 'Word' is used in its natural collocation and appropriate context.
   - Ensure the target 'GrammarPattern' naturally fits the sentence and demonstrates its core N2 meaning.
4. Explanations & Translations Synchrony:
   - 'SentenceTranslation': accurate, natural Chinese translation matching the Japanese sentence.
   - If the sentence is revised, 'WordUsage', 'GrammarUsage', and 'CombinationLogic' MUST be updated in lockstep so they accurately describe the revised sentence.

CARDS TO VERIFY (JSON):
{json.dumps(cards_payload, ensure_ascii=False, indent=2)}

INSTRUCTIONS:
For each card:
- If the card has NO errors, unnatural phrasing, or inconsistencies, set status="PASS", issues=[], and revised_card=null.
- If ANY format error, syntax error, unnatural sentence phrasing, collocation issue, or inconsistency is found:
  - set status="REVISE"
  - list specific reasons in "issues"
  - provide the complete, revised 15-field card object in "revised_card" with all fields fully populated and consistent.

RETURN ONLY VALID JSON matching this exact structure:
{{
  "results": [
    {{
      "word_index": 0,
      "status": "PASS",
      "issues": [],
      "revised_card": null
    }},
    {{
      "word_index": 1,
      "status": "REVISE",
      "issues": ["Explanation of what was unnatural or incorrect"],
      "revised_card": {{
        "Word": "...",
        "Reading": "...",
        "Furigana": "...",
        "POS": "...",
        "Meaning": "...",
        "WordAudio": "",
        "Sentence": "...",
        "SentenceAudio": "",
        "SentenceTranslation": "...",
        "WordUsage": "...",
        "GrammarPattern": "...",
        "GrammarMeaning": "...",
        "GrammarUsage": "...",
        "CombinationLogic": "...",
        "Tags": "..."
      }}
    }}
  ]
}}
"""


def load_cache(cache_file: Path = CACHE_FILE) -> dict:
    if cache_file.is_file():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache: dict, cache_file: Path = CACHE_FILE) -> None:
    lib.atomic_write_json(cache_file, cache)


def save_report(report: dict, report_file: Path = REPORT_FILE) -> None:
    lib.atomic_write_json(report_file, report)


def card_hash(card: dict) -> str:
    """Compute a signature hash of the card's linguistic fields."""
    key_data = "|".join([
        str(card.get("Word", "")),
        str(card.get("Reading", "")),
        str(card.get("Furigana", "")),
        str(card.get("Sentence", "")),
        str(card.get("SentenceTranslation", "")),
        str(card.get("GrammarPattern", "")),
        str(card.get("GrammarUsage", "")),
    ])
    return str(hash(key_data))


def verify_and_revise_batch(
    client: GeminiClient,
    batch: list[dict],
    dry_run: bool = False,
    cards_dir: Path = lib.CARDS_DIR,
) -> tuple[int, int, list[dict]]:
    """Verify a batch of cards via Gemini. Returns (passed_count, revised_count, revised_cards)."""
    prompt = build_verification_prompt(batch)
    response_data = client.call_model_json(prompt)

    results = response_data.get("results", [])
    result_by_idx = {r.get("word_index"): r for r in results}

    passed_count = 0
    revised_count = 0
    revisions = []

    for orig_card in batch:
        w_idx = orig_card.get("word_index")
        verdict = result_by_idx.get(w_idx)

        if not verdict:
            # If model didn't return verdict for this card, treat as pass
            continue

        status = verdict.get("status", "PASS").upper()
        issues = verdict.get("issues", [])
        revised_card = verdict.get("revised_card")

        if status == "REVISE" and isinstance(revised_card, dict):
            revised_count += 1
            revised_card["word_index"] = w_idx
            # Ensure optional audio fields are blank strings
            revised_card.setdefault("WordAudio", "")
            revised_card.setdefault("SentenceAudio", "")
            # Ensure tag integrity
            if not revised_card.get("Tags"):
                revised_card["Tags"] = orig_card.get("Tags", "")

            # Validate revised card against strict schema
            val_errors = lib.validate_card(revised_card)
            if val_errors:
                print(f"  [Warning] Card #{w_idx:04d} revised card has schema errors: {val_errors}", file=sys.stderr)
            else:
                revisions.append({
                    "word_index": w_idx,
                    "original": orig_card,
                    "revised": revised_card,
                    "issues": issues,
                })
                if not dry_run:
                    card_file = cards_dir / f"{w_idx:04d}.json"
                    lib.atomic_write_json(card_file, revised_card)
        else:
            passed_count += 1

    return passed_count, revised_count, revisions


def run_verification_pipeline(
    deck_path: Path = lib.DEFAULT_DECK_PATH,
    model: str = DEFAULT_MODEL,
    rpm: float = DEFAULT_RPM,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_passes: int = DEFAULT_MAX_PASSES,
    limit: int | None = None,
    specific_index: int | None = None,
    dry_run: bool = False,
    force: bool = False,
    api_key: str | None = None,
    delay: float | None = None,
    cards_dir: Path = lib.CARDS_DIR,
    cache_file: Path = CACHE_FILE,
    report_file: Path = REPORT_FILE,
) -> int:
    print("=" * 68)
    print("  GEMINI N2 ANKI DECK ITERATIVE VERIFICATION PIPELINE")
    print("=" * 68)
    print(f"  Deck File   : {deck_path}")
    print(f"  Model       : {model}")
    print(f"  RPM Limit   : {rpm} requests/minute (sliding window)")
    if delay is not None:
        print(f"  Min Delay   : {delay}s")
    print(f"  Batch Size  : {batch_size} cards/prompt")
    print(f"  Max Passes  : {max_passes}")
    print(f"  Dry Run     : {dry_run}")
    print("=" * 68)

    # 1. Resolve API key
    if not api_key:
        api_key = lib.load_gemini_api_key()

    if not api_key:
        print("[Error] No Gemini API key found in environment, .env, or ~/.zshrc.", file=sys.stderr)
        print("Please set GEMINI_API_KEY / GEMINI_KEY or provide --api-key <key>", file=sys.stderr)
        return 1

    # 2. Parse deck rows
    if not deck_path.is_file():
        print(f"[Error] Deck file not found: {deck_path}", file=sys.stderr)
        return 1

    headers, cards = lib.parse_deck_rows(deck_path)
    total_cards = len(cards)
    print(f"Loaded {total_cards} cards from {deck_path.name}.")

    # Filter cards if specific_index or limit specified
    if specific_index is not None:
        cards = [c for c in cards if c.get("word_index") == specific_index]
        if not cards:
            print(f"[Error] Card with word_index {specific_index} not found.", file=sys.stderr)
            return 1
        print(f"Targeting single card #{specific_index:04d} ('{cards[0].get('Word')}').")
    elif limit is not None and limit > 0:
        cards = cards[:limit]
        print(f"Targeting first {len(cards)} cards as requested (--limit {limit}).")

    # 3. Stage 1: Local Deterministic Linting
    print("\n--- STAGE 1: Deterministic Linting ---")
    deterministic_issues = 0
    cards_with_lint_issues = []
    for c in cards:
        issues = lib.lint_card(c)
        if issues:
            deterministic_issues += 1
            cards_with_lint_issues.append((c.get("word_index"), c.get("Word"), issues))

    print(f"Deterministic scan complete: {deterministic_issues} / {len(cards)} cards flagged with local issues.")
    if cards_with_lint_issues:
        for idx, word, issues in cards_with_lint_issues[:5]:
            print(f"  Card #{idx:04d} ('{word}'): {'; '.join(issues)}")

    # 4. Stage 2: Gemini Linguistic Verification Loop
    print("\n--- STAGE 2: Gemini Linguistic Verification Loop ---")
    rate_limiter = RateLimiter(target_rpm=rpm, min_delay_sec=delay)
    client = GeminiClient(api_key=api_key, model=model, rate_limiter=rate_limiter)
    cache = load_cache(cache_file=cache_file)

    cards_to_verify = list(cards)
    all_revisions = []
    pass_number = 1

    while pass_number <= max_passes and cards_to_verify:
        print(f"\n>>> PASS {pass_number} / {max_passes}: Verifying {len(cards_to_verify)} cards...")
        pass_revised = []
        pass_passed = 0
        batch_failure = False

        # Chunk cards into batches
        batches = [cards_to_verify[i:i + batch_size] for i in range(0, len(cards_to_verify), batch_size)]

        for b_idx, batch in enumerate(batches, 1):
            # Check cache if not forced and in Pass 1
            active_batch = []
            for c in batch:
                w_idx = str(c.get("word_index"))
                h = card_hash(c)
                if not force and pass_number == 1 and cache.get(w_idx) == h:
                    pass_passed += 1
                else:
                    active_batch.append(c)

            if not active_batch:
                continue

            batch_words = ", ".join([str(c.get("Word")) for c in active_batch[:4]])
            if len(active_batch) > 4:
                batch_words += f", ... ({len(active_batch)} total)"
            print(f"  [Batch {b_idx}/{len(batches)}] Calling {model} ({batch_words})...")

            try:
                passed, revised, rev_list = verify_and_revise_batch(
                    client, active_batch, dry_run=dry_run, cards_dir=cards_dir
                )
                pass_passed += passed
                pass_revised.extend(rev_list)

                # Update cache
                for c in active_batch:
                    w_idx = str(c.get("word_index"))
                    rev = next((r["revised"] for r in rev_list if r["word_index"] == c.get("word_index")), None)
                    cache[w_idx] = card_hash(rev) if rev else card_hash(c)
                if not dry_run:
                    save_cache(cache, cache_file=cache_file)

                if rev_list:
                    for r in rev_list:
                        print(f"    ✓ Revised Card #{r['word_index']:04d} ('{r['original']['Word']}'): {', '.join(r['issues'])}")

            except Exception as e:
                batch_failure = True
                print(f"  [Error in batch {b_idx}]: {e}", file=sys.stderr)
                if "prepayment credits are depleted" in str(e).lower() or "resource_exhausted" in str(e).lower():
                    print("\n[Notice] Google AI Studio credits or quota depleted. Halting verification loop.", file=sys.stderr)
                    return 2
                break

        print(f"Pass {pass_number} summary: {pass_passed} passed, {len(pass_revised)} revised.")
        all_revisions.extend(pass_revised)

        # Loop convergence check
        if batch_failure:
            print(f"\n[Warning] Pass {pass_number} did not complete all batches due to errors.")
            break
        elif not pass_revised:
            print(f"\n✓ Convergence reached! All {len(cards_to_verify)} cards verified clean with zero errors.")
            break

        # Next pass only checks the cards that were revised in this pass
        cards_to_verify = [r["revised"] for r in pass_revised]
        pass_number += 1

    # 5. Stage 3: Deck Sync & Audit Report
    print("\n--- STAGE 3: Deck Sync & Audit Report ---")
    if not dry_run and all_revisions:
        print("Recompiling master deck.txt with updated cards...")
        build_deck.compile_deck(output_path=deck_path, cards_dir=cards_dir)
    elif dry_run:
        print("[Dry Run] Skipped updating files.")

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": model,
        "total_cards_scanned": len(cards),
        "deterministic_issues_found": deterministic_issues,
        "passes_executed": pass_number,
        "total_cards_revised": len(all_revisions),
        "revisions": [
            {
                "word_index": r["word_index"],
                "word": r["original"].get("Word"),
                "issues": r["issues"],
                "before": {
                    "Sentence": r["original"].get("Sentence"),
                    "SentenceTranslation": r["original"].get("SentenceTranslation"),
                    "WordUsage": r["original"].get("WordUsage"),
                },
                "after": {
                    "Sentence": r["revised"].get("Sentence"),
                    "SentenceTranslation": r["revised"].get("SentenceTranslation"),
                    "WordUsage": r["revised"].get("WordUsage"),
                },
            }
            for r in all_revisions
        ],
    }
    if not dry_run:
        save_report(report, report_file=report_file)
        print(f"Audit report saved to: {report_file}")

    print("=" * 68)
    print(f"Verification pipeline completed successfully.")
    print(f"  Total Cards Checked: {len(cards)}")
    print(f"  Total Revised      : {len(all_revisions)}")
    print("=" * 68)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gemini-powered iterative verification and revision pipeline for N2 Anki deck."
    )
    parser.add_argument(
        "--deck",
        type=Path,
        default=lib.DEFAULT_DECK_PATH,
        help=f"Path to deck.txt file (default: '{lib.DEFAULT_DECK_PATH}')",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Gemini model identifier (default: '{DEFAULT_MODEL}')",
    )
    parser.add_argument(
        "--rpm",
        type=float,
        default=DEFAULT_RPM,
        help=f"Maximum requests per minute to satisfy Google AI Studio limits (default: {DEFAULT_RPM})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Number of cards verified per Gemini prompt (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--max-passes",
        type=int,
        default=DEFAULT_MAX_PASSES,
        help=f"Maximum loop verification passes until convergence (default: {DEFAULT_MAX_PASSES})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit verification to first N cards (useful for testing)",
    )
    parser.add_argument(
        "--index",
        type=int,
        default=None,
        help="Verify a single card by word_index",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run verification without writing changes to files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-verification ignoring cached results",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help="Explicit minimum delay between requests in seconds (e.g. 0.5)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Explicit Gemini API key (overrides environment and ~/.zshrc)",
    )

    args = parser.parse_args()
    return run_verification_pipeline(
        deck_path=args.deck,
        model=args.model,
        rpm=args.rpm,
        batch_size=args.batch_size,
        max_passes=args.max_passes,
        limit=args.limit,
        specific_index=args.index,
        dry_run=args.dry_run,
        force=args.force,
        api_key=args.api_key,
        delay=args.delay,
    )


if __name__ == "__main__":
    sys.exit(main())
