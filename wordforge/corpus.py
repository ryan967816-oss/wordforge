"""Passage corpus for translation/back-translation training.

Committed passages live in ``data/corpus/passages.jsonl``. Local-only passages
such as OCR from copyrighted textbooks can live under ``data/corpus/local/``;
that directory is gitignored and loaded by the app when present.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import config

REQUIRED_FIELDS = {
    "id",
    "source",
    "level",
    "title",
    "text_en",
    "target_structures",
    "glosses",
    "scaffold",
    "palette",
    "grammar",
    "note",
    "vocab_targets",
}


def corpus_dir() -> Path:
    d = config.data_dir() / "corpus"
    d.mkdir(parents=True, exist_ok=True)
    return d


def public_path() -> Path:
    return corpus_dir() / "passages.jsonl"


def routes_path() -> Path:
    return corpus_dir() / "reading_paths.json"


def local_dir() -> Path:
    d = corpus_dir() / "local"
    d.mkdir(parents=True, exist_ok=True)
    return d


def corpus_paths() -> list[Path]:
    paths = [public_path()]
    paths.extend(sorted(local_dir().glob("*.jsonl")))
    return paths


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}:{lineno}: invalid JSON: {e}") from e
        missing = sorted(REQUIRED_FIELDS - row.keys())
        if missing:
            raise ValueError(f"{path}:{lineno}: missing fields: {', '.join(missing)}")
        rows.append(row)
    return rows


def load_passages() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in corpus_paths():
        for row in _read_jsonl(path):
            pid = str(row["id"])
            if pid in seen:
                continue
            seen.add(pid)
            rows.append(row)
    return rows


def list_passages() -> list[dict[str, Any]]:
    return [
        {
            "id": p["id"],
            "title": p["title"],
            "level": p["level"],
            "source": p["source"],
            "route": p.get("route", p.get("module", "")),
            "module": p.get("module", ""),
            "why_selected": p.get("why_selected", ""),
            "target_structures": p.get("target_structures", []),
            "local": str(p.get("source", "")).lower().startswith("edge"),
        }
        for p in load_passages()
    ]


def get_passage(pid: str) -> dict[str, Any] | None:
    for passage in load_passages():
        if passage.get("id") == pid:
            return passage
    return None


def validate() -> dict[str, Any]:
    passages = load_passages()
    ids = [p["id"] for p in passages]
    return {
        "count": len(passages),
        "ids": ids,
        "public_path": str(public_path()),
        "local_dir": str(local_dir()),
    }


def load_routes() -> list[dict[str, Any]]:
    path = routes_path()
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("routes", []))


def get_route(rid: str) -> dict[str, Any] | None:
    for route in load_routes():
        if route.get("id") == rid:
            return route
    return None
