#!/usr/bin/env bash
set -e

echo "========================================"
echo "  MediaPull - Media Downloader"
echo "========================================"

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.9+ from https://python.org"
    exit 1
fi

echo "Installing / updating dependencies..."
pip3 install -q --upgrade yt-dlp curl_cffi

if ! command -v ffmpeg &>/dev/null; then
    echo ""
    echo "WARNING: ffmpeg not found."
    echo "  macOS  : brew install ffmpeg"
    echo "  Ubuntu : sudo apt install ffmpeg"
    echo ""
fi

echo "Starting MediaPull..."
python3 app.py
