#!/bin/bash
# Build + launch the NATIVE WordForge (SwiftUI, real glass/vibrancy) front end.
# It talks to the Python backend at localhost:8764, so the engines are reused.
#
# First run only: fixes a known Command Line Tools bug (a stale duplicate Swift
# module map from 2023 that breaks every GUI-Swift compile). That step needs your
# admin password and is fully reversible (the file is renamed to .bak, not deleted).
cd "$(dirname "$0")/.." || exit 1
REPO="$(pwd)"
SWIFT="native/WordForge.swift"
APP="dist/WordForge.app"

MM="/Library/Developer/CommandLineTools/usr/include/swift/module.modulemap"
BR="/Library/Developer/CommandLineTools/usr/include/swift/bridging.modulemap"
if [ -f "$MM" ] && [ -f "$BR" ] && grep -q "module SwiftBridging" "$MM"; then
  echo "==> One-time toolchain fix: renaming a stale Swift module map (needs your password)."
  echo "    (reversible — kept as module.modulemap.bak)"
  sudo mv "$MM" "$MM.bak" && echo "    fixed." || { echo "    fix failed"; read -n1 -s -r; exit 1; }
fi

echo "==> Compiling the native app…"
rm -rf "$APP"; mkdir -p "$APP/Contents/MacOS"
if swiftc -swift-version 5 -O "$SWIFT" -o "$APP/Contents/MacOS/WordForge" -framework AppKit -framework SwiftUI; then
  cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>WordForge</string>
  <key>CFBundleExecutable</key><string>WordForge</string>
  <key>CFBundleIdentifier</key><string>com.wordforge.native</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>0.1</string>
  <key>NSPrincipalClass</key><string>NSApplication</string>
  <key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST
  echo "    built $APP"
  echo "==> Making sure the Python backend is up (the native app calls it)…"
  pgrep -f -- '-m wordforge\.studio' >/dev/null 2>&1 || nohup "$REPO/.venv/bin/python" -m wordforge.studio >/tmp/wf_studio.log 2>&1 &
  sleep 1
  echo "==> Launching the native glass window…"
  open "$APP"
  echo "Done. If the window is empty, the backend wasn't up yet — re-run this."
else
  echo
  echo "!! COMPILE FAILED — copy ALL the error lines above and paste them to Claude."
fi
read -n 1 -s -r -p "Press any key to close."
