#!/usr/bin/env python3
"""
Helper to format worker prompts for subagents.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from get_batch import fetch_batch


def format_prompt(worker_id: int, size: int, offset: int) -> str:
    res = fetch_batch(size=size, offset=offset)
    batch = res["batch"]
    if not batch:
        return ""

    lines = [
        f"You are Japanese Language Expert Worker Agent #{worker_id}.",
        "Your working directory is: /Users/jessy/repo/anki-generator",
        "",
        f"Task: Directly generate high quality JLPT N2 Anki flashcards for your assigned {len(batch)} items.",
        "DO NOT use any external APIs. Use your own native Japanese linguistic knowledge to craft each card directly.",
        "",
        "For EACH assigned item below:",
        "1. Craft a natural Japanese N2 sentence meaningfully combining the target word and grammar pattern.",
        "2. Translate the sentence into fluent Chinese.",
        "3. Provide WordUsage (collocation, grammatical role of the word in Chinese).",
        "4. Provide GrammarUsage (conjugation and grammatical function of the grammar pattern in Chinese).",
        "5. Provide CombinationLogic (the contextual and semantic logic connecting the word and grammar in Chinese).",
        '6. Set "WordAudio": "", "SentenceAudio": "", "Tags": "N2::Vocabulary N2::Grammar::<grammar_id>".',
        "7. Save each card using run_command:",
        "   python3 scripts/record_card.py --json '<card_json>'",
        "",
        "Ensure the JSON keys are exactly:",
        "word_index, Word, Reading, Furigana, POS, Meaning, WordAudio, Sentence, SentenceAudio, SentenceTranslation, WordUsage, GrammarPattern, GrammarMeaning, GrammarUsage, CombinationLogic, Tags",
        "",
        f"=== Assigned {len(batch)} Items ===",
    ]

    for item in batch:
        g = item["grammar"]
        lines.append(
            f"- Item (word_index {item['word_index']}): Word='{item['word']}', Reading='{item['reading']}', "
            f"Furigana='{item['furigana']}', POS='{item['pos']}', Meaning='{item['meaning']}' | "
            f"Grammar ID={g['id']}, Pattern='{g['pattern']}', Meaning='{g['meaning']}', Connection='{g['connection']}'"
        )

    lines.append("")
    lines.append("When all cards are recorded with record_card.py, reply with a short summary of recorded indices.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker-id", type=int, default=1)
    parser.add_argument("--size", type=int, default=6)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()

    prompt = format_prompt(args.worker_id, args.size, args.offset)
    print(prompt)


if __name__ == "__main__":
    main()
