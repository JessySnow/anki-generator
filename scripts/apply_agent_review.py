#!/usr/bin/env python3
"""
scripts/apply_agent_review.py - Applies agent review decisions directly to Deck_2 cards and cache.
"""

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CARDS_DIR = REPO_ROOT / "Deck_2" / "progress" / "cards"
CACHE_FILE = REPO_ROOT / "Deck_2" / "progress" / ".verify_cache.json"

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

def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise

def main():
    parser = argparse.ArgumentParser(description="Apply agent review decisions to cards and cache.")
    parser.add_argument("result_file", type=str, help="Path to review result JSON file")
    parser.add_argument("--cache-file", type=str, default=None, help="Custom path to cache file")
    args = parser.parse_args()

    rf = Path(args.result_file)
    if not rf.is_file():
        print(f"Error: Result file not found: {rf}", file=sys.stderr)
        return 1

    try:
        with open(rf, "r", encoding="utf-8") as f:
            items = json.load(f)
    except Exception as e:
        print(f"Error reading {rf}: {e}", file=sys.stderr)
        return 1

    if isinstance(items, dict) and "results" in items:
        items = items["results"]

    if not isinstance(items, list):
        print(f"Error: Expected a list of review objects in {rf}", file=sys.stderr)
        return 1

    cache_file = Path(args.cache_file) if args.cache_file else CACHE_FILE
    cache = {}
    if cache_file.is_file():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}

    pass_count = 0
    revise_count = 0

    for item in items:
        idx = item.get("word_index")
        if idx is None:
            continue
        status = str(item.get("status", "PASS")).upper()
        cf = CARDS_DIR / f"{idx:04d}.json"
        if not cf.is_file():
            print(f"Warning: Card file {cf} does not exist. Skipping.")
            continue

        with open(cf, "r", encoding="utf-8") as f:
            card = json.load(f)

        if status == "PASS" or not item.get("revised_card"):
            pass_count += 1
            cache[str(idx)] = card_hash(card)
            print(f"  ✓ Card #{idx:04d} [{card.get('Word')}]: PASS")
        else:
            revise_count += 1
            issues = item.get("issues", [])
            revised = item["revised_card"]
            # Preserve critical invariant fields
            for k in ("guid", "word_index", "WordAudio", "SentenceAudio"):
                if k in card:
                    revised[k] = card[k]
                elif k in ("WordAudio", "SentenceAudio"):
                    revised[k] = ""
            # Ensure ruby brackets are clean
            atomic_write_json(cf, revised)
            cache[str(idx)] = card_hash(revised)
            print(f"  ⚡ Card #{idx:04d} [{revised.get('Word')}]: REVISE -> {issues}")

    atomic_write_json(cache_file, cache)
    print(f"\nApplied: {pass_count} PASS, {revise_count} REVISED. Total cached: {len(cache)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
