"""WordForge — native macOS menu-bar app.

Menu-bar item (📖 with a due-count badge) → add words, drill, write graded
sentences, run an article upgrade pass, see stats, settings. A global hotkey
(default ⌘⌥D) fires the next due drill from anywhere.

Threading model
---------------
rumps runs the AppKit run loop on the main thread; all UI (dialogs, alerts)
must happen there. Slow work (Claude API calls) runs on worker threads, which
push zero-arg callables onto a queue. A rumps.Timer drains that queue on the
main thread, so worker results open their dialogs safely. The global hotkey
fires on pynput's listener thread and likewise enqueues onto the main thread.
"""

from __future__ import annotations

import queue
import subprocess
import threading
from datetime import datetime, timezone
from typing import Any, Callable

import rumps

from . import config, drills, grounding, scheduler, store

POLL_INTERVAL = 0.25  # seconds; main-thread queue drain + badge refresh


class WordForgeApp(rumps.App):
    def __init__(self) -> None:
        super().__init__(config.APP_NAME, title="📖", quit_button=None)
        self._main_q: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self._busy = False  # guard against overlapping API jobs
        self._build_menu()
        self._timer = rumps.Timer(self._on_tick, POLL_INTERVAL)
        self._timer.start()
        self._tick_count = 0
        self._start_hotkey()
        self._refresh_badge()

    # --- menu -----------------------------------------------------------------

    def _build_menu(self) -> None:
        self.menu = [
            rumps.MenuItem("Add word…", callback=self.on_add_word),
            rumps.MenuItem("Drill (keeps going)", callback=self.on_drill),
            rumps.MenuItem("Quick drill (one word)", callback=self.on_quick_drill),
            rumps.MenuItem("My mistakes & weak words", callback=self.on_weak),
            None,
            rumps.MenuItem("Write a sentence (graded)…", callback=self.on_use_word),
            rumps.MenuItem("Look up a word…", callback=self.on_lookup),
            rumps.MenuItem("Upgrade an article…", callback=self.on_upgrade),
            None,
            rumps.MenuItem("Stats", callback=self.on_stats),
            rumps.MenuItem("Open data folder", callback=self.on_open_data),
            rumps.MenuItem("Settings…", callback=self.on_settings),
            None,
            rumps.MenuItem("Quit WordForge", callback=rumps.quit_application),
        ]

    # --- main-thread plumbing -------------------------------------------------

    def _hide_dock_icon(self) -> None:
        # Menu-bar only — no Dock icon — regardless of how we're launched
        # (terminal, nohup, or a launchd LaunchAgent). Done once the run loop
        # is up so the shared NSApplication exists.
        try:
            from AppKit import NSApp, NSApplicationActivationPolicyAccessory
            NSApp().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        except Exception:
            pass

    def _on_tick(self, _timer: rumps.Timer) -> None:
        if not getattr(self, "_dock_hidden", False):
            self._hide_dock_icon()
            self._dock_hidden = True
        # Drain any callables queued by worker / hotkey threads.
        while True:
            try:
                fn = self._main_q.get_nowait()
            except queue.Empty:
                break
            try:
                fn()
            except Exception as e:  # never let a UI callback kill the timer
                self._alert("WordForge error", str(e))
        # Refresh the due-count badge roughly every 5s.
        self._tick_count += 1
        if self._tick_count % int(5 / POLL_INTERVAL) == 0:
            self._refresh_badge()

    def _enqueue(self, fn: Callable[[], None]) -> None:
        self._main_q.put(fn)

    def _run_worker(self, work: Callable[[], Any], on_done: Callable[[Any], None],
                    on_error: Callable[[Exception], None] | None = None) -> None:
        """Run `work` on a thread; deliver result/error to the main thread."""
        def runner() -> None:
            try:
                result = work()
            except Exception as e:  # noqa: BLE001 - surface to UI
                self._enqueue(lambda: (on_error or self._default_error)(e))
            else:
                self._enqueue(lambda: on_done(result))
            finally:
                self._enqueue(self._clear_busy)
        threading.Thread(target=runner, daemon=True).start()

    def _clear_busy(self) -> None:
        self._busy = False
        self._refresh_badge()

    def _default_error(self, e: Exception) -> None:
        self._alert("WordForge error", str(e))

    # --- badge ----------------------------------------------------------------

    def _refresh_badge(self) -> None:
        try:
            n = store.stats()["due_now"]
        except Exception:
            n = 0
        base = "⏳📖" if self._busy else "📖"
        self.title = f"{base} {n}" if n else base

    # --- small UI helpers -----------------------------------------------------

    def _alert(self, title: str, message: str = "", ok: str = "OK") -> None:
        rumps.alert(title=title, message=message, ok=ok)

    def _prompt(self, title: str, message: str = "", default: str = "",
                ok: str = "OK", cancel: str = "Cancel", lines: int = 1) -> str | None:
        """Modal text prompt. Returns the entered text, or None if cancelled."""
        win = rumps.Window(
            message=message, title=title, default_text=default,
            ok=ok, cancel=cancel,
            dimensions=(360, 22 * max(1, lines)),
        )
        resp = win.run()
        if not resp.clicked:
            return None
        return resp.text.strip()

    # --- actions: add ---------------------------------------------------------

    def on_add_word(self, _sender: Any) -> None:
        term = self._prompt("Add a word", "Type a word or short phrase to ground and learn:")
        if not term:
            return
        if self._busy:
            self._alert("Busy", "Another word is being grounded — try again in a moment.")
            return
        self._busy = True
        self._refresh_badge()
        self._run_worker(
            work=lambda: grounding.ground_word(term),
            on_done=self._after_ground,
        )

    def _after_ground(self, data: dict[str, Any]) -> None:
        created = store.add_word(data)
        self._refresh_badge()
        self._alert(
            f"{'Added' if created else 'Updated'}: {data['headword']}",
            _format_entry(data),
        )

    # --- actions: drill -------------------------------------------------------

    def on_drill(self, _sender: Any) -> None:
        # Continuous: drill due words, then the weakest words for extra practice,
        # until you press Stop. Never abruptly ends after one word.
        self._run_drill_session()

    def on_quick_drill(self, _sender: Any) -> None:
        words = store.load_words()
        if not words:
            self._alert("No words yet", "Add a word first (Add word…).")
            return
        due = drills.next_due_word(words)
        word = due or store.weakest_word(words)
        practice = due is None
        drill = drills.pick_drill(word)
        if not drill:
            self._alert("No drills", f"'{word['headword']}' has no drills.")
            return
        answered, correct = self._present_drill(word, drill)
        if answered:
            self._grade_and_log(word, drill, correct, practice)
        store.update_word(word)
        self._refresh_badge()

    def _run_drill_session(self) -> None:
        """Modally loop — due words first, then the weakest words for extra
        practice — until the user presses Stop."""
        count = 0
        while True:
            words = store.load_words()
            if not words:
                self._alert("No words yet", "Add a word first (Add word…).")
                return
            due = drills.next_due_word(words)
            word = due or store.weakest_word(words)
            practice = due is None
            drill = drills.pick_drill(word)
            if not drill:
                store.update_word(word)  # advance cursor even if empty
                continue
            answered, correct = self._present_drill(word, drill)
            if not answered:  # Stop
                store.update_word(word)
                self._refresh_badge()
                self._alert("Session ended",
                            f"Reviewed {count} item(s). 📈" if count else "Stopped.")
                return
            self._grade_and_log(word, drill, correct, practice)
            store.update_word(word)
            self._refresh_badge()
            count += 1

    def _present_drill(self, word: dict[str, Any], drill: dict[str, Any]) -> tuple[bool, bool | None]:
        """Show one drill; report (answered, correct). No scheduling/logging here."""
        if drill.get("kind") == "discrimination":
            opts = "\n".join(f"  {i}. {o}" for i, o in enumerate(drill.get("options", []), 1))
            note = (f"Pick the word that best fits the context — it may be a near-synonym, "
                    f"not necessarily “{word['headword']}”.")
            msg = f"{note}\n\n{drill['prompt']}\n\n{opts}\n\n(Type the number or the word.)"
            title = f"Word choice — {word['headword']} & near-synonyms"
        else:
            msg = f"{drill['prompt']}\n\n(Type the antonym.)"
            title = f"Antonym — {word['headword']}"
        answer = self._prompt(title, msg, ok="Submit", cancel="Stop", lines=4)
        if answer is None:
            return False, None
        correct, explanation = drills.check_answer(word, drill, answer)
        verdict = "✓ Correct" if correct else f"✗ Not quite — answer: {drill['answer']}"
        self._alert(verdict, explanation)
        return True, correct

    def _grade_and_log(self, word: dict[str, Any], drill: dict[str, Any],
                       correct: bool, practice: bool) -> None:
        """Update the schedule and log the review. Mistakes are recorded in BOTH
        normal and extra-practice modes (correct flag + lapses + production score)."""
        if practice:
            # Past the due queue: don't push correct words further out (protect the
            # real SRS schedule); resurface a missed word immediately.
            grade = "good" if correct else "again"
            if not correct:
                word["due"] = store.now_iso()
                word["lapses"] = int(word.get("lapses", 0)) + 1
                word["production_score"] = max(0, int(word.get("production_score", 0)) - 1)
        else:
            grade = drills.grade_for_correctness(correct)
            scheduler.review(word, grade)
        store.append_review({"headword": word["headword"], "kind": drill.get("kind"),
                             "grade": grade, "correct": correct, "practice": practice})

    def on_weak(self, _sender: Any) -> None:
        words = store.load_words()
        missed = [w for w in store.weak_list(words) if int(w.get("lapses", 0)) > 0]
        lines: list[str] = []
        if missed:
            lines.append("Words you've missed (most-missed first):")
            for w in missed[:15]:
                lines.append(f"  • {w['headword']} — missed {w['lapses']}×, "
                             f"score {w.get('production_score', 0)}")
        else:
            lines.append("No misses logged yet. Drill a bit and they'll show up here.")
        recent = store.recent_mistakes(10)
        if recent:
            lines.append("\nRecent wrong answers:")
            for r in recent:
                lines.append(f"  • {r.get('headword','?')} ({r.get('kind','')}) "
                             f"— {str(r.get('ts',''))[:16].replace('T',' ')}")
        self._alert("My mistakes & weak words", "\n".join(lines))

    # --- actions: write a sentence (generative, graded) -----------------------

    def on_use_word(self, _sender: Any) -> None:
        words = store.load_words()
        default = (drills.next_due_word(words) or (words[0] if words else {})).get("headword", "")
        term = self._prompt("Write a sentence", "Which word do you want to use?", default=default)
        if not term:
            return
        w = store.find_word(store.load_words(), term)
        if not w:
            self._alert("Unknown word", f"'{term}' is not in your lexicon. Add it first.")
            return
        sentence = self._prompt(
            f"Use '{w['headword']}'", f"{w.get('core_sense','')}\n\nWrite your sentence:",
            ok="Grade it", lines=4,
        )
        if not sentence:
            return
        if self._busy:
            self._alert("Busy", "Try again in a moment.")
            return
        self._busy = True
        self._refresh_badge()
        self._run_worker(
            work=lambda: grounding.grade_sentence(w["headword"], w.get("core_sense", ""), sentence),
            on_done=lambda g: self._after_grade(w, g),
        )

    def _after_grade(self, w: dict[str, Any], g: dict[str, Any]) -> None:
        grade = drills.SCORE_TO_GRADE.get(g["score"], "good")
        scheduler.review(w, grade)
        store.update_word(w)
        store.append_review({"headword": w["headword"], "kind": "generative",
                             "grade": grade, "score": g["score"]})
        body = (
            f"Score: {g['score'].upper()}\n"
            f"Correct sense: {g['correct_sense']}   Natural collocation: {g['collocation_ok']}\n"
            f"Register: {g['register_fit']}\nNaturalness: {g['naturalness']}\n\n"
            f"{g['feedback']}"
        )
        if g.get("better_version"):
            body += f"\n\nSharper: {g['better_version']}"
        self._alert(f"Graded: {w['headword']}", body)
        self._refresh_badge()

    # --- actions: look up -----------------------------------------------------

    def on_lookup(self, _sender: Any) -> None:
        q = self._prompt("Look up", "Type a word in your lexicon (or part of a meaning):")
        if not q:
            return
        words = store.load_words()
        w = store.find_word(words, q)
        if w:
            self._alert(w["headword"], _format_entry(w))
            return
        ql = q.lower()
        matches = [w for w in words
                   if ql in w.get("core_sense", "").lower()
                   or any(ql in s.get("word", "").lower() for s in w.get("synonyms", []))]
        if matches:
            body = "\n".join(f"- {m['headword']}: {m.get('core_sense','')}" for m in matches[:8])
            self._alert(f"{len(matches)} match(es)", body)
        else:
            self._alert("Not found", f"'{q}' isn't in your lexicon yet. Use Add word… to learn it.")

    # --- actions: article upgrade --------------------------------------------

    def on_upgrade(self, _sender: Any) -> None:
        text = self._prompt("Upgrade an article", "Paste your draft — I'll suggest sharper "
                            "words, preferring your own learning-words:", lines=8)
        if not text:
            return
        if self._busy:
            self._alert("Busy", "Try again in a moment.")
            return
        known = [w["headword"] for w in store.load_words()]
        self._busy = True
        self._refresh_badge()
        self._run_worker(
            work=lambda: grounding.upgrade_article(text, known),
            on_done=self._after_upgrade,
        )

    def _after_upgrade(self, result: dict[str, Any]) -> None:
        sugs = result.get("suggestions", [])
        if not sugs:
            self._alert("No upgrades", "Your draft already reads well — nothing to sharpen.")
            return
        lines = []
        for s in sugs:
            tag = " ★your word" if s.get("from_your_words") else ""
            lines.append(f"• {s['original']} → {s['replacement']}{tag}\n    {s['rewritten_phrase']}\n    ({s['why']})")
        self._alert(f"{len(sugs)} upgrade(s)", "\n".join(lines))

    # --- actions: stats / data / settings ------------------------------------

    def on_stats(self, _sender: Any) -> None:
        s = store.stats()
        body = (
            f"Words in lexicon : {s['total_words']}\n"
            f"Due now          : {s['due_now']}\n"
            f"Reviewed today   : {s['reviewed_today']}\n"
            f"Reviews total    : {s['reviews_total']}\n"
            f"Avg production score : {s['avg_production_score']}\n\n"
            f"Model: {config.get_model()}\n"
            f"Hotkey: {config.get_hotkey()}"
        )
        self._alert("WordForge stats", body)

    def on_open_data(self, _sender: Any) -> None:
        subprocess.run(["open", str(config.data_dir())], check=False)

    def on_settings(self, _sender: Any) -> None:
        has_key = bool(config.get_api_key())
        status = "set ✓" if has_key else "NOT set ✗"
        msg = (
            f"API key: {status}\nModel: {config.get_model()}\n\n"
            "Paste an Anthropic API key to save it to your macOS Keychain "
            "(needed when launched as a .app, which gets no shell env). "
            "Leave blank to keep the current key.\n\n"
            "To change the model, set WORDFORGE_MODEL (e.g. claude-sonnet-4-6) "
            "before launching."
        )
        key = self._prompt("Settings", msg, ok="Save", cancel="Close")
        if key:
            try:
                config.set_api_key(key)
                self._alert("Saved", "API key stored in Keychain.")
            except Exception as e:
                self._alert("Could not save key", str(e))

    # --- global hotkey --------------------------------------------------------

    def _start_hotkey(self) -> None:
        import os
        if os.environ.get("WORDFORGE_NO_HOTKEY"):
            self._hotkey = None
            return
        try:
            from pynput import keyboard
        except Exception:
            return

        def on_activate() -> None:
            # Runs on pynput's thread; bounce to the main thread.
            self._enqueue(lambda: self._run_drill_session(due_only=True))

        try:
            self._hotkey = keyboard.GlobalHotKeys({config.get_hotkey(): on_activate})
            self._hotkey.daemon = True
            self._hotkey.start()
        except Exception:
            # Hotkey is optional; the menu still works without Accessibility perms.
            self._hotkey = None


def _format_entry(w: dict[str, Any]) -> str:
    lines = [f"{w.get('pos','')} · {w.get('register','')} · {w.get('frequency','')}",
             f"\n{w.get('core_sense','')}",
             f"\n💡 {w.get('image','')}"]
    if w.get("synonyms"):
        lines.append("\nSynonyms (when to prefer):")
        for s in w["synonyms"]:
            lines.append(f"  • {s['word']} [{s.get('register','')}] — {s['nuance']}")
    if w.get("antonyms"):
        lines.append("\nAntonyms: " + ", ".join(a["word"] for a in w["antonyms"]))
    if w.get("collocations"):
        lines.append("Collocations: " + ", ".join(w["collocations"]))
    if w.get("examples"):
        lines.append("\nExamples:")
        for ex in w["examples"]:
            lines.append(f"  – {ex}")
    return "\n".join(lines)


def main() -> None:
    WordForgeApp().run()


if __name__ == "__main__":
    main()
