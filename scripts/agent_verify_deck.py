#!/usr/bin/env python3
"""
Agent-level offline verification for the Anki JLPT N2 Deck.
Performs deterministic, syntactic, typographic, and linguistic integrity checks
across all 1,634 cards in N2 Level/deck.txt and progress/cards/*.json
without consuming external API quota.
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

from pipeline_lib import (
    CARD_COLUMNS,
    CARDS_DIR,
    DEFAULT_DECK_PATH,
    generate_furigana,
    lint_card,
    parse_deck_rows,
)

# Common Simplified Chinese characters that often mistakenly replace Japanese Shinjitai
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
    '步': '歩', '歼': '殲', '毕': '畢', '残': '残', '毁': '毀',
    '汉': '漢', '汗': '汗', '污': '汚', '沦': '淪', '浅': '浅',
    '测': '測', '济': '済', '浓': '濃', '灾': '災', '灵': '霊',
    '点': '点', '炼': '錬', '热': '熱', '爱': '愛', '独': '独',
    '狭': '狭', '猎': '猟', '现': '現', '理': '理', '环': '環',
    '电': '電', '疗': '療', '疯': '瘋', '盖': '蓋', '盘': '盤',
    '监': '監', '睁': '睜', '瞒': '瞞', '确': '確', '码': '碼',
    '离': '離', '科': '科', '秘': '秘', '称': '称', '稳': '穏',
    '积': '積', '穷': '窮', '窃': '竊', '竞': '競', '笔': '筆',
    '算': '算', '简': '簡', '练': '練', '织': '織', '绘': '絵',
    '给': '給', '络': '絡', '绝': '絶', '绞': '絞', '统': '統',
    '绪': '緒', '续': '続', '维': '維', '绵': '綿', '综': '綜',
    '绿': '緑', '缀': '綴', '线': '線', '缎': '緞', '缔': '締',
    '编': '編', '缓': '緩', '纬': '緯', '紧': '緊', '纵': '縦',
    '缝': '縫', '缩': '縮', '结': '結', '绕': '繞', '诱': '誘',
    '语': '語', '误': '誤', '说': '説', '读': '読', '课': '課',
    '谁': '誰', '调': '調', '谈': '談', '谋': '謀', '谎': '謊',
    '设': '設', '访': '訪', '证': '証', '评': '評', '识': '識',
    '诈': '詐', '诉': '訴', '诊': '診', '词': '詞', '译': '訳',
    '试': '試', '诗': '詩', '诚': '誠', '话': '話', '诞': '誕',
    '该': '該', '详': '詳', '赶': '趕', '趋': '趨', '跃': '躍',
    '转': '転', '轮': '輪', '软': '軟', '轰': '轟', '轻': '軽',
    '载': '載', '辉': '輝', '边': '辺', '达': '達', '迁': '遷',
    '过': '過', '运': '運', '还': '還', '进': '進', '远': '遠',
    '违': '違', '连': '連', '迟': '遅', '选': '選', '遗': '遺',
    '邮': '郵', '邻': '隣', '郑': '鄭', '针': '針', '钟': '鐘',
    '铁': '鉄', '银': '銀', '铺': '鋪', '链': '鏈', '销': '銷',
    '锐': '鋭', '铸': '鋳', '铺': '舗', '键': '鍵', '门': '門',
    '闭': '閉', '问': '問', '间': '間', '闷': '悶', '闹': '鬧',
    '闻': '聞', '阀': '閥', '阁': '閣', '阅': '閲', '队': '隊',
    '阳': '陽', '阴': '陰', '阵': '陣', '阶': '階', '际': '際',
    '随': '随', '险': '険', '隐': '隠', '难': '難', '震': '震',
    '静': '静', '面': '面', '革': '革', '顶': '頂', '项': '項',
    '顺': '順', '须': '須', '顽': '頑', '顾': '顧', '顿': '頓',
    '预': '預', '颁': '頒', '领': '領', '频': '頻', '题': '題',
    '风': '風', '馆': '館', '验': '験', '齐': '斉',
}

# Note: In Japanese, 叶 in 叶える (かなえる) is standard (常用/人名用), not a typo.
EXEMPT_KANJI = {'叶', '窃'}


def check_card_agent(card: dict, card_index: int) -> list[str]:
    """Run thorough agent checks on a single card dictionary."""
    issues = []

    # 1. Base linting
    issues.extend(lint_card(card))

    word = str(card.get('Word', '')).strip()
    reading = str(card.get('Reading', '')).strip()
    furigana = str(card.get('Furigana', '')).strip()
    pos = str(card.get('POS', '')).strip()
    sentence = str(card.get('Sentence', '')).strip()
    translation = str(card.get('SentenceTranslation', '')).strip()
    gp = str(card.get('GrammarPattern', '')).strip()
    logic = str(card.get('CombinationLogic', '')).strip()

    # 2. Audio format check
    wa = card.get('WordAudio', '').strip()
    sa = card.get('SentenceAudio', '').strip()
    if wa and not re.match(r'^\[sound:n2_card_\d{4}\.mp3\]$', wa):
        issues.append(f"Invalid WordAudio format: '{wa}'")
    if sa and not re.match(r'^\[sound:n2_card_\d{4}\.mp3\]$', sa):
        issues.append(f"Invalid SentenceAudio format: '{sa}'")

    # 3. Furigana consistency with generate_furigana
    expected_furi = generate_furigana(word, reading)
    expected_furi = re.sub(r'\]\s+([^\s\[\]])', r']', expected_furi)
    if furigana != expected_furi:
        issues.append(f"Furigana '{furigana}' does not match expected '{expected_furi}'")

    # 4. Sentence ending punctuation
    if not sentence.endswith(('。', '！', '？', '」', '』', '…')):
        issues.append('Sentence missing proper Japanese ending punctuation')

    # 5. Translation completeness
    if len(translation) < 4:
        issues.append(f"Sentence translation too short or missing: '{translation}'")

    # 6. Check for Simplified Chinese typos
    for fld in ('Word', 'Reading', 'Furigana', 'Sentence', 'GrammarPattern'):
        val = str(card.get(fld, ''))
        for ch in val:
            if ch in SIMPLIFIED_CHINESE_CHECK and ch not in EXEMPT_KANJI:
                jp = SIMPLIFIED_CHINESE_CHECK[ch]
                if ch != jp:
                    issues.append(f"Simplified Chinese character '{ch}' detected in {fld} (should be '{jp}')")

    # 7. Word presence in Sentence
    clean_word = word.strip('～〜~')
    variants = [v.strip() for v in re.split(r'[/／]', clean_word) if v.strip()]
    word_found = False
    for v in variants:
        if v in sentence:
            word_found = True
            break
        # Kanji stem
        stem = re.sub(r'[ぁ-ん]+$', '', v)
        if stem and len(stem) >= 1 and stem in sentence:
            word_found = True
            break
        # Pure kana verb inflection stem (e.g. ためらう -> ためら, ちぎる -> ちぎ)
        if len(v) >= 3 and all('぀' <= ch <= 'ゟ' for ch in v):
            if v[:-1] in sentence or (len(v) >= 4 and v[:-2] in sentence):
                word_found = True
                break
    if not word_found:
        clean_reading = reading.strip('～〜~')
        r_variants = [rv.strip() for rv in re.split(r'[/／]', clean_reading) if rv.strip()]
        for rv in r_variants:
            if rv in sentence:
                word_found = True
                break
            stem_r = re.sub(r'[ぁ-ん]+$', '', rv)
            if stem_r and len(stem_r) >= 2 and stem_r in sentence:
                word_found = True
                break
    if not word_found:
        issues.append(f"Target word '{word}' or valid inflection not found in sentence")

    # 8. GrammarPattern presence in Sentence
    gp_clean = gp.strip('～〜~')
    gp_opts = [opt.strip().strip('～〜~') for opt in re.split(r'[/／]', gp_clean) if opt.strip()]
    gp_found = False
    for opt in gp_opts:
        if '～' in opt:
            subparts = [p.strip() for p in opt.split('～') if p.strip()]
            if all(sp in sentence for sp in subparts):
                gp_found = True
                break
        else:
            if opt in sentence:
                gp_found = True
                break
            opt_no_paren = re.sub(r'[（\(].*?[）\)]', '', opt).strip()
            opt_unbracketed = opt.replace('（', '').replace('）', '').replace('(', '').replace(')', '').strip()
            if (opt_no_paren and opt_no_paren in sentence) or (opt_unbracketed and opt_unbracketed in sentence):
                gp_found = True
                break
            inflections = []
            for stem, reps in [
                ('得る', ['うる', 'える', 'え', '得ます']),
                ('ない', ['なく', 'ず', 'なかった']),
                ('すむ', ['すんだ', 'すま']),
                ('きる', ['きれ', 'きっ', 'きり']),
                ('抜く', ['抜い', 'ぬき', 'ぬく', 'ぬいた']), ('ぬく', ['抜く', '抜い', 'ぬき', 'ぬいた', 'ぬく']),
                ('かねる', ['かね']),
                ('っぽい', ['っぽ']),
                ('がち', ['がち']),
                ('甲斐', ['甲斐']),
                ('たまらない', ['たまら']),
                ('ならない', ['なら']),
                ('しょうがない', ['しょうが']),
                ('しようがない', ['しようが']),
                ('とたん', ['とたん']),
                ('ところ', ['ところ']),
                ('わたる', ['わた']),
                ('かける', ['かけ']),
                ('しまう', ['しまっ', 'しまい']),
                ('ばかりはいられない', ['ばかりはいられない', 'ばかりもいられない']),
                ('ともなって', ['伴って']),
            ]:
                if stem in opt:
                    for rep in reps:
                        inflections.append(opt.replace(stem, rep))
                        inflections.append(rep)
            if any(inf in sentence for inf in inflections):
                gp_found = True
                break

    if not gp_found:
        issues.append(f"Grammar pattern '{gp}' not recognized in sentence")

    return issues


def verify_deck(
    deck_path: Path = DEFAULT_DECK_PATH,
    cards_dir: Path = CARDS_DIR,
) -> dict[str, Any]:
    """Verify entire Anki deck file and card JSON cache."""
    print('=' * 68)
    print('  AGENT OFFLINE DECK VERIFICATION')
    print('=' * 68)
    print(f'  Deck File: {deck_path}')
    print(f'  Cards Dir: {cards_dir}')
    print('=' * 68)

    headers, cards = parse_deck_rows(deck_path)
    total_cards = len(cards)
    print(f'Loaded {total_cards} cards from deck file.')

    results: dict[str, Any] = {
        'total_cards': total_cards,
        'valid_cards': 0,
        'flagged_cards': 0,
        'missing_json_cards': 0,
        'json_mismatches': 0,
        'card_issues': {},
        'summary': 'PASSED',
    }

    # Verify synchronization with progress/cards/
    for i, c in enumerate(cards):
        p = cards_dir / f'{i:04d}.json'
        if not p.is_file():
            p = cards_dir / f'{i}.json'
        if not p.is_file():
            results['missing_json_cards'] += 1
            continue

        with open(p, 'r', encoding='utf-8') as f:
            jcard = json.load(f)

        for col in CARD_COLUMNS:
            if c.get(col, '').strip() != jcard.get(col, '').strip():
                results['json_mismatches'] += 1
                break

    # Run agent checks on every card
    for i, c in enumerate(cards):
        issues = check_card_agent(c, i)
        if issues:
            results['card_issues'][i] = {
                'word': c.get('Word', ''),
                'reading': c.get('Reading', ''),
                'issues': issues,
            }

    results['flagged_cards'] = len(results['card_issues'])
    results['valid_cards'] = total_cards - results['flagged_cards']

    print('\n--- VERIFICATION RESULTS ---')
    print(f'  Total Cards Checked   : {results["total_cards"]}')
    print(f'  Valid Clean Cards     : {results["valid_cards"]}')
    print(f'  Flagged Cards         : {results["flagged_cards"]}')
    print(f'  Missing Card JSONs    : {results["missing_json_cards"]}')
    print(f'  Deck/JSON Mismatches  : {results["json_mismatches"]}')

    if results['flagged_cards'] > 0 or results['missing_json_cards'] > 0 or results['json_mismatches'] > 0:
        results['summary'] = 'FAILED'
        print('\n[!] Issues detected:')
        for idx, details in list(results['card_issues'].items())[:10]:
            print(f'  Card #{idx:04d} ({details["word"]}): {details["issues"]}')
        if len(results['card_issues']) > 10:
            print(f'  ... and {len(results["card_issues"]) - 10} more cards.')
    else:
        results['summary'] = 'PASSED'
        print('\n✓ 100% of cards passed agent offline verification with ZERO errors!')

    print('=' * 68)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description='Agent offline deck verification')
    parser.add_argument('--deck', type=Path, default=DEFAULT_DECK_PATH, help='Path to deck.txt')
    parser.add_argument('--cards-dir', type=Path, default=CARDS_DIR, help='Path to cards directory')
    args = parser.parse_args()

    results = verify_deck(deck_path=args.deck, cards_dir=args.cards_dir)
    return 0 if results['summary'] == 'PASSED' else 1


if __name__ == '__main__':
    sys.exit(main())
