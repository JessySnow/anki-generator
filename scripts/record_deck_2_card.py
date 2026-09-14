#!/usr/bin/env python3
"""
Record one or more generated cards to Deck_2/progress/cards/{idx:04d}.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import pipeline_lib as lib

CARDS_DIR = REPO_ROOT / "Deck_2" / "progress" / "cards"

REQUIRED_FIELDS = [
    "guid",
    "Word",
    "Reading",
    "Furigana",
    "POS",
    "Meaning",
    "Sentence",
    "SentenceTranslation",
    "WordUsage",
    "GrammarPattern",
    "GrammarMeaning",
    "GrammarUsage",
    "CombinationLogic",
    "Tags",
]

def record_card(card: dict) -> tuple[bool, str]:
    if not isinstance(card, dict):
        return False, "Payload must be a dict"
    idx = card.get("word_index")
    if idx is None or not isinstance(idx, int):
        return False, "Card missing integer 'word_index'"

    # Enforce Audio Drop Policy
    card["WordAudio"] = ""
    card["SentenceAudio"] = ""

    # Ensure required fields
    for r in REQUIRED_FIELDS:
        val = str(card.get(r, "")).strip()
        if not val:
            return False, f"Card #{idx:04d} missing required field '{r}'"

    target_file = CARDS_DIR / f"{idx:04d}.json"
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    lib.atomic_write_json(target_file, card)
    return True, f"Card #{idx:04d} ({card.get('Word')}) saved."

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=str, default="")
    parser.add_argument("--file", type=Path, default=None)
    parser.add_argument("--stdin", action="store_true")
    args = parser.parse_args()

    payload = None
    if args.stdin:
        payload = json.loads(sys.stdin.read())
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            payload = json.load(f)
    elif args.json:
        payload = json.loads(args.json)

    if not payload:
        print("Error: No card payload provided.", file=sys.stderr)
        return 1

    cards = payload if isinstance(payload, list) else [payload]
    for c in cards:
        ok, msg = record_card(c)
        if not ok:
            print(f"Error: {msg}", file=sys.stderr)
            return 1
        print(msg)
    return 0

if __name__ == "__main__":
    sys.exit(main())
