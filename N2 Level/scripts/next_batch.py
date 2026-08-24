#!/usr/bin/env python3
"""Pick the next N unused words from one Words*.json file, each paired with a
randomly chosen grammar pattern. Prints the batch as JSON to stdout.

Usage: next_batch.py --words-file Words1.json [--n 5]
"""

import argparse
import random
import sys

import lib


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--words-file", required=True, choices=lib.WORDS_FILES)
    parser.add_argument("--n", type=int, default=5)
    args = parser.parse_args()

    vocab = lib.load_vocab(args.words_file)
    grammar = lib.load_grammar()
    progress = lib.load_progress(args.words_file)
    done_ids = set(progress.get("completed_ids", []))

    batch = []
    for item in vocab:
        if len(batch) >= args.n:
            break
        if item["id"] in done_ids:
            continue
        entry = dict(item)
        chosen = dict(random.choice(grammar))
        chosen["example_sentences"] = chosen["example_sentences"][:2]
        entry["grammar"] = chosen
        batch.append(entry)

    print(lib.json.dumps({"words_file": args.words_file, "batch": batch}, ensure_ascii=False, indent=2))

    if not batch:
        print(f"[next_batch] no unused words remaining in {args.words_file}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
