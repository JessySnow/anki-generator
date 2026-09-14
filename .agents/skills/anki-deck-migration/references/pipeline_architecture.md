# Anki Deck Migration Architecture & Technical Reference

## Pipeline File Manifest

| File Path | Role | Key Function |
| :--- | :--- | :--- |
| `scripts/pipeline_lib.py` | Shared Library | Provider resolution, `GeminiClient`, `RateLimiter`, TSV formatting, card schema validation |
| `scripts/prepare_n3_4_words.py` | Normalization | Ingests `Selected Notes.txt`, maps V2 corruptions, enriches POS from cache, generates `Words.json` |
| `scripts/enrich_pos_jisho.py` | POS Enrichment | Jisho.org API integration with exponential backoff and caching in `pos_cache.json` |
| `scripts/generate_n3_4_deck.py` | Gemini 3.8 Generation | Bulk / batch card generation using Gemini 3.8 Flash via Google AI Studio API |
| `scripts/build_n3_4_deck.py` | Compiler | Merges `template.txt` header block and `cards/*.json` into `N3_4_Level/deck.txt` |
| `scripts/validate_n3_4_deck.py` | Schema Validator | Asserts 556 notes, 16 TSV columns, GUID match, empty audio strings |
| `scripts/agent_verify_n3_4_deck.py` | Deterministic Linter | Fast offline linter checking Shinjitai kanji, lemma inflection, ruby formatting |
| `scripts/verify_n3_4_deck.py` | Verification Loop | Multi-pass linguistic review and patch loop powered by Gemini 3.8 Flash |
| `scripts/status_n3_4.py` | Status Monitor | Instant progress checking for generated card counts and missing index ranges |

## Authentication Precedence

`scripts/pipeline_lib.py:load_gemini_api_key()` checks keys in the following priority order:
1. `~/.zshrc` (highest priority to detect interactive updates in active shell sessions)
2. `GOOGLE_API_KEY` / `GEMINI_API_KEY` environment variables
3. Local `.env` in repository root
4. `OPENROUTER_API_KEY` environment variable (as secondary fallback)
