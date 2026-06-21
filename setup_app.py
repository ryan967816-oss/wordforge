"""py2app build config for a standalone WordForge.app.

Usage (via build_app.command):
    ./.venv/bin/pip install py2app
    ./.venv/bin/python setup_app.py py2app

This is OPTIONAL polish — run.command already launches the native menu-bar app.
The .app gives you a Dock-less, double-clickable bundle you can add to Login
Items. When run as a bundle, the lexicon lives in ~/Documents/WordForge.
"""

from setuptools import setup

APP = ["run_app.py"]

OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "WordForge",
        "CFBundleDisplayName": "WordForge",
        "CFBundleIdentifier": "com.wordforge.app",
        "CFBundleVersion": "0.1.0",
        "LSUIElement": True,  # menu-bar only, no Dock icon
        "NSHumanReadableCopyright": "WordForge",
    },
    "packages": ["wordforge", "anthropic", "keyring", "rumps", "pynput"],
    "includes": ["httpx", "httpcore", "certifi", "anyio", "pydantic", "pydantic_core"],
    "resources": ["wordforge/data/seed_words.jsonl"],
}

setup(
    app=APP,
    name="WordForge",
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
