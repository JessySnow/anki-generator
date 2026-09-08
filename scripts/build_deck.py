#!/usr/bin/env python3
"""
Compile all recorded cards from progress/cards/*.json into the final Anki deck file.
Strictly adheres to N2 Level/template.txt headers and column structure.

Usage:
  python3 scripts/build_deck.py
  python3 scripts/build_deck.py --output "N2 Level/deck.txt"
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# Add scripts directory to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import pipeline_lib as lib


def compile_deck(
    output_path: Path = lib.DEFAULT_DECK_PATH,
    cards_dir: Path = lib.CARDS_DIR,
    template_path: Path = lib.TEMPLATE_PATH,
    words_path: Path = lib.WORDS_PATH,
) -> int:
    headers = lib.read_template_headers(template_path)
    if not headers:
        print(f"Error: No valid headers found in {template_path}", file=sys.stderr)
        return 1

    card_files = sorted(cards_dir.glob("*.json")) if cards_dir.is_dir() else []
    if not card_files:
        print(f"[build_deck] No card files found in {cards_dir}. Deck file not modified.")
        return 0

    cards = []
    for cf in card_files:
        try:
            with open(cf, "r", encoding="utf-8") as f:
                card_data = json.load(f)
            cards.append(card_data)
        except Exception as e:
            print(f"[build_deck] Warning: could not load {cf.name}: {e}", file=sys.stderr)

    # Sort cards by word_index
    cards.sort(key=lambda x: x.get("word_index", 0))

    # Total words in vocab file
    total_vocab = 0
    if words_path.is_file():
        try:
            total_vocab = len(lib.load_words(words_path))
        except Exception:
            pass

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        # Write exact Anki headers
        for h in headers:
            f.write(h + "\n")

        # Write data rows
        writer = csv.writer(
            f,
            delimiter="\t",
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\n",
        )
        for c in cards:
            row = lib.card_to_row(c)
            writer.writerow(row)

    pct = (len(cards) / total_vocab * 100) if total_vocab > 0 else 0
    print("-" * 60)
    print(f"Deck compilation complete:")
    print(f"  Destination : {output_path}")
    print(f"  Cards written: {len(cards)} / {total_vocab} ({pct:.1f}%)")
    print(f"  Columns     : {len(lib.CARD_COLUMNS)} fields per card")
    print("-" * 60)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile individual cards into the master Anki TSV deck file."
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_path",
        type=Path,
        default=lib.DEFAULT_DECK_PATH,
        help=f"Output Anki deck file path (default: '{lib.DEFAULT_DECK_PATH}')",
    )
    parser.add_argument(
        "--cards-dir",
        dest="cards_dir",
        type=Path,
        default=lib.CARDS_DIR,
        help=f"Directory containing card JSON files (default: '{lib.CARDS_DIR}')",
    )
    args = parser.parse_args()

    return compile_deck(
        output_path=args.output_path,
        cards_dir=args.cards_dir,
    )


if __name__ == "__main__":
    sys.exit(main())
