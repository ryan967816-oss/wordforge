# WordForge — Architecture & Vision

A personal **English-mastery system** for an advanced learner (a physician headed
to clinical training in the US). The north star is **native-level expressive
command** — not vocabulary size or technical terms, but (a) *productive* command
(summon the exact word/image under pressure) and (b) *fluency* (think in English
and render it smoothly). Built local-first, git-versioned, with Claude for
judgment and local whisper.cpp for speech.

## The five pillars (and what serves each)

| Pillar | What it trains | Module | UI | Status |
|---|---|---|---|---|
| **Vocabulary** (productive + nuance) | summon/choose the exact word; synonym/antonym discrimination | `wordforge.cli` + `wordforge.app` | menu-bar + CLI | ✅ |
| **Writing / Expression** | render a thought; figurative range (the "sapphire vs lake" gap) | `wordforge.express` (ladder), `wordforge.writing` (essays) | studio + web + CLI | ✅ |
| **Listening** | parse the speech stream; dictation + read-along | `wordforge.listening` (dictation), `wordforge.reader` (synced transcript) | studio + web + CLI | ✅ |
| **Reading / Translation bridge** | comprehensible input → reconstructive output; text structure + vocabulary tail | `wordforge.translate`, `wordforge.corpus` | studio | ✅ seed + local OCR path |
| **Speaking** | automaticity; shadowing; pronunciation | (shadowing mode = backlog) | — | ⛏ backlog |

The honest framing throughout: **these tools accelerate the *deliberate* slice;
the bulk of native command comes from volume of reading + listening over years.**
The tool is a force-multiplier, not a substitute for input hours.

## Design principles (load-bearing — keep these)

1. **Production, not recognition.** Every drill makes the learner *produce*
   (summon a word, write a sentence, render an image, type what they heard),
   never just recognize. This is the whole differentiator vs. flashcard apps.
2. **Local-first & git-versioned.** The learner's data (lexicon, reviews,
   writing, transcripts) lives as diffable JSONL/markdown under `data/`. Big
   binaries (whisper model, audio caches) are gitignored.
3. **Claude for judgment, structured outputs.** All grounding/grading/generation
   goes through the Anthropic SDK with `output_config.format` (JSON-schema) so
   results are always valid. Default model `claude-opus-4-8`
   (`WORDFORGE_MODEL=claude-sonnet-4-6` to cut cost). One client/helper:
   `grounding._structured_call(system, user, schema, max_tokens)` — reuse it.
4. **Local whisper.cpp for speech.** `mp3 → afconvert (built-in) → wav →
   whisper-cli → segments (cached)`. No cloud, no key. Deepgram is reserved for a
   future *live-streaming* mode only (pre-recorded files don't need it).
5. **Web UI to dodge the macOS-26 notch.** The learner is on a notched MacBook
   Air; menu-bar icons hide behind the notch. New interactive tools are **local
   web apps** (stdlib `http.server`, open in browser) — robust, no notch, no
   packaging. The menu-bar `app.py` remains for the always-resident vocab badge.
6. **Honest scope.** Edge ELD tops out ~US-high-school; the literary/expressive
   layer needs real prose as input. Say the limit; don't oversell the tool.

## Module map

```
wordforge/
  config.py      paths, model, API key (env→Keychain), data dir (repo/data or ~/Documents/WordForge when frozen)
  store.py       JSONL lexicon + reviews; file-lock + atomic/fsync; weak_list/recent_mistakes
  scheduler.py   SM-2 (production-graded); pluggable (FSRS swap-in later)
  grounding.py   Claude: ground_word / grade_sentence / upgrade_article + _structured_call (reused everywhere)
  drills.py      drill selection (rotation) + local answer checking
  cli.py         vocab CLI (add/session/weak/use/...)
  app.py         menu-bar app (rumps) + hotkey; LaunchAgent-resident; Dock-hidden
  writing.py     essay trainer (6-dim rubric); CLI; discovers ~/Documents/toefl prompts
  express.py     EXPRESSION-LADDER web app (:8766) — concept→image-ladder + grade attempt
  translate.py   中英桥 engine — E→C prep/grade + C→E scaffold/grade
  corpus.py      passage corpus loader — committed public seed + gitignored local textbook packages
  listening.py   dictation trainer (whisper.cpp) — CLI
  reader.py      LISTENING READER web app (:8765) — synced scrolling transcript + seek + PDF jump
  studio.py      WORDFORGE STUDIO web app (:8764) — Vocab + Expression + Reader + Writing + Translate + Stats
data/            lexicon.jsonl, reviews.jsonl, writing/, express/, corpus/passages.jsonl  (git-versioned)
data/corpus/local/ and data/corpus/sources_local/  private textbook packages/OCR rows (gitignored)
models/          ggml-base.en.bin (gitignored)         data/listening/  (wav+transcript cache, gitignored)
run_studio.command  install_listening.command  setup_app.py / build_app.command  install/uninstall_login_item.command
```

## Data model (a word record)

Grounding fields: `headword, pos, core_sense, image, register, frequency,
synonyms[{word,nuance,register,example}], antonyms[{word,note}], collocations[],
examples[], confusions[{word,difference}], discrimination_drills[{prompt,options,
answer,explanation}], antonym_drills[{prompt,answer,explanation}]`.
Schedule/progress: `added, ease, interval, reps, lapses, due, production_score,
drill_cursor, last_reviewed`. One word per line in `data/lexicon.jsonl`.

## How to run

```
python -m wordforge.cli session       # vocab drills (continuous, rotating)
python -m wordforge.studio            # unified web studio (web :8764)
python -m wordforge.express           # expression ladder (web :8766)
python -m wordforge.writing prompts   # essay trainer
python -m wordforge.reader            # listening read-along (web :8765)
python -m wordforge.listening library # dictation
```

## The learner's materials (verified)

- **California Edge** (Nat Geo/Hampton-Brown) ELD: levels F/A/B/C × 7 units.
  Reading PDFs (~3000pp, scanned) in `~/Documents/english_training/`; multimedia
  units in `~/Documents/english for listening /` (note trailing space): **432
  mp3** (selection / fluency-shadowing / language-model audio), writing projects
  with rubrics, grammar/writing workbooks.
- **TOEFL** prompts in `~/Documents/toefl/写作-Writing/*.md` (auto-discovered by `writing.py`).
- **ArguMentor / 大辩** debate-judge web app in `~/Documents/ArguMentor/` — its
  `/api/transcribe` is a 501 stub (no working ASR); but its BP + liberal-arts
  **retrieval corpora** are real and reusable for an argument/rhetoric pillar.

See `CODEX_BACKLOG.md` for the prioritized heavy work.
