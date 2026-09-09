import re
import json

def get_cards(words):
    cards = []
    with open('N2 Level/deck.txt', 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#'): continue
            parts = line.strip('\n').split('\t')
            if len(parts) >= 15 and parts[0] in words:
                cards.append(parts)
    return cards

cards_data = get_cards(['ぶつ', 'ふざける', 'まるで', '老ける', '噴き出す'])

# We need to construct a javascript array of objects for these cards
js_data = []
for parts in cards_data:
    card = {
        'word': parts[0],
        'pos': parts[3],
        'sentence': parts[6],
        'translation': parts[8],
        'furigana': parts[2],
        'meaning': parts[4],
        'sentence_jp': parts[6],
        'sentence_zh': parts[8],
        'grammar_pattern': parts[10],
        'grammar_meaning': parts[11],
        'grammar_usage': parts[12],
        'word_usage': parts[9],
        'combination_logic': parts[13],
        'tags': parts[14]
    }
    js_data.append(card)

# Read original preview.html for styles and structure
with open('N2 Level/card_template/preview.html', 'r', encoding='utf-8') as f:
    html = f.read()

# We will inject our data and script to update the DOM
# First, add a select dropdown to the toolbar
toolbar_html = """
  <div class="preview-toolbar">
    <select id="card-selector" onchange="loadCard(this.value)" style="padding: 6px; border-radius: 6px; border: 1px solid #cbd5e1;">
      <!-- Options will be injected -->
    </select>
    <button class="preview-btn active" id="btn-front" onclick="showCard('front')">Front (Question)</button>
    <button class="preview-btn" id="btn-back" onclick="showCard('back')">Back (Answer)</button>
    <button class="preview-btn" id="btn-theme" onclick="toggleTheme()">Toggle Night Mode</button>
  </div>
"""

html = re.sub(r'<div class="preview-toolbar">.*?</div>', toolbar_html, html, flags=re.DOTALL)

# Now inject the javascript
script_injection = f"""
  <script>
    const cardsData = {json.dumps(js_data, ensure_ascii=False)};
    
    function initCards() {{
        const selector = document.getElementById('card-selector');
        cardsData.forEach((card, index) => {{
            const opt = document.createElement('option');
            opt.value = index;
            opt.textContent = card.word;
            selector.appendChild(opt);
        }});
        if(cardsData.length > 0) loadCard(0);
    }}
    
    function parseFurigana(furiStr) {{
        // Very basic parsing for Word[furigana] format
        // Example: ぶつ[ぶつ] -> <ruby>ぶつ<rt>ぶつ</rt></ruby>
        let result = furiStr;
        const regex = /([^\[\]]+)\[([^\[\]]+)\]/g;
        return result.replace(regex, '<ruby>$1<rt>$2</rt></ruby>');
    }}
    
    function loadCard(index) {{
        const card = cardsData[index];
        if(!card) return;
        
        // Front
        document.querySelectorAll('.word-main').forEach(el => el.textContent = card.word);
        document.querySelectorAll('.pos-pill').forEach(el => el.textContent = card.pos);
        document.querySelectorAll('.sentence-text').forEach(el => el.textContent = card.sentence);
        document.getElementById('demo-hint').textContent = card.translation;
        
        // Back
        document.querySelector('.furigana-title').innerHTML = parseFurigana(card.furigana);
        document.querySelector('.meaning-text').textContent = card.meaning;
        document.querySelector('.sentence-jp').innerHTML = card.sentence_jp + ' <span class="replay-button-mock" title="Replay sentence audio">🔊</span>';
        document.querySelector('.sentence-zh').textContent = card.sentence_zh;
        document.querySelector('.grammar-pattern').textContent = card.grammar_pattern;
        document.querySelector('.grammar-meaning').textContent = card.grammar_meaning;
        document.querySelector('.grammar-usage-text').textContent = card.grammar_usage;
        document.querySelector('.tags-pill').textContent = card.tags;
        
        // Analysis
        const analysisHtml = `
            <div class="analysis-item">
                <span class="item-title">词汇用法：</span>${{card.word_usage}}
            </div>
            <div class="analysis-item">
                <span class="item-title">语境逻辑：</span>${{card.combination_logic}}
            </div>
        `;
        document.querySelector('.analysis-body').innerHTML = analysisHtml;
        
        // Reset view to front
        showCard('front');
    }}

    function showCard(view) {{
      const front = document.getElementById('front-view');
      const back = document.getElementById('back-view');
      const btnFront = document.getElementById('btn-front');
      const btnBack = document.getElementById('btn-back');

      if (view === 'front') {{
        front.style.display = 'block';
        back.style.display = 'none';
        btnFront.classList.add('active');
        btnBack.classList.remove('active');
      }} else {{
        front.style.display = 'none';
        back.style.display = 'block';
        btnBack.classList.add('active');
        btnFront.classList.remove('active');
      }}
    }}

    function toggleTheme() {{
      const card = document.getElementById('main-card');
      const body = document.body;
      card.classList.toggle('nightMode');
      body.classList.toggle('dark-theme');
    }}
    
    window.onload = initCards;
  </script>
"""

html = re.sub(r'<script>.*?</script>', script_injection, html, flags=re.DOTALL)

with open('N2 Level/card_template/preview_updated.html', 'w', encoding='utf-8') as f:
    f.write(html)
