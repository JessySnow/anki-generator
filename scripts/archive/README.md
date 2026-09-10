# Scripts Archive

This directory contains one-off data cleanup and patch scripts used during the initial generation and normalization of the N2 deck. They are preserved for auditability and historical reference.

## Historical Scripts

- `fix_deck.py`: Initial patch script mapping legacy grammar tags (e.g. `N2::Grammar::95` -> `121`) and fixing missing columns.
- `fix_deck_2.py`: Second-pass tag correction and typo fixes for target vocabulary.
- `fix_deck_3.py`: Batch grammar tag alignment and sentence punctuation normalization.
- `fix_deck_sort.py`: 50-on alphabetical sorting script based on the hiragana reading column.
- `fix_marude.py`: Targeted fix replacing kanji `丸で` with standard kana `まるで`.
- `fix_deck_final.py`: Final grammar index correction for `～のも無理はない`.
