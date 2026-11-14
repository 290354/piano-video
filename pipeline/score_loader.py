#!/usr/bin/env python3
"""Turn a human/AI-written score.json into note events.

Score format (see scores/README.md):

{
  "key": "A", "mode": "minor", "meter": [4, 4], "bpm": 72,
  "pattern": "nocturne",                 // nocturne | waltz | block | arpeggio
  "chords": ["Am", "F", "C", "G", ...],  // one per bar
  "melody": [[bar, beat, dur, degree, octave, velocity], ...]
}

`degree` counts scale steps from the tonic (0 = tonic, 7 = tonic an octave up),
`octave` is relative to the octave of middle C. On downbeats the loader snaps
the melody to the chord tones so a rough idea still sounds consonant.
"""
import json, re

NOTE_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
           "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
SCALES = {"minor": [0, 2, 3, 5, 7, 8, 10],
          "major": [0, 2, 4, 5, 7, 9, 11],
          "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
          "dorian": [0, 2, 3, 5, 7, 9, 10]}


def parse_chord(name):
    m = re.match(r"^([A-G][#b]?)(.*)$", name.strip())
    if not m:
        raise ValueError(f"bad chord: {name}")
    root = NOTE_PC[m.group(1)]
    q = m.group(2) or ""
    minor = q.startswith("m") and not q.startswith("maj")
    third = 3 if minor else 4
    if q.startswith("dim"):
        third, fifth = 3, 6
    elif q.startswith("aug"):
        fifth = 8
    else:
        fifth = 7
    pcs = [root % 12, (root + third) % 12, (root + fifth) % 12]
    if q.endswith("7") and not q.startswith("maj7"):
        pcs.append((root + (10 if minor else 11)) % 12)
    return pcs


def voicing(pcs, low=45, n=4):
    """Stack the chord tones upward from `low` — a plain, singable left hand."""
    out, m = [], low
    while len(out) < n and m < low + 30:
        if m % 12 in pcs:
            out.append(m)
        m += 1
    return out


def snap(midi, pcs, span=6):
    best = 0
    for d in range(-span, span + 1):
        if (midi + d) % 12 in pcs and abs(d) < abs(best):
            best = d
    return midi + best


def build(path, transpose=0):
    with open(path) as f:
        sc = json.load(f)

    key = sc.get("key", "A")
    mode = sc.get("mode", "minor")
    if mode not in SCALES:
        raise ValueError(f"unknown mode {mode}")
    scale = SCALES[mode]
    root_pc = NOTE_PC[key]
    meter = sc.get("meter", [4, 4])
    bpb = meter[0] * 4.0 / meter[1]
    pattern = sc.get("pattern", "nocturne")
    vs = float(sc.get("velocity", 1.0))
    chords = sc["chords"]
    events = []

    def add(beat, dur, midi, vel, part):
        events.append({"beat": float(beat), "dur": float(dur), "midi": int(midi) + transpose,
                       "vel": float(vel), "part": part})

    for bar, name in enumerate(chords):
        pcs = parse_chord(name)
        v = voicing(pcs, low=int(sc.get("lhLow", 45)))
        base = bar * bpb

        add(base, bpb, v[0] - 12, 0.40 * vs, "bass")

        if pattern == "nocturne":                      # rolling eighths
            seq = [0, 1, 2, 3, 2, 1]
            step = bpb / len(seq)
            for i, ci in enumerate(seq):
                add(base + i * step, step, v[ci],
                    (0.34 + (0.06 if i == 0 else 0) + (0.02 if i % 2 == 0 else 0)) * vs, "harmony")
        elif pattern == "waltz":                       # bass on 1, chord on 2 and 3
            add(base, 1.0, v[0], 0.38 * vs, "harmony")
            for k in (1, 2):
                for ci in (1, 2, 3):
                    add(base + k, 0.9, v[ci], 0.30 * vs, "harmony")
        elif pattern == "block":                       # sustained chords
            for ci in range(4):
                add(base, bpb - 0.1, v[ci], (0.30 + 0.02 * ci) * vs, "harmony")
        elif pattern == "arpeggio":                    # sixteenths
            seq = [0, 1, 2, 3, 2, 1, 0, 1]
            step = bpb / len(seq)
            for i, ci in enumerate(seq):
                add(base + i * step, step, v[ci], (0.28 + 0.05 * (i == 0)) * vs, "harmony")
        else:
            raise ValueError(f"unknown pattern {pattern}")

    for item in sc.get("melody", []):
        bar, beat, dur, deg, octv, vel = (list(item) + [0, 0, 1, 0, 0, 0.75])[:6]
        deg, octv = int(deg), int(octv)
        midi = 12 * (octv + 5) + root_pc + scale[deg % 7] + 12 * (deg // 7)
        if abs(float(beat) - round(float(beat))) < 1e-6:
            midi = snap(midi, parse_chord(chords[int(bar) % len(chords)]))
        add(int(bar) * bpb + float(beat), float(dur), midi, float(vel) * vs, "melody")

    # a thin octave shimmer above the loudest phrase, like the built-in piece
    if sc.get("shimmer", True):
        mel = [e for e in events if e["part"] == "melody"]
        for e in mel:
            if e["vel"] >= 0.86:
                add(e["beat"], e["dur"], e["midi"] + 12, e["vel"] * 0.32, "sparkle")

    events.sort(key=lambda e: (e["beat"], e["midi"]))
    return events
