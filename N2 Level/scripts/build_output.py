#!/usr/bin/env python3
"""Take this turn's scratch cards for one Words file, append the passing ones
as TSV rows to output_cards.txt, and revert any excluded (failed-verification)
ids out of progress so they're automatically re-offered by a future next_batch
call. Clears the scratch file afterwards - it's turn-scoped working state.

Usage: build_output.py --words-file Words1.json [--exclude-ids 1501,1810]
"""

import argparse
import sys

import lib


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--words-file", required=True, choices=lib.WORDS_FILES)
    parser.add_argument("--exclude-ids", default="")
    args = parser.parse_args()

    exclude_ids = {int(x) for x in args.exclude_ids.split(",") if x.strip()}

    scratch = lib.load_scratch(args.words_file)
    cards = scratch.get("cards", [])
    if not cards:
        print(f"[build_output] no scratch cards for {args.words_file}", file=sys.stderr)
        return 0

    passing = [c for c in cards if c["id"] not in exclude_ids]
    failing = [c for c in cards if c["id"] in exclude_ids]

    rows = []
    for card in passing:
        card = dict(card)
        card["_words_file"] = args.words_file
        rows.append(lib.card_to_row(card))
    lib.write_output_rows(rows)

    if failing:
        progress = lib.load_progress(args.words_file)
        completed = set(progress.get("completed_ids", []))
        completed -= exclude_ids
        lib.atomic_write_json(lib.progress_path(args.words_file), {"completed_ids": sorted(completed)})

    lib.atomic_write_json(lib.scratch_path(args.words_file), {"words_file": args.words_file, "cards": []})

    print(f"[build_output] {args.words_file}: wrote {len(passing)} cards, "
          f"deferred {len(failing)} failed ids: {sorted(exclude_ids)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
