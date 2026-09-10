import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def validate(file_path):
    file_path = Path(file_path)
    if not file_path.is_file():
        print(f"Error: file not found at {file_path}", file=sys.stderr)
        return 1

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    errors = []
    
    # headers
    expected_header_start = [
        "#separator:tab",
        "#html:true",
        "#notetype:Japanese N2 Vocab & Grammar",
        "#deck:Japanese::JLPT N2",
        "#tags column:15",
        "#columns:Word\tReading\tFurigana\tPOS\tMeaning\tWordAudio\tSentence\tSentenceAudio\tSentenceTranslation\tWordUsage\tGrammarPattern\tGrammarMeaning\tGrammarUsage\tCombinationLogic\tTags"
    ]
    
    for i, expected in enumerate(expected_header_start):
        if i >= len(lines) or not lines[i].strip() == expected:
            actual = lines[i].strip() if i < len(lines) else "EOF"
            errors.append(f"Header line {i+1} mismatch. Expected:\n{expected}\nGot:\n{actual}")
            
    for idx, line in enumerate(lines[6:], start=7):
        parts = line.strip('\n').split('\t')
        if len(parts) != 15:
            errors.append(f"Line {idx} has {len(parts)} columns instead of 15. First part: {parts[0] if parts else 'empty'}")
            
    if not errors:
        print(f"All requirements met: {len(lines) - 6} cards, 15 columns per card, correct headers.")
        return 0
    else:
        for err in errors[:20]:
            print(err)
        if len(errors) > 20:
            print(f"... and {len(errors) - 20} more errors.")
        return 1

if __name__ == '__main__':
    deck_path = sys.argv[1] if len(sys.argv) > 1 else REPO_ROOT / 'N2 Level' / 'deck.txt'
    sys.exit(validate(deck_path))

