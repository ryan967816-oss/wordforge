# WordForge Studio — UI Design Brief (prompt for Claude Design)

**Paste this whole file to Claude Design (and optionally point it at the repo
`github.com/ryan967816-oss/wordforge`, file `wordforge/studio.py`).** Your job is
to redesign the front end only — same backend, same API. Deliver markup we can
drop straight into the existing local server.

---

## What WordForge Studio is
A personal English-mastery study app for an advanced learner. It runs **locally**
as one web app at `http://localhost:8764`, served by a tiny Python stdlib HTTP
server (`wordforge/studio.py`). Five training modes share one page (a sidebar
single-page app): **Vocab, Expression, Reader, Writing, Stats**. The current UI
works but looks like a developer dashboard; we want it *designed*.

## Aesthetic — COLD / ICY (this is the whole point)
Mood: **glacier, sapphire, a winter sky over snow.** Cold clarity — crystalline,
precise, restrained, quiet. Beauty that keeps its distance. Dark theme.

- **Palette (cold only — no warm tones):**
  - background: deep glacial ink `#0A0D12`; panels `#10141B`; raised cards `#141A22`.
  - hairlines/borders: cold slate `#1E2730` (1px, thin, sharp).
  - text: frost white `#E8EEF5` primary; cold gray `#8A95A5` secondary; faint `#5A6472`.
  - **single accent: glacial sapphire** `#5B8FD6` (and a brighter ice `#8FC0F0` for
    the *active* state — current transcript line, active nav, focus ring). Use the
    accent sparingly; the coldness comes from restraint, not blue everywhere.
- **Type:** a precise sans for UI/data (system-ui / Inter). A refined, slightly
  cold **serif** (e.g. Spectral, Newsreader, or Georgia) ONLY for the literary
  content — the Expression ladder renderings and Writing's model paragraph — so
  the *language* is the hero. Everything else stays sans.
- **Texture:** flat. No gradients, no glows, no drop shadows, no neon. Thin 1px
  hairlines, small sharp corners (4–8px), generous negative space, a sense of
  air and ice. Transitions subtle and quick (≤120ms).
- Think: a frozen lake at dusk, a cut sapphire, the flat blue of a winter sky.
  NOT a glossy SaaS dashboard, NOT cozy, NOT playful.

## Hard delivery constraints (or it won't work)
1. **One self-contained `.html`**: inline `<style>` + inline vanilla `<script>`.
   **No React, no framework, no build step, no bundler.** It becomes a single
   Python string (`PAGE`) inside `studio.py`.
2. **Keep the real API calls.** Bind the UI to the endpoints below with `fetch`.
   You may show placeholder data for preview, but the actual `fetch(path)` calls
   and the JSON field names must match exactly so it works against the live server.
3. External fonts via Google Fonts are OK; everything else must run offline.
   No `position: fixed`. Works at desktop **and** 390px mobile (sidebar collapses
   to a top row). Dark only.
4. Don't change backend behavior, routes, or JSON shapes.

## The five views (content + behavior)

**Sidebar nav:** WordForge wordmark + 5 items (Vocab / Expression / Reader /
Writing / Stats); switching shows one view at a time.

### 1. Vocab
- A metric strip: words, due now, reviewed today, avg production.
- "Add a word": text input + Add button → `POST /api/add`.
- "Next drill": shows `GET /api/drill`. If `drill.options` exist, render them as
  clickable choices (the answer may be a near-synonym, not the headword — that's
  the point); else a text input. On answer → `POST /api/drill/answer`, show
  correct/explanation, then auto-load the next drill.

### 2. Expression (the hero — make this beautiful)
- A textarea for a plain thought + "Show ladder" → `POST /api/expression/ladder`.
- Render the returned `feeling_question` as the framed choice, then each `rung`
  as a card: a small `kind` tag (plain → precise adjective → simile → metaphor →
  in a scene — a visible *climb*), the **`rendering` set in the serif, large**,
  and a meta line `image` · `connotation` (the feeling). This is where the cold
  serif typography should sing.
- Then "Your version": textarea + Grade → `POST /api/expression/grade`, show
  score / image_apt / connotation_match / fluency / feedback / better_version.

### 3. Reader (listening read-along)
- A `<select>` of audio from `GET /api/listening/list` → `[{i,name}]`.
- `<audio controls src="/api/listening/audio?i=N">`.
- Transcript from `GET /api/listening/transcript?i=N` → `[{start_ms,end_ms,text}]`,
  rendered as lines; on `audio.timeupdate` highlight + auto-scroll the current
  line (this is the signature moment — the **active line should glow cold**, a
  thin sapphire left-border + brighter text). Click a line → seek. An "Open
  folder" button → `GET /api/listening/pdf?i=N`.

### 4. Writing
- A `<select>` of prompts from `GET /api/writing/prompts` → `[{id,preview,prompt}]`.
- A large textarea + "Grade essay" → `POST /api/writing/grade`.
- Render the result: `level_estimate` + `overall_band`/5, the six `dimensions`
  (name, band/5, comment), `priority_fixes` (issue, from_your_text, how_to_fix),
  `model_paragraph` (serif), and `weak_words`.

### 5. Stats
- The same metric strip, plus two lists: `weak_words` (headword, lapses,
  production_score, due) and `recent_mistakes` (headword, kind, ts).

## API contract (exact — bind to these)
```
GET  /api/stats            -> { stats:{total_words,due_now,reviewed_today,reviews_total,avg_production_score},
                                 weak_words:[{headword,lapses,production_score,due}],
                                 recent_mistakes:[{headword,kind,ts}] }
GET  /api/drill            -> { empty, message?, headword, core_sense, practice, next_cursor,
                                 drill:{kind, prompt, options?[], answer, explanation} }
POST /api/drill/answer     <- { headword, drill, answer, practice, next_cursor }   -> { correct, grade, explanation, answer }
POST /api/add              <- { term }            -> { created, word:{headword,pos,core_sense,image,register,frequency} }
POST /api/expression/ladder<- { thought }         -> { feeling_question, note, rungs:[{kind,rendering,image,connotation,register}] }
POST /api/expression/grade <- { thought, attempt }-> { score, image_apt, connotation_match, fluency, feedback, better_version }
GET  /api/listening/list   -> [{ i, name }]
GET  /api/listening/transcript?i=N -> [{ start_ms, end_ms, text }]
GET  /api/listening/audio?i=N      -> audio/mpeg (supports HTTP Range for seeking)
GET  /api/listening/pdf?i=N        -> { ok }
GET  /api/writing/prompts  -> [{ id, preview, prompt }]
POST /api/writing/grade    <- { prompt_id, essay } -> { level_estimate, overall_band,
                                 dimensions:[{name,band,comment}], strengths[],
                                 priority_fixes:[{issue,from_your_text,how_to_fix}], model_paragraph, weak_words[] }
```
POST bodies are JSON. Loading states matter: `/api/add`, both `/api/expression/*`,
and `/api/writing/grade` call Claude and take a few seconds — show a quiet
"thinking" state, disable the button.

## Hand-back
Return the single `.html`. We replace the `PAGE` string in `wordforge/studio.py`
with its contents (keeping the `fetch` paths). Then it's live at `:8764`.
