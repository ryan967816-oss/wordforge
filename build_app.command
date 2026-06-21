#!/bin/bash
# OPTIONAL: build a standalone WordForge.app (Dock-less menu-bar bundle).
# run.command already launches the app — use this only if you want a real .app
# to add to Login Items. py2app bundling can be finicky; if it fails, just use
# run.command.
cd "$(dirname "$0")" || exit 1

if [ ! -d .venv ]; then
  echo "Run setup.command first."; read -n 1 -s -r -p "Press any key."; exit 1
fi

echo "==> Installing py2app…"
./.venv/bin/pip install --quiet py2app
echo "==> Building WordForge.app (this can take a few minutes)…"
rm -rf build dist
./.venv/bin/python setup_app.py py2app

if [ -d "dist/WordForge.app" ]; then
  echo
  echo "==> Built: dist/WordForge.app"
  echo "    Move it to /Applications and add it to System Settings > General >"
  echo "    Login Items to launch at startup. Set your API key via Settings…"
  open dist 2>/dev/null
else
  echo "==> Build did not produce dist/WordForge.app. Use run.command instead."
fi
read -n 1 -s -r -p "Press any key to close."
