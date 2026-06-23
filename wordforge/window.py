"""WordForge — native macOS window.

    python -m wordforge.window

Runs the existing Studio HTTP server in a background thread, then opens it in a
real, frameless macOS window with **vibrancy** (the cold frosted-glass look that
lets the desktop blur through) instead of a browser tab. Everything else — all
routes, all data — is the same `studio` server.

Requires pywebview:  pip install pywebview
(run_native.command installs it automatically into the venv.)
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
import urllib.error
import urllib.request

# Make the studio server NOT pop open a browser tab — we host it in our window.
os.environ.setdefault("WORDFORGE_NO_OPEN", "1")

from . import studio  # noqa: E402  (after env var is set)


def _backend_ready() -> bool:
    """The native shell needs the current Studio API, not merely any server."""
    url = f"http://127.0.0.1:{studio.PORT}/api/translate/corpus"
    try:
        with urllib.request.urlopen(url, timeout=1.0) as r:
            return r.status == 200
    except (OSError, urllib.error.URLError):
        return False


def _stop_stale_backend() -> None:
    """Clear an old WordForge Studio process from this port before opening native."""
    try:
        out = subprocess.run(
            ["lsof", "-tiTCP:%d" % studio.PORT, "-sTCP:LISTEN"],
            text=True,
            capture_output=True,
            check=False,
        ).stdout
    except OSError:
        return
    for raw in out.splitlines():
        pid = raw.strip()
        if pid:
            subprocess.run(["kill", pid], check=False)
    if out.strip():
        time.sleep(0.8)


def _ensure_backend() -> None:
    if _backend_ready():
        return
    _stop_stale_backend()
    if _backend_ready():
        return
    threading.Thread(target=studio.main, daemon=True).start()
    for _ in range(30):
        if _backend_ready():
            return
        time.sleep(0.1)
    raise RuntimeError(f"WordForge backend did not become ready on :{studio.PORT}")


class _Api:
    """Tiny JS bridge so the frameless window's traffic lights actually work."""

    def close(self) -> None:
        import webview
        for w in list(webview.windows):
            try:
                w.destroy()
            except Exception:
                pass

    def minimize(self) -> None:
        import webview
        try:
            webview.windows[0].minimize()
        except Exception:
            pass


def run() -> None:
    try:
        import webview
    except ImportError:
        raise SystemExit(
            "pywebview is not installed.\n"
            "  ./.venv/bin/pip install pywebview\n"
            "or just double-click run_native.command."
        )

    # 1) make sure the current Studio server is ready. If a stale server from an
    #    older run is still on the port, replace it so the native window has the
    #    corpus-backed Translate API.
    _ensure_backend()

    url = f"http://localhost:{studio.PORT}"
    api = _Api()

    # 2) open a native window. Try the full glassy treatment first; fall back
    #    gracefully on older pywebview builds that lack some kwargs.
    common = dict(
        title="WordForge",
        url=url,
        width=1200,
        height=820,
        min_size=(960, 660),
        background_color="#0A0D12",
        js_api=api,
    )
    try:
        window = webview.create_window(
            frameless=True, easy_drag=True, transparent=True, vibrancy=True, **common
        )
    except TypeError:
        # older pywebview: no vibrancy/transparent/frameless support
        window = webview.create_window(**common)

    # 3) start the GUI loop (vibrancy is also a start() kwarg on some versions)
    try:
        webview.start(vibrancy=True)
    except TypeError:
        webview.start()


if __name__ == "__main__":
    run()
