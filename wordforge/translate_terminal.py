"""Terminal practice for the corpus-backed Translate pillar.

This is the reliable local fallback: it uses pre-baked JSON corpus packages and
does not call Claude unless ``--claude-grade`` is passed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config, corpus, translate

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "had", "has", "have", "he", "her", "his", "i", "in", "is", "it", "its",
    "me", "my", "not", "of", "on", "or", "she", "that", "the", "their",
    "them", "they", "this", "to", "was", "were", "what", "when", "who",
    "with", "you",
}


def _plain_scaffold(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\[[^\]]+\]", "", text or "")).strip()


def _content_tokens(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", text.lower())
    return [t.strip("'") for t in tokens if len(t.strip("'")) > 2 and t not in STOPWORDS]


def _wrap(text: str, width: int = 96) -> str:
    words = str(text).split()
    lines: list[str] = []
    cur: list[str] = []
    n = 0
    for word in words:
        if cur and n + len(word) + 1 > width:
            lines.append(" ".join(cur))
            cur = [word]
            n = len(word)
        else:
            cur.append(word)
            n += len(word) + (1 if n else 0)
    if cur:
        lines.append(" ".join(cur))
    return "\n".join(lines)


def _print_title(p: dict[str, Any]) -> None:
    print(f"\n# {p['title']}  [{p['level']}]")
    print(f"source: {p['source']}")
    if p.get("target_structures"):
        print("structures: " + " · ".join(p["target_structures"]))


def _word_hint_line(glosses: list[dict[str, str]]) -> None:
    if not glosses:
        return
    print("\nword hints:")
    print("  " + "  |  ".join(f"{g['word']} = {g['chinese']}" for g in glosses))


def _hard_words(glosses: list[dict[str, str]]) -> None:
    if not glosses:
        return
    print("\nhard words:")
    for g in glosses:
        print(f"  - {g['word']}: {g['hint']} / {g['chinese']}")


def _palette(palette: list[dict[str, str]]) -> None:
    if not palette:
        return
    print("\npalette (English = 中文 | where):")
    for item in palette:
        print(f"  - {item['english']} = {item['chinese']} | {item['usage']}")


def _sentence_split(text: str) -> None:
    print("\nsentence split:")
    for i, sent in enumerate(re.split(r"(?<=[.!?])\s+", text), 1):
        sent = sent.strip()
        if sent:
            print(f"  {i}. {sent}")


def _show_support(p: dict[str, Any], mode: str, support: int) -> None:
    glosses = p.get("glosses", [])
    grammar = p.get("grammar", [])
    if support == 4:
        print("\nsupport: bare")
        return
    if mode == "e2c":
        if support == 1:
            _word_hint_line(glosses)
            if grammar:
                print("\nwatch: " + " · ".join(grammar))
            _hard_words(glosses)
        elif support == 2:
            _word_hint_line(glosses)
            if grammar:
                print("\nwatch: " + " · ".join(grammar))
        else:
            _sentence_split(p["text_en"])
        return

    if support == 1:
        _word_hint_line(glosses)
        print("\nChinese in English word order:")
        print(_wrap(p.get("scaffold", "")))
        if grammar:
            print("\nwatch: " + " · ".join(grammar))
        _palette(p.get("palette", []))
    elif support == 2:
        _word_hint_line(glosses)
        if p.get("target_structures"):
            print("\nstructures: " + " · ".join(p["target_structures"]))
        if grammar:
            print("watch: " + " · ".join(grammar))
    else:
        print("\nChinese in English word order (no tags, no palette):")
        print(_wrap(_plain_scaffold(p.get("scaffold", ""))))


def _read_multiline(prompt: str) -> str:
    print(f"\n{prompt}")
    print("(finish with an empty line)")
    lines: list[str] = []
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        if line == "":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _local_back_check(original: str, answer: str) -> dict[str, Any]:
    original_tokens = list(dict.fromkeys(_content_tokens(original)))
    answer_tokens = set(_content_tokens(answer))
    missed = [t for t in original_tokens if t not in answer_tokens]
    covered = len(original_tokens) - len(missed)
    pct = round(100 * covered / max(1, len(original_tokens)))
    return {"coverage": pct, "missed_words": missed[:30]}


def _local_e2c_check(p: dict[str, Any], answer: str) -> dict[str, Any]:
    missing: list[str] = []
    for g in p.get("glosses", []):
        gloss = str(g.get("chinese", "")).replace("；", ";")
        options = [x.strip() for x in re.split(r"[;/,，；]", gloss) if x.strip()]
        if options and not any(opt in answer for opt in options):
            missing.append(g["word"])
    return {"hint_coverage": f"{len(p.get('glosses', [])) - len(missing)}/{len(p.get('glosses', []))}", "possibly_missing": missing}


def _attempt_path() -> Path:
    return config.data_dir() / "translate_attempts.jsonl"


def _save_attempt(row: dict[str, Any]) -> None:
    path = _attempt_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _choose_passage(pid: str | None) -> dict[str, Any] | None:
    passages = corpus.load_passages()
    if not passages:
        print("No corpus passages found.")
        return None
    if pid:
        p = corpus.get_passage(pid)
        if not p:
            print(f"passage not found: {pid}")
            return None
        return p
    for i, p in enumerate(passages, 1):
        structures = ", ".join(p.get("target_structures", [])[:2])
        print(f"{i:2d}. {p['level']} · {p['title']} — {structures}")
    try:
        raw = input("\nPick passage number: ").strip()
    except EOFError:
        return None
    if not raw:
        return None
    try:
        return passages[int(raw) - 1]
    except (ValueError, IndexError):
        print("invalid selection")
        return None


def cmd_practice(args: argparse.Namespace) -> int:
    p = _choose_passage(args.id)
    if not p:
        return 1
    mode = args.mode
    support = max(1, min(4, args.support))
    _print_title(p)
    print("\nSOURCE / 原文:")
    print(_wrap(p["text_en"]))
    _show_support(p, mode, support)
    if mode == "e2c":
        answer = _read_multiline("Your Chinese translation")
        local = _local_e2c_check(p, answer)
    else:
        answer = _read_multiline("Your English reconstruction")
        local = _local_back_check(p["text_en"], answer)
    if not answer:
        print("stopped")
        return 0
    print("\nlocal check:")
    print(json.dumps(local, ensure_ascii=False, indent=2))
    grade: dict[str, Any] | None = None
    if args.claude_grade:
        print("\nClaude grading ...")
        grade = translate.grade_e2c(p["text_en"], answer) if mode == "e2c" else translate.grade_back(p["text_en"], answer)
        print(json.dumps(grade, ensure_ascii=False, indent=2))
    _save_attempt({
        "ts": datetime.now(timezone.utc).isoformat(),
        "passage_id": p["id"],
        "mode": mode,
        "support": support,
        "answer": answer,
        "local_check": local,
        "claude_grade": grade,
    })
    print(f"\nsaved: {_attempt_path()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WordForge terminal Translate practice")
    parser.add_argument("--id", help="passage id; omit to choose from a list")
    parser.add_argument("--mode", choices=["e2c", "back"], default="back")
    parser.add_argument("--support", type=int, default=1, help="1 thick, 2 hints, 3 thin, 4 bare")
    parser.add_argument("--claude-grade", action="store_true", help="call Claude for final grading")
    args = parser.parse_args(argv)
    return cmd_practice(args)


if __name__ == "__main__":
    raise SystemExit(main())
