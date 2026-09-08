#!/usr/bin/env python3
"""
Inspect generation progress across all vocabulary words in Words.json.

Usage:
  python3 scripts/status.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import pipeline_lib as lib


def format_ranges(nums: list[int]) -> str:
    """Compress a list of integers into human-readable ranges like '0-49, 100-150'."""
    if not nums:
        return "None"
    nums = sorted(nums)
    ranges = []
    start = nums[0]
    end = nums[0]

    for n in nums[1:]:
        if n == end + 1:
            end = n
        else:
            ranges.append(f"{start}-{end}" if start != end else f"{start}")
            start = end = n
    ranges.append(f"{start}-{end}" if start != end else f"{start}")
    return ", ".join(ranges)


def show_status():
    words = lib.load_words()
    total_words = len(words)
    completed = lib.get_completed_indices()
    completed_count = len(completed)
    remaining_count = total_words - completed_count
    pct = (completed_count / total_words * 100) if total_words > 0 else 0

    uncompleted = [i for i in range(total_words) if i not in completed]

    print("=" * 60)
    print(" ANKI GENERATOR PIPELINE STATUS")
    print("=" * 60)
    print(f" Total Vocabulary : {total_words}")
    print(f" Completed Cards  : {completed_count} ({pct:.1f}%)")
    print(f" Remaining Cards  : {remaining_count}")
    print(f" Card Ledger Path : {lib.CARDS_DIR}")

    deck_file = lib.DEFAULT_DECK_PATH
    if deck_file.is_file():
        # Count data rows in deck file
        with open(deck_file, "r", encoding="utf-8") as f:
            deck_rows = sum(1 for line in f if not line.startswith("#") and line.strip())
        print(f" Deck File Output : {deck_file} ({deck_rows} cards written)")
    else:
        print(f" Deck File Output : {deck_file} (not compiled yet)")

    print("-" * 60)
    if uncompleted:
        print(f" Next 5 uncompleted word indices: {uncompleted[:5]}")
        sample_words = [words[i].get("term", "?") for i in uncompleted[:5]]
        print(f" Next words: {', '.join(sample_words)}")
    else:
        print(" 🎉 All vocabulary words have been generated!")
    print("=" * 60)


if __name__ == "__main__":
    show_status()
