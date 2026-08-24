"""Shared helpers for the N2 card generation pipeline."""

import csv
import html
import json
import os
import re
import tempfile
from pathlib import Path

N2_DIR = Path(__file__).resolve().parent.parent
WORDS_FILES = ["Words1.json", "Words2.json", "Words3.json", "Words4.json"]
GRAMMAR_FILE = "Grammar.json"

PROGRESS_DIR = N2_DIR / "progress"
SCRATCH_DIR = N2_DIR / "scratch"
OUTPUT_FILE = N2_DIR / "output_cards.txt"

# Cosmetic-only: strips a leading "[POS]"-style bracket tag out of the raw
# `meaning` string for display. Not used to derive the actual POS value -
# the subagent determines POS itself since the bracket format is inconsistent
# across the four Words files (some entries have no bracket at all).
BRACKET_TAG_RE = re.compile(r"\[[^\]]+\]")

TSV_COLUMNS = [
    "Word",
    "Reading",
    "POS",
    "Meaning",
    "Dictionary Example",
    "Example Sentence",
    "Sentence Translation",
    "Word Usage Note",
    "Grammar Pattern",
    "Grammar Meaning",
    "Grammar Connection",
    "Grammar Usage Note",
    "Tags",
]

CARD_KEYS = [
    "id",
    "word",
    "reading",
    "pos",
    "meaning",
    "dictionary_example",
    "example_sentence",
    "sentence_translation",
    "word_usage_note",
    "grammar_id",
    "grammar_pattern",
    "grammar_meaning",
    "grammar_connection",
    "grammar_usage_note",
]


def load_vocab(words_file: str) -> list:
    with open(N2_DIR / words_file, encoding="utf-8") as f:
        return json.load(f)["vocabulary_lists"]


def load_grammar() -> list:
    with open(N2_DIR / GRAMMAR_FILE, encoding="utf-8") as f:
        return json.load(f)["grammar_list"]


def clean_meaning(meaning: str) -> str:
    return re.sub(r"\s+", " ", BRACKET_TAG_RE.sub("", meaning)).strip()


def atomic_write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except BaseException:
        os.remove(tmp_path)
        raise


def read_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def progress_path(words_file: str) -> Path:
    return PROGRESS_DIR / words_file


def scratch_path(words_file: str) -> Path:
    return SCRATCH_DIR / (Path(words_file).stem + ".cards.json")


def load_progress(words_file: str) -> dict:
    return read_json(progress_path(words_file), {"completed_ids": []})


def load_scratch(words_file: str) -> dict:
    return read_json(scratch_path(words_file), {"words_file": words_file, "cards": []})


def escape_field(text) -> str:
    """Clean a value for use as one TSV column in an #html:true Anki import."""
    s = "" if text is None else str(text)
    s = s.strip()
    s = html.escape(s, quote=False)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\n", "<br>")
    s = s.replace("\t", " ")
    return s


def write_output_rows(rows: list) -> None:
    is_new = not OUTPUT_FILE.exists()
    with open(OUTPUT_FILE, "a", encoding="utf-8", newline="") as f:
        if is_new:
            f.write("#separator:tab\n")
            f.write("#html:true\n")
            f.write(f"#tags column:{len(TSV_COLUMNS)}\n")
            f.write("# columns: " + " | ".join(TSV_COLUMNS) + "\n")
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        for row in rows:
            writer.writerow(row)


def card_to_row(card: dict) -> list:
    tags = f"N2::{Path(card['_words_file']).stem} N2::Grammar::{card['grammar_id']}"
    return [
        escape_field(card["word"]),
        escape_field(card["reading"]),
        escape_field(card["pos"]),
        escape_field(card["meaning"]),
        escape_field(card["dictionary_example"]),
        escape_field(card["example_sentence"]),
        escape_field(card["sentence_translation"]),
        escape_field(card["word_usage_note"]),
        escape_field(card["grammar_pattern"]),
        escape_field(card["grammar_meaning"]),
        escape_field(card["grammar_connection"]),
        escape_field(card["grammar_usage_note"]),
        escape_field(tags),
    ]
