with open('N2 Level/deck.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(len(lines)):
    if lines[i].startswith("まるで\t"):
        parts = lines[i].split("\t")
        for j in range(6, 14):
            parts[j] = parts[j].replace("丸で", "まるで")
        lines[i] = "\t".join(parts)
with open('N2 Level/deck.txt', 'w', encoding='utf-8') as f:
    f.writelines(lines)
