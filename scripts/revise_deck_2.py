#!/usr/bin/env python3
"""
Comprehensive normalization and revision script for Deck_2.
Fixes:
1. Mangled Word fields (removes <br>, duplicate kana/kanji strings, stray parentheses/collocations).
2. Mangled Reading fields (replaces with pure kana, removes HTML, Kanji, and parentheses).
3. Mangled Furigana fields (regenerates clean ruby bracket notation Kanji[reading]).
4. Unstandardized POS values (maps Chinese/raw descriptions to Japanese standard POS).
5. Standardizes punctuation (replaces ~ with fullwidth ～, cleans bracket spaces).
6. Syncs all changes to Deck_2/progress/cards/*.json, Deck_2/Words.json, and compiles Deck_2/deck.txt.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import pipeline_lib as lib
import build_deck_2

NOTES_PATH = REPO_ROOT / "Selected Notes 2.txt"
DECK_PATH = REPO_ROOT / "Deck_2" / "deck.txt"
WORDS_PATH = REPO_ROOT / "Deck_2" / "Words.json"
CARDS_DIR = REPO_ROOT / "Deck_2" / "progress" / "cards"

KANJI_RE = re.compile(r"[\u4e00-\u9fff]")
KANA_RE = re.compile(r"^[\u3040-\u309F\u30A0-\u30FF\u30FC\u30FB\uFF5E\u301C~〜・/／\s\-－\u3001\u3002\u2015？！\?!…]+$")

POS_STANDARDIZE_MAP = {
    "フレーズ": "表現",
    "动词 (三类/他动词)": "名・他動3",
    "疑問詞": "代・疑問",
    "二类形容词": "ナ形",
    "动词 (三类/自动词)": "名・自動3",
    "助詞": "助詞",
    "一类形容词": "イ形",
    "名・副": "名・副",
    "指示詞": "代",
    "名・サ変": "名・自他動3",
    "词组": "連語",
    "名・自动3": "名・自動3",
    "動": "動",
    "接续词": "接",
    "二类形容词/名词": "名・ナ形",
    "名・他动3": "名・他動3",
    "连体词": "連体",
    "名・自サ": "名・自動3",
    "補助動詞": "動",
    "副词词组": "副",
    "名词/二类形容词": "名・ナ形",
    "名词/副词": "名・副",
    "动词 (三类/自动词/他动词)": "名・自他動3",
    "副・自動3": "副・自動3",
    "名詞": "名",
    "複合助詞": "連語",
    "助動詞": "助動詞",
    "特殊尊敬動詞": "他動",
    "动词 (三类)": "名・自他動3",
    "名・サ変動詞": "名・自他動3",
    "名・形動": "名・ナ形",
    "名・スル動": "名・自他動3",
    "名・接尾": "名・接尾",
    "名.ナ形": "名・ナ形",
    "名・ナ形・自動3": "名・ナ形・自動3",
    "接头": "接頭",
    "副・疑問詞": "副・疑問",
    "名・量": "名・量",
    "感動詞": "感",
    "不規則": "動",
    "名詞・副詞": "名・副",
    "接尾辞": "接尾",
    "動詞": "動",
    "形": "イ形",
    "自": "自動",
    "下一段": "一段",
    "特殊 (尊敬語)": "他動",
    "助動": "助動詞",
    "名词 (略语)": "名",
    "连体词/名词": "連体・名",
    "副词/接续词": "副・接",
    "动词 (词组/他动词)": "連語・他動",
    "动词 (自动词/他动词)": "自他動",
    "副词/二类形容词": "副・ナ形",
    "Na-形容词": "ナ形",
    "I-形容词": "イ形",
    "副词/名词": "副・名",
    "二类形容词/动词(三类)": "ナ形・自他動3",
    "动词 (词组/自动词)": "連語・自動",
    "接续词/副词": "接・副",
    "形容動詞/副詞": "ナ形・副",
    "动词 (三类/他动词/自动词)": "名・自他動3",
    "名詞 (言語学用語)": "名",
    "动词 (自动词)": "自動",
    "他動・サ変": "他動3",
    "二类形容词/感叹词": "ナ形・感",
    "名・形動・自動3": "名・ナ形・自動3",
    "副词": "副",
    "名/形動": "名・ナ形",
    "名・動": "名・動",
    "动词 (词组)": "連語",
    "名词/形容动词": "名・ナ形",
    "动词 (一段/他动词)": "他動2",
    "形容詞": "イ形",
    "自動5": "自動1",
    "名・ナ形・副": "名・ナ形・副",
    "名・感": "名・感",
    "名・他動3・ナ形": "名・他動3・ナ形",
    "自他動1": "自他動1",
    "他動詞": "他動",
    "名・他サ": "名・他動3",
    "副・接": "副・接",
    "名・自他动3": "名・自他動3",
    "自他动2": "自他動2",
    "名词": "名",
}

MANUAL_FIXES = {
    "捜す": ("捜す", "さがす", "捜[さが]す"),
    "千元纸币": ("千円札", "せんえんさつ", "千円札[せんえんさつ]"),
    "售罄": ("売り切れ", "うりきれ", "売[う]り切[き]れ"),
    "商务用语 抱歉": ("恐れ入る", "おそれいる", "恐[おそ]れ入[い]る"),
    "～社 (～しゃ) / ～長 (～ちょう)": ("～社/～長", "～しゃ/～ちょう", "～社[しゃ]/～長[ちょう]"),
    "気味": ("気味", "ぎみ", "気味[ぎみ]"),
    "iPSさいぼう iPS細胞": ("iPS細胞", "アイピーエスさいぼう", "iPS細[さい]胞[ぼう]"),
    "iPS細胞": ("iPS細胞", "アイピーエスさいぼう", "iPS細[さい]胞[ぼう]"),
    "～でも 飲みませんか": ("～でも飲みませんか", "～でものみませんか", "～でも飲[の]みませんか"),
    "～でも飲みませんか": ("～でも飲みませんか", "～でものみませんか", "～でも飲[の]みませんか"),
    "飲みませんか": ("～でも飲みませんか", "～でものみませんか", "～でも飲[の]みませんか"),
    "もう 帰らないと……": ("もう帰らないと……", "もうかえらないと……", "もう帰[かえ]らないと……"),
    "もう帰らないと……": ("もう帰らないと……", "もうかえらないと……", "もう帰[かえ]らないと……"),
    "帰らないと……": ("もう帰らないと……", "もうかえらないと……", "もう帰[かえ]らないと……"),
    "お世話に なりました": ("お世話になりました", "おせわになりました", "お世話[せわ]になりました"),
    "お世話になりました": ("お世話になりました", "おせわになりました", "お世話[せわ]になりました"),
    "お世話に": ("お世話になりました", "おせわになりました", "お世話[せわ]になりました"),
    "どうぞ お元気で": ("どうぞお元気で", "どうぞおげんきで", "どうぞお元気[げんき]で"),
    "どうぞお元気で": ("どうぞお元気で", "どうぞおげんきで", "どうぞお元気[げんき]で"),
    "お元気で": ("どうぞお元気で", "どうぞおげんきで", "どうぞお元気[げんき]で"),
    "助け合う": ("助け合う", "たすけあう", "助[たす]け合[あ]う"),
    "助け合います": ("助け合う", "たすけあう", "助[たす]け合[あ]う"),
    "お祝い": ("お祝い", "おいわい", "お祝[いわ]い"),
    "楽しみにしています": ("楽しみにしています", "たのしみにしています", "楽[たの]しみにしています"),
    "失礼いたします。": ("失礼いたします", "しつれいいたします", "失礼[しつれい]いたします"),
    "失礼いたします": ("失礼いたします", "しつれいいたします", "失礼[しつれい]いたします"),
    "これからお世話になります": ("これからお世話になります", "これからおせわになります", "これからお世話[せわ]になります"),
    "こちらこそ、よろしくお願いします": ("こちらこそ、よろしくお願いします", "こちらこそ、よろしくおねがいします", "こちらこそ、よろしくお願[ねが]いします"),
    "失礼します": ("失礼します", "しつれいします", "失礼[しつれい]します"),
    "お願いします": ("お願いします", "おねがいします", "お願[ねが]いします"),
    "行ってきます": ("行ってきます", "いってきます", "行[い]ってきます"),
    "これでお願いします": ("これでお願いします", "これでおねがいします", "これでお願[ねが]いします"),
    "お先に失礼します": ("お先に失礼します", "おさきにしつれいします", "お先[さき]に失礼[しつれい]します"),
}

def clean_sound(t: str) -> str:
    return re.sub(r"\[sound:[^\]]+\]", "", t).strip()

def has_kanji(t: str) -> bool:
    return bool(KANJI_RE.search(t))

def convert_verb_masu(w: str, r: str, pos: str) -> tuple[str, str]:
    if any(k in pos for k in ("動詞", "五段", "一段", "カ変", "サ変", "動")):
        if w.endswith("ます"):
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
            else:
                conv = {"い": "う", "き": "く", "ぎ": "ぐ", "し": "す", "ち": "つ", "に": "ぬ", "び": "ぶ", "み": "む", "り": "る"}
                stem_w = w[:-2]
                stem_r = r[:-2]
                if stem_w and stem_w[-1] in conv:
                    w = stem_w[:-1] + conv[stem_w[-1]]
                if stem_r and stem_r[-1] in conv:
                    r = stem_r[:-1] + conv[stem_r[-1]]
    return w, r

def convert_reading_masu(r: str, pos: str) -> str:
    if not r.endswith("ます"):
        return r
    if r.endswith("します") and ("サ変" in pos or "名・" in pos):
        return r[:-3] + "する"
    if "一段" in pos:
        return r[:-2] + "る"
    elif "サ変" in pos:
        return r[:-3] + "する"
    elif "カ変" in pos:
        return r[:-2] + "る"
    else:
        conv = {"い": "う", "き": "く", "ぎ": "ぐ", "し": "す", "ち": "つ", "に": "ぬ", "び": "ぶ", "み": "む", "り": "る"}
        stem_r = r[:-2]
        if stem_r and stem_r[-1] in conv:
            return stem_r[:-1] + conv[stem_r[-1]]
    return r

def safe_generate_furigana(w: str, r: str) -> str:
    w = w.strip()
    r = r.strip()
    if not w or not r:
        return w or r
    if w == r:
        return w
    if w.startswith("―"):
        return "―" + lib.generate_furigana(w[1:], r.lstrip("―")).strip()
    return lib.generate_furigana(w, r).strip()

def normalize_card_terms(word: str, reading: str, furigana: str, pos: str, raw_note_text: str) -> tuple[str, str, str, str]:
    raw_w = clean_sound(raw_note_text).replace("~", "～")

    new_w, new_r, new_f = word.strip(), reading.strip(), furigana.strip()

    if word in MANUAL_FIXES:
        new_w, new_r, new_f = MANUAL_FIXES[word]
    elif raw_w in MANUAL_FIXES:
        new_w, new_r, new_f = MANUAL_FIXES[raw_w]
    elif "<br" in raw_w or "<br" in word:
        src = raw_w if "<br" in raw_w else word
        parts = [p.strip() for p in re.split(r"<br\s*/?>", src) if p.strip()]
        if len(parts) >= 2:
            p1, p2 = parts[0], parts[1]
            p1_clean = re.sub(r"[\(（\[].*?[\)）\]]", "", p1).strip()
            p2_clean = re.sub(r"[\(（\[].*?[\)）\]]", "", p2).strip()
            if has_kanji(p2_clean):
                new_w, new_r = p2_clean, p1_clean
            elif has_kanji(p1_clean):
                new_w, new_r = p1_clean, p2_clean
            else:
                new_w = p2_clean or p1_clean
                new_r = p1_clean or p2_clean
        else:
            p1_clean = re.sub(r"[\(（\[].*?[\)）\]]", "", parts[0]).strip()
            new_w, new_r = p1_clean, p1_clean
        new_w = new_w.replace(" ", "").replace("　", "")
        new_r = new_r.replace(" ", "").replace("　", "")
        new_w, new_r = convert_verb_masu(new_w, new_r, pos)
        new_f = safe_generate_furigana(new_w, new_r)
    elif " " in word:
        parts = word.split()
        if len(parts) == 2 and not has_kanji(parts[0]) and has_kanji(parts[1]):
            new_r, new_w = parts[0].strip(), parts[1].strip()
            new_w, new_r = convert_verb_masu(new_w, new_r, pos)
            new_f = safe_generate_furigana(new_w, new_r)
        elif len(parts) == 2 and has_kanji(parts[0]) and not has_kanji(parts[1]):
            new_w, new_r = parts[0].strip(), parts[1].strip()
            new_w, new_r = convert_verb_masu(new_w, new_r, pos)
            new_f = safe_generate_furigana(new_w, new_r)
        elif len(parts) == 2 and parts[0].endswith("ます"):
            new_w = parts[1].strip()
            new_r = parts[1].strip()
            new_f = parts[1].strip()
        elif len(parts) == 2 and parts[1] == "<br>":
            new_w = parts[0].strip()
            new_r = parts[0].strip()
            new_f = parts[0].strip()
        else:
            clean_phrase = word.replace(" ", "").replace("　", "")
            new_w = clean_phrase
            new_r = reading.replace(" ", "").replace("　", "")
            if has_kanji(new_r):
                cand = re.sub(r"[一-龥々ヶA-Za-z0-9~～\-－]+\s*\[([^\]]+)\]", r"\1", furigana).replace(" ", "")
                if not has_kanji(cand) and KANA_RE.match(cand):
                    new_r = cand
            new_f = safe_generate_furigana(new_w, new_r)
    elif any(b in word for b in "()（）[]"):
        m = re.search(r"^([^\(\（]+)[\s]*[\(\（]([^\)\）]+)[\)\）]$", word)
        if m:
            p1, p2 = m.group(1).strip(), m.group(2).strip()
            if has_kanji(p1) and not has_kanji(p2):
                new_w, new_r = p1, p2
            elif not has_kanji(p1) and has_kanji(p2):
                new_w, new_r = p2, p1
            else:
                new_w, new_r = p1, p2
        else:
            new_w = re.sub(r"[\(（\[].*?[\)）\]]", "", word).strip()
            new_r = re.sub(r"[\(（\[].*?[\)）\]]", "", reading).strip()
        new_w = new_w.replace(" ", "").replace("　", "")
        new_r = new_r.replace(" ", "").replace("　", "")
        new_f = safe_generate_furigana(new_w, new_r)
    elif has_kanji(reading):
        cand = re.sub(r"[一-龥々ヶA-Za-z0-9~～\-－]+\s*\[([^\]]+)\]", r"\1", furigana).replace(" ", "")
        if not has_kanji(cand) and KANA_RE.match(cand):
            new_r = cand
            new_f = safe_generate_furigana(new_w, new_r)

    # Standardize POS
    new_p = POS_STANDARDIZE_MAP.get(pos, pos)

    # Convert reading if still ending in ます for verbs whose word is a dictionary lemma
    if new_r.endswith("ます") and not new_w.endswith("ます") and new_p not in ("表現", "挨拶", "連語"):
        new_r = convert_reading_masu(new_r, new_p)
        new_f = safe_generate_furigana(new_w, new_r)

    # Clean residual parens/brackets in reading
    new_r = re.sub(r"[\(（\[].*?[\)）\]]", "", new_r).strip()

    # Standardize tildes
    new_w = new_w.replace("~", "～")
    new_r = new_r.replace("~", "～")
    new_f = new_f.replace("~", "～")

    # Clean bracket whitespace
    new_f = re.sub(r"\[\s+", "[", new_f)
    new_f = re.sub(r"\s+\]", "]", new_f)

    # If furigana still contains [reading_ending_in_masu] while word is lemma, regenerate
    if "[" in new_f and new_f.endswith("ます]") and not new_w.endswith("ます"):
        new_f = safe_generate_furigana(new_w, new_r)

    # If furigana contains empty brackets [], regenerate
    if "[]" in new_f:
        new_f = safe_generate_furigana(new_w, new_r)

    return new_w, new_r, new_f, new_p

def main() -> int:
    print("==================================================================")
    print("  REVISING DECK_2 FLASHCARDS AND BUILDING CLEAN DECK")
    print("==================================================================")

    if not NOTES_PATH.is_file():
        print(f"Error: {NOTES_PATH} not found", file=sys.stderr)
        return 1

    with open(NOTES_PATH, "r", encoding="utf-8") as f:
        note_lines = [l.rstrip("\r\n").split("\t") for l in f if not l.startswith("#") and l.strip()]

    card_files = sorted(CARDS_DIR.glob("*.json"))
    if not card_files:
        print(f"Error: No card files found in {CARDS_DIR}", file=sys.stderr)
        return 1

    print(f"Loaded {len(note_lines)} notes and {len(card_files)} card files.")

    revised_count = 0
    words_update_map = {}

    for cf in card_files:
        with open(cf, "r", encoding="utf-8") as f:
            card = json.load(f)

        idx = card.get("word_index")
        if idx is None or idx >= len(note_lines):
            continue

        raw_note = note_lines[idx]
        raw_w = raw_note[4]

        orig_w = card.get("Word", "")
        orig_r = card.get("Reading", "")
        orig_f = card.get("Furigana", "")
        orig_p = card.get("POS", "")

        new_w, new_r, new_f, new_p = normalize_card_terms(orig_w, orig_r, orig_f, orig_p, raw_w)

        changed = (new_w != orig_w or new_r != orig_r or new_f != orig_f or new_p != orig_p)

        card["Word"] = new_w
        card["Reading"] = new_r
        card["Furigana"] = new_f
        card["POS"] = new_p
        card["WordAudio"] = ""
        card["SentenceAudio"] = ""

        if changed:
            revised_count += 1
            with open(cf, "w", encoding="utf-8") as f:
                json.dump(card, f, ensure_ascii=False, indent=2)

        words_update_map[idx] = (new_w, new_r, new_f, new_p)

    print(f"Revised {revised_count} / {len(card_files)} card JSON files.")

    # Update Words.json
    if WORDS_PATH.is_file():
        with open(WORDS_PATH, "r", encoding="utf-8") as f:
            words_doc = json.load(f)

        for it in words_doc.get("vocabulary_list", []):
            idx = it.get("word_index")
            if idx in words_update_map:
                nw, nr, nf, np = words_update_map[idx]
                it["word"] = nw
                it["reading"] = nr
                it["furigana"] = nf
                it["pos"] = np

        with open(WORDS_PATH, "w", encoding="utf-8") as f:
            json.dump(words_doc, f, ensure_ascii=False, indent=2)
        print(f"Updated {WORDS_PATH}")

    # Compile Deck_2/deck.txt
    print("Compiling final deck...")
    build_deck_2.compile_deck()

    return 0

if __name__ == "__main__":
    sys.exit(main())
