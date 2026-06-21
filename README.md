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
- **Drill due words** → spaced-repetition (SM-2) production drills:
  - *discrimination*: a cloze with a register/context constraint, pick the right
    near-synonym;
  - *antonym contrast*: supply the opposite.
  These are graded locally from stored data, so daily drilling is instant and
  offline.
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

### API key

The grounding/grading uses the Claude API. Provide your Anthropic key one of two ways:

- **Recommended:** open the menu-bar **Settings…** and paste your key — it's saved
  to your macOS **Keychain** (this is the durable path, and the only one that
  works for the optional `.app` bundle, which gets no shell environment).
- Or export `ANTHROPIC_API_KEY` in your shell profile (`~/.zshrc`) before launching
  via `run.command`.

Default model is `claude-opus-4-8`. To cut grounding cost ~40% at a small quality
tradeoff, launch with `WORDFORGE_MODEL=claude-sonnet-4-6`.

### Global hotkey & permissions

The ⌘⌥D global hotkey needs **Accessibility** permission: System Settings →
Privacy & Security → Accessibility → enable Python (or WordForge.app). The menu
still works without it.

## CLI (testing / power use)

```
./.venv/bin/python -m wordforge.cli add perfunctory   # ground + add a word
./.venv/bin/python -m wordforge.cli drill             # one due drill
./.venv/bin/python -m wordforge.cli session 10        # up to 10 due drills
./.venv/bin/python -m wordforge.cli use perfunctory   # write a sentence, get it graded
./.venv/bin/python -m wordforge.cli stats
./.venv/bin/python -m wordforge.cli list
```

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
