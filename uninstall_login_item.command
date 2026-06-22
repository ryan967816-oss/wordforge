#!/bin/bash
# Stop the resident WordForge service and remove it from login.
PLIST="$HOME/Library/LaunchAgents/com.wordforge.agent.plist"
launchctl unload "$PLIST" 2>/dev/null
pkill -f -- '-m wordforge\.app' 2>/dev/null
rm -f "$PLIST"
echo "WordForge resident service removed and stopped."
echo "(You can still launch it manually with run.command.)"
read -n 1 -s -r -p "Press any key to close."
