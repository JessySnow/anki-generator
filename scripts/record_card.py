#!/usr/bin/env python3
"""
Atomically record one or more generated cards to the progress ledger.
Thread-safe and process-safe across concurrent subagents.

Usage:
  python3 scripts/record_card.py --json '<card_or_cards_json>'
  python3 scripts/record_card.py --file <path_to_cards.json>
  cat cards.json | python3 scripts/record_card.py --stdin
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add scripts directory to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import pipeline_lib as lib


def record_single_card(card: dict, cards_dir: Path = lib.CARDS_DIR) -> tuple[bool, str]:
    """Validate and atomically persist a single card dict."""
    if not isinstance(card, dict):
        return False, "Payload must be a dictionary"

    word_idx = card.get("word_index")
    if word_idx is None or not isinstance(word_idx, int):
        return False, "Card is missing valid integer 'word_index'"

    # Normalize optional / default fields
    card.setdefault("WordAudio", "")
    card.setdefault("SentenceAudio", "")
    if not card.get("Tags"):
        grammar_id = card.get("grammar_id", "")
        card["Tags"] = f"N2::Vocabulary N2::Grammar::{grammar_id}".strip()

    # Validate against schema
    errors = lib.validate_card(card)
    if errors:
        return False, f"Validation errors for card #{word_idx}: " + "; ".join(errors)

    target_file = cards_dir / f"{word_idx:04d}.json"
    lib.atomic_write_json(target_file, card)
    return True, f"Card #{word_idx:04d} ('{card.get('Word')}') saved successfully"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record generated Anki cards to atomic progress ledger."
    )
    parser.add_argument("--json", type=str, default="", help="JSON string of a card or list of cards")
    parser.add_argument("--file", type=Path, default=None, help="Path to JSON file containing card(s)")
    parser.add_argument("--stdin", action="store_true", help="Read JSON payload from stdin")
    parser.add_argument("--dir", type=Path, default=lib.CARDS_DIR, help="Target cards progress directory")
    args = parser.parse_args()

    raw_payload = ""
    if args.stdin:
        raw_payload = sys.stdin.read()
    elif args.file:
        if not args.file.is_file():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            return 1
        with open(args.file, "r", encoding="utf-8") as f:
            raw_payload = f.read()
    elif args.json:
        raw_payload = args.json
    else:
        parser.print_help(sys.stderr)
        return 1

    try:
        data = json.loads(raw_payload)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON payload: {e}", file=sys.stderr)
        return 1

    # Support either a single card dict or a list of cards
    cards = data if isinstance(data, list) else [data]

    success_count = 0
    fail_count = 0
    for card in cards:
        ok, msg = record_single_card(card, cards_dir=args.dir)
        if ok:
            print(f"[record_card] ✓ {msg}")
            success_count += 1
        else:
            print(f"[record_card] ✗ {msg}", file=sys.stderr)
            fail_count += 1

    print(f"[record_card] Summary: {success_count} succeeded, {fail_count} failed.")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
