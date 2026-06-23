"""Persistent records for translation/back-translation attempts.

The translation loop is learning data, not just UI feedback. Each check writes a
full attempt and also extracts error rows that can later become vocab/structure
reviews or analytics.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from . import config, store


def attempts_path() -> Path:
    return config.data_dir() / "translate_attempts.jsonl"


def errors_path() -> Path:
    return config.data_dir() / "translate_errors.jsonl"


def _append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = dict(row)
    row.setdefault("ts", store.now_iso())
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with store._file_lock():  # shared data lock; keep app/CLI/native writes serialized
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())


def record_attempt(
    *,
    mode: str,
    source: str,
    answer: str,
    result: dict[str, Any],
    passage_id: str = "",
    support: str | int = "",
    sentence_index: int | None = None,
) -> dict[str, Any]:
    attempt = {
        "mode": mode,
        "passage_id": passage_id,
        "support": support,
        "sentence_index": sentence_index,
        "source": source,
        "answer": answer,
        "score": result.get("score", ""),
        "result": result,
    }
    _append(attempts_path(), attempt)

    errors = _extract_errors(
        mode=mode,
        passage_id=passage_id,
        support=support,
        sentence_index=sentence_index,
        result=result,
    )
    for err in errors:
        _append(errors_path(), err)
    return {"attempt_path": str(attempts_path()), "errors_path": str(errors_path()), "error_count": len(errors)}


def _extract_errors(
    *,
    mode: str,
    passage_id: str,
    support: str | int,
    sentence_index: int | None,
    result: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if mode == "e2c":
        for i, line in enumerate(result.get("sentences", []) or []):
            if line.get("accurate") is False:
                rows.append({
                    "kind": "sentence",
                    "mode": mode,
                    "passage_id": passage_id,
                    "support": support,
                    "sentence_index": sentence_index if sentence_index is not None else i,
                    "original": line.get("english", ""),
                    "yours": line.get("your_chinese", ""),
                    "comment": line.get("note", "") or line.get("correction", ""),
                })
    else:
        for i, line in enumerate(result.get("lines", []) or []):
            if line.get("verdict") == "off":
                rows.append({
                    "kind": "sentence",
                    "mode": mode,
                    "passage_id": passage_id,
                    "support": support,
                    "sentence_index": sentence_index if sentence_index is not None else i,
                    "original": line.get("original", ""),
                    "yours": line.get("yours", ""),
                    "comment": line.get("comment", ""),
                })

    for word in result.get("missed_words", []) or []:
        rows.append({
            "kind": "word",
            "mode": mode,
            "passage_id": passage_id,
            "support": support,
            "sentence_index": sentence_index,
            "target": word,
        })
    for structure in result.get("missed_structures", []) or []:
        rows.append({
            "kind": "structure",
            "mode": mode,
            "passage_id": passage_id,
            "support": support,
            "sentence_index": sentence_index,
            "target": structure,
        })
    return rows
