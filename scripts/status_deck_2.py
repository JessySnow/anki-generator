#!/usr/bin/env python3
"""
Report current generation status for Deck_2.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORDS_PATH = REPO_ROOT / "Deck_2" / "Words.json"
CARDS_DIR = REPO_ROOT / "Deck_2" / "progress" / "cards"
DECK_PATH = REPO_ROOT / "Deck_2" / "deck.txt"

def main():
    if not WORDS_PATH.exists():
        print("Deck_2/Words.json not found.", file=sys.stderr)
        return 1

    with open(WORDS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        words = data["vocabulary_list"]
        grammar_pool = data.get("grammar_pool_size", 407)

    total_words = len(words)
    card_files = sorted(CARDS_DIR.glob("*.json")) if CARDS_DIR.is_dir() else []
    done_count = len(card_files)
    pct = (done_count / total_words * 100) if total_words > 0 else 0.0

    print("==================================================================")
    print("  DECK_2 GENERATION STATUS")
    print("==================================================================")
    print(f"Total Notes to Migrate: {total_words}")
    print(f"Combined Grammar Pool:  {grammar_pool} points (N2 + N3/N4)")
    print(f"Generated Cards:        {done_count} / {total_words} ({pct:.1f}%)")
    print(f"Remaining Cards:        {total_words - done_count}")

    if done_count > 0:
        latest = card_files[-5:]
        print("\nRecent Generated Cards:")
        for cf in latest:
            try:
                with open(cf, "r", encoding="utf-8") as f:
                    c = json.load(f)
                print(f"  #{c.get('word_index', 0):04d} [{c.get('Word')}] ({c.get('Reading')}) - Grammar: {c.get('GrammarPattern')}")
            except Exception:
                pass

    if DECK_PATH.exists():
        with open(DECK_PATH, "r", encoding="utf-8") as f:
            deck_lines = [l for l in f if not l.startswith("#") and l.strip()]
        print(f"\nCompiled deck.txt:      {len(deck_lines)} cards")
    else:
        print("\nCompiled deck.txt:      Not yet compiled")
    print("==================================================================")
    return 0

if __name__ == "__main__":
    sys.exit(main())
