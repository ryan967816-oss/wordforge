"""Listening reader — a local web app (opens in your browser).

Your vision: open it, pick an Edge audio file, press play, and watch the
transcript scroll + highlight in sync; click any line to jump there; open the
source folder/PDF. Local whisper.cpp does the transcription (word/segment
timestamps, cached) — no cloud, no key, no per-minute cost.

    python -m wordforge.reader            # serves http://localhost:8765 and opens it

Deepgram (live streaming) is intentionally NOT used here — for pre-recorded
files local whisper is better. A live/streaming mode can be added later.
"""

from __future__ import annotations

import http.server
import json
import re
import subprocess
import threading
import urllib.parse
import webbrowser
from pathlib import Path

from . import listening

PORT = 8765

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>WordForge · Listening Reader</title>
<style>
  :root { color-scheme: dark; }
  body { margin:0; font:16px/1.6 -apple-system,system-ui,sans-serif; background:#15171c; color:#e7e9ee; }
  header { position:sticky; top:0; background:#1c1f26; padding:12px 18px; border-bottom:1px solid #2a2e37; display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
  select { flex:1; min-width:240px; background:#0f1115; color:#e7e9ee; border:1px solid #2a2e37; border-radius:8px; padding:8px; }
  button { background:#2d6cdf; color:#fff; border:0; border-radius:8px; padding:8px 14px; cursor:pointer; }
  button.secondary { background:#333a47; }
  audio { width:100%; margin-top:8px; }
  #transcript { max-width:760px; margin:24px auto 120px; padding:0 18px; }
  .seg { padding:6px 10px; margin:2px 0; border-radius:8px; cursor:pointer; color:#aeb4c0; transition:background .1s,color .1s; }
  .seg:hover { background:#222632; }
  .seg.active { background:#26405f; color:#fff; }
  .time { color:#6b7280; font-variant-numeric:tabular-nums; margin-right:10px; font-size:13px; }
  #status { color:#9aa0ac; padding:18px; text-align:center; }
</style></head><body>
<header>
  <select id="file"></select>
  <button id="pdf" class="secondary">Open unit folder (PDFs)</button>
  <div style="flex-basis:100%"></div>
  <audio id="audio" controls preload="none"></audio>
</header>
<div id="status">Pick a file above…</div>
<div id="transcript"></div>
<script>
const sel = document.getElementById('file');
const audio = document.getElementById('audio');
const tdiv = document.getElementById('transcript');
const status = document.getElementById('status');
let segs = [];

async function loadList(){
  const r = await fetch('/api/list'); const files = await r.json();
  sel.innerHTML = files.map(f=>`<option value="${f.i}">${f.name}</option>`).join('');
  if(files.length) load(0);
}
async function load(i){
  audio.src = '/api/audio?i='+i;
  tdiv.innerHTML=''; status.textContent='Transcribing (first time only; cached after)…';
  const r = await fetch('/api/transcript?i='+i);
  segs = await r.json();
  status.textContent='';
  tdiv.innerHTML = segs.map((s,k)=>
    `<div class="seg" data-k="${k}" data-start="${s.start_ms/1000}">`+
    `<span class="time">${fmt(s.start_ms)}</span>${escape(s.text)}</div>`).join('');
  [...tdiv.querySelectorAll('.seg')].forEach(el=>el.onclick=()=>{ audio.currentTime=+el.dataset.start; audio.play(); });
}
function fmt(ms){ const s=Math.floor(ms/1000); return (Math.floor(s/60))+':'+String(s%60).padStart(2,'0'); }
function escape(t){ return t.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
audio.ontimeupdate=()=>{
  const t=audio.currentTime*1000; let act=-1;
  for(let k=0;k<segs.length;k++){ if(t>=segs[k].start_ms && t<segs[k].end_ms){ act=k; break; } }
  tdiv.querySelectorAll('.seg').forEach(el=>{
    const on = +el.dataset.k===act;
    if(on && !el.classList.contains('active')){ el.classList.add('active'); el.scrollIntoView({block:'center',behavior:'smooth'}); }
    if(!on) el.classList.remove('active');
  });
};
sel.onchange=()=>load(+sel.value);
document.getElementById('pdf').onclick=()=>fetch('/api/pdf?i='+sel.value);
loadList();
</script></body></html>"""


def _files():
    return listening.index_audio()


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(u.query)
        files = _files()

        def idx():
            return int(qs.get("i", ["0"])[0])

        if u.path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif u.path == "/api/list":
            root = listening.listening_dir()
            self._json([{"i": i, "name": str(f.relative_to(root))} for i, f in enumerate(files)])
        elif u.path == "/api/transcript":
            try:
                segs = listening.transcribe(files[idx()])
                self._json(segs)
            except Exception as e:
                self._json({"error": str(e)}, 500)
        elif u.path == "/api/audio":
            self._serve_audio(files[idx()])
        elif u.path == "/api/pdf":
            # Open the audio file's unit folder in Finder so the user can grab the PDF.
            subprocess.run(["open", str(files[idx()].parent.parent)], check=False)
            self._json({"ok": True})
        else:
            self.send_error(404)

    def _serve_audio(self, path: Path):
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
    if not _files():
        print(f"No audio under {listening.listening_dir()}. Set WORDFORGE_LISTENING_DIR.")
        return
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Listening Reader at {url}  (Ctrl-C to stop)")
    import os
    if not os.environ.get("WORDFORGE_NO_OPEN"):
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
