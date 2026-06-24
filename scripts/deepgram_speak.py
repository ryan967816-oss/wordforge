#!/usr/bin/env python3
"""Turn stdin or a command-line string into local mp3 files via Deepgram TTS."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wordforge import deepgram_tts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="*", help="Text to speak. If omitted, read stdin.")
    ap.add_argument("--slug", default="wordforge-tts", help="Safe output filename prefix.")
    ap.add_argument("--model", default=deepgram_tts.DEFAULT_MODEL)
    ap.add_argument("--speed", default=deepgram_tts.DEFAULT_SPEED)
    args = ap.parse_args()

    text = " ".join(args.text).strip() or sys.stdin.read().strip()
    outputs = deepgram_tts.speak_to_files(text, slug=args.slug, model=args.model, speed=args.speed)
    print(json.dumps({"outputs": outputs}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
