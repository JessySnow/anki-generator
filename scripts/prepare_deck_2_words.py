#!/usr/bin/env python3
"""
Prepare and normalize vocabulary entries from Selected Notes 2.txt into Deck_2/Words.json.
Combines grammar points from N2 Level/Grammar.json (180 points) and N3_4_Level/Grammar.json (227 points).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import pipeline_lib as lib
from prepare_n3_4_words import GRAMMAR_ZH

SELECTED_NOTES_2_PATH = REPO_ROOT / "Selected Notes 2.txt"
N2_GRAMMAR_PATH = REPO_ROOT / "N2 Level" / "Grammar.json"
N3_4_GRAMMAR_PATH = REPO_ROOT / "N3_4_Level" / "Grammar.json"
OUTPUT_DIR = REPO_ROOT / "Deck_2"
WORDS_OUTPUT_PATH = OUTPUT_DIR / "Words.json"
BATCHES_DIR = OUTPUT_DIR / "batches"
POS_CACHE_PATH = REPO_ROOT / "N3_4_Level" / "pos_cache.json"

POS_STANDARDIZE_MAP = {
    "名詞": "名",
    "名词": "名",
    "副詞": "副",
    "副词": "副",
    "い形容詞": "イ形",
    "形容词": "イ形",
    "な形容詞": "ナ形",
    "形容动词": "ナ形",
    "代名詞": "代",
    "代词": "代",
    "接続詞": "接",
    "连词": "接",
    "感動詞": "感",
    "感叹词": "感",
    "接尾辞": "接尾",
    "后缀": "接尾",
    "接頭辞": "接頭",
    "前缀": "接頭",
    "助数詞": "量",
    "量词": "量",
    "連体詞": "連体",
    "連語": "連語",
    "表現": "表現",
    "挨拶": "挨拶",
    "慣用句": "慣用",
    "ことわざ": "諺",
    "五段動詞": "五段",
    "一段動詞": "一段",
    "サ変動詞": "サ変",
    "カ変動詞": "カ変",
    "动词 (他动词)": "他動",
    "动词 (自动词)": "自動",
    "名词/动词(三类)": "名・自他動3",
}

def clean_sound(text: str) -> str:
    return re.sub(r"\[sound:[^\]]+\]", "", text).strip()

def has_kanji(text: str) -> bool:
    return any(0x4e00 <= ord(c) <= 0x9fff for c in text)

def has_digits(text: str) -> bool:
    return any(c.isdigit() or ('０' <= c <= '９') for c in text)

def normalize_v2_word_reading(raw_text: str, pos: str) -> tuple[str, str, str]:
    """Parse V2 raw word into (word, reading, collocation_note)."""
    w = clean_sound(raw_text)

    # 1. Check for slashes (e.g., '思います (おもいます) / 思う (おもう)')
    if "/" in w or "／" in w:
        parts = re.split(r"\s*[/／]\s*", w)
        w = parts[-1].strip()

    # 2. Check for bracketed collocations/context: 'あります [お祭りが～]' or '[どうぞ]よろしく[お願いします]'
    colloc = ""
    # Distinguish context brackets at end vs optional words at start/end
    if w.startswith("[") and "]" in w and not w.endswith("]"):
        # e.g. [どうぞ]よろしく[お願いします] -> word is よろしく, colloc is どうぞ...お願いします
        bracket_parts = re.findall(r"\[(.*?)\]", w)
        colloc = " ".join(bracket_parts)
        w = re.sub(r"\[.*?\]", "", w).strip()
    elif "[" in w and "]" in w:
        m_col = re.search(r"\[(.*?)\]", w)
        if m_col:
            colloc = m_col.group(1).strip()
            w = re.sub(r"\[.*?\]", "", w).strip()

    # 3. Check for parentheses: 'わたし(私)' or '習います (ならいます)' or 'きゅう(9)'
    r = ""
    m_paren = re.search(r"^([^\(\（]+)[\s]*[\(\（]([^\)\）]+)[\)\）]$", w)
    if m_paren:
        p1 = m_paren.group(1).strip()
        p2 = m_paren.group(2).strip()

        p1_k = has_kanji(p1) or has_digits(p1)
        p2_k = has_kanji(p2) or has_digits(p2)

        if not p1_k and p2_k:
            w = p2
            r = p1
        elif p1_k and not p2_k:
            w = p1
            r = p2
        else:
            # e.g. IMC(アイ・エム・シー) -> English word, Katakana reading
            w = p1
            r = p2
    else:
        r = w

    # 4. Verb dictionary form conversion if ending in ます
    if any(k in pos for k in ("動詞", "五段", "一段", "カ変", "サ変")) and w.endswith("ます"):
        if "一段" in pos:
            w = w[:-2] + "る"
            if r.endswith("ます"):
                r = r[:-2] + "る"
        elif "サ変" in pos:
            w = w[:-2] + "する"
            if r.endswith("ます"):
                r = r[:-2] + "する"
        elif "カ変" in pos:
            w = w[:-2] + "る"
            if r.endswith("ます"):
                r = r[:-2] + "る"
        elif "五段" in pos or "動詞" in pos:
            conv = {"い": "う", "き": "く", "ぎ": "ぐ", "し": "す", "ち": "つ", "に": "ぬ", "び": "ぶ", "み": "む", "り": "る"}
            stem_w = w[:-2]
            stem_r = r[:-2]
            if stem_w and stem_w[-1] in conv:
                w = stem_w[:-1] + conv[stem_w[-1]]
            if stem_r and stem_r[-1] in conv:
                r = stem_r[:-1] + conv[stem_r[-1]]

    return w.strip(), r.strip(), colloc.strip()

def load_combined_grammar() -> list[dict]:
    """Load the unified 407 grammar points from Deck_2/Grammar.json."""
    merged_grammar_path = OUTPUT_DIR / "Grammar.json"
    with open(merged_grammar_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["grammar_list"]

def main():
    print("==================================================================")
    print("  PREPARING VOCABULARY DATASET FROM Selected Notes 2.txt")
    print("==================================================================")

    if not SELECTED_NOTES_2_PATH.is_file():
        print(f"Error: {SELECTED_NOTES_2_PATH} not found!", file=sys.stderr)
        return 1

    with open(SELECTED_NOTES_2_PATH, "r", encoding="utf-8") as f:
        lines = [l.rstrip("\r\n") for l in f if l.strip() and not l.startswith("#")]

    print(f"Loaded {len(lines)} raw note lines.")

    # Load POS cache if available
    pos_cache = {}
    if POS_CACHE_PATH.is_file():
        try:
            with open(POS_CACHE_PATH, "r", encoding="utf-8") as f:
                pos_cache = json.load(f)
        except Exception:
            pos_cache = {}

    combined_grammar = load_combined_grammar()
    grammar_count = len(combined_grammar)
    print(f"Loaded {grammar_count} combined grammar points (N2: 180, N3/N4: 227).")

    words_data = []

    for idx, line in enumerate(lines):
        parts = line.split("\t")
        if len(parts) < 19:
            # Pad if needed
            parts = parts + [""] * (19 - len(parts))

        guid = parts[0]
        notetype = parts[1]
        deck = parts[2]
        tags = parts[18].strip()

        colloc = ""

        if notetype == "Japanese N2 Vocab & Grammar":
            w = parts[3].strip()
            r = parts[4].strip()
            furi = parts[5].strip()
            p = parts[6].strip()
            meaning = parts[7].strip()
        elif notetype == "日文单词V3":
            raw_w = clean_sound(parts[4])
            if "/" in raw_w or "／" in raw_w:
                raw_w = re.split(r"[/／]", raw_w)[0].strip()
            w = raw_w
            r = parts[5].strip()
            p = parts[6].strip()
            meaning = parts[3].strip()
            furi = lib.generate_furigana(w, r)
        else:
            # 日文单词V2
            meaning = parts[3].strip()
            raw_w = parts[4]
            raw_pos = parts[5].strip()
            w, r, colloc = normalize_v2_word_reading(raw_w, raw_pos)
            p = raw_pos
            furi = lib.generate_furigana(w, r)

        # Standardize POS
        p_std = POS_STANDARDIZE_MAP.get(p, p)
        # Check POS cache
        if w in pos_cache:
            p_std = pos_cache[w].get("mapped_pos", p_std)

        # Assign deterministic grammar point
        g_entry = combined_grammar[idx % grammar_count]

        words_data.append({
            "word_index": idx,
            "guid": guid,
            "notetype": "Japanese N2 Vocab & Grammar",
            "deck": deck,
            "word": w,
            "reading": r,
            "furigana": furi,
            "pos": p_std,
            "meaning": meaning,
            "collocation_note": colloc,
            "grammar_id": g_entry["grammar_id"],
            "grammar_level": g_entry["level"],
            "grammar_pattern": g_entry["pattern"],
            "grammar_meaning": g_entry["meaning"],
            "grammar_connection": g_entry["connection"],
            "grammar_tag": g_entry["tag"],
            "original_tags": tags,
            "source_notetype": notetype
        })

    # Save to Words.json
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(WORDS_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "total": len(words_data),
            "grammar_pool_size": grammar_count,
            "vocabulary_list": words_data
        }, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(words_data)} entries to {WORDS_OUTPUT_PATH}")

    # Split into batches of 100 for tracking
    BATCHES_DIR.mkdir(parents=True, exist_ok=True)
    batch_size = 100
    for b_idx in range(0, len(words_data), batch_size):
        chunk = words_data[b_idx : b_idx + batch_size]
        batch_num = b_idx // batch_size + 1
        batch_file = BATCHES_DIR / f"batch_{batch_num:02d}.json"
        with open(batch_file, "w", encoding="utf-8") as f:
            json.dump({
                "batch_number": batch_num,
                "count": len(chunk),
                "items": chunk
            }, f, ensure_ascii=False, indent=2)

    print(f"Generated {(len(words_data) + batch_size - 1) // batch_size} batch files in {BATCHES_DIR}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
