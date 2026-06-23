# WordForge Worklog

## 2026-06-23 - Corpus-backed Translate Loop

Operator: Codex.

Context:
- Ming asked for two translation loops inside Studio:
  - A: English -> Chinese with hard-word hints, sentence-by-sentence grading, and
    accuracy/naturalness/omission feedback.
  - B: Chinese-word-order back-translation, then comparison against the original,
    with missed words/structures feeding WordForge.
- Ming also asked to begin turning Edge/public texts into a corpus and to make
  the support progressively thinner: thick scaffold -> hints -> word-order
  Chinese -> bare translation/back-translation.

Current state:
- Studio Translate now has a "Pick a passage" corpus selector and four support
  levels.
- The committed seed corpus contains 6 copyright-clean public-domain passages
  from Emerson, Thoreau, Douglass, and Mary Shelley.
- Local Edge/textbook OCR is supported through gitignored local directories, so
  private study text can be used without publishing copyrighted passage text.

Files changed:
- `data/corpus/passages.jsonl` - 6 pre-baked passage packages with glosses,
  tense-tagged scaffolds, palettes, grammar notes, and vocab targets.
- `data/corpus/README.md` - explains committed public corpus vs local textbook
  corpus.
- `wordforge/corpus.py` - loads committed passages plus
  `data/corpus/local/*.jsonl`.
- `wordforge/studio.py` - adds `/api/translate/corpus` and
  `/api/translate/corpus/get`.
- `wordforge/studio_page.html` - adds passage picker, support levels, pre-baked
  E->C/back-translation rendering, clickable palette, and hides the English
  source during selected-corpus back-translation.
- `scripts/build_corpus.py` - validates the corpus and can bake source passages
  into full packages.
- `scripts/ocr_edge_pages.py` - OCRs selected local Edge PDF pages into
  gitignored source rows for later baking.
- `.gitignore` - ignores local textbook packages and raw OCR rows.
- `README.md` / `ARCHITECTURE.md` - documents the corpus-backed Translate path.

Verification:
```bash
./.venv/bin/python -m py_compile wordforge/corpus.py wordforge/studio.py wordforge/translate.py scripts/build_corpus.py scripts/ocr_edge_pages.py
# pass

./.venv/bin/python scripts/build_corpus.py --validate
# count: 6; ids: emerson-self-reliance-trust-thyself, emerson-self-reliance-consistency,
# thoreau-walden-live-deliberately, thoreau-walden-quiet-desperation,
# douglass-silver-trump-freedom, shelley-frankenstein-creator-light

WORDFORGE_NO_OPEN=1 WORDFORGE_STUDIO_PORT=8774 ./.venv/bin/python -m wordforge.studio
# served http://127.0.0.1:8774

curl http://127.0.0.1:8774/api/translate/corpus
# returned 6 passage summaries

curl 'http://127.0.0.1:8774/api/translate/corpus/get?id=thoreau-walden-live-deliberately'
# returned the full pre-baked package
```

Browser QA:
- Translate tab shows 6 passages in "Pick a passage".
- Selecting a passage instantly renders support with no live Claude call.
- Back-translation level 1 shows tagged scaffold + grammar + structures +
  clickable palette; clicking a palette phrase inserts it into the answer box.
- Back-translation level 3 removes tense tags and hides the palette.
- When a corpus passage is selected in back-translation mode, the original
  English source box and "Make scaffold" button are hidden; the original remains
  stored only for grading.

Next action:
- Grow `data/corpus/passages.jsonl` toward 50-100 public-domain passages.
- Use `scripts/ocr_edge_pages.py` on specific Edge C selections, then bake them
  into `data/corpus/local/edge_passages.jsonl` for private local practice.
- Add structure filters once the corpus is larger.

Boundaries:
- Edge C scanned PDF text was not committed. Public repo content stays
  copyright-clean; local textbook material belongs under gitignored
  `data/corpus/local/`.
- Live grading still uses Claude; pre-baked corpus support loads instantly.

## 2026-06-22 - P1 Studio Shell

Operator: Codex.

Context:
- Ming handed off Claude Code's `ARCHITECTURE.md` / `CODEX_BACKLOG.md` and asked
  Codex to take P1.

Current state:
- Initial WordForge Studio shell is implemented at one local web port.

Files changed:
- `wordforge/studio.py` - new stdlib `http.server` studio with Vocab,
  Expression, Listening Reader, Writing, and Stats tabs.
- `run_studio.command` - double-click launcher for the studio.
- `README.md` - documents the studio as the main web UI entry point.
- `ARCHITECTURE.md` - records `studio.py` in the module map.
- `CODEX_BACKLOG.md` - marks the initial P1 shell as landed.

Verification:
```bash
./.venv/bin/python -m py_compile wordforge/studio.py wordforge/express.py wordforge/reader.py wordforge/writing.py wordforge/listening.py
# pass

WORDFORGE_NO_OPEN=1 ./.venv/bin/python -m wordforge.studio
# served http://localhost:8764

curl http://127.0.0.1:8764/
# HTTP 200

curl http://127.0.0.1:8764/api/stats
# returned stats for 6 words, 25 reviews, no error

curl http://127.0.0.1:8764/api/drill
# returned a drill with next_cursor; no data/lexicon.jsonl diff after GET

curl http://127.0.0.1:8764/api/writing/prompts
# returned built-in and TOEFL prompts

curl http://127.0.0.1:8764/api/listening/list
# returned 432 Edge audio files

WORDFORGE_DATA_DIR=<tempdir> ./.venv/bin/python -c '<studio drill answer smoke>'
# returned {'headword': 'perfunctory', 'correct': True, 'reviews_total': 1}
```

Browser QA:
- Desktop 1280px: Vocab, Reader, Writing, and Expression panels render with no
  horizontal overflow.
- Mobile 390px: nav folds into a top bar; Vocab and Reader remain within viewport.
- Browser console error log: empty.

Next action:
- Continue with P2 word-level karaoke or P4 one-click unknown-word capture.

Boundaries:
- Claude/API-backed generation routes were not exercised to avoid spending model
  calls during smoke tests.
- `/api/drill` is intentionally read-only; study state advances only on answer.
