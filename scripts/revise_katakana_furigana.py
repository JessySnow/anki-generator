#!/usr/bin/env python3
"""
Revise cards in Deck_Full/Selected Notes.txt that should use 'カタカナ' in the '振り仮名' field.

Creates standalone output files:
1. Deck_Full/Revised Notes.txt - Standalone file containing the 64 revised cards with Anki headers
   (ready to import into Anki to update existing cards via GUID matching).
2. Deck_Full/Selected Notes (Full Revised).txt - Complete consolidated collection (6,146 notes)
   with the 64 revisions integrated.

The original Deck_Full/Selected Notes.txt is preserved completely unmodified.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = REPO_ROOT / "Deck_Full" / "Selected Notes.txt"
REVISED_DIFF_PATH = REPO_ROOT / "Deck_Full" / "Revised Notes.txt"
FULL_REVISED_PATH = REPO_ROOT / "Deck_Full" / "Selected Notes (Full Revised).txt"

# 1. Pure Katakana words where Reading/Furigana was Hiragana (56 cards)
PURE_KATAKANA_LINES = [2587] + [
    3037, 3039, 3040, 3042, 3043, 3056, 3073, 3086, 3087, 3111, 3123,
    3215, 3264, 3265, 3266, 3267, 3270, 3271, 3272, 3273, 3274, 3276, 3278, 3280, 3281, 3287,
    3353, 3361, 3363, 3364, 3368, 3369, 3370, 3371, 3372, 3375,
    3429, 3439, 3442, 3472, 3474, 3475,
    3959, 3960, 4090, 4092, 4131, 4156, 4160, 4165, 4168, 4169, 4173, 4191, 4232
]

# 2. Acronym loanwords with Hiragana Reading/Furigana (3 cards)
ACRONYM_HIRA_LINES = [3440, 3467, 3471]

# 3. Acronym loanwords with Latin Furigana (2 cards)
ACRONYM_LATIN_LINES = [96, 507]

# 4. Mixed/compound words with Furigana/Ruby issues (3 cards)
MIXED_LINES = [486, 582, 5911]

ALL_TARGET_LINES = sorted(PURE_KATAKANA_LINES + ACRONYM_HIRA_LINES + ACRONYM_LATIN_LINES + MIXED_LINES)


def revise_card(parts: list[str], line_no: int) -> tuple[list[str], str]:
    """Return revised parts and the category explanation."""
    new_parts = list(parts)
    word = parts[3].strip()
    category = ""

    if line_no in PURE_KATAKANA_LINES:
        category = "カタカナ単語（外来語・生物名）の振り仮名・読み方をカタカナに修正"
        if word == "アイス〜":
            new_r = "アイス〜"
            new_f = "アイス〜"
        elif word == "〜スタンド":
            new_r = "〜スタンド"
            new_f = "〜スタンド"
        elif word == "〜ケース":
            new_r = "〜ケース"
            new_f = "〜ケース"
        else:
            new_r = word
            new_f = word
        new_parts[4] = new_r
        new_parts[5] = new_f

    elif line_no == 3440:  # NHK
        category = "英略語の読み方・振り仮名をカタカナに修正"
        new_parts[4] = "エヌエイチケー"
        new_parts[5] = "エヌエイチケー"

    elif line_no == 3467:  # OL
        category = "英略語の読み方・振り仮名をカタカナに修正"
        new_parts[4] = "オーエル"
        new_parts[5] = "オーエル"

    elif line_no == 3471:  # OK
        category = "英略語の読み方・振り仮名をカタカナに修正"
        new_parts[4] = "オーケー"
        new_parts[5] = "オーケー"

    elif line_no == 96:  # CD
        category = "英略語の振り仮名（未設定・アルファベット表示）をカタカナ読みに修正"
        new_parts[4] = "シーディー"
        new_parts[5] = "シーディー"

    elif line_no == 507:  # ATM
        category = "英略語の振り仮名（未設定・アルファベット表示）をカタカナ読みに修正"
        new_parts[4] = "エー・ティー・エム"
        new_parts[5] = "エー・ティー・エム"

    elif line_no == 486:  # ローマ字
        category = "混種語の振り仮名ルビ漏れを修正"
        new_parts[4] = "ローマじ"
        new_parts[5] = "ローマ 字[じ]"

    elif line_no == 582:  # 一カ月
        category = "カタカナ混じり語のルビ位置（カの脱落）を修正"
        new_parts[4] = "いっかげつ"
        new_parts[5] = "一[いっ]カ月[げつ]"

    elif line_no == 5911:  # レジ袋
        category = "混種語のカタカナ部分がルビ内で平仮名化された誤りを修正"
        new_parts[4] = "レジぶくろ"
        new_parts[5] = "レジ 袋[ぶくろ]"

    return new_parts, category


def main():
    print(f"Reading from: {INPUT_PATH}")
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    header_lines = [l for l in raw_lines if l.startswith("#")]
    print(f"Loaded {len(raw_lines)} total lines ({len(header_lines)} headers, {len(raw_lines) - len(header_lines)} cards).")

    revised_rows: list[list[str]] = []
    full_revised_lines: list[str] = []

    # Copy headers to full file
    full_revised_lines.extend(header_lines)

    target_set = set(ALL_TARGET_LINES)
    count_revised = 0

    for idx, line in enumerate(raw_lines):
        line_no = idx + 1
        if line.startswith("#"):
            continue

        parts = line.strip("\r\n").split("\t")
        assert len(parts) == 19, f"Row {line_no} does not have 19 columns: {len(parts)}"

        if line_no in target_set:
            new_parts, category = revise_card(parts, line_no)
            assert len(new_parts) == 19
            revised_rows.append(new_parts)
            full_revised_lines.append("\t".join(new_parts) + "\n")
            count_revised += 1
        else:
            full_revised_lines.append(line)

    print(f"Total cards revised: {count_revised} (expected: {len(ALL_TARGET_LINES)})")
    assert count_revised == len(ALL_TARGET_LINES), "Mismatch in revised count!"

    # 1. Write standalone Revised Notes.txt (headers + revised cards)
    with open(REVISED_DIFF_PATH, "w", encoding="utf-8") as f:
        for h in header_lines:
            f.write(h)
        for r in revised_rows:
            f.write("\t".join(r) + "\n")
    print(f"Successfully wrote {len(revised_rows)} revised cards to: {REVISED_DIFF_PATH}")

    # 2. Write standalone Selected Notes (Full Revised).txt (all 6,146 cards)
    with open(FULL_REVISED_PATH, "w", encoding="utf-8") as f:
        for l in full_revised_lines:
            f.write(l)
    print(f"Successfully wrote full collection ({len(full_revised_lines) - len(header_lines)} cards) to: {FULL_REVISED_PATH}")


if __name__ == "__main__":
    main()
