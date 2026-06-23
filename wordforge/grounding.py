"""Claude-powered grounding and grading.

Two calls, both forced through JSON-schema structured outputs so the result is
always valid and parseable (no brittle prose-parsing):

  ground_word(term)      -> a full grounded entry: nuance-annotated synonyms,
                            antonyms, collocations, a concrete image, examples,
                            confusions, AND pre-generated discrimination +
                            antonym drills (one call per added word).
  grade_sentence(...)    -> grades the learner's own sentence for productive use.

We do NOT enable extended thinking: output_config.format constrains the output
to the schema, so the model can't ramble, and we save latency + tokens.
"""

from __future__ import annotations

import json
import re
import urllib.request
from typing import Any

from . import config


class GroundingError(RuntimeError):
    pass


# --- Schemas -----------------------------------------------------------------

GROUND_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "headword": {"type": "string"},
        "pos": {"type": "string"},
        "core_sense": {"type": "string"},
        "image": {"type": "string"},
        "register": {
            "type": "string",
            "enum": ["formal", "neutral", "informal", "literary", "technical", "slang"],
        },
        "frequency": {
            "type": "string",
            "enum": ["very common", "common", "uncommon", "rare"],
        },
        "synonyms": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "word": {"type": "string"},
                    "nuance": {"type": "string"},
                    "register": {"type": "string"},
                    "example": {"type": "string"},
                },
                "required": ["word", "nuance", "register", "example"],
            },
        },
        "antonyms": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "word": {"type": "string"},
                    "note": {"type": "string"},
                },
                "required": ["word", "note"],
            },
        },
        "collocations": {"type": "array", "items": {"type": "string"}},
        "examples": {"type": "array", "items": {"type": "string"}},
        "confusions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "word": {"type": "string"},
                    "difference": {"type": "string"},
                },
                "required": ["word", "difference"],
            },
        },
        "discrimination_drills": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "prompt": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "answer": {"type": "string"},
                    "explanation": {"type": "string"},
                },
                "required": ["prompt", "options", "answer", "explanation"],
            },
        },
        "antonym_drills": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "prompt": {"type": "string"},
                    "answer": {"type": "string"},
                    "explanation": {"type": "string"},
                },
                "required": ["prompt", "answer", "explanation"],
            },
        },
    },
    "required": [
        "headword", "pos", "core_sense", "image", "register", "frequency",
        "synonyms", "antonyms", "collocations", "examples", "confusions",
        "discrimination_drills", "antonym_drills",
    ],
}

GRADE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "correct_sense": {"type": "boolean"},
        "register_fit": {"type": "string"},
        "collocation_ok": {"type": "boolean"},
        "naturalness": {"type": "string"},
        "feedback": {"type": "string"},
        "better_version": {"type": "string"},
        "score": {"type": "string", "enum": ["excellent", "good", "weak", "wrong"]},
    },
    "required": [
        "correct_sense", "register_fit", "collocation_ok", "naturalness",
        "feedback", "better_version", "score",
    ],
}

# --- Prompts -----------------------------------------------------------------

GROUND_SYSTEM = """You are a master American-English lexicographer and writing coach. \
You build entries for an advanced learner who wants the ACTIVE, productive command \
of an American English professor: able to summon the exact word while writing and \
speaking, vary register through synonyms, and use antonyms for contrast. Produce a \
*grounded* entry, never a dictionary dump.

For the given headword:
- core_sense: one vivid sentence capturing the essential meaning.
- image: a concrete mental picture or etymological hook that makes the word \
memorable and retrievable (the Latin/Greek root, or a scene). One or two sentences.
- synonyms: 3-6 near-synonyms. For EACH, a `nuance` note saying WHEN to prefer it \
over the headword (connotation, intensity, register, typical collocation) — this is \
the most important field, where productive command lives. Include its register and \
one natural example sentence that uses that synonym.
- antonyms: 2-4 true opposites, each with a short note on the contrast.
- collocations: 4-8 words/phrases the headword naturally travels with (the fluency lever).
- examples: 2 natural, professor-level sentences using the headword correctly, in \
different registers/contexts.
- confusions: 0-3 commonly confused or false-friend words, each with the precise difference.
- discrimination_drills: 2-3 items. Each is a cloze — a sentence with `___` plus an \
explicit register/context constraint, and 3-4 options drawn from the headword and its \
near-synonyms, where exactly ONE best fits given the constraint. Give the answer (the \
exact option text) and an explanation of the nuance that decides it.
- antonym_drills: 1-2 items prompting the learner to supply the opposite and use it in \
a contrastive sentence; give the answer and an explanation.

Be precise and scholarly, not flowery. American English. Output strictly via the schema."""

GRADE_SYSTEM = """You are a strict but constructive American-English writing coach. The \
learner is practicing PRODUCTIVE use of a target word. Given the target word, its core \
sense, and the learner's sentence, judge whether they used it correctly and naturally:
- correct_sense: did they use the word's actual meaning (not a near-miss)?
- register_fit: does the word suit the sentence's register? (one phrase)
- collocation_ok: are the word partners natural?
- naturalness: how a fluent professor would rate the sentence's flow (one phrase).
- feedback: 1-2 sentences, concrete and honest.
- better_version: if it could be improved, a sharper sentence that keeps the learner's \
intent and still uses the target word; otherwise repeat their sentence.
- score: excellent / good / weak / wrong.
Honesty is how they learn — do not inflate."""


def _client():
    try:
        import anthropic
    except ImportError as e:  # pragma: no cover
        raise GroundingError(
            "The 'anthropic' package is not installed. Run setup.command."
        ) from e
    key = config.get_api_key()
    if not key:
        raise GroundingError(
            "No Anthropic API key found. Set ANTHROPIC_API_KEY or save one via "
            "the menu-bar Settings."
        )
    return anthropic.Anthropic(api_key=key)


def _structured_call(system: str, user: str, schema: dict[str, Any], max_tokens: int) -> dict[str, Any]:
    if config.get_provider() == "deepseek":
        return _deepseek_structured_call(system, user, schema, max_tokens)
    client = _client()
    try:
        resp = client.messages.create(
            model=config.get_model(),
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
    except Exception as e:  # surface a clean message to the UI
        raise GroundingError(f"Claude API call failed: {e}") from e

    if getattr(resp, "stop_reason", None) == "refusal":
        raise GroundingError("The request was declined by the model's safety system.")
    if getattr(resp, "stop_reason", None) == "max_tokens":
        # Structured outputs keep the JSON well-formed but do NOT guarantee the
        # object finished before the cap — a truncated doc would otherwise fail
        # json.loads with a misleading 'could not parse' error. Name it plainly.
        raise GroundingError("The response was cut off at the token limit (try again).")

    text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), None)
    if not text:
        raise GroundingError("Empty response from Claude.")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise GroundingError(f"Could not parse model output as JSON: {e}") from e


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise


def _deepseek_structured_call(system: str, user: str, schema: dict[str, Any], max_tokens: int) -> dict[str, Any]:
    key = config.get_deepseek_api_key()
    if not key:
        raise GroundingError("No DeepSeek API key found. Set DEEPSEEK_API_KEY or save one to Keychain.")
    schema_text = json.dumps(schema, ensure_ascii=False)
    payload = {
        "model": config.get_deepseek_model(),
        "messages": [
            {
                "role": "system",
                "content": (
                    system
                    + "\n\nReturn ONLY valid JSON. It must match this JSON Schema exactly:\n"
                    + schema_text
                ),
            },
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        config.get_deepseek_base_url(),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise GroundingError(f"DeepSeek API call failed: {e}") from e
    try:
        text = data["choices"][0]["message"]["content"]
        return _extract_json(text)
    except Exception as e:
        raise GroundingError(f"Could not parse DeepSeek output as JSON: {e}") from e


def ground_word(term: str) -> dict[str, Any]:
    term = term.strip()
    if not term:
        raise GroundingError("Empty term.")
    user = f"Headword: {term}\n\nProduce the grounded entry."
    # 8192 gives comfortable headroom over the ~2k-token worst case; unused
    # output budget isn't billed.
    data = _structured_call(GROUND_SYSTEM, user, GROUND_SCHEMA, max_tokens=8192)
    # Normalize the headword to what the user typed (model may re-lemmatize).
    if not data.get("headword"):
        data["headword"] = term
    return data


def grade_sentence(headword: str, core_sense: str, sentence: str) -> dict[str, Any]:
    user = (
        f"Target word: {headword}\n"
        f"Core sense: {core_sense}\n"
        f"Learner's sentence: {sentence}"
    )
    return _structured_call(GRADE_SYSTEM, user, GRADE_SCHEMA, max_tokens=1024)


# --- Article upgrade pass (secondary feature) --------------------------------

UPGRADE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "original": {"type": "string"},
                    "replacement": {"type": "string"},
                    "rewritten_phrase": {"type": "string"},
                    "why": {"type": "string"},
                    "from_your_words": {"type": "boolean"},
                },
                "required": ["original", "replacement", "rewritten_phrase", "why", "from_your_words"],
            },
        }
    },
    "required": ["suggestions"],
}

UPGRADE_SYSTEM = """You are a precise American-English writing coach. Given a draft and a \
list of the learner's active vocabulary words, find places where a bland or imprecise \
word could be upgraded to a sharper, more exact word — PREFERRING the learner's own active \
words wherever they genuinely fit. For each suggestion give: the original word/phrase in \
the draft, the replacement word, the rewritten phrase, a one-line reason (the nuance the \
upgrade buys), and whether the replacement is from the learner's word list. Only suggest \
upgrades that improve precision or register without distorting meaning — do not pad. Order \
by impact. At most 8 suggestions."""


def upgrade_article(text: str, known_words: list[str]) -> dict[str, Any]:
    words = ", ".join(known_words) if known_words else "(none yet)"
    user = (
        f"The learner's active vocabulary words: {words}\n\n"
        f"Draft to upgrade:\n\"\"\"\n{text}\n\"\"\""
    )
    return _structured_call(UPGRADE_SYSTEM, user, UPGRADE_SCHEMA, max_tokens=2048)
