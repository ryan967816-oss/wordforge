#!/bin/bash
# WordForge — open the native macOS window (frameless, vibrancy).
# Double-click this file in Finder.
cd "$(dirname "$0")" || exit 1

PY=".venv/bin/python"
PIP=".venv/bin/pip"

if [ ! -x "$PY" ]; then
  echo "No .venv found. Run setup.command first."
  read -n 1 -s -r -p "Press any key to close…"
  exit 1
fi

# Install pywebview into the venv if it isn't there yet (one-time).
if ! "$PY" -c "import webview" 2>/dev/null; then
  echo "Installing pywebview (one-time)…"
  "$PIP" install pywebview >/dev/null
fi

echo "Opening WordForge…"
exec "$PY" -m wordforge.window
