#!/usr/bin/env python3
"""
Unit and integration tests for scripts/verify_deck.py.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import pipeline_lib as lib
import verify_deck
from verify_deck import RateLimiter, GeminiClient, verify_and_revise_batch


class TestRateLimiter(unittest.TestCase):
    def test_minimum_delay_enforcement(self):
        # Target 60 RPM -> 1 second minimum delay
        limiter = RateLimiter(target_rpm=60.0, min_delay_sec=0.05)
        t0 = time.time()
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        elapsed = time.time() - t0
        self.assertGreaterEqual(elapsed, 0.04)

    def test_window_tracking(self):
        limiter = RateLimiter(target_rpm=2.0, min_delay_sec=0.0)
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        self.assertEqual(len(limiter.request_timestamps), 2)


class TestKeyResolution(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_gemini_api_key_from_zshrc(self):
        zshrc = self.temp_dir / ".zshrc"
        zshrc.write_text(
            'export PATH="/bin:$PATH"\n'
            'GEMINI_KEY="TEST_SECRET_KEY_12345"\n'
            'alias ll="ls -l"\n',
            encoding="utf-8",
        )
        with patch.dict("os.environ", {}, clear=True):
            key = lib.load_gemini_api_key(zshrc_path=zshrc)
            self.assertEqual(key, "TEST_SECRET_KEY_12345")

    def test_load_gemini_api_key_from_env(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "ENV_KEY_XYZ"}):
            key = lib.load_gemini_api_key(zshrc_path=self.temp_dir / "nonexistent")
            self.assertEqual(key, "ENV_KEY_XYZ")


class TestDeterministicLinting(unittest.TestCase):
    def test_valid_card(self):
        card = {
            "word_index": 0,
            "Word": "赤道",
            "Reading": "せきどう",
            "Furigana": "赤道[せきどう]",
            "POS": "名",
            "Meaning": "赤道",
            "WordAudio": "",
            "Sentence": "赤道直下の国々は過ごしやすい代わりに紫外線が強い。",
            "SentenceAudio": "",
            "SentenceTranslation": "赤道正下方的国家虽然宜居但紫外线强烈。",
            "WordUsage": "修饰国々",
            "GrammarPattern": "～代わりに",
            "GrammarMeaning": "虽然……但是……",
            "GrammarUsage": "接在過ごしやすい后面",
            "CombinationLogic": "转折关系",
            "Tags": "N2::Vocabulary N2::Grammar::38",
        }
        issues = lib.lint_card(card)
        self.assertEqual(issues, [])

    def test_mismatched_brackets(self):
        card = {
            "word_index": 1,
            "Word": "赤道",
            "Reading": "せきどう",
            "Furigana": "赤道[せきどう",
            "POS": "名",
            "Meaning": "赤道",
            "Sentence": "テスト文です。",
            "SentenceTranslation": "测试句子。",
            "WordUsage": "用法",
            "GrammarPattern": "～について",
            "GrammarMeaning": "关于",
            "GrammarUsage": "用法",
            "CombinationLogic": "逻辑",
            "Tags": "N2::Vocabulary N2::Grammar::1",
        }
        issues = lib.lint_card(card)
        self.assertTrue(any("Mismatched furigana brackets" in i for i in issues))

    def test_non_standard_tags(self):
        card = {
            "word_index": 2,
            "Word": "赤道",
            "Reading": "せきどう",
            "Furigana": "赤道[せきどう]",
            "POS": "名",
            "Meaning": "赤道",
            "Sentence": "テスト文です。",
            "SentenceTranslation": "测试句子。",
            "WordUsage": "用法",
            "GrammarPattern": "～について",
            "GrammarMeaning": "关于",
            "GrammarUsage": "用法",
            "CombinationLogic": "逻辑",
            "Tags": "InvalidTagFormat",
        }
        issues = lib.lint_card(card)
        self.assertTrue(any("Non-standard tag format" in i for i in issues))


class TestDeckParsing(unittest.TestCase):
    def test_parse_deck_rows_from_existing_deck(self):
        headers, cards = lib.parse_deck_rows()
        self.assertGreaterEqual(len(headers), 6)
        self.assertGreaterEqual(len(cards), 1000)
        self.assertEqual(cards[0]["Word"], "赤道")
        self.assertEqual(cards[0]["word_index"], 0)


class TestVerificationBatchWithMockClient(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cards_dir = self.temp_dir / "cards"
        self.cards_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_verify_and_revise_batch(self):
        client = MagicMock()
        client.call_model_json.return_value = {
            "results": [
                {
                    "word_index": 10,
                    "status": "PASS",
                    "issues": [],
                    "revised_card": None,
                },
                {
                    "word_index": 11,
                    "status": "REVISE",
                    "issues": ["Unnatural particle usage in sentence"],
                    "revised_card": {
                        "Word": "世帯",
                        "Reading": "せたい",
                        "Furigana": "世帯[せたい]",
                        "POS": "名",
                        "Meaning": "家，户，家庭",
                        "WordAudio": "",
                        "Sentence": "子育て世帯にとって住みやすい環境を整えるに限る。",
                        "SentenceAudio": "",
                        "SentenceTranslation": "最好是为育儿家庭营造宜居的环境。",
                        "WordUsage": "在句中作修饰成分",
                        "GrammarPattern": "～に限る",
                        "GrammarMeaning": "最好是……",
                        "GrammarUsage": "接在动词辞书形整える后",
                        "CombinationLogic": "最佳选择",
                        "Tags": "N2::Vocabulary N2::Grammar::111",
                    },
                },
            ]
        }

        batch = [
            {"word_index": 10, "Word": "赤道", "Tags": "N2::Vocabulary N2::Grammar::38"},
            {"word_index": 11, "Word": "世帯", "Tags": "N2::Vocabulary N2::Grammar::111"},
        ]

        passed, revised, rev_list = verify_and_revise_batch(
            client, batch, dry_run=False, cards_dir=self.cards_dir
        )
        self.assertEqual(passed, 1)
        self.assertEqual(revised, 1)
        self.assertEqual(len(rev_list), 1)
        self.assertEqual(rev_list[0]["word_index"], 11)

        # Check saved file
        saved_file = self.cards_dir / "0011.json"
        self.assertTrue(saved_file.is_file())
        with open(saved_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data["Sentence"], "子育て世帯にとって住みやすい環境を整えるに限る。")

    @patch("verify_deck.build_deck.compile_deck")
    @patch("verify_deck.GeminiClient")
    def test_run_verification_pipeline_multi_pass(self, mock_client_cls, mock_compile):
        # Pass 1: returns REVISE for card #0
        # Pass 2: returns PASS for revised card #0 -> loop convergence!
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        mock_client.call_model_json.side_effect = [
            # Pass 1 response
            {
                "results": [
                    {
                        "word_index": 0,
                        "status": "REVISE",
                        "issues": ["Fixed unnatural collocation"],
                        "revised_card": {
                            "Word": "赤道",
                            "Reading": "せきどう",
                            "Furigana": "赤道[せきどう]",
                            "POS": "名",
                            "Meaning": "赤道",
                            "WordAudio": "",
                            "Sentence": "赤道直下では日差しが極めて強い。",
                            "SentenceAudio": "",
                            "SentenceTranslation": "赤道正下方日照极其强烈。",
                            "WordUsage": "修饰日差し",
                            "GrammarPattern": "～極めて",
                            "GrammarMeaning": "极其",
                            "GrammarUsage": "修饰強い",
                            "CombinationLogic": "程度强化",
                            "Tags": "N2::Vocabulary N2::Grammar::38",
                        },
                    }
                ]
            },
            # Pass 2 response (clean pass)
            {
                "results": [
                    {
                        "word_index": 0,
                        "status": "PASS",
                        "issues": [],
                        "revised_card": None,
                    }
                ]
            },
        ]

        code = verify_deck.run_verification_pipeline(
            limit=1,
            api_key="mock_key",
            rpm=100.0,
            max_passes=3,
            force=True,
            cards_dir=self.cards_dir,
            cache_file=self.temp_dir / ".verify_cache.json",
            report_file=self.temp_dir / "report.json",
        )
        self.assertEqual(code, 0)
        self.assertEqual(mock_client.call_model_json.call_count, 2)
        mock_compile.assert_called_once()


if __name__ == "__main__":
    unittest.main()

