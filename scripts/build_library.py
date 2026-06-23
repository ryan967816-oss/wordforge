"""Batch-build a big drill library: ground a word list via Claude into the lexicon.

    python scripts/build_library.py data/wordlists/library_seed.txt --workers 6

Resume-safe: words already in the lexicon are skipped, so you can stop/restart.
Grounding (the slow Claude calls) runs concurrently; adds to the store are
serialized (the store is file-locked). Progress is written to
data/wordlists/_build_status.json and printed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wordforge import config, grounding, store  # noqa: E402


def load_wordlist(path: Path) -> list[str]:
    words: list[str] = []
    seen = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        w = line.strip()
        if not w or w.startswith("#"):
            continue
        w = w.split("|")[0].strip()  # tolerate "word|sublist" form
        key = w.lower()
        if key not in seen:
            seen.add(key)
            words.append(w)
    return words


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("wordlist")
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--limit", type=int, default=0)
    args = p.parse_args()

    words = load_wordlist(Path(args.wordlist))
    existing = {w["headword"].lower() for w in store.load_words()}
    todo = [w for w in words if w.lower() not in existing]
    if args.limit:
        todo = todo[: args.limit]

    status_path = config.data_dir() / "wordlists" / "_build_status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    total = len(todo)
    done = 0
    failed: list[str] = []
    t0 = time.time()
    print(f"library build: {total} new words to ground (model={config.get_model()}), "
          f"{len(existing)} already in lexicon", flush=True)

    def write_status(current: str = "") -> None:
        status_path.write_text(json.dumps({
            "total": total, "done": done, "failed": len(failed),
            "current": current, "elapsed_s": round(time.time() - t0),
            "lexicon_size": len(existing) + done,
        }), encoding="utf-8")

    write_status()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(grounding.ground_word, w): w for w in todo}
        for fut in as_completed(futs):
            w = futs[fut]
            try:
                data = fut.result()
                store.add_word(data)          # serialized here (file-locked)
                done += 1
                print(f"  [{done}/{total}] + {data['headword']}", flush=True)
            except Exception as e:            # noqa: BLE001
                failed.append(w)
                print(f"  [!] {w}: {e}", flush=True)
            write_status(w)

    write_status()
    print(f"\ndone: grounded {done}/{total} in {round(time.time()-t0)}s. "
          f"lexicon now {len(existing)+done} words. failed: {len(failed)}", flush=True)
    if failed:
        print("  retry later (just re-run this script): " + ", ".join(failed[:20]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
