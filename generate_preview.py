import re
import json
import os

def get_cards(sample_words):
    cards = []
    deck_path = os.path.join(os.path.dirname(__file__), 'N2 Level', 'deck.txt')
    found_words = set()
    with open(deck_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip('\n').split('\t')
            if len(parts) >= 15 and parts[0] in sample_words and parts[0] not in found_words:
                cards.append(parts)
                found_words.add(parts[0])
    return cards

sample_words = ['真剣', '赤道', 'ぶつ', 'ふざける', 'まるで', '老ける', '噴き出す', 'せっせと']
cards_data = get_cards(sample_words)

js_data = []
for parts in cards_data:
    card = {
        'word': parts[0],
        'reading': parts[1],
        'furigana': parts[2],
        'pos': parts[3],
        'meaning': parts[4],
        'word_audio': parts[5] if len(parts) > 5 else '',
        'sentence': parts[6],
        'sentence_audio': parts[7] if len(parts) > 7 else '',
        'sentence_zh': parts[8],
        'word_usage': parts[9],
        'grammar_pattern': parts[10],
        'grammar_meaning': parts[11],
        'grammar_usage': parts[12],
        'combination_logic': parts[13],
        'tags': parts[14] if len(parts) > 14 else 'N2::Vocabulary'
    }
    js_data.append(card)

# Read style.css
style_path = os.path.join(os.path.dirname(__file__), 'N2 Level', 'card_template', 'style.css')
with open(style_path, 'r', encoding='utf-8') as f:
    css_content = f.read()

html_template = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Anki Card Preview - Japanese N2 Vocab &amp; Grammar</title>
  <style>
    /* Global Preview Page Wrapper */
    body {{
      margin: 0;
      padding: 32px 16px;
      background: #e2e8f0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-height: 100vh;
      box-sizing: border-box;
      transition: background-color 0.3s ease;
    }}
    body.dark-theme {{
      background: #060911;
    }}
    .preview-header {{
      text-align: center;
      margin-bottom: 20px;
    }}
    .preview-title {{
      font-size: 20px;
      font-weight: 700;
      color: #1e293b;
      margin: 0 0 6px 0;
      letter-spacing: -0.01em;
      transition: color 0.3s;
    }}
    body.dark-theme .preview-title {{
      color: #f1f5f9;
    }}
    .preview-subtitle {{
      font-size: 13px;
      color: #64748b;
      margin: 0;
      transition: color 0.3s;
    }}
    body.dark-theme .preview-subtitle {{
      color: #94a3b8;
    }}
    .preview-toolbar {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: center;
      gap: 10px;
      margin-bottom: 24px;
      background: #ffffff;
      padding: 8px 16px;
      border-radius: 40px;
      box-shadow: 0 4px 16px rgba(15, 23, 42, 0.08);
      border: 1px solid #cbd5e1;
      transition: all 0.3s ease;
    }}
    body.dark-theme .preview-toolbar {{
      background: #131b2e;
      border-color: rgba(255, 255, 255, 0.1);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    }}
    .preview-select {{
      padding: 6px 14px;
      border-radius: 20px;
      border: 1px solid #cbd5e1;
      background: #f8fafc;
      color: #1e293b;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      outline: none;
      transition: all 0.2s;
    }}
    body.dark-theme .preview-select {{
      background: #1e293b;
      color: #f1f5f9;
      border-color: #475569;
    }}
    .preview-btn {{
      padding: 6px 16px;
      border-radius: 20px;
      border: 1px solid #cbd5e1;
      background: #ffffff;
      color: #334155;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
      user-select: none;
    }}
    .preview-btn:hover {{
      background: #f1f5f9;
      color: #0f172a;
    }}
    .preview-btn.active {{
      background: #2563eb;
      color: #ffffff;
      border-color: #2563eb;
      box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
    }}
    body.dark-theme .preview-btn {{
      background: #1e293b;
      color: #cbd5e1;
      border-color: #475569;
    }}
    body.dark-theme .preview-btn:hover {{
      background: #28354e;
      color: #f8fafc;
    }}
    body.dark-theme .preview-btn.active {{
      background: #60a5fa;
      color: #0b0f19;
      border-color: #60a5fa;
      box-shadow: 0 2px 10px rgba(96, 165, 250, 0.4);
    }}
    .card-frame {{
      width: 100%;
      max-width: 660px;
    }}
    .keyboard-hint {{
      margin-top: 20px;
      font-size: 12px;
      color: #64748b;
      text-align: center;
    }}
    body.dark-theme .keyboard-hint {{
      color: #94a3b8;
    }}
    kbd {{
      background: #e2e8f0;
      border: 1px solid #cbd5e1;
      border-radius: 4px;
      padding: 2px 6px;
      font-family: monospace;
      font-size: 11px;
    }}
    body.dark-theme kbd {{
      background: #1e293b;
      border-color: #475569;
      color: #f1f5f9;
    }}

    /* ==========================================================================
       ACTUAL ANKI CARD CSS (from card_template/style.css)
       ========================================================================== */
{css_content}
  </style>
</head>
<body>

  <div class="preview-header">
    <h1 class="preview-title">Japanese N2 Card Template Preview</h1>
    <p class="preview-subtitle">Front: Target Word &amp; POS (No Sentence Spoilers) &nbsp;|&nbsp; Back: Reading, Meaning, Sentence &amp; Grammar</p>
  </div>

  <!-- Interactive Controls -->
  <div class="preview-toolbar">
    <label for="card-selector" style="font-size: 12px; font-weight: 600; color: #64748b;">Word:</label>
    <select id="card-selector" class="preview-select" onchange="loadCard(this.value)">
      <!-- Options injected by JS -->
    </select>
    <button class="preview-btn active" id="btn-front" onclick="showCard('front')">Front (Question)</button>
    <button class="preview-btn" id="btn-back" onclick="showCard('back')">Back (Answer)</button>
    <button class="preview-btn" id="btn-theme" onclick="toggleTheme()">🌙 Night Mode</button>
  </div>

  <div class="card-frame">
    <div class="card" id="main-card">

      <!-- FRONT CARD VIEW -->
      <div id="front-view">
        <div class="card-box front-card">
          <div class="deck-tag">Japanese::JLPT N2</div>

          <div class="word-container">
            <div class="word-main" id="front-word"></div>
            <div class="pos-pill" id="front-pos"></div>
          </div>
        </div>
      </div>

      <!-- BACK CARD VIEW (Contains {{FrontSide}} + <hr id="answer"> + Back) -->
      <div id="back-view" style="display: none;">
        <!-- Front side included on top ({{FrontSide}}) -->
        <div class="card-box front-card">
          <div class="deck-tag">Japanese::JLPT N2</div>
          <div class="word-container">
            <div class="word-main" id="back-front-word"></div>
            <div class="pos-pill" id="back-front-pos"></div>
          </div>
        </div>

        <hr id="answer">

        <!-- Back Template -->
        <div class="card-box back-card">
          <div class="reading-row">
            <!-- 日语目标词汇与注音 -->
            <div class="furigana-title" id="back-furigana"></div>
          </div>

          <div class="meaning-section">
            <div class="badge-label"><span class="badge-icon">💡</span> 释义</div>
            <div class="meaning-text" id="back-meaning"></div>
          </div>

          <div class="sentence-detail-section">
            <div class="badge-label"><span class="badge-icon">📖</span> 例句解析</div>
            <div class="sentence-jp" id="back-sentence-jp"></div>
            <div class="sentence-zh" id="back-sentence-zh"></div>
          </div>

          <div class="grammar-section">
            <div class="badge-label grammar-label"><span class="badge-icon">✨</span> 语法重点</div>
            <div class="grammar-header">
              <span class="grammar-pattern" id="back-grammar-pattern"></span>
              <span class="grammar-meaning" id="back-grammar-meaning"></span>
            </div>
            <div class="grammar-usage-text" id="back-grammar-usage"></div>
          </div>

          <details class="analysis-details" open>
            <summary>深入解析与语境逻辑</summary>
            <div class="analysis-body" id="back-analysis-body">
              <!-- Injected by JS -->
            </div>
          </details>

          <div class="tags-row">
            <span class="tags-pill" id="back-tags"></span>
          </div>
        </div>
      </div>

    </div>
  </div>

  <div class="keyboard-hint">
    快捷键: <kbd>Space</kbd> 切换正/反面 &nbsp;|&nbsp; <kbd>D</kbd> 切换暗色模式 &nbsp;|&nbsp; <kbd>↑</kbd>/<kbd>↓</kbd> 切换单词
  </div>

  <script>
    const cardsData = {json.dumps(js_data, ensure_ascii=False)};
    let currentView = 'front';
    let currentIndex = 0;

    function initCards() {{
      const selector = document.getElementById('card-selector');
      cardsData.forEach((card, index) => {{
        const opt = document.createElement('option');
        opt.value = index;
        opt.textContent = `${{card.word}} (${{card.meaning}})`;
        selector.appendChild(opt);
      }});
      if (cardsData.length > 0) {{
        loadCard(0);
      }}
    }}

    function parseFurigana(furiStr) {{
      if (!furiStr) return '';
      // Parses Word[reading] into ruby: e.g. 真剣[しんけん] -> <ruby>真剣<rt>しんけん</rt></ruby>
      const regex = /([^\\s\\[\\]]+)\\[([^\\]]+)\\]/g;
      return furiStr.replace(regex, '<ruby>$1<rt>$2</rt></ruby>');
    }}



    function extractKanjiOnly(furiStr, fallbackWord) {{
      if (!furiStr) return fallbackWord || '';
      // Removes [reading] ruby bracket: e.g. 真剣[しんけん] -> 真剣
      return furiStr.replace(/\[[^\]]+\]/g, '');
    }}

    function loadCard(index) {{
      currentIndex = parseInt(index, 10);
      const card = cardsData[currentIndex];
      if (!card) return;

      const selector = document.getElementById('card-selector');
      if (selector.value != currentIndex) selector.value = currentIndex;

      // Front: Word only (kanji without furigana spoiler) + POS
      const wordText = extractKanjiOnly(card.furigana, card.word);
      document.getElementById('front-word').textContent = wordText;
      document.getElementById('front-pos').textContent = card.pos;

      // Back FrontSide clone
      document.getElementById('back-front-word').textContent = wordText;
      document.getElementById('back-front-pos').textContent = card.pos;

      const speakerSvg = `<span class="replay-button-mock" title="播放发音" onclick="mockPlayAudio()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" fill="currentColor"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg></span>`;
      document.getElementById('back-furigana').innerHTML = parseFurigana(card.furigana) + ' ' + speakerSvg;
      document.getElementById('back-meaning').textContent = card.meaning;
      document.getElementById('back-sentence-jp').innerHTML = card.sentence + ' ' + speakerSvg;
      document.getElementById('back-sentence-zh').textContent = card.sentence_zh;

      document.getElementById('back-grammar-pattern').textContent = card.grammar_pattern;
      document.getElementById('back-grammar-meaning').textContent = card.grammar_meaning ? `（${{card.grammar_meaning}}）` : '';
      document.getElementById('back-grammar-usage').textContent = card.grammar_usage;

      document.getElementById('back-tags').textContent = card.tags;

      // Analysis Section
      const analysisHtml = `
        <div class="analysis-item">
          <span class="item-title">词汇用法</span>
          <div class="item-content">${{card.word_usage}}</div>
        </div>
        ${{card.combination_logic ? `
        <div class="analysis-item">
          <span class="item-title">语境逻辑</span>
          <div class="item-content">${{card.combination_logic}}</div>
        </div>` : ''}}
      `;
      document.getElementById('back-analysis-body').innerHTML = analysisHtml;

      // Keep current view or default to front
      showCard(currentView);
    }}

    function showCard(view) {{
      currentView = view;
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
      const btn = document.getElementById('btn-theme');
      if (body.classList.contains('dark-theme')) {{
        btn.textContent = '☀️ Light Mode';
      }} else {{
        btn.textContent = '🌙 Night Mode';
      }}
    }}

    function mockPlayAudio() {{
      const btns = document.querySelectorAll('.replay-button-mock');
      btns.forEach(b => {{
        b.style.transform = 'scale(1.2)';
        setTimeout(() => b.style.transform = '', 200);
      }});
    }}

    // Keyboard Shortcuts
    document.addEventListener('keydown', (e) => {{
      if (e.target.tagName === 'SELECT' || e.target.tagName === 'INPUT') return;
      if (e.code === 'Space') {{
        e.preventDefault();
        showCard(currentView === 'front' ? 'back' : 'front');
      }} else if (e.code === 'KeyD') {{
        toggleTheme();
      }} else if (e.code === 'ArrowDown' || e.code === 'ArrowRight') {{
        e.preventDefault();
        if (currentIndex < cardsData.length - 1) loadCard(currentIndex + 1);
      }} else if (e.code === 'ArrowUp' || e.code === 'ArrowLeft') {{
        e.preventDefault();
        if (currentIndex > 0) loadCard(currentIndex - 1);
      }}
    }});

    window.onload = initCards;
  </script>
</body>
</html>
"""

if __name__ == '__main__':
    try:
        preview_path = os.path.join(os.path.dirname(__file__), 'N2 Level', 'card_template', 'preview.html')
        with open(preview_path, 'w', encoding='utf-8') as f:
            f.write(html_template)

        preview_updated_path = os.path.join(os.path.dirname(__file__), 'N2 Level', 'card_template', 'preview_updated.html')
        with open(preview_updated_path, 'w', encoding='utf-8') as f:
            f.write(html_template)

        print("Preview files generated successfully!")
    except Exception as e:
        print(f"Direct file write skipped: {e}")

