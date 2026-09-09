with open('N2 Level/deck.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.startswith("筆記\t"):
        parts = line.strip('\n').split('\t')
        if parts[10] == "～のも無理はない":
            parts[14] = parts[14].replace("N2::Grammar::138", "N2::Grammar::139") 
            lines[i] = '\t'.join(parts) + '\n'

with open('N2 Level/deck.txt', 'w', encoding='utf-8') as f:
    f.writelines(lines)
