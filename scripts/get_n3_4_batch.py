#!/usr/bin/env python3
"""
Fetch batch of vocabulary items from N3_4_Level/Words.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORDS_PATH = REPO_ROOT / "N3_4_Level" / "Words.json"
CARDS_DIR = REPO_ROOT / "N3_4_Level" / "progress" / "cards"

def fetch_batch(start: int = 0, end: int = 0, size: int = 10, only_uncompleted: bool = True):
    with open(WORDS_PATH, "r", encoding="utf-8") as f:
        words = json.load(f)["vocabulary_list"]

    completed = set()
    if CARDS_DIR.is_dir():
        for p in CARDS_DIR.glob("*.json"):
            try:
                completed.add(int(p.stem))
            except ValueError:
                pass

    if end > start:
        target_indices = list(range(start, min(end, len(words))))
    else:
        uncompleted = [w["word_index"] for w in words if w["word_index"] not in completed]
        target_indices = uncompleted[start : start + size]

    if only_uncompleted:
        target_indices = [i for i in target_indices if i not in completed]

    return [words[i] for i in target_indices if i < len(words)]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=0)
    parser.add_argument("--size", type=int, default=10)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    items = fetch_batch(start=args.start, end=args.end, size=args.size, only_uncompleted=not args.all)
    print(json.dumps(items, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
