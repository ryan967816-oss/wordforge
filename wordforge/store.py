"""JSONL-backed lexicon store.

One word per line in `lexicon.jsonl` — human-readable, git-diffable, portable.
Reviews are appended to `reviews.jsonl` as an immutable log. For thousands of
words this loads fully into memory each call, which is plenty fast and keeps the
store dependency-free (no SQLite binary blob to fight git over).

A word record (dict) has these keys:
  Grounding (from Claude or seed):
    headword, pos, core_sense, image, register, frequency,
    synonyms[{word,nuance,register,example}], antonyms[{word,note}],
    collocations[str], examples[str], confusions[{word,difference}],
    discrimination_drills[{prompt,options,answer,explanation}],
    antonym_drills[{prompt,answer,explanation}]
  Scheduling / progress (managed by scheduler + drills):
    added (iso), ease, interval (days), reps, lapses, due (iso),
    production_score (int), drill_cursor (int), last_reviewed (iso|None)
"""

from __future__ import annotations

import fcntl
import json
import os
import shutil
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import config


@contextmanager
def _file_lock():
    """Cross-process exclusive lock (menu-bar app and CLI share one lexicon).

    Wrap each read-modify-write so two processes can't interleave and silently
    clobber each other's edits. flock is advisory but honored by every WordForge
    writer, which is all we need on a single machine. Do not nest these.
    """
    lock_path = config.data_dir() / ".lock"
    f = open(lock_path, "w")
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        f.close()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def soon_iso(minutes: int = 10) -> str:
    """A near-future timestamp — used to resurface a just-missed word shortly,
    without making it 'due now' and re-triggering the same single word."""
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def parse_iso(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                # Tolerate a torn/edited line (e.g. a crash mid-append) rather
                # than letting one bad record brick every read. Skip it.
                continue
    return out


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    # Write atomically and durably: write a temp file, fsync it, then rename.
    # The rename is atomic w.r.t. visibility; the fsyncs make the data survive a
    # crash so the rename can't expose a truncated file.
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)
    dirfd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(dirfd)
    finally:
        os.close(dirfd)


def _ensure_seeded() -> None:
    """On first run, copy the shipped seed lexicon into the live lexicon."""
    lex = config.lexicon_path()
    if lex.exists():
        return
    seed = config.seed_path()
    if seed.exists():
        # Copy atomically: the lexicon is either absent (re-seed can retry) or a
        # complete copy — never a truncated file that blocks re-seeding forever.
        tmp = lex.with_suffix(lex.suffix + ".tmp")
        shutil.copyfile(seed, tmp)
        tmp.replace(lex)
    else:
        lex.touch()


def load_words() -> list[dict[str, Any]]:
    _ensure_seeded()
    return _read_jsonl(config.lexicon_path())


def save_words(words: list[dict[str, Any]]) -> None:
    _write_jsonl(config.lexicon_path(), words)


def find_word(words: list[dict[str, Any]], headword: str) -> dict[str, Any] | None:
    hw = headword.strip().lower()
    for w in words:
        if w.get("headword", "").strip().lower() == hw:
            return w
    return None


def add_word(word: dict[str, Any]) -> bool:
    """Add a grounded word with fresh scheduling fields. Returns False if it
    already exists (updates grounding in place instead, keeping schedule)."""
    scheduled = _with_schedule_defaults(word)
    with _file_lock():
        # Re-read fresh inside the lock so a concurrent writer's changes aren't lost.
        words = load_words()
        existing = find_word(words, word["headword"])
        if existing is not None:
            # Preserve the learner's schedule/progress; refresh grounding content.
            for k in (
                "pos", "core_sense", "image", "register", "frequency", "synonyms",
                "antonyms", "collocations", "examples", "confusions",
                "discrimination_drills", "antonym_drills",
            ):
                if k in word:
                    existing[k] = word[k]
            save_words(words)
            return False
        words.append(scheduled)
        save_words(words)
        return True


def update_word(word: dict[str, Any]) -> None:
    with _file_lock():
        # Re-read fresh inside the lock and replace only the matching record, so
        # a concurrent edit to a *different* word isn't clobbered.
        words = load_words()
        for i, w in enumerate(words):
            if w.get("headword", "").lower() == word.get("headword", "").lower():
                words[i] = word
                save_words(words)
                return
        words.append(word)
        save_words(words)


def _with_schedule_defaults(word: dict[str, Any]) -> dict[str, Any]:
    w = dict(word)
    w.setdefault("added", now_iso())
    w.setdefault("ease", 2.5)
    w.setdefault("interval", 0)
    w.setdefault("reps", 0)
    w.setdefault("lapses", 0)
    w.setdefault("due", now_iso())  # due immediately
    w.setdefault("production_score", 0)
    w.setdefault("drill_cursor", 0)
    w.setdefault("last_reviewed", None)
    return w


def get_due(words: list[dict[str, Any]], at: datetime | None = None) -> list[dict[str, Any]]:
    at = at or datetime.now(timezone.utc)
    due = [w for w in words if parse_iso(w.get("due", now_iso())) <= at]
    due.sort(key=lambda w: parse_iso(w.get("due", now_iso())))
    return due


def weak_list(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Words ranked weakest-first: most lapses, then lowest production score,
    then soonest due. Drives 'extra practice' and the mistakes view."""
    return sorted(
        words,
        key=lambda w: (-int(w.get("lapses", 0)),
                       int(w.get("production_score", 0)),
                       w.get("due", "")),
    )


def weakest_word(words: list[dict[str, Any]]) -> dict[str, Any] | None:
    ranked = weak_list(words)
    return ranked[0] if ranked else None


def recent_mistakes(limit: int = 20) -> list[dict[str, Any]]:
    """Most recent wrong answers from the review log (newest first)."""
    reviews = _read_jsonl(config.reviews_path())
    wrong = [r for r in reviews if r.get("correct") is False or r.get("grade") == "again"]
    return list(reversed(wrong))[:limit]


def append_review(record: dict[str, Any]) -> None:
    record = dict(record)
    record.setdefault("ts", now_iso())
    path = config.reviews_path()
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with _file_lock():
        # Single write of the whole serialized line, flushed + fsynced, under the
        # lock — so it can't interleave with another writer or leave a torn line.
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())


def stats() -> dict[str, Any]:
    words = load_words()
    now = datetime.now(timezone.utc)
    due = get_due(words, now)
    reviews = _read_jsonl(config.reviews_path())
    today = now.date().isoformat()
    reviewed_today = sum(1 for r in reviews if r.get("ts", "").startswith(today))
    total_score = sum(w.get("production_score", 0) for w in words)
    return {
        "total_words": len(words),
        "due_now": len(due),
        "reviews_total": len(reviews),
        "reviewed_today": reviewed_today,
        "avg_production_score": round(total_score / len(words), 2) if words else 0.0,
    }
