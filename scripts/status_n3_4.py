#!/usr/bin/env python3
"""Check generation status for N3_4_Level cards."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CARDS_DIR = REPO_ROOT / "N3_4_Level" / "progress" / "cards"
TOTAL = 556

def main():
    existing = set()
    if CARDS_DIR.is_dir():
        for p in CARDS_DIR.glob("*.json"):
            try:
                existing.add(int(p.stem))
            except ValueError:
                pass

    count = len(existing)
    pct = (count / TOTAL) * 100
    print(f"Progress: {count} / {TOTAL} cards completed ({pct:.1f}%)")

    missing = sorted(set(range(TOTAL)) - existing)
    if missing:
        ranges = []
        start = missing[0]
        prev = start
        for m in missing[1:]:
            if m == prev + 1:
                prev = m
            else:
                ranges.append(f"{start}-{prev}" if start != prev else f"{start}")
                start = m
                prev = m
        ranges.append(f"{start}-{prev}" if start != prev else f"{start}")
        print(f"Missing indices: {', '.join(ranges[:10])}{' ...' if len(ranges) > 10 else ''}")

if __name__ == "__main__":
    main()
