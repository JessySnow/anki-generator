#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Assemble generated batch 09 cards and write to output file.
"""

import json
import os
import sys
from pathlib import Path

# Add scripts directory to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from batch_09_part1 import DATA_PART1
from batch_09_part2 import DATA_PART2

def main():
    merged_data = {}
    merged_data.update(DATA_PART1)
    merged_data.update(DATA_PART2)

    batch_path = REPO_ROOT / "N3_4_Level" / "batches" / "batch_09.json"
    with open(batch_path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    print(f"Loaded {len(raw_items)} raw items from {batch_path}")
    print(f"Loaded {len(merged_data)} linguistic card contents")

    cards = []
    for item in raw_items:
        w_idx = item["word_index"]
        if w_idx not in merged_data:
            print(f"ERROR: missing card data for word_index {w_idx} ({item.get('word')})")
            sys.exit(1)

        c_info = merged_data[w_idx]

        orig_tags = item.get("original_tags", "").strip()
        tag_parts = ["N3_4::Vocabulary", f"N3_4::Grammar::{item['grammar_id']}"]
        if orig_tags:
            tag_parts.append(orig_tags)
        tags_str = " ".join(tag_parts)

        card = {
            "guid": item["guid"],
            "word_index": w_idx,
            "Word": item["word"],
            "Reading": item["reading"],
            "Furigana": item["furigana"],
            "POS": item["pos"],
            "Meaning": item["meaning"],
            "WordAudio": "",
            "Sentence": c_info["Sentence"],
            "SentenceAudio": "",
            "SentenceTranslation": c_info["SentenceTranslation"],
            "WordUsage": c_info["WordUsage"],
            "GrammarPattern": item["grammar_pattern"],
            "GrammarMeaning": item["grammar_meaning"],
            "GrammarUsage": c_info["GrammarUsage"],
            "CombinationLogic": c_info["CombinationLogic"],
            "Tags": tags_str
        }

        # Verification of required fields
        required = [
            "guid", "word_index", "Word", "Reading", "Furigana", "POS", "Meaning",
            "Sentence", "SentenceTranslation", "WordUsage",
            "GrammarPattern", "GrammarMeaning", "GrammarUsage", "CombinationLogic", "Tags"
        ]
        for r in required:
            if card.get(r) is None or str(card[r]).strip() == "":
                print(f"ERROR: card {w_idx} has empty field {r}")
                sys.exit(1)

        cards.append(card)

    print(f"All {len(cards)} cards successfully constructed and validated.")

    # Targets to write
    out_dir_brain = Path("/Users/jessy/.gemini/antigravity-cli/brain/3abb8178-8eed-4291-a9d9-73b17c24edb7/scratch")
    out_dir_brain.mkdir(parents=True, exist_ok=True)
    target_brain = out_dir_brain / "generated_batch_09.json"

    with open(target_brain, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
    print(f"Successfully wrote {len(cards)} cards to {target_brain}")

    target_local = REPO_ROOT / "N3_4_Level" / "batches" / "generated_batch_09.json"
    with open(target_local, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
    print(f"Successfully wrote local copy to {target_local}")

if __name__ == "__main__":
    main()
