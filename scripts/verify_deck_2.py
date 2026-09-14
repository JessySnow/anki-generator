#!/usr/bin/env python3
"""
scripts/verify_deck_2.py - Gemini 3.8 Flash LLM Linguistic Verification Loop for Deck_2.
Critically reviews Japanese sentences, grammar connection forms, collocations,
and translations in batches of 15 cards, auto-correcting any subtle linguistic nuances.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor
import threading

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import pipeline_lib as lib
import build_deck_2
import agent_verify_deck_2

DEFAULT_DECK_PATH = REPO_ROOT / "Deck_2" / "deck.txt"
DEFAULT_CARDS_DIR = REPO_ROOT / "Deck_2" / "progress" / "cards"
CACHE_FILE = REPO_ROOT / "Deck_2" / "progress" / ".verify_cache.json"
REPORT_FILE = REPO_ROOT / "Deck_2" / "progress" / "verification_report.json"

DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_RPM = 1000.0
DEFAULT_BATCH_SIZE = 15


class RateLimiter:
    def __init__(self, target_rpm: float = DEFAULT_RPM):
        self.target_rpm = max(1.0, float(target_rpm))
        self.window_sec = 60.0
        self.min_delay = max(0.05, self.window_sec / self.target_rpm)
        self.request_timestamps: collections.deque[float] = collections.deque()
        self.last_request_time: float = 0.0
        self.lock = threading.Lock()

    def wait_if_needed(self) -> float:
        with self.lock:
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


import ssl

class UniversalVerifierClient:
    def __init__(self, api_key: str, provider: str = "google", model: str = DEFAULT_MODEL, rate_limiter: RateLimiter | None = None):
        self.api_key = api_key
        self.provider = provider
        self.model = model
        self.rate_limiter = rate_limiter or RateLimiter()
        self.ssl_ctx = ssl._create_unverified_context()

    def call_model_json(self, prompt: str, max_retries: int = 4) -> dict:
        base_backoff = 4.0
        for attempt in range(1, max_retries + 1):
            self.rate_limiter.wait_if_needed()
            try:
                if self.provider == "openrouter":
                    url = "https://openrouter.ai/api/v1/chat/completions"
                    payload = {
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"},
                    }
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/JessySnow/anki-generator",
                        "X-Title": "Anki Generator",
                    }
                else:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "responseMimeType": "application/json",
                            "temperature": 0.1,
                        },
                    }
                    headers = {"Content-Type": "application/json"}

                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=120, context=self.ssl_ctx) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    if self.provider == "openrouter":
                        text = res_json["choices"][0]["message"]["content"]
                    else:
                        parts = res_json.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                        answer_parts = [p.get("text", "") for p in parts if not p.get("thought") and p.get("text")]
                        if answer_parts:
                            text = answer_parts[-1]
                        elif parts and "text" in parts[-1]:
                            text = parts[-1]["text"]
                        else:
                            text = ""

                cleaned_text = re.sub(r"^```json\s*", "", text.strip(), flags=re.IGNORECASE)
                cleaned_text = re.sub(r"\s*```$", "", cleaned_text.strip())
                try:
                    return json.loads(cleaned_text)
                except json.JSONDecodeError:
                    m = re.search(r"(\[.*\]|\{.*\})", cleaned_text, re.DOTALL)
                    if m:
                        return json.loads(m.group(0))
                    raise

            except urllib.error.HTTPError as e:
                status_code = e.code
                error_body = ""
                try:
                    error_body = e.read().decode("utf-8")
                except Exception:
                    pass

                if status_code == 429 or "RESOURCE_EXHAUSTED" in error_body or "rate-limited" in error_body.lower():
                    sleep_time = (base_backoff * (2 ** (attempt - 1))) + random.uniform(0.5, 2.0)
                    time.sleep(sleep_time)
                    continue
                elif status_code in (500, 502, 503, 504):
                    time.sleep(3.0 * attempt)
                    continue
                raise RuntimeError(f"API HTTP Error {status_code}: {error_body}")
            except Exception as e:
                if attempt < max_retries:
                    time.sleep(2.0 * attempt)
                    continue
                raise
        raise RuntimeError("Exceeded maximum retries calling model.")


def build_verification_prompt(batch: list[dict]) -> str:
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

    return f"""You are a distinguished native Japanese linguist, educator, and JLPT exam specialist.
Your task is to critically inspect and verify the following Japanese Anki flashcards.

Verification Standards:
1. Syntax & Grammar (文法・助詞・活用):
   - Correct particles (は/が/を/に/で/と/へ/から/より/まで).
   - Natural verb/adjective inflections and conjunctions (て形, た形, ない形, 可能形, 意向形, etc.).
   - Modern Japanese Shinjitai (新字体) kanji only (no Simplified Chinese characters).
2. Natural Collocations & Phrasing (自然な日本語・コロケーション):
   - The sentence MUST sound 100% natural, idiomatic, and authentic to native speakers.
   - Avoid stiff, awkward translation-ese (不自然な直訳調).
   - Ensure the target 'Word' is used in its authentic native collocation.
   - Ensure the target 'GrammarPattern' naturally fits the sentence and demonstrates its exact meaning.
3. Explanations & Translations Synchrony:
   - 'SentenceTranslation': accurate, natural Chinese translation matching the Japanese sentence.
   - 'WordUsage', 'GrammarUsage', and 'CombinationLogic' must accurately describe the sentence structure.

CARDS TO VERIFY:
{json.dumps(cards_payload, ensure_ascii=False, indent=2)}

INSTRUCTIONS:
For each card:
- If the card has NO errors, unnatural phrasing, or inconsistencies, return status="PASS", issues=[], revised_card=null.
- If ANY format error, syntax error, unnatural sentence phrasing, collocation issue, or inconsistency is found:
  - set status="REVISE"
  - list specific reasons in "issues"
  - provide the complete, revised 15-field card object in "revised_card" with all fields fully populated.

RETURN ONLY A VALID JSON OBJECT matching this exact structure:
{{
  "results": [
    {{
      "word_index": 0,
      "status": "PASS",
      "issues": [],
      "revised_card": null
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


def main():
    parser = argparse.ArgumentParser(description="LLM Linguistic Verification for Deck_2")
    parser.add_argument("--provider", type=str, default="auto", choices=["auto", "google", "openrouter"], help="Provider (auto, google, openrouter)")
    parser.add_argument("--batch-size", type=int, default=None, help="Cards per verification call (default: 4 for Gemma, 15 for Gemini)")
    parser.add_argument("--workers", type=int, default=2, help="Concurrent workers (default: 2)")
    parser.add_argument("--rpm", type=float, default=None, help="Target RPM rate limiter (default: 30 for Gemma, 1000 for Gemini)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Model identifier")
    parser.add_argument("--indices", type=str, default="", help="Specific indices or ranges (e.g. 0-99, 100-199)")
    parser.add_argument("--cache-file", type=str, default=None, help="Custom path to cache file")
    parser.add_argument("--no-recompile", action="store_true", help="Do not recompile deck at completion")
    parser.add_argument("--force", action="store_true", help="Re-verify cards even if cached as PASS")
    parser.add_argument("--dry-run", action="store_true", help="Check and print issues without saving changes")
    args = parser.parse_args()

    # Determine provider and API key
    provider = args.provider
    if provider == "auto":
        if "/" in args.model:
            provider = "openrouter"
        else:
            provider = "google"

    is_gemma = "gemma" in args.model.lower()

    if provider == "openrouter":
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            _, api_key, _ = lib.load_gemini_api_key()
        if not api_key:
            print("Error: OPENROUTER_API_KEY environment variable not found.", file=sys.stderr)
            return 1
        target_rpm = args.rpm if args.rpm is not None else (30.0 if is_gemma else 60.0)
        batch_size = args.batch_size if args.batch_size is not None else (2 if is_gemma else 10)
    else:
        _, api_key, _ = lib.load_gemini_api_key()
        if not api_key:
            print("Error: No Gemini API key found.", file=sys.stderr)
            return 1
        target_rpm = args.rpm if args.rpm is not None else (30.0 if is_gemma else DEFAULT_RPM)
        batch_size = args.batch_size if args.batch_size is not None else (2 if is_gemma else DEFAULT_BATCH_SIZE)

    card_files = sorted(DEFAULT_CARDS_DIR.glob("*.json"))
    if not card_files:
        print(f"Error: No card JSON files found in {DEFAULT_CARDS_DIR}", file=sys.stderr)
        return 1

    cards = []
    for cf in card_files:
        try:
            with open(cf, "r", encoding="utf-8") as f:
                cards.append(json.load(f))
        except Exception:
            pass

    cards.sort(key=lambda c: c.get("word_index", 0))

    target_indices = None
    if args.indices:
        target_indices = set()
        for part in args.indices.split(","):
            part = part.strip()
            if "-" in part:
                s_idx, e_idx = part.split("-", 1)
                target_indices.update(range(int(s_idx), int(e_idx) + 1))
            elif part.isdigit():
                target_indices.add(int(part))

    cache_file = Path(args.cache_file) if args.cache_file else CACHE_FILE
    cache = {}
    if CACHE_FILE.is_file():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}
    if cache_file.is_file() and cache_file != CACHE_FILE:
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache.update(json.load(f))
        except Exception:
            pass

    pending_cards = []
    for c in cards:
        idx = c.get("word_index")
        if target_indices is not None and idx not in target_indices:
            continue
        chash = card_hash(c)
        if not args.force and cache.get(str(idx)) == chash:
            continue
        pending_cards.append(c)

    print("==================================================================")
    print("  LLM LINGUISTIC VERIFICATION (Deck_2)")
    print("==================================================================")
    print(f"Provider:                {provider}")
    print(f"Model:                   {args.model}")
    print(f"Target RPM:              {target_rpm:.1f}")
    print(f"Batch Size:              {batch_size}")
    print(f"Concurrent Workers:      {args.workers}")
    print(f"Total Cards Loaded:      {len(cards)}")
    print(f"Cards Pending Check:     {len(pending_cards)}")

    if not pending_cards:
        print("All requested cards already verified and cached as PASS!")
        return 0

    rate_limiter = RateLimiter(target_rpm=target_rpm)
    client = UniversalVerifierClient(api_key=api_key, provider=provider, model=args.model, rate_limiter=rate_limiter)

    chunks = [pending_cards[i : i + batch_size] for i in range(0, len(pending_cards), batch_size)]
    total_chunks = len(chunks)

    lock = threading.Lock()
    pass_count = 0
    revise_count = 0
    start_time = time.time()

    def process_verification_chunk(chunk_tuple):
        nonlocal pass_count, revise_count
        b_idx, chunk = chunk_tuple
        chunk_indices = [c["word_index"] for c in chunk]
        with lock:
            print(f"\n[Batch {b_idx + 1}/{total_chunks}] Verifying indices {chunk_indices[0]}..{chunk_indices[-1]} ({len(chunk)} cards)...", flush=True)

        prompt = build_verification_prompt(chunk)
        try:
            res = client.call_model_json(prompt)
        except Exception as e:
            with lock:
                print(f"  [Error] Verification API call failed for batch {chunk_indices}: {e}", file=sys.stderr, flush=True)
            return

        if isinstance(res, list):
            results = res
        elif isinstance(res, dict):
            results = res.get("results", [])
        else:
            results = []

        results_by_idx = {r.get("word_index"): r for r in results if isinstance(r, dict) and r.get("word_index") is not None}

        for card in chunk:
            idx = card["word_index"]
            r_info = results_by_idx.get(idx)
            if not r_info:
                continue

            status = r_info.get("status", "PASS").upper()
            issues = r_info.get("issues", [])
            revised = r_info.get("revised_card")

            with lock:
                if status == "PASS" or not revised:
                    pass_count += 1
                    cache[str(idx)] = card_hash(card)
                    print(f"  ✓ Card #{idx:04d} [{card.get('Word')}]: PASS", flush=True)
                else:
                    revise_count += 1
                    print(f"  ⚡ Card #{idx:04d} [{card.get('Word')}]: REVISE -> {issues}", flush=True)
                    if not args.dry_run:
                        # Keep original metadata
                        for k in ("guid", "word_index", "WordAudio", "SentenceAudio"):
                            if k in card:
                                revised[k] = card[k]
                        cf_path = DEFAULT_CARDS_DIR / f"{idx:04d}.json"
                        lib.atomic_write_json(cf_path, revised)
                        cache[str(idx)] = card_hash(revised)

        with lock:
            if not args.dry_run:
                lib.atomic_write_json(cache_file, cache)

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        list(executor.map(process_verification_chunk, enumerate(chunks)))

    if not args.dry_run:
        lib.atomic_write_json(cache_file, cache)

    elapsed = time.time() - start_time
    print("\n==================================================================")
    print(f"Verification Pass Complete in {elapsed:.1f}s!")
    print(f"Verified PASS:   {pass_count} cards")
    print(f"Revised & Fixed: {revise_count} cards")
    print("==================================================================")

    if revise_count > 0 and not args.dry_run and not args.no_recompile:
        print("\nRecompiling Deck_2/deck.txt and running deterministic linter...")
        build_deck_2.compile_deck()
        agent_verify_deck_2.verify_deck()

    return 0

if __name__ == "__main__":
    sys.exit(main())
