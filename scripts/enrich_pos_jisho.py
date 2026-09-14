#!/usr/bin/env python3
"""
Enrich and standardize Part of Speech (POS) tags for all 556 entries
in Selected Notes.txt using the free and open Jisho.org API.
Results are cached in N3_4_Level/pos_cache.json.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SELECTED_NOTES_PATH = REPO_ROOT / "Selected Notes.txt"
CACHE_PATH = REPO_ROOT / "N3_4_Level" / "pos_cache.json"

# Explicit fallback / override dictionary for idioms, expressions, and grammar phrases
SPECIAL_POS_OVERRIDES = {
    "いいえ": "感動詞",
    "ごちそうさまでした": "連語・挨拶",
    "そろそろ失礼します": "連語・挨拶",
    "一緒にいかがですか": "連语・表現",
    "また今度お願いします": "連語・挨拶",
    "どうもすみません": "連語・挨拶",
    "お引き出しですか": "連語・表現",
    "それはいけませんね": "連語・挨拶",
    "さあ": "感動詞",
    "～によって": "連語",
    "～みたいにしてください": "連語・表現",
    "～加減": "接尾",
    "～柄": "接尾",
    "～期": "接尾",
    "～目": "接尾",
    "～中": "接尾",
    "～製": "接尾",
    "～位": "接尾",
    "～自身": "接尾",
    "準〜": "接頭",
    "国際～": "接頭",
    "ざらざら": "副・自他動3",
    "さんざん": "副・ナ形",
    "ごちゃごちゃ": "副・ナ形・自動3",
    "うとうと": "副・自動3",
    "うんざり": "副・自動3",
    "ごろごろ": "副・自動3",
    "終始": "副・自動3",
    "何": "代",
    "何人": "名",
    "二人": "名",
    "どこか": "代",
    "これら": "代",
    "それに": "接続",
    "従って": "接続",
    "かまいません": "連語・表現",
    "お住まい": "名",
    "自分では": "連語",
    "困った人": "名",
}

def map_jisho_pos(pos_list: list[str]) -> str:
    """Map Jisho parts_of_speech array to standard Japanese POS format."""
    is_noun = any("Noun" in p for p in pos_list)
    is_adv = any("Adverb" in p for p in pos_list)
    is_i_adj = any("I-adjective" in p for p in pos_list)
    is_na_adj = any("Na-adjective" in p for p in pos_list)
    is_pronoun = any("Pronoun" in p for p in pos_list)
    is_conj = any("Conjunction" in p for p in pos_list)
    is_prefix = any("Prefix" in p for p in pos_list)
    is_suffix = any("Suffix" in p for p in pos_list)
    is_interj = any("Interjection" in p for p in pos_list)
    is_expr = any("Expressions" in p for p in pos_list)

    is_trans = any("Transitive verb" in p for p in pos_list)
    is_intrans = any("Intransitive verb" in p for p in pos_list)
    is_godan = any("Godan" in p for p in pos_list)
    is_ichidan = any("Ichidan" in p for p in pos_list)
    is_suru = any("Suru verb" in p for p in pos_list)

    verb_type = ""
    if is_godan:
        verb_type = "1"
    elif is_ichidan:
        verb_type = "2"
    elif is_suru:
        verb_type = "3"

    if verb_type:
        if is_trans and is_intrans:
            v_str = f"自他動{verb_type}"
        elif is_trans:
            v_str = f"他動{verb_type}"
        elif is_intrans:
            v_str = f"自動{verb_type}"
        else:
            v_str = f"他動{verb_type}" if verb_type == "3" else f"動{verb_type}"
    else:
        v_str = ""

    parts = []
    if is_noun and not is_suru:
        parts.append("名")
    elif is_noun and is_suru:
        parts.append(f"名・{v_str}" if v_str else "名・他動3")
        v_str = ""

    if is_na_adj:
        parts.append("ナ形")
    if is_i_adj:
        parts.append("イ形")
    if is_adv:
        parts.append("副")
    if v_str:
        parts.append(v_str)
    if is_pronoun:
        parts.append("代")
    if is_conj:
        parts.append("接続")
    if is_prefix:
        parts.append("接頭")
    if is_suffix:
        parts.append("接尾")
    if is_interj:
        parts.append("感")
    if is_expr and not parts:
        parts.append("連語")

    return "・".join(parts) if parts else "名"

def fetch_jisho(word: str) -> list[str]:
    """Fetch parts of speech from Jisho API with polite retry/backoff."""
    # Clean query word
    query_word = re.sub(r"^[～~～\-－]+|[～~～\-－]+$", "", word).strip()
    query_word = re.sub(r"[（\(].*?[）\)]", "", query_word).strip()
    if "/" in query_word or "／" in query_word:
        query_word = re.split(r"[/／]", query_word)[0].strip()

    if not query_word:
        return []

    url = f"https://jisho.org/api/v1/search/words?keyword={urllib.parse.quote(query_word)}"
    headers = {"User-Agent": "Mozilla/5.0 (AnkiDeckMigrationBot/1.0; +https://github.com)"}

    max_retries = 3
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for entry in data.get("data", []):
                    # Find first sense with parts_of_speech
                    for sense in entry.get("senses", []):
                        pos = sense.get("parts_of_speech", [])
                        if pos:
                            return pos
                return []
        except urllib.error.HTTPError as e:
            if e.code == 429:
                # Rate limited, backoff
                wait_time = 2.0 * (attempt + 1)
                time.sleep(wait_time)
            else:
                return []
        except Exception:
            time.sleep(1.0)
    return []

def main():
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    cache: dict[str, dict] = {}
    if CACHE_PATH.exists():
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                cache = json.load(f)
            print(f"Loaded {len(cache)} cached entries from {CACHE_PATH}")
        except Exception:
            cache = {}

    # Import word normalization from prepare_n3_4_words
    from prepare_n3_4_words import load_normalized_words
    words = load_normalized_words()
    print(f"Total words to verify POS: {len(words)}")

    updated = 0
    for idx, w_entry in enumerate(words):
        word = w_entry["word"]
        clean_key = word.strip()

        if clean_key in SPECIAL_POS_OVERRIDES:
            pos = SPECIAL_POS_OVERRIDES[clean_key]
            cache[clean_key] = {"jisho_pos": [pos], "mapped_pos": pos, "source": "override"}
            continue

        if clean_key in cache:
            continue

        # Fetch from Jisho
        jisho_pos = fetch_jisho(clean_key)
        if jisho_pos:
            mapped_pos = map_jisho_pos(jisho_pos)
            source = "jisho"
        else:
            mapped_pos = w_entry.get("pos", "名")
            source = "fallback"

        cache[clean_key] = {
            "jisho_pos": jisho_pos,
            "mapped_pos": mapped_pos,
            "source": source
        }
        updated += 1
        if updated % 10 == 0 or updated == 1:
            print(f"[{idx+1}/{len(words)}] {clean_key} -> {mapped_pos} (from {source})")
            # Save cache incrementally
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        time.sleep(0.35)

    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print(f"Finished POS enrichment! Cache now has {len(cache)} entries.")

if __name__ == "__main__":
    main()
