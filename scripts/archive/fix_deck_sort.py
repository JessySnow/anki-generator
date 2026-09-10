def parse_line(line):
    return line.strip('\n').split('\t')

with open('N2 Level/deck_temp_2.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

headers = lines[:6]
content = lines[6:]

# Create a sort key function for 50-on order based on furigana.
# For simplicity, we just use the first few characters of the reading column (parts[1]).
# Wait, the user mentioned specific words being misplaced. Let's find them and move them.
# 1. 「明暗」「名医」「明記」: move before 「明確」
# 2. 「民家」: move before 「満開」 -> actually it should be in "mi" row.
# 3. 「沸く」「筆記」: abnormal insertion after 「仏道」

# Actually, the user says "在后半部分发生了明显的批量重复生成与排序混乱"
# If we just sort the whole file by the reading column (parts[1]), that would fix everything automatically!
# The reading column is the hiragana reading.

def sort_key(line_str):
    parts = line_str.strip('\n').split('\t')
    if len(parts) >= 2:
        return parts[1] # sorting by the reading (hiragana)
    return ""

# Let's sort only the content lines based on the reading column
content.sort(key=sort_key)

with open('N2 Level/deck.txt', 'w', encoding='utf-8') as f:
    f.writelines(headers)
    f.writelines(content)

