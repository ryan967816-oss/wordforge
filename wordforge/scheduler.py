"""Spaced-repetition scheduler (SM-2), graded on *production*.

SM-2 is the battle-tested, dependency-free algorithm behind Anki's legacy mode.
We grade with four buttons mapped to SM-2's 0-5 quality scale:

    again -> q=1  (lapse: you couldn't produce it)
    hard  -> q=3  (produced, but with effort)
    good  -> q=4  (produced correctly)
    easy  -> q=5  (produced instantly, automatic)

`production_score` tracks *active* mastery separately from the schedule: it goes
up when you produce a word and down when you lapse — the number that says "this
is now in my productive vocabulary," not just recognizable.

The scheduler interface is intentionally narrow (one function mutating a word
dict) so a stronger scheduler (FSRS via the `fsrs` package) can drop in later.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

GRADE_Q = {"again": 1, "hard": 3, "good": 4, "easy": 5}
MIN_EASE = 1.3


def review(word: dict[str, Any], grade: str, at: datetime | None = None) -> dict[str, Any]:
    """Apply a review grade in place and return the word. `grade` is one of
    again / hard / good / easy."""
    if grade not in GRADE_Q:
        raise ValueError(f"unknown grade: {grade!r}")
    at = at or datetime.now(timezone.utc)
    q = GRADE_Q[grade]

    ease = float(word.get("ease", 2.5))
    interval = int(word.get("interval", 0))
    reps = int(word.get("reps", 0))
    lapses = int(word.get("lapses", 0))
    score = int(word.get("production_score", 0))

    if q < 3:
        # Lapse: reset repetitions, re-show soon (same day), bump lapse counter.
        reps = 0
        interval = 0
        lapses += 1
        score = max(0, score - 1)
        next_due = at + timedelta(minutes=10)
    else:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = max(1, round(interval * ease))
        # Hard pulls the interval in; easy pushes it out.
        if grade == "hard":
            interval = max(1, round(interval * 0.6))
        elif grade == "easy":
            interval = round(interval * 1.3)
        reps += 1
        score += 2 if grade == "easy" else 1
        next_due = at + timedelta(days=interval)

    # SM-2 ease-factor update.
    ease = ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    ease = max(MIN_EASE, ease)

    word["ease"] = round(ease, 3)
    word["interval"] = interval
    word["reps"] = reps
    word["lapses"] = lapses
    word["production_score"] = score
    word["due"] = next_due.isoformat()
    word["last_reviewed"] = at.isoformat()
    return word
