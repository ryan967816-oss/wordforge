# WordForge Worklog

## 2026-06-24 - Thick Scaffold Vocab Drill

Operator: Codex.

Context:
- Ming pointed out that a quiz-first vocabulary UI is the wrong learning shape:
  if it only produces about ten understood words per day, long-term retention
  will be far too low.
- The desired shape is a large learning card: one question, four option words,
  Chinese translation of the prompt, and clear Chinese notes for each word's
  meaning, usage, and trap.

Current state:
- Vocab drill now opens as a single-column learning surface. The old left-side
  `Add a word` panel no longer takes half the screen; it is collapsed below the
  main drill.
- Each discrimination drill can request a cached Chinese scaffold with:
  prompt translation, context, blank role, option cards, and a final choosing
  rule.
- The base drill remains local. The Chinese scaffold is generated only when
  missing, then cached in a local gitignored JSONL file.

Files changed:
- `.gitignore` - ignores local scaffold cache and lock files.
- `wordforge/drill_scaffold.py` - builds and caches thick Chinese drill
  scaffolds.
- `wordforge/studio.py` - adds `/api/drill/scaffold`.
- `wordforge/studio_page.html` - renders the single-column Vocab UI and rich
  option cards.
- `README.md` - documents the scaffold-first Vocab behavior.

Verification:
```bash
./.venv/bin/python -m py_compile wordforge/drill_scaffold.py wordforge/studio.py wordforge/app.py
# pass

curl http://127.0.0.1:8764/api/drill
# HTTP 200

POST /api/drill/scaffold for a deleterious/noxious drill
# returned fallback=false, 4 option cards, Chinese prompt, context, blank role,
# and a choosing rule
```

Browser QA:
- Chrome at `http://127.0.0.1:8764/` showed the Vocab drill as a large
  single-column card with Chinese prompt/scaffold and four rich option cards.
- `Add a word` is present only as a collapsed drawer below the drill.

Boundaries:
- `data/lexicon.jsonl` and `data/reviews.jsonl` contain live learner history and
  were intentionally left uncommitted in this code change.
- First-time scaffold generation still uses the configured provider; after that
  it is local cache.

## 2026-06-24 - Put Studio Into Daily Use

Operator: Codex.

Context:
- Ming asked whether the system could be fixed and put into use immediately:
  he wants to read, not keep asking Codex to wake the tool.

Current state:
- The menu-bar vocabulary app is running as a resident LaunchAgent.
- The Studio reading backend is now also installed as a resident LaunchAgent
  (`com.wordforge.studio`) and serves `http://127.0.0.1:8764`.
- A native Studio reader window is open against that resident backend.
- The menu-bar app has an `Open Studio Reader` item, so the 📖 menu becomes the
  daily doorway into the reading UI.

Files changed:
- `install_studio_login_item.command` - installs `com.wordforge.studio` as a
  launchd backend service with `WORDFORGE_NO_OPEN=1`.
- `uninstall_studio_login_item.command` - removes the Studio backend service.
- `wordforge/app.py` - adds `Open Studio Reader` to the menu-bar app.
- `README.md` - documents the resident Studio backend and menu entry.

Verification:
```bash
./.venv/bin/python -m py_compile wordforge/app.py wordforge/window.py wordforge/studio.py
# pass

bash -n install_studio_login_item.command uninstall_studio_login_item.command install_login_item.command run_native.command run_studio.command
# pass

printf '\n' | ./install_studio_login_item.command
# wrote ~/Library/LaunchAgents/com.wordforge.studio.plist
# Studio backend ready at http://127.0.0.1:8764

old=$(pgrep -f -- '-m wordforge\.studio' | head -n1); kill "$old"; sleep 3; pgrep -f -- '-m wordforge\.studio' | head -n1
# launchd restarted the backend with a new PID

curl http://127.0.0.1:8764/api/translate/routes
# HTTP 200

curl http://127.0.0.1:8764/api/translate/corpus
# 16 passages
```

Next action:
- Use the native Studio window for reading now.
- Later, add a local-model option for offline Ask/grading if true no-network
  reading becomes the priority.

Boundaries:
- The resident backend keeps the local UI/corpus ready. Live Ask/grading still
  depends on the configured provider unless the passage support is already
  pre-baked.

## 2026-06-23 - Four Reading Routes + Passage Ask

Operator: Codex.

Context:
- Ming asked to turn the four public-domain books into a real local reading
  practice system, not only isolated translation exercises: route selection,
  denser support, per-sentence production, local records, and direct questions
  while reading.

Current state:
- Translate has four reading routes: Emerson `Self-Reliance`, Thoreau `Walden`,
  Douglass `Narrative`, and Shelley `Frankenstein`.
- The public corpus now has 16 pre-baked passages.
- Each route has a central question, "why this hits", first attention act,
  Gutenberg URL, and local source PDF path.
- The Studio UI exposes `Ask this passage / 问这段`; answers are Chinese but
  anchored to exact English phrases and concrete English features.
- Native Studio is running through `run_native.command`; browser fallback is at
  `http://127.0.0.1:8764/`.

Files changed:
- `data/corpus/passages.jsonl` - expanded from 6 to 16 public-domain practice
  packages and added route/book metadata to the seed rows.
- `data/corpus/reading_paths.json` - four book-route definitions.
- `wordforge/corpus.py` - loads reading routes and surfaces route metadata in
  passage summaries.
- `wordforge/translate.py` - adds passage-level Ask schema/prompt and increases
  scaffold output budget for dense long passages.
- `wordforge/studio.py` - adds route and ask APIs plus local PDF/source opening.
- `wordforge/studio_page.html` - adds Reading path selector, route card, Ask
  panel, and route-filtered passage picker.
- `scripts/build_corpus.py` - preserves route/book/context metadata while baking
  source rows and makes provider wording generic.
- `README.md` / `data/corpus/README.md` - documents the route-backed corpus.

Verification:
```bash
./.venv/bin/python scripts/build_corpus.py --validate
# count: 16

./.venv/bin/python -m py_compile wordforge/corpus.py wordforge/translate.py wordforge/studio.py scripts/build_corpus.py
# pass

curl http://127.0.0.1:8764/api/translate/routes
# returned 4 routes

curl http://127.0.0.1:8764/api/translate/corpus
# returned 16 passage summaries

curl -X POST http://127.0.0.1:8764/api/translate/ask ...
# returned answer_zh, english_anchor, what_to_notice, and next_question
```

Browser QA:
- Translate showed `Reading path`, `Pick a passage`, and `Support`.
- Selecting `Emerson · Self-Reliance` showed 4 passages and the route card.
- Selecting `Trust Thyself` showed source text, word hints, sticky
  `Source follows / 原文跟随`, Ask panel, and per-sentence input boxes.
- Ask returned a visible answer anchored to `Trust thyself: every heart vibrates
  to that iron string.`
- Switching to `回译 C→E · 产出` kept the source visible and changed the answer
  boxes to English reconstruction.

Next action:
- Continue growing the public-domain corpus by route.
- Add better route-level sequencing once each book has 10-20 passages.

Boundaries:
- The DeepSeek key remains local in Keychain/env and is not committed.
- Project Gutenberg/public-domain text is committed; copyrighted textbook OCR
  remains a local-only path under gitignored directories.

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

### Follow-up fix - UI support visibility + terminal fallback

Context:
- Browser showed `Failed to fetch` because the old Studio backend was no longer
  listening on `:8764`.
- Ming also corrected the product shape: the source text must stay visible while
  typing, and word hints need to be a separate, glanceable line with Chinese
  glosses.

Changes:
- `wordforge/studio_page.html` keeps the source/original text visible in both
  E->C and back-translation modes.
- Corpus support now starts with a separate `WORD HINTS` line such as
  `thyself = 你自己`.
- `wordforge/translate_terminal.py` adds a terminal practice fallback using the
  same pre-baked corpus, with no Claude call unless `--claude-grade` is passed.
- `wordforge/cli.py translate` exposes that terminal mode from the main CLI.

Verification:
```bash
./.venv/bin/python -m py_compile wordforge/translate_terminal.py wordforge/cli.py wordforge/corpus.py wordforge/studio.py
# pass

./.venv/bin/python -m wordforge.cli translate --id thoreau-walden-live-deliberately --mode back --support 1
# printed SOURCE / 原文, word hints, scaffold, palette, accepted an answer, and emitted local missed-word coverage

curl 'http://127.0.0.1:8764/api/translate/corpus/get?id=emerson-self-reliance-trust-thyself'
# returned the full passage package
```

Browser QA:
- Selecting `Trust Thyself` loads the source text instead of placeholder text.
- E->C support shows `WORD HINTS` with Chinese glosses.
- Back-translation keeps the source area visible and also shows `WORD HINTS`,
  scaffold, grammar, structures, and palette.

### Follow-up fix - Native Claude Design window is the primary UI

Context:
- Ming clarified that the desired local UI is not terminal-first; the existing
  Claude Design local window (`run_native.command`) should be the primary
  surface.

Changes:
- `wordforge/window.py` now checks `/api/translate/corpus` before opening the
  native pywebview window.
- If no current backend is running, it starts Studio in-process.
- If a stale WordForge backend is occupying `:8764` without the corpus API, it
  clears that port and starts the current backend, so the native window is not
  stuck with old routes.
- `README.md` now names `run_native.command` as the main Studio UI and
  `run_studio.command` as the browser fallback.

Verification:
```bash
./.venv/bin/python -m py_compile wordforge/window.py
# pass

./.venv/bin/python - <<'PY'
from wordforge import window
print(window._backend_ready())
PY
# True
```

### Follow-up fix - DeepSeek provider, dense hints, per-line records

Context:
- Ming reported Claude/API calls failing and provided a DeepSeek key to use
  locally.
- Ming also noted that C->E is hard when the UI does not show which English slot
  corresponds to each Chinese cue. He asked for denser hints and sentence-level
  input boxes that can be checked separately or together.

Changes:
- `wordforge/config.py` supports provider selection and DeepSeek key/model/base
  URL lookup. Provider/key can live in env or macOS Keychain.
- `wordforge/grounding.py` routes `_structured_call` through DeepSeek when the
  provider is `deepseek`, using JSON-only output with schema prompting.
- The supplied DeepSeek key was saved to local macOS Keychain and provider was
  set to `deepseek`; no key was committed.
- `wordforge/translate_history.py` records every translation check to
  `data/translate_attempts.jsonl` and extracts sentence/word/structure errors
  to `data/translate_errors.jsonl`.
- `wordforge/studio.py` records full-passage checks and adds
  `/api/translate/grade_line` for sentence-level checks.
- `wordforge/studio_page.html` splits corpus passages into per-sentence answer
  boxes, adds local sentence-specific palette chips, flags fronted opening
  phrases such as `With consistency`, and supports `Check line` plus `Check all`.

Verification:
```bash
./.venv/bin/python -m py_compile wordforge/config.py wordforge/grounding.py wordforge/translate_history.py wordforge/studio.py
# pass

./.venv/bin/python - <<'PY'
from wordforge import grounding
schema={"type":"object","additionalProperties":False,"properties":{"ok":{"type":"boolean"},"word":{"type":"string"}},"required":["ok","word"]}
print(grounding._structured_call('Return JSON only.', 'Return ok true and word test.', schema, 80))
PY
# {'ok': True, 'word': 'test'}

curl -X POST http://127.0.0.1:8764/api/translate/grade_line ...
# DeepSeek identified: For -> With changes meaning; missing simply; recorded 3 error items.
```

Browser QA:
- Emerson `A Foolish Consistency` renders 4 per-sentence answer boxes.
- Sentence 2 shows `With consistency ... = fronted phrase · 对于/在...方面/带着`
  plus `has simply nothing to do`; unrelated sentence 1/3 chips no longer leak
  into that sentence.
- Clicking `Check line` calls DeepSeek and shows/records the line-level feedback.

### Follow-up fix - Source follows while writing

Context:
- Ming reported that after scrolling down into the sentence answer boxes, the
  source text disappeared above the viewport, making reconstruction cumbersome.

Changes:
- `wordforge/studio_page.html` now renders a sticky `Source follows / 原文跟随`
  panel between the scaffold and answer area.
- Each per-sentence answer box also shows its own source sentence above the
  local hints and textarea.

Verification:
- Browser QA scrolled to sentence 4 of `A Foolish Consistency`; the sticky source
  panel remained visible near the top of the viewport.
- The line answer area rendered 4 `.line-source` blocks; sentence 4 showed the
  correct source sentence inline.

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
