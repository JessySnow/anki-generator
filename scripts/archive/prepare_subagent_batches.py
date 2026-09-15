#!/usr/bin/env python3
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORDS_PATH = REPO_ROOT / "N3_4_Level" / "Words.json"
SCRATCH_DIR = Path("/Users/jessy/.gemini/antigravity-cli/brain/3abb8178-8eed-4291-a9d9-73b17c24edb7/scratch/batches")
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

with open(WORDS_PATH, "r", encoding="utf-8") as f:
    words = json.load(f)["vocabulary_list"]

ranges = [
    (1, 3, 59),
    (2, 59, 115),
    (3, 115, 171),
    (4, 171, 227),
    (5, 227, 283),
    (6, 283, 339),
    (7, 339, 395),
    (8, 395, 451),
    (9, 451, 507),
    (10, 507, 556)
]

for b_id, start, end in ranges:
    batch_words = words[start:end]
    batch_file = SCRATCH_DIR / f"batch_{b_id:02d}.json"
    with open(batch_file, "w", encoding="utf-8") as f:
        json.dump(batch_words, f, ensure_ascii=False, indent=2)
    print(f"Batch {b_id:02d}: indices {start:03d}-{end-1:03d} ({len(batch_words)} words) -> {batch_file}")

