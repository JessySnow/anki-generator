#!/usr/bin/env python3
"""
Unit tests for JLPT N3/N4 deck components and validation logic.
"""

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORDS_PATH = REPO_ROOT / "N3_4_Level" / "Words.json"
TEMPLATE_PATH = REPO_ROOT / "N3_4_Level" / "template.txt"
SELECTED_NOTES_PATH = REPO_ROOT / "Selected Notes.txt"

class TestN34Deck(unittest.TestCase):
    def test_words_json_integrity(self):
        self.assertTrue(WORDS_PATH.is_file(), "Words.json must exist")
        with open(WORDS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        vocab = data.get("vocabulary_list", [])
        self.assertEqual(len(vocab), 556, "Must have exactly 556 vocabulary items")

        guids = set()
        for v in vocab:
            self.assertIn("guid", v)
            self.assertIn("word", v)
            self.assertIn("reading", v)
            self.assertIn("furigana", v)
            self.assertIn("meaning", v)
            self.assertIn("grammar_id", v)
            self.assertIn("grammar_pattern", v)
            self.assertIn("grammar_meaning", v)
            self.assertTrue(len(v["guid"]) > 0)
            guids.add(v["guid"])
        self.assertEqual(len(guids), 556, "All GUIDs must be distinct")

    def test_template_headers(self):
        self.assertTrue(TEMPLATE_PATH.is_file(), "template.txt must exist")
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        self.assertIn("#separator:tab", lines)
        self.assertIn("#guid column:1", lines)
        self.assertIn("#tags column:16", lines)

if __name__ == "__main__":
    unittest.main()
