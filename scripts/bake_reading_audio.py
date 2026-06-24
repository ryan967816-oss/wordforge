#!/usr/bin/env python3
"""Bake Deepgram TTS audio for pre-baked reading packages.

Generated mp3 files stay local under data/reading_audio/. The JSONL package can
record the local filename; WordForge hides that audio flag on machines where the
mp3 is absent.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wordforge import deepgram_tts, reading_packages  # noqa: E402


def _request_with_retries(text: str, model: str, speed: str, attempts: int = 3) -> bytes:
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return deepgram_tts._request_mp3(text, model, speed=speed)
        except Exception as e:
            last = e
            if attempt == attempts:
                break
            wait = 2 * attempt
            print(f"  retry {attempt}/{attempts - 1} after {type(e).__name__}: {e}; waiting {wait}s", flush=True)
            time.sleep(wait)
    assert last is not None
    raise last


def _duration_ms(path: Path) -> int:
    ffprobe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if ffprobe.returncode == 0 and ffprobe.stdout.strip():
        return max(1, int(float(ffprobe.stdout.strip()) * 1000))

    afinfo = subprocess.run(["afinfo", str(path)], text=True, capture_output=True, check=False)
    match = re.search(r"estimated duration:\s*([0-9.]+)\s*sec", afinfo.stdout)
    if match:
        return max(1, int(float(match.group(1)) * 1000))
    return 0


def _assign_timings(package: dict, duration_ms: int) -> None:
    segments = package.get("segments", []) or []
    if not segments or duration_ms <= 0:
        return
    weights = [max(1, len(str(s.get("text_en", "")))) for s in segments]
    total = sum(weights)
    cursor = 0
    for i, (segment, weight) in enumerate(zip(segments, weights)):
        end = duration_ms if i == len(segments) - 1 else round((sum(weights[: i + 1]) / total) * duration_ms)
        segment["start_ms"] = cursor
        segment["end_ms"] = max(cursor + 1, int(end))
        cursor = segment["end_ms"]


def _segment_ranges_for_chunks(segments: list[dict], chunks: list[str]) -> list[tuple[int, int]]:
    """Map each TTS chunk back to the sentence segments used to build it."""
    ranges: list[tuple[int, int]] = []
    idx = 0
    texts = [re.sub(r"\s+", " ", str(s.get("text_en", "")).strip()) for s in segments]
    for chunk in chunks:
        start = idx
        cur = ""
        while idx < len(texts):
            candidate = (cur + " " + texts[idx]).strip()
            # Allow a few chars of quote/space normalization drift.
            if cur and len(candidate) > len(chunk) + 5:
                break
            cur = candidate
            idx += 1
            if len(cur) >= len(chunk) - 5:
                break
        ranges.append((start, idx))
    if idx < len(texts) and ranges:
        start, _ = ranges[-1]
        ranges[-1] = (start, len(texts))
    return ranges


def _assign_timings_from_parts(package: dict, final_audio: Path, text: str, final_duration_ms: int) -> bool:
    """Use real per-chunk mp3 durations for tighter text/audio sync."""
    segments = package.get("segments", []) or []
    if not segments or final_duration_ms <= 0:
        return False
    chunks = deepgram_tts.chunk_text(text, max_chars=1200)
    parts = [final_audio.with_name(f"{final_audio.stem}.part-{i:03d}{final_audio.suffix}") for i in range(1, len(chunks) + 1)]
    if not all(p.exists() for p in parts):
        return False

    part_durations = [_duration_ms(p) for p in parts]
    if not all(d > 0 for d in part_durations):
        return False
    total_parts = sum(part_durations)
    scale = final_duration_ms / total_parts if total_parts else 1.0
    ranges = _segment_ranges_for_chunks(segments, chunks)

    cursor = 0
    for (start, end), part_duration in zip(ranges, part_durations):
        chunk_duration = max(1, round(part_duration * scale))
        chunk_end = min(final_duration_ms, cursor + chunk_duration)
        group = segments[start:end]
        if not group:
            cursor = chunk_end
            continue
        weights = [max(1, len(str(s.get("text_en", "")))) for s in group]
        total_weight = sum(weights)
        local = cursor
        for offset, (segment, weight) in enumerate(zip(group, weights)):
            if offset == len(group) - 1:
                seg_end = chunk_end
            else:
                seg_end = cursor + round((sum(weights[: offset + 1]) / total_weight) * chunk_duration)
            segment["start_ms"] = local
            segment["end_ms"] = max(local + 1, int(seg_end))
            local = segment["end_ms"]
        cursor = chunk_end
    if segments:
        segments[-1]["end_ms"] = final_duration_ms
    package["audio_timing"] = "chunk-duration-proportional"
    return True


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def _concat_mp3(parts: list[Path], output: Path) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as f:
        list_path = Path(f.name)
        for part in parts:
            f.write(f"file '{part.as_posix()}'\n")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(output)],
            check=True,
        )
    finally:
        list_path.unlink(missing_ok=True)


def bake_package(
    package: dict,
    *,
    force: bool = False,
    model: str = deepgram_tts.DEFAULT_MODEL,
    speed: str = deepgram_tts.DEFAULT_SPEED,
    workers: int = 1,
) -> dict:
    package_id = str(package.get("id", "")).strip()
    if not package_id:
        raise ValueError("package missing id")
    text = " ".join(str(s.get("text_en", "")).strip() for s in package.get("segments", []) or []).strip()
    if not text:
        text = str(package.get("text_en", "")).strip()
    if not text:
        raise ValueError(f"{package_id}: no text to speak")

    out_dir = deepgram_tts.audio_dir()
    filename = f"{deepgram_tts.safe_slug(package_id)}.mp3"
    path = out_dir / filename
    if force or not path.exists():
        chunks = deepgram_tts.chunk_text(text, max_chars=1200)
        parts: list[Path] = []
        jobs: list[tuple[int, str, Path]] = []
        for i, chunk in enumerate(chunks, 1):
            part = out_dir / f"{path.stem}.part-{i:03d}.mp3"
            if force or not part.exists():
                jobs.append((i, chunk, part))
            parts.append(part)
        if jobs:
            def generate(job: tuple[int, str, Path]) -> tuple[int, Path]:
                i, chunk, part = job
                print(f"{package_id}: TTS chunk {i}/{len(chunks)} ({len(chunk)} chars)", flush=True)
                part.write_bytes(_request_with_retries(chunk, model, speed))
                return i, part

            with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
                futures = [pool.submit(generate, job) for job in jobs]
                for fut in as_completed(futures):
                    i, part = fut.result()
                    print(f"{package_id}: done chunk {i}/{len(chunks)} -> {part.name}", flush=True)
        if len(parts) == 1:
            path.write_bytes(parts[0].read_bytes())
        else:
            _concat_mp3(parts, path)

    duration_ms = _duration_ms(path)
    package["audio_file"] = filename
    package["audio_model"] = model
    package["audio_speed"] = speed
    if duration_ms:
        package["audio_duration_ms"] = duration_ms
        if not _assign_timings_from_parts(package, path, text, duration_ms):
            package["audio_timing"] = "global-character-proportional"
            _assign_timings(package, duration_ms)
    return {"id": package_id, "file": filename, "duration_ms": duration_ms, "chars": len(text)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=str(reading_packages.emerson_path()))
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--model", default=deepgram_tts.DEFAULT_MODEL)
    parser.add_argument("--speed", default=deepgram_tts.DEFAULT_SPEED)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    if not deepgram_tts.configured():
        raise SystemExit("Deepgram key is not configured. Run scripts/set_deepgram_key.py first.")

    path = Path(args.path)
    rows = _load_jsonl(path)
    outputs = []
    for row in rows:
        if row.get("category", "book") != "book":
            continue
        outputs.append(
            bake_package(row, force=args.force, model=args.model, speed=args.speed, workers=args.workers)
        )
    _write_jsonl(path, rows)
    print(json.dumps({"path": str(path), "count": len(outputs), "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
