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


def load_gemini_api_key(zshrc_path: Path | None = None) -> str | None:
    """Load Gemini API key from environment, .env file, or ~/.zshrc."""
    # 1. Environment variables
    for env_var in ("GEMINI_API_KEY", "GEMINI_KEY"):
        val = os.environ.get(env_var, "").strip()
        if val:
            return val

    # 2. Local .env file in repo root
    env_file = REPO_ROOT / ".env"
    if env_file.is_file():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    if k.strip() in ("GEMINI_API_KEY", "GEMINI_KEY"):
                        cleaned = v.strip().strip("\"'")
                        if cleaned:
                            return cleaned
        except Exception:
            pass

    # 3. ~/.zshrc or custom path
    if zshrc_path is None:
        zshrc_path = Path.home() / ".zshrc"
    if zshrc_path.is_file():
        try:
            with open(zshrc_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#"):
                        continue
                    # Match GEMINI_KEY="xxx" or export GEMINI_KEY='xxx'
                    m = re.match(r"^(?:export\s+)?(GEMINI_API_KEY|GEMINI_KEY)\s*=\s*[\"']?([^\"'\s]+)[\"']?", line)
                    if m:
                        return m.group(2).strip()
        except Exception:
            pass

    return None


def parse_deck_rows(deck_path: Path = DEFAULT_DECK_PATH) -> tuple[list[str], list[dict]]:
    """Parse Anki deck file into headers and list of card dicts with word_index."""
    if not deck_path.is_file():
        raise FileNotFoundError(f"Deck file not found: {deck_path}")

    headers = []
    cards = []
    with open(deck_path, "r", encoding="utf-8") as f:
        data_index = 0
        for line in f:
            line = line.rstrip("\r\n")
            if not line.strip():
                continue
            if line.startswith("#"):
                headers.append(line)
            else:
                parts = line.split("\t")
                # Pad or slice to 15 columns
                if len(parts) < len(CARD_COLUMNS):
                    parts.extend([""] * (len(CARD_COLUMNS) - len(parts)))
                card = dict(zip(CARD_COLUMNS, parts[:len(CARD_COLUMNS)]))
                card["word_index"] = data_index
                cards.append(card)
                data_index += 1
    return headers, cards


def is_kanji(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff" or ch == "々"


def is_kana(ch: str) -> bool:
    return "\u3040" <= ch <= "\u309f" or "\u30a0" <= ch <= "\u30ff"


def generate_furigana(word: str, reading: str) -> str:
    """Generate standard Anki ruby furigana with okurigana placed outside brackets."""
    # 1. Pure kana words (no kanji): return pure kana
    if not any(is_kanji(ch) for ch in word):
        # Strip any extraneous brackets or English notes if present
        return reading.strip()

    has_leading_tilde = word.startswith("～") or word.startswith("〜") or word.startswith("~")
    has_trailing_tilde = word.endswith("～") or word.endswith("〜") or word.endswith("~")
    w = word.strip("～〜~")
    r = reading.strip("～〜~")

    # Tokenize word into alternating blocks of Kanji and Kana
    blocks = []
    current_type = None
    current_chars = []
    for ch in w:
        t = "kanji" if is_kanji(ch) else ("kana" if is_kana(ch) else "other")
        if t == current_type:
            current_chars.append(ch)
        else:
            if current_chars:
                blocks.append((current_type, "".join(current_chars)))
            current_type = t
            current_chars = [ch]
    if current_chars:
        blocks.append((current_type, "".join(current_chars)))

    # Case A: Pure kanji word (e.g. 赤道[せきどう])
    if len(blocks) == 1 and blocks[0][0] == "kanji":
        res = f"{w}[{r}]"
    # Case B: Kanji + Kana (e.g. 接[せっ]する, 迫[せま]る)
    elif len(blocks) == 2 and blocks[0][0] == "kanji" and blocks[1][0] == "kana":
        suffix = blocks[1][1]
        if r.endswith(suffix):
            stem_r = r[:-len(suffix)]
            res = f"{blocks[0][1]}[{stem_r}]{suffix}"
        else:
            res = f"{w}[{r}]"
    # Case C: Kana + Kanji (e.g. お 手本[てほん])
    elif len(blocks) == 2 and blocks[0][0] == "kana" and blocks[1][0] == "kanji":
        pref = blocks[0][1]
        if r.startswith(pref):
            stem_r = r[len(pref):]
            res = f"{pref} {blocks[1][1]}[{stem_r}]"
        else:
            res = f"{w}[{r}]"
    # Case D: Compound word with alternating kanji & kana (e.g. 抱[だ]き締[し]める, 立ち上がる)
    else:
        res_parts = []
        r_idx = 0
        failed = False
        for i, (b_type, b_text) in enumerate(blocks):
            if b_type == "kana":
                k_pos = r.find(b_text, r_idx)
                if k_pos == -1:
                    failed = True
                    break
                if i > 0 and blocks[i-1][0] == "kanji":
                    res_parts.append(f"{blocks[i-1][1]}[{r[r_idx:k_pos]}]")
                res_parts.append(b_text)
                r_idx = k_pos + len(b_text)

        if not failed:
            if blocks[-1][0] == "kanji":
                res_parts.append(f"{blocks[-1][1]}[{r[r_idx:]}]")
            res = "".join(res_parts)
        else:
            res = f"{w}[{r}]"

    if has_leading_tilde:
        res = f"～{res}"
    if has_trailing_tilde:
        res = f"{res}～"
    return res


def standardize_card_format(card: dict) -> tuple[dict, list[str]]:
    """Standardize card fields to eliminate format inconsistencies.

    Returns (updated_card_dict, list_of_changes).
    """
    updated = dict(card)
    changes = []

    # 1. Normalize Tildes across all text fields (～ U+FF5E is standard)
    for col in CARD_COLUMNS:
        val = updated.get(col, "")
        if isinstance(val, str) and ("〜" in val or (col in ("Word", "Reading", "Furigana", "GrammarPattern") and "~" in val)):
            new_val = val.replace("〜", "～").replace("~", "～")
            if new_val != val:
                changes.append(f"Normalized tilde in '{col}'")
                updated[col] = new_val

    # 2. Standardize POS (remove outer square brackets, standardize middle dots)
    pos = str(updated.get("POS", "")).strip()
    if pos.startswith("[") and pos.endswith("]"):
        pos = pos[1:-1].strip()
        changes.append("Removed outer brackets from POS")
    if "·" in pos: # Latin middle dot U+00B7
        pos = pos.replace("·", "・")
        changes.append("Converted Latin middle dot in POS to Japanese fullwidth middle dot")
    if pos != updated.get("POS"):
        updated["POS"] = pos

    # 3. Clean Loanword reading anomalies
    word = str(updated.get("Word", "")).strip()
    reading = str(updated.get("Reading", "")).strip()
    if word.startswith("トレイ（tray）") or word == "トレイ（tray）＝トレー":
        updated["Word"] = "トレイ（トレー）"
        updated["Reading"] = "トレイ"
        updated["Furigana"] = "トレイ"
        changes.append("Cleaned English note from 'トレイ' reading and furigana")
    elif word.startswith("ミリ (メートル)") or word == "ミリ (メートル)":
        updated["Word"] = "ミリ（メートル）"
        updated["Reading"] = "ミリ"
        updated["Furigana"] = "ミリ"
        changes.append("Cleaned parenthetical note from 'ミリ' reading and furigana")

    # 4. Standardize Furigana & Okurigana Separation
    cur_furi = str(updated.get("Furigana", "")).strip()
    cur_reading = str(updated.get("Reading", "")).strip()
    cur_word = str(updated.get("Word", "")).strip()

    expected_furi = generate_furigana(cur_word, cur_reading)
    # Clean internal spaces if present
    expected_furi = re.sub(r"\]\s+([^\s\[\]])", r"]\1", expected_furi)

    if cur_furi != expected_furi:
        changes.append(f"Standardized Furigana: '{cur_furi}' -> '{expected_furi}'")
        updated["Furigana"] = expected_furi

    # 5. Clean CSV Double Quote Escaping Artifacts
    for col in ("WordUsage", "GrammarMeaning", "GrammarUsage", "CombinationLogic"):
        val = str(updated.get(col, ""))
        if (val.startswith('"') and val.endswith('"')) or '""' in val:
            cleaned_val = val
            if cleaned_val.startswith('"') and cleaned_val.endswith('"'):
                cleaned_val = cleaned_val[1:-1].strip()
            # Replace double quotes inside Chinese text with standard quotes
            cleaned_val = cleaned_val.replace('""', '“')
            changes.append(f"Cleaned CSV quote artifacts from '{col}'")
            updated[col] = cleaned_val

    return updated, changes


def lint_card(card: dict) -> list[str]:
    """Perform fast local deterministic linting on a single card dict.

    Returns a list of issue descriptions (empty if perfectly valid).
    """
    issues = []

    # 1. Base schema validation
    base_errors = validate_card(card)
    issues.extend(base_errors)

    word = str(card.get("Word", "")).strip()
    reading = str(card.get("Reading", "")).strip()
    furigana = str(card.get("Furigana", "")).strip()
    pos = str(card.get("POS", "")).strip()
    sentence = str(card.get("Sentence", "")).strip()
    tags = str(card.get("Tags", "")).strip()

    # 2. POS format check
    if pos.startswith("[") and pos.endswith("]"):
        issues.append(f"POS has extraneous outer brackets: '{pos}'")
    if "·" in pos:
        issues.append(f"POS uses Latin middle dot '·' instead of Japanese '・': '{pos}'")

    # 3. Furigana bracket & syntax check
    if "[" in furigana or "]" in furigana:
        if furigana.count("[") != furigana.count("]"):
            issues.append(f"Mismatched furigana brackets in '{furigana}'")
        if re.search(r"\[\s*\]", furigana):
            issues.append(f"Empty furigana brackets in '{furigana}'")
        if re.search(r"\[[～〜~]", furigana):
            issues.append(f"Furigana bracket contains redundant tilde: '{furigana}'")

    # 4. Tags format check: standard is N2::Vocabulary N2::Grammar::<id>
    if tags and not re.match(r"^N2::(?:Vocabulary|Words\d*)\s+N2::Grammar::\w+$", tags):
        issues.append(f"Non-standard tag format: '{tags}'")

    # 5. Sentence length & content sanity
    if len(sentence) < 5:
        issues.append("Sentence is unusually short (< 5 characters)")

    # 6. Raw tabs check inside fields
    for col in CARD_COLUMNS:
        val = str(card.get(col, ""))
        if "\t" in val:
            issues.append(f"Raw tab character inside field '{col}'")
        if (val.startswith('"') and val.endswith('"')) or '""' in val:
            issues.append(f"CSV double-quote escaping artifact in field '{col}'")

    return issues

