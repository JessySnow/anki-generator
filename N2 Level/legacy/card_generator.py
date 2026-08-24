#!/usr/bin/env python3
# Superseded by ../scripts/ (subagent-based generation, no external LLM API).
# Kept for reference only.

import argparse
import csv
import json
import os
import random
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

N2_DIR = Path(__file__).resolve().parent
WORDS_FILES = ["Words1.json", "Words2.json", "Words3.json", "Words4.json"]
GRAMMAR_FILE = "Grammar.json"
DEFAULT_OUTPUT = N2_DIR / "output_cards.txt"
DEFAULT_PROGRESS = N2_DIR / "progress.json"
HEADER_LINES = ["#separator:tab", "#html:true", "#tags column:7"]
MAX_ATTEMPTS = 3
REQUIRED_KEYS = ["sentence", "translation", "word_usage", "grammar_usage", "combination_logic"]

POS_RE = re.compile(r"\[([^\]]+)\]")

SYSTEM_PROMPT = (
    "You are a Japanese language teacher creating study material. "
    "Always reply with a single JSON object and nothing else - no markdown fences, no commentary."
)


@dataclass
class VocabEntry:
    card_id: str
    word: str
    reading: str
    meaning: str
    pos: str


@dataclass
class GrammarEntry:
    grammar_id: int
    pattern: str
    connection: str
    meaning: str
    example_sentences: list


@dataclass
class GeneratedCard:
    sentence: str
    translation: str
    word_usage: str
    grammar_usage: str
    combination_logic: str


def load_vocab() -> list:
    entries = []
    for filename in WORDS_FILES:
        with open(N2_DIR / filename, encoding="utf-8") as f:
            items = json.load(f)["vocabulary_lists"]
        for item in items:
            meaning = item["meaning"]
            pos_match = POS_RE.search(meaning)
            entries.append(VocabEntry(
                card_id=f"{filename}:{item['id']}",
                word=item["vocabulary"],
                reading=item["pronounce"],
                meaning=meaning,
                pos=pos_match.group(1) if pos_match else "",
            ))
    return entries


def load_grammar() -> list:
    with open(N2_DIR / GRAMMAR_FILE, encoding="utf-8") as f:
        items = json.load(f)["grammar_list"]
    return [
        GrammarEntry(
            grammar_id=item["id"],
            pattern=item["pattern"],
            connection=item["connection"],
            meaning=item["meaning"],
            example_sentences=item["example_sentences"],
        )
        for item in items
    ]


class ProgressStore:
    """Tracks which vocabulary cards are already done so a run can be resumed."""

    def __init__(self, path: Path):
        self.path = path
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"completed_ids": [], "failed": []}
        self.completed_ids = set(data.get("completed_ids", []))
        self.failed = data.get("failed", [])

    def is_done(self, card_id: str) -> bool:
        return card_id in self.completed_ids

    def mark_completed(self, card_id: str) -> None:
        self.completed_ids.add(card_id)
        self._save()

    def mark_failed(self, card_id: str, reason: str) -> None:
        self.completed_ids.add(card_id)
        self.failed.append({"id": card_id, "reason": reason})
        self._save()

    def _save(self) -> None:
        data = {"completed_ids": sorted(self.completed_ids), "failed": self.failed}
        fd, tmp_path = tempfile.mkstemp(dir=self.path.parent, prefix=".progress-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.path)
        except BaseException:
            os.remove(tmp_path)
            raise


REGISTERS = [
    "a casual conversation between friends",
    "a polite conversation with a stranger or colleague",
    "a business email",
    "a news report or narration",
    "an internal monologue/diary entry",
]


def build_prompt(vocab: VocabEntry, grammar: GrammarEntry, feedback: Optional[str]) -> str:
    examples = "\n".join(f"- {s}" for s in grammar.example_sentences[:2])
    register = random.choice(REGISTERS)
    lines = [
        "Create one JLPT N2-level Japanese example sentence that naturally uses BOTH of the "
        "following, then analyze it.",
        "",
        f"Vocabulary word: {vocab.word} ({vocab.reading})",
        f"Word meaning (Chinese): {vocab.meaning}",
        f"Use the word specifically in this sense - if {vocab.word} has other meanings or "
        "readings, do not use those.",
        "",
        f"Grammar pattern: {grammar.pattern}",
        f"Conjugation rule: {grammar.connection}",
        f"Grammar meaning (Chinese): {grammar.meaning}",
    ]
    if examples:
        lines += [
            "Reference example sentences using this grammar pattern (these show the grammar "
            "form only - your sentence must use a different topic/situation, not reuse their "
            "wording):",
            examples,
        ]
    lines += [
        "",
        f"Write the sentence as {register}.",
        "",
        "Requirements:",
        f'- The sentence must contain the word "{vocab.word}" exactly as written, in the meaning given above.',
        f'- The sentence must correctly apply the grammar pattern "{grammar.pattern}".',
        "- Exactly one sentence, about 20-40 Japanese characters - long enough to give real "
        "context, short enough to read comfortably on a flashcard.",
        "- Naturalness check: before finalizing, confirm the sentence is something a native "
        "Japanese speaker would actually say in that register/context, not merely a "
        "grammatically valid textbook sentence. If it sounds stiff or artificial, rewrite it.",
        "",
        "Reply with ONLY a JSON object with exactly these keys:",
        '{"sentence": "<the Japanese sentence>", '
        '"translation": "<Chinese translation of the sentence>", '
        f'"word_usage": "<Chinese explanation of how {vocab.word} is used in the sentence>", '
        '"grammar_usage": "<Chinese explanation of how the grammar pattern is used in the sentence>", '
        '"combination_logic": "<Chinese explanation of how the word and grammar work together naturally>"}',
    ]
    if feedback:
        lines += ["", f"Your previous attempt was rejected: {feedback}. Fix it and try again."]
    return "\n".join(lines)


def call_llm(client: httpx.Client, base_url: str, prompt: str) -> str:
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            response = client.post(
                f"{base_url}/generate",
                json={
                    "prompt": prompt,
                    "system_prompt": SYSTEM_PROMPT,
                    "max_new_tokens": 600,
                    "temperature": 0.7,
                    "top_p": 0.9,
                },
                timeout=120,
            )
        except httpx.TransportError:
            if attempt == max_retries:
                raise
            time.sleep(3)
            continue
        if response.status_code == 503 and attempt < max_retries:
            time.sleep(3)
            continue
        response.raise_for_status()
        return response.json()["generated_text"]
    raise RuntimeError("LLM service unavailable after retries")


def extract_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found in model output")
    return json.loads(text[start:end + 1])


def validate(payload: dict) -> list:
    return [f"missing or empty '{key}'" for key in REQUIRED_KEYS if not str(payload.get(key, "")).strip()]


def generate_card(client, base_url, vocab, grammar):
    feedback = None
    problems = ["unknown error"]
    for _ in range(MAX_ATTEMPTS):
        try:
            raw = call_llm(client, base_url, build_prompt(vocab, grammar, feedback))
            payload = extract_json(raw)
        except (httpx.HTTPError, ValueError) as exc:
            problems = [str(exc)]
            feedback = problems[0]
            continue
        problems = validate(payload)
        if not problems:
            return GeneratedCard(*(str(payload[key]).strip() for key in
                                    ["sentence", "translation", "word_usage", "grammar_usage",
                                     "combination_logic"])), None
        feedback = "; ".join(problems)
    return None, "; ".join(problems)


def format_row(vocab: VocabEntry, grammar: GrammarEntry, card: GeneratedCard) -> list:
    breakdown = {
        f"{vocab.word}_usage": card.word_usage,
        "grammar_usage": card.grammar_usage,
        "combination_logic": card.combination_logic,
    }
    back_field = (
        f"例句翻译：{card.translation}&lt;br&gt;"
        f"文法解析：【{grammar.pattern}（{grammar.meaning}）】"
        f"{json.dumps(breakdown, ensure_ascii=False)}"
    )
    return [vocab.meaning, vocab.word, vocab.reading, vocab.pos, card.sentence, back_field, ""]


def ensure_output_header(path: Path) -> None:
    if not path.exists():
        with open(path, "w", encoding="utf-8", newline="") as f:
            for line in HEADER_LINES:
                f.write(line + "\n")


def append_row(path: Path, row: list) -> None:
    with open(path, "a", encoding="utf-8", newline="") as f:
        csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL).writerow(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate N2 Anki cards using an LLM.")
    parser.add_argument("--base-url", default=os.environ.get("LLM_BASE_URL"),
                         help="Base URL of the LLM service (or set LLM_BASE_URL)")
    parser.add_argument("--limit", type=int, default=None, help="Only generate this many new cards")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--progress", type=Path, default=DEFAULT_PROGRESS)
    args = parser.parse_args()
    if not args.base_url:
        parser.error("LLM base URL is required: pass --base-url or set LLM_BASE_URL")
    return args


def main() -> int:
    args = parse_args()
    vocab_entries = load_vocab()
    grammar_entries = load_grammar()
    progress = ProgressStore(args.progress)
    ensure_output_header(args.output)

    generated = skipped = failed = 0
    with httpx.Client() as client:
        for vocab in vocab_entries:
            if progress.is_done(vocab.card_id):
                skipped += 1
                continue
            if args.limit is not None and generated >= args.limit:
                break

            grammar = random.choice(grammar_entries)
            card, error = generate_card(client, args.base_url, vocab, grammar)
            if card is None:
                progress.mark_failed(vocab.card_id, error)
                failed += 1
                print(f"[FAILED] {vocab.word}: {error}", file=sys.stderr)
                continue

            append_row(args.output, format_row(vocab, grammar, card))
            progress.mark_completed(vocab.card_id)
            generated += 1
            print(f"[OK] {vocab.word} + {grammar.pattern}")

    print(f"\nGenerated: {generated}  Skipped (already done): {skipped}  Failed: {failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
