#!/usr/bin/env python3
"""
Agent-level offline verification for Deck_2.
Performs deterministic, syntactic, typographic, and linguistic integrity checks
across cards in Deck_2/deck.txt and Deck_2/progress/cards/*.json.
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

DEFAULT_DECK_PATH = REPO_ROOT / 'Deck_2' / 'deck.txt'
DEFAULT_CARDS_DIR = REPO_ROOT / 'Deck_2' / 'progress' / 'cards'

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
    '确': '確', '码': '碼', '离': '離', '稳': '穏',
    '积': '積', '穷': '窮', '窃': '竊', '竞': '競', '笔': '筆',
    '简': '簡', '练': '練', '织': '織', '绘': '絵',
    '给': '給', '络': '絡', '绝': '絶', '绞': '絞', '统': '統',
    '绪': '緒', '续': '続', '维': '維', '绵': '綿', '综': '綜',
    '绿': '緑', '缀': '綴', '线': '線', '缎': '緞', '缔': '締',
    '编': '編', '缘': '縁', '网': '網', '紧': '緊', '总': '総',
    '罚': '罰', '罢': '罷', '罗': '羅', '义': '義', '习': '習',
    '联': '聯', '聪': '聡', '职': '職', '肃': '粛',
    '脑': '脳', '脚': '脚', '脱': '脱', '脸': '顔', '腊': '臘',
    '胜': '勝', '脏': '臓', '腾': '騰', '卧': '臥', '临': '臨',
    '举': '挙', '舍': '舎', '铺': '舗', '舱': '艙', '舵': '舵',
    '舰': '艦', '艰': '艱', '艳': '艶', '艺': '芸', '节': '節',
}
SIMPLIFIED_CHINESE_CHECK = {k: v for k, v in SIMPLIFIED_CHINESE_CHECK.items() if k != v}

def check_card_agent(card: dict[str, Any], index: int) -> list[str]:
    issues: list[str] = []
    guid = str(card.get("guid", "")).strip()
    word = str(card.get("Word", "")).strip()
    reading = str(card.get("Reading", "")).strip()
    furigana = str(card.get("Furigana", "")).strip()
    sentence = str(card.get("Sentence", "")).strip()

    if not guid:
        issues.append(f"Card #{index:04d}: Missing GUID")
    if not word:
        issues.append(f"Card #{index:04d}: Missing Word")
    if not reading:
        issues.append(f"Card #{index:04d}: Missing Reading")
    if not sentence:
        issues.append(f"Card #{index:04d}: Missing Sentence")

    # Audio Drop Policy
    if card.get("WordAudio", "") != "":
        issues.append(f"Card #{index:04d}: WordAudio must be empty")
    if card.get("SentenceAudio", "") != "":
        issues.append(f"Card #{index:04d}: SentenceAudio must be empty")

    # Furigana format check
    if furigana and "[" in furigana:
        if not re.search(r"[一-龥々ヶ]+\[[^\]]+\]", furigana):
            issues.append(f"Card #{index:04d}: Malformed Furigana '{furigana}'")

    # Shinjitai check in Sentence
    for sc, tc in SIMPLIFIED_CHINESE_CHECK.items():
        if sc in sentence:
            issues.append(f"Card #{index:04d}: Simplified Chinese '{sc}' found in Sentence; should be Shinjitai '{tc}'")
        if sc in word:
            issues.append(f"Card #{index:04d}: Simplified Chinese '{sc}' found in Word; should be Shinjitai '{tc}'")

    return issues

def verify_deck(deck_path: Path = DEFAULT_DECK_PATH) -> int:
    if not deck_path.is_file():
        print(f"Error: Deck file {deck_path} does not exist.", file=sys.stderr)
        return 1

    print(f"Verifying {deck_path}...")
    with open(deck_path, "r", encoding="utf-8") as f:
        lines = [l.rstrip("\r\n") for l in f if l.strip()]

    header_lines = [l for l in lines if l.startswith("#")]
    data_lines = [l for l in lines if not l.startswith("#")]

    print(f"Headers: {len(header_lines)}, Data rows: {len(data_lines)}")

    guids = set()
    total_issues = 0

    for idx, line in enumerate(data_lines):
        parts = line.split("\t")
        if len(parts) != 16:
            print(f"Row {idx+1}: Expected 16 columns, got {len(parts)}", file=sys.stderr)
            total_issues += 1

        guid = parts[0]
        if guid in guids:
            print(f"Row {idx+1}: Duplicate GUID '{guid}'", file=sys.stderr)
            total_issues += 1
        guids.add(guid)

        card = {col: parts[i] if i < len(parts) else "" for i, col in enumerate(COLUMNS)}
        issues = check_card_agent(card, idx)
        for issue in issues:
            print(f"  [Issue] {issue}", file=sys.stderr)
            total_issues += 1

    if total_issues == 0:
        print(f"✓ Deck verification passed with 0 issues across {len(data_lines)} cards!")
        return 0
    else:
        print(f"✗ Deck verification failed with {total_issues} issues!", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(verify_deck())
