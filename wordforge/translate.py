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
    "properties": {
        "scaffold": {"type": "string"},
        "palette": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {"english": {"type": "string"}, "chinese": {"type": "string"},
                           "usage": {"type": "string"}},
            "required": ["english", "chinese", "usage"]}},
        "grammar": {"type": "array", "items": {"type": "string"}},
        "note": {"type": "string"},
    },
    "required": ["scaffold", "palette", "grammar", "note"],
}

SCAFFOLD_SYSTEM = """Build a THICK scaffold for back-translation — maximize support so the learner \
SELECTS and ASSEMBLES the English rather than recalling it from nothing. The goal is to lower the \
barrier until the task is just touchable, NOT to add difficulty.

1. scaffold: the passage rendered in Chinese that follows ENGLISH word order and structure (subject–\
verb–object, relative clauses AFTER the noun, prepositional phrases in English position) — 'English \
wearing Chinese words', deliberately NOT natural Chinese. CRUCIAL: because Chinese does not inflect, \
annotate TENSE/ASPECT inline on EVERY verb with a compact tag so the learner can rebuild the exact \
English — e.g. 花费[过去完成 had+pp] / 看见[一般过去] / 闪烁[现在分词 -ing] / 被证实[被动]. Also tag \
structural pivots briefly inline (定语从句起点, 被动, 倒装, that-从句).
2. palette: a COMPREHENSIVE list of the usable words/phrases in the passage as {english, chinese, \
usage} — english = the exact word/phrase to use; chinese = its gloss; usage = where/how it's used \
(its collocation, register, or which slot in the sentence). Include content words AND useful \
connectors, so the learner can pick the right word instead of retrieving it cold.
3. grammar: 1-4 short notes on the key tense/structure points to get right.
4. note: one line on the main word-order difference this passage highlights.
American English."""


def make_scaffold(passage: str) -> dict[str, Any]:
    return grounding._structured_call(SCAFFOLD_SYSTEM, f"English passage:\n{passage}",
                                      SCAFFOLD_SCHEMA, max_tokens=3500)


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


# --- Reading questions -------------------------------------------------------

ASK_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "answer_zh": {"type": "string"},
        "english_anchor": {"type": "string"},
        "what_to_notice": {"type": "array", "items": {"type": "string"}},
        "next_question": {"type": "string"},
    },
    "required": ["answer_zh", "english_anchor", "what_to_notice", "next_question"],
}

ASK_SYSTEM = """You are helping a Chinese learner read a difficult English source text deeply.
Answer in clear English, not Chinese, so the answer can be spoken by English TTS.
Do NOT replace the source with a loose summary. Keep the user's attention attached
to the original English.

For every answer:
- Give a light, useful answer to the question in English.
- Anchor it in one exact English phrase or sentence from the passage.
- Name 2-4 concrete English things to notice: word choice, structure, metaphor, tense, register, or rhetorical force.
- Suggest one next question the learner could ask.

Do not over-explain the whole book unless asked. Preserve curiosity."""


def ask_about_passage(passage: dict[str, Any], question: str, route: dict[str, Any] | None = None) -> dict[str, Any]:
    route_bits = ""
    if route:
        route_bits = (
            f"\nBook route: {route.get('title','')}\n"
            f"Central question: {route.get('central_question','')}\n"
            f"Why it may hit: {route.get('why_it_hits','')}\n"
        )
    user = (
        f"Title: {passage.get('title','')}\n"
        f"Source: {passage.get('source','')}\n"
        f"Why selected: {passage.get('why_selected','')}\n"
        f"{route_bits}\n"
        f"Passage:\n{passage.get('text_en','')}\n\n"
        f"Learner question:\n{question}"
    )
    return grounding._structured_call(ASK_SYSTEM, user, ASK_SCHEMA, max_tokens=1800)
