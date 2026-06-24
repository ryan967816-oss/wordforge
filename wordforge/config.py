"""Configuration: paths, model, API key, hotkey.

The lexicon lives in the repo's `data/` directory by default so your whole
learning history is git-versioned and diffable. Override with WORDFORGE_DATA_DIR.

API key resolution order:
  1. Provider-specific env var (works when launched from a terminal / run.command)
  2. macOS Keychain (works for the double-clickable .app, which does NOT inherit
     your shell environment)
A double-clicked .app bundle gets no shell env vars, so the Keychain path is the
durable one — set it once via the menu-bar Settings dialog.
"""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "WordForge"
KEYCHAIN_SERVICE = "WordForge"
KEYCHAIN_ACCOUNT = "ANTHROPIC_API_KEY"
DEEPSEEK_KEYCHAIN_ACCOUNT = "DEEPSEEK_API_KEY"
DEEPGRAM_KEYCHAIN_ACCOUNT = "DEEPGRAM_API_KEY"
PROVIDER_KEYCHAIN_ACCOUNT = "WORDFORGE_PROVIDER"

# Default model. claude-opus-4-8 is the most capable; set WORDFORGE_MODEL to
# claude-sonnet-4-6 to cut grounding cost ~40% at a small quality tradeoff.
DEFAULT_MODEL = "claude-opus-4-8"

# Default global hotkey to fire the next due drill from anywhere.
DEFAULT_HOTKEY = "<cmd>+<alt>+d"


def repo_root() -> Path:
    """The project root (parent of this package directory)."""
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    import sys

    override = os.environ.get("WORDFORGE_DATA_DIR")
    if override:
        d = Path(override).expanduser()
    elif getattr(sys, "frozen", False):
        # Running inside a py2app .app bundle — the bundle is read-only, so keep
        # the learner's data in a writable, stable location.
        d = Path.home() / "Documents" / "WordForge"
    else:
        # Running from the repo (run.command / dev) — keep the lexicon in the
        # repo's data/ so the learning history is git-versioned and diffable.
        d = repo_root() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def lexicon_path() -> Path:
    return data_dir() / "lexicon.jsonl"


def reviews_path() -> Path:
    return data_dir() / "reviews.jsonl"


def seed_path() -> Path:
    # Shipped starter lexicon, copied into lexicon.jsonl on first run.
    return Path(__file__).resolve().parent / "data" / "seed_words.jsonl"


def get_model() -> str:
    return os.environ.get("WORDFORGE_MODEL", DEFAULT_MODEL)


def get_provider() -> str:
    provider = os.environ.get("WORDFORGE_PROVIDER")
    if provider:
        return provider.strip().lower()
    try:
        import keyring

        saved = keyring.get_password(KEYCHAIN_SERVICE, PROVIDER_KEYCHAIN_ACCOUNT)
        if saved:
            return saved.strip().lower()
    except Exception:
        pass
    return "deepseek" if get_deepseek_api_key() else "anthropic"


def get_deepseek_model() -> str:
    return os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")


def get_deepseek_base_url() -> str:
    return os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions")


def get_hotkey() -> str:
    return os.environ.get("WORDFORGE_HOTKEY", DEFAULT_HOTKEY)


def get_api_key() -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        import keyring

        return keyring.get_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
    except Exception:
        return None


def get_deepseek_api_key() -> str | None:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key:
        return key
    try:
        import keyring

        return keyring.get_password(KEYCHAIN_SERVICE, DEEPSEEK_KEYCHAIN_ACCOUNT)
    except Exception:
        return None


def get_deepgram_api_key() -> str | None:
    key = os.environ.get("DEEPGRAM_API_KEY")
    if key:
        return key
    try:
        import keyring

        return keyring.get_password(KEYCHAIN_SERVICE, DEEPGRAM_KEYCHAIN_ACCOUNT)
    except Exception:
        return None


def set_api_key(key: str) -> None:
    import keyring

    keyring.set_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT, key)


def set_deepseek_api_key(key: str) -> None:
    import keyring

    keyring.set_password(KEYCHAIN_SERVICE, DEEPSEEK_KEYCHAIN_ACCOUNT, key)


def set_deepgram_api_key(key: str) -> None:
    import keyring

    keyring.set_password(KEYCHAIN_SERVICE, DEEPGRAM_KEYCHAIN_ACCOUNT, key)


def set_provider(provider: str) -> None:
    import keyring

    keyring.set_password(KEYCHAIN_SERVICE, PROVIDER_KEYCHAIN_ACCOUNT, provider.strip().lower())
