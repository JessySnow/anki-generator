# Anki Card Template: Japanese N2 Vocab & Grammar

This card template is built according to official Anki manual instructions and best practices:
- **Active Recall & Minimum Information Principle** (`background.md`, `editing.md`)
- **Field Separation** (`editing.md#adding-a-note-type`): media, readings, meanings, grammar, and notes are decoupled.
- **Production Active Recall** (`background.md`, `editing.md`): Uses `{{Meaning}}` and `{{POS}}` on front for active recall of the Japanese vocabulary, and reveals `{{furigana:Furigana}}` on back with elegant ruby positioning.
- **Answer Scroll Anchor** (`templates/fields.md#basic-replacements`): Uses `<hr id="answer">` for mobile scrolling.
- **Dark Mode Support** (`templates/styling.md#night-mode`): Full `.card.nightMode` integration.

## Note Type Fields (15 Fields)

1. `Word`
2. `Reading`
3. `Furigana`
4. `POS`
5. `Meaning`
6. `WordAudio`
7. `Sentence`
8. `SentenceAudio`
9. `SentenceTranslation`
10. `WordUsage`
11. `GrammarPattern`
12. `GrammarMeaning`
13. `GrammarUsage`
14. `CombinationLogic`
15. `Tags`

## How to Configure in Anki

1. In Anki, go to **Tools** > **Manage Note Types** > **Add**.
2. Create a new Note Type named `Japanese N2 Vocab & Grammar` (Base on "Basic").
3. Click **Fields...** and configure the 15 fields listed above.
4. Click **Cards...**:
   - Paste [`front.html`](front.html) into **Front Template**.
   - Paste [`back.html`](back.html) into **Back Template**.
   - Paste [`style.css`](style.css) into **Styling**.
5. Save and close. When importing [`template.txt`](../template.txt), Anki 2.1.54+ will automatically detect the headers (`#notetype`, `#deck`, `#columns`, `#tags column`) and map all fields seamlessly.
