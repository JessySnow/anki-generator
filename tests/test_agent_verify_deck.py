#!/usr/bin/env python3
"""
Unit tests for agent-level offline verification in scripts/agent_verify_deck.py.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import agent_verify_deck as agent_v


class TestAgentVerifyDeck(unittest.TestCase):
    def test_clean_card_passes(self):
        card = {
            "word_index": 1,
            "Word": "接する",
            "Reading": "せっする",
            "Furigana": "接[せっ]する",
            "POS": "他動1",
            "Meaning": "接触，接待",
            "WordAudio": "[sound:n2_card_0001.mp3]",
            "Sentence": "彼は誰に対しても温かい態度で接する。",
            "SentenceAudio": "[sound:n2_card_0001.mp3]",
            "SentenceTranslation": "他对任何人都是以温和的态度相待。",
            "WordUsage": "表示人际交往态度",
            "GrammarPattern": "～に対して",
            "GrammarMeaning": "对……，对于……",
            "GrammarUsage": "接对象名词",
            "CombinationLogic": "逻辑自然顺畅",
            "Tags": "N2::Vocabulary N2::Grammar::1",
        }
        issues = agent_v.check_card_agent(card, 1)
        self.assertEqual(issues, [])

    def test_simplified_chinese_detection(self):
        card = {
            "word_index": 1,
            "Word": "発言",
            "Reading": "はつげん",
            "Furigana": "発言[はつげん]",
            "POS": "名",
            "Meaning": "发言",
            "WordAudio": "",
            "Sentence": "会议上他积极发言。",  # contains Simplified Chinese '议' and '发' (wait, '发' is in check)
            "SentenceAudio": "",
            "SentenceTranslation": "在会议上他积极发言。",
            "WordUsage": "用法",
            "GrammarPattern": "～について",
            "GrammarMeaning": "关于",
            "GrammarUsage": "用法",
            "CombinationLogic": "逻辑",
            "Tags": "N2::Vocabulary N2::Grammar::1",
        }
        # In sentence, let's put Simplified '发' or '关'
        card["Sentence"] = "会議において重要な発言をした。"  # clean
        card["Sentence"] = "会議において重要な关言をした。"  # simplified 关
        issues = agent_v.check_card_agent(card, 1)
        self.assertTrue(any("Simplified Chinese" in issue for issue in issues))

    def test_missing_word_in_sentence(self):
        card = {
            "word_index": 1,
            "Word": "赤道",
            "Reading": "せきどう",
            "Furigana": "赤道[せきどう]",
            "POS": "名",
            "Meaning": "赤道",
            "WordAudio": "",
            "Sentence": "この島は一年中とても暑い。",  # missing 赤道
            "SentenceAudio": "",
            "SentenceTranslation": "这个岛屿一整年都非常炎热。",
            "WordUsage": "用法",
            "GrammarPattern": "～について",
            "GrammarMeaning": "关于",
            "GrammarUsage": "用法",
            "CombinationLogic": "逻辑",
            "Tags": "N2::Vocabulary N2::Grammar::1",
        }
        issues = agent_v.check_card_agent(card, 1)
        self.assertTrue(any("Target word '赤道'" in issue for issue in issues))

    def test_hiragana_verb_inflection_matches(self):
        card = {
            "word_index": 1,
            "Word": "ためらう",
            "Reading": "ためらう",
            "Furigana": "ためらう",
            "POS": "自他動1",
            "Meaning": "犹豫，踌躇",
            "WordAudio": "",
            "Sentence": "自らが正しいと信じる道を歩むことを決してためらってはならない。",
            "SentenceAudio": "",
            "SentenceTranslation": "决不能对自己坚信正确的道路产生犹豫。",
            "WordUsage": "用法",
            "GrammarPattern": "～てはならない",
            "GrammarMeaning": "不能……，不可……",
            "GrammarUsage": "接动词て形",
            "CombinationLogic": "逻辑结合",
            "Tags": "N2::Vocabulary N2::Grammar::1",
        }
        issues = agent_v.check_card_agent(card, 1)
        self.assertEqual(issues, [])

    def test_verify_entire_deck_clean(self):
        results = agent_v.verify_deck()
        self.assertEqual(results["summary"], "PASSED")
        self.assertEqual(results["flagged_cards"], 0)
        self.assertEqual(results["total_cards"], 1615)
        self.assertEqual(results["json_mismatches"], 0)


if __name__ == "__main__":
    unittest.main()
