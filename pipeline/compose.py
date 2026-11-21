#!/usr/bin/env python3
"""Compose a short piano nocturne and render it with Salamander grand-piano samples."""
import json, os, subprocess, math, argparse
from fractions import Fraction
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly, butter, sosfilt
from scipy.signal import fftconvolve

_ap = argparse.ArgumentParser(description="Compose a piano piece and render it with Salamander samples")
_ap.add_argument("--bpm", type=float, default=72.0)
_ap.add_argument("--transpose", type=int, default=0, help="semitones, positive = higher")
_ap.add_argument("--samples", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "samples"))
_ap.add_argument("--out", default="/root/piano/build")
_ap.add_argument("--score", default=None, help="score.json written by hand or by an LLM")
_ARGS, _ = _ap.parse_known_args()

SR = 48000
BPM = _ARGS.bpm
TRANSPOSE = _ARGS.transpose
BEAT = 60.0 / BPM
SAMPLE_DIR = _ARGS.samples
OUT = _ARGS.out
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- note names
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
def midi_to_name(m):
    return NAMES[m % 12] + str(m // 12 - 1)

SAMPLE_FILES = {
    "A0": 21, "Ds1": 27, "Fs1": 30, "C1": 24, "A1": 33, "C2": 36, "Ds2": 39,
    "Fs2": 42, "A2": 45, "C3": 48, "Ds3": 51, "Fs3": 54, "A3": 57, "C4": 60,
    "Ds4": 63, "Fs4": 66, "A4": 69, "C5": 72, "Ds5": 75, "Fs5": 78, "A5": 81,
    "C6": 84, "Ds6": 87, "Fs6": 90, "A6": 93, "C7": 96, "Ds7": 99, "Fs7": 102,
    "A7": 105, "C8": 108,
}
ROOTS = sorted(SAMPLE_FILES.items(), key=lambda kv: kv[1])

SAMPLES = {}
def load_samples():
    for name, _ in ROOTS:
        p = os.path.join(SAMPLE_DIR, name + ".wav")
        sr, data = wavfile.read(p)
        if data.dtype == np.int16:
            data = data.astype(np.float32) / 32768.0
        # the samples ship at 44.1 kHz but the mix runs at 48 kHz: convert
        # before pitch-shifting, otherwise everything plays ~1.5 semitones flat
        if sr != SR:
            data = resample_poly(data, SR, sr, axis=0).astype(np.float32)
            sr = SR
        if data.ndim == 1:
            data = np.stack([data, data], axis=1)
        # trim the near-silent head (keep 8 ms of pre-attack)
        env = np.abs(data).max(axis=1)
        idx = np.argmax(env > 0.02 * env.max())
        start = max(0, idx - int(0.008 * sr))
        data = data[start:]
        data /= max(1e-6, np.abs(data).max())
        SAMPLES[name] = (sr, data.astype(np.float32))
    print(f"loaded {len(SAMPLES)} samples")

def nearest_sample(midi):
    return min(ROOTS, key=lambda kv: abs(kv[1] - midi))[0]

# ---------------------------------------------------------------- composition
# chords: root voicing used by the left hand (midi numbers, ascending)
CH = {
    "Am": [45, 52, 57, 60, 64],
    "F":  [41, 48, 53, 57, 60],
    "C":  [48, 55, 60, 64, 67],
    "G":  [43, 50, 55, 59, 62],
    "Dm": [50, 57, 62, 65, 69],
    "E":  [40, 47, 52, 56, 59],
}

BARS = ["Am", "Am", "Am", "F", "C", "G", "Am", "F", "Dm", "E",
        "F", "C", "G", "Am", "Am", "F", "C", "G", "F", "E", "Am"]

events = []   # dicts: beat, dur, midi, vel, part

def add(beat, dur, midi, vel, part):
    events.append({"beat": float(beat), "dur": float(dur), "midi": int(midi) + TRANSPOSE,
                   "vel": float(vel), "part": part})

# --- intro (bars 1-2): rolled A minor, a call in the dark
for i, m in enumerate([33, 45, 52, 57, 60, 64]):
    add(0.05 * i, 8 - 0.05 * i, m, 0.36 - 0.02 * i, "harmony")
add(5.0, 1.5, 81, 0.42, "melody")
add(6.5, 1.5, 76, 0.38, "melody")

# --- left hand arpeggios, bars 3-18
ARP = [0, 1, 2, 3, 4, 3, 2, 1]
for bar in range(2, 18):          # zero-based bar index -> bars 3..18
    chord = CH[BARS[bar]]
    base = bar * 4.0
    add(base, 4.0, chord[0] - 12, 0.40, "bass")
    for i, ci in enumerate(ARP):
        v = 0.34 + (0.05 if i % 4 == 0 else 0.0) + (0.02 if i % 2 == 0 else 0.0)
        if bar >= 10:             # B section: a little fuller
            v += 0.03
        add(base + i * 0.5, 0.5, chord[ci], v, "harmony")

# --- melody A1 (bars 3-6)
A1 = [
    (8.0, 1.0, 76, .78), (9.0, 0.5, 81, .86), (9.5, 0.5, 79, .80),
    (10.0, 1.0, 77, .80), (11.0, 1.0, 76, .74),
    (12.0, 1.5, 74, .74), (13.5, 0.5, 76, .78), (14.0, 2.0, 77, .82),
    (16.0, 1.0, 76, .80), (17.0, 0.5, 79, .86), (17.5, 0.5, 77, .78),
    (18.0, 2.0, 76, .80),
    (20.0, 1.5, 74, .74), (21.5, 0.5, 72, .72), (22.0, 2.0, 71, .70),
]
for b, d, m, v in A1:
    add(b, d, m, v, "melody")

# --- melody A1 second phrase (bars 7-10)
A2 = [
    (24.0, 1.0, 72, .78), (25.0, 0.5, 76, .82), (25.5, 0.5, 81, .90),
    (26.0, 2.0, 79, .84),
    (28.0, 1.0, 77, .80), (29.0, 0.5, 76, .78), (29.5, 0.5, 74, .74),
    (30.0, 2.0, 72, .76),
    (32.0, 1.0, 74, .78), (33.0, 0.5, 77, .82), (33.5, 0.5, 81, .88),
    (34.0, 2.0, 77, .78),
    (36.0, 1.0, 76, .80), (37.0, 1.0, 74, .74), (38.0, 2.0, 71, .72),
]
for b, d, m, v in A2:
    add(b, d, m, v, "melody")

# --- B section (bars 11-14), higher and fuller, with a third above
B = [
    (40.0, 1.0, 81, .90), (41.0, 1.0, 84, .95), (42.0, 1.0, 83, .90),
    (43.0, 1.0, 81, .86),
    (44.0, 1.5, 79, .86), (45.5, 0.5, 76, .80), (46.0, 2.0, 79, .86),
    (48.0, 1.0, 77, .82), (49.0, 1.0, 74, .78), (50.0, 2.0, 71, .76),
    (52.0, 1.0, 72, .80), (53.0, 1.0, 76, .84), (54.0, 2.0, 81, .90),
]
for b, d, m, v in B:
    add(b, d, m, v, "melody")
# octave shimmer on the top of the B line
for b, d, m, v in B:
    if b >= 40 and b < 48:
        add(b, d, m + 12, v * 0.35, "sparkle")

# --- return (bars 15-18)
RET = [
    (56.0, 1.0, 76, .84), (57.0, 0.5, 81, .90), (57.5, 0.5, 79, .84),
    (58.0, 1.0, 77, .84), (59.0, 1.0, 76, .80),
    (60.0, 1.5, 74, .80), (61.5, 0.5, 76, .82), (62.0, 2.0, 77, .86),
    (64.0, 1.0, 76, .84), (65.0, 0.5, 79, .88), (65.5, 0.5, 77, .82),
    (66.0, 2.0, 76, .84),
    (68.0, 1.5, 74, .78), (69.5, 0.5, 72, .76), (70.0, 2.0, 69, .74),
]
for b, d, m, v in RET:
    add(b, d, m, v, "melody")

# --- coda (bars 19-21)
CODA = [
    (72.0, 1.5, 81, .80), (73.5, 0.5, 79, .74), (74.0, 2.0, 77, .78),
    (76.0, 2.0, 76, .76), (78.0, 2.0, 74, .70),
    (80.0, 4.0, 81, .66),
]
for b, d, m, v in CODA:
    add(b, d, m, v, "melody")

# coda left hand: slow, open
add(72.0, 4.0, 41, .34, "bass"); add(72.0, 4.0, 53, .30, "harmony")
add(72.0, 4.0, 57, .28, "harmony"); add(72.0, 4.0, 60, .26, "harmony")
add(76.0, 4.0, 40, .34, "bass"); add(76.0, 4.0, 52, .30, "harmony")
add(76.0, 4.0, 56, .28, "harmony"); add(76.0, 4.0, 59, .26, "harmony")
# final rolled A minor add9
for i, m in enumerate([33, 45, 52, 57, 60, 64, 71, 76]):
    add(80.0 + 0.07 * i, 8.0, m, 0.40 - 0.02 * i, "harmony")

if _ARGS.score:
    import score_loader
    events.clear()
    events.extend(score_loader.build(_ARGS.score, TRANSPOSE))
    print(f"score: {_ARGS.score} -> {len(events)} notes")

events.sort(key=lambda e: (e["beat"], e["midi"]))

# ---------------------------------------------------------------- tempo map
# A score may ask for tempo changes and a closing ritardando:
#   "tempo": {"map": [[0, 66], [8, 72], [16, 62]], "rit": {"bar": 14, "factor": 0.78}}
# Everything downstream works in seconds, so build beat -> second once.
_TEMPO, _BPB = {}, 4.0
if _ARGS.score:
    try:
        with open(_ARGS.score) as _f:
            _SC_RAW = json.load(_f)
        _TEMPO = _SC_RAW.get("tempo") or {}
        _m = _SC_RAW.get("meter") or [4, 4]
        _BPB = _m[0] * 4.0 / _m[1]
    except Exception:
        _TEMPO, _BPB = {}, 4.0

_END_BEAT = max(e["beat"] + e["dur"] for e in events)
_CTRL = [[0.0, BPM]]
for bar, v in (_TEMPO.get("map") or []):
    _CTRL.append([float(bar) * _BPB, float(v)])
_CTRL.sort()
_RIT = _TEMPO.get("rit") or {}


def bpm_at(beat):
    bpm = _CTRL[0][1]
    for i in range(1, len(_CTRL)):
        b0, v0 = _CTRL[i - 1]
        b1, v1 = _CTRL[i]
        if beat <= b1:
            t = (beat - b0) / max(1e-9, b1 - b0)
            bpm = v0 + (v1 - v0) * min(1.0, max(0.0, t))
            break
        bpm = v1
    if _RIT:
        r0 = float(_RIT.get("bar", 0)) * _BPB
        r1 = float(_RIT.get("barTo", _END_BEAT / _BPB)) * _BPB
        if beat > r0:
            t = min(1.0, (beat - r0) / max(1e-9, r1 - r0))
            bpm *= 1.0 + (float(_RIT.get("factor", 1.0)) - 1.0) * t
    return max(20.0, bpm)


_BT_CACHE = {}


def bt(beat, _dt=0.01):
    """integrate 60/bpm from 0 to `beat` — beat position to seconds"""
    if beat <= 0:
        return 0.0
    key = round(beat, 4)
    if key in _BT_CACHE:
        return _BT_CACHE[key]
    n = int(beat / _dt) + 1
    acc = 0.0
    prev = 0.0
    for i in range(1, n + 1):
        b = min(beat, i * _dt)
        acc += (b - prev) * 60.0 / bpm_at(prev + (b - prev) * 0.5)
        prev = b
        if prev >= beat:
            break
    _BT_CACHE[key] = acc
    return acc

# ---------------------------------------------------------------- rendering
def velocity_filter(cutoff):
    sos = butter(1, min(cutoff, SR / 2 * 0.92) / (SR / 2), btype="low", output="sos")
    return sos

def render_note(ev):
    midi, vel, dur = ev["midi"], ev["vel"], ev["dur"]
    art = ev.get("art") or ""
    # articulation shortens the key press, not the written value
    sounding = dur
    if art == "stacc":
        sounding = dur * 0.45
    elif art == "marc":
        sounding = dur * 0.82
    # damper pedal: the string keeps ringing until the pedal is lifted
    pedalled = False
    ped_end = ev.get("pedEnd")
    if ped_end and ped_end > ev["beat"] + sounding + 1e-6:
        sounding = ped_end - ev["beat"]
        pedalled = True

    name = nearest_sample(midi)
    sr, x = SAMPLES[name]
    r = 2.0 ** ((midi - SAMPLE_FILES[name]) / 12.0)
    frac = Fraction(r).limit_denominator(400)
    y = resample_poly(x, frac.numerator, frac.denominator, axis=0).astype(np.float32)

    ring = 2.9 if pedalled else 2.0
    total = int((sounding + ring) * SR)
    if len(y) < total:
        y = np.pad(y, ((0, total - len(y)), (0, 0)))
    else:
        y = y[:total]

    # velocity: level + brightness (soft playing is darker)
    gain = 0.16 + 0.84 * vel ** 1.7
    if art == "acc":
        gain *= 1.10
    elif art == "marc":
        gain *= 1.14
    y *= gain
    cutoff = 2200.0 + 13500.0 * (vel ** 1.15)
    if cutoff < SR / 2 * 0.92:
        sos = velocity_filter(cutoff)
        y = sosfilt(sos, y, axis=0).astype(np.float32)

    # damper: the key lifts, the string keeps ringing under the pedal
    off = int(sounding * SR)
    n = len(y)
    if off < n:
        t = np.arange(n - off) / SR
        env = np.exp(-t / (2.4 if pedalled else 0.85)).astype(np.float32)
        y[off:] *= env[:, None]

    # short fade-in to avoid clicks on the softest notes
    a = min(int(0.004 * SR), n)
    y[:a] *= np.linspace(0, 1, a, dtype=np.float32)[:, None]

    # a little air between the hands
    pan = {"melody": 0.10, "harmony": -0.08, "bass": 0.0,
           "sparkle": 0.26}.get(ev["part"], 0.0)
    if pan:
        y[:, 0] *= (1.0 - pan)
        y[:, 1] *= (1.0 + pan)
    return y

def make_ir(seconds=3.0, decay=1.05, predelay=0.022):
    rng = np.random.default_rng(11)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)).astype(np.float32)
    ir *= np.exp(-t / decay)[:, None]
    # darker as it decays
    sos = butter(1, 3200 / (SR / 2), btype="low", output="sos")
    ir = sosfilt(sos, ir, axis=0).astype(np.float32)
    # a few early reflections
    for d, g in [(0.011, .5), (0.019, .35), (0.031, .28), (0.047, .2)]:
        k = int(d * SR)
        ir[k:k + 200] += g * rng.standard_normal((200, 2)).astype(np.float32) * np.linspace(1, 0, 200)[:, None]
    pre = int(predelay * SR)
    ir = np.concatenate([np.zeros((pre, 2), np.float32), ir], axis=0)
    ir /= np.sqrt((ir ** 2).sum(axis=0, keepdims=True))
    return ir

def main():
    load_samples()
    last_note = max(e["beat"] + e["dur"] for e in events)
    end_beat = max(max(e["beat"] + e["dur"], e.get("pedEnd", 0.0)) for e in events)

    # how much silence to keep after the last note; external scores can ask for
    # a longer ring-out (room for the end card) via {"tail": seconds}
    tail = 0.6
    if _ARGS.score:
        try:
            with open(_ARGS.score) as _f:
                tail = float(json.load(_f).get("tail", 0.6))
        except Exception:
            tail = 0.6
    tail = max(0.4, min(tail, 12.0))

    total = int((bt(end_beat) + max(4.0, tail + 2.5)) * SR)
    mix = np.zeros((total, 2), dtype=np.float32)
    print(f"{len(events)} notes, {bt(end_beat):.1f}s + tail")

    for i, ev in enumerate(events):
        start = int(bt(ev["beat"]) * SR)
        y = render_note(ev)
        stop = min(total, start + len(y))
        if stop <= start:
            continue
        mix[start:stop] += y[:stop - start]

    print("reverb")
    ir = make_ir()
    wet = np.stack([fftconvolve(mix[:, c], ir[:, c])[:total] for c in range(2)], axis=1)
    wet = wet.astype(np.float32)
    out = 0.92 * mix + 0.30 * wet
    # gentle bus glue + safety limiter
    out = np.tanh(out * 1.15) / 1.15
    peak = np.abs(out).max()
    out *= 0.84 / peak
    wavfile.write(os.path.join(OUT, "piano_raw.wav"), SR, (out * 32767).astype(np.int16))

    # note data for the picture
    data = []
    for ev in events:
        data.append({
            "t": round(bt(ev["beat"]), 4),
            "d": round(bt(ev["beat"] + ev["dur"]) - bt(ev["beat"]), 4),
            "m": ev["midi"],
            "v": round(ev["vel"], 3),
            "p": ev["part"],
        })
    meta = {"bpm": BPM, "beat": BEAT, "duration": round(total / SR, 3),
            "video": round(bt(last_note) + tail, 2),
            "transpose": TRANSPOSE, "notes": data}
    with open(os.path.join(OUT, "notes.json"), "w") as f:
        json.dump(meta, f, separators=(",", ":"))
    print("wrote", total / SR, "s")

if __name__ == "__main__":
    main()
