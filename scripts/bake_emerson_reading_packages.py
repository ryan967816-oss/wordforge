#!/usr/bin/env python3
"""Bake the first Self-Reliance reading package from committed corpus rows."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wordforge import reading_packages


def main() -> None:
    print(json.dumps(reading_packages.bake_emerson_self_reliance(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
