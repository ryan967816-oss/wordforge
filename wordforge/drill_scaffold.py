"""Chinese scaffolds for vocabulary discrimination drills.

The base drill remains local/offline. This module adds an optional cached layer:
translate the prompt, name the context, and explain each near-synonym option in
Chinese. Once generated, a scaffold is reused from ``data/drill_scaffolds.jsonl``.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config, grounding


SCAFFOLD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "prompt_zh": {"type": "string"},
        "context_hint_zh": {"type": "string"},
        "blank_role_zh": {"type": "string"},
        "option_cards": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "word": {"type": "string"},
                    "chinese": {"type": "string"},
                    "use_zh": {"type": "string"},
                    "example_zh": {"type": "string"},
                    "trap_zh": {"type": "string"},
                },
                "required": ["word", "chinese", "use_zh", "example_zh", "trap_zh"],
            },
        },
        "decision_rule_zh": {"type": "string"},
    },
    "required": [
        "prompt_zh",
        "context_hint_zh",
        "blank_role_zh",
        "option_cards",
        "decision_rule_zh",
    ],
}

SCAFFOLD_SYSTEM = """You are building a thick Chinese learning scaffold for an advanced
English vocabulary discrimination drill. The learner is not trying to pass a test cold;
they are trying to feel the difference between near-synonyms.

Return:
- prompt_zh: faithful Chinese translation of the whole prompt. Preserve the blank as ___.
- context_hint_zh: what situation/register the prompt is asking for.
- blank_role_zh: what kind of word should fill the blank, in Chinese.
- option_cards: one card for EACH option, in the same order. For each option:
  - word: exact option text.
  - chinese: compact Chinese gloss.
  - use_zh: when this word is the right choice; mention register/collocation.
  - example_zh: Chinese explanation of the example/use, not a new English example.
  - trap_zh: why this option may look close but may fail in this prompt.
- decision_rule_zh: the final choosing rule in one or two Chinese sentences.

Do not hide useful support. This is a wheelchair scaffold by design. Do not be vague."""


def cache_path() -> Path:
    return config.data_dir() / "drill_scaffolds.jsonl"


@contextmanager
def _cache_lock():
    lock_path = config.data_dir() / ".drill_scaffolds.lock"
    f = open(lock_path, "w")
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        f.close()


def _key(headword: str, drill: dict[str, Any]) -> str:
    stable = {
        "headword": headword,
        "kind": drill.get("kind", ""),
        "prompt": drill.get("prompt", ""),
        "options": drill.get("options", []),
        "answer": drill.get("answer", ""),
    }
    raw = json.dumps(stable, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def key_for(headword: str, drill: dict[str, Any]) -> str:
    return _key(headword, drill)


def cached_keys() -> set[str]:
    return set(_read_cache().keys())


def word_drills(word: dict[str, Any], *, multiple_choice_only: bool = True) -> list[dict[str, Any]]:
    drills: list[dict[str, Any]] = []
    for d in word.get("discrimination_drills", []) or []:
        row = {"kind": "discrimination", **d}
        if not multiple_choice_only or row.get("options"):
            drills.append(row)
    for d in word.get("antonym_drills", []) or []:
        row = {"kind": "antonym", **d}
        if not multiple_choice_only or row.get("options"):
            drills.append(row)
    return drills


def _read_cache() -> dict[str, dict[str, Any]]:
    path = cache_path()
    if not path.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        key = str(row.get("key", ""))
        if key:
            out[key] = row
    return out


def _append_cache(row: dict[str, Any]) -> None:
    path = cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with _cache_lock():
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())


def _option_source_note(word: dict[str, Any], option: str) -> dict[str, Any]:
    opt = option.strip().lower()
    headword = str(word.get("headword", "")).strip().lower()
    if opt == headword:
        return {
            "word": option,
            "source": "headword",
            "sense": word.get("core_sense", ""),
            "register": word.get("register", ""),
            "examples": word.get("examples", [])[:2],
            "collocations": word.get("collocations", [])[:6],
        }
    for syn in word.get("synonyms", []) or []:
        if opt == str(syn.get("word", "")).strip().lower():
            return {"word": option, "source": "synonym", **syn}
    for ant in word.get("antonyms", []) or []:
        if opt == str(ant.get("word", "")).strip().lower():
            return {"word": option, "source": "antonym", **ant}
    for conf in word.get("confusions", []) or []:
        if opt == str(conf.get("word", "")).strip().lower():
            return {"word": option, "source": "confusion", **conf}
    return {"word": option, "source": "option", "note": ""}


def _source_notes(word: dict[str, Any], drill: dict[str, Any]) -> list[dict[str, Any]]:
    return [_option_source_note(word, str(o)) for o in (drill.get("options", []) or [])]


def _fallback(word: dict[str, Any], drill: dict[str, Any], key: str, error: str = "") -> dict[str, Any]:
    cards: list[dict[str, str]] = []
    for note in _source_notes(word, drill):
        source = note.get("source", "")
        use = note.get("nuance") or note.get("sense") or note.get("note") or note.get("difference") or ""
        if note.get("register"):
            use = f"{use} Register: {note.get('register')}."
        if note.get("collocations"):
            use = f"{use} Collocations: {', '.join(note.get('collocations', [])[:4])}."
        cards.append(
            {
                "word": str(note.get("word", "")),
                "chinese": "",
                "use_zh": use or "No cached note yet.",
                "example_zh": str(note.get("example", "")),
                "trap_zh": "中文脚手架暂未生成；先看英文 nuance。",
            }
        )
    return {
        "key": key,
        "cached": False,
        "fallback": True,
        "error": error,
        "prompt_zh": "",
        "context_hint_zh": "中文脚手架暂不可用；先用下面的词义差别卡片。",
        "blank_role_zh": "",
        "option_cards": cards,
        "decision_rule_zh": str(drill.get("explanation", "")),
    }


def build(word: dict[str, Any], drill: dict[str, Any]) -> dict[str, Any]:
    key = _key(str(word.get("headword", "")), drill)
    cached = _read_cache().get(key)
    if cached:
        cached = dict(cached)
        cached["cached"] = True
        return cached

    user = json.dumps(
        {
            "headword": word.get("headword", ""),
            "headword_core_sense": word.get("core_sense", ""),
            "drill": {
                "kind": drill.get("kind", ""),
                "prompt": drill.get("prompt", ""),
                "options": drill.get("options", []),
                "answer": drill.get("answer", ""),
                "explanation": drill.get("explanation", ""),
            },
            "option_source_notes": _source_notes(word, drill),
        },
        ensure_ascii=False,
        indent=2,
    )
    try:
        data = grounding._structured_call(SCAFFOLD_SYSTEM, user, SCAFFOLD_SCHEMA, max_tokens=3000)
    except Exception as e:  # noqa: BLE001
        return _fallback(word, drill, key, str(e))

    row = {
        "key": key,
        "created": datetime.now(timezone.utc).isoformat(),
        **data,
    }
    _append_cache(row)
    row["cached"] = False
    return row
