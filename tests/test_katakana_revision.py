from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parent.parent
REVISED_PATH = REPO_ROOT / "Deck_Full" / "Revised Notes.txt"
ORIGINAL_PATH = REPO_ROOT / "Deck_Full" / "Selected Notes.txt"
FULL_REVISED_PATH = REPO_ROOT / "Deck_Full" / "Selected Notes (Full Revised).txt"


def test_original_file_untouched():
    assert ORIGINAL_PATH.is_file()
    with open(ORIGINAL_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 6152
    # Check that original file still has the unmodified line for フクロウ as a canary
    canary = False
    for l in lines:
        if "Ep/lO$B.?4" in l and "\tふくろう\tふくろう\t" in l:
            canary = True
            break
    assert canary, "Original file was modified!"


def test_revised_file_structure():
    assert REVISED_PATH.is_file()
    with open(REVISED_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    assert len(lines) == 70  # 6 headers + 64 cards
    headers = [l for l in lines if l.startswith("#")]
    assert len(headers) == 6

    for idx, l in enumerate(lines[6:], 7):
        parts = l.strip("\r\n").split("\t")
        assert len(parts) == 19, f"Row {idx} has {len(parts)} columns"
        guid, word, reading, furigana = parts[0], parts[3], parts[4], parts[5]

        # Ensure furigana has katakana
        has_kata = any(0x30A1 <= ord(c) <= 0x30FA for c in furigana)
        assert has_kata, f"Word {word} ({guid}) has no katakana in Furigana: {furigana}"


def test_full_revised_file_integrity():
    assert FULL_REVISED_PATH.is_file()
    with open(FULL_REVISED_PATH, "r", encoding="utf-8") as f:
        full_lines = f.readlines()
    with open(ORIGINAL_PATH, "r", encoding="utf-8") as f:
        orig_lines = f.readlines()

    assert len(full_lines) == len(orig_lines) == 6152
