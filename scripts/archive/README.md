# Scripts Archive

This directory contains one-off generation, data cleanup, and patch scripts used during the initial generation, batching, and normalization of the Anki decks. They are preserved for auditability and historical reference.

## Historical Patch & Fix Scripts

- `fix_deck.py`: Initial patch script mapping legacy grammar tags (e.g. `N2::Grammar::95` -> `121`) and fixing missing columns.
- `fix_deck_2.py`: Second-pass tag correction and typo fixes for target vocabulary.
- `fix_deck_3.py`: Batch grammar tag alignment and sentence punctuation normalization.
- `fix_deck_sort.py`: 50-on alphabetical sorting script based on the hiragana reading column.
- `fix_marude.py`: Targeted fix replacing kanji `丸で` with standard kana `まるで`.
- `fix_deck_final.py`: Final grammar index correction for `～のも無理はない`.
- `apply_agent_review.py`: One-off review applier for Deck 2 card evaluations.
- `merge_verify_caches.py`: Merge tool for distributed verification cache shards.
- `prepare_subagent_batches.py`: Temporary slicer script for N3/N4 subagent allocations.

## Subagent Batch Generators (`n3_4_batches/`)

Contains one-off subagent generation scripts used during concurrent batch generation for the N3/N4 deck (556 cards):
- `generate_batch_01.py` through `generate_batch_09.py`
- `batch_06_part1.py`, `batch_06_part2.py`
- `batch_09_part1.py`, `batch_09_part2.py`
- `batch_10_part1.py`, `batch_10_part2.py`
- `build_batch_03_data.py`
