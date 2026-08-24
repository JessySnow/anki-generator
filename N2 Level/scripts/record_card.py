#!/usr/bin/env python3
"""Atomically record one finished card: append it to this Words file's scratch
output AND mark its word id done in this Words file's progress file, together,
so the two can never drift out of sync if a run is interrupted.

Usage: record_card.py --words-file Words1.json --card-json '<json>'
"""

import argparse
import json
import sys

import lib


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--words-file", required=True, choices=lib.WORDS_FILES)
    parser.add_argument("--card-json", required=True)
    args = parser.parse_args()

    card = json.loads(args.card_json)
    missing = [k for k in lib.CARD_KEYS if k not in card]
    if missing:
        print(f"[record_card] missing keys: {missing}", file=sys.stderr)
        return 1

    scratch = lib.load_scratch(args.words_file)
    scratch["cards"].append(card)
    lib.atomic_write_json(lib.scratch_path(args.words_file), scratch)

    progress = lib.load_progress(args.words_file)
    completed = set(progress.get("completed_ids", []))
    completed.add(card["id"])
    lib.atomic_write_json(lib.progress_path(args.words_file), {"completed_ids": sorted(completed)})

    print(f"[record_card] recorded id={card['id']} word={card['word']!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
