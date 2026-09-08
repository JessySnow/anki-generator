#!/usr/bin/env python3
"""
Randomly pick one (or more) grammar entries from Grammar.json for JLPT study.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

# Resolve default Grammar.json relative to repository root
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GRAMMAR_PATH = REPO_ROOT / "N2 Level" / "Grammar.json"


def load_grammar(file_path: Path) -> list[dict]:
    """Load grammar entries from JSON file."""
    if not file_path.is_file():
        raise FileNotFoundError(f"Grammar file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data.get("grammar_list", [])
    if not entries:
        raise ValueError(f"No grammar entries found in {file_path}")
    return entries


def format_entry(entry: dict) -> str:
    """Format a single grammar entry for terminal display."""
    entry_id = entry.get("id", "?")
    pattern = entry.get("pattern", "")
    meaning = entry.get("meaning", "")
    connection = entry.get("connection", "")
    examples = entry.get("example_sentences", [])

    lines = [
        "═" * 60,
        f" [{entry_id}] {pattern}",
        "═" * 60,
        f" Meaning    : {meaning}",
        f" Connection : {connection}",
    ]

    if examples:
        lines.append(" Examples   :")
        for idx, ex in enumerate(examples, 1):
            lines.append(f"   {idx}. {ex}")

    return "\n".join(lines)


def pick_random(
    file_path: Path,
    count: int = 1,
    as_json: bool = False,
    entry_id: int | None = None,
) -> None:
    try:
        entries = load_grammar(file_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if entry_id is not None:
        selected = [e for e in entries if e.get("id") == entry_id]
        if not selected:
            print(f"Error: Grammar entry with ID {entry_id} not found.", file=sys.stderr)
            sys.exit(1)
    else:
        sample_size = min(count, len(entries))
        selected = random.sample(entries, sample_size)

    if as_json:
        output_obj = selected if len(selected) > 1 else selected[0]
        print(json.dumps(output_obj, ensure_ascii=False, indent=2))
    else:
        for idx, entry in enumerate(selected):
            if idx > 0:
                print("\n")
            print(format_entry(entry))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Randomly pick grammar entry from JLPT Grammar.json."
    )
    parser.add_argument(
        "-f",
        "--file",
        dest="file_path",
        type=Path,
        default=DEFAULT_GRAMMAR_PATH,
        help=f"Path to Grammar.json (default: '{DEFAULT_GRAMMAR_PATH}')",
    )
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=1,
        help="Number of grammar entries to randomly pick (default: 1)",
    )
    parser.add_argument(
        "--id",
        dest="entry_id",
        type=int,
        default=None,
        help="Pick a specific entry by its ID instead of randomly",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Output raw JSON format instead of human-readable text",
    )

    args = parser.parse_args()
    pick_random(
        file_path=args.file_path,
        count=args.count,
        as_json=args.as_json,
        entry_id=args.entry_id,
    )


if __name__ == "__main__":
    main()
