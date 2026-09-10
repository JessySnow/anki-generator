# JLPT N2 Anki Deck Generator 🎌

A comprehensive, production-grade Anki card generator and management pipeline for **JLPT N2 Vocabulary & Grammar**. Built strictly adhering to the [official Anki manual](https://docs.ankiweb.net/) standards, active recall principles, and modern responsive UI design.

---

## ✨ Features

- **Active Recall by Default**: Front card displays strictly the target word (Kanji) and POS pill—no reading or sentence spoilers before testing recognition.
- **Rich Contextual Back Cards**:
  - Accurate Furigana ruby formatting (`{{furigana:Furigana}}` with okurigana placed outside ruby brackets).
  - Highlighting for definitions, example sentences, and translations.
  - Dedicated **Grammar Points** section aligning vocabulary with N2/N3 grammatical structures.
  - Collapsible `<details>` section for **Deep Nuance Analysis & Collocation Logic**.
  - Crisp vector SVG audio buttons replacing low-quality emojis and fixing Anki's native double-outline SVG artifacts.
- **Dark Mode / Night Mode**: Seamless dynamic theme support matching Anki Desktop, AnkiMobile (iOS), and AnkiDroid without hardcoded inline overrides.
- **100% Verified & Deterministic**: Full unit test coverage and offline agent linting across all **1,615 curated N2 entries**, sorted in standard Japanese 50-on alphabetical order.
- **Interactive Browser Preview**: Zero-dependency standalone HTML previewer featuring word switching, flip animation, night mode toggle, and keyboard shortcuts (<kbd>Space</kbd>, <kbd>D</kbd>, <kbd>↑</kbd>/<kbd>↓</kbd>).

---

## 📁 Repository Structure

```text
anki-generator/
├── README.md                      # Project documentation and guide
├── .gitignore                     # Git ignore rules for caches, envs, OS artifacts
├── .gitmodules                    # Submodule configuration for official anki-manual
├── anki-manual/                   # Upstream Anki documentation submodule
├── N2 Level/
│   ├── deck.txt                   # Master Anki TSV deck (1,615 cards, 15 fields)
│   ├── template.txt               # Anki export header template
│   ├── Words.json                 # Unified source vocabulary database
│   ├── Grammar.json               # JLPT grammar points database
│   ├── card_template/             # Production card templates & styling
│   │   ├── front.html             # Front card HTML template
│   │   ├── back.html              # Back card HTML template
│   │   ├── style.css              # Card CSS (Variables, Night Mode, Mobile responsive)
│   │   ├── preview.html           # Interactive browser preview
│   │   └── README.md              # Template configuration instructions
│   └── Source/                    # Raw source vocabulary and grammar materials
├── progress/
│   └── cards/                     # Individual JSON card files (0000.json - 1614.json)
├── scripts/
│   ├── build_deck.py              # Compiles progress/cards/*.json into N2 Level/deck.txt
│   ├── generate_preview.py        # Generates N2 Level/card_template/preview.html
│   ├── validate_deck.py           # Fast structural & column validator for deck.txt
│   ├── agent_verify_deck.py       # Offline linting (Furigana, POS, Hanzi vs Kanji check)
│   ├── verify_deck.py             # Gemini-assisted semantic & linguistic verifier
│   ├── pipeline_lib.py            # Shared pipeline utilities, parsing & ruby generation
│   ├── get_batch.py               # Batch processor for card generation
│   ├── record_card.py             # Card recorder for progress tracking
│   ├── merge_words.py             # Vocabulary file merger utility
│   ├── pick_grammar.py            # Grammar selection helper
│   ├── status.py                  # Generation progress reporter
│   └── archive/                   # Historical one-off migration and patch scripts
└── tests/
    ├── test_agent_verify_deck.py  # Offline agent integrity test suite
    ├── test_pipeline.py           # Pipeline parsing, formatting, and ruby tests
    ├── test_standardize_format.py # Format normalization test suite
    └── test_verify_deck.py        # Verification loop & error handling tests
```

---

## 🚀 Quickstart & Workflows

### 1. Run the Test Suite
Ensure full system integrity and bidirectional card synchronization:
```bash
python3 -m unittest discover tests
```

### 2. Validate Deck Structure
Verify headers, 15-column format, and card counts:
```bash
python3 scripts/validate_deck.py
```

### 3. Run Offline Agent Verification
Check Japanese Shinjitai (no Simplified Chinese typos), valid inflections, ruby spacing, and tags:
```bash
python3 scripts/agent_verify_deck.py
```

### 4. Update the Card Preview
Regenerate the interactive browser preview with latest CSS or data:
```bash
python3 scripts/generate_preview.py
# Open N2 Level/card_template/preview.html in your browser
```

### 5. Compile Deck from JSON Cards
When modifying card JSON files in `progress/cards/`:
```bash
python3 scripts/build_deck.py
```

---

## 📇 Applying to Anki

### Step 1: Create Note Type in Anki
1. In Anki Desktop, go to **Tools** > **Manage Note Types** > **Add**.
2. Select **Add: Basic**, and name it `Japanese N2 Vocab & Grammar`.
3. Click **Fields...** and set up the **15 fields** in this exact order:
   1. `Word`
   2. `Reading`
   3. `Furigana`
   4. `POS`
   5. `Meaning`
   6. `WordAudio`
   7. `Sentence`
   8. `SentenceAudio`
   9. `SentenceTranslation`
   10. `WordUsage`
   11. `GrammarPattern`
   12. `GrammarMeaning`
   13. `GrammarUsage`
   14. `CombinationLogic`
   15. `Tags`

### Step 2: Configure Card Templates
1. In Note Types, click **Cards...**:
   - Paste [`front.html`](N2%20Level/card_template/front.html) into **Front Template**.
   - Paste [`back.html`](N2%20Level/card_template/back.html) into **Back Template**.
   - Paste [`style.css`](N2%20Level/card_template/style.css) into **Styling**.
2. Save and close.

### Step 3: Import the Deck
1. Go to **File** > **Import...** and select [`N2 Level/deck.txt`](N2%20Level/deck.txt).
2. Anki 2.1.54+ will automatically recognize the headers (`#separator:tab`, `#notetype`, `#columns`) and map every column directly to the card.
