#!/bin/bash
# Double-click to launch the WordForge menu-bar app. It detaches, so you can
# close this Terminal window and the 📖 icon stays in your menu bar.
cd "$(dirname "$0")" || exit 1

if [ ! -d .venv ]; then
  echo "WordForge isn't set up yet. Double-click setup.command first."
  read -n 1 -s -r -p "Press any key to close."; exit 1
fi

# Already running? Avoid a second menu-bar icon. Anchor on the actual launch
# token so an editor/tail of wordforge/app.py doesn't trip a false positive.
if pgrep -f -- '-m wordforge\.app' >/dev/null 2>&1; then
  echo "WordForge is already running (look for 📖 in your menu bar)."
  read -n 1 -s -r -p "Press any key to close."; exit 0
fi

LOG="$HOME/Library/Logs/WordForge.log"
mkdir -p "$(dirname "$LOG")"
echo "Launching WordForge…  (logs: $LOG)"
umask 077  # keep the log private to your user account
nohup ./.venv/bin/python -m wordforge.app > "$LOG" 2>&1 &
sleep 1
echo "Launched. Look for 📖 in your menu bar. You can close this window."
sleep 2
