"""Headless CLI — for testing the engine and power use without the menu bar.

    python -m wordforge.cli add perfunctory
    python -m wordforge.cli show perfunctory
    python -m wordforge.cli drill            # one due drill, interactive
    python -m wordforge.cli session 10       # up to 10 due drills
    python -m wordforge.cli use perfunctory  # write a sentence, get it graded
    python -m wordforge.cli stats
    python -m wordforge.cli list
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from . import drills, grounding, scheduler, store


def _print_word(w: dict[str, Any]) -> None:
    print(f"\n# {w['headword']}  ({w.get('pos','')}) — {w.get('register','')}, {w.get('frequency','')}")
    print(f"  sense : {w.get('core_sense','')}")
    print(f"  image : {w.get('image','')}")
    if w.get("synonyms"):
        print("  synonyms (when to prefer):")
        for s in w["synonyms"]:
            print(f"    - {s['word']} [{s.get('register','')}]: {s['nuance']}")
            print(f"        e.g. {s.get('example','')}")
    if w.get("antonyms"):
        print("  antonyms:")
        for a in w["antonyms"]:
            print(f"    - {a['word']}: {a.get('note','')}")
    if w.get("collocations"):
        print("  collocations: " + ", ".join(w["collocations"]))
    if w.get("examples"):
        print("  examples:")
        for ex in w["examples"]:
            print(f"    - {ex}")
    if w.get("confusions"):
        print("  don't confuse with:")
        for c in w["confusions"]:
            print(f"    - {c['word']}: {c.get('difference','')}")


def cmd_add(args: argparse.Namespace) -> int:
    term = " ".join(args.term)
    print(f"Grounding '{term}' via Claude ...")
    data = grounding.ground_word(term)
    created = store.add_word(data)
    _print_word(store.find_word(store.load_words(), data["headword"]))
    print("\n[added]" if created else "\n[updated existing entry, schedule kept]")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    term = " ".join(args.term)
    w = store.find_word(store.load_words(), term)
    if not w:
        print(f"'{term}' is not in your lexicon. Add it with: add {term}")
        return 1
    _print_word(w)
    return 0


def _run_one_drill(word: dict[str, Any]) -> bool:
    """Present one drill interactively. Returns True if a drill was run."""
    drill = drills.pick_drill(word)
    if not drill:
        print(f"({word['headword']} has no drills; skipping)")
        return False
    print(f"\n--- {word['headword']} ---")
    print(drill["prompt"])
    if drill.get("kind") == "discrimination":
        for i, opt in enumerate(drill.get("options", []), 1):
            print(f"   {i}. {opt}")
    try:
        ua = input("Your answer: ").strip()
    except EOFError:
        return False
    correct, explanation = drills.check_answer(word, drill, ua)
    print("✓ correct" if correct else f"✗ — answer: {drill['answer']}")
    if explanation:
        print(f"   {explanation}")
    grade = drills.grade_for_correctness(correct)
    scheduler.review(word, grade)
    store.update_word(word)
    store.append_review({
        "headword": word["headword"], "kind": drill.get("kind"),
        "grade": grade, "correct": correct,
    })
    return True


def cmd_drill(args: argparse.Namespace) -> int:
    words = store.load_words()
    word = drills.next_due_word(words)
    if not word:
        print("Nothing due. 🎉")
        return 0
    _run_one_drill(word)
    return 0


def cmd_session(args: argparse.Namespace) -> int:
    limit = args.count
    done = 0
    while done < limit:
        words = store.load_words()
        word = drills.next_due_word(words)
        if not word:
            print("\nNothing more due. 🎉")
            break
        if _run_one_drill(word):
            done += 1
    print(f"\nReviewed {done} item(s).")
    return 0


def cmd_use(args: argparse.Namespace) -> int:
    term = " ".join(args.term)
    w = store.find_word(store.load_words(), term)
    if not w:
        print(f"'{term}' is not in your lexicon.")
        return 1
    print(f"Write a sentence using '{w['headword']}' ({w.get('core_sense','')}):")
    try:
        sentence = input("> ").strip()
    except EOFError:
        return 1
    if not sentence:
        return 1
    print("Grading ...")
    g = grounding.grade_sentence(w["headword"], w.get("core_sense", ""), sentence)
    print(f"\nscore: {g['score']}")
    print(f"sense ok: {g['correct_sense']} | register: {g['register_fit']} | "
          f"collocation ok: {g['collocation_ok']}")
    print(f"naturalness: {g['naturalness']}")
    print(f"feedback: {g['feedback']}")
    if g.get("better_version"):
        print(f"better: {g['better_version']}")
    grade = drills.SCORE_TO_GRADE.get(g["score"], "good")
    scheduler.review(w, grade)
    store.update_word(w)
    store.append_review({"headword": w["headword"], "kind": "generative",
                         "grade": grade, "score": g["score"]})
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    s = store.stats()
    print(f"words            : {s['total_words']}")
    print(f"due now          : {s['due_now']}")
    print(f"reviewed today   : {s['reviewed_today']}")
    print(f"reviews total    : {s['reviews_total']}")
    print(f"avg prod. score  : {s['avg_production_score']}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    for w in store.load_words():
        print(f"{w['headword']:20s} due={w.get('due','')[:10]}  "
              f"prod={w.get('production_score',0)}  reps={w.get('reps',0)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wordforge", description="WordForge CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("add"); pa.add_argument("term", nargs="+"); pa.set_defaults(fn=cmd_add)
    ps = sub.add_parser("show"); ps.add_argument("term", nargs="+"); ps.set_defaults(fn=cmd_show)
    sub.add_parser("drill").set_defaults(fn=cmd_drill)
    psess = sub.add_parser("session"); psess.add_argument("count", type=int, nargs="?", default=10); psess.set_defaults(fn=cmd_session)
    pu = sub.add_parser("use"); pu.add_argument("term", nargs="+"); pu.set_defaults(fn=cmd_use)
    sub.add_parser("stats").set_defaults(fn=cmd_stats)
    sub.add_parser("list").set_defaults(fn=cmd_list)

    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except grounding.GroundingError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
