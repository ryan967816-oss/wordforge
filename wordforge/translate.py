"""Translation trainer — build the Chinese<->English bridge.

Two modes, both graded by Claude; missed words feed back into the WordForge
lexicon (so translation work becomes the source, and the vocab drills become the
*test* of whether the nuance was internalized).

  Mode A (E->C, intake/precision):
    prep_e2c(passage)  -> sentences + glosses (hint + 中文) for the hard words
    grade_e2c(passage, your_chinese) -> per-sentence accuracy, corrections, missed words

  Mode B (back-translation, production — the user's idea):
    make_scaffold(passage) -> the passage rendered as Chinese in ENGLISH word order
    grade_back(original, your_english) -> line-by-line diff vs the original, missed words/structures
"""

from __future__ import annotations

from typing import Any

from . import grounding

# --- Mode A: E -> C ----------------------------------------------------------

PREP_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "sentences": {"type": "array", "items": {"type": "string"}},
        "hard_words": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {"word": {"type": "string"}, "hint": {"type": "string"},
                           "chinese": {"type": "string"}},
            "required": ["word", "hint", "chinese"]}},
    },
    "required": ["sentences", "hard_words"],
}

PREP_SYSTEM = """You prepare an English passage for a Chinese learner to translate into Chinese. \
Split it into sentences (keep them in order). Then list the words/phrases an advanced learner \
would likely find hard — for EACH give: a short English hint (a synonym or one-line sense, NOT \
the full Chinese) and a precise Chinese gloss (中文). Skip easy words; only the genuinely hard \
ones. Don't translate the sentences."""


def prep_e2c(passage: str) -> dict[str, Any]:
    return grounding._structured_call(PREP_SYSTEM, f"Passage:\n{passage}", PREP_SCHEMA, max_tokens=2000)


GRADE_E2C_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "score": {"type": "string", "enum": ["excellent", "good", "partial", "off"]},
        "overall": {"type": "string"},
        "sentences": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "english": {"type": "string"},
                "your_chinese": {"type": "string"},
                "accurate": {"type": "boolean"},
                "correction": {"type": "string"},
                "note": {"type": "string"}},
            "required": ["english", "your_chinese", "accurate", "correction", "note"]}},
        "missed_words": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["score", "overall", "sentences", "missed_words"],
}

GRADE_E2C_SYSTEM = """The learner translated an English passage into Chinese to show they UNDERSTOOD \
it (this tests comprehension + precision, not Chinese style — their Chinese is native). Align each \
English sentence with the learner's corresponding Chinese. For each: accurate=true if the Chinese \
faithfully captures the English meaning AND its nuance; if not, give the correct Chinese (correction) \
and a one-line note on exactly what was misunderstood (a sense, a connotation, a structure). \
missed_words: the English words/phrases (clean lemmas) the learner clearly misunderstood or skipped — \
these go to vocabulary study. score: excellent / good / partial / off. overall: one or two honest sentences."""


def grade_e2c(passage: str, your_chinese: str) -> dict[str, Any]:
    user = f"English passage:\n{passage}\n\nLearner's Chinese translation:\n{your_chinese}"
    return grounding._structured_call(GRADE_E2C_SYSTEM, user, GRADE_E2C_SCHEMA, max_tokens=3000)


# --- Mode B: back-translation (Chinese in English word order -> reconstruct English) ---

SCAFFOLD_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "properties": {"scaffold": {"type": "string"}, "note": {"type": "string"}},
    "required": ["scaffold", "note"],
}

SCAFFOLD_SYSTEM = """Render the English passage into Chinese that follows ENGLISH word order and \
structure — a structural scaffold for back-translation. Translate the meaning phrase by phrase but \
KEEP the English syntax: subject–verb–object order, relative clauses AFTER the noun, prepositional \
phrases in English position, articles/auxiliaries reflected as needed. The result should read as \
'English wearing Chinese words' — clear enough that a learner can reconstruct the original English, \
yet deliberately NOT natural Chinese (that's the point: it exposes the word-order bridge). In `note`, \
give one short line on the main structural difference this passage highlights (e.g. 定语后置/语序倒装)."""


def make_scaffold(passage: str) -> dict[str, Any]:
    return grounding._structured_call(SCAFFOLD_SYSTEM, f"English passage:\n{passage}",
                                      SCAFFOLD_SCHEMA, max_tokens=2000)


GRADE_BACK_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "score": {"type": "string", "enum": ["excellent", "good", "partial", "off"]},
        "feedback": {"type": "string"},
        "lines": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "original": {"type": "string"},
                "yours": {"type": "string"},
                "verdict": {"type": "string", "enum": ["match", "also-valid", "off"]},
                "comment": {"type": "string"}},
            "required": ["original", "yours", "verdict", "comment"]}},
        "missed_words": {"type": "array", "items": {"type": "string"}},
        "missed_structures": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["score", "feedback", "lines", "missed_words", "missed_structures"],
}

GRADE_BACK_SYSTEM = """The learner reconstructed English from a Chinese scaffold; compare their English \
to the ORIGINAL. Align sentence by sentence. For each line: verdict=match (essentially the original), \
also-valid (different wording but correct and natural — say so, don't punish good paraphrase), or off \
(wrong meaning/structure/word) with a comment on the exact gap. missed_words: words/phrases in the \
original the learner failed to produce or got wrong (clean lemmas, for vocab study). missed_structures: \
any English structures they didn't reproduce (e.g. 'relative clause', 'passive', 'inversion'). \
score: excellent / good / partial / off. feedback: one or two honest sentences. American English."""


def grade_back(original: str, your_english: str) -> dict[str, Any]:
    user = f"Original English:\n{original}\n\nLearner's reconstruction:\n{your_english}"
    return grounding._structured_call(GRADE_BACK_SYSTEM, user, GRADE_BACK_SCHEMA, max_tokens=3000)
