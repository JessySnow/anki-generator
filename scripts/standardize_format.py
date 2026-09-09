#!/usr/bin/env python3
"""
scripts/standardize_format.py - Standalone tool to standardize card formats across N2 deck.

Eliminates format inconsistencies:
1. Strips outer square brackets from POS and converts Latin middle dots '·' to Japanese '・'.
2. Separates okurigana in Furigana for clean Anki ruby formatting.
3. Normalizes all tildes to standard fullwidth '～' (U+FF5E).
4. Removes duplicate tildes inside Furigana brackets (e.g. '～船[～せん]' -> '～船[せん]').
5. Cleans loanword reading contamination (e.g. 'トレイ（tray）＝トレー' -> 'トレイ').
6. Cleans CSV double-quote escaping artifacts.

Usage:
  python3 scripts/standardize_format.py --dry-run
  python3 scripts/standardize_format.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add scripts directory to path
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import pipeline_lib as lib
import build_deck


def run_standardization(
    deck_path: Path = lib.DEFAULT_DECK_PATH,
    cards_dir: Path = lib.CARDS_DIR,
    dry_run: bool = False,
) -> int:
    print("=" * 68)
    print("  N2 ANKI DECK FORMAT STANDARDIZATION TOOL")
    print("=" * 68)
    print(f"  Deck Path : {deck_path}")
    print(f"  Cards Dir : {cards_dir}")
    print(f"  Dry Run   : {dry_run}")
    print("=" * 68)

    headers, cards = lib.parse_deck_rows(deck_path)
    total_cards = len(cards)
    print(f"Loaded {total_cards} cards from {deck_path.name}.")

    cards_changed = 0
    all_changes = []

    for card in cards:
        w_idx = card["word_index"]
        updated_card, changes = lib.standardize_card_format(card)
        if changes:
            cards_changed += 1
            all_changes.append((w_idx, card.get("Word"), changes))
            if not dry_run:
                card_file = cards_dir / f"{w_idx:04d}.json"
                lib.atomic_write_json(card_file, updated_card)

    print(f"\nStandardization scan complete: {cards_changed} / {total_cards} cards standardized.")
    if all_changes:
        print("\nSample changes applied:")
        for w_idx, word, ch_list in all_changes[:15]:
            print(f"  Card #{w_idx:04d} ('{word}'): {'; '.join(ch_list)}")
        if len(all_changes) > 15:
            print(f"  ... and {len(all_changes) - 15} more cards.")

    if not dry_run and cards_changed > 0:
        print("\nRecompiling master deck.txt...")
        build_deck.compile_deck(output_path=deck_path, cards_dir=cards_dir)
        print("✓ Recompilation complete.")
    elif dry_run:
        print("\n[Dry Run] No files modified.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Standardize card format across N2 Anki deck.")
    parser.add_argument("--deck", type=Path, default=lib.DEFAULT_DECK_PATH, help="Path to deck.txt")
    parser.add_argument("--cards-dir", type=Path, default=lib.CARDS_DIR, help="Path to cards directory")
    parser.add_argument("--dry-run", action="store_true", help="Audit without saving changes")
    args = parser.parse_args()

    return run_standardization(deck_path=args.deck, cards_dir=args.cards_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
