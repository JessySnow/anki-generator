#!/usr/bin/env python3
"""
Unit tests for Deck 2 (Minna no Nihongo / 大家的日语) components and validation logic.
"""

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DECK_2_DIR = REPO_ROOT / "Deck_2"
WORDS_PATH = DECK_2_DIR / "Words.json"
DECK_PATH = DECK_2_DIR / "deck.txt"
TEMPLATE_PATH = DECK_2_DIR / "template.txt"


class TestDeck2(unittest.TestCase):
    def test_words_json_integrity(self):
        self.assertTrue(WORDS_PATH.is_file(), "Deck_2/Words.json must exist")
        with open(WORDS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        vocab = data.get("vocabulary_list", [])
        self.assertEqual(len(vocab), 3975, "Must have exactly 3,975 vocabulary items")

        guids = set()
        for v in vocab:
            self.assertIn("guid", v)
            self.assertIn("word", v)
            self.assertIn("reading", v)
            self.assertIn("furigana", v)
            self.assertIn("pos", v)
            self.assertIn("meaning", v)
            self.assertTrue(len(v["guid"]) > 0)
            guids.add(v["guid"])
        self.assertEqual(len(guids), 3975, "All GUIDs in Words.json must be unique")

    def test_template_headers(self):
        self.assertTrue(TEMPLATE_PATH.is_file(), "Deck_2/template.txt must exist")
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        self.assertIn("#separator:tab", lines)
        self.assertIn("#guid column:1", lines)
        self.assertIn("#tags column:16", lines)

    def test_deck_txt_structure(self):
        self.assertTrue(DECK_PATH.is_file(), "Deck_2/deck.txt must exist")
        with open(DECK_PATH, "r", encoding="utf-8") as f:
            lines = [l.rstrip("\r\n") for l in f]

        header_lines = [l for l in lines if l.startswith("#")]
        data_lines = [l for l in lines if not l.startswith("#") and l.strip()]

        self.assertGreaterEqual(len(header_lines), 6, "Must contain standard Anki headers")
        self.assertEqual(len(data_lines), 3975, "Must contain exactly 3,975 card data lines")

        guids = set()
        for idx, line in enumerate(data_lines):
            fields = line.split("\t")
            self.assertEqual(len(fields), 16, f"Row {idx} must have 16 TSV fields")
            guid, word, reading, furigana, pos, meaning, w_aud, sentence, s_aud = fields[:9]
            self.assertNotIn(guid, guids, f"Duplicate GUID at row {idx}")
            guids.add(guid)
            self.assertEqual(w_aud, "", f"WordAudio must be empty at row {idx}")
            self.assertEqual(s_aud, "", f"SentenceAudio must be empty at row {idx}")
            self.assertNotIn("<br>", word, f"Word must not leak HTML at row {idx}")
            self.assertNotIn("<br>", reading, f"Reading must not leak HTML at row {idx}")
            self.assertNotIn("[]", furigana, f"Furigana must not have empty brackets at row {idx}")


if __name__ == "__main__":
    unittest.main()
