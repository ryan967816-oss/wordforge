"""Deepgram text-to-speech helpers for local WordForge audio.

The browser never sees the API key. This module reads it from WordForge's
existing config layer, then writes generated mp3 files under data/reading_audio.

Deepgram REST TTS docs:
https://developers.deepgram.com/docs/text-to-speech
https://developers.deepgram.com/docs/text-to-speech-latency
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from . import config

# Deep masculine English voice. Deepgram's model catalog describes Zeus as
# masculine, deep, trustworthy, and smooth.
DEFAULT_MODEL = "aura-2-zeus-en"
DEFAULT_SPEED = "1.2"
MAX_CHARS = 1900


def audio_dir() -> Path:
    d = config.data_dir() / "reading_audio"
    d.mkdir(parents=True, exist_ok=True)
    return d


def safe_slug(text: str, fallback: str = "wordforge-tts") -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", text.strip()).strip("-._").lower()
    return (slug or fallback)[:72]


def chunk_text(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    """Split text into API-sized chunks without cutting through sentences first."""
    clean = re.sub(r"\s+", " ", text.strip())
    if not clean:
        raise ValueError("empty text")
    if len(clean) <= max_chars:
        return [clean]

    pieces = re.split(r"(?<=[.!?。！？])\s+", clean)
    chunks: list[str] = []
    cur = ""
    for piece in pieces:
        if not piece:
            continue
        if len(piece) > max_chars:
            words = piece.split()
            for word in words:
                candidate = (cur + " " + word).strip()
                if len(candidate) > max_chars and cur:
                    chunks.append(cur)
                    cur = word
                else:
                    cur = candidate
            continue
        candidate = (cur + " " + piece).strip()
        if len(candidate) > max_chars and cur:
            chunks.append(cur)
            cur = piece
        else:
            cur = candidate
    if cur:
        chunks.append(cur)
    return chunks


def _request_mp3(text: str, model: str, speed: str = DEFAULT_SPEED) -> bytes:
    key = config.get_deepgram_api_key()
    if not key:
        raise RuntimeError("Deepgram key is not configured. Run scripts/set_deepgram_key.py first.")
    if len(text) > MAX_CHARS:
        raise ValueError(f"text chunk is too long for Deepgram TTS ({len(text)} chars)")

    query = urllib.parse.urlencode({"model": model, "speed": speed})
    url = f"https://api.deepgram.com/v1/speak?{query}"
    body = json.dumps({"text": text}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Token {key}",
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Deepgram TTS failed: HTTP {e.code}: {detail}") from e


def speak_to_files(
    text: str,
    slug: str = "",
    model: str = DEFAULT_MODEL,
    speed: str = DEFAULT_SPEED,
) -> list[dict[str, Any]]:
    chunks = chunk_text(text)
    base = safe_slug(slug or text[:48])
    stamp = time.strftime("%Y%m%d-%H%M%S")
    outputs: list[dict[str, Any]] = []
    for i, chunk in enumerate(chunks, 1):
        suffix = f"-{i:02d}" if len(chunks) > 1 else ""
        name = f"{base}-{stamp}{suffix}.mp3"
        path = audio_dir() / name
        path.write_bytes(_request_mp3(chunk, model, speed=speed))
        outputs.append(
            {
                "file": name,
                "path": str(path),
                "chars": len(chunk),
                "model": model,
                "speed": speed,
                "part": i,
                "parts": len(chunks),
            }
        )
    return outputs


def configured() -> bool:
    return bool(config.get_deepgram_api_key())
