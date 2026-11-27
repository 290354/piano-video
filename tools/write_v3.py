#!/usr/bin/env python3
"""write_v3.py — three pieces that are not the same piece three times.

What the last batch still did wrong, and what changes here:

1. One shape for all three (quiet intro, rise, block-chord climax, slower
   return, fade). Now each piece has its own architecture and its own ending:
     铁轨    through-composed accumulation; the loudest bar is the last bar,
             it stops on a cut, nothing fades.
     三月的信 arch with the climax early (bar 11), a long harmonic unwind that
             ends in A minor — a different key than it began in.
     铜与霜 sonata: exposition, tritone-area second subject, fugato development,
             recapitulation, then a coda that lands on E major.
2. Left hand as wallpaper. The left hand now carries the subject (canon,
   inversion, stretto) in the sections where that matters, written out note by
   note; the fixed figures are kept only where a motor is the point.
3. Harmony that only leans sideways. Each piece visits a key a tritone away
   and resolves by chromatic-mediant or tritone root motion, not by a borrowed
   chord two steps from home.

Everything is generated from the same degree lists so the transformations are
literal: P, I (inversion), R (retrograde), RI, augmentation, compression.
"""
import json, os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scores")
PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
      "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def m(name, octv):
    """MIDI for a written pitch; octave 4 = middle C."""
    return 12 * (octv + 1) + PC[name]


def tr(seq, k):
    return [(d + k, du) for d, du in seq]


def inv(seq, axis=0):
    return [(2 * axis - d, du) for d, du in seq]


def ret(seq):
    return list(reversed(seq))


def stretch(seq, f):
    return [(d, du * f) for d, du in seq]


def line(rows, bar, t0, seq, octv, vel, art="", step=1.0, semi=0):
    """Place a (degree, duration) sequence; `step` scales every duration."""
    t = t0
    for d, du in seq:
        rows.append([bar, round(t, 3), round(du * step, 3), d, octv, vel, semi, art])
        t += du * step
    return t


def lh(rows, bar, t0, notes, vel, art="", step=1.0):
    """Written left hand: [(midi, duration), ...] starting at beat t0."""
    t = t0
    for midi, du in notes:
        rows.append([bar, round(t, 3), round(du * step, 3), midi, vel, art])
        t += du * step
    return t


def pedal_all(nbars, bpb=4.0):
    return [[b, 0, bpb - 0.05] for b in range(nbars)]


def dyn(points):
    return [[b, v] for b, v in points]


# ---------------------------------------------------------------------------
# 1. 铁轨 — D dorian, 126 BPM, 32 bars.  Builds to the last bar and stops.
# ---------------------------------------------------------------------------
def tracks():
    N = 32
    mel, cnt, left = [], [], []
    # the cell: D F E G  (degrees 0 2 1 3), one beat + two eighths + a held note
    P = [(0, 1.0), (2, 0.5), (1, 0.5), (3, 2.0)]
    Q = [(0, 0.5), (2, 0.5), (1, 0.5), (3, 1.5)]        # compressed
    Q2 = [(0, 0.5), (2, 0.5), (1, 0.5), (3, 0.5)]       # two beats, fits anywhere
    R = [(3, 0.5), (1, 0.5), (2, 0.5), (0, 1.5)]        # retrograde, compressed

    # --- 1-4  left hand alone, the cell at half speed, no harmony yet
    for b in range(4):
        lh(left, b, 0, [(m("D", 2), 4)], 0.42, "ten")
        lh(left, b, 0, [(m("D", 3), 2), (m("F", 3), 1), (m("E", 3), 1)], 0.30 + 0.03 * b, "ten")
    # right hand enters at bar 3, two octaves up, thin
    line(mel, 2, 0, P, 1, 0.34, "ten")
    line(mel, 3, 0, tr(P, 1), 1, 0.38, "ten")

    # --- 5-8  sequence up, left hand starts answering in the tenor
    line(mel, 4, 0, tr(P, 2), 1, 0.44, "ten")
    line(mel, 5, 0, tr(P, 4), 1, 0.48, "ten")
    line(mel, 6, 0, tr(P, 5), 1, 0.54, "marc")
    cnt_start = 6
    line(cnt, cnt_start, 2, tr(Q2, 0), 0, 0.40, "ten")
    line(mel, 7, 0, tr(P, 2), 1, 0.58, "marc")
    line(cnt, 7, 2, tr(Q2, 2), 0, 0.44, "ten")
    for b in range(4, 8):
        lh(left, b, 0, [(m("D", 2), 4)], 0.34 + 0.04 * (b - 4), "ten")
        lh(left, b, 0, [(m("A", 3), 1), (m("G", 3), 1), (m("F", 3), 1), (m("E", 3), 1)],
           0.26 + 0.03 * (b - 4))

    # --- 9-11  A flat major: the tritone, stated while D is still holding
    # D pedal under A flat major is the shock; the cell keeps its shape
    line(mel, 8, 0, P, 1, 0.62, "marc")                 # A flat C B flat D flat
    line(cnt, 8, 2, tr(Q2, 0), 0, 0.42, "ten")
    line(mel, 9, 0, tr(P, 2), 1, 0.66, "marc")
    line(cnt, 9, 2, tr(Q2, 2), 0, 0.46, "ten")
    line(mel, 10, 0, stretch(tr(P, 3), 1.0), 1, 0.70, "marc")
    for b in (8, 9, 10):
        lh(left, b, 0, [(m("D", 2), 4)], 0.40)          # the pedal that refuses to move
        lh(left, b, 0, [(m("Eb", 3), 2), (m("C", 4), 2)], 0.26, "ten")

    # --- 12-13  link: chromatic bass back to D, right hand in fragments
    lh(left, 11, 0, [(m("Ab", 2), 1), (m("G", 2), 1), (m("Gb", 2), 1), (m("F", 2), 1)], 0.52, "marc")
    lh(left, 11, 0, [(m("D", 2), 4)], 0.34, "ten")
    lh(left, 12, 0, [(m("E", 2), 1), (m("F", 2), 1), (m("E", 2), 1), (m("D", 2), 1)], 0.56, "marc")
    lh(left, 12, 0, [(m("D", 2), 4)], 0.34, "ten")
    line(mel, 11, 0, [(3, 0.5), (2, 0.5), (1, 0.5), (0, 1.0)], 1, 0.60)
    line(mel, 12, 0, [(1, 0.5), (0, 0.5), (2, 0.5), (0, 1.0)], 1, 0.66, "marc")

    # --- 14-19  canon: the tenor states, the soprano answers two beats later,
    # then the entries close to one beat, then to half a beat.
    q4 = [(3, 0.5), (1, 0.5), (2, 0.5), (0, 0.5)]      # two beats, retrograde
    line(cnt, 13, 0, Q2, 0, 0.50, "ten")
    line(mel, 13, 2, Q2, 1, 0.62, "marc")
    line(cnt, 14, 0, tr(Q2, 4), 0, 0.52, "ten")
    line(mel, 14, 2, tr(Q2, 4), 1, 0.64, "marc")
    line(cnt, 15, 0, Q2, 0, 0.54, "ten")
    line(mel, 15, 1, Q2, 1, 0.66, "marc")
    line(cnt, 15, 2, tr(Q2, 2), 0, 0.50, "ten")
    line(mel, 15, 2, tr(Q2, 2), 1, 0.62, "marc")
    for i, k in enumerate([0, 2, 4]):                  # half-beat stretto
        line(cnt, 16, i * 0.5, tr(q4, k), 0, 0.50, "ten")
        line(mel, 16, i * 0.5 + 0.5, tr(q4, k), 1, 0.62, "marc")
    line(mel, 17, 0, inv(P, 3), 1, 0.70, "marc")       # contrary motion
    line(cnt, 17, 0, tr(P, 0), 0, 0.54, "ten")
    for b in range(13, 19):
        lh(left, b, 0, [(m("D", 2), 4)], 0.40, "ten")
        if b != 17:
            lh(left, b, 0, [(m("A", 3), 0.5)] * 8, 0.22)

    # --- 20-21  the canon runs down to one note and speeds up
    for b in (19, 20):
        for i in range(8):
            line(mel, b, i * 0.5, [(0, 0.45)], 1, 0.60 + 0.03 * i, "marc")
            line(cnt, b, i * 0.5 + 0.25, [(0, 0.22)], 1, 0.48, "stacc")
        lh(left, b, 0, [(m("D", 2), 4)], 0.52, "ten")
        lh(left, b, 0, [(m("D", 3), 0.25)] * 16, 0.24)

    # --- 22-27  double canon in contrary motion, no chords anywhere
    for i, b in enumerate(range(21, 27)):
        k = [0, 2, 3, 5, 4, 2][i]
        line(mel, b, 0, tr(P, k), 1, 0.78, "marc")
        line(cnt, b, 0, inv(tr(P, k), 3), 1, 0.66, "marc")
        lh(left, b, 0, [(m("D", 2), 2), (m("A", 1), 2)], 0.56, "ten")
        lh(left, b, 0, [(m("B", 2), 2), (m("Bb", 2), 2)], 0.34, "ten")
    line(mel, 26, 0, [(0, 2.0), (2, 1.0), (1, 1.0)], 1, 0.84, "marc")
    line(mel, 27, 0, [(3, 4.0)], 1, 0.80, "marc")
    lh(left, 26, 0, [(m("D", 2), 4)], 0.62, "marc")
    lh(left, 26, 0, [(m("Eb", 2), 2), (m("D", 2), 2)], 0.40, "marc")

    # --- 28-29  everything drops to bare fifths; the hush comes after the peak
    for b in (27, 28):
        lh(left, b, 0, [(m("D", 2), 4)], 0.22, "ten")
        lh(left, b, 0, [(m("A", 2), 4)], 0.17, "ten")
        line(mel, b, 0, [(0, 4)], 1, 0.24, "ten")

    # --- 30-32  hammered octaves, crescendo, cut on a cluster
    for j, b in enumerate((29, 30, 31)):
        v = 0.55 + 0.13 * j
        for i in range(8):
            line(mel, b, i * 0.5, [(0, 0.45)], 1, v, "marc")
            line(cnt, b, i * 0.5, [(0, 0.45)], 0, v - 0.10, "marc")
        lh(left, b, 0, [(m("D", 2), 0.5)] * 8, min(0.95, v + 0.08), "marc")
    # last bar: D + E flat + A, struck once and left to ring
    for midi, vel in ((m("D", 2), 0.95), (m("D", 3), 0.88), (m("Eb", 3), 0.82), (m("A", 3), 0.76)):
        lh(left, 31, 0, [(midi, 4)], vel, "marc")

    return {
        "title": "铁 轨", "titleEn": "Tracks", "subtitle": "D  DORIAN   ·   126  BPM   ·   SOLO  PIANO",
        "key": "D", "mode": "dorian", "meter": [4, 4], "bpm": 126, "snap": False,
        "pattern": "none", "voicing": "lead", "ending": "cut", "tail": 0.9,
        "sections": [
            {"name": "A", "bars": [0, 8], "pattern": "none", "dynamic": 0.72, "texture": "cell"},
            {"name": "B", "bars": [8, 11], "pattern": "none", "dynamic": 0.78, "texture": "tritone",
             "key": "Ab", "mode": "major"},
            {"name": "L1", "bars": [11, 13], "pattern": "none", "dynamic": 0.84, "texture": "walk"},
            {"name": "C", "bars": [13, 19], "pattern": "none", "dynamic": 0.90, "texture": "canon"},
            {"name": "L2", "bars": [19, 21], "pattern": "none", "dynamic": 0.94, "texture": "unison"},
            {"name": "D", "bars": [21, 27], "pattern": "none", "dynamic": 1.00, "texture": "double-canon"},
            {"name": "L3", "bars": [27, 29], "pattern": "none", "dynamic": 0.55, "texture": "fifths"},
            {"name": "Coda", "bars": [29, 32], "pattern": "none", "dynamic": 1.00, "texture": "hammer"},
        ],
        "chords": (["Dm9"] * 4 + ["Dm9", "Gm9", "Dm9", "Eb7"] +      # 1-8
                   ["Abmaj7", "Dbmaj7", "Abmaj7"] +                  # 9-11 A flat
                   ["Bbm7", "A7"] +                                  # 12-13 link
                   ["Dm9", "Gm9", "Dm9", "Bbmaj7", "Gm9", "A7b9"] +  # 14-19 canon
                   ["Dm9", "Dm9"] +                                  # 20-21 collapse
                   ["Bbmaj7", "Eb9", "Dm9", "Abmaj7", "G7b9", "Dm9"] +  # 22-27
                   ["D5", "D5"] +                                    # 28-29 fifths
                   ["Dm9", "Dm9", "Dm9"]),                           # 30-32
        "bassLine": (["D2"] * 4 + ["D2", "G1", "D2", "Eb2"] +
                     ["D2", "Db2", "D2"] + ["Bb1", "A1"] +
                     ["D2", "G1", "D2", "Bb1", "G1", "A1"] +
                     ["D2", "D2"] +
                     ["Bb1", "Eb2", "D2", "Ab1", "G1", "D2"] +
                     ["D2", "D2"] + ["D2", "D2", "D2"]),
        "melody": mel, "counter": cnt, "left": left,
        "motif": [0, 2, 1, 3],
        "motifForms": {"P": [2, 4, 5, 8, 13, 14, 21, 22], "I": [18],
                       "R": [15], "RI": [16], "aug": [10, 26]},
        "expression": {
            "dyn": dyn([[0, 0.34], [3, 0.42], [6, 0.55], [8, 0.62], [10, 0.68],
                        [12, 0.60], [13, 0.66], [18, 0.78], [19, 0.86], [21, 0.95],
                        [26, 0.98], [27, 0.30], [29, 0.55], [31, 1.00]]),
            "pedal": [p for p in pedal_all(N) if p[0] not in (27, 28)],
            "marks": [
                {"bar": 0, "beat": 0, "type": "dyn", "text": "p"},
                {"bar": 2, "beat": 0, "type": "words", "text": "sempre staccato"},
                {"bar": 4, "beat": 0, "type": "wedge", "text": "cresc"},
                {"bar": 6, "beat": 0, "type": "dyn", "text": "mf"},
                {"bar": 8, "beat": 0, "type": "tempo", "text": "Meno mosso", "bpm": 112},
                {"bar": 8, "beat": 0, "type": "words", "text": "come di lontano"},
                {"bar": 10, "beat": 0, "type": "wedge", "text": "dim"},
                {"bar": 11, "beat": 0, "type": "tempo", "text": "Tempo I", "bpm": 126},
                {"bar": 11, "beat": 0, "type": "wedge", "text": "cresc"},
                {"bar": 13, "beat": 0, "type": "dyn", "text": "f"},
                {"bar": 13, "beat": 0, "type": "words", "text": "a due, stretto"},
                {"bar": 19, "beat": 0, "type": "wedge", "text": "cresc"},
                {"bar": 21, "beat": 0, "type": "dyn", "text": "ff"},
                {"bar": 21, "beat": 0, "type": "words", "text": "contrario motu"},
                {"bar": 27, "beat": 0, "type": "dyn", "text": "pp"},
                {"bar": 27, "beat": 0, "type": "words", "text": "senza pedale"},
                {"bar": 29, "beat": 0, "type": "dyn", "text": "f"},
                {"bar": 29, "beat": 0, "type": "words", "text": "martellato"},
                {"bar": 30, "beat": 0, "type": "wedge", "text": "cresc"},
                {"bar": 31, "beat": 0, "type": "dyn", "text": "fff"},
            ],
        },
    }


# ---------------------------------------------------------------------------
def validate(d, name):
    bpb = d["meter"][0] * 4.0 / d["meter"][1]
    n = len(d["chords"])
    bad = []
    for key in ("melody", "counter"):
        for row in d.get(key) or []:
            bar, beat, dur = row[0], row[1], row[2]
            if beat < 0 or beat + dur > bpb + 1e-6:
                bad.append((key, bar, beat, dur))
    for row in d.get("left") or []:
        bar, beat, dur = row[0], row[1], row[2]
        if beat < 0 or beat + dur > bpb + 1e-6:
            bad.append(("left", bar, beat, dur))
    for s in d["sections"]:
        if s["bars"][1] > n:
            bad.append(("section", s["name"], s["bars"]))
    if len(d.get("bassLine") or []) not in (0, n):
        bad.append(("bassLine", len(d.get("bassLine") or []), n))
    print(f"{name}: {n} bars, mel {len(d['melody'])}, cnt {len(d.get('counter') or [])}, "
          f"left {len(d.get('left') or [])}, problems {len(bad)}")
    for b in bad[:8]:
        print("   !", b)
    return not bad


def write(d, name):
    validate(d, name)
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print("wrote", path)




# ---------------------------------------------------------------------------
# 2. 三月的信 — F minor, 84 BPM, 3/4, 34 bars.
#    The climax is at bar 11, not at three quarters; the piece then unwinds for
#    twenty bars and ends in A minor, a major third away from where it started.
# ---------------------------------------------------------------------------
def waltz_bar(left, bar, bass, chord, vel, dyn=1.0):
    lh(left, bar, 0, [(bass, 1.0)], vel * dyn, "ten")
    for b in (1, 2):
        for i, mi in enumerate(chord):
            lh(left, bar, b, [(mi, 0.85)], vel * dyn * (0.72 + 0.04 * i))


def letter():
    N = 34
    mel, cnt, left = [], [], []
    P = [(0, 1.0), (4, 1.0), (3, 0.5), (2, 0.5)]          # F C Bb Ab
    Q = [(0, 0.5), (4, 0.5), (3, 0.5)]                    # compressed, 1.5 beats

    # --- 1-7  A: the letter is read once, plainly
    prog = [  # bar, bass midi, upper chord, melody transpose, vel
        (0, m("F", 2), [m("C", 4), m("Eb", 4), m("Ab", 4)], 0, 0.40),
        (1, m("Eb", 2), [m("Bb", 3), m("Db", 4), m("G", 4)], 1, 0.42),
        (2, m("Db", 2), [m("Ab", 3), m("C", 4), m("F", 4)], 2, 0.44),
        (3, m("C", 2), [m("G", 3), m("Bb", 3), m("E", 4)], 3, 0.46),
        (4, m("F", 2), [m("C", 4), m("Eb", 4), m("Ab", 4)], 0, 0.48),
        (5, m("Bb", 1), [m("F", 3), m("Ab", 3), m("D", 4)], 2, 0.50),
        (6, m("C", 2), [m("G", 3), m("Bb", 3), m("E", 4)], 3, 0.52),
    ]
    for bar, bass, ch, k, v in prog:
        waltz_bar(left, bar, bass, ch, v)
        line(mel, bar, 0, tr(P, k), 1, v + 0.12, "ten")
    # the counter enters on the second phrase and moves against the tune:
    # long notes falling while the melody climbs
    for bar, seq, v in ((3, [(4, 2.0), (2, 1.0)], 0.38),
                        (4, [(3, 1.5), (1, 1.5)], 0.40),
                        (5, [(2, 2.0), (0, 1.0)], 0.42),
                        (6, [(3, 1.5), (4, 1.5)], 0.44)):
        line(cnt, bar, 0, seq, 0, v, "ten")

    # --- 8-9  L1: the tail is repeated, the harmony slides to D flat
    for bar, bass, ch in ((7, m("Db", 2), [m("Ab", 3), m("C", 4), m("F", 4)]),
                          (8, m("Db", 2), [m("Ab", 3), m("Db", 4), m("F", 4)])):
        waltz_bar(left, bar, bass, ch, 0.50)
        line(mel, bar, 0, [(2, 1.0), (3, 0.5), (2, 0.5), (0, 1.0)], 1, 0.52, "ten")

    # --- 10-15  B: B minor, a tritone from F.  The climax is here, at bar 11.
    bmin = [(9, m("B", 2), [m("F#", 3), m("A", 3), m("D", 4)], 0.62),
            (10, m("G", 2), [m("D", 3), m("F#", 3), m("B", 3)], 0.74),
            (11, m("F#", 2), [m("C#", 4), m("E", 4), m("A", 4)], 0.84),
            (12, m("B", 2), [m("F#", 3), m("A", 3), m("D", 4)], 0.78),
            (13, m("D", 2), [m("A", 3), m("C#", 4), m("F#", 4)], 0.70),
            (14, m("F#", 2), [m("C#", 4), m("E", 4), m("A", 4)], 0.62)]
    for i, (bar, bass, ch, v) in enumerate(bmin):
        waltz_bar(left, bar, bass, ch, v)
        line(mel, bar, 0, tr(P, 0), 1, v + 0.10, "marc")
        # the lower voice holds and falls; it never doubles the tune
        k = [6, 5, 4, 3, 5, 4][i]
        line(cnt, bar, 0, [(k, 2.0), (k - 2, 1.0)], 0, v - 0.08, "ten")
    # bars 11-12 double the melody in octaves and add the counter in tenths
    for bar in (11, 12):
        line(cnt, bar, 0, inv(P, 4), 0, 0.72, "marc")
        lh(left, bar, 0, [(m("B", 1), 3)], 0.70, "marc")

    # --- 16-17  L2: the climax dissolves onto F#, which is also Gb
    for bar, bass, ch in ((15, m("F#", 2), [m("C#", 4), m("E", 4), m("A", 4)]),
                          (16, m("F#", 2), [m("C#", 4), m("F#", 4), m("A", 4)])):
        waltz_bar(left, bar, bass, ch, 0.46)
        # the last echo turns the tune upside down before it disappears
        line(mel, bar, 0, inv(P, 2) if bar == 16 else [(0, 3.0)], 1, 0.40, "ten")
        line(cnt, bar, 1.5, [(4, 1.5)], 0, 0.34, "ten")

    # --- 18-23  C: D flat major, canon at the fifth, inversion in the answer
    db = [(17, m("Db", 2), [m("Ab", 3), m("Db", 4), m("F", 4)]),
          (18, m("Ab", 2), [m("Eb", 3), m("Ab", 3), m("C", 4)]),
          (19, m("Gb", 2), [m("Db", 3), m("Gb", 3), [m("Bb", 3)][0]]),
          (20, m("Db", 2), [m("Ab", 3), m("Db", 4), m("F", 4)]),
          (21, m("Bb", 1), [m("F", 3), m("Bb", 3), m("Db", 4)]),
          (22, m("Ab", 2), [m("Eb", 3), m("Ab", 3), m("C", 4)])]
    for i, (bar, bass, ch) in enumerate(db):
        waltz_bar(left, bar, bass, ch, 0.42)
        if i % 2 == 0:
            line(cnt, bar, 0, tr(Q, i), 0, 0.40, "ten")
            line(mel, bar, 1.5, tr(Q, i), 1, 0.48, "ten")
        elif i == 3:
            # one full statement in inversion, not the compressed cell
            line(cnt, bar, 0, inv(tr(P, 0), 3), 0, 0.42, "ten")
        else:
            line(cnt, bar, 0, inv(tr(Q, i), 3), 0, 0.40, "ten")
            line(mel, bar, 1.5, inv(tr(Q, i), 3), 1, 0.48, "ten")

    # --- 24-29  A': the tune moves into the left hand, the right answers it
    a2 = [(23, m("F", 2), 0.38), (24, m("Eb", 2), 0.40), (25, m("Db", 2), 0.42),
          (26, m("C", 2), 0.44), (27, m("F", 2), 0.44), (28, m("Bb", 1), 0.42)]
    for bar, bass, v in a2:
        lh(left, bar, 0, [(bass, 1.0)], v, "ten")
        # the melody in the tenor, phrased as written pitches
        deg = tr(P, 0)
        t = 0.0
        for d, du in deg:
            pitch = 12 * 4 + PC["F"] + [0, 2, 3, 5, 7, 8, 10][d % 7] + 12 * (d // 7)
            lh(left, bar, t, [(pitch, du * 0.95)], v + 0.10, "ten")
            t += du
        # obbligato: the inversion, in sixteenths, above
        for j in range(6):
            k = [0, 2, 1, 3, 2, 0][j]
            line(mel, bar, j * 0.5, [(6 - (k % 4), 0.4)], 1, v * 0.9, "stacc")
        # waltz chord on 2 and 3, thin
        for b in (1, 2):
            lh(left, bar, b, [(bass + 7, 0.8)], v * 0.55)

    # --- 30-31  L3: to A minor by way of E7
    for bar, bass, ch in ((29, m("E", 2), [m("B", 3), m("D", 4), m("G#", 4)]),
                          (30, m("E", 2), [m("B", 3), m("D", 4), m("G#", 4)])):
        waltz_bar(left, bar, bass, ch, 0.36)
        line(cnt, bar, 0, [(6, 3.0)], 0, 0.30, "ten")

    # --- 32-35  Coda in A minor: one note, thinning, no fade
    for i, bar in enumerate((31, 32, 33)):
        lh(left, bar, 0, [(m("A", 2), 3)], 0.34 - 0.05 * i, "ten")
        for b in (0, 1, 2):
            line(mel, bar, b, [(0, 0.9)], 1, 0.40 - 0.05 * i, "ten" if i == 0 else "stacc")
    lh(left, 33, 0, [(m("A", 2), 3)], 0.24, "ten")

    for row in mel:                        # an intimate register, not a soprano
        row[4] -= 1
    for row in mel + cnt:                  # no marcato in a letter
        if len(row) > 7 and row[7] == "marc":
            row[7] = "ten"

    return {
        "title": "三 月 的 信", "titleEn": "A Letter in March",
        "subtitle": "F  MINOR   ·   84  BPM   ·   SOLO  PIANO",
        "key": "F", "mode": "minor", "meter": [3, 4], "bpm": 84, "snap": False,
        "pattern": "none", "voicing": "lead", "ending": "cut", "tail": 1.0,
        "sections": [
            {"name": "A", "bars": [0, 7], "pattern": "none", "dynamic": 0.74, "texture": "waltz"},
            {"name": "L1", "bars": [7, 9], "pattern": "none", "dynamic": 0.80, "texture": "echo"},
            {"name": "B", "bars": [9, 15], "pattern": "none", "dynamic": 0.92, "texture": "tritone",
             "key": "B", "mode": "minor"},
            {"name": "L2", "bars": [15, 17], "pattern": "none", "dynamic": 0.66, "texture": "dissolve"},
            {"name": "C", "bars": [17, 23], "pattern": "none", "dynamic": 0.78, "texture": "canon",
             "key": "Db", "mode": "major"},
            {"name": "A'", "bars": [23, 29], "pattern": "none", "dynamic": 0.72, "texture": "inverted-hands"},
            {"name": "L3", "bars": [29, 31], "pattern": "none", "dynamic": 0.60, "texture": "pedal"},
            {"name": "Coda", "bars": [31, 34], "pattern": "none", "dynamic": 0.52, "texture": "single-note",
             "key": "A", "mode": "minor"},
        ],
        "chords": (["Fm9", "Ebmaj7", "Dbmaj7", "C7b9", "Fm9", "Bbm7", "C7b9"] +
                   ["Dbmaj7", "Dbmaj7"] +
                   ["Bm9", "Gmaj7", "F#7", "Bm9", "Dmaj7", "F#7"] +
                   ["F#m7", "F#m7"] +
                   ["Dbmaj7", "Abmaj7", "Gbmaj7", "Dbmaj7", "Bbm7", "Abmaj7"] +
                   ["Fm9", "Ebmaj7", "Dbmaj7", "C7b9", "Fm9", "Bbm7"] +
                   ["E7", "E7"] +
                   ["Am9", "Am9", "Am9"]),
        "bassLine": (["F2", "Eb2", "Db2", "C2", "F2", "Bb1", "C2"] +
                     ["Db2", "Db2"] +
                     ["B1", "G1", "F#1", "B1", "D2", "F#1"] +
                     ["F#1", "F#1"] +
                     ["Db2", "Ab1", "Gb1", "Db2", "Bb1", "Ab1"] +
                     ["F2", "Eb2", "Db2", "C2", "F2", "Bb1"] +
                     ["E2", "E2"] +
                     ["A1", "A1", "A1"]),
        "melody": mel, "counter": cnt, "left": left,
        "motif": [0, 4, 3, 2],
        "motifForms": {"P": [0, 1, 2, 3, 4, 5, 9, 10, 24],
                       "I": [11, 19, 21], "R": [], "RI": [], "aug": [31]},
        "expression": {
            "dyn": dyn([[0, 0.36], [4, 0.44], [7, 0.50], [9, 0.58], [11, 0.86],
                        [13, 0.72], [15, 0.50], [17, 0.52], [22, 0.56], [23, 0.54],
                        [28, 0.44], [31, 0.30], [33, 0.22]]),
            "pedal": pedal_all(N, 3.0),
            "marks": [
                {"bar": 0, "beat": 0, "type": "dyn", "text": "p"},
                {"bar": 0, "beat": 0, "type": "words", "text": "una lettera, piano"},
                {"bar": 4, "beat": 0, "type": "wedge", "text": "cresc"},
                {"bar": 7, "beat": 0, "type": "dyn", "text": "mp"},
                {"bar": 9, "beat": 0, "type": "tempo", "text": "Più mosso", "bpm": 92},
                {"bar": 9, "beat": 0, "type": "words", "text": "come un'altra voce"},
                {"bar": 11, "beat": 0, "type": "dyn", "text": "ff"},
                {"bar": 13, "beat": 0, "type": "wedge", "text": "dim"},
                {"bar": 15, "beat": 0, "type": "dyn", "text": "p"},
                {"bar": 17, "beat": 0, "type": "tempo", "text": "Tempo I", "bpm": 84},
                {"bar": 17, "beat": 0, "type": "words", "text": "senza espansione"},
                {"bar": 23, "beat": 0, "type": "words", "text": "la melodia al basso"},
                {"bar": 29, "beat": 0, "type": "wedge", "text": "dim"},
                {"bar": 31, "beat": 0, "type": "dyn", "text": "pp"},
                {"bar": 31, "beat": 0, "type": "words", "text": "una sola nota"},
            ],
        },
    }



# ---------------------------------------------------------------------------
# 3. 铜与霜 — C minor, 66 BPM, 36 bars.
#    Sonata shape: exposition, a second subject a tritone away, a fugato
#    development, a recapitulation whose left hand takes the inversion, and a
#    coda that lands on E major — a chromatic mediant, fortissimo, no fade.
# ---------------------------------------------------------------------------
SCALES = {"minor": [0, 2, 3, 5, 7, 8, 10], "major": [0, 2, 4, 5, 7, 9, 11],
          "dorian": [0, 2, 3, 5, 7, 9, 10], "harmonic_minor": [0, 2, 3, 5, 7, 8, 11]}


def dm(key, mode, deg, octv):
    sc = SCALES[mode]
    return 12 * (octv + 1) + PC[key] + sc[deg % 7] + 12 * (deg // 7)


def brass():
    N = 36
    mel, cnt, left = [], [], []
    P = [(4, 1.5), (5, 0.5), (4, 1.0), (2, 1.0)]        # G Ab G Eb

    # --- 1-3  bare fifths, the call heard once without harmony
    for b in range(3):
        lh(left, b, 0, [(m("C", 2), 4)], 0.40 + 0.04 * b, "ten")
        lh(left, b, 0, [(m("G", 2), 4)], 0.28, "ten")
    line(cnt, 0, 0, P, 0, 0.34, "ten")
    line(mel, 2, 0, P, 1, 0.44, "marc")

    # --- 4-11  A: the theme, left hand in tenths, counter from bar 8
    theme = [(3, 0, 0, 0.50), (4, 0, 0, 0.52), (5, 0, 2, 0.54), (6, 0, 2, 0.56),
             (7, 0, 0, 0.58), (8, 0, 4, 0.62), (9, 0, 4, 0.64), (10, 0, 3, 0.68)]
    for bar, t0, k, v in theme:
        line(mel, bar, t0, tr(P, k), 1, v, "marc")
        lh(left, bar, 0, [(m("C", 2), 4)], v * 0.62, "ten")
        lh(left, bar, 0, [(m("G", 3), 4)], v * 0.40, "ten")
        lh(left, bar, 2, [(m("Eb", 3), 2)], v * 0.34, "ten")
    line(cnt, 7, 0, tr(P, 0), 0, 0.44, "ten")            # countersubject enters
    line(cnt, 8, 0, inv(tr(P, 0), 4), 0, 0.46, "ten")
    line(cnt, 9, 0, tr(P, 2), 0, 0.48, "ten")
    line(cnt, 10, 0, inv(tr(P, 3), 4), 0, 0.50, "ten")

    # --- 12-13  transition: a sequence up a minor third, into E flat minor
    for bar, key, k, v in ((11, "Eb", 0, 0.66), (12, "Eb", 2, 0.70)):
        line(mel, bar, 0, tr(P, k), 1, v, "marc")
        line(cnt, bar, 0, inv(tr(P, k), 4), 0, v - 0.10, "ten")
        lh(left, bar, 0, [(dm(key, "minor", 0, 2), 4)], v * 0.60, "ten")
        lh(left, bar, 0, [(dm(key, "minor", 4, 3), 4)], v * 0.38, "ten")

    # --- 14-19  B: F sharp minor, the second subject, tritone away from C
    subj2 = [(0, 1.5), (4, 0.5), (2, 1.0), (1, 1.0)]     # F# C# D# B? kept as shape
    for i, bar in enumerate(range(13, 19)):
        k = [0, 0, 2, 0, 3, 2][i]
        v = 0.62 + 0.03 * i
        line(mel, bar, 0, tr(subj2, k), 1, v, "ten")
        line(cnt, bar, 0, inv(tr(subj2, k), 3), 0, v - 0.12, "ten")
        lh(left, bar, 0, [(dm("F#", "minor", 0, 1), 2)], v * 0.62, "ten")
        lh(left, bar, 2, [(dm("F#", "minor", 4, 1), 2)], v * 0.44, "ten")
        lh(left, bar, 0, [(dm("F#", "minor", 2, 2), 4)], v * 0.30, "ten")

    # --- 20-21  L1: chromatic pivot F# -> G -> Ab, ending on A flat major
    lh(left, 19, 0, [(m("F#", 1), 1), (m("G", 1), 1), (m("Ab", 1), 1), (m("A", 1), 1)], 0.56, "marc")
    lh(left, 20, 0, [(m("Ab", 1), 4)], 0.46, "ten")
    line(mel, 19, 0, [(3, 1.0), (2, 1.0), (1, 1.0), (0, 1.0)], 1, 0.58, "marc")
    line(mel, 20, 0, stretch(tr(P, 0), 1.0), 1, 0.52, "ten")

    # --- 22-28  fugato: subject in the left hand, answer in the right,
    # then a third entry; the climax is two lines in contrary motion
    line(left, 21, 0, [(dm("Ab", "major", 4, 1), 1.5), (dm("Ab", "major", 5, 1), 0.5),
                       (dm("Ab", "major", 4, 1), 1.0), (dm("Ab", "major", 2, 1), 1.0)], 0.56, "ten")
    line(mel, 22, 0, [(4, 1.5), (5, 0.5), (4, 1.0), (2, 1.0)], 1, 0.62, "marc")
    line(left, 23, 0, [(dm("Ab", "major", 0, 1), 1.5), (dm("Ab", "major", 1, 1), 0.5),
                       (dm("Ab", "major", 0, 1), 1.0), (dm("Ab", "major", 5, 1), 1.0)], 0.60, "ten")
    line(mel, 24, 0, [(1, 1.5), (2, 0.5), (1, 1.0), (6, 1.0)], 1, 0.66, "marc")
    line(left, 24, 2, [(dm("Ab", "major", 6, 1), 2.0)], 0.54, "ten")
    for bar in (25, 26, 27):
        line(mel, bar, 0, tr(P, 0), 1, 0.86, "marc")
        line(cnt, bar, 0, inv(P, 4), 0, 0.80, "marc")
        lh(left, bar, 0, [(dm("Ab", "major", 0, 1), 4)], 0.70, "marc")
        lh(left, bar, 0, [(dm("Ab", "major", 4, 2), 4)], 0.48, "marc")
    line(mel, 27, 0, [(4, 2.0), (5, 2.0)], 1, 0.90, "marc")
    line(cnt, 27, 0, [(4, 2.0), (2, 2.0)], 0, 0.82, "marc")

    # --- 29-30  L2: everything falls away except one line, augmented
    for bar in (28, 29):
        line(cnt, bar, 0, [(4, 4.0)], 0, 0.36, "ten")
        lh(left, bar, 0, [(m("C", 2), 4)], 0.30, "ten")

    # --- 31-34  recapitulation: theme in the right hand, its inversion below
    for i, bar in enumerate(range(30, 34)):
        k = [0, 0, 2, 3][i]
        v = 0.66 + 0.02 * i
        line(mel, bar, 0, tr(P, k), 1, v, "marc")
        line(left, bar, 0, [(dm("C", "minor", 6 - (k % 4), 2), 1.5),
                            (dm("C", "minor", 5 - (k % 3), 2), 0.5),
                            (dm("C", "minor", 4 - (k % 3), 2), 2.0)], v * 0.70, "ten")
        lh(left, bar, 0, [(m("C", 2), 4)], v * 0.55, "ten")

    # --- 35-36  coda: C minor slides to E major and stops there, loud
    lh(left, 34, 0, [(m("C", 2), 1), (m("B", 1), 1), (m("A", 1), 1), (m("G#", 1), 1)], 0.72, "marc")
    for i, bar in enumerate((34, 35)):
        for j, (pitch, vel) in enumerate(((m("E", 1), 0.90), (m("B", 1), 0.84),
                                          (m("E", 2), 0.88), (m("G#", 2), 0.80))):
            lh(left, bar, 0 if j < 2 else 2, [(pitch, 2.0 if j < 2 else 2.0)], vel, "marc")
        line(mel, bar, 0, [(4, 2.0), (2, 2.0)], 1, 0.92, "marc")
        line(cnt, bar, 0, [(0, 2.0), (4, 2.0)], 1, 0.86, "marc")

    for row in mel:                        # keep the accent for the downbeat
        if len(row) > 7 and row[7] == "marc" and float(row[1]) != 0:
            row[7] = ""

    return {
        "title": "铜 与 霜", "titleEn": "Brass and Frost",
        "subtitle": "C  MINOR   ·   66  BPM   ·   SOLO  PIANO",
        "key": "C", "mode": "minor", "meter": [4, 4], "bpm": 66, "snap": False,
        "pattern": "none", "voicing": "lead", "ending": "ring", "tail": 5.0,
        "sections": [
            {"name": "Intro", "bars": [0, 3], "pattern": "none", "dynamic": 0.62, "texture": "fifths"},
            {"name": "A", "bars": [3, 11], "pattern": "none", "dynamic": 0.78, "texture": "tenths"},
            {"name": "T", "bars": [11, 13], "pattern": "none", "dynamic": 0.82, "texture": "sequence",
             "key": "Eb", "mode": "minor"},
            {"name": "B", "bars": [13, 19], "pattern": "none", "dynamic": 0.86, "texture": "subject2",
             "key": "F#", "mode": "minor"},
            {"name": "L1", "bars": [19, 21], "pattern": "none", "dynamic": 0.72, "texture": "sequence"},
            {"name": "Dev", "bars": [21, 28], "pattern": "none", "dynamic": 0.96, "texture": "fugato",
             "key": "Ab", "mode": "major"},
            {"name": "L2", "bars": [28, 30], "pattern": "none", "dynamic": 0.50, "texture": "bare"},
            {"name": "A'", "bars": [30, 34], "pattern": "none", "dynamic": 0.80, "texture": "inversion"},
            {"name": "Coda", "bars": [34, 36], "pattern": "none", "dynamic": 1.00, "texture": "mediant",
             "key": "E", "mode": "major"},
        ],
        "chords": (["C5", "C5", "C5"] +
                   ["Cm9", "Cm9", "Abmaj7", "Fm9", "Cm9", "G7b9", "Cm9", "Bdim7"] +
                   ["Ebm9", "Bb7"] +
                   ["F#m9", "Bm7", "C#7b9", "F#m9", "Dmaj7", "C#7b9"] +
                   ["F#dim7", "Abmaj7"] +
                   ["Abmaj7", "Ebmaj7", "Bb7", "Abmaj7", "D7", "G7b9", "Cm9"] +
                   ["Cm9", "Cm9"] +
                   ["Cm9", "Abmaj7", "Fm9", "G7b9"] +
                   ["E", "E"]),
        "bassLine": (["C2", "C2", "C2"] +
                     ["C2", "C2", "Ab1", "F1", "C2", "G1", "C2", "B1"] +
                     ["Eb2", "Bb1"] +
                     ["F#1", "B1", "C#2", "F#1", "D2", "C#2"] +
                     ["F#1", "Ab1"] +
                     ["Ab1", "Eb2", "Bb1", "Ab1", "D2", "G1", "C2"] +
                     ["C2", "C2"] +
                     ["C2", "Ab1", "F1", "G1"] +
                     ["E1", "E1"]),
        "melody": mel, "counter": cnt, "left": left,
        "motif": [4, 5, 4, 2],
        "motifForms": {"P": [0, 2, 3, 11, 21, 30], "I": [7, 9, 22, 26],
                       "R": [24], "RI": [23], "aug": [20, 28]},
        "expression": {
            "dyn": dyn([[0, 0.40], [3, 0.52], [6, 0.60], [9, 0.66], [11, 0.72],
                        [13, 0.64], [15, 0.72], [19, 0.44], [21, 0.60], [25, 0.84],
                        [27, 0.98], [28, 0.34], [30, 0.66], [33, 0.74], [34, 1.00]]),
            "pedal": pedal_all(N),
            "marks": [
                {"bar": 0, "beat": 0, "type": "dyn", "text": "pp"},
                {"bar": 0, "beat": 0, "type": "words", "text": "come un corno lontano"},
                {"bar": 3, "beat": 0, "type": "dyn", "text": "mp"},
                {"bar": 3, "beat": 0, "type": "words", "text": "pesante"},
                {"bar": 7, "beat": 0, "type": "wedge", "text": "cresc"},
                {"bar": 11, "beat": 0, "type": "tempo", "text": "Più mosso", "bpm": 72},
                {"bar": 11, "beat": 0, "type": "dyn", "text": "mf"},
                {"bar": 13, "beat": 0, "type": "words", "text": "freddo, lontanissimo"},
                {"bar": 19, "beat": 0, "type": "wedge", "text": "dim"},
                {"bar": 21, "beat": 0, "type": "tempo", "text": "Meno mosso", "bpm": 60},
                {"bar": 21, "beat": 0, "type": "words", "text": "fugato"},
                {"bar": 25, "beat": 0, "type": "wedge", "text": "cresc"},
                {"bar": 27, "beat": 0, "type": "dyn", "text": "fff"},
                {"bar": 28, "beat": 0, "type": "dyn", "text": "p"},
                {"bar": 28, "beat": 0, "type": "words", "text": "solo, senza colore"},
                {"bar": 30, "beat": 0, "type": "tempo", "text": "Tempo I", "bpm": 66},
                {"bar": 34, "beat": 0, "type": "dyn", "text": "ff"},
                {"bar": 34, "beat": 0, "type": "words", "text": "come un metallo"},
            ],
        },
    }


PIECES = {"rework_1_tracks.json": tracks, "rework_2_letter.json": letter,
          "rework_3_brass.json": brass}


if __name__ == "__main__":
    import sys
    only = sys.argv[1:] or list(PIECES)
    for fn in only:
        write(PIECES[fn](), fn)
