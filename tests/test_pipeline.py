#!/usr/bin/env python3
"""
Unit and integration tests for the multi-agent Anki card pipeline.
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Add scripts directory to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import pipeline_lib as lib
from get_batch import fetch_batch
from record_card import record_single_card
from build_deck import compile_deck


class TestPipelineLib(unittest.TestCase):
    def test_parse_term_standard(self):
        w, r, f = lib.parse_term("赤道(せきどう)⓪")
        self.assertEqual(w, "赤道")
        self.assertEqual(r, "せきどう")
        self.assertEqual(f, "赤道[せきどう]")

    def test_parse_term_fullwidth_parens(self):
        w, r, f = lib.parse_term("手本（てほん）②")
        self.assertEqual(w, "手本")
        self.assertEqual(r, "てほん")
        self.assertEqual(f, "手本[てほん]")

    def test_parse_term_pure_kana(self):
        w, r, f = lib.parse_term("せっせと①")
        self.assertEqual(w, "せっせと")
        self.assertEqual(r, "せっせと")
        self.assertEqual(f, "せっせと")

    def test_parse_term_abbreviation_loanword(self):
        w, r, f = lib.parse_term("ゼミ(「ゼミナール(seminar)の略語」)①")
        self.assertEqual(w, "ゼミ")
        self.assertEqual(r, "ゼミ")
        self.assertEqual(f, "ゼミ")

    def test_parse_term_prefix(self):
        w, r, f = lib.parse_term("〜夜（〜や）")
        self.assertEqual(w, "〜夜")
        self.assertEqual(r, "〜や")
        self.assertEqual(f, "〜夜[〜や]")

    def test_read_template_headers(self):
        headers = lib.read_template_headers()
        self.assertEqual(len(headers), 6)
        self.assertTrue(headers[0].startswith("#separator:tab"))
        self.assertTrue(headers[1].startswith("#html:true"))
        self.assertTrue(headers[2].startswith("#notetype:Japanese N2 Vocab & Grammar"))
        self.assertTrue(headers[3].startswith("#deck:Japanese::JLPT N2"))
        self.assertTrue(headers[4].startswith("#tags column:15"))
        self.assertTrue(headers[5].startswith("#columns:"))
        cols = headers[5][len("#columns:"):].split("\t")
        self.assertEqual(len(cols), 15)
        self.assertEqual(cols, lib.CARD_COLUMNS)

    def test_escape_anki_field(self):
        self.assertEqual(lib.escape_anki_field("hello\nworld"), "hello<br>world")
        self.assertEqual(lib.escape_anki_field("hello\tworld"), "hello world")
        self.assertEqual(lib.escape_anki_field(None), "")


class TestGetBatch(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cards_dir = self.temp_dir / "cards"
        self.cards_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_fetch_batch_uncompleted(self):
        batch = fetch_batch(size=3, cards_dir=self.cards_dir)
        self.assertEqual(batch["batch_size"], 3)
        self.assertEqual(len(batch["batch"]), 3)
        self.assertEqual(batch["batch"][0]["word_index"], 0)
        self.assertEqual(batch["batch"][1]["word_index"], 1)
        self.assertEqual(batch["batch"][2]["word_index"], 2)

    def test_fetch_batch_skips_completed(self):
        # Simulate index 0 already completed
        (self.cards_dir / "0000.json").write_text("{}", encoding="utf-8")
        batch = fetch_batch(size=2, cards_dir=self.cards_dir)
        self.assertEqual(batch["completed_count"], 1)
        # Should now start from index 1
        self.assertEqual(batch["batch"][0]["word_index"], 1)
        self.assertEqual(batch["batch"][1]["word_index"], 2)


class TestAtomicRecordingAndDeckBuild(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cards_dir = self.temp_dir / "cards"
        self.cards_dir.mkdir(parents=True, exist_ok=True)
        self.deck_output = self.temp_dir / "deck.txt"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _sample_card(self, idx: int, word: str = "真剣") -> dict:
        return {
            "word_index": idx,
            "Word": word,
            "Reading": "しんけん",
            "Furigana": f"{word}[しんけん]",
            "POS": "名・ナ形",
            "Meaning": "做事认真",
            "WordAudio": "",
            "Sentence": f"{word}に取り組む。",
            "SentenceAudio": "",
            "SentenceTranslation": "认真投入工作。",
            "WordUsage": "副词性用法",
            "GrammarPattern": "～（ら）れる",
            "GrammarMeaning": "受害被动",
            "GrammarUsage": "接续用法说明",
            "CombinationLogic": "前后语境逻辑",
            "Tags": "N2::Vocab N2::Grammar::1",
        }

    def test_record_single_card_success(self):
        card = self._sample_card(0)
        ok, msg = record_single_card(card, cards_dir=self.cards_dir)
        self.assertTrue(ok)
        self.assertTrue((self.cards_dir / "0000.json").is_file())

        with open(self.cards_dir / "0000.json", "r", encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved["Word"], "真剣")

    def test_record_single_card_validation_failure(self):
        # Missing Meaning
        card = self._sample_card(1)
        del card["Meaning"]
        ok, msg = record_single_card(card, cards_dir=self.cards_dir)
        self.assertFalse(ok)
        self.assertIn("Meaning", msg)

    def test_concurrent_recording(self):
        """Verify that concurrent threads writing cards do not race or corrupt data."""
        def worker(idx: int):
            c = self._sample_card(idx, word=f"Word{idx}")
            return record_single_card(c, cards_dir=self.cards_dir)

        indices = list(range(20))
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(worker, indices))

        for ok, msg in results:
            self.assertTrue(ok)

        completed = lib.get_completed_indices(cards_dir=self.cards_dir)
        self.assertEqual(completed, set(range(20)))

    def test_build_deck_structure(self):
        # Record two cards
        record_single_card(self._sample_card(0, "赤道"), cards_dir=self.cards_dir)
        record_single_card(self._sample_card(1, "世帯"), cards_dir=self.cards_dir)

        code = compile_deck(
            output_path=self.deck_output,
            cards_dir=self.cards_dir,
            template_path=lib.TEMPLATE_PATH,
        )
        self.assertEqual(code, 0)
        self.assertTrue(self.deck_output.is_file())

        with open(self.deck_output, "r", encoding="utf-8") as f:
            lines = [l.rstrip("\r\n") for l in f]

        # First 6 lines must be headers
        self.assertEqual(len(lines), 8)
        self.assertTrue(lines[0].startswith("#separator:tab"))
        self.assertTrue(lines[1].startswith("#html:true"))
        self.assertTrue(lines[4].startswith("#tags column:15"))

        # Next 2 lines must be data rows
        row1 = lines[6].split("\t")
        row2 = lines[7].split("\t")
        self.assertEqual(len(row1), 15)
        self.assertEqual(len(row2), 15)
        self.assertEqual(row1[0], "赤道")
        self.assertEqual(row2[0], "世帯")


if __name__ == "__main__":
    unittest.main()
