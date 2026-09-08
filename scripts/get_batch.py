#!/usr/bin/env python3
"""
Fetch the next uncompleted batch of words from Words.json, paired with
randomly sampled grammar points from Grammar.json.
Outputs a structured JSON payload for worker subagents.

Usage:
  python3 scripts/get_batch.py --size 5 --json
  python3 scripts/get_batch.py --indices 0,1,2 --json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

# Add scripts directory to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import pipeline_lib as lib


def fetch_batch(
    size: int = 5,
    offset: int = 0,
    specific_indices: list[int] | None = None,
    words_path: Path = lib.WORDS_PATH,
    grammar_path: Path = lib.GRAMMAR_PATH,
    cards_dir: Path = lib.CARDS_DIR,
) -> dict:
    words = lib.load_words(words_path)
    grammar = lib.load_grammar(grammar_path)
    completed = lib.get_completed_indices(cards_dir)

    total_words = len(words)

    if specific_indices is not None:
        target_indices = [i for i in specific_indices if 0 <= i < total_words]
    else:
        # Find all uncompleted indices in order
        uncompleted = [i for i in range(total_words) if i not in completed]
        target_indices = uncompleted[offset : offset + size]

    batch_items = []
    for idx in target_indices:
        w = words[idx]
        word, reading, furigana = lib.parse_term(w.get("term", ""))
        chosen_grammar = random.choice(grammar)

        batch_items.append({
            "word_index": idx,
            "word": word,
            "reading": reading,
            "furigana": furigana,
            "pos": w.get("part_of_speech", ""),
            "meaning": w.get("definition", ""),
            "context_sentence": w.get("context_sentence", ""),
            "grammar": {
                "id": chosen_grammar.get("id"),
                "pattern": chosen_grammar.get("pattern", ""),
                "connection": chosen_grammar.get("connection", ""),
                "meaning": chosen_grammar.get("meaning", ""),
                "example_sentences": chosen_grammar.get("example_sentences", [])[:2],
            },
        })

    return {
        "total_words": total_words,
        "completed_count": len(completed),
        "remaining_count": total_words - len(completed),
        "batch_size": len(batch_items),
        "batch": batch_items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch uncompleted word batch paired with grammar for card generation."
    )
    parser.add_argument(
        "--size",
        type=int,
        default=5,
        help="Number of uncompleted items to fetch (default: 5)",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Offset among uncompleted items (default: 0)",
    )
    parser.add_argument(
        "--indices",
        type=str,
        default="",
        help="Specific comma-separated word indices to fetch (e.g. '0,1,2')",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=True,
        help="Output raw JSON format (default: True)",
    )
    args = parser.parse_args()

    specific_indices = None
    if args.indices.strip():
        try:
            specific_indices = [int(x.strip()) for x in args.indices.split(",") if x.strip()]
        except ValueError:
            print("Error: --indices must be comma-separated integers", file=sys.stderr)
            return 1

    result = fetch_batch(
        size=args.size,
        offset=args.offset,
        specific_indices=specific_indices,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
