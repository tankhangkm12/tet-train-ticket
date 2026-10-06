#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Extract the spoken content of a video into text.

Order of attempts:
  1. Direct text: human-written subtitles (YouTube manual captions, sidecar
     .srt/.vtt next to a local file, or an embedded subtitle stream).
     Auto-generated YouTube captions are used only with --allow-auto-subs.
  2. ffmpeg -> mono 16 kHz mp3 -> faster-whisper transcription.

Outputs (in --out): transcript.txt, transcript.md, transcript.json,
manifest.json, and audio.mp3 when --keep-audio is given.

The script never installs software and never works around access
restrictions: on failure it exits non-zero with a clear message.
"""
import argparse
import datetime as dt
import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

URL_RE = re.compile(r"^https?://", re.I)
TS_RE = re.compile(r"(\d+):(\d+):(\d+)[.,](\d+)\s*-->\s*(\d+):(\d+):(\d+)[.,](\d+)")


def die(msg, code=2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def need(tool):
    if not shutil.which(tool):
        die(f"'{tool}' not found. Run scripts/check_env.py and ask the user to approve installation.")


def ytdlp_cmd():
    if shutil.which("yt-dlp"):
        return ["yt-dlp"]
    if importlib.util.find_spec("yt_dlp"):
        return [sys.executable, "-m", "yt_dlp"]
    die("yt-dlp not found (needed for URLs). Run scripts/check_env.py and ask the user to approve installation, "
        "or ask the user for a downloaded video file instead.")


# ---------- subtitle parsing ----------
def _sec(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")[:3]) / 1000


def parse_subtitle(path):
    """Parse .vtt/.srt into [{start,end,text}], de-duplicating rolling captions."""
    segs = []
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    i = 0
    while i < len(lines):
        m = TS_RE.search(lines[i])
        if not m:
            i += 1
            continue
        start = _sec(*m.group(1, 2, 3, 4))
        end = _sec(*m.group(5, 6, 7, 8))
        i += 1
        buf = []
        while i < len(lines) and lines[i].strip():
            t = re.sub(r"<[^>]+>", "", lines[i]).strip()
            if t:
                buf.append(t)
            i += 1
        text = " ".join(buf).strip()
        if text and (not segs or segs[-1]["text"] != text):
            segs.append({"start": start, "end": end, "text": text})
    return segs


# ---------- direct text ----------
def subs_from_url(url, work, lang, allow_auto):
    base = ytdlp_cmd()
    langs = lang if lang else "all,-live_chat"
    # human-written subtitles first
    r = run(base + ["--skip-download", "--write-subs", "--sub-langs", langs, "--sub-format", "vtt/srt/best",
                    "--convert-subs", "vtt", "-o", os.path.join(work, "sub.%(ext)s"), url])
    files = sorted(glob.glob(os.path.join(work, "sub*.vtt")))
    if files:
        return files[0], "manual-subtitles", r.stderr
    if allow_auto:
        r = run(base + ["--skip-download", "--write-auto-subs", "--sub-langs", lang or "en.*,vi.*,.*-orig",
                        "--sub-format", "vtt", "-o", os.path.join(work, "auto.%(ext)s"), url])
        files = sorted(glob.glob(os.path.join(work, "auto*.vtt")))
        if files:
            return files[0], "auto-captions", r.stderr
    return None, None, r.stderr


def subs_from_file(path, work):
    stem = os.path.splitext(path)[0]
    for ext in (".srt", ".vtt"):
        for cand in glob.glob(glob.escape(stem) + "*" + ext):
            return cand, "sidecar-subtitles"
    if shutil.which("ffmpeg"):
        out = os.path.join(work, "embedded.srt")
        r = run(["ffmpeg", "-y", "-v", "error", "-i", path, "-map", "0:s:0", out])
        if r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0:
            return out, "embedded-subtitles"
    return None, None


# ---------- audio ----------
def download_audio(url, work):
    base = ytdlp_cmd()
    r = run(base + ["-f", "bestaudio/best", "-x", "--audio-format", "mp3", "--audio-quality", "0",
                    "-o", os.path.join(work, "dl.%(ext)s"), url])
    files = glob.glob(os.path.join(work, "dl.*"))
    if r.returncode != 0 or not files:
        die("Could not download the audio. The video may be private, age/geo-restricted, or the host blocked the "
            "request. Report this to the user and ask for a downloaded file. yt-dlp said:\n" + r.stderr[-800:], 3)
    return files[0]


def to_mp3(src, dst):
    need("ffmpeg")
    r = run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000",
             "-codec:a", "libmp3lame", "-q:a", "4", dst])
    if r.returncode != 0 or not os.path.exists(dst):
        die("ffmpeg could not extract audio (does the file contain an audio track?):\n" + r.stderr[-800:], 4)


def duration(path):
    if not shutil.which("ffprobe"):
        return None
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


# ---------- ASR ----------
def transcribe(mp3, model_name, lang, device):
    if importlib.util.find_spec("faster_whisper") is None:
        die("faster-whisper not installed. Re-run with `uv run --with faster-whisper --script scripts/extract_content.py ...` "
            "after the user approves the download.")
    from faster_whisper import WhisperModel

    compute = "float16" if device == "cuda" else "int8"
    try:
        model = WhisperModel(model_name, device=device, compute_type=compute)
    except Exception as e:  # model download blocked, no GPU, etc.
        die(f"Could not load Whisper model '{model_name}' on {device}: {e}\n"
            "Ask the user: use a smaller model (--model medium), another device, or provide a transcript.", 5)
    it, info = model.transcribe(mp3, language=lang, vad_filter=True, beam_size=5,
                                condition_on_previous_text=False)
    segs = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in it if s.text.strip()]
    return segs, info.language, getattr(info, "language_probability", None)


# ---------- output ----------
def fmt(t):
    t = int(t)
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def write_outputs(out, segs, manifest):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "transcript.txt"), "w", encoding="utf-8") as f:
        f.write(" ".join(s["text"] for s in segs) + "\n")
    with open(os.path.join(out, "transcript.md"), "w", encoding="utf-8") as f:
        f.write(f"# Transcript\n\nSource: {manifest['source']}\nMethod: {manifest['method']}\n\n")
        for s in segs:
            f.write(f"[{fmt(s['start'])}] {s['text']}\n")
    with open(os.path.join(out, "transcript.json"), "w", encoding="utf-8") as f:
        json.dump(segs, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="public YouTube URL or path to a local video/audio file")
    ap.add_argument("--out", default="./out/work", help="output folder")
    ap.add_argument("--lang", help="language code (e.g. vi, en). Default: auto-detect")
    ap.add_argument("--model", default="large-v3", help="faster-whisper model (default large-v3, most accurate)")
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    ap.add_argument("--allow-auto-subs", action="store_true", help="accept auto-generated YouTube captions")
    ap.add_argument("--force-asr", action="store_true", help="skip direct subtitles, always transcribe audio")
    ap.add_argument("--keep-audio", action="store_true", help="keep audio.mp3 in the output folder")
    a = ap.parse_args()

    is_url = bool(URL_RE.match(a.source))
    if not is_url and not os.path.isfile(a.source):
        die(f"File not found: {a.source}. Ask the user for the correct path.")
    os.makedirs(a.out, exist_ok=True)
    work = tempfile.mkdtemp(prefix="v2s_", dir=a.out)
    warnings, method, lang, segs = [], None, a.lang, None

    # 1. direct text
    if not a.force_asr:
        if is_url:
            sub, kind, err = subs_from_url(a.source, work, a.lang, a.allow_auto_subs)
        else:
            sub, kind = subs_from_file(a.source, work)
        if sub:
            segs = parse_subtitle(sub)
            if segs:
                method = kind
                if kind == "auto-captions":
                    warnings.append("Auto-generated captions: lower accuracy than Whisper; verify names and terms.")
            else:
                warnings.append("Subtitle file found but empty; falling back to speech-to-text.")
                segs = None

    # 2. ffmpeg -> mp3 -> ASR
    audio_len = None
    if segs is None:
        mp3 = os.path.join(work, "audio.mp3")
        if is_url:
            raw = download_audio(a.source, work)
            if raw != mp3:
                to_mp3(raw, mp3)
        else:
            to_mp3(a.source, mp3)
        audio_len = duration(mp3)
        device = a.device
        if device == "auto":
            device = "cuda" if shutil.which("nvidia-smi") else "cpu"
        if device == "cpu" and a.model.startswith("large"):
            warnings.append("Running large model on CPU can be slow; consider --model medium if too slow.")
        segs, lang, prob = transcribe(mp3, a.model, a.lang, device)
        method = f"ffmpeg-mp3 + faster-whisper:{a.model}"
        if prob is not None and prob < 0.6:
            warnings.append(f"Low language-detection confidence ({prob:.2f}); consider passing --lang.")
        if a.keep_audio:
            shutil.copy(mp3, os.path.join(a.out, "audio.mp3"))

    if not segs:
        die("No speech content was extracted (silent video or unsupported audio). Ask the user how to proceed.", 6)

    manifest = {
        "source": a.source,
        "method": method,
        "language": lang,
        "segments": len(segs),
        "audio_seconds": audio_len,
        "extracted_at": dt.datetime.now().isoformat(timespec="seconds"),
        "warnings": warnings,
    }
    write_outputs(a.out, segs, manifest)
    shutil.rmtree(work, ignore_errors=True)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"\nWrote transcript.txt / transcript.md / transcript.json / manifest.json to {a.out}")


if __name__ == "__main__":
    main()
