import sys

def validate(file_path):
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
        if not lines[i].strip() == expected:
            errors.append(f"Header line {i+1} mismatch. Expected:\n{expected}\nGot:\n{lines[i].strip()}")
            
    for idx, line in enumerate(lines[6:], start=7):
        parts = line.strip('\n').split('\t')
        if len(parts) != 15:
            errors.append(f"Line {idx} has {len(parts)} columns instead of 15. First part: {parts[0] if parts else 'empty'}")
            
    if not errors:
        print("All requirements met: 15 columns per card, correct headers.")
    else:
        for err in errors[:20]:
            print(err)
        if len(errors) > 20:
            print(f"... and {len(errors) - 20} more errors.")
            
validate('N2 Level/deck.txt')
