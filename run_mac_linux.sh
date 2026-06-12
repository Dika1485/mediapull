#!/usr/bin/env bash
set -e

echo "========================================"
echo "  MediaPull - Media Downloader"
echo "========================================"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.9+ from https://python.org"
    exit 1
fi

# Install / upgrade yt-dlp
echo "Installing / updating yt-dlp..."
pip3 install -q --upgrade yt-dlp

# FFmpeg check
if ! command -v ffmpeg &>/dev/null; then
    echo ""
    echo "WARNING: ffmpeg not found. Best-quality merging may not work."
    echo "  macOS  : brew install ffmpeg"
    echo "  Ubuntu : sudo apt install ffmpeg"
    echo "  Fedora : sudo dnf install ffmpeg"
    echo ""
fi

echo "Starting MediaPull..."
python3 app.py
