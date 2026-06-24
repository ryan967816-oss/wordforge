#!/bin/bash
# Stop and remove the WordForge Studio backend LaunchAgent.
cd "$(dirname "$0")" || exit 1

PLIST="$HOME/Library/LaunchAgents/com.wordforge.studio.plist"
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null
pkill -f -- '-m wordforge\.studio' 2>/dev/null
rm -f "$PLIST"

echo "✓ Removed WordForge Studio resident backend."
read -n 1 -s -r -p "Press any key to close."
