#!/usr/bin/env python3
"""Turn a written score.json into note events.

Score format (see scores/README.md):

{
  "key": "A", "mode": "minor", "meter": [4, 4], "bpm": 72,
  "pattern": "nocturne",                 // nocturne | waltz | block | arpeggio
  "voicing": "lead",                     // close | lead
  "sections": [                          // optional: contrast between sections
    {"name": "A", "bars": [0, 8], "pattern": "nocturne", "dynamic": 0.85},
    {"name": "B", "bars": [8, 16], "pattern": "arpeggio", "dynamic": 1.0}
  ],
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


def bass_note(root_pc, lo=40, hi=52):
    """Root of the chord in the E2–E3 register: low enough to support the
    harmony, high enough that the keyboard does not sprawl over five octaves."""
    m = lo + ((root_pc - lo) % 12)
    return m if m <= hi else m - 12


def _chord_notes(pcs, lo, hi):
    return [m for m in range(lo, hi) if m % 12 in pcs]


def voicing(pcs, low=45, n=4, prev=None, style="lead"):
    """Stack chord tones in the left hand.

    style="close" — plain root-position stack (the original behaviour).
    style="lead"  — take the inversion that moves least from the previous bar,
                    so the left hand carries a line instead of jumping around.
    """
    if style != "lead" or not prev:
        out, m = [], low
        while len(out) < n and m < low + 30:
            if m % 12 in pcs:
                out.append(m)
            m += 1
        return out

    pool = _chord_notes(pcs, low - 12, low + 34)
    best, best_cost = None, None
    for start in range(max(1, len(pool) - n + 1)):
        cand = pool[start:start + n]
        if len(cand) < n or cand[-1] - cand[0] > 22:      # keep the hand span playable
            continue
        cost = sum(abs(cand[i] - prev[min(i, len(prev) - 1)]) for i in range(n))
        cost += 0.4 * abs(cand[0] - low)                  # stay near the written register
        if best_cost is None or cost < best_cost:
            best, best_cost = cand, cost
    return best or pool[:n]


def snap(midi, pcs, span=6):
    best = 0
    for d in range(-span, span + 1):
        if (midi + d) % 12 in pcs and abs(d) < abs(best):
            best = d
    return midi + best


def _section_of(bar, sections):
    for s in sections:
        b = s.get("bars") or [0, 10 ** 9]
        if b[0] <= bar < b[1]:
            return s
    return {}


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
    base_pattern = sc.get("pattern", "nocturne")
    vs = float(sc.get("velocity", 1.0))
    sections = sc.get("sections") or []
    style = sc.get("voicing", "lead")
    var = float(sc.get("patternVar", 0.0))
    chords = sc["chords"]
    events = []
    prev_v = None

    def add(beat, dur, midi, vel, part):
        events.append({"beat": float(beat), "dur": float(dur), "midi": int(midi) + transpose,
                       "vel": float(min(1.0, max(0.05, vel))), "part": part})

    for bar, name in enumerate(chords):
        sec = _section_of(bar, sections)
        pattern = sec.get("pattern", base_pattern)
        dyn = float(sec.get("dynamic", 1.0))
        pcs = parse_chord(name)
        v = voicing(pcs, low=int(sc.get("lhLow", 45)), prev=prev_v, style=style)
        prev_v = v
        base = bar * bpb

        add(base, bpb, bass_note(pcs[0]), 0.40 * vs * dyn, "bass")

        if pattern == "nocturne":                      # rolling eighths
            seq = [0, 1, 2, 3, 2, 1]
        elif pattern == "arpeggio":                    # sixteenths
            seq = [0, 1, 2, 3, 2, 1, 0, 1]
        else:
            seq = None

        if seq is not None:
            if var > 0 and bar % 3 == 1:               # vary the figure every few bars
                seq = seq[1:] + seq[:1]
            step = bpb / len(seq)
            for i, ci in enumerate(seq):
                base_v = 0.34 if pattern == "nocturne" else 0.28
                accent = 0.06 if i == 0 else (0.02 if i % 2 == 0 else 0)
                add(base + i * step, step, v[ci], (base_v + accent) * vs * dyn, "harmony")
        elif pattern == "waltz":                       # bass on 1, chord on 2 and 3
            add(base, 1.0, v[0], 0.38 * vs * dyn, "harmony")
            for k in (1, 2):
                for ci in (1, 2, 3):
                    add(base + k, 0.9, v[ci], 0.30 * vs * dyn, "harmony")
        elif pattern == "block":                       # sustained chords
            for ci in range(4):
                add(base, bpb - 0.1, v[ci], (0.30 + 0.02 * ci) * vs * dyn, "harmony")
        else:
            raise ValueError(f"unknown pattern {pattern}")

    for item in sc.get("melody", []):
        bar, beat, dur, deg, octv, vel = (list(item) + [0, 0, 1, 0, 0, 0.75])[:6]
        bar, deg, octv = int(bar), int(deg), int(octv)
        sec = _section_of(bar, sections)
        dyn = float(sec.get("dynamic", 1.0))
        midi = 12 * (octv + 5) + root_pc + scale[deg % 7] + 12 * (deg // 7)
        if abs(float(beat) - round(float(beat))) < 1e-6:
            midi = snap(midi, parse_chord(chords[bar % len(chords)]))
        add(bar * bpb + float(beat), float(dur), midi, float(vel) * vs * dyn, "melody")

    # optional octave doubling; off by default so the written register is what
    # you hear (and what the keyboard shows)
    if sc.get("shimmer", False):
        mel = [e for e in events if e["part"] == "melody"]
        for e in mel:
            # only at the loudest point, and never above the written register,
            # otherwise the doubling turns into a second melody in the stratosphere
            if e["vel"] >= 0.90 and e["midi"] <= 84:
                add(e["beat"], e["dur"], e["midi"] + 12, e["vel"] * 0.22, "sparkle")

    events.sort(key=lambda e: (e["beat"], e["midi"]))
    return events
