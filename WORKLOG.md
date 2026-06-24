# WordForge Worklog

## 2026-06-24 - Raw Sidebar and Ten Local Lessons

Operator: Codex.

Context:
- Ming wanted the raw transcript tool out of the main Reader flow and asked for
  ten California/Edge lesson packages to read tonight.
- A read-only explorer checked the local listening library: the active shelf is
  `/Users/yuhangxiao/Documents/english for listening `, with 432 mp3 files and
  173 real selection recordings.

Current state:
- Reader now uses a two-column layout on desktop:
  - main column: pre-baked reading packages, page reader, selected-block follow,
    and ask box;
  - right sidebar: `Raw listening transcript / 原始听写工具`, with its own audio,
    transcript, and open-folder controls.
- Native launch now opens Reader on the `Lessons / 课文` shelf by default.
- Added `scripts/bake_local_lesson_batch.py` to batch-bake local selection
  recordings into gitignored lesson packages.
- Baked ten local lesson packages under `data/reading_packages/local/`:
  - First Names
  - Romeo and Juliet · balcony scene
  - Growing Together
  - My People
  - Ways to Know You
  - Who Is She?
  - The Good Samaritan · Part 1
  - The Good Samaritan · Part 2
  - The Good Samaritan · Part 3
  - The World Is in Their Hands

Verification:
```bash
./.venv/bin/python -m py_compile scripts/bake_local_lesson_batch.py wordforge/studio.py wordforge/reading_packages.py wordforge/window.py
# pass

node - <<'NODE'
# parsed Studio embedded JS with new Function(...)
# js parse ok
NODE

./.venv/bin/python scripts/bake_local_lesson_batch.py --count 10 --workers 3 --force
# baked: 10, failed: 0

./.venv/bin/python - <<'PY'
# reading_packages.list_packages() reports 11 lesson packages:
# existing Ambush plus 10 new local Edge lessons, all with audio.
PY
```

Boundaries:
- The new lesson JSONL files and transcript caches are local-only and
  gitignored. The committed artifact is the repeatable baking script plus UI
  shell.
- These ten packages are starter scaffolds for immediate reading. They have
  audio, page blocks, Chinese reading handles, structure/watch notes, and vocab
  chips, but not yet hand-curated commentary on every sentence.

## 2026-06-24 - Reader Partition UX

Operator: Codex.

Context:
- Ming reported that the Reader was functionally richer but still not pleasant
  to use. The Books/Lessons split was hidden inside dropdowns, lesson paging was
  hard to discover, and the old raw transcript tools crowded the main reading
  surface.

Current state:
- Reader entry now has explicit `Books / 想读的书` and `Lessons / 课文` shelf
  cards with counts and different reading modes.
- Package selection is now card-based. A user can click a book or lesson card
  directly instead of choosing a shelf dropdown plus a package dropdown plus
  Load.
- URL deep links with `?package=...` now infer the correct shelf category before
  rendering, so opening the full Emerson package switches to Books even if the
  previous local preference was Lessons.
- Raw listening transcript tools are collapsed under `Raw listening transcript /
  原始听写工具`, leaving the main Reader focused on the pre-baked reading
  experience.

Files changed:
- `wordforge/studio_page.html` - Reader shelf tabs, package cards, category
  inference, and collapsed raw transcript section.

Verification:
```bash
./.venv/bin/python -m py_compile wordforge/studio.py wordforge/reading_packages.py scripts/bake_current_lesson_package.py
# pass

node - <<'NODE'
# parsed Studio embedded JS with new Function(...)
# js parse ok
NODE
```

Browser QA:
- Opened Reader with local preference on Lessons: saw `Lessons / 课文` active,
  one lesson card, one visible reading block, `Page 1 / 7`, and raw transcript
  tools collapsed.
- Clicked Books: saw `Books / 想读的书` active, five book cards, and block-scroll
  reading.
- Clicked back to Lessons: saw one lesson card and page reader again.
- Opened `?package=emerson-self-reliance-complete`: UI auto-selected Books,
  selected the complete Emerson card, and rendered 101 blocks.
- Browser console had no warnings/errors in both checks.

Boundaries:
- This improves Reader information architecture and selection flow. It does not
  change the current Emerson audio timing strategy or make true forced
  alignment.

## 2026-06-24 - Lesson Paging Reader

Operator: Codex.

Context:
- Ming accepted the first Emerson block reader as a stopping point for now, but
  pointed out that lesson packages had not changed and should not be displayed
  as one crowded stack.
- The desired lesson shape is page-like: one teaching block at a time, with
  Prev/Next navigation, audio still attached, and local-only lesson data.

Current state:
- `scripts/bake_current_lesson_package.py` now bakes `lesson-ambush-local` with
  7 high-scaffold blocks, including a dedicated `peril` block explaining why
  `There was no real peril` matters after the grenade scene.
- Reader UI now treats lesson packages as paged readers:
  - one visible `.reading-block` at a time;
  - `Page N / total` navigation;
  - Prev/Next buttons;
  - sticky follow text updates to the current page;
  - audio remains the local lesson audio via `/api/listening/audio?i=0`.
- Book packages still keep block-scroll behavior.

Verification:
```bash
./.venv/bin/python -m py_compile scripts/bake_current_lesson_package.py wordforge/reading_packages.py wordforge/studio.py
# pass

node - <<'NODE'
# parsed Studio embedded JS with new Function(...)
# js parse ok
NODE

./.venv/bin/python scripts/bake_current_lesson_package.py --index 0 --id lesson-ambush-local --title 'Ambush · local lesson'
# wrote local-only package with 98 segments

curl 'http://127.0.0.1:8764/api/reading/package/get?id=lesson-ambush-local'
# category=lesson, segments=98, blocks=7
```

Browser QA:
- Opened Reader, switched Shelf to `Lessons / 课文`.
- Confirmed selected package `lesson-ambush-local`, `lyricsPaged=true`,
  exactly one `.reading-block` visible, `Page 1 / 7`, audio source
  `/api/listening/audio?i=0`.
- Clicked `Next`; confirmed `Page 2 / 7`, still one block visible, sticky
  follow text updated, and browser console had no warnings/errors.

Boundaries:
- The updated local lesson package is under `data/reading_packages/local/` and
  remains gitignored. The committed source of truth is the baking script plus UI
  behavior.
- This does not fix Emerson forced alignment. Ming explicitly paused that part
  for now.

## 2026-06-24 - Block-Level Emerson Reader

Operator: Codex.

Context:
- Ming could follow the audio but not the meaning fast enough. Sentence-level
  lyric scrolling was too fragmented; the English source disappeared from view
  while reading deeper in the page.
- Ming wanted pre-baked teaching: block-by-block explanation, high-density
  vocabulary hints, and quick questions on selected words.

Current state:
- Reader packages now normalize a top-level `blocks` layer while preserving the
  underlying sentence `segments` needed for audio timing.
- `Self-Reliance · Complete Essay` now has 101 reading blocks:
  - 11 hand-baked high-scaffold blocks from the opening through `foolish
    consistency`.
  - fallback blocks for the rest of the essay, so the whole text remains
    readable before every later block is hand-curated.
- Reader UI now syncs audio to the active block, keeps the current block's
  English source in the sticky follow bar, renders Chinese core notes, why-good
  notes, watch points, and vocab chips, and lets vocab chips pre-fill/send a
  block-anchored question.
- The complete local Emerson mp3 remains
  `data/reading_audio/emerson-self-reliance-complete.mp3`, with
  `chunk-duration-proportional` timing.

Files changed:
- `wordforge/reading_packages.py` - block normalization and fallback blocks.
- `wordforge/studio_page.html` - block-level Reader UI and selected-word
  questions.
- `wordforge/studio.py` - `/api/reading/ask` can answer from a selected block.
- `scripts/bake_self_reliance_full.py` - source of truth for the first curated
  Emerson reading blocks.
- `data/reading_packages/emerson_self_reliance_full.jsonl` - regenerated
  package with blocks plus existing audio metadata.

Verification:
```bash
./.venv/bin/python -m py_compile wordforge/reading_packages.py wordforge/studio.py scripts/bake_self_reliance_full.py scripts/bake_reading_audio.py
# pass

node - <<'NODE'
# parsed Studio embedded JS with new Function(...)
# js parse ok
NODE

curl 'http://127.0.0.1:8764/api/reading/package/get?id=emerson-self-reliance-complete'
# audio_timing=chunk-duration-proportional, segments=489, blocks=101
```

Browser QA:
- Opened `http://127.0.0.1:8764/?view=reader&package=emerson-self-reliance-complete&native=1`.
- Confirmed Reader visible, package selected, audio source present, 101
  `.reading-block` nodes, first block title `自己的思想就是天才的入口`,
  first block has 8 vocab chips, sticky follow contains the English source, and
  browser console had no errors.

Boundaries:
- This is not true word-level forced alignment. Audio chooses the active block
  from sentence timings that are still chunk-duration proportional.
- Only the opening through `foolish consistency` is hand-curated at high
  density. Later blocks are readable fallback blocks until they are baked.
- Local learner history in `data/lexicon.jsonl` and `data/reviews.jsonl` was
  left uncommitted.

## 2026-06-24 - Full Self-Reliance Reader Package

Operator: Codex.

Context:
- Ming wanted to read the whole Emerson `Self-Reliance`, not only four short
  practice excerpts.
- Ming wanted Deepgram to use a deep male English voice, faster than the first
  slow tests.

Current state:
- `data/reading_packages/emerson_self_reliance_full.jsonl` contains the full
  Project Gutenberg `Self-Reliance` essay as a Reader package.
- The full package has 489 sentence segments.
- Local Deepgram audio was baked with `aura-2-zeus-en` at `speed=1.2`.
- The generated full mp3 is local-only:
  `data/reading_audio/emerson-self-reliance-complete.mp3`.
- The native window opens Reader with the complete package selected.
- Reading questions are now instructed to answer in English so Deepgram TTS can
  speak answers reliably.

Verification:
```bash
./.venv/bin/python scripts/bake_self_reliance_full.py
# chars: 55145
# segments: 489

./.venv/bin/python scripts/bake_reading_audio.py \
  --path data/reading_packages/emerson_self_reliance_full.jsonl \
  --model aura-2-zeus-en --speed 1.2 --workers 10
# duration_ms: 2760048
# file: emerson-self-reliance-complete.mp3
```

Boundary:
- Generated audio remains gitignored under `data/reading_audio/`.
- The committed package records local audio metadata, but WordForge hides the
  audio flag if the mp3 is absent on another machine.

## 2026-06-24 - Deepgram Key Plumbing Only

Operator: Codex.

Context:
- Ming shared a Deepgram key but noted that Deepgram Voice Agent feels too
  complex to integrate right now.

Current state:
- WordForge can now read `DEEPGRAM_API_KEY` from env or macOS Keychain.
- `scripts/set_deepgram_key.py` stores a Deepgram key using hidden input.
- No Deepgram Voice Agent integration was attempted.

Files changed:
- `wordforge/config.py` - adds Deepgram key getter/setter.
- `scripts/set_deepgram_key.py` - hidden-input Keychain helper.
- `README.md` / `MULTIMODAL_READING_PLAN.md` - document safe key storage and the
  current boundary.

Boundary:
- The key that appeared in chat was not written to code, git, or docs. Rotate it
  before storing a new one.

## 2026-06-24 - Vocab Cache + Blind Mode + Reading Model Tiering

Operator: Codex.

Context:
- Ming wanted Vocab scaffolds to stop regenerating live per question, then asked
  whether bulk pre-baking should use Codex/strong-model curation rather than DS,
  especially for book understanding.
- The live distinction is now explicit: DS is acceptable for low-risk bulk
  scaffolds when the English nuance is already present; book interpretation
  needs Codex/strong-model curation into a pre-baked data package.

Current state:
- Vocab has a `Mode` selector:
  - `Scaffold / 脚手架` shows the thick Chinese support.
  - `Blind test / 盲测` hides the scaffold and does not request it.
- `scripts/prebake_drill_scaffolds.py` can fill missing
  `data/drill_scaffolds.jsonl` rows ahead of time. It is resumable and only
  generates missing cache rows.
- A partial DS pre-bake generated 61 scaffold rows, then was intentionally
  stopped after the quality boundary discussion.
- `MULTIMODAL_READING_PLAN.md` defines the passage-reader direction: audio,
  timestamped English scroll, English-order Chinese components, DS bulk labels,
  strong-model/Codex professor explanation, and selected-sentence Ask.

Files changed:
- `wordforge/drill_scaffold.py` - exposes cache keys and drill iteration helpers.
- `scripts/prebake_drill_scaffolds.py` - batch pre-bake script for Vocab
  scaffold cache.
- `wordforge/studio_page.html` - adds Vocab scaffold/blind selector and avoids
  scaffold requests in blind mode.
- `MULTIMODAL_READING_PLAN.md` - specifies the multimodal reading package and
  model-tier boundary.
- `README.md` / `CODEX_BACKLOG.md` - document the new workflow and reading task.

Verification:
```bash
./.venv/bin/python -m py_compile wordforge/drill_scaffold.py scripts/prebake_drill_scaffolds.py
# pass

node - <<'NODE'
# parsed Studio embedded JS with new Function(...)
# js parse ok
NODE

./.venv/bin/python scripts/prebake_drill_scaffolds.py --dry-run
# words: 226
# missing scaffolds: 584
```

Boundaries:
- `data/drill_scaffolds.jsonl` remains local/gitignored.
- DS should not be treated as a professor for Emerson/Thoreau/Douglass/Shelley
  explanations. Use stronger-model/Codex curation for those reading packages.

## 2026-06-24 - Correct Back-Translation Source

Operator: Codex.

Context:
- Ming noticed that C->E back-translation still followed the English original.
  That leaks the answer and violates the intended loop: the learner should see a
  Chinese-in-English-order source, then reconstruct English.

Current state:
- In `回译 C→E · 产出`, the sticky follow bar now shows
  `Chinese source follows / 中文语序稿跟随`.
- The per-sentence answer boxes now show `Chinese source 1/2/3...` and display
  the Chinese word-order scaffold, not the English original.
- The original English is still retained internally for grading and line checks,
  so feedback compares the learner's English against the correct original.
- For selected corpus passages in C->E mode, the top English source box is hidden
  once the Chinese source is available.

Files changed:
- `.gitignore` - keeps local translation attempt/error logs out of framework
  commits.
- `wordforge/studio_page.html` - separates practice source text from grading
  source text in Translate back-translation mode.

Verification:
```bash
./.venv/bin/python -m py_compile wordforge/studio.py wordforge/translate.py
# pass

node - <<'NODE'
# parsed the embedded Studio script with new Function(...)
# js parse ok
NODE

curl http://127.0.0.1:8764/api/translate/corpus
# HTTP 200
```

Browser QA:
- Chrome at `http://127.0.0.1:8764/`, Translate tab, `回译 C→E · 产出`,
  Emerson route, corpus passage selected.
- Confirmed the sticky source is Chinese word-order text.
- Confirmed each line card is labeled `Chinese source N` and shows the Chinese
  scaffold while `Check line` still works against the English original.

Boundaries:
- Browser QA generated local learner records under `data/translate_attempts.jsonl`
  and `data/translate_errors.jsonl`; those are not part of the code commit.

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

## 2026-06-24 - Reading Lab and offline scaffold boundary

Operator: Codex.

Context:
- Ming wants the local/native WordForge UI to become a personal reading system:
  pre-baked book passages, English kept as the object, Chinese component
  scaffolds, Codex comments, selected-sentence questions, and optional TTS.
- He also noticed Vocab was still effectively generating support live through
  DS, which makes the UI feel slow and non-local.

Changes:
- Added `wordforge/reading_packages.py` plus
  `scripts/bake_emerson_reading_packages.py`.
- Baked the first public-domain Emerson `Self-Reliance` reading package into
  `data/reading_packages/emerson_self_reliance.jsonl`.
- Added Reader UI surface `Reading Lab · 预烤阅读包`:
  package picker, sentence cards, sticky selected-source follow panel, English
  sentence, English-order Chinese component scaffold, Codex comments, palette
  chips, selected-sentence Ask, and Speak buttons.
- Split Reading Lab into `Books / 想读的书` and `Lessons / 课文` shelves.
- Reworked the reading body into a lyric-style scroll panel so long texts do not
  require endless page scrolling. For packages with timestamps, the audio player
  can drive the active sentence.
- Added `scripts/bake_current_lesson_package.py`, which writes a local-only
  lesson package from the current Listening Reader transcript into
  `data/reading_packages/local/`.
- Added safe Deepgram TTS utility module `wordforge/deepgram_tts.py` and
  `scripts/deepgram_speak.py`. The browser never sees the key; audio is written
  under gitignored `data/reading_audio/`.
- Added Studio routes:
  `/api/reading/packages`, `/api/reading/package/get`,
  `/api/reading/ask`, `/api/tts/speak`, and `/api/tts/audio`.
- Changed `/api/drill/scaffold` to read the Vocab scaffold cache by default and
  only generate when explicitly called with `generate: true`. The Studio UI now
  avoids live model calls during drilling.

Verification:
- `py_compile` passed for the new modules, scripts, and `wordforge/studio.py`.
- The Studio page script parsed with Node.
- Temporary Studio on `http://127.0.0.1:8769` returned four Emerson packages.
- `emerson-self-reliance-consistency` returned four sentence segments; sentence
  2 preserved the correct English-order Chinese source:
  `对于 一致性，一个 伟大的灵魂 简直 没有什么 要做[...]`.
- Chrome visual QA confirmed Reader renders the new Reading Lab, package picker,
  sentence cards, and sticky selected-source panel.
- Deepgram configuration currently reports false until a key is stored through
  the hidden-input script. No key was written to files or logs.
- Vocab scaffold endpoint on the restarted Studio returns a local fallback for
  missing cache rows (`not pre-baked yet`) instead of making a live model call.
- Vocab scaffold pre-bake completed all remaining rows:
  `done: ok=578 fallback=0 failed=0`; follow-up dry-run reported
  `missing scaffolds: 0`.
- Restarted the resident Studio backend on `:8764`; it now returns four `book`
  packages and one local `lesson` package. Restarted the native pywebview window.
- Verified `data/reading_packages/local/`, `data/drill_scaffolds.jsonl`, and
  `data/reading_audio/` are gitignored.

Next:
- Continue pre-baking Vocab scaffold rows with
  `scripts/prebake_drill_scaffolds.py`; the cache file is local/gitignored.
- Store a rotated Deepgram key with `scripts/set_deepgram_key.py`, then smoke one
  short mp3 before using TTS from the UI.

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
