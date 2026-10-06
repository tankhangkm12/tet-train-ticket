#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Check which tools aizen-video-to-skill needs and print install hints.

Usage: uv run check_env.py [--json]
Exit code 0 if everything required for the common paths is present, 1 otherwise.
This script never installs anything; the agent must ask the user first.
"""
import importlib.util
import json
import platform
import shutil
import subprocess
import sys


def version(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return (out.stdout or out.stderr).splitlines()[0].strip()
    except Exception:
        return None


def install_hints():
    system = platform.system()
    ffmpeg = {
        "Linux": "sudo apt install ffmpeg   (or: dnf install ffmpeg / pacman -S ffmpeg)",
        "Darwin": "brew install ffmpeg",
        "Windows": "winget install Gyan.FFmpeg   (or: choco install ffmpeg)",
    }.get(system, "see https://ffmpeg.org/download.html")
    return {
        "ffmpeg": ffmpeg,
        "yt-dlp": "uv tool install yt-dlp",
        "faster-whisper": "uv run --with faster-whisper --script scripts/extract_content.py ...  (no install; uv caches it)",
    }


def main():
    as_json = "--json" in sys.argv
    ffmpeg_path = shutil.which("ffmpeg")
    ytdlp_path = shutil.which("yt-dlp")
    ytdlp_mod = importlib.util.find_spec("yt_dlp") is not None
    fw = importlib.util.find_spec("faster_whisper") is not None

    report = {
        "python": sys.version.split()[0],
        "os": platform.platform(),
        "ffmpeg": {"ok": bool(ffmpeg_path), "path": ffmpeg_path,
                   "version": version(["ffmpeg", "-version"]) if ffmpeg_path else None,
                   "needed_for": "audio extraction when no direct subtitles exist"},
        "yt-dlp": {"ok": bool(ytdlp_path or ytdlp_mod), "path": ytdlp_path,
                   "needed_for": "YouTube URLs only (subtitles + audio download)"},
        "faster-whisper": {"ok": fw,
                           "needed_for": "speech-to-text when no direct subtitles exist"},
        "install_hints": install_hints(),
    }
    missing = [k for k in ("ffmpeg", "yt-dlp", "faster-whisper") if not report[k]["ok"]]
    report["missing"] = missing

    if as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for k in ("ffmpeg", "yt-dlp", "faster-whisper"):
            print(f"[{'OK' if report[k]['ok'] else 'MISSING'}] {k}  - {report[k]['needed_for']}")
        if missing:
            print("\nMissing tools. Ask the user before installing. Suggested commands:")
            for k in missing:
                print(f"  {k}: {report['install_hints'][k]}")
            print("\nNote: yt-dlp is only needed for URLs; local files need just ffmpeg"
                  " (+ faster-whisper if the file has no subtitles).")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
