# Multimodal Reading Plan

This is the next reading shape for WordForge: one passage becomes a small
pre-baked learning object, not a live model call every time.

## Goal

Let Ming read a difficult passage through several synchronized channels:

- audio plays;
- the English transcript scrolls and highlights;
- a Chinese-in-English-order scaffold stays available as "components", with
  tense/aspect tags;
- DeepSeek gives a short anchored explanation of what the passage is saying;
- the only live local interaction is asking about a selected sentence or phrase.

The Chinese layer must not replace English reading. It is a component map:
word order, tense tags, clause slots, and phrase meaning.

## Why This Is Different From Translation

Normal Chinese summary destroys the force of the English. The learner knows the
rough meaning but does not acquire the English structure.

This mode keeps the English as the object:

1. audio makes the sentence temporal;
2. scrolling English keeps attention on the real text;
3. Chinese word-order scaffold makes the structure touchable;
4. DS explanation answers "what is this doing?" without summarizing away the
   English;
5. selected-sentence Ask keeps curiosity local.

## Data Package

One passage package should live under `data/reading_packages/` or be derived from
the committed corpus:

```json
{
  "id": "emerson-self-reliance-trust-thyself",
  "title": "Trust Thyself",
  "source": "Ralph Waldo Emerson, Self-Reliance",
  "text_en": "...",
  "audio_path": "data/reading_audio/emerson-trust-thyself.mp3",
  "segments": [
    {
      "start_ms": 0,
      "end_ms": 4200,
      "english": "Trust thyself: every heart vibrates to that iron string.",
      "component_zh": "信任[祈使] 你自己：每一颗心 震动[一般现在] 到 那根 铁弦。",
      "glosses": [
        {"english": "thyself", "chinese": "你自己", "usage": "archaic reflexive"},
        {"english": "vibrates to", "chinese": "随...共鸣", "usage": "metaphoric response"}
      ],
      "ds_explain_zh": "这一句不是普通建议，而是命令式的自我授权..."
    }
  ],
  "global_explain_zh": "这段在说..."
}
```

## API Roles

Use APIs offline-at-build-time when possible:

- TTS or original audio: creates the audio object.
- Deepgram or local whisper: turns audio into timestamped English segments.
- DeepSeek: acceptable for low-risk bulk component labels, tense tags, and
  glossary drafts when the English source and local structure are already known.
- Codex / stronger model pass: required for book-level interpretation, passage
  force, "why this matters", and any explanation that functions like a skilled
  professor.

Runtime should mostly read the package. Live calls are only for:

- selected sentence Ask;
- optional re-generation when the package is missing.

## Model Tiering

Do not use one model tier for all work.

- Cheap/bulk tier: DS-style model for JSON scaffolds, glossary drafts, sentence
  splits, and tense/component tags.
- Professor tier: Codex/strong model for close reading, quality audit, and the
  final explanation stored into the package.
- Runtime: no model call unless the learner selects a sentence and asks a new
  question.

This is the same pattern as Vocab: pre-bake first, thin support later, then use
blind tests for retrieval.

## Deepgram Boundary

Deepgram is useful when there is audio that needs reliable timestamps. It does
not by itself solve the whole reading mode. If there is no original audio, the
pipeline still needs a TTS source first.

Deepgram keys should live in env or macOS Keychain, never in git. Store a rotated
key with:

```bash
./.venv/bin/python scripts/set_deepgram_key.py
```

Do not build or claim a Deepgram pipeline until a key exists in env/Keychain and
a one-file smoke test has passed.

## First Slice

Build the first package from the existing corpus passage:

- `emerson-self-reliance-trust-thyself`
- generate or attach audio;
- produce sentence segments;
- reuse existing corpus `scaffold`, `palette`, `grammar`, and `note`;
- add per-sentence `component_zh` and `ds_explain_zh`;
- render in Studio Reader as:
  - audio controls;
  - scrolling English;
  - right/under panel with component Chinese;
  - click sentence -> Ask this sentence.

## Acceptance

- Opening the package requires no model call.
- Pressing play scrolls the English.
- The Chinese visible beside each sentence is English-order component Chinese,
  not natural Chinese summary.
- Ask on a selected sentence returns an anchored Chinese explanation that quotes
  or names the English phrase being explained.
