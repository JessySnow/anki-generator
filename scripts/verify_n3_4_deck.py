#!/usr/bin/env python3
"""
scripts/verify_n3_4_deck.py - Gemini-Powered Iterative Loop Verification Pipeline for N3/N4 Anki Deck.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import pipeline_lib as lib
import build_n3_4_deck

DEFAULT_DECK_PATH = REPO_ROOT / "N3_4_Level" / "deck.txt"
DEFAULT_CARDS_DIR = REPO_ROOT / "N3_4_Level" / "progress" / "cards"
CACHE_FILE = REPO_ROOT / "N3_4_Level" / "progress" / ".verify_cache.json"
REPORT_FILE = REPO_ROOT / "N3_4_Level" / "progress" / "verification_report.json"

DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_RPM = 1000.0
DEFAULT_BATCH_SIZE = 15
DEFAULT_MAX_PASSES = 3

import hashlib
import agent_verify_n3_4_deck

class RateLimiter:
    """Sliding-window RPM governor with minimum inter-request delay and exponential backoff."""

    def __init__(self, target_rpm: float = DEFAULT_RPM, min_delay_sec: float | None = None):
        self.target_rpm = max(1.0, float(target_rpm))
        self.window_sec = 60.0
        self.min_delay = min_delay_sec if min_delay_sec is not None else max(0.05, self.window_sec / self.target_rpm)
        self.request_timestamps: collections.deque[float] = collections.deque()
        self.last_request_time: float = 0.0

    def wait_if_needed(self) -> float:
        now = time.time()
        waited_total = 0.0

        time_since_last = now - self.last_request_time
        if self.last_request_time > 0 and time_since_last < self.min_delay:
            gap_needed = self.min_delay - time_since_last
            time.sleep(gap_needed)
            waited_total += gap_needed
            now = time.time()

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
        base_backoff = 6.0

        for attempt in range(1, max_retries + 1):
            self.rate_limiter.wait_if_needed()

            try:
                if self._sdk_client is not None:
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
    """Build a rigorous JLPT N3/N4 Japanese linguistic verification prompt."""
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

    return f"""You are a distinguished native Japanese linguist, educator, and JLPT N3/N4 exam specialist.
Your task is to critically inspect and verify the following JLPT N3/N4 Anki flashcards.

Standards:
1. Format & Integrity:
   - Exactly 15 fields preserved.
   - Furigana format: standard Kanji[kana] (e.g. 英語[えいご], or pure kana if no kanji).
   - Audio fields WordAudio and SentenceAudio MUST remain strictly empty string "".
   - Tags format: must follow 'N3_4::Vocabulary N3_4::Grammar::<id>'.
2. Japanese Syntax & Grammar (文法・助詞・活用):
   - Correct particles (は/が/を/に/で/と/へ/から/より/まで).
   - Natural verb/adjective inflections and conjunctions (て形, た形, ない形, 可能形, etc.).
   - Japanese Shinjitai kanji only (no simplified Chinese characters).
3. Natural Japanese Collocations & Phrasing (自然な日本語・コロケーション):
   - The example sentence MUST sound 100% natural, idiomatic, and authentic to native speakers, tailored for N3/N4 learners.
   - Avoid stiff, awkward translation-ese (不自然な直訳調).
   - Ensure the target 'Word' is used in its authentic collocation and context.
   - Ensure the target 'GrammarPattern' naturally fits the sentence and demonstrates its N3/N4 meaning.
4. Explanations & Translations Synchrony:
   - 'SentenceTranslation': accurate, natural Chinese translation matching the Japanese sentence.
   - 'WordUsage', 'GrammarUsage', and 'CombinationLogic' must accurately describe the sentence.

CARDS TO VERIFY (JSON):
{json.dumps(cards_payload, ensure_ascii=False, indent=2)}

INSTRUCTIONS:
For each card:
- If the card has NO errors, unnatural phrasing, or inconsistencies, set status="PASS", issues=[], and revised_card=null.
- If ANY format error, syntax error, unnatural sentence phrasing, collocation issue, or inconsistency is found:
  - set status="REVISE"
  - list specific reasons in "issues"
  - provide the complete, revised 15-field card object in "revised_card" with all fields fully populated.

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


def card_hash(card: dict) -> str:
    parts = [
        str(card.get("word_index", "")),
        card.get("Word", ""),
        card.get("Sentence", ""),
        card.get("SentenceTranslation", ""),
        card.get("WordUsage", ""),
        card.get("GrammarUsage", ""),
        card.get("CombinationLogic", ""),
    ]
    return hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()[:16]


def load_cache(cache_file: Path = CACHE_FILE) -> dict:
    if cache_file.is_file():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache: dict, cache_file: Path = CACHE_FILE) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def save_report(report: dict, report_file: Path = REPORT_FILE) -> None:
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def run_verification_pipeline(
    deck_path: Path = DEFAULT_DECK_PATH,
    cards_dir: Path = DEFAULT_CARDS_DIR,
    cache_file: Path = CACHE_FILE,
    report_file: Path = REPORT_FILE,
    model: str = DEFAULT_MODEL,
    rpm: float = DEFAULT_RPM,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_passes: int = DEFAULT_MAX_PASSES,
    limit: int | None = None,
    specific_index: int | None = None,
    indices: str | None = None,
    dry_run: bool = False,
    force: bool = False,
    recompile: bool = True,
    api_key: str | None = None,
    delay: float | None = None,
) -> int:
    provider, resolved_api_key, def_model = lib.load_gemini_api_key()
    if api_key:
        resolved_api_key = api_key
        provider = "openrouter" if "sk-or-" in api_key else "google"

    if not resolved_api_key:
        print("Notice: No GEMINI_API_KEY or OPENROUTER_API_KEY available. Running offline agent verification...")
        return agent_verify_n3_4_deck.main()

    card_files = sorted(cards_dir.glob("*.json"))
    if not card_files:
        print(f"Error: No card JSON files found in {cards_dir}")
        return 1

    cards = []
    for cf in card_files:
        try:
            with open(cf, "r", encoding="utf-8") as f:
                cards.append(json.load(f))
        except Exception as e:
            print(f"Warning: Failed to load {cf.name}: {e}")

    cards.sort(key=lambda c: c.get("word_index", 0))

    if specific_index is not None:
        cards = [c for c in cards if c.get("word_index") == specific_index]
        if not cards:
            print(f"Error: Card with word_index={specific_index} not found.")
            return 1
    elif indices:
        from generate_n3_4_deck import parse_index_ranges
        allowed = parse_index_ranges(indices, 1000)
        cards = [c for c in cards if c.get("word_index") in allowed]
        if not cards:
            print(f"Error: No cards found matching indices {indices}.")
            return 1
    elif limit is not None:
        cards = cards[:limit]

    print("=" * 68)
    print(f"JLPT N3/N4 Anki Deck Verification Pipeline")
    print(f"  Model       : {model}")
    print(f"  Target RPM  : {rpm}")
    print(f"  Batch Size  : {batch_size}")
    print(f"  Max Passes  : {max_passes}")
    print(f"  Total Cards : {len(cards)}")
    print(f"  Dry Run     : {dry_run}")
    print("=" * 68)

    print("\n--- STAGE 1: Deterministic Offline Linting ---")
    deterministic_issues = 0
    for c in cards:
        w_idx = c.get("word_index", 0)
        issues = agent_verify_n3_4_deck.check_card_agent(c, w_idx)
        if issues:
            deterministic_issues += len(issues)
            print(f"  Card #{w_idx:04d} ({c.get('Word')}): {'; '.join(issues)}")

    if deterministic_issues == 0:
        print(f"✓ All {len(cards)} cards passed deterministic offline checks.")
    else:
        print(f"! Found {deterministic_issues} deterministic issues across cards.")

    print(f"\n--- STAGE 2: Gemini Linguistic Verification Loop ({model}) ---")
    cache = {} if force else load_cache(cache_file)
    rate_limiter = lib.RateLimiter(target_rpm=rpm, min_delay_sec=delay)
    client = lib.GeminiClient(api_key=resolved_api_key, provider=provider, model=model, rate_limiter=rate_limiter)

    cards_to_verify = list(cards)
    all_revisions: list[dict] = []
    pass_number = 1

    while pass_number <= max_passes and cards_to_verify:
        print(f"\n--- Pass {pass_number} / {max_passes}: Verifying {len(cards_to_verify)} cards ---")

        uncached_cards = []
        for c in cards_to_verify:
            w_idx = str(c.get("word_index", ""))
            current_h = card_hash(c)
            if not force and cache.get(w_idx) == current_h:
                continue
            uncached_cards.append(c)

        cached_count = len(cards_to_verify) - len(uncached_cards)
        if cached_count > 0:
            print(f"  [Cache] {cached_count} cards already verified unchanged. Skipping API calls.")

        if not uncached_cards:
            print(f"✓ All cards in Pass {pass_number} passed or cached.")
            break

        num_batches = (len(uncached_cards) + batch_size - 1) // batch_size
        pass_revised: list[dict] = []
        pass_passed = cached_count
        batch_failure = False

        for b_idx in range(num_batches):
            batch = uncached_cards[b_idx * batch_size : (b_idx + 1) * batch_size]
            prompt = build_verification_prompt(batch)
            print(f"  Verifying batch {b_idx + 1}/{num_batches} ({len(batch)} cards)...", end="", flush=True)

            try:
                response = client.call_model_json(prompt)
                results = response.get("results", [])
                results_by_index = {r.get("word_index"): r for r in results if isinstance(r, dict)}

                batch_revised_count = 0
                for c in batch:
                    w_idx = c.get("word_index")
                    res = results_by_index.get(w_idx)
                    if not res:
                        continue

                    status = res.get("status", "PASS")
                    if status == "REVISE" and res.get("revised_card"):
                        revised = res["revised_card"]
                        revised["guid"] = c.get("guid", "")
                        revised["word_index"] = w_idx
                        revised["WordAudio"] = ""
                        revised["SentenceAudio"] = ""
                        issues = res.get("issues", ["Linguistic revision"])
                        pass_revised.append({
                            "word_index": w_idx,
                            "original": c,
                            "revised": revised,
                            "issues": issues,
                        })
                        batch_revised_count += 1
                        if not dry_run:
                            target_file = cards_dir / f"{w_idx:04d}.json"
                            with open(target_file, "w", encoding="utf-8") as f:
                                json.dump(revised, f, ensure_ascii=False, indent=2)
                        cache[str(w_idx)] = card_hash(revised)
                    else:
                        pass_passed += 1
                        cache[str(w_idx)] = card_hash(c)

                if not dry_run:
                    save_cache(cache, cache_file=cache_file)

                print(f" done ({batch_revised_count} revised).")

            except Exception as e:
                batch_failure = True
                print(f" failed: {e}", file=sys.stderr)
                break

        print(f"Pass {pass_number} summary: {pass_passed} passed, {len(pass_revised)} revised.")
        all_revisions.extend(pass_revised)

        if batch_failure or not pass_revised:
            break

        cards_to_verify = [r["revised"] for r in pass_revised]
        pass_number += 1

    print("\n--- STAGE 3: Deck Sync & Audit Report ---")
    if not dry_run and all_revisions and recompile:
        print("Recompiling N3_4_Level/deck.txt with updated cards...")
        build_n3_4_deck.compile_deck(cards_dir=cards_dir, output_path=deck_path)
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
            }
            for r in all_revisions
        ],
    }
    if not dry_run:
        save_report(report, report_file=report_file)
        print(f"Audit report saved to: {report_file}")

    print("=" * 68)
    print(f"Verification pipeline complete. Revised: {len(all_revisions)}")
    print("=" * 68)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Gemini API Verification for N3/N4 deck")
    parser.add_argument("--deck", type=Path, default=DEFAULT_DECK_PATH)
    parser.add_argument("--cards-dir", type=Path, default=DEFAULT_CARDS_DIR)
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    parser.add_argument("--rpm", type=float, default=DEFAULT_RPM)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--max-passes", type=int, default=DEFAULT_MAX_PASSES)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--index", type=int, default=None)
    parser.add_argument("--indices", type=str, default=None, help="Range or comma-separated list of word indices (e.g. 0-139)")
    parser.add_argument("--cache-file", type=Path, default=CACHE_FILE)
    parser.add_argument("--report-file", type=Path, default=REPORT_FILE)
    parser.add_argument("--no-recompile", action="store_true", help="Skip recompiling deck.txt")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--delay", type=float, default=None)
    args = parser.parse_args()

    return run_verification_pipeline(
        deck_path=args.deck,
        cards_dir=args.cards_dir,
        cache_file=args.cache_file,
        report_file=args.report_file,
        model=args.model,
        rpm=args.rpm,
        batch_size=args.batch_size,
        max_passes=args.max_passes,
        limit=args.limit,
        specific_index=args.index,
        indices=args.indices,
        dry_run=args.dry_run,
        force=args.force,
        recompile=not args.no_recompile,
        api_key=args.api_key,
        delay=args.delay,
    )


if __name__ == "__main__":
    sys.exit(main())

