#!/usr/bin/env python3
"""
scripts/generate_n3_4_deck.py - Gemini 3.8 Powered Card Generation Pipeline for N3/N4 Anki Deck.

Generates complete 15-field active recall cards adhering to the N2 production standard
using Gemini 3.8 (google/gemini-3.8-flash via OpenRouter or Direct Google API).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import pipeline_lib as lib
import record_n3_4_card as recorder
from prepare_n3_4_words import GRAMMAR_ZH

WORDS_PATH = REPO_ROOT / "N3_4_Level" / "Words.json"
GRAMMAR_PATH = REPO_ROOT / "N3_4_Level" / "Grammar.json"
CARDS_DIR = REPO_ROOT / "N3_4_Level" / "progress" / "cards"

with open(GRAMMAR_PATH, "r", encoding="utf-8") as f:
    GRAMMAR_BY_ID = {g["id"]: g for g in json.load(f)["grammar_list"]}

SYSTEM_PROMPT = """You are an elite Japanese lexicographer and JLPT exam author creating master-level Anki flashcards.
Your goal is to author authentic, natural, high-context Japanese sentences and deep linguistic annotations for JLPT N3/N4 vocabulary paired with specific N3/N4 grammar points.

For each vocabulary item, generate:
1. Sentence:
   - An authentic, grammatically flawless, natural Japanese sentence.
   - Seamlessly integrates the target vocabulary (or its natural conjugation) with the assigned grammar pattern.
   - Do NOT use furigana ruby brackets, HTML tags, or romaji inside the Sentence string. Write plain, natural Japanese (kanji/kana).
   - Japanese Shinjitai (新字体) only. Never use Simplified Chinese characters.
2. SentenceTranslation:
   - Elegant, accurate Chinese translation capturing the exact nuance and tone of the Japanese sentence.
3. WordUsage:
   - Detailed grammatical explanation in Chinese: syntactic function (subject, direct object, predicate), key collocations, and contextual nuance.
4. GrammarMeaning:
   - Deep explanation of the grammar pattern in Chinese: grammatical function, core meaning, nuances, and register.
5. GrammarUsage:
   - Grammatical connection form (辞書形, 連用形, て形, 名詞+の, etc.) and structural role in this sentence in Chinese.
6. CombinationLogic:
   - Clear Chinese rationale explaining why this vocabulary item and this grammar pattern naturally co-occur in native communication.

Strict Output Format:
Return a single JSON object with the key "cards", containing an array of card objects with keys:
"word_index", "Sentence", "SentenceTranslation", "WordUsage", "GrammarMeaning", "GrammarUsage", "CombinationLogic".
"""


def build_generation_prompt(items: list[dict]) -> str:
    lines = [
        SYSTEM_PROMPT,
        "\nGenerate complete linguistic data for the following vocabulary items:\n"
    ]
    for it in items:
        w_idx = it["word_index"]
        word = it["word"]
        reading = it["reading"]
        pos = it["pos"]
        meaning = it["meaning"]
        colloc = it.get("collocation_note", "")
        gid = it["grammar_id"]
        g_entry = GRAMMAR_BY_ID.get(gid, {})
        gpat = g_entry.get("pattern", it["grammar_pattern"])
        gconn = g_entry.get("connection", "")
        gmean = g_entry.get("meaning", "")

        entry_text = (
            f"Item #{w_idx:04d}:\n"
            f"  - Word: {word} ({reading})\n"
            f"  - POS: {pos}\n"
            f"  - Meaning: {meaning}\n"
        )
        if colloc:
            entry_text += f"  - Collocation Note: {colloc}\n"
        entry_text += (
            f"  - Grammar Point #{gid}: {gpat}\n"
            f"  - Connection Form: {gconn}\n"
            f"  - Grammar Core Meaning: {gmean}\n"
        )
        lines.append(entry_text)

    lines.append("\nOutput the JSON object with the 'cards' list now:")
    return "\n".join(lines)


def parse_index_ranges(range_str: str, max_count: int) -> set[int]:
    if not range_str or range_str.lower() == "all":
        return set(range(max_count))
    indices = set()
    for part in range_str.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start, end = int(start_s), int(end_s)
            indices.update(range(start, end + 1))
        else:
            indices.add(int(part))
    return indices


def main():
    parser = argparse.ArgumentParser(description="Gemini 3.8 Card Generation Pipeline for N3/N4")
    parser.add_argument("--batch-size", type=int, default=5, help="Cards per API call (default: 5)")
    parser.add_argument("--rpm", type=float, default=1000.0, help="Target RPM rate limiter (default: 1000)")
    parser.add_argument("--model", type=str, default="gemini-3.8-flash", help="Gemini 3.8 model identifier")
    parser.add_argument("--indices", type=str, default="", help="Specific indices or ranges (e.g. 56-111,280-335)")
    parser.add_argument("--force", action="store_true", help="Regenerate cards even if already present")
    args = parser.parse_args()

    if not WORDS_PATH.exists():
        print(f"Error: {WORDS_PATH} not found. Run scripts/prepare_n3_4_words.py first.", file=sys.stderr)
        return 1

    with open(WORDS_PATH, "r", encoding="utf-8") as f:
        words_data = json.load(f)["vocabulary_list"]
    total_words = len(words_data)

    target_indices = parse_index_ranges(args.indices, total_words)

    # Filter for missing or forced cards
    pending_items = []
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    for it in words_data:
        idx = it["word_index"]
        if idx not in target_indices:
            continue
        card_file = CARDS_DIR / f"{idx:04d}.json"
        if not args.force and card_file.exists():
            continue
        pending_items.append(it)

    print("==================================================================")
    print("  GEMINI 3.8 JLPT N3/N4 CARD GENERATION PIPELINE")
    print("==================================================================")
    print(f"Total vocabulary items:  {total_words}")
    print(f"Items pending authoring: {len(pending_items)}")
    print(f"Batch size per call:     {args.batch_size}")
    print(f"Model:                   {args.model}")

    if not pending_items:
        print("All requested cards already exist! Nothing to generate.")
        return 0

    provider, api_key, _ = lib.load_gemini_api_key()
    if not api_key:
        print("Error: No Gemini or OpenRouter API key found in environment.", file=sys.stderr)
        return 1

    print(f"Using Provider:          {provider}")
    rate_limiter = lib.RateLimiter(target_rpm=args.rpm)
    client = lib.GeminiClient(api_key=api_key, provider=provider, model=args.model, rate_limiter=rate_limiter)

    # Process in batches
    success_count = 0
    start_time = time.time()

    for b_start in range(0, len(pending_items), args.batch_size):
        chunk = pending_items[b_start : b_start + args.batch_size]
        chunk_indices = [it["word_index"] for it in chunk]
        print(f"\n[Batch {b_start // args.batch_size + 1}/{(len(pending_items) + args.batch_size - 1) // args.batch_size}] Generating indices {chunk_indices[0]}..{chunk_indices[-1]} ({len(chunk)} cards)...", flush=True)

        prompt = build_generation_prompt(chunk)
        try:
            res = client.call_model_json(prompt)
        except Exception as e:
            print(f"  [Error] Failed to call model for batch {chunk_indices}: {e}", file=sys.stderr, flush=True)
            continue

        raw_cards = res.get("cards", [])
        def parse_idx(v):
            try:
                return int(v)
            except Exception:
                return None

        cards_by_idx = {parse_idx(c.get("word_index")): c for c in raw_cards if parse_idx(c.get("word_index")) is not None}
        if len(raw_cards) == len(chunk):
            for i, c in enumerate(raw_cards):
                c_idx = parse_idx(c.get("word_index"))
                if c_idx is None or c_idx not in chunk_indices:
                    cards_by_idx[chunk[i]["word_index"]] = c

        for it in chunk:
            idx = it["word_index"]
            c_data = cards_by_idx.get(idx)
            if not c_data:
                print(f"  [Warning] Card #{idx:04d} ({it['word']}) missing from model output!", file=sys.stderr, flush=True)
                continue

            gid = it["grammar_id"]
            g_entry = GRAMMAR_BY_ID.get(gid, {})
            gpat = g_entry.get("pattern", it["grammar_pattern"])
            gmean = c_data.get("GrammarMeaning", "").strip() or g_entry.get("meaning", "")

            # Assemble full 15-field card schema
            full_card = {
                "guid": it["guid"],
                "word_index": idx,
                "Word": it["word"],
                "Reading": it["reading"],
                "Furigana": it["furigana"],
                "POS": it["pos"],
                "Meaning": it["meaning"],
                "WordAudio": "",
                "Sentence": c_data.get("Sentence", "").strip(),
                "SentenceAudio": "",
                "SentenceTranslation": c_data.get("SentenceTranslation", "").strip(),
                "WordUsage": c_data.get("WordUsage", "").strip(),
                "GrammarPattern": gpat,
                "GrammarMeaning": gmean,
                "GrammarUsage": c_data.get("GrammarUsage", "").strip(),
                "CombinationLogic": c_data.get("CombinationLogic", "").strip(),
                "Tags": f"N3_4::Vocabulary N3_4::Grammar::{gid} {it.get('original_tags', '')}".strip()
            }

            ok, msg = recorder.record_card(full_card)
            if ok:
                success_count += 1
                total_done = len(list(CARDS_DIR.glob("*.json")))
                print(f"  ✓ [{total_done}/{total_words}] ({total_done/total_words*100:.1f}%) Saved Card #{idx:04d}: {it['word']}", flush=True)
            else:
                print(f"  ✗ [Validation Error] Card #{idx:04d}: {msg}", file=sys.stderr, flush=True)

    elapsed = time.time() - start_time
    total_completed = len(list(CARDS_DIR.glob("*.json")))
    print("\n==================================================================", flush=True)
    print(f"Generation Pass Complete in {elapsed:.1f}s!", flush=True)
    print(f"Newly Generated:  {success_count} cards", flush=True)
    print(f"Total Completed:  {total_completed} / {total_words} ({total_completed/total_words*100:.1f}%)", flush=True)
    print("==================================================================", flush=True)

    return 0 if total_completed == total_words else 1


if __name__ == "__main__":
    sys.exit(main())
