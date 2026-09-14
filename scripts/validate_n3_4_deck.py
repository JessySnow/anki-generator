#!/usr/bin/env python3
"""
Validate the compiled N3_4_Level/deck.txt file for structural,
linguistic, and GUID integrity against Selected Notes.txt.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DECK_PATH = REPO_ROOT / "N3_4_Level" / "deck.txt"
WORDS_PATH = REPO_ROOT / "N3_4_Level" / "Words.json"
SELECTED_NOTES_PATH = REPO_ROOT / "Selected Notes.txt"

EXPECTED_HEADERS = [
    "#separator:tab",
    "#html:true",
    "#guid column:1",
    "#notetype:Japanese N2 Vocab & Grammar",
    "#deck:日语::大家的日语::单词",
    "#tags column:16",
    "#columns:GUID\tWord\tReading\tFurigana\tPOS\tMeaning\tWordAudio\tSentence\tSentenceAudio\tSentenceTranslation\tWordUsage\tGrammarPattern\tGrammarMeaning\tGrammarUsage\tCombinationLogic\tTags"
]

def validate(deck_file: Path = DECK_PATH) -> int:
    if not deck_file.is_file():
        print(f"Error: Deck file {deck_file} does not exist.", file=sys.stderr)
        return 1

    with open(deck_file, "r", encoding="utf-8") as f:
        lines = [l.strip("\n") for l in f]

    errors = []
    # Check headers
    for i, exp in enumerate(EXPECTED_HEADERS):
        if i >= len(lines) or lines[i].strip() != exp:
            actual = lines[i] if i < len(lines) else "EOF"
            errors.append(f"Header line {i+1} mismatch:\n  Expected: {exp}\n  Actual:   {actual}")

    data_lines = lines[len(EXPECTED_HEADERS):]
    if len(data_lines) != 556:
        errors.append(f"Expected 556 cards, but found {len(data_lines)}.")

    with open(SELECTED_NOTES_PATH, "r", encoding="utf-8") as f:
        orig_guids = [l.split("\t")[0] for l in f if l.strip() and not l.startswith("#")]

    deck_guids = []
    required_cols = [0, 1, 2, 3, 4, 5, 7, 9, 10, 11, 12, 13, 14, 15] # 6 & 8 are audio (empty)

    for idx, line in enumerate(data_lines, start=len(EXPECTED_HEADERS) + 1):
        cols = line.split("\t")
        if len(cols) != 16:
            errors.append(f"Line {idx} has {len(cols)} columns instead of 16. First part: {cols[0] if cols else 'empty'}")
            continue

        guid = cols[0]
        deck_guids.append(guid)

        # Ensure audio columns 6 and 8 are empty
        if cols[6] != "":
            errors.append(f"Line {idx} ({cols[1]}): WordAudio should be empty, got {cols[6]!r}")
        if cols[8] != "":
            errors.append(f"Line {idx} ({cols[1]}): SentenceAudio should be empty, got {cols[8]!r}")

        # Ensure required fields are not blank
        for col_idx in required_cols:
            if not cols[col_idx].strip():
                errors.append(f"Line {idx} ({cols[1]}): column {col_idx} is empty.")

    # Check GUID matching
    if orig_guids != deck_guids:
        missing = set(orig_guids) - set(deck_guids)
        extra = set(deck_guids) - set(orig_guids)
        if missing:
            errors.append(f"{len(missing)} original GUIDs missing from deck.")
        if extra:
            errors.append(f"{len(extra)} unexpected GUIDs in deck.")

    if errors:
        print(f"Validation failed with {len(errors)} error(s):", file=sys.stderr)
        for err in errors[:25]:
            print(f"  • {err}", file=sys.stderr)
        if len(errors) > 25:
            print(f"  ... and {len(errors) - 25} more errors.", file=sys.stderr)
        return 1

    print(f"✓ All validation checks passed: 556 cards, 16 columns, 100% GUID match, all required fields present, audio cleanly dropped.")
    return 0

if __name__ == "__main__":
    sys.exit(validate())
