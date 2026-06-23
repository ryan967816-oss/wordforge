"""OCR selected Edge PDF pages into local corpus source rows.

This does not commit textbook text. It writes source passages to
``data/corpus/sources_local/``; run ``scripts/build_corpus.py`` afterward to
turn those rows into full local training packages under ``data/corpus/local/``.

Example:

    python scripts/ocr_edge_pages.py ~/Documents/english_training/path/to/unit.pdf \
      --pages 12-13 --id edge-c-unit-01-p012-013 --title "Unit 1 selection" \
      --structure "relative clause" --structure "past perfect"

    python scripts/build_corpus.py \
      --source-jsonl data/corpus/sources_local/edge_sources.jsonl \
      --out data/corpus/local/edge_passages.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wordforge import corpus  # noqa: E402


def _parse_pages(spec: str) -> tuple[int, int]:
    m = re.fullmatch(r"\s*(\d+)(?:\s*-\s*(\d+))?\s*", spec)
    if not m:
        raise SystemExit("--pages must look like 12 or 12-14")
    first = int(m.group(1))
    last = int(m.group(2) or first)
    if first < 1 or last < first:
        raise SystemExit("--pages must be 1-based and increasing")
    return first, last


def _clean_ocr(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        if re.fullmatch(r"\d+", line):
            continue
        lines.append(line)
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "command failed: " + " ".join(cmd))
    return proc.stdout


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    if not shutil.which("pdftoppm"):
        raise SystemExit("pdftoppm is required. Install poppler first.")
    if not shutil.which("tesseract"):
        raise SystemExit("tesseract is required. Install tesseract first.")

    p = argparse.ArgumentParser()
    p.add_argument("pdf", type=Path)
    p.add_argument("--pages", required=True, help="1-based page or page range, e.g. 12-13")
    p.add_argument("--id", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--level", default="B2-C1")
    p.add_argument("--source", default="Edge C local OCR")
    p.add_argument("--structure", action="append", default=[], dest="structures")
    p.add_argument(
        "--out",
        type=Path,
        default=corpus.corpus_dir() / "sources_local" / "edge_sources.jsonl",
    )
    args = p.parse_args()

    pdf = args.pdf.expanduser().resolve()
    if not pdf.exists():
        raise SystemExit(f"PDF not found: {pdf}")
    first, last = _parse_pages(args.pages)

    with tempfile.TemporaryDirectory(prefix="wf-edge-ocr-") as tmp:
        prefix = Path(tmp) / "page"
        _run(["pdftoppm", "-f", str(first), "-l", str(last), "-r", "200", "-png", str(pdf), str(prefix)])
        chunks = []
        for image in sorted(Path(tmp).glob("page-*.png")):
            chunks.append(_run(["tesseract", str(image), "stdout", "-l", "eng", "--psm", "6"]))

    text = _clean_ocr("\n".join(chunks))
    if len(text.split()) < 30:
        raise SystemExit("OCR text is too short; check page numbers or scan quality.")

    row = {
        "id": args.id,
        "source": args.source,
        "source_url": "",
        "level": args.level,
        "title": args.title,
        "text_en": text,
        "target_structures": args.structures,
    }
    _append_jsonl(args.out, row)
    print(json.dumps({"out": str(args.out), "id": args.id, "words": len(text.split())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
