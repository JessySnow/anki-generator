#!/usr/bin/env python3
"""
Generate an interactive browser preview for N3_4_Level cards.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DECK_PATH = REPO_ROOT / "N3_4_Level" / "deck.txt"
STYLE_PATH = REPO_ROOT / "N3_4_Level" / "card_template" / "style.css"
OUTPUT_HTML = REPO_ROOT / "N3_4_Level" / "card_template" / "preview.html"

def generate_preview():
    if not DECK_PATH.is_file():
        print(f"Deck file not found: {DECK_PATH}")
        return 1

    cards = []
    with open(DECK_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.strip("\n").split("\t")
            if len(parts) >= 16:
                cards.append({
                    "guid": parts[0],
                    "word": parts[1],
                    "reading": parts[2],
                    "furigana": parts[3],
                    "pos": parts[4],
                    "meaning": parts[5],
                    "sentence": parts[7],
                    "sentence_zh": parts[9],
                    "word_usage": parts[10],
                    "grammar_pattern": parts[11],
                    "grammar_meaning": parts[12],
                    "grammar_usage": parts[13],
                    "combination_logic": parts[14],
                    "tags": parts[15]
                })

    if not cards:
        print("No cards loaded from deck.txt")
        return 1

    with open(STYLE_PATH, "r", encoding="utf-8") as f:
        css = f.read()

    cards_json = json.dumps(cards[:50], ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Anki Card Preview - Japanese N3/N4 Vocab & Grammar</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: #e2e8f0;
      margin: 0;
      padding: 24px;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-height: 100vh;
    }}
    .controls {{
      display: flex;
      gap: 12px;
      margin-bottom: 20px;
      align-items: center;
      flex-wrap: wrap;
      background: #ffffff;
      padding: 10px 20px;
      border-radius: 9999px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    }}
    button, select {{
      padding: 6px 14px;
      border-radius: 8px;
      border: 1px solid #cbd5e1;
      background: #ffffff;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
    }}
    button:hover {{ background: #f8fafc; }}
    .card-viewport {{
      width: 100%;
      max-width: 640px;
      perspective: 1000px;
    }}
    .card {{
      box-sizing: border-box;
      width: 100%;
      border-radius: 18px;
      padding: 30px;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    {css}
  </style>
</head>
<body>
  <div class="controls">
    <select id="cardSelect"></select>
    <button id="flipBtn">翻面 (空格键 / Space)</button>
    <button id="nightToggle">暗黑模式 (D)</button>
  </div>
  <div class="card-viewport">
    <div id="cardRoot" class="card"></div>
  </div>

  <script>
    const cards = {cards_json};
    let currentIdx = 0;
    let isFlipped = false;
    let isNight = false;

    const select = document.getElementById("cardSelect");
    cards.forEach((c, i) => {{
      const opt = document.createElement("option");
      opt.value = i;
      opt.textContent = `${{i + 1}}. ${{c.word}} (${{c.reading}})`;
      select.appendChild(opt);
    }});

    function parseFurigana(text) {{
      return text.replace(/ ?([^ >\\[\\]]+)\\[([^\\]]+)\\]/g, '<ruby>$1<rt>$2</rt></ruby>');
    }}

    function render() {{
      const c = cards[currentIdx];
      const root = document.getElementById("cardRoot");
      root.className = "card" + (isNight ? " nightMode" : "");

      if (!isFlipped) {{
        root.innerHTML = `
          <div class="card-box front-card">
            <div class="deck-tag">日语::大家的日语::单词</div>
            <div class="word-container">
              <div class="word-main">${{c.meaning}}</div>
              <div class="pos-pill">${{c.pos}}</div>
            </div>
          </div>
        `;
      }} else {{
        root.innerHTML = `
          <div class="card-box front-card">
            <div class="deck-tag">日语::大家的日语::单词</div>
            <div class="word-container">
              <div class="word-main">${{c.meaning}}</div>
              <div class="pos-pill">${{c.pos}}</div>
            </div>
          </div>
          <hr id="answer">
          <div class="card-box back-card">
            <div class="reading-row">
              <div class="furigana-title">${{parseFurigana(c.furigana)}} <span class="replay-button-mock" title="播放发音"></span></div>
            </div>
            <div class="sentence-detail-section">
              <div class="badge-label"><span class="badge-icon">📖</span> 例句解析</div>
              <div class="sentence-jp">${{c.sentence}} <span class="replay-button-mock" title="播放发音"></span></div>
              <div class="sentence-zh">${{c.sentence_zh}}</div>
            </div>
            <div class="grammar-section">
              <div class="badge-label grammar-label"><span class="badge-icon">✨</span> 语法重点</div>
              <div class="grammar-header">
                <span class="grammar-pattern">${{c.grammar_pattern}}</span>
                <span class="grammar-meaning">（${{c.grammar_meaning}}）</span>
              </div>
              <div class="grammar-usage-text">${{c.grammar_usage}}</div>
            </div>
            <details class="analysis-details" open>
              <summary>深入解析与语境逻辑</summary>
              <div class="analysis-body">
                <div class="analysis-item">
                  <span class="item-title">词汇用法</span>
                  <div class="item-content">${{c.word_usage}}</div>
                </div>
                <div class="analysis-item">
                  <span class="item-title">语境逻辑</span>
                  <div class="item-content">${{c.combination_logic}}</div>
                </div>
              </div>
            </details>
            <div class="tags-row"><span class="tags-pill">${{c.tags}}</span></div>
          </div>
        `;
      }}
    }}

    select.addEventListener("change", (e) => {{
      currentIdx = parseInt(e.target.value, 10);
      isFlipped = false;
      render();
    }});

    document.getElementById("flipBtn").addEventListener("click", () => {{
      isFlipped = !isFlipped;
      render();
    }});

    document.getElementById("nightToggle").addEventListener("click", () => {{
      isNight = !isNight;
      render();
    }});

    window.addEventListener("keydown", (e) => {{
      if (e.code === "Space") {{
        e.preventDefault();
        isFlipped = !isFlipped;
        render();
      }} else if (e.code === "KeyD") {{
        isNight = !isNight;
        render();
      }}
    }});

    render();
  </script>
</body>
</html>
"""
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated preview at {OUTPUT_HTML}")
    return 0

if __name__ == "__main__":
    generate_preview()
