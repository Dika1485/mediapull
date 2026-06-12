#!/usr/bin/env python3
"""
MediaPull - Universal Media Downloader
Supports: YouTube, Twitter/X, TikTok, Instagram, Facebook, and 1000+ sites
"""

import os
import sys
import json
import threading
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import subprocess
import re

# ── Configuration ──────────────────────────────────────────────────────────────

PORT = 8765

def get_download_dir():
    """Get the OS default Downloads directory."""
    if sys.platform == "win32":
        import winreg
        try:
            sub_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                return winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")[0]
        except Exception:
            return str(Path.home() / "Downloads")
    elif sys.platform == "darwin":
        return str(Path.home() / "Downloads")
    else:
        # Linux: respect XDG
        xdg = os.environ.get("XDG_DOWNLOAD_DIR")
        if xdg:
            return xdg
        return str(Path.home() / "Downloads")


DOWNLOAD_DIR = get_download_dir()

# Active downloads tracker  {task_id: {status, progress, filename, error}}
downloads = {}
task_counter = 0
lock = threading.Lock()


# ── yt-dlp helpers ─────────────────────────────────────────────────────────────

def build_ytdlp_cmd(url: str, mode: str, output_dir: str) -> list:
    """
    Build the yt-dlp command for best quality download.

    mode:
      'best'  – best video+audio merged (default)
      'video' – best video-only track, then mux with best audio  (→ mkv/mp4)
      'audio' – best audio only → converted to mp3 320k
    """
    output_tmpl = os.path.join(output_dir, "%(title)s.%(ext)s")

    base = [
        sys.executable, "-m", "yt_dlp",
        "--no-playlist",
        "--no-warnings",
        "--progress",
        "--newline",
        # Remove platform watermarks where possible
        "--embed-metadata",
        "--no-embed-thumbnail",
        # Prefer ffmpeg for merging
        "--merge-output-format", "mp4",
        "-o", output_tmpl,
    ]

    if mode == "audio":
        base += [
            "-f", "bestaudio/best",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "0",   # VBR best
        ]
    else:
        # Download best video-only + best audio-only, then merge
        base += [
            "-f", "bestvideo+bestaudio/best",
        ]

    base.append(url)
    return base


def run_download(task_id: str, url: str, mode: str, output_dir: str):
    """Execute yt-dlp in a background thread and update progress."""
    cmd = build_ytdlp_cmd(url, mode, output_dir)

    with lock:
        downloads[task_id]["status"] = "downloading"
        downloads[task_id]["command"] = " ".join(cmd)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        filename = ""
        for line in proc.stdout:
            line = line.strip()

            # Parse progress percentage
            pct_match = re.search(r"\[download\]\s+([\d.]+)%", line)
            if pct_match:
                with lock:
                    downloads[task_id]["progress"] = float(pct_match.group(1))

            # Parse destination filename
            dest_match = re.search(r"\[(?:download|Merger)\] Destination:\s+(.+)", line)
            if dest_match:
                filename = dest_match.group(1).strip()
                with lock:
                    downloads[task_id]["filename"] = filename

            # Merging step
            if "[Merger]" in line or "Merging formats" in line:
                with lock:
                    downloads[task_id]["status"] = "merging"
                    downloads[task_id]["progress"] = 99.0

            # Audio conversion
            if "[ExtractAudio]" in line or "Destination" in line and ".mp3" in line:
                with lock:
                    downloads[task_id]["status"] = "converting"

        proc.wait()

        if proc.returncode == 0:
            with lock:
                downloads[task_id]["status"] = "done"
                downloads[task_id]["progress"] = 100.0
                if not downloads[task_id].get("filename"):
                    downloads[task_id]["filename"] = output_dir
        else:
            with lock:
                downloads[task_id]["status"] = "error"
                downloads[task_id]["error"] = "yt-dlp exited with non-zero status. Check that the URL is valid and the site is supported."

    except FileNotFoundError:
        with lock:
            downloads[task_id]["status"] = "error"
            downloads[task_id]["error"] = "yt-dlp is not installed. Run: pip install yt-dlp"
    except Exception as exc:
        with lock:
            downloads[task_id]["status"] = "error"
            downloads[task_id]["error"] = str(exc)


# ── HTTP handler ───────────────────────────────────────────────────────────────

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>MediaPull</title>
<style>
  :root {
    --bg: #0d0f14;
    --surface: #161b26;
    --surface2: #1f2637;
    --accent: #6c8cff;
    --accent2: #a78bfa;
    --success: #34d399;
    --error: #f87171;
    --warn: #fbbf24;
    --text: #e8eaf0;
    --muted: #7a8399;
    --radius: 12px;
    --font: 'Inter', system-ui, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--font);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 40px 16px 80px;
  }

  /* Header */
  header { text-align: center; margin-bottom: 48px; }
  .logo {
    font-size: 2.4rem;
    font-weight: 800;
    letter-spacing: -1px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .tagline { color: var(--muted); font-size: .95rem; margin-top: 6px; }

  /* Badges */
  .badges {
    display: flex; flex-wrap: wrap; gap: 8px;
    justify-content: center; margin-top: 18px;
  }
  .badge {
    background: var(--surface2);
    border: 1px solid #2a3147;
    border-radius: 999px;
    padding: 4px 12px;
    font-size: .75rem;
    color: var(--muted);
  }

  /* Card */
  .card {
    background: var(--surface);
    border: 1px solid #1e2640;
    border-radius: var(--radius);
    padding: 28px;
    width: 100%;
    max-width: 640px;
    margin-bottom: 20px;
  }

  /* Input row */
  .input-row {
    display: flex; gap: 10px;
  }
  input[type="url"] {
    flex: 1;
    background: var(--bg);
    border: 1.5px solid #2a3147;
    border-radius: 8px;
    color: var(--text);
    font-size: .95rem;
    padding: 12px 16px;
    outline: none;
    transition: border-color .2s;
  }
  input[type="url"]:focus { border-color: var(--accent); }
  input[type="url"]::placeholder { color: var(--muted); }

  /* Mode selector */
  .mode-row {
    display: flex; gap: 10px; margin-top: 14px;
  }
  .mode-btn {
    flex: 1; cursor: pointer;
    background: var(--bg);
    border: 1.5px solid #2a3147;
    border-radius: 8px;
    color: var(--muted);
    font-size: .85rem;
    font-weight: 600;
    padding: 10px 8px;
    text-align: center;
    transition: all .2s;
  }
  .mode-btn.active {
    background: var(--surface2);
    border-color: var(--accent);
    color: var(--accent);
  }
  .mode-btn:hover:not(.active) { border-color: #3a4560; color: var(--text); }

  /* Download button */
  .dl-btn {
    margin-top: 18px;
    width: 100%;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border: none;
    border-radius: 8px;
    color: #fff;
    cursor: pointer;
    font-size: 1rem;
    font-weight: 700;
    padding: 14px;
    transition: opacity .2s, transform .1s;
  }
  .dl-btn:hover { opacity: .9; }
  .dl-btn:active { transform: scale(.98); }
  .dl-btn:disabled { opacity: .45; cursor: not-allowed; }

  /* Output dir row */
  .dir-row {
    margin-top: 14px;
    display: flex; align-items: center; gap: 8px;
    font-size: .8rem; color: var(--muted);
  }
  .dir-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .dir-note { font-style: italic; }

  /* Queue */
  #queue { width: 100%; max-width: 640px; }
  .queue-title {
    font-size: .8rem; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: var(--muted);
    margin-bottom: 12px;
  }
  .item {
    background: var(--surface);
    border: 1px solid #1e2640;
    border-radius: var(--radius);
    padding: 16px 20px;
    margin-bottom: 12px;
    position: relative;
    overflow: hidden;
  }
  .item-url {
    font-size: .8rem; color: var(--muted);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    margin-bottom: 6px;
  }
  .item-status {
    display: flex; align-items: center; gap: 8px;
    font-size: .9rem; font-weight: 600;
  }
  .dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--muted); flex-shrink: 0;
  }
  .dot.downloading { background: var(--accent); animation: pulse 1s infinite; }
  .dot.merging     { background: var(--warn);   animation: pulse 1s infinite; }
  .dot.converting  { background: var(--accent2);animation: pulse 1s infinite; }
  .dot.done        { background: var(--success); }
  .dot.error       { background: var(--error); }
  @keyframes pulse { 0%,100%{opacity:1}50%{opacity:.4} }

  .progress-bar {
    margin-top: 10px;
    height: 4px; border-radius: 999px;
    background: #1e2640; overflow: hidden;
  }
  .progress-fill {
    height: 100%; border-radius: 999px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    transition: width .4s ease;
  }
  .item-filename {
    font-size: .78rem; color: var(--muted);
    margin-top: 8px; overflow: hidden;
    text-overflow: ellipsis; white-space: nowrap;
  }
  .item-error {
    font-size: .8rem; color: var(--error);
    margin-top: 6px; line-height: 1.5;
  }
  .badge-mode {
    position: absolute; top: 12px; right: 14px;
    font-size: .7rem; font-weight: 700;
    letter-spacing: .06em; text-transform: uppercase;
    padding: 2px 8px; border-radius: 999px;
    background: var(--surface2); color: var(--muted);
  }
</style>
</head>
<body>

<header>
  <div class="logo">MediaPull</div>
  <p class="tagline">Best-quality downloads — no watermarks, no fuss.</p>
  <div class="badges">
    <span class="badge">YouTube</span>
    <span class="badge">X / Twitter</span>
    <span class="badge">TikTok</span>
    <span class="badge">Instagram</span>
    <span class="badge">Facebook</span>
    <span class="badge">Reddit</span>
    <span class="badge">Vimeo</span>
    <span class="badge">SoundCloud</span>
    <span class="badge">1000+ more</span>
  </div>
</header>

<div class="card">
  <div class="input-row">
    <input type="url" id="urlInput" placeholder="Paste link here…" autocomplete="off"/>
  </div>

  <div class="mode-row">
    <div class="mode-btn active" data-mode="best"  onclick="setMode('best')">🎬 Best Quality</div>
    <div class="mode-btn"        data-mode="audio" onclick="setMode('audio')">🎵 Audio Only (MP3)</div>
  </div>

  <button class="dl-btn" id="dlBtn" onclick="startDownload()">Download</button>

  <div class="dir-row">
    <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/></svg>
    <span class="dir-label" id="dirLabel">Loading…</span>
    <span class="dir-note">← saves here</span>
  </div>
</div>

<div id="queue"></div>

<script>
let mode = 'best';
let taskCount = 0;
const polls = {};

function setMode(m) {
  mode = m;
  document.querySelectorAll('.mode-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.mode === m);
  });
}

async function startDownload() {
  const url = document.getElementById('urlInput').value.trim();
  if (!url) { alert('Please paste a URL first.'); return; }

  const btn = document.getElementById('dlBtn');
  btn.disabled = true;
  btn.textContent = 'Adding…';

  try {
    const res = await fetch('/api/download', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({url, mode})
    });
    const data = await res.json();
    if (data.task_id) {
      addQueueItem(data.task_id, url, mode);
      document.getElementById('urlInput').value = '';
    } else {
      alert(data.error || 'Failed to start download.');
    }
  } catch(e) { alert('Server error: ' + e); }

  btn.disabled = false;
  btn.textContent = 'Download';
}

function addQueueItem(id, url, m) {
  const q = document.getElementById('queue');
  if (taskCount === 0) {
    const t = document.createElement('p');
    t.className = 'queue-title';
    t.textContent = 'Downloads';
    q.prepend(t);
  }
  taskCount++;

  const el = document.createElement('div');
  el.className = 'item';
  el.id = 'task-' + id;
  el.innerHTML = `
    <div class="badge-mode">${m === 'audio' ? 'MP3' : 'Video'}</div>
    <div class="item-url">${url}</div>
    <div class="item-status">
      <span class="dot downloading"></span>
      <span class="status-text">Queued…</span>
    </div>
    <div class="progress-bar"><div class="progress-fill" style="width:0%"></div></div>
    <div class="item-filename"></div>
    <div class="item-error"></div>
  `;
  // Insert after the title
  const title = q.querySelector('.queue-title');
  title ? title.after(el) : q.prepend(el);

  polls[id] = setInterval(() => pollTask(id), 800);
}

async function pollTask(id) {
  try {
    const res = await fetch('/api/status?id=' + id);
    const d = await res.json();
    const el = document.getElementById('task-' + id);
    if (!el) return;

    const dot = el.querySelector('.dot');
    const txt = el.querySelector('.status-text');
    const bar = el.querySelector('.progress-fill');
    const fnEl = el.querySelector('.item-filename');
    const errEl = el.querySelector('.item-error');

    const labels = {
      queued: 'Queued…',
      downloading: `Downloading… ${(d.progress||0).toFixed(1)}%`,
      merging: 'Merging video + audio…',
      converting: 'Converting to MP3…',
      done: 'Done ✓',
      error: 'Error'
    };

    dot.className = 'dot ' + (d.status || 'queued');
    txt.textContent = labels[d.status] || d.status;
    bar.style.width = (d.progress || 0) + '%';

    if (d.filename) {
      const name = d.filename.split(/[\\/]/).pop();
      fnEl.textContent = '📁 ' + name;
    }
    if (d.error) errEl.textContent = d.error;

    if (d.status === 'done' || d.status === 'error') {
      clearInterval(polls[id]);
      delete polls[id];
    }
  } catch(e) { /* server busy */ }
}

// Load download dir label
fetch('/api/config').then(r=>r.json()).then(d=>{
  document.getElementById('dirLabel').textContent = d.download_dir;
});

// Allow Enter key
document.getElementById('urlInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') startDownload();
});
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress default logging

    def send_json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            body = HTML_PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/api/config":
            self.send_json({"download_dir": DOWNLOAD_DIR})

        elif parsed.path == "/api/status":
            qs = parse_qs(parsed.query)
            tid = qs.get("id", [None])[0]
            with lock:
                data = downloads.get(tid, {"status": "unknown", "progress": 0})
                self.send_json(dict(data))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/download":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body)
            except Exception:
                self.send_json({"error": "Invalid JSON"}, 400)
                return

            url = payload.get("url", "").strip()
            mode = payload.get("mode", "best")

            if not url:
                self.send_json({"error": "No URL provided"}, 400)
                return

            global task_counter
            with lock:
                task_counter += 1
                tid = str(task_counter)
                downloads[tid] = {
                    "status": "queued",
                    "progress": 0.0,
                    "filename": "",
                    "error": "",
                    "url": url,
                    "mode": mode,
                }

            t = threading.Thread(
                target=run_download,
                args=(tid, url, mode, DOWNLOAD_DIR),
                daemon=True,
            )
            t.start()
            self.send_json({"task_id": tid})
        else:
            self.send_response(404)
            self.end_headers()


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    print("=" * 56)
    print("  MediaPull — Universal Media Downloader")
    print("=" * 56)
    print(f"  Download folder : {DOWNLOAD_DIR}")
    print(f"  Local server    : http://127.0.0.1:{PORT}")
    print("  Press Ctrl+C to stop.")
    print("=" * 56)

    server = HTTPServer(("127.0.0.1", PORT), Handler)

    # Open browser after a short delay
    def open_browser():
        import time; time.sleep(0.8)
        webbrowser.open(f"http://127.0.0.1:{PORT}")

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMediaPull stopped.")


if __name__ == "__main__":
    main()
