#!/usr/bin/env python3
"""Bake the full Project Gutenberg Self-Reliance essay as a Reader package."""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wordforge import reading_packages  # noqa: E402

SOURCE_URL = "https://www.gutenberg.org/files/2944/2944-0.txt"
OUT = reading_packages.reading_package_dir() / "emerson_self_reliance_full.jsonl"


def _download() -> str:
    with urllib.request.urlopen(SOURCE_URL, timeout=30) as r:
        return r.read().decode("utf-8-sig", errors="replace").replace("\r\n", "\n")


def _extract_self_reliance(book: str) -> str:
    starts = [m.start() for m in re.finditer(r"(?m)^SELF-RELIANCE$", book)]
    if len(starts) < 2:
        raise ValueError("could not find the body SELF-RELIANCE heading")
    start = starts[1]
    end_match = re.search(r"(?m)^III\.\nCOMPENSATION$", book[start:])
    if not end_match:
        raise ValueError("could not find the next essay heading")
    essay = book[start : start + end_match.start()]
    essay = re.sub(r"(?m)^SELF-RELIANCE\s*", "", essay, count=1)
    essay = re.sub(r"\n{3,}", "\n\n", essay).strip()
    return essay


def _sentences(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", text).strip()
    pieces = re.split(r"(?<=[.!?])\s+(?=[“\"A-Z])", flat)
    return [p.strip() for p in pieces if p.strip()]


def main() -> int:
    essay = _extract_self_reliance(_download())
    segments = [
        {
            "index": i,
            "text_en": sentence,
            "component_zh": "",
            "codex_comment": "",
            "palette": [],
        }
        for i, sentence in enumerate(_sentences(essay))
    ]
    package = {
        "id": "emerson-self-reliance-complete",
        "title": "Self-Reliance · Complete Essay",
        "book": "Emerson · Essays, First Series",
        "source": "Ralph Waldo Emerson, Essays: First Series, Self-Reliance (Project Gutenberg #2944)",
        "source_url": "https://www.gutenberg.org/ebooks/2944",
        "route": "self-reliance",
        "category": "book",
        "local": False,
        "level": "C1-C2",
        "why_selected": "The complete public-domain essay behind the shorter practice excerpts, for continuous reading and listening.",
        "context_note": "Fast-baked full text: audio and sentence map first; sentence-by-sentence Chinese scaffolds can be added later for the parts you choose to study closely.",
        "target_structures": ["aphorism", "imperative", "parallelism", "abstract noun chains", "long periodic sentences"],
        "glosses": [
            {"word": "self-reliance", "hint": "trust in one's own perception and responsibility", "chinese": "自立；自信；依靠自己的判断"},
            {"word": "conformity", "hint": "living by social pattern rather than inner perception", "chinese": "从众；顺从"},
            {"word": "integrity", "hint": "inner wholeness; not splitting oneself for approval", "chinese": "完整性；正直"},
            {"word": "consistency", "hint": "keeping the same public self even when today's perception changes", "chinese": "一致性"},
        ],
        "vocab_targets": ["self-reliance", "conformity", "integrity", "consistency", "intuition", "genius"],
        "grammar": [
            "Emerson often states an aphorism, then expands it through metaphor and command.",
            "Many sentences are long because appositions, participles, and parallel phrases keep attaching to one main claim.",
            "Archaic or formal diction gives the essay a sermon-like pressure.",
        ],
        "codex_comment_zh": "这是完整正文包：先让你今晚能听完、滚动读完、随时选句提问；精细中文脚手架可以从你卡住的句子开始补。",
        "codex_comment_en": "Complete text package: continuous listening first, close reading on demand sentence by sentence.",
        "segments": segments,
        "text_en": essay,
    }
    OUT.write_text(json.dumps(package, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(OUT), "chars": len(essay), "segments": len(segments)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
