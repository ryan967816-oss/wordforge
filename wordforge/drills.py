"""Drill selection and answer checking (no UI, no network).

The v1 spine is synonym/antonym *discrimination*: given a sentence with a blank
and a register/context constraint, pick the right near-synonym; or supply the
antonym. These are graded locally from the stored drill data, so daily drilling
is instant and works offline — Claude is only spent at ingest (grounding) and on
the optional generative-use drill (grading your own sentence).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from . import store


def next_due_word(words: list[dict[str, Any]], at: datetime | None = None) -> dict[str, Any] | None:
    due = store.get_due(words, at or datetime.now(timezone.utc))
    return due[0] if due else None


def _drill_pool(word: dict[str, Any]) -> list[dict[str, Any]]:
    """Interleave discrimination and antonym drills, tagged by kind."""
    pool: list[dict[str, Any]] = []
    for d in word.get("discrimination_drills", []) or []:
        pool.append({"kind": "discrimination", **d})
    for d in word.get("antonym_drills", []) or []:
        pool.append({"kind": "antonym", **d})
    return pool


def pick_drill(word: dict[str, Any]) -> dict[str, Any] | None:
    """Return the next drill item for a word, cycling through its pool. Mutates
    `drill_cursor` on the word (caller is responsible for persisting)."""
    pool = _drill_pool(word)
    if not pool:
        return None
    cursor = int(word.get("drill_cursor", 0))
    item = pool[cursor % len(pool)]
    word["drill_cursor"] = cursor + 1
    return item


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def check_answer(word: dict[str, Any], drill: dict[str, Any], user_answer: str) -> tuple[bool, str]:
    """Return (correct, explanation). Accepts the answer text, or — for
    discrimination drills — the option's 1-based number."""
    answer = drill.get("answer", "")
    ua = user_answer.strip()
    correct = False

    if drill.get("kind") == "discrimination":
        options = drill.get("options", []) or []
        # Allow answering by number ("2") or by the option text. The numeric path
        # is terminal: a digit is judged solely by the option it selects, so a
        # selection digit can't coincidentally equal a digit-valued answer text.
        if ua.isdigit():
            idx = int(ua) - 1
            correct = 0 <= idx < len(options) and _normalize(options[idx]) == _normalize(answer)
        else:
            correct = _normalize(ua) == _normalize(answer)
    else:  # antonym
        if _normalize(ua) == _normalize(answer):
            correct = True
        else:
            # Accept any listed antonym of the word as also correct.
            for a in word.get("antonyms", []) or []:
                if _normalize(ua) == _normalize(a.get("word", "")):
                    correct = True
                    break

    return correct, drill.get("explanation", "")


def grade_for_correctness(correct: bool) -> str:
    """Map a binary discrimination/antonym result to a scheduler grade."""
    return "good" if correct else "again"


SCORE_TO_GRADE = {"excellent": "easy", "good": "good", "weak": "hard", "wrong": "again"}
