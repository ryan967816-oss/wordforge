"""Expression-ladder trainer — a local web app for productive figurative range.

Your real gap (your own diagnosis): not vocabulary size, but reaching for the apt
image — "his eyes are like sapphires" vs only managing "like a lake". This tool
teaches the writer's move: concept -> a field of candidate images -> choose by
the *feeling* (connotation) you want.

    python -m wordforge.express      # serves http://localhost:8766 and opens it

You type a plain thought; Claude returns a ladder from plain -> precise ->
simile -> metaphor -> embedded-in-scene, each rung annotated with the image and
the connotation it carries. Then you write your own version and it grades the
aptness of your image, the connotation match, and the fluency.
"""

from __future__ import annotations

import http.server
import json
import os
import threading
import webbrowser
from typing import Any

from . import grounding

PORT = 8766

LADDER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "feeling_question": {"type": "string"},
        "note": {"type": "string"},
        "rungs": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "kind": {"type": "string",
                             "enum": ["plain", "precise adjective", "simile", "metaphor", "in a scene"]},
                    "rendering": {"type": "string"},
                    "image": {"type": "string"},
                    "connotation": {"type": "string"},
                    "register": {"type": "string"},
                },
                "required": ["kind", "rendering", "image", "connotation", "register"],
            },
        },
    },
    "required": ["feeling_question", "note", "rungs"],
}

GRADE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "score": {"type": "string", "enum": ["plain", "getting there", "vivid", "native-level"]},
        "image_apt": {"type": "boolean"},
        "connotation_match": {"type": "string"},
        "fluency": {"type": "string"},
        "feedback": {"type": "string"},
        "better_version": {"type": "string"},
    },
    "required": ["score", "image_apt", "connotation_match", "fluency", "feedback", "better_version"],
}

LADDER_SYSTEM = """You are a master of English prose style and imagery, teaching an advanced \
learner to reach for the apt image. Given a plain thought, build a LADDER of renderings from \
plain to literary, teaching the move: a concept maps to a field of candidate images, and you \
choose the image by the FEELING (connotation) you want to convey.

- feeling_question: one line naming the choice the writer faces, e.g. "Do you want her eyes to \
feel calm and deep, or brilliant and cold, or distant?"
- rungs (5–6): one each of kind = plain, precise adjective, simile, metaphor, in a scene. For \
EACH rung give: rendering (the actual English), image (the concrete picture it uses), connotation \
(the exact feeling it carries — this is the teaching), register (formal/neutral/literary).
- note: one or two sentences on the underlying move, so the learner can reuse it.

Show how different images encode different feelings (sapphire = brilliant, hard, precious, cold; \
lake = calm, deep, natural). American English. Precise and vivid, never purple or clichéd."""

GRADE_SYSTEM = """You are an exacting but encouraging English style coach. The learner saw a \
ladder of ways to express a thought and then wrote their OWN version. Judge it:
- score: plain / getting there / vivid / native-level.
- image_apt: does their image actually fit the thought?
- connotation_match: does the feeling their image carries match what they seem to want? (one phrase)
- fluency: does it read like natural, flowing English, not translated? (one phrase)
- feedback: 1–2 concrete sentences — what works, what to push.
- better_version: a sharper rendering that keeps THEIR image/idea where possible, so they see the next step.
American English. Be honest; this is how taste is built."""


def ladder(thought: str) -> dict[str, Any]:
    return grounding._structured_call(
        LADDER_SYSTEM, f"Plain thought:\n{thought}", LADDER_SCHEMA, max_tokens=2500)


def grade_attempt(thought: str, attempt: str) -> dict[str, Any]:
    user = f"The thought: {thought}\n\nThe learner's own version: {attempt}"
    return grounding._structured_call(GRADE_SYSTEM, user, GRADE_SCHEMA, max_tokens=1200)


PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>WordForge · Expression Ladder</title>
<style>
 :root{color-scheme:dark}
 body{margin:0;font:16px/1.6 -apple-system,system-ui,sans-serif;background:#15171c;color:#e7e9ee}
 .wrap{max-width:760px;margin:0 auto;padding:24px 18px 120px}
 h1{font-size:20px} .sub{color:#9aa0ac;margin-top:-8px}
 textarea{width:100%;box-sizing:border-box;background:#0f1115;color:#e7e9ee;border:1px solid #2a2e37;border-radius:10px;padding:12px;font:inherit}
 button{background:#2d6cdf;color:#fff;border:0;border-radius:8px;padding:9px 16px;cursor:pointer;margin-top:8px}
 .q{color:#f0c674;margin:18px 0 6px}
 .rung{border:1px solid #2a2e37;border-radius:10px;padding:12px 14px;margin:10px 0;background:#1a1d24}
 .kind{font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em}
 .render{font-size:18px;margin:4px 0}
 .meta{color:#aeb4c0;font-size:14px}
 .note{color:#9aa0ac;font-style:italic;margin-top:14px}
 .card{border:1px solid #26405f;background:#18222e;border-radius:10px;padding:12px 14px;margin-top:12px}
 #status{color:#9aa0ac}
</style></head><body><div class="wrap">
 <h1>Expression Ladder</h1>
 <p class="sub">Type a plain thought. See it climb from plain → literary, each rung labeled with the image and the feeling it carries. Then write your own and get it graded.</p>
 <textarea id="thought" rows="2" placeholder="e.g. his eyes are blue and striking"></textarea>
 <button onclick="showLadder()">Show ladder</button>
 <div id="status"></div>
 <div id="ladder"></div>
 <div id="attemptBox" style="display:none">
   <p class="q">Now you try — write your own version of the same thought:</p>
   <textarea id="attempt" rows="2"></textarea>
   <button onclick="grade()">Grade my version</button>
   <div id="grade"></div>
 </div>
</div>
<script>
let curThought="";
async function showLadder(){
  curThought=document.getElementById('thought').value.trim(); if(!curThought)return;
  document.getElementById('status').textContent='Thinking…'; document.getElementById('ladder').innerHTML='';
  const r=await fetch('/api/ladder',{method:'POST',body:JSON.stringify({thought:curThought})});
  const d=await r.json(); document.getElementById('status').textContent='';
  if(d.error){document.getElementById('status').textContent='error: '+d.error;return;}
  let h=`<div class="q">${esc(d.feeling_question)}</div>`;
  for(const g of d.rungs){ h+=`<div class="rung"><div class="kind">${esc(g.kind)} · ${esc(g.register)}</div>`+
    `<div class="render">${esc(g.rendering)}</div>`+
    `<div class="meta"><b>image:</b> ${esc(g.image)}<br><b>feeling:</b> ${esc(g.connotation)}</div></div>`; }
  h+=`<div class="note">${esc(d.note)}</div>`;
  document.getElementById('ladder').innerHTML=h;
  document.getElementById('attemptBox').style.display='block';
}
async function grade(){
  const a=document.getElementById('attempt').value.trim(); if(!a)return;
  document.getElementById('grade').innerHTML='<div class="card">Grading…</div>';
  const r=await fetch('/api/grade',{method:'POST',body:JSON.stringify({thought:curThought,attempt:a})});
  const d=await r.json();
  if(d.error){document.getElementById('grade').innerHTML='error: '+d.error;return;}
  document.getElementById('grade').innerHTML=`<div class="card"><b>${esc(d.score)}</b> · image apt: ${d.image_apt}`+
    `<br>connotation: ${esc(d.connotation_match)} · fluency: ${esc(d.fluency)}`+
    `<br>${esc(d.feedback)}<br><b>sharper:</b> ${esc(d.better_version)}</div>`;
}
function esc(t){return (t||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        req = json.loads(self.rfile.read(n) or b"{}")
        try:
            if self.path == "/api/ladder":
                self._json(ladder(req.get("thought", "")))
            elif self.path == "/api/grade":
                self._json(grade_attempt(req.get("thought", ""), req.get("attempt", "")))
            else:
                self.send_error(404)
        except Exception as e:
            self._json({"error": str(e)}, 500)


def main() -> None:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Expression Ladder at {url}  (Ctrl-C to stop)")
    if not os.environ.get("WORDFORGE_NO_OPEN"):
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
