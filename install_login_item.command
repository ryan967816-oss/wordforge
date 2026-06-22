#!/bin/bash
# Make WordForge a real resident service: starts at login, restarts if it
# crashes, runs menu-bar-only (no Dock icon). Double-click to install.
cd "$(dirname "$0")" || exit 1

PLIST="$HOME/Library/LaunchAgents/com.wordforge.agent.plist"
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"

if [ ! -d .venv ]; then
  echo "Run setup.command first."; read -n 1 -s -r -p "Press any key."; exit 1
fi

# Stop any running copies (LaunchAgent will be the single owner).
launchctl unload "$PLIST" 2>/dev/null
pkill -f -- '-m wordforge\.app' 2>/dev/null
sleep 1

# Generate the LaunchAgent plist. The Anthropic API key is embedded so the
# resident agent (which gets no shell env) can ground words; the file is chmod
# 600 (your-user-only) and is NOT in the git repo. Key comes from your shell
# env if present, else the macOS Keychain (Settings…).
./.venv/bin/python - "$PLIST" "$(pwd)" <<'PY'
import os, sys, plistlib
from pathlib import Path
plist_path, repo = sys.argv[1], sys.argv[2]
try:
    from wordforge import config
    kc = config.get_api_key()
except Exception:
    kc = None
key = os.environ.get("ANTHROPIC_API_KEY") or kc or ""
env = {"ANTHROPIC_API_KEY": key} if key else {}
data = {
    "Label": "com.wordforge.agent",
    "ProgramArguments": [str(Path(repo) / ".venv/bin/python"), "-m", "wordforge.app"],
    "WorkingDirectory": repo,
    "EnvironmentVariables": env,
    "RunAtLoad": True,
    "KeepAlive": {"SuccessfulExit": False},  # restart on crash, honor a clean Quit
    "StandardOutPath": str(Path.home() / "Library/Logs/WordForge.log"),
    "StandardErrorPath": str(Path.home() / "Library/Logs/WordForge.log"),
    "ProcessType": "Interactive",
}
with open(plist_path, "wb") as f:
    plistlib.dump(data, f)
os.chmod(plist_path, 0o600)
print("Wrote", plist_path, "(API key embedded)" if key else "(NO key — set it in Settings…)")
PY
chmod 600 "$PLIST"

launchctl load -w "$PLIST"
sleep 2
if pgrep -f -- '-m wordforge\.app' >/dev/null 2>&1; then
  echo
  echo "✓ WordForge is now resident: it starts at login and restarts if it crashes."
  echo "  To stop it for good, double-click uninstall_login_item.command."
  echo "  Logs: ~/Library/Logs/WordForge.log"
else
  echo "Did not start — check ~/Library/Logs/WordForge.log"
fi
read -n 1 -s -r -p "Press any key to close."
