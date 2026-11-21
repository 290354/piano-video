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


# Quality suffixes, longest-first so "m7b5" wins over "m7" and "maj7" over "m".
# Plain triads are unchanged from the original implementation, so every score
# written before this table existed still renders to exactly the same events.
_QUALITIES = [
    ("maj13", (0, 4, 7, 11, 14, 21)), ("maj9", (0, 4, 7, 11, 14)),
    ("maj7#11", (0, 4, 7, 11, 18)), ("maj7", (0, 4, 7, 11)), ("m13", (0, 3, 7, 10, 14, 21)),
    ("m11", (0, 3, 7, 10, 14, 17)), ("m9", (0, 3, 7, 10, 14)),
    ("mMaj7", (0, 3, 7, 11)), ("m7b5", (0, 3, 6, 10)), ("madd9", (0, 3, 7, 14)),
    ("m7", (0, 3, 7, 10)), ("m6/9", (0, 3, 7, 9, 14)), ("m6", (0, 3, 7, 9)), ("m", (0, 3, 7)),
    ("dim7", (0, 3, 6, 9)), ("dim", (0, 3, 6)),
    ("aug", (0, 4, 8)), ("7sus4", (0, 5, 7, 10)), ("7b9", (0, 4, 7, 10, 13)),
    ("7#11", (0, 4, 7, 10, 18)), ("7#9", (0, 4, 7, 10, 15)),
    ("13", (0, 4, 7, 10, 14, 21)), ("11", (0, 4, 7, 10, 14, 17)),
    ("9", (0, 4, 7, 10, 14)), ("7", (0, 4, 7, 10)),
    ("sus2", (0, 2, 7)), ("sus4", (0, 5, 7)), ("add9", (0, 4, 7, 14)),
    ("6/9", (0, 4, 7, 9, 14)), ("m6/9", (0, 3, 7, 9, 14)),
    ("6", (0, 4, 7, 9)), ("5", (0, 7)), ("", (0, 4, 7)),
]


class Chord(list):
    """Pitch classes in interval order (root first), plus the slash bass.

    Subclasses list so every call site that indexes, iterates or does
    `pc in chord` keeps working unchanged.
    """
    bass = None


def parse_chord(name):
    raw = name.strip()
    body, _, tail = raw.partition("/")
    tail = tail.strip()
    if tail and tail not in NOTE_PC:
        body = body + "/" + tail          # "C6/9" — the 9 belongs to the quality
        tail = ""
    m = re.match(r"^([A-G][#b]?)(.*)$", body)
    if not m:
        raise ValueError(f"bad chord: {name}")
    root = NOTE_PC[m.group(1)]
    q = m.group(2) or ""
    ivs = (0, 4, 7)
    for sfx, ints in _QUALITIES:
        if q.startswith(sfx):
            ivs = ints
            break
    out, seen = Chord(), set()
    for i in ivs:
        pc = (root + i) % 12
        if pc not in seen:
            seen.add(pc)
            out.append(pc)
    if tail:
        out.bass = NOTE_PC[tail]
    return out


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
    style="color" — keep the root at the bottom and put the colour tones
                    (7th / 9th) on top, dropping the 5th when the chord has
                    five notes. This is what makes extended chords read as
                    harmony rather than as a muddy cluster in the low register.
    """
    if style == "color":
        root = pcs[0]
        tones = list(pcs)
        if len(tones) >= 5:                 # drop the 5th, keep 9ths and 7ths
            quint = (root + 7) % 12
            tones = [t for t in tones if t != quint]
        tones = tones[:4]
        b = bass_note(root)
        upper = [m for m in range(b + 3, b + 26) if m % 12 in tones[1:]]
        if len(upper) < 3:
            upper = [m for m in range(b + 1, b + 34) if m % 12 in tones[1:]]
        if len(upper) < 3:
            return [b] + upper + [b + 12] * (3 - len(upper))
        pick = upper[:3]
        if prev and len(prev) >= 4:         # nearest position to the previous bar
            best, cost = pick, sum(abs(pick[i] - prev[i + 1]) for i in range(3))
            for sh in range(1, max(1, len(upper) - 2)):
                c = upper[sh:sh + 3]
                if len(c) < 3 or c[-1] - c[0] > 14:
                    continue
                k = sum(abs(c[i] - prev[i + 1]) for i in range(3))
                if k < cost:
                    best, cost = c, k
            pick = best
        return [b] + pick

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


NEW_PATTERNS = {"pulse", "ostinato", "counter", "drone", "broken", "waltz2"}


def _tone(u, ci):
    """Index into the upper voices, wrapping upward instead of repeating."""
    return u[ci] if ci < len(u) else u[ci % len(u)] + 12


def _bass_midi(bar, sc, pcs):
    """Written bass line beats the chord root; a slash chord beats it too."""
    bl = sc.get("bassLine")
    if bl:
        name = str(bl[min(bar, len(bl) - 1)]).strip()
        m = re.match(r"^([A-G][#b]?)(-?\d)$", name)
        if m:
            return 12 * (int(m.group(2)) + 1) + NOTE_PC[m.group(1)]
        if name in NOTE_PC:
            return bass_note(NOTE_PC[name])
    if pcs.bass is not None:
        return bass_note(pcs.bass)
    return bass_note(pcs[0])


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

        if pattern in NEW_PATTERNS:
            amp = vs * dyn
            bn = _bass_midi(bar, sc, pcs)
            u = v[1:] if len(v) > 1 else v          # upper voices, without the bass

            if pattern == "pulse":                  # quarter-note chordal drive
                for k in range(int(round(bpb))):
                    add(base + k, 0.9, bn, (0.42 if k == 0 else 0.32) * amp, "bass")
                    for i, ci in enumerate((0, 1, 2)):
                        w = (0.25 + 0.035 * i) * (1.08 if k == 0 else 1.0)
                        add(base + k, 0.86, _tone(u, ci), w * amp, "harmony")

            elif pattern == "ostinato":             # angular eighth-note figure
                shape = [0, 3, 1, 2, 0, 2, 3, 1] if bar % 4 != 2 else [0, 2, 3, 1, 0, 3, 1, 2]
                step = bpb / 8.0
                for i, ci in enumerate(shape):
                    acc = 0.07 if i in (0, 3) else 0.0
                    add(base + i * step, step * 0.92, _tone(u, ci), (0.29 + acc) * amp, "harmony")
                add(base, step * 1.7, bn, 0.45 * amp, "bass")
                add(base + bpb * 0.625, step * 1.5, bn + 7, 0.26 * amp, "bass")

            elif pattern == "counter":              # two-part left hand
                add(base, 1.9, bn, 0.44 * amp, "bass")
                alt = u[0] - 12 if u[0] - 12 > 33 else u[0]
                add(base + 2.0, 1.9, alt, 0.36 * amp, "bass")
                for k, ci in ((1.5, 1), (3.5, 2)):  # tenor answers off the beat
                    add(base + k, 0.45, _tone(u, ci), 0.24 * amp, "harmony")

            elif pattern == "drone":                # held root, sparse colour
                add(base, bpb - 0.02, bn, 0.34 * amp, "bass")
                add(base, bpb - 0.02, bn + 7, 0.19 * amp, "harmony")
                if bar % 2 == 0:
                    add(base + bpb * 0.75, 1.4, _tone(u, 0), 0.22 * amp, "harmony")
                    add(base + bpb * 0.75, 1.4, _tone(u, 2), 0.18 * amp, "harmony")

            elif pattern == "broken":               # eighths, syncopated bass
                shape = [0, 2, 1, 3, 2, 0, 3, 1] if bar % 2 == 0 else [0, 1, 3, 2, 1, 3, 0, 2]
                step = bpb / 8.0
                for i, ci in enumerate(shape):
                    w = 0.30 + (0.03 if i % 2 else 0.0)
                    add(base + i * step, step * 0.9, _tone(u, ci), w * amp, "harmony")
                add(base + 0.5, 1.4, bn, 0.42 * amp, "bass")
                add(base + bpb * 0.6875, 1.0, bn, 0.28 * amp, "bass")

            elif pattern == "waltz2":               # the waltz with its weight reversed
                for ci in (0, 1, 2):
                    add(base, 0.85, _tone(u, ci), (0.30 + 0.02 * ci) * amp, "harmony")
                    add(base + 1, 0.85, _tone(u, ci), 0.26 * amp, "harmony")
                add(base + 2, 0.95, bn, 0.40 * amp, "bass")

            else:
                raise ValueError(f"unknown pattern {pattern}")

        else:
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

    for item in list(sc.get("melody", [])):
        item = list(item)
        bar, beat, dur, deg, octv, vel = (item + [0, 0, 1, 0, 0, 0.75])[:6]
        acc = int(item[6]) if len(item) > 6 else 0     # semitone inflection
        bar, deg, octv = int(bar), int(deg), int(octv)
        sec = _section_of(bar, sections)
        dyn = float(sec.get("dynamic", 1.0))
        midi = 12 * (octv + 5) + root_pc + scale[deg % 7] + 12 * (deg // 7) + acc
        if acc == 0 and abs(float(beat) - round(float(beat))) < 1e-6:
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
