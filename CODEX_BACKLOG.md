# Codex Backlog — the heavy work (大活)

Handoff from Claude Code (地魂 / 冯明) to Codex (天魂 / 迟裕明). The framework is
laid (`ARCHITECTURE.md`); below is the prioritized heavy build, each task
self-contained enough to cold-start. Ming is final authority; no irreversible
actions without his approval.

## Ground rules (keep the framework coherent)
- **Reuse `grounding._structured_call(system, user, schema, max_tokens)`** for every
  Claude call; keep `output_config.format` JSON-schema (constraints:
  `additionalProperties:false`, no min/max, enums ok). Default model
  `claude-opus-4-8`.
- **Keep the principles** in `ARCHITECTURE.md`: production-not-recognition,
  local-first + git-versioned data, local whisper.cpp (not Deepgram) for files,
  **web UI** for new interactive tools (the learner's notched Mac hides menu-bar
  icons), honest scope.
- **Don't break the data model** (`data/lexicon.jsonl` records) or the file-lock /
  atomic-write in `store.py`. Don't commit secrets; the API key lives in env /
  Keychain / the gitignored LaunchAgent plist, never in the repo. `models/` and
  `data/listening/` stay gitignored.
- Verify with real runs and report exact files/commands; land evidence.

## P1 — Unify into one UI app (the "有 UI 的 app" Ming asked for)
**Status.** Landed initial studio shell in `wordforge/studio.py` plus
`run_studio.command`: Vocab, Expression, Listening Reader, Writing, and Stats now
share one local web app at `:8764`. Translate is also wired into Studio with a
corpus picker, four support levels, and E->C / C->E loops. Remaining P1 polish
can continue in small passes without changing the underlying engines.

**Goal.** One local web app (a "WordForge Studio" shell at a single port) with a
left nav hosting: Vocab drill, Expression ladder, Listening reader, Writing,
Stats — so it's one coherent UI, not five entry points.
**Where.** New `wordforge/studio.py` (stdlib `http.server`, merge the routes from
`reader.py` + `express.py`, add `/api/drill`, `/api/add`, `/api/stats` wrapping
`drills`/`store`/`grounding`). Serve a single SPA shell.
**Approach.** Keep each tool's existing functions; the studio just routes + serves
one page with a nav. Reuse reader/express HTML as panels.
**Acceptance.** `python -m wordforge.studio` opens one app where Ming can do
vocab, expression, and listening without separate commands. Add a double-click
`run_studio.command`.

## P2 — Word-level karaoke in the reader
**Goal.** Highlight the *current word* (not just sentence) as audio plays.
**Where.** `listening.transcribe` → add a variant using `whisper-cli -ojf` (full
JSON has token timestamps) or `-owts`; store per-word `[start_ms,end_ms,word]`.
`reader.py` PAGE JS: render words as spans, highlight by `audio.currentTime`.
**Acceptance.** Words light up in sync; sentence-scroll still works.

## P3 — Precise audio → source-PDF mapping + jump-to-page
**Goal.** The reader's "Open PDF" jumps to the *exact selection page*, not just the
unit folder.
**Where.** `reader.py` `/api/pdf`. Build a mapping from audio filename
(`edge_C_SR_CD1_01.mp3`) → textbook PDF + page. The Edge `INDEX.md` has
file→page ranges; selection summaries (`Edge.SSChin.*`) may help align. Likely
needs a one-time index built by reading the unit PDFs (Claude PDF document
blocks) to extract selection titles + page numbers.
**Acceptance.** Clicking opens the right PDF at (or near) the selection page.

## P4 — One-click "unknown word → WordForge"
**Goal.** Select a word anywhere (reader transcript, express ladder, writing
feedback) → it grounds + adds to the lexicon in one click.
**Where.** Add `/api/add?word=` to the studio/reader/express servers calling
`grounding.ground_word` + `store.add_word` on a background thread; frontend: on
word double-click, POST it, toast "added".
**Acceptance.** Double-clicking a word in the reader queues it into vocab drills.

## P5 — Commonplace book (idea / phrase capture)
**Goal.** Capture vivid phrasings/images Ming likes (his own or from the ladder)
into a personal "image bank", then spaced-repeat producing them.
**Where.** New `data/phrasebook.jsonl` + `wordforge/phrasebook.py`; surface in
`express` ("your saved images") and as occasional production prompts.
**Acceptance.** Ming can save a rendering and later be drilled to reproduce it.

## P6 — Reading ingestion (Edge PDF → study material)
**Status.** First corpus-backed Translate slice landed: committed public-domain
seed corpus in `data/corpus/passages.jsonl`; Studio loads it through
`/api/translate/corpus`; local Edge/textbook passages can be built into
gitignored `data/corpus/local/*.jsonl`. Remaining P6 is scale and richer Edge
selection indexing.

**Goal.** Paste/point at an Edge selection → auto-extract target vocabulary into
WordForge + generate comprehension/cloze + listening questions (rebuild the
adapted Q-set Ming deleted).
**Where.** New `wordforge/reading.py`. The textbook PDFs are scanned (~100MB);
pass per-selection page ranges as Claude PDF document blocks (the API reads
scanned PDFs via vision) to extract text + build items. Mind size/cost — do one
selection at a time.
**Acceptance.** `reading ingest <level> <unit> <selection>` yields words added +
a question set saved under `data/reading/`.

## P7 — Speaking / shadowing mode
**Goal.** Play a fluency-model clip → Ming repeats → score pronunciation/accuracy.
**Where.** New `wordforge/speaking.py` + web UI. Capture mic via browser
`MediaRecorder` (like ArguMentor's working capture in `app/public/app.js`),
POST the blob, transcribe with whisper-cli, diff against the model transcript;
score timing/word-accuracy. (Pronunciation scoring is approximate — be honest.)
**Acceptance.** Ming shadows a sentence and gets a word-accuracy score + missed sounds.

## P8 — Expression pillar growth + reconnect the debate corpora
**Goal.** Grow `express` from one-shot ladders into a trained skill: log graded
attempts, track weak image-types, spaced-repeat them; and reconnect ArguMentor's
**BP + liberal-arts retrieval corpora** (`~/Documents/ArguMentor/corpora/`) for an
argument/rhetoric register (make-a-case, rebut, concede) — a higher pillar than
sentence-level imagery.
**Acceptance.** A weekly "expression review" that resurfaces Ming's weakest
renderings + a rhetoric drill grounded in the debate corpus (cited, `judge_decision=false`).

## P9 — Deepgram live-streaming mode (only when there's a live use case)
**Goal.** Real-time transcription of *live* audio (a lecture, Ming speaking) — the
one place Deepgram beats local whisper.
**Where.** Browser mic / system audio → WebSocket → Deepgram streaming → live
scrolling transcript in the studio. Needs `DEEPGRAM_API_KEY` (not currently set;
ask Ming, store in env/Keychain, never commit).
**Acceptance.** A "Live" tab transcribes a real-time source as it speaks.

## P10 — Packaging & tests
**Goal.** Make it a real distributable app + a test suite.
**Where.** Either bundle the studio web app behind a menu-bar/Tauri launcher, or
finish the py2app path (`setup_app.py`). Add `tests/` covering store (lock,
atomic, rotation), scheduler (SM-2), drills (answer checking), and a mocked
grounding layer.
**Acceptance.** `pytest` green; one double-click launch for the whole studio.

---
*Repo: `github.com/ryan967816-oss/wordforge` (private). Read `ARCHITECTURE.md` first.*
