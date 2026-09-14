#!/usr/bin/env python3
"""
Compile all recorded cards from Deck_2/progress/cards/*.json
into the final Anki deck file Deck_2/deck.txt.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CARDS_DIR = REPO_ROOT / "Deck_2" / "progress" / "cards"
DEFAULT_TEMPLATE_PATH = REPO_ROOT / "Deck_2" / "template.txt"
DEFAULT_DECK_PATH = REPO_ROOT / "Deck_2" / "deck.txt"
DEFAULT_WORDS_PATH = REPO_ROOT / "Deck_2" / "Words.json"

COLUMNS = [
    "guid",
    "Word",
    "Reading",
    "Furigana",
    "POS",
    "Meaning",
    "WordAudio",
    "Sentence",
    "SentenceAudio",
    "SentenceTranslation",
    "WordUsage",
    "GrammarPattern",
    "GrammarMeaning",
    "GrammarUsage",
    "CombinationLogic",
    "Tags",
]

def read_headers(template_path: Path) -> list[str]:
    headers = []
    if template_path.is_file():
        with open(template_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\r\n")
                if line.startswith("#"):
                    headers.append(line)
    return headers

def compile_deck(
    cards_dir: Path = DEFAULT_CARDS_DIR,
    template_path: Path = DEFAULT_TEMPLATE_PATH,
    output_path: Path = DEFAULT_DECK_PATH,
    words_path: Path = DEFAULT_WORDS_PATH,
) -> int:
    headers = read_headers(template_path)
    if not headers:
        print(f"Error: No valid headers in {template_path}", file=sys.stderr)
        return 1

    card_files = sorted(cards_dir.glob("*.json")) if cards_dir.is_dir() else []
    if not card_files:
        print(f"[build_deck_2] No card files found in {cards_dir}.")
        return 0

    cards = []
    for cf in card_files:
        try:
            with open(cf, "r", encoding="utf-8") as f:
                cards.append(json.load(f))
        except Exception as e:
            print(f"[build_deck_2] Warning: could not load {cf.name}: {e}", file=sys.stderr)

    cards.sort(key=lambda c: c.get("word_index", 0))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        for h in headers:
            f.write(h + "\n")
        for card in cards:
            row = [str(card.get(col, "")) for col in COLUMNS]
            # Clean fields
            clean_row = [c.replace("\t", " ").replace("\r\n", " ").replace("\r", " ").replace("\n", "<br>") if idx != 0 else c for idx, c in enumerate(row)]
            f.write("\t".join(clean_row) + "\n")

    print(f"Successfully compiled {len(cards)} cards to {output_path}")
    return 0

if __name__ == "__main__":
    sys.exit(compile_deck())
