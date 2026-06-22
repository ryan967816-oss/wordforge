"""WordForge Studio — one local web UI for the main training pillars.

    python -m wordforge.studio      # serves http://localhost:8764

This module is deliberately a thin shell. It keeps the existing engines
(`store`, `drills`, `express`, `reader`/`listening`, `writing`) as the source of
truth and only adds a single browser surface plus small HTTP wrappers.
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

from . import drills, express, grounding, listening, scheduler, store, writing

PORT = int(os.environ.get("WORDFORGE_STUDIO_PORT", "8764"))


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WordForge Studio</title>
<style>
  :root {
    color-scheme: dark;
    --bg: #121417;
    --panel: #191d23;
    --panel-2: #20252d;
    --line: #303641;
    --text: #eceff4;
    --muted: #9ca3af;
    --faint: #6f7784;
    --blue: #4f8cff;
    --green: #52b788;
    --amber: #e6b450;
    --red: #e06c75;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    min-height: 100vh;
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
  }
  button, input, select, textarea {
    font: inherit;
  }
  button {
    min-height: 36px;
    border: 0;
    border-radius: 8px;
    padding: 8px 12px;
    background: var(--blue);
    color: white;
    cursor: pointer;
  }
  button.secondary { background: #333a46; }
  button.ghost { background: transparent; border: 1px solid var(--line); color: var(--text); }
  button:disabled { cursor: wait; opacity: .65; }
  input, select, textarea {
    width: 100%;
    color: var(--text);
    background: #0e1115;
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 9px 10px;
    outline: none;
  }
  textarea { resize: vertical; }
  .app {
    min-height: 100vh;
    display: grid;
    grid-template-columns: 220px minmax(0, 1fr);
  }
  .side {
    position: sticky;
    top: 0;
    height: 100vh;
    padding: max(18px, env(safe-area-inset-top)) 14px 18px;
    border-right: 1px solid var(--line);
    background: #161a20;
  }
  .brand { font-size: 20px; font-weight: 700; margin: 2px 6px 18px; }
  .nav { display: grid; gap: 6px; }
  .nav button {
    width: 100%;
    justify-content: flex-start;
    text-align: left;
    background: transparent;
    color: var(--muted);
    border: 1px solid transparent;
  }
  .nav button.active {
    background: var(--panel-2);
    color: var(--text);
    border-color: var(--line);
  }
  .main {
    min-width: 0;
    padding: max(18px, env(safe-area-inset-top)) 24px 80px;
  }
  .view { display: none; max-width: 1060px; margin: 0 auto; }
  .view.active { display: block; }
  .bar {
    display: flex;
    gap: 10px;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }
  h1 { margin: 0; font-size: 22px; letter-spacing: 0; }
  h2 { margin: 0 0 10px; font-size: 15px; letter-spacing: 0; }
  .muted { color: var(--muted); }
  .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
  .metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
  .metric, .card, .rung, .seg, .feedback {
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--panel);
  }
  .metric { padding: 12px; min-height: 72px; }
  .metric b { display: block; font-size: 23px; line-height: 1.1; }
  .metric span { color: var(--muted); font-size: 12px; }
  .card { padding: 14px; margin-bottom: 14px; }
  .row { display: flex; gap: 10px; align-items: center; }
  .row > * { min-width: 0; }
  .row .grow { flex: 1; }
  .status { min-height: 22px; color: var(--muted); margin-top: 8px; }
  .status.err { color: var(--red); }
  .prompt { color: var(--amber); margin-bottom: 10px; }
  .options { display: grid; gap: 8px; margin: 10px 0; }
  .options button {
    background: #2a303a;
    text-align: left;
    border: 1px solid var(--line);
  }
  .options button:hover { border-color: var(--blue); }
  .rung { padding: 12px; margin: 10px 0; }
  .kind { color: var(--faint); font-size: 12px; text-transform: uppercase; }
  .render { margin: 4px 0; font-size: 17px; }
  .meta { color: var(--muted); font-size: 13px; }
  .feedback { padding: 12px; margin-top: 12px; }
  audio { width: 100%; margin-top: 10px; }
  #transcript { margin-top: 18px; }
  .seg {
    padding: 7px 10px;
    margin: 3px 0;
    color: #b9c0cc;
    cursor: pointer;
  }
  .seg:hover { background: #222834; }
  .seg.active { background: #24425f; color: white; }
  .time { color: var(--faint); font-variant-numeric: tabular-nums; margin-right: 10px; font-size: 13px; }
  .list { display: grid; gap: 6px; }
  .list div { padding: 8px 10px; border-bottom: 1px solid #252b35; }
  .pill {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 999px;
    background: #26313a;
    color: #cbd5e1;
    font-size: 12px;
  }
  @media (max-width: 840px) {
    .app { grid-template-columns: 1fr; }
    .side {
      position: sticky;
      z-index: 5;
      height: auto;
      padding: max(10px, env(safe-area-inset-top)) 10px 10px;
      border-right: 0;
      border-bottom: 1px solid var(--line);
    }
    .brand { margin-bottom: 8px; }
    .nav { grid-template-columns: repeat(5, minmax(0, 1fr)); }
    .nav button { text-align: center; justify-content: center; padding: 8px 6px; }
    .main { padding: 16px 12px 64px; }
    .grid, .metrics { grid-template-columns: 1fr; }
    .bar, .row { align-items: stretch; flex-direction: column; }
  }
</style>
</head>
<body>
<div class="app">
  <aside class="side">
    <div class="brand">WordForge</div>
    <nav class="nav" id="nav">
      <button class="active" data-view="vocab">Vocab</button>
      <button data-view="express">Expression</button>
      <button data-view="reader">Reader</button>
      <button data-view="writing">Writing</button>
      <button data-view="stats">Stats</button>
    </nav>
  </aside>
  <main class="main">
    <section id="vocab" class="view active">
      <div class="bar"><h1>Vocab Drill</h1><button class="ghost" onclick="refreshAll()">Refresh</button></div>
      <div class="metrics" id="vocabMetrics"></div>
      <div class="grid">
        <div class="card">
          <h2>Add a word</h2>
          <div class="row">
            <input class="grow" id="addTerm" placeholder="perfunctory">
            <button id="addBtn" onclick="addWord()">Add</button>
          </div>
          <div id="addStatus" class="status"></div>
        </div>
        <div class="card">
          <h2>Next drill</h2>
          <div id="drillBox" class="muted">Loading...</div>
        </div>
      </div>
    </section>

    <section id="express" class="view">
      <div class="bar"><h1>Expression Ladder</h1></div>
      <div class="card">
        <textarea id="thought" rows="2" placeholder="his eyes are blue and striking"></textarea>
        <button id="ladderBtn" onclick="showLadder()">Show ladder</button>
        <div id="ladderStatus" class="status"></div>
      </div>
      <div id="ladderOut"></div>
      <div id="attemptBox" class="card" style="display:none">
        <h2>Your version</h2>
        <textarea id="attempt" rows="2"></textarea>
        <button id="gradeExprBtn" onclick="gradeExpression()">Grade</button>
        <div id="exprGrade"></div>
      </div>
    </section>

    <section id="reader" class="view">
      <div class="bar"><h1>Listening Reader</h1></div>
      <div class="card">
        <div class="row">
          <select class="grow" id="audioFile"></select>
          <button class="secondary" onclick="openPdfFolder()">Open folder</button>
        </div>
        <audio id="audio" controls preload="none"></audio>
        <div id="readerStatus" class="status"></div>
      </div>
      <div id="transcript"></div>
    </section>

    <section id="writing" class="view">
      <div class="bar"><h1>Writing</h1></div>
      <div class="card">
        <select id="promptSelect"></select>
        <textarea id="essay" rows="14" placeholder="Write your essay here..."></textarea>
        <button id="gradeEssayBtn" onclick="gradeEssay()">Grade essay</button>
        <div id="writingStatus" class="status"></div>
      </div>
      <div id="writingOut"></div>
    </section>

    <section id="stats" class="view">
      <div class="bar"><h1>Stats</h1><button class="ghost" onclick="refreshStats()">Refresh</button></div>
      <div class="metrics" id="statsMetrics"></div>
      <div class="grid">
        <div class="card">
          <h2>Weak words</h2>
          <div class="list" id="weakWords"></div>
        </div>
        <div class="card">
          <h2>Recent mistakes</h2>
          <div class="list" id="mistakes"></div>
        </div>
      </div>
    </section>
  </main>
</div>

<script>
const $ = (id) => document.getElementById(id);
let currentThought = "";
let currentDrill = null;
let currentSegs = [];

function esc(t) {
  return String(t ?? "").replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
}
function setBusy(id, busy) {
  const el = $(id);
  if (el) el.disabled = busy;
}
function fmt(ms) {
  const s = Math.floor(ms / 1000);
  return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
}
async function api(path, opts = {}) {
  const r = await fetch(path, opts);
  const data = await r.json();
  if (!r.ok || data.error) throw new Error(data.error || ("HTTP " + r.status));
  return data;
}
function showView(name) {
  document.querySelectorAll(".view").forEach(v => v.classList.toggle("active", v.id === name));
  document.querySelectorAll(".nav button").forEach(b => b.classList.toggle("active", b.dataset.view === name));
  if (name === "stats") refreshStats();
}
$("nav").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-view]");
  if (b) showView(b.dataset.view);
});

async function refreshAll() {
  await Promise.allSettled([refreshStats(), loadDrill()]);
}
function metricHtml(s) {
  return [
    ["total_words", "words"],
    ["due_now", "due now"],
    ["reviewed_today", "reviewed today"],
    ["avg_production_score", "avg production"]
  ].map(([k, label]) => `<div class="metric"><b>${esc(s[k])}</b><span>${label}</span></div>`).join("");
}
async function refreshStats() {
  const d = await api("/api/stats");
  $("vocabMetrics").innerHTML = metricHtml(d.stats);
  $("statsMetrics").innerHTML = metricHtml(d.stats);
  $("weakWords").innerHTML = d.weak_words.length
    ? d.weak_words.map(w => `<div><b>${esc(w.headword)}</b> <span class="pill">${esc(w.lapses)} misses</span><br><span class="muted">score ${esc(w.production_score)} · due ${esc(w.due)}</span></div>`).join("")
    : `<div class="muted">No misses yet.</div>`;
  $("mistakes").innerHTML = d.recent_mistakes.length
    ? d.recent_mistakes.map(m => `<div><b>${esc(m.headword)}</b> <span class="pill">${esc(m.kind || "review")}</span><br><span class="muted">${esc(m.ts || "")}</span></div>`).join("")
    : `<div class="muted">No recent wrong answers.</div>`;
}
async function addWord() {
  const term = $("addTerm").value.trim();
  if (!term) return;
  $("addStatus").className = "status";
  $("addStatus").textContent = "Grounding via Claude...";
  setBusy("addBtn", true);
  try {
    const d = await api("/api/add", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({term})
    });
    $("addStatus").textContent = (d.created ? "Added " : "Updated ") + d.word.headword + ".";
    $("addTerm").value = "";
    await refreshAll();
  } catch (e) {
    $("addStatus").className = "status err";
    $("addStatus").textContent = e.message;
  } finally {
    setBusy("addBtn", false);
  }
}
async function loadDrill() {
  const box = $("drillBox");
  const d = await api("/api/drill");
  currentDrill = d.empty ? null : d;
  if (d.empty) {
    box.innerHTML = `<span class="muted">${esc(d.message)}</span>`;
    return;
  }
  const opts = (d.drill.options || []).map((o, i) =>
    `<button onclick="answerDrill('${i + 1}')">${i + 1}. ${esc(o)}</button>`).join("");
  box.innerHTML = `
    <div class="prompt">${esc(d.drill.prompt)}</div>
    ${opts ? `<div class="options">${opts}</div>` : `<input id="drillAnswer" placeholder="type the answer">`}
    ${opts ? "" : `<button onclick="answerDrill($('drillAnswer').value)">Submit</button>`}
    <div class="status">${esc(d.headword)} · ${esc(d.practice ? "extra practice" : "scheduled")}</div>
    <div id="drillResult"></div>`;
}
async function answerDrill(answer) {
  if (!currentDrill || !String(answer).trim()) return;
  const d = await api("/api/drill/answer", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({...currentDrill, answer})
  });
  $("drillResult").innerHTML = `<div class="feedback"><b>${d.correct ? "Correct" : "Try again"}</b><br>${esc(d.explanation || "")}</div>`;
  setTimeout(loadDrill, 700);
  refreshStats();
}

async function showLadder() {
  currentThought = $("thought").value.trim();
  if (!currentThought) return;
  $("ladderStatus").className = "status";
  $("ladderStatus").textContent = "Thinking...";
  $("ladderOut").innerHTML = "";
  setBusy("ladderBtn", true);
  try {
    const d = await api("/api/expression/ladder", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({thought: currentThought})
    });
    $("ladderStatus").textContent = "";
    $("ladderOut").innerHTML = `<div class="card"><div class="prompt">${esc(d.feeling_question)}</div>${
      d.rungs.map(r => `<div class="rung"><div class="kind">${esc(r.kind)} · ${esc(r.register)}</div><div class="render">${esc(r.rendering)}</div><div class="meta"><b>image:</b> ${esc(r.image)}<br><b>feeling:</b> ${esc(r.connotation)}</div></div>`).join("")
    }<div class="muted">${esc(d.note)}</div></div>`;
    $("attemptBox").style.display = "block";
  } catch (e) {
    $("ladderStatus").className = "status err";
    $("ladderStatus").textContent = e.message;
  } finally {
    setBusy("ladderBtn", false);
  }
}
async function gradeExpression() {
  const attempt = $("attempt").value.trim();
  if (!attempt) return;
  $("exprGrade").innerHTML = `<div class="feedback">Grading...</div>`;
  setBusy("gradeExprBtn", true);
  try {
    const d = await api("/api/expression/grade", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({thought: currentThought, attempt})
    });
    $("exprGrade").innerHTML = `<div class="feedback"><b>${esc(d.score)}</b> · image apt: ${esc(d.image_apt)}<br>connotation: ${esc(d.connotation_match)}<br>fluency: ${esc(d.fluency)}<br>${esc(d.feedback)}<br><b>sharper:</b> ${esc(d.better_version)}</div>`;
  } catch (e) {
    $("exprGrade").innerHTML = `<div class="feedback" style="color:var(--red)">${esc(e.message)}</div>`;
  } finally {
    setBusy("gradeExprBtn", false);
  }
}

async function loadAudioList() {
  const files = await api("/api/listening/list");
  if (!files.length) {
    $("audioFile").innerHTML = "";
    $("readerStatus").textContent = "No audio found. Set WORDFORGE_LISTENING_DIR or install the Edge audio library.";
    return;
  }
  $("audioFile").innerHTML = files.map(f => `<option value="${f.i}">${esc(f.name)}</option>`).join("");
  loadTranscript(0);
}
async function loadTranscript(i) {
  $("audio").src = "/api/listening/audio?i=" + i;
  $("transcript").innerHTML = "";
  $("readerStatus").className = "status";
  $("readerStatus").textContent = "Transcribing if needed...";
  try {
    currentSegs = await api("/api/listening/transcript?i=" + i);
    $("readerStatus").textContent = "";
    $("transcript").innerHTML = currentSegs.map((s, k) =>
      `<div class="seg" data-k="${k}" data-start="${s.start_ms / 1000}"><span class="time">${fmt(s.start_ms)}</span>${esc(s.text)}</div>`).join("");
    document.querySelectorAll(".seg").forEach(el => {
      el.onclick = () => {
        $("audio").currentTime = +el.dataset.start;
        $("audio").play();
      };
    });
  } catch (e) {
    $("readerStatus").className = "status err";
    $("readerStatus").textContent = e.message;
  }
}
$("audioFile").onchange = () => loadTranscript(+$("audioFile").value);
$("audio").ontimeupdate = () => {
  const t = $("audio").currentTime * 1000;
  let active = -1;
  for (let k = 0; k < currentSegs.length; k++) {
    if (t >= currentSegs[k].start_ms && t < currentSegs[k].end_ms) {
      active = k;
      break;
    }
  }
  document.querySelectorAll(".seg").forEach(el => {
    const on = +el.dataset.k === active;
    if (on && !el.classList.contains("active")) {
      el.classList.add("active");
      el.scrollIntoView({block: "center", behavior: "smooth"});
    }
    if (!on) el.classList.remove("active");
  });
};
async function openPdfFolder() {
  await api("/api/listening/pdf?i=" + $("audioFile").value);
}

async function loadPrompts() {
  const prompts = await api("/api/writing/prompts");
  $("promptSelect").innerHTML = prompts.map(p => `<option value="${esc(p.id)}">${esc(p.id)} - ${esc(p.preview)}</option>`).join("");
}
async function gradeEssay() {
  const promptId = $("promptSelect").value;
  const essay = $("essay").value.trim();
  if (essay.split(/\\s+/).filter(Boolean).length < 20) {
    $("writingStatus").className = "status err";
    $("writingStatus").textContent = "Write at least 20 words first.";
    return;
  }
  $("writingStatus").className = "status";
  $("writingStatus").textContent = "Grading via Claude...";
  $("writingOut").innerHTML = "";
  setBusy("gradeEssayBtn", true);
  try {
    const d = await api("/api/writing/grade", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({prompt_id: promptId, essay})
    });
    $("writingStatus").textContent = "";
    $("writingOut").innerHTML = `<div class="card"><h2>${esc(d.level_estimate)} · ${esc(d.overall_band)}/5</h2>
      <div class="list">${d.dimensions.map(x => `<div><b>${esc(x.name)}</b> <span class="pill">${esc(x.band)}/5</span><br><span class="muted">${esc(x.comment)}</span></div>`).join("")}</div>
      <h2 style="margin-top:14px">Top fixes</h2>
      <div class="list">${d.priority_fixes.map(x => `<div><b>${esc(x.issue)}</b><br><span class="muted">your text: ${esc(x.from_your_text)}</span><br>${esc(x.how_to_fix)}</div>`).join("")}</div>
      <h2 style="margin-top:14px">Model paragraph</h2><p>${esc(d.model_paragraph)}</p>
      <p class="muted">Words to study: ${esc((d.weak_words || []).join(", "))}</p></div>`;
  } catch (e) {
    $("writingStatus").className = "status err";
    $("writingStatus").textContent = e.message;
  } finally {
    setBusy("gradeEssayBtn", false);
  }
}

loadPrompts();
loadAudioList();
refreshAll();
</script>
</body>
</html>"""


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
                _html_response(self, PAGE)
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
