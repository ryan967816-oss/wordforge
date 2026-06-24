#!/bin/bash
# WordForge Studio backend resident service.
# Starts the local Studio server at login and restarts it if it crashes.
cd "$(dirname "$0")" || exit 1

PLIST="$HOME/Library/LaunchAgents/com.wordforge.studio.plist"
LOG="$HOME/Library/Logs/WordForge-Studio.log"
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"

if [ ! -x ./.venv/bin/python ]; then
  echo "No .venv found. Run setup.command first."
  read -n 1 -s -r -p "Press any key to close."
  exit 1
fi

# The resident backend should own :8764. Close native Studio windows and any
# older standalone Studio server before launchd starts the durable one.
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null
pkill -f -- '-m wordforge\.studio' 2>/dev/null
pkill -f -- '-m wordforge\.window' 2>/dev/null
sleep 1

./.venv/bin/python - "$PLIST" "$(pwd)" "$LOG" <<'PY'
import os
import plistlib
import sys
from pathlib import Path

plist_path, repo, log_path = sys.argv[1], sys.argv[2], sys.argv[3]
data = {
    "Label": "com.wordforge.studio",
    "ProgramArguments": [str(Path(repo) / ".venv/bin/python"), "-m", "wordforge.studio"],
    "WorkingDirectory": repo,
    "EnvironmentVariables": {"WORDFORGE_NO_OPEN": "1"},
    "RunAtLoad": True,
    "KeepAlive": {"SuccessfulExit": False},
    "StandardOutPath": log_path,
    "StandardErrorPath": log_path,
    "ProcessType": "Background",
}
with open(plist_path, "wb") as f:
    plistlib.dump(data, f)
os.chmod(plist_path, 0o600)
print("Wrote", plist_path)
PY
chmod 600 "$PLIST"

launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null || launchctl load -w "$PLIST"
sleep 2

if curl -fsS "http://127.0.0.1:8764/api/translate/routes" >/dev/null 2>&1; then
  echo
  echo "✓ WordForge Studio backend is now resident at http://127.0.0.1:8764"
  echo "  Open the native reader with run_native.command or the menu-bar Open Studio Reader item."
  echo "  Logs: $LOG"
else
  echo
  echo "Studio did not become ready. Check: $LOG"
fi

read -n 1 -s -r -p "Press any key to close."
