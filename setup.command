#!/bin/bash
# Double-click to set up WordForge: creates a Python venv, installs deps,
# builds the starter lexicon. Run this once.
cd "$(dirname "$0")" || exit 1

echo "==> Setting up WordForge in: $(pwd)"
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3 first (e.g. from python.org or Homebrew)."
  read -n 1 -s -r -p "Press any key to close."; exit 1
fi

python3 -m venv .venv || { echo "venv creation failed"; read -n1 -s -r; exit 1; }
echo "==> Installing dependencies (this can take a minute)…"
./.venv/bin/python -m pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r requirements.txt || { echo "pip install failed"; read -n1 -s -r; exit 1; }

echo "==> Building starter lexicon…"
./.venv/bin/python scripts/build_seed.py

echo
echo "==> Done."
echo "    Next: double-click  run.command  to launch the menu-bar app."
echo "    The first time you Add a word, set your Anthropic API key via the"
echo "    menu-bar Settings… (or export ANTHROPIC_API_KEY in your shell profile)."
echo
read -n 1 -s -r -p "Press any key to close."
