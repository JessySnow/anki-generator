#!/usr/bin/env python3
"""
Agent-level offline verification for the Anki JLPT N3/N4 Deck.
Performs deterministic, syntactic, typographic, and linguistic integrity checks
across all 556 cards in N3_4_Level/deck.txt and N3_4_Level/progress/cards/*.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / 'scripts'))

from pipeline_lib import generate_furigana

DEFAULT_DECK_PATH = REPO_ROOT / 'N3_4_Level' / 'deck.txt'
DEFAULT_CARDS_DIR = REPO_ROOT / 'N3_4_Level' / 'progress' / 'cards'

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

SIMPLIFIED_CHINESE_CHECK = {
    '发': '発', '关': '関', '气': '気', '开': '開', '门': '門',
    '车': '車', '东': '東', '马': '馬', '鸟': '鳥', '鱼': '魚',
    '见': '見', '贝': '貝', '页': '頁', '风': '風', '飞': '飛',
    '齿': '歯', '长': '長', '专': '専', '业': '業', '严': '厳',
    '书': '書', '买': '買', '卖': '売', '亲': '親', '产': '産',
    '亿': '億', '仪': '儀', '们': '們', '价': '価', '众': '衆',
    '优': '優', '传': '伝', '伤': '傷', '伪': '偽', '债': '債',
    '倾': '傾', '偿': '償', '储': '儲', '兽': '獣', '军': '軍',
    '农': '農', '决': '決', '准': '準', '减': '減', '刘': '劉',
    '刚': '剛', '创': '創', '别': '別', '劝': '勧', '办': '弁',
    '务': '務', '动': '動', '劳': '労', '势': '勢', '勋': '勲',
    '压': '圧', '厌': '厭', '县': '県', '变': '変', '叹': '嘆',
    '响': '響', '哑': '唖', '哗': '嘩', '啸': '嘯', '喷': '噴',
    '园': '園', '团': '団', '围': '囲', '图': '図', '坚': '堅',
    '报': '報', '执': '執', '扩': '拡', '扫': '掃', '扰': '擾',
    '杂': '雑', '检': '検', '样': '様', '树': '樹', '欢': '歓',
    '电': '電', '疗': '療', '疯': '瘋', '盖': '蓋', '盘': '盤',
    '确': '確', '码': '碼', '离': '離', '称': '称', '稳': '穏',
    '积': '積', '穷': '窮', '窃': '竊', '竞': '競', '笔': '筆',
    '算': '算', '简': '簡', '练': '練', '织': '織', '绘': '絵',
    '给': '給', '络': '絡', '绝': '絶', '绞': '絞', '统': '統',
    '绪': '緒', '续': '続', '维': '維', '绵': '綿', '综': '綜',
    '绿': '緑', '缀': '綴', '线': '線', '缎': '緞', '缔': '締',
    '编': '編', '缘': '縁', '网': '網', '紧': '緊', '总': '総',
    '罚': '罰', '罢': '罷', '罗': '羅', '义': '義', '习': '習',
    '联': '聯', '聪': '聡', '声': '声', '职': '職', '肃': '粛',
    '脑': '脳', '脚': '脚', '脱': '脱', '脸': '顔', '腊': '臘',
    '胜': '勝', '胡': '胡', '脏': '臓', '腾': '騰', '臣': '臣',
    '卧': '臥', '临': '臨', '自': '自', '臭': '臭', '至': '至',
    '致': '致', '台': '台', '与': '与', '兴': '興', '举': '挙',
    '旧': '旧', '舌': '舌', '舍': '舎', '铺': '舗', '舞': '舞',
    '舟': '舟', '舱': '艙', '舵': '舵', '舶': '舶', '船': '船',
    '舰': '艦', '艰': '艱', '色': '色', '艳': '艶', '艺': '芸',
    '节': '節', '苹': '苹', '芒': '芒', '芝': '芝', '芦': '芦',
    '芬': '芬', '芭': '芭', '芯': '芯', '花': '花', '芳': '芳',
    '芷': '芷', '芸': '芸', '芹': '芹', '芽': '芽', '芾': '芾',
}
# Filter out any identical entries where simplified == shinjitai
SIMPLIFIED_CHINESE_CHECK = {k: v for k, v in SIMPLIFIED_CHINESE_CHECK.items() if k != v}


def check_card_agent(card: dict[str, Any], index: int) -> list[str]:
    issues: list[str] = []
    guid = str(card.get("guid", "")).strip()
    word = str(card.get("Word", "")).strip()
    reading = str(card.get("Reading", "")).strip()
    furigana = str(card.get("Furigana", "")).strip()
    sentence = str(card.get("Sentence", "")).strip()
    translation = str(card.get("SentenceTranslation", "")).strip()
    grammar_pattern = str(card.get("GrammarPattern", "")).strip()
    tags = str(card.get("Tags", "")).strip()

    if not guid:
        issues.append("Missing GUID")
    if not word:
        issues.append("Missing Word")
    if not reading:
        issues.append("Missing Reading")
    if not furigana:
        issues.append("Missing Furigana")
    if not sentence:
        issues.append("Missing Sentence")
    if not translation:
        issues.append("Missing SentenceTranslation")
    if not grammar_pattern:
        issues.append("Missing GrammarPattern")

    # Ensure audio is empty
    if card.get("WordAudio", "") != "":
        issues.append(f"WordAudio must be empty, found {card.get('WordAudio')!r}")
    if card.get("SentenceAudio", "") != "":
        issues.append(f"SentenceAudio must be empty, found {card.get('SentenceAudio')!r}")

    # Check for simplified Chinese in Japanese sentence
    for simp, shin in SIMPLIFIED_CHINESE_CHECK.items():
        if simp in sentence:
            issues.append(f"Simplified Chinese '{simp}' found in Japanese sentence (expected Shinjitai '{shin}')")

    # Check that word or stem appears in sentence
    clean_w = re.sub(r'<br\s*/?>', ' ', word)
    clean_w = re.sub(r'[\(（][^\)）]*[\)）]', ' ', clean_w)
    clean_w = clean_w.strip('～〜~-‐ \t\n')

    tokens = [t.strip('～〜~-‐ ') for t in re.split(r'[/／\s]+', clean_w) if t.strip('～〜~-‐ ')]
    if not tokens:
        tokens = [word]
    if 'する' in tokens:
        tokens.extend(['し', 'され', 'せず', 'しよう', 'して'])
    if any(k in tokens for k in ('来る', 'くる')):
        tokens.extend(['来', 'こ', 'き'])

    stem_found = False
    for t in tokens:
        if t in sentence:
            stem_found = True
            break
        # Check stem without trailing kana for verbs/adjectives
        if len(t) >= 2 and t[-1] in 'るうつくすつぬふむぶぐい':
            stem = t[:-1]
            if stem in sentence:
                stem_found = True
                break
        # Check kanji root
        kanji_only = ''.join([c for c in t if '\u4e00' <= c <= '\u9fff'])
        if len(kanji_only) >= 1 and kanji_only in sentence:
            stem_found = True
            break

    if not stem_found and len(clean_w) > 0:
        issues.append(f"Target word '{word}' not found in sentence '{sentence[:25]}...'")

    # Validate ruby format
    if "[" in furigana or "]" in furigana:
        if furigana.count("[") != furigana.count("]"):
            issues.append(f"Mismatched furigana brackets: '{furigana}'")

    return issues

def main():
    parser = argparse.ArgumentParser(description="Agent offline verification for N3/N4 deck.")
    parser.add_argument("--deck", type=Path, default=DEFAULT_DECK_PATH)
    parser.add_argument("--cards-dir", type=Path, default=DEFAULT_CARDS_DIR)
    args = parser.parse_args()

    cards = []
    if args.deck.is_file():
        with open(args.deck, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("#"):
                    continue
                parts = line.strip("\n").split("\t")
                if len(parts) >= 16:
                    card = dict(zip(COLUMNS, parts[:16]))
                    cards.append(card)
        print(f"Loaded {len(cards)} cards from {args.deck}")
    elif args.cards_dir.is_dir():
        card_files = sorted(args.cards_dir.glob("*.json"))
        for cf in card_files:
            try:
                with open(cf, "r", encoding="utf-8") as f:
                    cards.append(json.load(f))
            except Exception as e:
                print(f"Warning: Failed to load {cf.name}: {e}")
        cards.sort(key=lambda c: c.get("word_index", 0))
        print(f"Loaded {len(cards)} cards from {args.cards_dir}")
    else:
        print(f"Error: Neither {args.deck} nor {args.cards_dir} found.")
        return 1
    flagged = 0
    for idx, card in enumerate(cards):
        issues = check_card_agent(card, idx)
        if issues:
            flagged += 1
            w = card.get("Word", "?")
            print(f"Card #{idx:04d} ({w}): {'; '.join(issues)}")

    if flagged == 0:
        print(f"✓ 100% of {len(cards)} cards passed agent offline verification with ZERO errors!")
        return 0
    else:
        print(f"Verification found issues in {flagged} / {len(cards)} cards.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
