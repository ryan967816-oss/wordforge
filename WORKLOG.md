# WordForge Worklog

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
