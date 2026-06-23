# Codex Brief — build the passage corpus (中英桥 training content)

Handoff to Codex. Read `ARCHITECTURE.md` + `CODEX_BACKLOG.md` first. This brief is
self-contained: build a large, pre-baked **corpus of translation-training passages**
so the Translate pillar (and Reader/Writing/Vocab) ship with rich ready content
instead of being paste-your-own. Ming is final authority; no irreversible actions
without approval.

## The point (理念 — keep this in the data, not just the code)
- **Production, not recognition.** Content must support *generating* English/Chinese, not picking from MCQs.
- **Thick scaffold to "touchable", not harder.** Each passage ships with maximal support (tense-tagged scaffold, full word palette with usage) so the learner *selects and assembles*, then the support thins as he internalizes. Lower the barrier; never raise difficulty for its own sake.
- **Verification ≠ learning.** The vocab drills are a *benchmark*; this corpus is the *construction* material. Missed words from translation feed the vocab库 (the test layer).
- **中英桥.** Leverage the learner's strong Chinese center; build E↔C bridges, rebuild only what must be rebuilt.

## What to build
A corpus of **passage packages**, each fully pre-computed (so the app loads instantly, no live API for scaffolds), stored as JSONL.

### Source texts (in priority order)
1. **California Edge, level C** (Advanced) — the learner's own textbook. Reading PDFs at `~/Documents/english_training/edge-C-A-*.pdf` and `edge-C-B-*.pdf` (scanned ~100MB each; `~/Documents/english_training/INDEX.md` maps files→page ranges). These are scanned images → OCR per selection: render the relevant pages to images (`pdftoppm`/`sips`) and read them with the Claude API document/vision blocks, or pass page ranges as PDF document blocks. Do ONE selection at a time (size/cost). Extract the reading selection's text + its "Key Vocabulary".
2. **If a selection is impractical to extract, choose high-quality texts yourself**, by these criteria: CEFR B2–C1; ~80–200 words; **structurally varied** for scaffold value (relative clauses, past perfect, participles, passives, inversion, that-clauses); literary or academic register matching the learner's goal (professor-level expressive command); **copyright-clean** (public-domain literature/essays, or Edge-owned). Record the source honestly.

### Per-passage package (the schema — mirror `wordforge/translate.py` outputs)
One JSON object per line in `data/corpus/passages.jsonl`:
```json
{
  "id": "edge-c-a-u1-s1",
  "source": "Edge C, Book A, Unit 1 — <selection title>, p.NN",
  "level": "C1",
  "title": "<short title>",
  "text_en": "<the English passage>",
  "target_structures": ["non-restrictive relative clause", "past perfect", "see + bare infinitive"],
  "glosses": [{"word": "elusive", "hint": "hard to capture", "chinese": "难以捉摸的"}],
  "scaffold": "<Chinese in ENGLISH word order, with inline tense/aspect tags on every verb, e.g. 花费[过去完成 had+pp] … and structural pivots 定语从句起点/被动/倒装>",
  "palette": [{"english": "had spent", "chinese": "花费了(之前)", "usage": "过去完成时,在 saw 之前;spend+时间"}],
  "grammar": ["主句 saw 用一般过去；从句 had spent 用过去完成表更早"],
  "note": "<one line on the main word-order difference>",
  "vocab_targets": ["elusive", "vindicate", "flicker"]
}
```
- `glosses` = `prep_e2c(text).hard_words`. `scaffold`/`palette`/`grammar`/`note` = `make_scaffold(text)`. Reuse those functions to GENERATE the package (don't hand-author the JSON):
  `from wordforge import translate; s = translate.make_scaffold(text); g = translate.prep_e2c(text)`.
- `vocab_targets` = the hard/target words → also feed `wordforge.store.add_word(grounding.ground_word(w))` so the corpus stocks the vocab库 (the benchmark layer).

### Build it like the word library (reuse the pattern)
- Model `scripts/build_corpus.py` on `scripts/build_library.py`: read a list of source texts → for each, run `make_scaffold` + `prep_e2c` → write the package to `data/corpus/passages.jsonl`. Concurrent, **resume-safe** (skip ids already present). 
- **Cost:** prefer the subscription via a Workflow of subagents (as was done for the last 74 words) over the metered API for bulk. Each agent: given a source text, produce the package JSON (matching the schema) and write it to a staging file; then a loader merges into `passages.jsonl`. Reuse `grounding._structured_call` / the schemas in `translate.py` so output is always valid.
- Scale: start ~50–100 passages spanning difficulty + structure variety; expandable. `log()` what was skipped (no silent truncation).

## Wire it into the app (so it's "pick a passage", not paste-only)
Add to `wordforge/studio.py` (and the engine):
- `GET /api/translate/corpus` → `[{id, title, level, source, target_structures}]` (list).
- `GET /api/translate/corpus/get?id=...` → the full package.
- In `wordforge/studio_page.html` Translate tab: a **"Pick a passage"** selector above the paste box. Choosing one loads `text_en` into the source box AND shows the pre-baked `scaffold`/`palette`/`glosses`/`grammar` **with no live API call** (instant). Grading (`grade_back`/`grade_e2c`) stays live. Keep paste-your-own as the other option.
- Optional: filter by level / target_structure so the learner can drill a specific structure (e.g. "give me 10 past-perfect passages").

## Boundaries / conventions
- Reuse `grounding._structured_call` + the JSON-schema structured-output approach; default model `claude-opus-4-8` (or `WORDFORGE_MODEL=claude-sonnet-4-6` for cheaper bulk).
- Don't break the data model (`data/lexicon.jsonl` records) or `store.py`'s file-lock/atomic-write. `models/` + `data/listening/` stay gitignored; decide whether `data/corpus/` is committed (it's content, probably yes) — confirm with Ming.
- **Cite sources** in `source`; keep copyright-clean. No secrets in the repo.
- Verify with real runs; land evidence (counts, a sample package, the working selector).

## Acceptance
- `data/corpus/passages.jsonl` with ≥50 valid packages (varied level + structure), each with text + glosses + tense-tagged scaffold + palette + grammar + vocab_targets.
- Studio Translate tab has a working "Pick a passage" selector that loads a pre-baked passage instantly; grading + "Add missed to库" still work.
- `scripts/build_corpus.py` is resume-safe and re-runnable to grow the corpus.

*Repo: `github.com/ryan967816-oss/wordforge` (public).*
