#!/usr/bin/env python3
"""
Shared library for the Multi-Agent Anki Card Generation Pipeline.
Provides data loading, term normalization, Anki TSV formatting,
schema validation, and atomic filesystem utilities.
"""

from __future__ import annotations

import html
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
WORDS_PATH = REPO_ROOT / "N2 Level" / "Words.json"
GRAMMAR_PATH = REPO_ROOT / "N2 Level" / "Grammar.json"
TEMPLATE_PATH = REPO_ROOT / "N2 Level" / "template.txt"
DEFAULT_DECK_PATH = REPO_ROOT / "N2 Level" / "deck.txt"
PROGRESS_DIR = REPO_ROOT / "progress"
CARDS_DIR = PROGRESS_DIR / "cards"

PITCH_RE = re.compile(r"[⓪①②③④⑤⑥⑦⑧⑨0-9]+")

CARD_COLUMNS = [
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


def parse_term(raw_term: str) -> tuple[str, str, str]:
    """Parse raw term into (word, reading, furigana).

    Handles half-width/full-width parens, pitch accents, loanword notes, and pure kana.
    """
    term = raw_term.strip()

    # Loanwords with abbreviation note: e.g. "ゼミ(「ゼミナール...の略語」)①"
    if "の略" in term:
        m = re.match(r"^([^(\s（]+)", term)
        if m:
            word = PITCH_RE.sub("", m.group(1)).strip()
            return word, word, word

    # Standard reading with parentheses: e.g. "赤道(せきどう)⓪" or "手本（てほん）②"
    m = re.search(r"^([^(\s（]+)[\s]*[\(（](.+?)[\)）][\s]*([⓪①②③④⑤⑥⑦⑧⑨0-9]*)$", term)
    if m:
        word_part = m.group(1).strip()
        reading_raw = m.group(2).strip()
        word = PITCH_RE.sub("", word_part).strip()
        reading = PITCH_RE.sub("", reading_raw).strip()
        if not word:
            word = reading
        # If the parenthetical content is English (e.g. "ダブル(double)①"), reading is the Katakana word
        if re.search(r"^[a-zA-Z\s\-]+$", reading):
            reading = word
            furigana = word
        else:
            furigana = f"{word}[{reading}]" if word != reading else word
        return word, reading, furigana

    # Pure kana or no parentheses: e.g. "せっせと①"
    word = PITCH_RE.sub("", term).strip()
    return word, word, word


def load_words(file_path: Path = WORDS_PATH) -> list[dict]:
    """Load vocabulary entries from Words.json."""
    if not file_path.is_file():
        raise FileNotFoundError(f"Words file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("vocabulary_list", [])
    if not entries:
        raise ValueError(f"No vocabulary entries found in {file_path}")
    return entries


def load_grammar(file_path: Path = GRAMMAR_PATH) -> list[dict]:
    """Load grammar entries from Grammar.json."""
    if not file_path.is_file():
        raise FileNotFoundError(f"Grammar file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("grammar_list", [])
    if not entries:
        raise ValueError(f"No grammar entries found in {file_path}")
    return entries


def get_completed_indices(cards_dir: Path = CARDS_DIR) -> set[int]:
    """Return set of word indices that have already been generated."""
    if not cards_dir.is_dir():
        return set()
    completed = set()
    for p in cards_dir.glob("*.json"):
        try:
            completed.add(int(p.stem))
        except ValueError:
            continue
    return completed


def atomic_write_json(path: Path, data: Any) -> None:
    """Atomically write JSON data using a temporary file and atomic replace.

    Thread-safe and process-safe across concurrent subagents.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def escape_anki_field(text: Any) -> str:
    """Clean and escape value for Anki TSV import (#html:true mode)."""
    if text is None:
        return ""
    s = str(text).strip()
    # Normalize line breaks
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\n", "<br>")
    # Escape tabs so they do not break column boundaries
    s = s.replace("\t", " ")
    return s


def validate_card(card: dict) -> list[str]:
    """Validate that a card dict has all required fields with proper types.

    Returns a list of validation error strings (empty if valid).
    """
    errors = []
    if not isinstance(card, dict):
        return ["Card must be a JSON dictionary"]

    if "word_index" not in card:
        errors.append("Missing required key: 'word_index'")

    for col in CARD_COLUMNS:
        # Audio fields are intentionally allowed to be empty
        if col in ("WordAudio", "SentenceAudio"):
            continue
        val = card.get(col)
        if val is None or str(val).strip() == "":
            errors.append(f"Field '{col}' is missing or empty")

    return errors


def card_to_row(card: dict) -> list[str]:
    """Convert a card dict to a 15-field TSV list matching CARD_COLUMNS."""
    return [escape_anki_field(card.get(col, "")) for col in CARD_COLUMNS]


def read_template_headers(template_path: Path = TEMPLATE_PATH) -> list[str]:
    """Read the top Anki header directives (#key:val) from template.txt."""
    if not template_path.is_file():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    headers = []
    with open(template_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if line.startswith("#") and not line.startswith("# Note:"):
                headers.append(line)
            elif not line.startswith("#") and line.strip():
                # Reached data rows
                break
    return headers
