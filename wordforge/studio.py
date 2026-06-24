"""WordForge Studio — one local web UI for the main training pillars.

    python -m wordforge.studio      # serves http://localhost:8764

This module is deliberately a thin shell. It keeps the existing engines
(`store`, `drills`, `express`, `reader`/`listening`, `writing`) as the source of
truth and only adds a single browser surface plus small HTTP wrappers.

NOTE (redesign): the page markup now lives in a sibling file
``studio_page.html`` instead of an inline ``PAGE`` string, so the UI can be
restyled/updated without touching this server. All routes and JSON shapes are
unchanged.
"""

from __future__ import annotations

import http.server
import json
import os
import re
import subprocess
import threading
import urllib.parse
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import (
    corpus,
    deepgram_tts,
    drill_scaffold,
    drills,
    express,
    grounding,
    listening,
    reading_packages,
    scheduler,
    store,
    translate,
    translate_history,
    writing,
)

PORT = int(os.environ.get("WORDFORGE_STUDIO_PORT", "8764"))

# The UI lives in studio_page.html next to this file. Edit that file to change
# the look; the server just serves it verbatim.
_PAGE_PATH = Path(__file__).with_name("studio_page.html")


def _page() -> str:
    try:
        return _PAGE_PATH.read_text(encoding="utf-8")
    except OSError:
        return (
            "<!doctype html><meta charset='utf-8'>"
            "<body style='font-family:system-ui;background:#0A0D12;color:#E8EEF5;"
            "padding:40px'><h1>studio_page.html not found</h1>"
            "<p>Expected next to <code>studio.py</code>. Re-copy it from the "
            "redesign bundle.</p></body>"
        )


def _json_response(handler: http.server.BaseHTTPRequestHandler, obj: Any, code: int = 200) -> None:
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _html_response(handler: http.server.BaseHTTPRequestHandler, html: str) -> None:
    body = html.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _request_json(handler: http.server.BaseHTTPRequestHandler) -> dict[str, Any]:
    n = int(handler.headers.get("Content-Length", "0"))
    if n <= 0:
        return {}
    return json.loads(handler.rfile.read(n) or b"{}")


def _audio_files() -> list[Path]:
    return listening.index_audio()


def _query_index(qs: dict[str, list[str]], files: list[Path]) -> int:
    i = int(qs.get("i", ["0"])[0])
    if not 0 <= i < len(files):
        raise IndexError(f"audio index {i} out of range")
    return i


def _word_summary(word: dict[str, Any]) -> dict[str, Any]:
    return {
        "headword": word.get("headword", ""),
        "pos": word.get("pos", ""),
        "core_sense": word.get("core_sense", ""),
        "image": word.get("image", ""),
        "register": word.get("register", ""),
        "frequency": word.get("frequency", ""),
    }


def _stats_payload() -> dict[str, Any]:
    words = store.load_words()
    weak = [
        {
            "headword": w.get("headword", ""),
            "lapses": int(w.get("lapses", 0)),
            "production_score": int(w.get("production_score", 0)),
            "due": str(w.get("due", ""))[:10],
        }
        for w in store.weak_list(words)
        if int(w.get("lapses", 0)) > 0
    ][:12]
    mistakes = [
        {
            "headword": r.get("headword", ""),
            "kind": r.get("kind", ""),
            "ts": str(r.get("ts", "")).replace("T", " ")[:16],
        }
        for r in store.recent_mistakes(12)
    ]
    return {"stats": store.stats(), "weak_words": weak, "recent_mistakes": mistakes}


def _next_drill_payload() -> dict[str, Any]:
    words = store.load_words()
    if not words:
        return {"empty": True, "message": "No words yet. Add one first."}

    due = store.get_due(words, datetime.now(timezone.utc))
    pool = due if due else store.weak_list(words)
    practice = not bool(due)
    for word in pool:
        drill, next_cursor = _pick_drill_readonly(word)
        if drill:
            return {
                "empty": False,
                "headword": word.get("headword", ""),
                "core_sense": word.get("core_sense", ""),
                "practice": practice,
                "next_cursor": next_cursor,
                "drill": drill,
            }
    return {"empty": True, "message": "The current words do not have drills yet."}


def _pick_drill_readonly(word: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
    pool: list[dict[str, Any]] = []
    for d in word.get("discrimination_drills", []) or []:
        pool.append({"kind": "discrimination", **d})
    for d in word.get("antonym_drills", []) or []:
        pool.append({"kind": "antonym", **d})
    if not pool:
        return None, int(word.get("drill_cursor", 0))
    cursor = int(word.get("drill_cursor", 0))
    return pool[cursor % len(pool)], cursor + 1


def _answer_drill(req: dict[str, Any]) -> dict[str, Any]:
    words = store.load_words()
    word = store.find_word(words, req.get("headword", ""))
    if not word:
        raise ValueError("word not found")

    drill = req.get("drill") or {}
    answer = str(req.get("answer", ""))
    correct, explanation = drills.check_answer(word, drill, answer)
    practice = bool(req.get("practice"))
    next_cursor = req.get("next_cursor")
    if isinstance(next_cursor, int) and next_cursor >= int(word.get("drill_cursor", 0)):
        word["drill_cursor"] = next_cursor

    if practice:
        grade = "good" if correct else "again"
        if correct:
            word["production_score"] = int(word.get("production_score", 0)) + 1
        else:
            word["due"] = store.soon_iso()
            word["lapses"] = int(word.get("lapses", 0)) + 1
            word["production_score"] = max(0, int(word.get("production_score", 0)) - 1)
    else:
        grade = drills.grade_for_correctness(correct)
        scheduler.review(word, grade)

    store.update_word(word)
    store.append_review(
        {
            "headword": word.get("headword", ""),
            "kind": drill.get("kind", ""),
            "grade": grade,
            "correct": correct,
            "practice": practice,
        }
    )
    return {
        "correct": correct,
        "grade": grade,
        "explanation": explanation,
        "answer": drill.get("answer", ""),
    }


def _prompts_payload() -> list[dict[str, str]]:
    prompts = writing.discover_prompts()
    return [
        {"id": pid, "preview": " ".join(text.split())[:78], "prompt": text}
        for pid, text in prompts.items()
    ]


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args: Any) -> None:
        pass

    def do_GET(self) -> None:
        try:
            u = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(u.query)

            if u.path in ("/", "/index.html"):
                _html_response(self, _page())
            elif u.path == "/api/stats":
                _json_response(self, _stats_payload())
            elif u.path == "/api/drill":
                _json_response(self, _next_drill_payload())
            elif u.path == "/api/listening/list":
                root = listening.listening_dir()
                files = _audio_files()
                _json_response(
                    self,
                    [{"i": i, "name": str(f.relative_to(root))} for i, f in enumerate(files)],
                )
            elif u.path == "/api/listening/transcript":
                files = _audio_files()
                _json_response(self, listening.transcribe(files[_query_index(qs, files)]))
            elif u.path == "/api/listening/audio":
                files = _audio_files()
                self._serve_audio(files[_query_index(qs, files)])
            elif u.path == "/api/listening/pdf":
                files = _audio_files()
                subprocess.run(["open", str(files[_query_index(qs, files)].parent.parent)], check=False)
                _json_response(self, {"ok": True})
            elif u.path == "/api/writing/prompts":
                _json_response(self, _prompts_payload())
            elif u.path == "/api/translate/corpus":
                _json_response(self, corpus.list_passages())
            elif u.path == "/api/translate/routes":
                _json_response(self, corpus.load_routes())
            elif u.path == "/api/translate/route/open_pdf":
                rid = qs.get("id", [""])[0]
                route = corpus.get_route(rid)
                if route is None:
                    _json_response(self, {"error": f"route not found: {rid}"}, 404)
                else:
                    local_pdf = str(route.get("local_pdf", ""))
                    source_url = str(route.get("source_url", ""))
                    target = local_pdf if local_pdf and Path(local_pdf).exists() else source_url
                    if not target:
                        raise ValueError("route has no local PDF or source URL")
                    subprocess.run(["open", target], check=False)
                    _json_response(self, {"ok": True, "opened": target})
            elif u.path == "/api/translate/corpus/get":
                pid = qs.get("id", [""])[0]
                passage = corpus.get_passage(pid)
                if passage is None:
                    _json_response(self, {"error": f"passage not found: {pid}"}, 404)
                else:
                    _json_response(self, passage)
            elif u.path == "/api/reading/packages":
                _json_response(self, reading_packages.list_packages())
            elif u.path == "/api/reading/package/get":
                pid = qs.get("id", [""])[0]
                package = reading_packages.get_package(pid)
                if package is None:
                    _json_response(self, {"error": f"reading package not found: {pid}"}, 404)
                else:
                    _json_response(self, package)
            elif u.path == "/api/tts/audio":
                name = qs.get("file", [""])[0]
                if not re.match(r"^[A-Za-z0-9_.-]+\.mp3$", name):
                    raise ValueError("invalid audio file")
                path = deepgram_tts.audio_dir() / name
                if not path.exists():
                    _json_response(self, {"error": f"audio not found: {name}"}, 404)
                else:
                    self._serve_audio(path)
            else:
                self.send_error(404)
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def do_POST(self) -> None:
        try:
            req = _request_json(self)
            if self.path == "/api/add":
                term = str(req.get("term", "")).strip()
                if not term:
                    raise ValueError("empty term")
                data = grounding.ground_word(term)
                created = store.add_word(data)
                word = store.find_word(store.load_words(), data["headword"]) or data
                _json_response(self, {"created": created, "word": _word_summary(word)})
            elif self.path == "/api/drill/answer":
                _json_response(self, _answer_drill(req))
            elif self.path == "/api/drill/scaffold":
                words = store.load_words()
                word = store.find_word(words, str(req.get("headword", "")))
                if not word:
                    raise ValueError("word not found")
                drill = req.get("drill") or {}
                if req.get("generate") is True:
                    _json_response(self, drill_scaffold.build(word, drill))
                else:
                    _json_response(self, drill_scaffold.cached_or_fallback(word, drill))
            elif self.path == "/api/expression/ladder":
                _json_response(self, express.ladder(str(req.get("thought", ""))))
            elif self.path == "/api/expression/grade":
                _json_response(
                    self,
                    express.grade_attempt(str(req.get("thought", "")), str(req.get("attempt", ""))),
                )
            elif self.path == "/api/writing/grade":
                prompts = writing.discover_prompts()
                prompt_id = str(req.get("prompt_id", ""))
                prompt = prompts.get(prompt_id, prompt_id or "(no prompt given)")
                essay = str(req.get("essay", "")).strip()
                if len(essay.split()) < 20:
                    raise ValueError("essay is too short")
                _json_response(self, writing.grade_essay(prompt, essay))
            elif self.path == "/api/translate/prep":
                _json_response(self, translate.prep_e2c(str(req.get("passage", ""))))
            elif self.path == "/api/translate/grade_e2c":
                source = str(req.get("passage", ""))
                answer = str(req.get("your_chinese", ""))
                result = translate.grade_e2c(source, answer)
                result["recorded"] = translate_history.record_attempt(
                    mode="e2c",
                    source=source,
                    answer=answer,
                    result=result,
                    passage_id=str(req.get("passage_id", "")),
                    support=req.get("support", ""),
                    sentence_index=req.get("sentence_index"),
                )
                _json_response(self, result)
            elif self.path == "/api/translate/scaffold":
                _json_response(self, translate.make_scaffold(str(req.get("passage", ""))))
            elif self.path == "/api/translate/grade_back":
                source = str(req.get("original", ""))
                answer = str(req.get("your_english", ""))
                result = translate.grade_back(source, answer)
                result["recorded"] = translate_history.record_attempt(
                    mode="back",
                    source=source,
                    answer=answer,
                    result=result,
                    passage_id=str(req.get("passage_id", "")),
                    support=req.get("support", ""),
                    sentence_index=req.get("sentence_index"),
                )
                _json_response(self, result)
            elif self.path == "/api/translate/grade_line":
                mode = str(req.get("mode", "back"))
                source = str(req.get("source", ""))
                answer = str(req.get("answer", ""))
                if mode == "e2c":
                    result = translate.grade_e2c(source, answer)
                else:
                    result = translate.grade_back(source, answer)
                result["recorded"] = translate_history.record_attempt(
                    mode=mode,
                    source=source,
                    answer=answer,
                    result=result,
                    passage_id=str(req.get("passage_id", "")),
                    support=req.get("support", ""),
                    sentence_index=req.get("sentence_index"),
                )
                _json_response(self, result)
            elif self.path == "/api/translate/ask":
                pid = str(req.get("passage_id", ""))
                question = str(req.get("question", "")).strip()
                if not question:
                    raise ValueError("empty question")
                passage = corpus.get_passage(pid)
                if passage is None:
                    raise ValueError(f"passage not found: {pid}")
                route = corpus.get_route(str(passage.get("route", passage.get("module", ""))))
                _json_response(self, translate.ask_about_passage(passage, question, route))
            elif self.path == "/api/reading/ask":
                pid = str(req.get("package_id", ""))
                question = str(req.get("question", "")).strip()
                segment_index = int(req.get("segment_index", 0))
                if not question:
                    raise ValueError("empty question")
                package = reading_packages.get_package(pid)
                if package is None:
                    raise ValueError(f"reading package not found: {pid}")
                segments = package.get("segments", []) or []
                segment = segments[segment_index] if 0 <= segment_index < len(segments) else {}
                passage = {
                    "title": package.get("title", ""),
                    "source": package.get("source", ""),
                    "why_selected": package.get("why_selected", ""),
                    "text_en": segment.get("text_en") or package.get("text_en", ""),
                }
                route = corpus.get_route(str(package.get("route", "")))
                _json_response(self, translate.ask_about_passage(passage, question, route))
            elif self.path == "/api/tts/speak":
                text = str(req.get("text", "")).strip()
                if not text:
                    raise ValueError("empty text")
                slug = str(req.get("slug", "wordforge-tts"))
                model = str(req.get("model", deepgram_tts.DEFAULT_MODEL))
                _json_response(
                    self,
                    {
                        "configured": deepgram_tts.configured(),
                        "outputs": deepgram_tts.speak_to_files(text, slug=slug, model=model),
                    },
                )
            else:
                self.send_error(404)
        except Exception as e:
            _json_response(self, {"error": str(e)}, 500)

    def _serve_audio(self, path: Path) -> None:
        data = path.read_bytes()
        total = len(data)
        rng = self.headers.get("Range")
        start, end = 0, total - 1
        if rng:
            m = re.match(r"bytes=(\d+)-(\d*)", rng)
            if m:
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else total - 1
        chunk = data[start:end + 1]
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Accept-Ranges", "bytes")
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end}/{total}")
        self.send_header("Content-Length", str(len(chunk)))
        self.end_headers()
        self.wfile.write(chunk)


def main() -> None:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"WordForge Studio at {url}  (Ctrl-C to stop)")
    if not os.environ.get("WORDFORGE_NO_OPEN"):
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
