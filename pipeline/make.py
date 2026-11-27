#!/usr/bin/env python3
"""make.py — one command, from empty folder to a finished piano video.

    python3 make.py --title 夜曲 --out ../out/nocturne.mp4
    python3 make.py --bpm 66 --transpose -2 --scale 2 --out ../out/4k.mp4
    python3 make.py --preview 4 --out /tmp/test.mp4      # quick smoke test

Pipeline: samples -> compose -> master -> canvas frames -> h264/aac -> cover
"""
import argparse, json, os, re, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(HERE, "assets", "samples")
WAV_DIR = os.path.join(SAMPLE_DIR, "wav")
SAMPLE_URL = "https://tonejs.github.io/audio/salamander/{}.ogg"

SAMPLE_NAMES = ["A0", "Ds1", "Fs1", "C1", "A1", "C2", "Ds2", "Fs2", "A2", "C3",
                "Ds3", "Fs3", "A3", "C4", "Ds4", "Fs4", "A4", "C5", "Ds5", "Fs5",
                "A5", "C6", "Ds6", "Fs6", "A6", "C7", "Ds7", "Fs7", "A7", "C8"]
# de-duplicated, order preserved
SAMPLE_NAMES = list(dict.fromkeys(SAMPLE_NAMES))


def ffmpeg_exe():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def ensure_samples():
    """Decode the bundled .ogg samples to wav; fetch anything missing."""
    os.makedirs(WAV_DIR, exist_ok=True)
    missing = []
    for name in SAMPLE_NAMES:
        wav = os.path.join(WAV_DIR, name + ".wav")
        if os.path.exists(wav) and os.path.getsize(wav) > 1024:
            continue
        ogg = os.path.join(SAMPLE_DIR, name + ".ogg")
        if not (os.path.exists(ogg) and os.path.getsize(ogg) > 1024):
            missing.append(name)
            continue
        subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-i", ogg,
                        "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", wav], check=True)
    if missing:
        log(f"downloading {len(missing)} samples")
        for name in missing:
            ogg = os.path.join(SAMPLE_DIR, name + ".ogg")
            urllib.request.urlretrieve(SAMPLE_URL.format(name), ogg)
            subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-i", ogg,
                            "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le",
                            os.path.join(WAV_DIR, name + ".wav")], check=True)
    have = len([n for n in SAMPLE_NAMES if os.path.exists(os.path.join(WAV_DIR, n + ".wav"))])
    log(f"samples ready: {have}/{len(SAMPLE_NAMES)}")


def compose(build, bpm, transpose, score=None):
    log(f"composing at {bpm:g} BPM, transpose {transpose:+d}")
    cmd = [sys.executable, os.path.join(HERE, "compose.py"),
           "--bpm", str(bpm), "--transpose", str(transpose),
           "--samples", WAV_DIR, "--out", build]
    if score:
        cmd += ["--score", os.path.abspath(score)]
    subprocess.run(cmd, check=True)
    with open(os.path.join(build, "notes.json")) as f:
        meta = json.load(f)
    log(f"{len(meta['notes'])} notes, video length {meta['video']:.1f}s")
    return meta


def master(raw, out, dur, gain_db=0.0, fade=3.6):
    """EQ + fade + fixed gain.

    loudnorm used to compress LRA to 9 LU, which flattened exactly the
    pianissimo link sections this batch is built around; a fixed gain keeps
    the written dynamics intact and a limiter guards the true peak.
    """
    af = ("highpass=f=32,"
          "equalizer=f=260:t=q:w=1:g=-1.6,"
          "equalizer=f=3200:t=q:w=0.8:g=2.2,"
          + (f"afade=t=out:st={max(0.0, dur - fade - 0.2):.2f}:d={fade:.2f},"
             if fade > 0.02 else "")
          + f"volume={gain_db:.2f}dB,alimiter=limit=0.87:level=false")
    ff = ffmpeg_exe()
    subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", raw,
                    "-t", f"{dur:.2f}", "-af", af, "-ar", "48000", "-ac", "2", out], check=True)
    log(f"mastered at {gain_db:+.1f} dB")


def write_config(build, cfg):
    with open(os.path.join(build, "config.js"), "w") as f:
        f.write("window.CONFIG=" + json.dumps(cfg, ensure_ascii=False) + ";\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default=None)
    ap.add_argument("--title-en", default=None)
    ap.add_argument("--subtitle", default=None)
    ap.add_argument("--end-word", default="曲 终")
    ap.add_argument("--credit1", default="画面由代码逐帧绘制")
    ap.add_argument("--credit2", default="钢琴采样 · Salamander Grand Piano")
    ap.add_argument("--bpm", type=float, default=None)
    ap.add_argument("--score", default=None, help="score.json; overrides the built-in piece")
    ap.add_argument("--transpose", type=int, default=0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--scale", type=int, default=1, help="1 = 1080p, 2 = 2160p")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--preview", type=float, default=0)
    ap.add_argument("--no-cover", action="store_true")
    ap.add_argument("--gain", type=float, default=0.0, help="dB, applied after EQ/fade")
    a = ap.parse_args()

    out = os.path.abspath(a.out)
    build = os.path.abspath(a.workdir) if a.workdir else os.path.join(os.path.dirname(out), "build")
    os.makedirs(build, exist_ok=True)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    sc = {}
    if a.score:
        with open(a.score) as f:
            sc = json.load(f)
    bpm = a.bpm or sc.get("bpm") or 72.0
    title = a.title or sc.get("title") or "夜  曲"
    title_en = a.title_en or sc.get("titleEn") or "NOCTURNE"

    ensure_samples()
    meta = compose(build, bpm, a.transpose, a.score)
    dur = meta["video"]

    raw = os.path.join(build, "piano_raw.wav")
    audio = os.path.join(build, "piano_master.wav")
    # how the piece is allowed to end: a fade is a decision, not a default
    ending = str(sc.get("ending", "fade"))
    fade = 0.10 if ending == "cut" else (0.0 if ending == "ring" else 3.6)
    master(raw, audio, dur, a.gain, fade)

    transpose = a.transpose
    NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    if sc.get("key"):
        root = sc["key"].upper()
        mode_word = {"major": "MAJOR", "dorian": "DORIAN"}.get(sc.get("mode", "minor"), "MINOR")
    else:
        root = NAMES[(9 + transpose) % 12]      # the built-in piece is in A minor
        mode_word = "MINOR"

    low, high = 40 + transpose, 84 + transpose
    if a.score:
        # let an external score decide how much of the keyboard is on screen
        ms = [n["m"] for n in meta["notes"] if n["p"] != "sparkle"]
        if ms:
            low = max(21, min(ms) - 3)
            high = min(108, max(ms) + 3)
            if high - low < 24:
                high = min(108, low + 24)
    cfg = {
        "dur": dur,
        "title": title,
        "titleEn": title_en,
        "subtitle": a.subtitle or sc.get("subtitle") or
                    f"{root}  {mode_word}   ·   {bpm:g}  BPM   ·   SOLO  PIANO",
        "endWord": a.end_word,
        "credit1": a.credit1,
        "credit2": a.credit2,
        "low": low,
        "high": high,
        "pixelRatio": a.scale,
    }
    write_config(build, cfg)
    for f in ("scene.js", "index.html"):
        src = os.path.join(HERE, f)
        dst = os.path.join(build, f)
        if os.path.abspath(src) != os.path.abspath(dst):
            with open(src, "rb") as r, open(dst, "wb") as w:
                w.write(r.read())
    with open(os.path.join(build, "notes.json")) as f:
        notes = json.load(f)
    with open(os.path.join(build, "notes.js"), "w") as f:
        f.write("window.NOTES=" + json.dumps(notes, separators=(",", ":")) + ";\n")

    log("rendering frames (this is the slow part)")
    subprocess.run([sys.executable, os.path.join(HERE, "render.py"),
                    "--workdir", build, "--audio", audio, "--out", out,
                    "--fps", str(a.fps), "--duration", f"{dur:.2f}",
                    "--crf", str(a.crf),
                    "--preview", str(a.preview)], check=True)

    if not a.no_cover and not a.preview:
        cover = os.path.splitext(out)[0] + ".cover.jpg"
        subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-ss", "3.0",
                        "-i", out, "-frames:v", "1", "-q:v", "2", cover], check=True)
        log(f"cover -> {cover}")

    size = os.path.getsize(out) / 1e6
    shown = min(dur, a.preview) if a.preview else dur
    log(f"done: {out}  ({size:.1f} MB, {shown:.1f}s, {a.fps} fps)")


if __name__ == "__main__":
    main()
