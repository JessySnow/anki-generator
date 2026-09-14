#!/usr/bin/env python3
"""
scripts/merge_verify_caches.py - Merges partial verification caches from subagents into .verify_cache.json.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROGRESS_DIR = REPO_ROOT / "Deck_2" / "progress"
MAIN_CACHE = PROGRESS_DIR / ".verify_cache.json"

def main():
    main_data = {}
    if MAIN_CACHE.is_file():
        try:
            with open(MAIN_CACHE, "r", encoding="utf-8") as f:
                main_data = json.load(f)
        except Exception:
            main_data = {}

    part_files = sorted(PROGRESS_DIR.glob(".verify_cache_part*.json"))
    print(f"Found {len(part_files)} partial cache files.")
    for pf in part_files:
        try:
            with open(pf, "r", encoding="utf-8") as f:
                p_data = json.load(f)
                main_data.update(p_data)
            print(f"  Merged {len(p_data)} entries from {pf.name}")
            pf.unlink()
        except Exception as e:
            print(f"  Error reading {pf.name}: {e}")

    with open(MAIN_CACHE, "w", encoding="utf-8") as f:
        json.dump(main_data, f, ensure_ascii=False, indent=2)

    print(f"Total entries in main cache: {len(main_data)}")

if __name__ == "__main__":
    main()
