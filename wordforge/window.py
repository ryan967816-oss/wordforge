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
import threading
import time

# Make the studio server NOT pop open a browser tab — we host it in our window.
os.environ.setdefault("WORDFORGE_NO_OPEN", "1")

from . import studio  # noqa: E402  (after env var is set)


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

    # 1) start the Studio server (blocking serve_forever) in the background
    threading.Thread(target=studio.main, daemon=True).start()
    time.sleep(0.8)  # let it bind the port

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
