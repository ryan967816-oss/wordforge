#!/usr/bin/env python3
"""Pre-generate Chinese scaffold cache for vocabulary drills.

This is intentionally a data-prep script, not a Studio request path. It walks the
local lexicon, finds multiple-choice drills, and fills data/drill_scaffolds.jsonl
so Vocab practice opens from cache instead of waiting on the model.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wordforge import config, drill_scaffold, store  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--limit", type=int, default=0, help="maximum new scaffolds to generate; 0 means all")
    p.add_argument("--sleep", type=float, default=0, help="reserved for sequential throttling")
    p.add_argument("--workers", type=int, default=4, help="parallel model calls")
    p.add_argument("--dry-run", action="store_true", help="count missing scaffolds without generating")
    p.add_argument("--include-typed", action="store_true", help="also include non-multiple-choice drills")
    p.add_argument(
        "--provider",
        default="deepseek",
        choices=["deepseek", "anthropic", "auto"],
        help="provider to use for this batch; default is deepseek",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.provider != "auto":
        os.environ["WORDFORGE_PROVIDER"] = args.provider

    words = store.load_words()
    cached = drill_scaffold.cached_keys()
    jobs: list[tuple[dict, dict, str]] = []
    for word in words:
        headword = str(word.get("headword", ""))
        for drill in drill_scaffold.word_drills(word, multiple_choice_only=not args.include_typed):
            key = drill_scaffold.key_for(headword, drill)
            if key not in cached:
                jobs.append((word, drill, key))

    print(f"provider: {config.get_provider()}")
    print(f"cache: {drill_scaffold.cache_path()}")
    print(f"words: {len(words)}")
    print(f"missing scaffolds: {len(jobs)}")
    if args.dry_run or not jobs:
        return 0

    total = len(jobs) if args.limit <= 0 else min(args.limit, len(jobs))
    ok = fallback = failed = 0
    started = time.time()
    selected = jobs[:total]

    def run_one(job: tuple[dict, dict, str]) -> tuple[str, str, bool, str]:
        word, drill, _key = job
        headword = str(word.get("headword", ""))
        kind = str(drill.get("kind", ""))
        prompt = " ".join(str(drill.get("prompt", "")).split())[:70]
        try:
            result = drill_scaffold.build(word, drill)
        except Exception as e:  # noqa: BLE001
            return headword, f"{kind} · {prompt}", False, f"error: {type(e).__name__}: {e}"
        if result.get("fallback"):
            return headword, f"{kind} · {prompt}", False, f"fallback: {result.get('error', '')}"
        return headword, f"{kind} · {prompt}", True, "cached"

    workers = max(1, args.workers)
    ex = ThreadPoolExecutor(max_workers=workers)
    try:
        futures = {ex.submit(run_one, job): job for job in selected}
        for i, fut in enumerate(as_completed(futures), 1):
            headword, label, success, message = fut.result()
            if success:
                ok += 1
            elif message.startswith("fallback:"):
                fallback += 1
            else:
                failed += 1
            print(f"[{i}/{total}] {headword} · {label}", flush=True)
            print(f"  {message}", flush=True)
            if failed and failed % 10 == 0:
                print("  warning: repeated failures; check provider/rate limits.", flush=True)
    except KeyboardInterrupt:
        ex.shutdown(wait=False, cancel_futures=True)
        print("interrupted; completed cache rows were kept", flush=True)
        return 130
    finally:
        ex.shutdown(wait=False, cancel_futures=True)

    elapsed = time.time() - started
    print(f"done: ok={ok} fallback={fallback} failed={failed} elapsed={elapsed:.1f}s")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
