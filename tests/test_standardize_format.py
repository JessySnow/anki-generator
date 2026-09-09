#!/usr/bin/env python3
"""
Unit tests for format standardization functions in pipeline_lib and standardize_format.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import pipeline_lib as lib
import standardize_format


class TestStandardizeFormat(unittest.TestCase):
    def test_generate_furigana_simple_kanji(self):
        self.assertEqual(lib.generate_furigana("赤道", "せきどう"), "赤道[せきどう]")

    def test_generate_furigana_pure_kana(self):
        self.assertEqual(lib.generate_furigana("せっせと", "せっせと"), "せっせと")
        self.assertEqual(lib.generate_furigana("セミナー", "セミナー"), "セミナー")

    def test_generate_furigana_okurigana_suffix(self):
        self.assertEqual(lib.generate_furigana("接する", "せっする"), "接[せっ]する")
        self.assertEqual(lib.generate_furigana("迫る", "せまる"), "迫[せま]る")
        self.assertEqual(lib.generate_furigana("攻める", "せめる"), "攻[せ]める")
        self.assertEqual(lib.generate_furigana("騒々しい", "そうぞうしい"), "騒々[そうぞう]しい")

    def test_generate_furigana_prefix_kana(self):
        self.assertEqual(lib.generate_furigana("お手本", "おてほん"), "お 手本[てほん]")

    def test_generate_furigana_prefix_suffix_tildes(self):
        self.assertEqual(lib.generate_furigana("～船", "～せん"), "～船[せん]")
        self.assertEqual(lib.generate_furigana("全～", "ぜん～"), "全[ぜん]～")

    def test_generate_furigana_compounds(self):
        self.assertEqual(lib.generate_furigana("抱き締める", "だきしめる"), "抱[だ]き締[し]める")
        self.assertEqual(lib.generate_furigana("立ち上がる", "たちあがる"), "立[た]ち上[あ]がる")
        self.assertEqual(lib.generate_furigana("使い分け", "つかいわけ"), "使[つか]い分[わ]け")

    def test_standardize_card_format_pos(self):
        card = {
            "Word": "テスト",
            "Reading": "テスト",
            "Furigana": "テスト",
            "POS": "[名·他動3]",
            "Tags": "N2::Vocabulary N2::Grammar::1",
            "Sentence": "テスト例文です。",
            "SentenceTranslation": "测试例句。",
            "WordUsage": "用法",
            "GrammarPattern": "～について",
            "GrammarMeaning": "关于",
            "GrammarUsage": "用法",
            "CombinationLogic": "逻辑",
        }
        std_card, changes = lib.standardize_card_format(card)
        self.assertEqual(std_card["POS"], "名・他動3")
        self.assertTrue(any("Removed outer brackets" in c for c in changes))
        self.assertTrue(any("Converted Latin middle dot" in c for c in changes))

    def test_standardize_card_format_quotes(self):
        card = {
            "Word": "使い分け",
            "Reading": "つかいわけ",
            "Furigana": "使い分け[つかいわけ]",
            "POS": "名",
            "Tags": "N2::Vocabulary N2::Grammar::1",
            "Sentence": "テスト例文です。",
            "SentenceTranslation": "测试例句。",
            "WordUsage": '"「使い分け」在句中表示""区分使用""。"',
            "GrammarPattern": "～について",
            "GrammarMeaning": "关于",
            "GrammarUsage": "用法",
            "CombinationLogic": "逻辑",
        }
        std_card, changes = lib.standardize_card_format(card)
        self.assertFalse(std_card["WordUsage"].startswith('"'))
        self.assertNotIn('""', std_card["WordUsage"])
        self.assertEqual(std_card["Furigana"], "使[つか]い分[わ]け")


if __name__ == "__main__":
    unittest.main()
