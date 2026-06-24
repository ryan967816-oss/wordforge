#!/usr/bin/env python3
"""Store a Deepgram API key in the macOS Keychain for WordForge.

The prompt uses hidden input. Do not pass keys as command-line arguments because
shell history and process listings can expose them.
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wordforge import config  # noqa: E402


def main() -> int:
    key = getpass.getpass("Deepgram API key: ").strip()
    if not key:
        print("No key entered; nothing saved.")
        return 1
    config.set_deepgram_api_key(key)
    print("Deepgram API key saved to Keychain service WordForge.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
