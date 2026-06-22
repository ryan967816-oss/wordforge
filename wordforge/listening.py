"""Listening trainer — dictation from your California Edge audio library.

Pipeline (all local, no fragile deps): your .mp3  ->  afconvert (built-in) -> wav
->  whisper.cpp (whisper-cli) -> a sentence-segmented transcript (cached). Then
for each sentence it plays just that clip (afplay on a stdlib-sliced wav), you
type what you heard, and it scores you word-by-word and shows what you missed.

    python -m wordforge.listening library            # list your audio, numbered
    python -m wordforge.listening dictate <N|path>   # dictation session
    python -m wordforge.listening play <N|path>      # just listen (extensive)
    python -m wordforge.listening text <N|path>      # print the transcript

Setup it relies on (already installed): `brew install whisper-cpp` and the model
at models/ggml-base.en.bin. afconvert + afplay ship with macOS.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any

from . import config


class ListeningError(RuntimeError):
    pass


# --- locations ----------------------------------------------------------------

def listening_dir() -> Path:
    env = os.environ.get("WORDFORGE_LISTENING_DIR")
    if env:
        return Path(env).expanduser()
    # The real folder name has a trailing space — glob to find it robustly.
    matches = sorted(Path.home().joinpath("Documents").glob("english*listening*"))
    return matches[0] if matches else Path.home() / "Documents" / "english for listening"


def whisper_bin() -> str:
    return shutil.which("whisper-cli") or "/opt/homebrew/bin/whisper-cli"


def whisper_model() -> Path:
    env = os.environ.get("WORDFORGE_WHISPER_MODEL")
    return Path(env).expanduser() if env else config.repo_root() / "models" / "ggml-base.en.bin"


def cache_dir() -> Path:
    d = config.data_dir() / "listening"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _key(mp3: Path) -> str:
    return hashlib.sha1(str(mp3).encode("utf-8")).hexdigest()[:16]


# --- audio index --------------------------------------------------------------

def index_audio() -> list[Path]:
    root = listening_dir()
    if not root.exists():
        return []
    return sorted(root.rglob("*.mp3"))


def resolve_target(target: str) -> Path:
    """Accept a 1-based index from `library`, or a path."""
    if target.isdigit():
        files = index_audio()
        i = int(target) - 1
        if not (0 <= i < len(files)):
            raise ListeningError(f"index {target} out of range (1..{len(files)})")
        return files[i]
    p = Path(target).expanduser()
    if not p.exists():
        raise ListeningError(f"no such file: {p}")
    return p


# --- transcription (whisper.cpp) ---------------------------------------------

def _to_wav(mp3: Path, wav: Path) -> None:
    subprocess.run(
        ["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(mp3), str(wav)],
        check=True, capture_output=True,
    )


def _wav_path(mp3: Path) -> Path:
    wav = cache_dir() / f"{_key(mp3)}.wav"
    if not wav.exists():
        _to_wav(mp3, wav)
    return wav


def transcribe(mp3: Path) -> list[dict[str, Any]]:
    """Return [{start_ms, end_ms, text}], cached per file."""
    cache = cache_dir() / f"{_key(mp3)}.segments.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))

    model = whisper_model()
    if not model.exists():
        raise ListeningError(
            f"whisper model not found at {model}. Download ggml-base.en.bin into models/."
        )
    wav = _wav_path(mp3)
    out = cache_dir() / f"{_key(mp3)}.whisper"
    proc = subprocess.run(
        [whisper_bin(), "-m", str(model), "-f", str(wav), "-oj", "-of", str(out)],
        capture_output=True, text=True,
    )
    raw = Path(str(out) + ".json")  # whisper-cli writes "<-of>.json"
    if not raw.exists():
        raise ListeningError(f"whisper produced no output. stderr:\n{proc.stderr[-500:]}")
    data = json.loads(raw.read_text(encoding="utf-8"))
    segs = [
        {"start_ms": s["offsets"]["from"], "end_ms": s["offsets"]["to"], "text": s["text"].strip()}
        for s in data.get("transcription", [])
        if s.get("text", "").strip()
    ]
    cache.write_text(json.dumps(segs, ensure_ascii=False, indent=0), encoding="utf-8")
    return segs


# --- playback (stdlib wav slice + afplay) ------------------------------------

def _slice_wav(src_wav: Path, start_ms: int, end_ms: int, dst: Path) -> None:
    with wave.open(str(src_wav), "rb") as w:
        fr, nch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        start = max(0, int(start_ms / 1000 * fr))
        end = int(end_ms / 1000 * fr)
        w.setpos(min(start, w.getnframes()))
        frames = w.readframes(max(0, end - start))
    with wave.open(str(dst), "wb") as o:
        o.setnchannels(nch)
        o.setsampwidth(sw)
        o.setframerate(fr)
        o.writeframes(frames)


def play_segment(mp3: Path, seg: dict[str, Any]) -> None:
    wav = _wav_path(mp3)
    clip = cache_dir() / "clip.wav"
    _slice_wav(wav, seg["start_ms"], seg["end_ms"], clip)
    subprocess.run(["afplay", str(clip)], check=False)


def play_file(mp3: Path) -> None:
    subprocess.run(["afplay", str(mp3)], check=False)


# --- scoring ------------------------------------------------------------------

_WORD = re.compile(r"[a-z0-9']+")


def _words(s: str) -> list[str]:
    return _WORD.findall(s.lower())


def score(reference: str, heard: str) -> dict[str, Any]:
    ref, got = _words(reference), _words(heard)
    sm = difflib.SequenceMatcher(a=ref, b=got, autojunk=False)
    correct = sum(b - a for tag, a, b, c, d in sm.get_opcodes() if tag == "equal")
    accuracy = correct / len(ref) if ref else 1.0
    # words in the reference the learner missed or got wrong
    missed = []
    for tag, a, b, c, d in sm.get_opcodes():
        if tag in ("replace", "delete"):
            missed.extend(ref[a:b])
    return {"accuracy": accuracy, "correct": correct, "total": len(ref), "missed": missed}


# --- CLI ----------------------------------------------------------------------

def cmd_library(args: argparse.Namespace) -> int:
    files = index_audio()
    if not files:
        print(f"No .mp3 found under {listening_dir()}")
        print("Set WORDFORGE_LISTENING_DIR to your audio folder if it's elsewhere.")
        return 1
    root = listening_dir()
    print(f"{len(files)} audio files under {root.name}/ :\n")
    for i, f in enumerate(files, 1):
        rel = f.relative_to(root)
        print(f"  {i:4d}  {rel}")
    print("\nUse:  dictate <N>   |   play <N>   |   text <N>")
    return 0


def cmd_text(args: argparse.Namespace) -> int:
    mp3 = resolve_target(args.target)
    print(f"Transcribing {mp3.name} … (first time only; cached after)")
    segs = transcribe(mp3)
    for s in segs:
        print(f"[{s['start_ms']//1000:>3}s] {s['text']}")
    return 0


def cmd_play(args: argparse.Namespace) -> int:
    mp3 = resolve_target(args.target)
    print(f"Playing {mp3.name} … (Ctrl-C to stop)")
    play_file(mp3)
    return 0


def cmd_dictate(args: argparse.Namespace) -> int:
    mp3 = resolve_target(args.target)
    print(f"Preparing {mp3.name} … (transcribing first time; cached after)")
    segs = transcribe(mp3)
    if not segs:
        print("No speech segments found.")
        return 1
    print(f"{len(segs)} sentences. For each: it plays, you type what you heard.")
    print("Commands at the prompt:  [Enter]=replay  s=show answer  n=skip  q=quit\n")
    accs: list[float] = []
    all_missed: list[str] = []
    for idx, seg in enumerate(segs, 1):
        print(f"--- sentence {idx}/{len(segs)} ---")
        play_segment(mp3, seg)
        while True:
            try:
                ans = input("heard> ").strip()
            except EOFError:
                ans = "q"
            if ans == "":
                play_segment(mp3, seg)
                continue
            if ans.lower() == "q":
                _summary(accs, all_missed)
                return 0
            if ans.lower() == "n":
                break
            if ans.lower() == "s":
                print(f"  answer: {seg['text']}")
                continue
            r = score(seg["text"], ans)
            pct = int(r["accuracy"] * 100)
            print(f"  {pct}%  ({r['correct']}/{r['total']} words)")
            print(f"  answer: {seg['text']}")
            if r["missed"]:
                print(f"  you missed: {', '.join(r['missed'])}")
            accs.append(r["accuracy"])
            all_missed.extend(r["missed"])
            break
        print()
    _summary(accs, all_missed)
    return 0


def _summary(accs: list[float], missed: list[str]) -> None:
    if accs:
        avg = int(sum(accs) / len(accs) * 100)
        print(f"\nSession: {len(accs)} sentences, average {avg}% words caught.")
    from collections import Counter
    common = Counter(w for w in missed if len(w) > 2).most_common(12)
    if common:
        print("Words you missed most (candidates for WordForge):")
        print("  " + ", ".join(f"{w}×{c}" for w, c in common))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wordforge.listening", description="Listening / dictation trainer")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("library").set_defaults(fn=cmd_library)
    for name, fn in (("dictate", cmd_dictate), ("play", cmd_play), ("text", cmd_text)):
        sp = sub.add_parser(name)
        sp.add_argument("target", help="index from `library`, or a path")
        sp.set_defaults(fn=fn)
    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except ListeningError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
