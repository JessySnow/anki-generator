import re

def fix_deck(file_path, output_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    out_lines = []
    
    # Mappings for tags
    tag_fixes = {
        "塞ぐ": ("N2::Grammar::95", "N2::Grammar::121"),
        "不作法": ("N2::Grammar::164", "N2::Grammar::179"),
        "ふと": ("N2::Grammar::4", "N2::Grammar::2"),
        "明暗": ("N2::Grammar::4", "N2::Grammar::2"),
        "丸で": ("N2::Grammar::125", "N2::Grammar::123"),
        "満期": ("N2::Grammar::125", "N2::Grammar::123"),
        "振り仮名": ("N2::Grammar::125", "N2::Grammar::123"),
        "もったいない": ("N2::Grammar::45", "N2::Grammar::113"),
        "最も": ("N2::Grammar::114", "N2::Grammar::131"),
        "尤も": ("N2::Grammar::85", "N2::Grammar::79"),
        "元々": ("N2::Grammar::141", "N2::Grammar::135"),
        "求める": ("N2::Grammar::12", "N2::Grammar::14"),
        "基づいて": ("N2::Grammar::142", "N2::Grammar::136"),
        "元手": ("N2::Grammar::134", "N2::Grammar::129"),
        "物音": ("N2::Grammar::130", "N2::Grammar::128"),
        "物語": ("N2::Grammar::140", "N2::Grammar::134"),
        "物語る": ("N2::Grammar::164", "N2::Grammar::175"),
        "物事": ("N2::Grammar::4", "N2::Grammar::3"),
        "物足りない": ("N2::Grammar::51", "N2::Grammar::19"),
        "籾": ("N2::Grammar::158", "N2::Grammar::18"),
        "催す": ("N2::Grammar::14", "N2::Grammar::25"),
        "文句": ("N2::Grammar::20", "N2::Grammar::31"),
        "門番": ("N2::Grammar::112", "N2::Grammar::117"),
        "夜明け": ("N2::Grammar::144", "N2::Grammar::138"),
        "酔う": ("N2::Grammar::121", "N2::Grammar::123"),
        "陽気": ("N2::Grammar::32", "N2::Grammar::70"),
        "用心": ("N2::Grammar::7", "N2::Grammar::5"),
        "様子": ("N2::Grammar::81", "N2::Grammar::78"),
        "要するに": ("N2::Grammar::160", "N2::Grammar::174"),
        "寄せる": ("N2::Grammar::10", "N2::Grammar::55"),
        "余計": ("N2::Grammar::71", "N2::Grammar::58"),
        "よす": ("N2::Grammar::88", "N2::Grammar::85"),
        "予測": ("N2::Grammar::145", "N2::Grammar::141"),
        "余暇": ("N2::Grammar::37", "N2::Grammar::70"),
        "夜更かし": ("N2::Grammar::111", "N2::Grammar::110"),
        "夜更け": ("N2::Grammar::16", "N2::Grammar::32"),
        "呼び掛ける": ("N2::Grammar::94", "N2::Grammar::97"),
        "呼び出す": ("N2::Grammar::13", "N2::Grammar::25"),
        "蘇る": ("N2::Grammar::116", "N2::Grammar::125"),
        "喜ぶ": ("N2::Grammar::5", "N2::Grammar::4"),
        "来日": ("N2::Grammar::148", "N2::Grammar::150"),
        "落第": ("N2::Grammar::149", "N2::Grammar::150"),
        "理科": ("N2::Grammar::84", "N2::Grammar::79"),
        "利害": ("N2::Grammar::155", "N2::Grammar::175"),
        "理解": ("N2::Grammar::25", "N2::Grammar::39"),
        "利口": ("N2::Grammar::162", "N2::Grammar::174"),
        "率直": ("N2::Grammar::65", "N2::Grammar::61"),
    }
    
    for i, line in enumerate(lines):
        if i < 6:
            out_lines.append(line.replace('〜', '～'))
            continue
            
        line = line.replace('〜', '～')
        
        parts = line.strip('\n').split('\t')
        if len(parts) != 15:
            out_lines.append(line)
            continue
            
        word = parts[0]
        
        # Issue 1: TSV quote cleanup
        if word in ["使い分け", "つかまる", "～付き"]:
            for col in [9, 11, 12, 13]:
                if col < len(parts):
                    # Replace multiple quotes and fix directions
                    val = parts[col]
                    val = val.replace('""', '')
                    val = val.replace('"', '')
                    val = val.replace('“', '「').replace('”', '」')
                    parts[col] = val
                    
        # Issue 2: POS column
        if word == "とはいいつつも":
            parts[3] = "接"
        elif word == "共":
            parts[3] = "名・接頭"
        elif word == "詫びる":
            parts[9] = parts[9].replace("他動詞。在句中作謂語「詫びる」", "在句中作他动词谓语")
            
        # Issue 3: Furigana syntax
        if word == "～料":
            parts[2] = "～料[りょう]"
        if word == "～っ子":
            parts[2] = parts[2].replace("っ 子[こ]", "っ子[こ]")
        if word == "ちり紙":
            parts[2] = parts[2].replace("り 紙[がみ]", "り紙[がみ]")
        if word == "にわか雨":
            parts[2] = parts[2].replace("か 雨[あめ]", "か雨[あめ]")
        
        if word == "混ざる / 交ざる":
            parts[2] = "混ざる[まざる]/交ざる[まざる]"
        if "混ぜる / 交ざる" in word or "混ぜる / 交ぜる" in word:
            parts[2] = "混ぜる[まぜる]/交ぜる[まぜる]"
            parts[0] = "混ぜる / 交ぜる"  # Correcting the typo as well if it was 交ざる
        if word == "的確/適確":
            parts[2] = "的確[てきかく]/適確[てきかく]"
        if word == "知能/智能":
            parts[2] = "知能[ちのう]/智能[ちのう]"
        if word == "羽/羽根":
            parts[2] = "羽[はね]/羽根[はね]"
        if word == "堀/濠":
            parts[2] = "堀[ほり]/濠[ほり]"
        if word == "偽物/贋物":
            parts[2] = "偽物[にせもの]/贋物[にせもの]"
            
        # Issue 4: Grammar Pattern and Tags
        if word == "噴き出す":
            parts[10] = "～きる/きれる/きれない"
            parts[14] = parts[14].replace("N2::Grammar::54", "N2::Grammar::41")
            
        if word == "ふざける":
            parts[14] = parts[14].replace("N2::Grammar::60", "N3::Grammar")
            
        if word == "節" and parts[1] == "ふし":
            parts[14] = parts[14].replace("N2::Grammar::61", "N3::Grammar")
            
        # Tag mismatch table
        clean_word = word.replace("(前)", "").replace("(后)", "")
        if word in tag_fixes:
            old_t, new_t = tag_fixes[word]
            parts[14] = parts[14].replace(old_t, new_t)
        elif clean_word in tag_fixes:
            old_t, new_t = tag_fixes[clean_word]
            parts[14] = parts[14].replace(old_t, new_t)
            
        # Issue 5: Example sentences
        if word == "老ける":
            parts[6] = parts[6].replace("早く老けるのを防ぐ", "老化を防ぐ")
            parts[8] = parts[8].replace("早变老", "老化")
        if word == "打つ" or word == "ぶつ":
            if parts[1] == "ぶつ":
                parts[0] = "ぶつ"
                parts[2] = "ぶつ[ぶつ]"
                parts[6] = parts[6].replace("打つ", "ぶつ")
                parts[9] = parts[9].replace("「打つ（ぶつ）」", "「ぶつ」").replace("相手を打つ", "相手をぶつ")
                parts[12] = parts[12].replace("相手を打つ", "相手をぶつ")
                parts[13] = parts[13].replace("相手を打つ", "相手をぶつ")
        if word == "尽きる":
            parts[6] = parts[6].replace("体力が尽きる尽きないにかかわらず", "疲れを感じる感じないにかかわらず")
        if word == "丸で" or word == "まるで":
            parts[0] = "まるで"
            parts[2] = "まるで[まるで]"
            
        out_lines.append('\t'.join(parts) + '\n')
        
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

fix_deck('N2 Level/deck.txt', 'N2 Level/deck.txt')
