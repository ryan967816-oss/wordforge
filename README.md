# WordForge 📖

A native macOS menu-bar app that forges **active (productive) English vocabulary** —
the command an American English professor has: summoning the *exact* word while
writing or speaking, varying register through synonyms, and using antonyms for
contrast.

## Why it's different

Every flashcard app trains **recognition** (see word → recall meaning), which
builds *passive* vocabulary. WordForge trains **production**: meaning/context →
summon the word → use it correctly. Receptive vocabulary runs 2–3× larger than
productive vocabulary, and that gap is exactly the gap between "I recognize
*perfunctory*" and "*perfunctory* shows up in my own sentence at the right moment."

The spine is **synonym / antonym discrimination**, scheduled by spaced repetition
and graded on production — not flip-a-card.

## What it does

- **Add a word** → Claude grounds it: nuance-annotated synonyms (*when* to prefer
  each), antonyms, collocations, a concrete image/etymology hook, example
  sentences, and confusions — *not* dictionary lines.
- **Drill (keeps going)** → spaced-repetition (SM-2) production drills that
  **don't stop after one word**: it works through everything due, then keeps you
  practicing the *weakest* words until you press **Stop**.
  - *discrimination*: a cloze with a register/context constraint, pick the right
    near-synonym (the answer may be a near-synonym, not the headword — that's the
    point);
  - *antonym contrast*: supply the opposite.
  The Studio UI adds a thick Chinese scaffold before the light test: prompt
  translation, context, blank role, and four large option cards with Chinese
  meaning, usage, and why each near-synonym may fail. Generated scaffolds are
  cached locally, while the underlying drill stays local and instant.
- **My mistakes & weak words** → every answer is logged to `data/reviews.jsonl`
  (with right/wrong), and each word tracks its miss count (`lapses`) and a
  productive-mastery score. This view lists your most-missed words and recent
  wrong answers; the drill prioritizes them.
- **Write a sentence (graded)** → you produce a sentence with a target word;
  Claude grades sense, register, collocation, and naturalness, and offers a
  sharper version.
- **Upgrade an article** → paste a draft; it suggests sharper words, *preferring
  your own learning-words*.
- **Global hotkey** (default ⌘⌥D) fires the next due drill from anywhere.

Your lexicon is stored as **git-versioned JSONL** (`data/lexicon.jsonl`), so your
whole learning history is diffable and portable.

## Setup

1. **Double-click `setup.command`** — creates a Python virtual environment,
   installs dependencies, and builds the starter lexicon (6 professor-level words
   so you can drill immediately).
2. **Double-click `run.command`** — launches the menu-bar app. Look for 📖 (with a
   due-count badge) in your menu bar. You can close the Terminal window; the app
   keeps running.
3. **Double-click `run_native.command`** — launches the Claude Design local
   desktop window (frameless/vibrancy) with Vocab, Expression, Listening Reader,
   Writing, Translate, and Stats.
4. **Double-click `run_studio.command`** only when you want the same Studio in a
   browser tab at `http://localhost:8764`.

### Make it always-on (resident, like a real app)

**Double-click `install_login_item.command`.** This installs a `launchd`
LaunchAgent so WordForge **starts automatically at login, restarts itself if it
ever crashes, and runs menu-bar-only (no Dock icon)** — a true background service.
Your API key is embedded in a user-only (`chmod 600`) plist under
`~/Library/LaunchAgents/` (never in the repo). To stop it for good, double-click
`uninstall_login_item.command`.

For the reading Studio backend, **double-click
`install_studio_login_item.command`**. This keeps the local Studio server alive
at `http://127.0.0.1:8764`, so Translate/Reader routes are ready without asking
Codex to wake anything. To remove that backend service, double-click
`uninstall_studio_login_item.command`.

Once the menu-bar app is running, use **Open Studio Reader** from the 📖 menu to
open the native reading window.

> On a MacBook with a notch, the 📖 icon can hide behind the notch when the menu
> bar is full. A free menu-bar manager like **Ice** (`brew install --cask
> jordanbaird-ice`) gives you a clickable overflow so nothing hides.

### API key

The grounding/grading layer can use Claude or DeepSeek. Provider selection:

- If `WORDFORGE_PROVIDER=deepseek` is set, or the Keychain provider is saved as
  `deepseek`, WordForge uses DeepSeek (`deepseek-chat` by default).
- Otherwise it uses Claude.

Provide API keys one of these ways:

- **Recommended:** open the menu-bar **Settings…** and paste your key — it's saved
  to your macOS **Keychain** for Claude/Anthropic.
- DeepSeek keys can also be saved to the same Keychain service by calling
  `wordforge.config.set_deepseek_api_key(...)`; do not commit keys to files.
- Deepgram keys are optional and only needed for future audio timestamp / live
  speech work. Save one with hidden input:
  `./.venv/bin/python scripts/set_deepgram_key.py`.
- Or export `ANTHROPIC_API_KEY` / `DEEPSEEK_API_KEY` in your shell profile
  (`~/.zshrc`) before launching via `run.command`.

Default Claude model is `claude-opus-4-8`; override with `WORDFORGE_MODEL`.
Default DeepSeek model is `deepseek-chat`; override with `DEEPSEEK_MODEL`.

### Global hotkey & permissions

The ⌘⌥D global hotkey needs **Accessibility** permission: System Settings →
Privacy & Security → Accessibility → enable Python (or WordForge.app). The menu
still works without it.

## CLI (testing / power use)

```
./.venv/bin/python -m wordforge.cli add perfunctory   # ground + add a word
./.venv/bin/python -m wordforge.cli session           # continuous drill (blank line to stop)
./.venv/bin/python -m wordforge.cli session 10        # cap at 10 drills
./.venv/bin/python -m wordforge.cli weak              # your missed / weak words + wrong answers
./.venv/bin/python -m wordforge.cli use perfunctory   # write a sentence, get it graded
./.venv/bin/python -m wordforge.cli stats
./.venv/bin/python -m wordforge.cli list
```

## WordForge Studio (native window + web fallback)

The main UI entry point is `run_native.command`: a local macOS window using the
Claude Design frameless/vibrancy shell. It wraps the Studio server instead of
replacing the engines: vocab drills use the same store/scheduler, Expression
uses the same Claude structured-output ladder, Listening Reader uses the same
whisper.cpp cache, Writing uses the same rubric grader, and Translate uses the
same translation/back-translation grader plus a pre-baked passage corpus.

The Vocab tab is now a single-column learning surface: `Next drill` is the main
screen, with the prompt and near-synonym scaffold kept large enough to read.
`Add a word` is still available, but collapsed below the drill so it does not
crowd the learning task. The mode selector lets you switch between
`Scaffold / 脚手架` and `Blind test / 盲测`: learn with full Chinese support, then
test retrieval without the support.

Vocab does **not** make live model calls while you are drilling. It reads the
local scaffold cache first. If a card has not been pre-baked yet, Studio shows a
local fallback and tells you to run the pre-bake script instead of blocking the
UI with an on-demand DS/Claude call.

To pre-bake the Chinese scaffold cache for all existing multiple-choice vocab
drills, run:

```
./.venv/bin/python scripts/prebake_drill_scaffolds.py
```

The script only generates missing cache rows, so it is safe to rerun. Use this
for Vocab-scale support, where the source data already contains the English
nuance. For literary passage explanations, use the stronger-model/Codex curation
path described in `MULTIMODAL_READING_PLAN.md`.

```
./run_native.command                        # native local desktop window
./.venv/bin/python -m wordforge.studio    # serves http://localhost:8764
```

`run_native.command` checks that the current Studio backend is ready before it
opens the window. If an older stale backend is still occupying `:8764`, it
replaces it so the Translate corpus API is available.

## Translate corpus (中英桥)

The Translate tab now supports both practice loops:

- **E→C · 理解:** pick or paste English, get difficult-word hints, translate
  sentence by sentence, then grade for accuracy, naturalness, and omissions.
- **回译 C→E · 产出:** pick a passage, rebuild the English from a Chinese
  word-order scaffold, then compare against the original and add missed
  words/structures to WordForge.
- For corpus passages, the answer area is split into one input box per sentence.
  Each sentence has local slot hints/palette chips, and you can `Check line` or
  `Check all`.
- **Reading path:** choose one of four public-domain book routes: Emerson
  `Self-Reliance`, Thoreau `Walden`, Douglass `Narrative`, or Shelley
  `Frankenstein`. The route card shows the central question, why the book matters
  for this learning loop, and a button to open the local source PDF.
- **Ask this passage / 问这段:** while reading, ask a local question about the
  selected passage. The answer is in Chinese but anchored to an exact English
  phrase or sentence, with concrete English features to notice next.

Corpus practice has four support levels:

1. tense tags + Chinese hints + clickable word palette;
2. only difficult words and syntax hints;
3. only Chinese-in-English-order scaffold;
4. bare translation / bare back-translation.

The committed seed corpus lives at `data/corpus/passages.jsonl`; the four
reading routes live at `data/corpus/reading_paths.json`. The current public
corpus contains 16 copyright-clean passages from Emerson, Thoreau, Douglass, and
Mary Shelley, chosen for dense, idea-bearing prose.

Local textbook passages, such as OCR from California Edge C, are supported but
not committed:

```
./.venv/bin/python scripts/ocr_edge_pages.py <edge-pdf> --pages 12-13 \
  --id edge-c-unit-01-p012-013 --title "Unit 1 selection" \
  --structure "relative clause" --structure "past perfect"

./.venv/bin/python scripts/build_corpus.py \
  --source-jsonl data/corpus/sources_local/edge_sources.jsonl \
  --out data/corpus/local/edge_passages.jsonl
```

Studio automatically loads completed local packages from `data/corpus/local/`.
Raw OCR rows stay in `data/corpus/sources_local/`; both directories are
gitignored.

Every translation check is logged locally:

```text
data/translate_attempts.jsonl
data/translate_errors.jsonl
```

These are the learner-owned records of what went wrong: wrong sentences, missed
words, and missed structures. They can later power review drills or analytics.

## Reading Lab (预烤阅读器)

The Reader tab now has a second surface above the old listening transcript:
`Reading Lab · 预烤阅读包`. It is for book-like reading, not test drilling.

The first baked package is Emerson's `Self-Reliance`, built from the committed
public-domain corpus. Each passage renders:

- the English source sentence;
- Chinese-in-English-order component text with tense/aspect tags;
- Codex close-reading comments;
- sentence-bound palette chips;
- separate shelves for `Books / 想读的书` and `Lessons / 课文`;
- a lyric-style scroll panel so reading does not become one endless page;
- a sticky selected-source panel so the original sentence does not disappear
  while you ask or read below it;
- `Ask selected sentence`, which answers in Chinese while anchoring attention to
  an exact English phrase.

Package data lives in:

```text
data/reading_packages/emerson_self_reliance.jsonl
```

Rebuild it from the committed corpus with:

```bash
./.venv/bin/python scripts/bake_emerson_reading_packages.py
```

Bake local Deepgram audio for the committed book packages with:

```bash
./.venv/bin/python scripts/bake_reading_audio.py
```

This writes stable local mp3 files and sentence timing hints, so the Reader can
show an audio bar and keep the lyric scroll tied to playback.

For the full `Self-Reliance` essay:

```bash
./.venv/bin/python scripts/bake_self_reliance_full.py
./.venv/bin/python scripts/bake_reading_audio.py \
  --path data/reading_packages/emerson_self_reliance_full.jsonl \
  --model aura-2-zeus-en \
  --speed 1.2 \
  --workers 10
```

The full package is a fast-reading map first: complete public-domain text,
sentence splitting, English TTS, and a sentence-following lyric reader. Close
Chinese scaffolds are still best added to selected passages as you read.

Deepgram TTS is deliberately a small utility, not a Voice Agent integration.
Once a rotated Deepgram key is stored with hidden input:

```bash
./.venv/bin/python scripts/set_deepgram_key.py
```

you can generate local mp3 files from any Codex/DS answer or passage comment:

```bash
echo "Trust thyself: every heart vibrates to that iron string." \
  | ./.venv/bin/python scripts/deepgram_speak.py --slug emerson-trust
```

Generated audio is local-only under `data/reading_audio/` and is gitignored.

Local lesson packages, such as the current Listening Reader lesson transcript,
live under:

```text
data/reading_packages/local/
```

That directory is gitignored because it may contain textbook or classroom text.
Generate the current Listening Reader lesson package with:

```bash
./.venv/bin/python scripts/bake_current_lesson_package.py --index 0
```

Lesson packages can carry audio timestamps, so the Reading Lab can behave like
karaoke: play the local audio, highlight the current line, and keep the selected
source sentence visible while you ask questions.

There is also a no-browser terminal fallback that uses the same local corpus and
does not call Claude unless you ask for final grading:

```
./.venv/bin/python -m wordforge.cli translate
./.venv/bin/python -m wordforge.cli translate --mode e2c --support 2
./.venv/bin/python -m wordforge.cli translate --mode back --support 1 --claude-grade
```

Terminal mode always prints the source text, a separate `word hints` line, the
selected support scaffold, and then records your attempt in
`data/translate_attempts.jsonl`.

## Expression Ladder (web app — figurative range)

For the real expressive gap (reaching for *"his eyes are like sapphires"* vs only
*"like a lake"*). Type a plain thought; it builds a ladder from plain → precise →
simile → metaphor → embedded-in-scene, each rung labeled with the **image** and
the **feeling** it carries; then you write your own version and it grades the
aptness of your image, the connotation match, and the fluency.

```
./.venv/bin/python -m wordforge.express     # serves http://localhost:8766 and opens it
```

## Writing trainer (Claude-graded essays)

A sibling tool that practices *writing* against an academic rubric, grounded in
your TOEFL prompts and California Edge writing projects:

```
./.venv/bin/python -m wordforge.writing prompts          # list prompts (incl. your TOEFL .md files)
./.venv/bin/python -m wordforge.writing new tech-and-attention   # opens a draft to write in
./.venv/bin/python -m wordforge.writing grade <draft.md> # 6-dimension rubric grade
```

Grades on task response / organization / development / grammar / vocabulary /
mechanics (each 0–5), gives a CEFR + TOEFL estimate, quotes your own text in the
fixes, rewrites your weakest paragraph as a model, and surfaces weak words to
`add` to WordForge.

## Listening trainer (dictation from your audio)

Turns your California Edge audio library into dictation practice, fully local.
One-time setup: **double-click `install_listening.command`** (installs whisper.cpp
+ the English model; `afconvert`/`afplay` already ship with macOS). Then:

```
./.venv/bin/python -m wordforge.listening library          # list your audio, numbered
./.venv/bin/python -m wordforge.listening dictate <N>      # play a sentence -> type it -> scored
./.venv/bin/python -m wordforge.listening text <N>         # print the transcript
./.venv/bin/python -m wordforge.listening play <N>         # just listen (extensive)
```

Pipeline: your `.mp3` → `afconvert` → wav → **whisper.cpp** transcript (cached) →
sentence segments → it plays one clip, you type what you heard, and it scores you
word-by-word and lists the words you missed (candidates to `add` to WordForge).
Point it elsewhere with `WORDFORGE_LISTENING_DIR`.

## Listening Reader (web app — read along while you listen)

A local web app (opens in your browser, so it sidesteps the menu-bar/notch
entirely). Pick an Edge audio file, press play, and the transcript **scrolls and
highlights in sync**; click any line to jump there; one button opens that unit's
folder to grab the source PDF.

```
./.venv/bin/python -m wordforge.reader     # serves http://localhost:8765 and opens it
```

Transcription is local **whisper.cpp** (cached per file) — no cloud, no API key,
no per-minute cost. (Deepgram-style live streaming is intentionally not used:
for pre-recorded files local whisper is better; a live/streaming mode can be
added later if you want to transcribe a lecture in real time.) Needs the same
one-time `install_listening.command` setup.

For the next reading shape, see `MULTIMODAL_READING_PLAN.md`: a passage package
with audio, timestamped English scroll, Chinese word-order components, DS
explanations, and selected-sentence Ask. Deepgram can provide timestamps when
there is audio and a key, but it does not replace the need for an audio source.

## Optional: standalone .app

`build_app.command` builds `dist/WordForge.app` (Dock-less, add to Login Items)
via py2app. `run.command` already launches the native menu-bar app, so this is
just polish. When run as a bundle, the lexicon lives in `~/Documents/WordForge`.

## Layout

```
wordforge/
  config.py      paths, model, API key (env or Keychain), hotkey
  store.py       JSONL lexicon + review log
  scheduler.py   SM-2 spaced repetition (production-graded)
  grounding.py   Claude: ground word, grade sentence, upgrade article
  drills.py      drill selection + local answer checking
  app.py         menu-bar app (rumps) + global hotkey (pynput)
  cli.py         headless CLI
  data/seed_words.jsonl   shipped starter lexicon
data/            your live lexicon.jsonl + reviews.jsonl (git-versioned)
scripts/build_seed.py     regenerates the starter lexicon
```

## Roadmap

- Speaking/fluency mode: timed production (cue → say it fast), then TTS
  pronunciation + Whisper auto-check.
- Semantic retrieval (embeddings) so "words for [vague meaning]" surfaces your
  own learned words first.
- FSRS scheduler (swap in via the `fsrs` package) behind the current SM-2 interface.
