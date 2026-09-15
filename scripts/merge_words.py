#!/usr/bin/env python3
"""
Merge Japanese vocabulary JSON files (e.g. Words1.json ... Words10.json)
into a single combined Words.json file.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Resolve default directory relative to repository root
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_DIR = (
    REPO_ROOT / "N2 Level" / "batches"
    if (REPO_ROOT / "N2 Level" / "batches").is_dir()
    else (REPO_ROOT / "N2 Level")
)


def extract_word_number(path: Path) -> int:
    """Extract the numeric index from filename like Words1.json or Words10.json."""
    match = re.search(r"Words(\d+)\.json$", path.name)
    if not match:
        raise ValueError(f"Could not find numeric index in filename: {path.name}")
    return int(match.group(1))


def merge_word_files(
    input_dir: Path,
    output_file: Path | None = None,
    dry_run: bool = False,
) -> int:
    """Find and merge all Words*.json in numerical order."""
    if not input_dir.is_dir():
        print(f"Error: Directory not found: {input_dir}", file=sys.stderr)
        return 1

    # Match Words<number>.json, explicitly excluding Words.json or non-numbered files
    candidates = [
        f for f in input_dir.glob("Words*.json")
        if re.search(r"Words\d+\.json$", f.name)
    ]

    if not candidates:
        print(f"Error: No numbered Words*.json files found in {input_dir}", file=sys.stderr)
        return 1

    # Sort numerically (1, 2, ..., 10)
    files = sorted(candidates, key=extract_word_number)

    default_output = REPO_ROOT / "N2 Level" / "Words.json"
    target_output = output_file or default_output

    print(f"Found {len(files)} vocabulary files in '{input_dir}':")
    print("-" * 60)

    merged_vocab = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)

        vocab = data.get("vocabulary_list", [])
        if not vocab:
            print(f"  [WARN] {f.name:15s}: 0 items found")
            continue

        first_term = vocab[0].get("term", "")
        last_term = vocab[-1].get("term", "")
        print(f"  ✓ {f.name:15s}: {len(vocab):4d} items ({first_term} → {last_term})")
        merged_vocab.extend(vocab)

    print("-" * 60)
    print(f"Total vocabulary items: {len(merged_vocab)}")

    if dry_run:
        print(f"[Dry Run] Skipped writing to {target_output}")
        return 0

    merged_data = {"vocabulary_list": merged_vocab}
    with open(target_output, "w", encoding="utf-8") as fp:
        json.dump(merged_data, fp, ensure_ascii=False, indent=2)
        fp.write("\n")

    print(f"Successfully written merged file to: {target_output}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Merge numbered Words*.json files in numerical order."
    )
    parser.add_argument(
        "-d",
        "--dir",
        dest="input_dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Directory containing Words*.json files (default: '{DEFAULT_INPUT_DIR}')",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_file",
        type=Path,
        default=None,
        help="Output JSON file path (default: <dir>/Words.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the merge without writing the output file",
    )

    args = parser.parse_args()
    sys.exit(merge_word_files(args.input_dir, args.output_file, args.dry_run))


if __name__ == "__main__":
    main()
