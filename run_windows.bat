@echo off
title MediaPull - Media Downloader

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install from https://python.org
    pause
    exit /b 1
)

echo Installing / updating yt-dlp...
pip install -q --upgrade yt-dlp

echo Checking FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: FFmpeg not found. Best-quality merging may not work.
    echo Download from: https://ffmpeg.org/download.html
    echo Then add ffmpeg\bin to your PATH.
    echo.
    pause
)

echo Starting MediaPull...
python app.py
pause
