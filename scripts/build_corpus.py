"""Build or validate the translation passage corpus.

Default use is a cheap validation pass:

    python scripts/build_corpus.py --validate

To grow the corpus from a JSONL file of source passages, pass ``--source-jsonl``.
Each source row needs at least: id, source, level, title, text_en,
target_structures. Live generation calls Claude through ``wordforge.translate``;
it is resume-safe and skips ids already present in ``data/corpus/passages.jsonl``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wordforge import corpus, translate  # noqa: E402


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _package_from_source(row: dict[str, Any]) -> dict[str, Any]:
    text = row["text_en"]
    prep = translate.prep_e2c(text)
    scaffold = translate.make_scaffold(text)
    glosses = prep.get("hard_words", [])
    vocab_targets = []
    for g in glosses:
        word = str(g.get("word", "")).strip()
        if word:
            vocab_targets.append(word)
    return {
        "id": row["id"],
        "source": row["source"],
        "source_url": row.get("source_url", ""),
        "level": row.get("level", "C1"),
        "title": row["title"],
        "text_en": text,
        "target_structures": row.get("target_structures", []),
        "glosses": glosses,
        "scaffold": scaffold.get("scaffold", ""),
        "palette": scaffold.get("palette", []),
        "grammar": scaffold.get("grammar", []),
        "note": scaffold.get("note", ""),
        "vocab_targets": vocab_targets,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--validate", action="store_true")
    p.add_argument("--source-jsonl", type=Path)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--out", type=Path, default=corpus.public_path())
    args = p.parse_args()

    if args.validate or not args.source_jsonl:
        result = corpus.validate()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    existing = {p["id"] for p in corpus.load_passages()}
    sources = [r for r in _read_jsonl(args.source_jsonl) if r["id"] not in existing]
    if args.limit:
        sources = sources[: args.limit]
    print(f"corpus build: {len(sources)} source passages to generate", flush=True)
    t0 = time.time()
    done = 0
    failed: list[str] = []
    for row in sources:
        try:
            package = _package_from_source(row)
            _append_jsonl(args.out, package)
            done += 1
            print(f"  [{done}/{len(sources)}] + {package['id']}", flush=True)
        except Exception as e:  # noqa: BLE001
            failed.append(str(row.get("id", "?")))
            print(f"  [!] {row.get('id', '?')}: {e}", flush=True)
    print(f"done: {done}/{len(sources)} in {round(time.time() - t0)}s; failed={len(failed)}")
    if failed:
        print("retry later: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
