# Japanese Anki Deck Generator & Management Pipeline 🎌

A comprehensive, production-grade Anki flashcard generation, normalization, and verification pipeline for Japanese vocabulary and grammar across multiple study tiers. Built strictly adhering to the [official Anki manual](https://docs.ankiweb.net/) standards, active recall principles, and modern responsive UI design.

---

## 🗂️ Managed Decks

| Deck Directory | Tier / Focus | Cards | Note Type | Deck Name in Anki | Status |
|---|---|---|---|---|---|
| **[`N2 Level/`](N2%20Level/)** | JLPT N2 Core Vocab & Grammar | **1,615** | `Japanese N2 Vocab & Grammar` | `日语::JLPT N2::N2 词汇与语法 (15字段高召回)` | ✓ 100% Verified |
| **[`N3_4_Level/`](N3_4_Level/)** | JLPT N3 & N4 Bridge | **556** | `Japanese N2 Vocab & Grammar` | `日语::JLPT N3-N4::词汇与语法` | ✓ 100% Verified |
| **[`Deck_2/`](Deck_2/)** | Minna no Nihongo (大家的日语) | **3,975** | `Japanese N2 Vocab & Grammar` | `日语::大家的日语::单词` | ✓ 100% Verified |

**Total Flashcards**: **6,146 cards** fully audited, 0 linting errors, 0 Simplified Chinese leaks, pure kana readings, and synchronized JSON ledgers.

---

## ✨ Design Principles

- **Active Recall Front Cards**: Front card displays strictly the target lemma (Kanji) and POS badge—no reading, furigana, or sentence spoilers before testing recognition.
- **Rich Contextual Back Cards**:
  - Accurate Furigana ruby markup (`{{furigana:Furigana}}` with okurigana placed outside brackets).
  - Clean definitions, authentic Japanese example sentences (Shinjitai orthography), and idiomatic translations.
  - Dedicated **Grammar Points** section aligning vocabulary with relevant grammar structures.
  - Collapsible `<details>` drawer for **Deep Nuance Analysis & Collocation Logic**.
  - Crisp vector SVG audio buttons replacing low-quality emojis and fixing native Anki double-outline SVG artifacts.
- **Native Night Mode**: Seamless theme switching matching Anki Desktop, AnkiMobile (iOS), and AnkiDroid.
- **Audio Drop Policy**: Standard audio fields (`WordAudio`, `SentenceAudio`) are intentionally formatted as empty strings `""` for lightweight offline usage and third-party TTS / audio add-on compatibility.

---

## 📁 Repository Structure

```text
anki-generator/
├── README.md                      # Master repository documentation
├── .gitignore                     # Git ignore rules for caches, envs, OS artifacts
├── .gitmodules                    # Submodule configuration for official anki-manual
├── anki-manual/                   # Upstream Anki documentation submodule
│
├── N2 Level/                      # JLPT N2 Core Deck (1,615 cards)
│   ├── deck.txt                   # Compiled master Anki TSV deck
│   ├── Words.json                 # Unified source vocabulary database
│   ├── Grammar.json               # JLPT N2 grammar points database
│   ├── template.txt               # Anki export header template
│   ├── batches/                   # Numbered word split files (Words1..10.json)
│   ├── card_template/             # Front/Back HTML templates, style.css & browser preview
│   ├── progress/cards/            # Card JSON ledgers (0000.json - 1614.json)
│   └── Source/                    # Raw vocabulary and grammar references
│
├── N3_4_Level/                    # JLPT N3/N4 Bridge Deck (556 cards)
│   ├── deck.txt                   # Compiled master Anki TSV deck
│   ├── Words.json                 # Ingested and enriched N3/N4 vocabulary database
│   ├── Grammar.json               # N3/N4 grammar points database
│   ├── template.txt               # Anki export header template
│   ├── pos_cache.json             # Jisho.org POS enrichment cache
│   ├── batches/                   # Subagent batch slices (batch_01..10.json)
│   ├── card_template/             # Card styling and interactive preview
│   └── progress/cards/            # Card JSON ledgers (0000.json - 0555.json)
│
├── Deck_2/                        # Minna no Nihongo (大家的日语) Deck (3,975 cards)
│   ├── deck.txt                   # Compiled master Anki TSV deck
│   ├── Words.json                 # Ingested and normalized vocabulary database
│   ├── Grammar.json               # Grammar references database
│   ├── template.txt               # Anki export header template
│   ├── batches/                   # Batch allocations (batch_01..40.json)
│   └── progress/cards/            # Card JSON ledgers (0000.json - 3974.json)
│
├── sources/                       # Canonical raw legacy notes
│   ├── Selected Notes.txt         # Raw notes for N2 & N3/N4 decks
│   └── Selected Notes 2.txt       # Raw notes for Minna no Nihongo (Deck 2)
│
├── progress/                      # Symlink -> N2 Level/progress/ (backward compatibility)
├── Selected Notes.txt             # Symlink -> sources/Selected Notes.txt
├── Selected Notes 2.txt           # Symlink -> sources/Selected Notes 2.txt
│
├── scripts/                       # Deck generators, compilers, and verification suites
│   ├── pipeline_lib.py            # Shared engine (ruby furigana, TSV parsing, LLM clients)
│   │
│   ├── [N2 Level Tools]
│   │   ├── build_deck.py          # Compiles N2 cards into N2 Level/deck.txt
│   │   ├── validate_deck.py       # Structural validator (15 TSV columns, headers)
│   │   ├── agent_verify_deck.py   # Offline linting for N2 deck
│   │   ├── verify_deck.py         # LLM verification loop (Gemini 3.8 Flash)
│   │   ├── generate_preview.py    # Generates interactive browser preview
│   │   ├── merge_words.py         # Merges N2 batches into Words.json
│   │   └── status.py              # Generation progress monitor
│   │
│   ├── [N3/N4 Level Tools]
│   │   ├── prepare_n3_4_words.py  # Ingests Selected Notes.txt -> N3_4_Level/Words.json
│   │   ├── enrich_pos_jisho.py    # Jisho.org POS enrichment pipeline
│   │   ├── generate_n3_4_deck.py  # LLM batch card generator
│   │   ├── build_n3_4_deck.py     # Compiles N3/N4 cards into deck.txt
│   │   ├── validate_n3_4_deck.py  # Structural validator for N3/N4 deck
│   │   ├── agent_verify_n3_4_deck.py # Deterministic offline linter
│   │   ├── verify_n3_4_deck.py    # Multi-pass LLM verifier
│   │   ├── generate_n3_4_preview.py # Preview generator
│   │   └── status_n3_4.py         # Generation progress monitor
│   │
│   ├── [Deck 2 Tools]
│   │   ├── prepare_deck_2_words.py# Ingests Selected Notes 2.txt -> Deck_2/Words.json
│   │   ├── generate_deck_2.py     # LLM batch card generator
│   │   ├── revise_deck_2.py       # Comprehensive syntax & ruby normalization engine
│   │   ├── build_deck_2.py        # Compiles Deck 2 cards into deck.txt
│   │   ├── agent_verify_deck_2.py # Deterministic offline linter
│   │   ├── verify_deck_2.py       # Multi-pass LLM verifier
│   │   └── status_deck_2.py       # Generation progress monitor
│   │
│   └── archive/                   # Historical patch scripts & one-off subagent generators
│       ├── README.md              # Detailed index of archived utilities
│       └── n3_4_batches/          # One-off batch generators for N3/N4 migration
│
└── tests/                         # Comprehensive unit test suite
    ├── test_pipeline.py           # Ruby bracket parsing, okurigana logic, audio drop tests
    ├── test_standardize_format.py # Format normalization tests
    ├── test_verify_deck.py        # API key resolution & linting tests
    ├── test_agent_verify_deck.py  # N2 deck offline linter integration test
    ├── test_n3_4_deck.py          # N3/N4 deck integrity test
    └── test_deck_2.py             # Deck 2 integrity & 3,975 card validation test
```

---

## 🚀 Quickstart & Verification

### 1. Run Complete Test Suite
Executes all 41 test cases across the entire pipeline:
```bash
python3 -m unittest discover tests
```

### 2. Verify Decks Offline
Each deck includes a fast, zero-dependency offline deterministic linter:
```bash
# N2 Core Deck (1,615 cards)
python3 scripts/validate_deck.py
python3 scripts/agent_verify_deck.py

# N3/N4 Bridge Deck (556 cards)
python3 scripts/validate_n3_4_deck.py
python3 scripts/agent_verify_n3_4_deck.py

# Minna no Nihongo / Deck 2 (3,975 cards)
python3 scripts/agent_verify_deck_2.py
```

### 3. Recompile Decks from Card JSONs
If you modify individual card JSON files under `progress/cards/`:
```bash
python3 scripts/build_deck.py        # Rebuilds N2 Level/deck.txt
python3 scripts/build_n3_4_deck.py   # Rebuilds N3_4_Level/deck.txt
python3 scripts/build_deck_2.py      # Rebuilds Deck_2/deck.txt
```

---

## 📇 Importing to Anki

All decks share the same production note type (`Japanese N2 Vocab & Grammar`) with 16 columns (15 content columns + 1 tags column):

1. **Columns**: `GUID`, `Word`, `Reading`, `Furigana`, `POS`, `Meaning`, `WordAudio`, `Sentence`, `SentenceAudio`, `SentenceTranslation`, `WordUsage`, `GrammarPattern`, `GrammarMeaning`, `GrammarUsage`, `CombinationLogic`, `Tags`.
2. In Anki Desktop, go to **File** > **Import...** and select any deck file (`N2 Level/deck.txt`, `N3_4_Level/deck.txt`, or `Deck_2/deck.txt`).
3. Anki will automatically recognize the headers (`#separator:tab`, `#html:true`, `#notetype`, `#guid column:1`, `#tags column:16`) and map all fields directly.
