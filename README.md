# MediaPull — Universal Media Downloader

Download best-quality video or audio from YouTube, TikTok, Instagram,
Twitter/X, Facebook, Reddit, Vimeo, SoundCloud, and 1000+ sites.
No watermarks. Files land in your OS default Downloads folder.

---

## Quick-start (3 steps)

### Step 1 — Install Python 3.9+

| OS | Link |
|---|---|
| Windows | https://www.python.org/downloads/ ← tick **Add to PATH** |
| macOS | https://www.python.org/downloads/ or `brew install python` |
| Ubuntu/Debian | `sudo apt install python3 python3-pip` |

Verify: open a terminal and run `python --version` (or `python3 --version`).

---

### Step 2 — Install FFmpeg  *(required for best quality)*

FFmpeg merges the separate high-quality video + audio streams that
YouTube and other platforms provide.

**Windows**
1. Download the *essentials* build from https://www.gyan.dev/ffmpeg/builds/
2. Extract the zip anywhere (e.g. `C:\ffmpeg`)
3. Add `C:\ffmpeg\bin` to your system PATH:
   - Search → "Edit environment variables" → Path → New → paste path

**macOS**
```
brew install ffmpeg
```

**Ubuntu / Debian**
```
sudo apt update && sudo apt install ffmpeg
```

**Verify**
```
ffmpeg -version
```

---

### Step 3 — Run MediaPull

**Windows** — double-click `run_windows.bat`

**macOS / Linux**
```bash
chmod +x run_mac_linux.sh
./run_mac_linux.sh
```

**Manual (any OS)**
```bash
pip install yt-dlp        # or: pip3 install yt-dlp
python app.py             # or: python3 app.py
```

A browser window will open automatically at http://127.0.0.1:8765

---

## How to use

1. Copy any video/audio link from YouTube, TikTok, Instagram, Twitter/X, etc.
2. Paste it into the URL box in MediaPull.
3. Choose mode:
   - **Best Quality** — downloads best video + best audio, merges into MP4
   - **Audio Only (MP3)** — extracts highest-quality audio as 320 kbps MP3
4. Click **Download**.
5. Watch the progress bar. When it says "Done ✓", find the file in your
   **Downloads** folder (or whatever your OS default is).

---

## Supported sites (sample)

YouTube · YouTube Music · Twitter / X · TikTok · Instagram (public posts)
Facebook (public videos) · Reddit · Vimeo · SoundCloud · Twitch (VODs)
Dailymotion · Bilibili · NicoNico · Rumble · Odysee · and 1000+ more

Full list: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md

---

## Notes & tips

- **Instagram / TikTok private accounts** — only your own content can be
  downloaded; you may need to pass cookies (`--cookies-from-browser` in yt-dlp).
- **Age-restricted YouTube** — log in via cookies for best results.
- **Multiple downloads** — you can queue several links at once; they run in parallel.
- **File location** — files go to your OS Downloads directory automatically.
  On Linux, `$XDG_DOWNLOAD_DIR` is respected.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `yt-dlp` not found | Run `pip install yt-dlp` |
| Merge fails / video has no audio | Install FFmpeg (Step 2) |
| Instagram/TikTok error | Use a public URL; private content is unsupported |
| YouTube "Sign in required" | Pass cookies: edit `build_ytdlp_cmd` to add `--cookies-from-browser chrome` |
| Port 8765 busy | Change `PORT = 8765` in `app.py` to any free port |

---

## Update yt-dlp (run periodically)

Sites change their formats often — keep yt-dlp current:

```bash
pip install -U yt-dlp
```

---

## Project structure

```
mediapull/
├── app.py              ← main application (run this)
├── requirements.txt    ← Python dependencies
├── run_windows.bat     ← Windows one-click launcher
├── run_mac_linux.sh    ← macOS / Linux one-click launcher
└── README.md           ← this file
```

---

*MediaPull is a personal tool. Respect copyright and the terms of service
of each platform. Only download content you have the right to use.*
