"""Writing trainer — practice essays against a rubric, graded by Claude.

Grounded in your TOEFL writing prompts and the California Edge writing projects.
Workflow:
    python -m wordforge.writing prompts            # list prompts
    python -m wordforge.writing new <id|"a topic">  # create a draft file to write in
    python -m wordforge.writing grade <draft.md>    # rubric-based grade + model upgrade

Grading is a 6-dimension academic rubric (task response / organization /
development / grammar / vocabulary / mechanics), each 0–5, plus an overall band,
a CEFR/TOEFL estimate, your top fixes quoted from your own text, a model upgrade
of your weakest paragraph, and weak words to send to WordForge.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from . import config, grounding

# Where drafts + graded reports live (git-versioned with the rest of your data).
def writing_dir() -> Path:
    d = config.data_dir() / "writing"
    d.mkdir(parents=True, exist_ok=True)
    return d


# A few solid academic/argumentative prompts to start; your own TOEFL .md files
# are auto-discovered and added to this list.
BUILTIN_PROMPTS: dict[str, str] = {
    "tech-and-attention": "Some people argue that constant access to the internet "
        "and smartphones has made it harder to think deeply. Do you agree or disagree? "
        "Develop your position with specific reasons and examples.",
    "specialist-vs-generalist": "In an age of rapid change, is it better to specialize "
        "deeply in one field or to develop a broad range of skills? Argue for one view, "
        "addressing the strongest objection to it.",
    "evidence-in-medicine": "Explain why a treatment that 'worked for someone you know' "
        "is weak evidence compared with a randomized controlled trial. Write for an "
        "intelligent reader who is not a scientist.",
    "city-vs-nature": "Should governments prioritize building more housing in cities or "
        "protecting natural land outside them? Take a position and defend it.",
}

ESSAY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "level_estimate": {"type": "string"},
        "overall_band": {"type": "integer"},
        "dimensions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {
                        "type": "string",
                        "enum": ["task response", "organization", "development",
                                 "grammar", "vocabulary", "mechanics"],
                    },
                    "band": {"type": "integer"},
                    "comment": {"type": "string"},
                },
                "required": ["name", "band", "comment"],
            },
        },
        "strengths": {"type": "array", "items": {"type": "string"}},
        "priority_fixes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "issue": {"type": "string"},
                    "from_your_text": {"type": "string"},
                    "how_to_fix": {"type": "string"},
                },
                "required": ["issue", "from_your_text", "how_to_fix"],
            },
        },
        "model_paragraph": {"type": "string"},
        "weak_words": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["level_estimate", "overall_band", "dimensions", "strengths",
                 "priority_fixes", "model_paragraph", "weak_words"],
}

GRADE_SYSTEM = """You are a demanding but constructive American academic-writing coach. \
Grade the student's essay against the given prompt on a 6-dimension rubric — task \
response, organization, development, grammar, vocabulary, mechanics — each scored 0–5, \
where 5 = a strong American undergraduate and 3 = solid upper-intermediate (B2). Be \
honest and specific:
- For each dimension give the band and a one-sentence reason.
- level_estimate: a short CEFR + TOEFL-ish estimate, e.g. "CEFR B2, TOEFL writing ~24".
- strengths: 2–3 concrete things done well.
- priority_fixes: the 3–5 highest-leverage fixes. For EACH, quote the exact phrase \
from the student's text (from_your_text) and show how to fix it.
- model_paragraph: take the student's WEAKEST paragraph and rewrite it at a strong level, \
keeping their ideas — so they can see the gap.
- weak_words: clean single target words (lemmas, ONE word each, no parentheses or notes) \
the student should learn — the CORRECT or upgraded word, e.g. "deeply", "concentration", \
"harmful" — so they drop straight into a vocabulary trainer.
Use American English. Quote the student's real words; do not invent text they didn't write."""


def discover_prompts() -> dict[str, str]:
    """Built-in prompts plus any of your TOEFL writing .md files."""
    prompts = dict(BUILTIN_PROMPTS)
    toefl = Path.home() / "Documents" / "toefl" / "写作-Writing"
    if toefl.exists():
        for md in sorted(toefl.glob("*.md")):
            if md.stem.lower().startswith("writing-study"):
                continue
            prompts[f"toefl:{md.stem}"] = md.read_text(encoding="utf-8", errors="ignore")[:1500]
    return prompts


def grade_essay(prompt: str, essay: str) -> dict[str, Any]:
    user = (
        f"PROMPT:\n{prompt}\n\n"
        f"STUDENT ESSAY ({len(essay.split())} words):\n\"\"\"\n{essay}\n\"\"\""
    )
    return grounding._structured_call(GRADE_SYSTEM, user, ESSAY_SCHEMA, max_tokens=3500)


# --- CLI ---------------------------------------------------------------------

def cmd_prompts(args: argparse.Namespace) -> int:
    prompts = discover_prompts()
    print("Available prompts (use the id with `new`):\n")
    for pid, text in prompts.items():
        first = " ".join(text.split())[:90]
        print(f"  {pid}\n      {first}…\n")
    print("Or just: new \"your own topic in quotes\"")
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    key = " ".join(args.idea).strip()
    prompts = discover_prompts()
    if key in prompts:
        prompt_text = prompts[key]
        slug = key.replace(":", "_")
    else:
        prompt_text = key  # treat the words as the prompt itself
        slug = "custom-" + "-".join(key.lower().split()[:4])
    draft = writing_dir() / f"{slug}.md"
    if not draft.exists():
        draft.write_text(
            f"<!-- PROMPT: {prompt_text} -->\n\n"
            f"# Prompt\n{prompt_text}\n\n# Your essay (write below this line)\n\n",
            encoding="utf-8",
        )
    print(f"Draft created: {draft}")
    print("Open it, write your essay under '# Your essay', save, then run:")
    print(f"    python -m wordforge.writing grade \"{draft}\"")
    # Open in the default text editor for convenience.
    import subprocess
    subprocess.run(["open", "-t", str(draft)], check=False)
    return 0


def _extract_essay(path: Path) -> tuple[str, str]:
    """Return (prompt, essay) from a draft file. Prompt is the '# Prompt' block
    (or the PROMPT comment); essay is everything under '# Your essay'."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    prompt = ""
    essay = text
    if "# Your essay" in text:
        head, _, tail = text.partition("# Your essay")
        essay = tail.split("\n", 1)[1] if "\n" in tail else ""
        if "# Prompt" in head:
            prompt = head.split("# Prompt", 1)[1].strip()
    return prompt.strip(), essay.strip()


def cmd_grade(args: argparse.Namespace) -> int:
    path = Path(args.file).expanduser()
    if not path.exists():
        print(f"No such file: {path}", file=sys.stderr)
        return 1
    prompt, essay = _extract_essay(path)
    if len(essay.split()) < 20:
        print("Your essay looks empty (<20 words). Write under '# Your essay' first.")
        return 1
    if not prompt and args.prompt:
        prompt = args.prompt
    print(f"Grading {len(essay.split())} words against Claude rubric …\n")
    g = grade_essay(prompt or "(no prompt given — judge as a free-standing essay)", essay)

    print(f"Level: {g['level_estimate']}      Overall: {g['overall_band']}/5\n")
    print("Rubric:")
    for d in g["dimensions"]:
        print(f"  {d['name']:14s} {d['band']}/5  — {d['comment']}")
    print("\nStrengths:")
    for s in g["strengths"]:
        print(f"  + {s}")
    print("\nTop fixes:")
    for i, f in enumerate(g["priority_fixes"], 1):
        print(f"  {i}. {f['issue']}")
        print(f"       your text: \"{f['from_your_text']}\"")
        print(f"       fix: {f['how_to_fix']}")
    print("\nModel upgrade of your weakest paragraph:")
    print(f"  {g['model_paragraph']}")
    if g["weak_words"]:
        print("\nWords to study (add to WordForge):")
        print("  " + ", ".join(g["weak_words"]))
        print("  e.g.  python -m wordforge.cli add " + (g["weak_words"][0] if g["weak_words"] else ""))

    report = path.with_suffix(".report.md")
    lines = [f"# Writing report — {path.name}", "",
             f"**Level:** {g['level_estimate']}  ·  **Overall:** {g['overall_band']}/5", "",
             "## Rubric"]
    lines += [f"- **{d['name']}** {d['band']}/5 — {d['comment']}" for d in g["dimensions"]]
    lines += ["", "## Strengths"] + [f"- {s}" for s in g["strengths"]]
    lines += ["", "## Top fixes"]
    for f in g["priority_fixes"]:
        lines += [f"- **{f['issue']}**", f"  - your text: \"{f['from_your_text']}\"",
                  f"  - fix: {f['how_to_fix']}"]
    lines += ["", "## Model paragraph", g["model_paragraph"],
              "", "## Words to study", ", ".join(g["weak_words"])]
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nSaved report: {report}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wordforge.writing", description="Writing trainer")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prompts").set_defaults(fn=cmd_prompts)
    pn = sub.add_parser("new"); pn.add_argument("idea", nargs="+"); pn.set_defaults(fn=cmd_new)
    pg = sub.add_parser("grade"); pg.add_argument("file"); pg.add_argument("--prompt", default="")
    pg.set_defaults(fn=cmd_grade)
    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except grounding.GroundingError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
