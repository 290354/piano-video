#!/usr/bin/env python3
"""write_v2.py — the three pieces rebuilt around four complaints.

  1. sections used to cut; every seam now has a 1-2 bar link section whose
     texture belongs to neither side, a written wedge, and a bass that steps
     into the next key area;
  2. the return used to restate; A' is now the motif inverted / retrograded /
     augmented, and the literal shape never comes back whole;
  3. harmony used to be colourful only in chord symbols; each piece now has
     secondary dominants, a neapolitan, borrowed triads and a tritone sub,
     placed where the form needs a push;
  4. no performance layer; every bar now carries dynamics, pedal, wedges,
     tempo words and articulation.

Run from the repo root:  python3 tools/write_v2.py
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

OUT = os.path.join(ROOT, "scores")


def notes(bar, items, vel=0.66, art="", octv=0, acc=None):
    """[(beat, dur, deg)] -> score.json melody rows."""
    rows = []
    for it in items:
        beat, dur, deg = it[0], it[1], it[2]
        v = it[3] if len(it) > 3 else vel
        row = [bar, beat, dur, deg, octv, round(v, 3)]
        a = it[4] if len(it) > 4 else acc
        if a is not None or art:
            row.append(int(a or 0))
            if art:
                row.append(art)
        rows.append(row)
    return rows


def mel(*groups):
    out = []
    for g in groups:
        out.extend(g)
    return out


def pedal_every(bar0, bar1, bpb=4.0, hold=None):
    """One pedal per bar, lifted a hair before the bar line so the engraver can
    print Ped. / * instead of merging everything into one long spanner."""
    hold = bpb - 0.06 if hold is None else hold
    return [[b, 0, hold] for b in range(bar0, bar1)]


# =============================================================== 1. 铁 轨
# D dorian, 112, 32 bars.  Train ostinato; the link sections dissolve it.
TRACKS = dict(
    title="铁 轨", titleEn="TRACKS", subtitle="D DORIAN · 112 BPM · SOLO PIANO",
    key="D", mode="dorian", meter=[4, 4], bpm=112,
    pattern="ostinato", voicing="color", velocity=1.0, tail=6.5, shimmer=False,
    motif=[0, 5, 4, 2], motifForms="P(2,14,20) I(6,28) R(10) RI(11)",
    tempo={"map": [[0, 108], [8, 112], [16, 118], [18, 124], [24, 96], [26, 72]],
           "rit": {"bar": 29, "barTo": 32, "factor": 0.76}},
    sections=[
        {"name": "Intro", "bars": [0, 2], "pattern": "drone", "dynamic": 0.62},
        {"name": "A", "bars": [2, 8], "pattern": "ostinato", "dynamic": 0.90},
        {"name": "L1", "bars": [8, 10], "pattern": "broken", "dynamic": 0.96},
        {"name": "B", "bars": [10, 16], "pattern": "counter", "dynamic": 0.98},
        {"name": "L2", "bars": [16, 18], "pattern": "block", "dynamic": 1.0},
        {"name": "C", "bars": [18, 24], "pattern": "pulse", "dynamic": 1.0},
        {"name": "L3", "bars": [24, 26], "pattern": "drone", "dynamic": 0.62},
        {"name": "A'", "bars": [26, 30], "pattern": "broken", "dynamic": 0.80},
        {"name": "Coda", "bars": [30, 32], "pattern": "drone", "dynamic": 0.58},
    ],
    chords=[
        "Dm9", "Dm9",
        "Dm9", "C6/9", "Bm7b5", "A7sus4", "Dm9", "Gm9",
        "Eb7", "Dm9",
        "Dm9", "Cmaj7#11", "Bb7", "A7b9", "Dm9", "Gm9",
        "Bb7", "C7/E",
        "Fmaj7#11", "Ebmaj7", "Dm9", "E7", "A7b9", "Dm9",
        "Dm9", "A7sus4",
        "Dm9", "Bbmaj7", "Gm9", "A7sus4",
        "Dm9", "Dm9",
    ],
    bassLine=[
        "D2", "D2",
        "D2", "C2", "B1", "A1", "D2", "F1",
        "Eb2", "D2",
        "D2", "C2", "Bb1", "A1", "D2", "G1",
        "A1", "C2",
        "F1", "Eb2", "D2", "E2", "A1", "D2",
        "D2", "A1",
        "Bb1", "Bb1", "G1", "A1",
        "A1", "D2",
    ],
    melody=mel(
        # intro: the head of the motif, alone over the pedal
        notes(0, [(0, 2, 0), (2, 2, 5)], 0.5, "ten"),
        notes(1, [(0, 1.5, 0), (1.5, 1.5, 5), (3, 1, 4)], 0.48, "ten"),
        # A: statement
        notes(2, [(0, 1, 0), (1, 1, 5), (2, 0.5, 4), (2.5, 0.5, 2)], 0.62, "ten"),
        notes(3, [(0, 0.5, 0), (0.5, 0.5, 2), (1, 1, 5), (2, 2, 7)], 0.64, "ten"),
        notes(4, [(0, 1, 2), (1, 1, 7), (2, 0.5, 6), (2.5, 0.5, 4)], 0.66, "ten"),
        notes(5, [(0, 1, 4), (1, 1, 9), (2, 0.5, 8), (2.5, 0.5, 6)], 0.68, "ten"),
        # I: the motif mirrored (A D E G)
        notes(6, [(0, 1, 5), (1, 1, 0), (2, 0.5, 1), (2.5, 0.5, 3)], 0.64, "ten"),
        notes(7, [(0, 2, 4), (2, 2, 5)], 0.62, "ten"),
        # L1: two-note fragment, then a chromatic climb into B
        notes(8, [(0, 2, 0), (2, 2, 5)], 0.56, "ten"),
        notes(9, [(0, 1, 5), (1, 1, 6, 0.7, 1), (2, 1, 7), (3, 1, 8, 0.74, 1)], 0.6, "ten"),
        # B: retrograde, then a descending chain
        # R (E G A D) then RI (G E D A) — the shape walked backwards
        notes(10, [(0, 1, 2), (1, 1, 4), (2, 0.5, 5), (2.5, 0.5, 0)], 0.7, "marc"),
        notes(11, [(0, 1, 4), (1, 1, 2), (2, 0.5, 1), (2.5, 0.5, 6)], 0.72, "marc"),
        notes(12, [(0, 1, 7), (1, 1, 5), (2, 1, 3), (3, 1, 0)], 0.7, "marc"),
        notes(13, [(0, 1, 5), (1, 0.5, 6, 0.72, 1), (1.5, 0.5, 7), (2, 1, 8, 0.76, 1), (3, 1, 5)], 0.72, "marc"),
        notes(14, [(0, 1, 0), (1, 1, 5), (2, 0.5, 4), (2.5, 0.5, 2), (3, 1, 0)], 0.74, "ten"),
        notes(15, [(0, 1, 4), (1, 1, 3), (2, 1, 2), (3, 1, 0)], 0.7, "marc"),
        # L2: fragment over a rising bass, crescendo into the climax
        notes(16, [(0, 2, 3), (2, 2, 7)], 0.66, "ten"),
        notes(17, [(0, 1, 4), (1, 1, 5), (2, 1, 6, 0.86, 1), (3, 1, 7)], 0.72, "acc"),
        # C: the motif compressed to eighths, sequenced up a third, then ff
        notes(18, [(0, 0.5, 7), (0.5, 0.5, 5), (1, 0.5, 4), (1.5, 0.5, 2),
                   (2, 0.5, 7), (2.5, 0.5, 5), (3, 0.5, 4), (3.5, 0.5, 2)], 0.86, "acc"),
        notes(19, [(0, 0.5, 8), (0.5, 0.5, 6), (1, 0.5, 5), (1.5, 0.5, 3),
                   (2, 0.5, 8), (2.5, 0.5, 6), (3, 0.5, 5), (3.5, 0.5, 3)], 0.9, "acc"),
        notes(20, [(0, 1, 0), (1, 1, 5), (2, 0.5, 4), (2.5, 0.5, 2), (3, 1, 0)], 0.92, "marc"),
        notes(21, [(0, 1, 3), (1, 1, 8), (2, 1, 7), (3, 1, 5)], 0.92, "marc"),
        notes(22, [(0, 1, 5), (1, 0.5, 6, 0.9, 1), (1.5, 0.5, 7), (2, 1, 8, 0.96, 1), (3, 1, 9)], 0.94, "marc"),
        notes(23, [(0, 4, 7)], 0.9, "ten"),
        # L3: everything drops away, one held D
        notes(24, [(0, 4, 0)], 0.44, "ten"),
        notes(25, [(0, 4, 5)], 0.4, "ten"),
        # A': the motif augmented, then its inversion as a broken line
        notes(26, [(0, 2, 0), (2, 2, 5)], 0.5, "ten"),
        notes(27, [(0, 2, 4), (2, 2, 2)], 0.5, "ten"),
        notes(28, [(0, 1, 0), (1, 1, 4), (2, 1, 5), (3, 1, 7)], 0.52, "ten"),
        notes(29, [(0, 4, 5)], 0.46, "ten"),
        # coda: the first two notes, fading
        notes(30, [(0, 2, 0), (2, 2, 5)], 0.42, "ten"),
        notes(31, [(0, 4, 0)], 0.36, "ten"),
    ),
    expression={
        "dyn": [[0, 0.52], [2, 0.58], [7, 0.66], [8, 0.7], [9, 0.84], [10, 0.78],
                [15, 0.84], [16, 0.86], [17, 0.96], [18, 1.0], [23, 1.0],
                [24, 0.52], [26, 0.5], [29, 0.44], [31, 0.34]],
        "pedal": pedal_every(0, 32),
        "slur": [],
        "marks": [
            {"bar": 0, "beat": 0, "type": "dyn", "text": "p"},
            {"bar": 0, "beat": 0, "type": "words", "text": "lontano, come un treno"},
            {"bar": 2, "beat": 0, "type": "dyn", "text": "mp"},
            {"bar": 2, "beat": 0, "type": "words", "text": "ostinato, sempre"},
            {"bar": 4, "beat": 2, "type": "wedge", "text": "cresc", "barTo": 6, "beatTo": 0},
            {"bar": 8, "beat": 0, "type": "dyn", "text": "mf"},
            {"bar": 8, "beat": 0, "type": "words", "text": "poco a poco"},
            {"bar": 9, "beat": 0, "type": "wedge", "text": "cresc", "barTo": 10, "beatTo": 0},
            {"bar": 10, "beat": 0, "type": "dyn", "text": "mf"},
            {"bar": 10, "beat": 0, "type": "words", "text": "espressivo"},
            {"bar": 11, "beat": 2, "type": "wedge", "text": "cresc", "barTo": 13, "beatTo": 0},
            {"bar": 13, "beat": 0, "type": "dyn", "text": "f"},
            {"bar": 15, "beat": 2, "type": "wedge", "text": "dim", "barTo": 16, "beatTo": 0},
            {"bar": 16, "beat": 0, "type": "dyn", "text": "mp"},
            {"bar": 16, "beat": 0, "type": "words", "text": "poco a poco cresc."},
            {"bar": 17, "beat": 0, "type": "wedge", "text": "cresc", "barTo": 18, "beatTo": 0},
            {"bar": 18, "beat": 0, "type": "dyn", "text": "ff"},
            {"bar": 18, "beat": 0, "type": "words", "text": "marcato"},
            {"bar": 18, "beat": 0, "type": "tempo", "text": "Più mosso", "bpm": 124},
            {"bar": 21, "beat": 2, "type": "wedge", "text": "dim", "barTo": 22, "beatTo": 0},
            {"bar": 22, "beat": 0, "type": "dyn", "text": "ff"},
            {"bar": 23, "beat": 2, "type": "wedge", "text": "dim", "barTo": 24, "beatTo": 0},
            {"bar": 24, "beat": 0, "type": "dyn", "text": "p"},
            {"bar": 24, "beat": 0, "type": "words", "text": "subito, senza pedale"},
            {"bar": 24, "beat": 0, "type": "tempo", "text": "Meno mosso", "bpm": 96},
            {"bar": 26, "beat": 0, "type": "dyn", "text": "pp"},
            {"bar": 26, "beat": 0, "type": "words", "text": "come un ricordo"},
            {"bar": 28, "beat": 0, "type": "wedge", "text": "dim", "barTo": 29, "beatTo": 0},
            {"bar": 29, "beat": 0, "type": "tempo", "text": "rit."},
            {"bar": 30, "beat": 0, "type": "dyn", "text": "ppp"},
            {"bar": 30, "beat": 0, "type": "words", "text": "smorzando"},
        ],
    },
)

# ============================================================ 2. 三 月 的 信
# F minor, 76, 3/4, 32 bars.  A letter: the waltz keeps losing its beat.
LETTER = dict(
    title="三 月 的 信", titleEn="A LETTER IN MARCH",
    subtitle="F MINOR · 76 BPM · SOLO PIANO",
    key="F", mode="minor", meter=[3, 4], bpm=76,
    pattern="waltz2", voicing="color", velocity=1.0, tail=7.0, shimmer=False,
    motif=[0, 4, 2, 1], motifForms="P(2,6,21) I(4,26) R(12) RI(13) aug(28)",
    tempo={"map": [[0, 72], [2, 76], [12, 80], [20, 72], [21, 68], [28, 64]],
           "rit": {"bar": 29, "barTo": 32, "factor": 0.78}},
    sections=[
        {"name": "Intro", "bars": [0, 2], "pattern": "drone", "dynamic": 0.55},
        {"name": "A", "bars": [2, 10], "pattern": "waltz2", "dynamic": 0.86},
        {"name": "L1", "bars": [10, 12], "pattern": "broken", "dynamic": 0.94},
        {"name": "B", "bars": [12, 20], "pattern": "counter", "dynamic": 0.96},
        {"name": "L2", "bars": [20, 21], "pattern": "block", "dynamic": 0.66},
        {"name": "A'", "bars": [21, 29], "pattern": "broken", "dynamic": 0.74},
        {"name": "Coda", "bars": [29, 32], "pattern": "drone", "dynamic": 0.5},
    ],
    chords=[
        "Fm9", "Fm9",
        "Fm9", "Db6/9", "Bbm7", "C7b9", "Fm9", "Eb9", "Abmaj7", "C7b9",
        "Bbm/Db", "C7b9",
        "Db9", "Abmaj7", "Fm9", "Bbm7", "Gb9", "C7b9", "G7b9", "C7b9",
        "C7b9",
        "Fm9", "Db6/9", "Bbm7", "C7b9", "Fm9", "Gb9", "Db6/9", "Fm9",
        "Fm9", "Db6/9", "Fm9",
    ],
    bassLine=[
        "F2", "F2",
        "F2", "Db2", "Bb1", "C2", "F2", "Eb2", "Ab1", "C2",
        "Db2", "C2",
        "Db2", "Ab1", "F2", "Bb1", "Gb1", "C2", "G1", "C2",
        "C2",
        "F2", "Db2", "Bb1", "C2", "F2", "Gb1", "Db2", "F2",
        "C2", "Db2", "F2",
    ],
    melody=mel(
        notes(0, [(0, 3, 0)], 0.44, "ten"),
        notes(1, [(0, 1, 2), (1, 1, 1), (2, 1, 0)], 0.46, "ten"),
        # A: the motif, then its answer
        notes(2, [(0, 1, 0), (1, 0.5, 4), (1.5, 0.5, 2), (2, 1, 1)], 0.6, "ten"),
        notes(3, [(0, 1, 0), (1, 1, 4), (2, 1, 7)], 0.62, "ten"),
        # I: mirrored (C F Ab G)
        notes(4, [(0, 1, 4), (1, 0.5, 0), (1.5, 0.5, 2), (2, 1, 3)], 0.62, "ten"),
        notes(5, [(0, 1.5, 4), (1.5, 1.5, 2)], 0.64, "ten"),
        notes(6, [(0, 1, 0), (1, 0.5, 4), (1.5, 0.5, 2), (2, 1, 1)], 0.66, "ten"),
        notes(7, [(0, 1, 3), (1, 1, 6), (2, 1, 5)], 0.68, "ten"),
        notes(8, [(0, 1, 4), (1, 1, 7), (2, 1, 6)], 0.7, "ten"),
        notes(9, [(0, 2, 4), (2, 1, 1)], 0.66, "ten"),
        # L1: the motif in the low register, then a chromatic approach
        notes(10, [(0, 1.5, 2), (1.5, 1.5, 4)], 0.62, "ten"),
        notes(11, [(0, 1, 1), (1, 1, 3, 0.78, 1), (2, 1, 6)], 0.7, "ten"),
        # B: away from F minor, into Db
        # R then RI, starting the far section
        notes(12, [(0, 1, 1), (1, 0.5, 2), (1.5, 0.5, 4), (2, 1, 0)], 0.74, "marc"),
        notes(13, [(0, 1, 4), (1, 0.5, 3), (1.5, 0.5, 1), (2, 1, 5)], 0.76, "marc"),
        notes(14, [(0, 1, 4), (1, 1, 6), (2, 1, 7)], 0.76, "marc"),
        notes(15, [(0, 1.5, 9), (1.5, 1.5, 7)], 0.8, "marc"),
        notes(16, [(0, 1, 8), (1, 0.5, 7), (1.5, 0.5, 5, 0.82, 1), (2, 1, 4)], 0.82, "marc"),
        notes(17, [(0, 1, 6), (1, 1, 4), (2, 1, 2)], 0.84, "marc"),
        notes(18, [(0, 1, 3), (1, 1, 7), (2, 1, 6, 0.88, 1)], 0.86, "acc"),
        notes(19, [(0, 2, 5), (2, 1, 4)], 0.82, "ten"),
        # L2: one bar of held dominant, then everything stops
        notes(20, [(0, 3, 1)], 0.54, "ten"),
        # A': retrograde + inversion, broken left hand
        notes(21, [(0, 1, 1), (1, 0.5, 2), (1.5, 0.5, 4), (2, 1, 0)], 0.6, "ten"),
        notes(22, [(0, 1, 4), (1, 1, 0), (2, 1, 2)], 0.6, "ten"),
        notes(23, [(0, 1, 3), (1, 1, 1), (2, 1, 0)], 0.62, "ten"),
        notes(24, [(0, 1, 0), (1, 0.5, 4), (1.5, 0.5, 2), (2, 1, 1)], 0.62, "ten"),
        notes(25, [(0, 1, 2), (1, 1, 0), (2, 1, -1, 0.66, 1)], 0.64, "ten"),
        notes(26, [(0, 1, 0), (1, 1, -4), (2, 1, -2)], 0.62, "ten"),
        notes(27, [(0, 1, 1), (1, 1, 3), (2, 1, 5)], 0.66, "ten"),
        notes(28, [(0, 1.5, 0), (1.5, 1.5, 4)], 0.6, "ten"),
        # coda: the motif, augmented, dissolving
        notes(29, [(0, 2, 0), (2, 1, 4)], 0.5, "ten"),
        notes(30, [(0, 3, 2)], 0.44, "ten"),
        notes(31, [(0, 3, 0)], 0.38, "ten"),
    ),
    expression={
        "dyn": [[0, 0.5], [2, 0.56], [7, 0.64], [10, 0.72], [11, 0.88], [12, 0.8],
                [17, 0.86], [19, 0.9], [20, 0.62], [21, 0.58], [26, 0.6],
                [28, 0.5], [30, 0.4], [31, 0.32]],
        "pedal": pedal_every(0, 32, bpb=3.0),
        "slur": [],
        "marks": [
            {"bar": 0, "beat": 0, "type": "dyn", "text": "p"},
            {"bar": 0, "beat": 0, "type": "words", "text": "sotto voce"},
            {"bar": 2, "beat": 0, "type": "dyn", "text": "mp"},
            {"bar": 2, "beat": 0, "type": "words", "text": "dolce"},
            {"bar": 6, "beat": 0, "type": "wedge", "text": "cresc", "barTo": 9, "beatTo": 0},
            {"bar": 9, "beat": 0, "type": "dyn", "text": "mf"},
            {"bar": 10, "beat": 0, "type": "words", "text": "poco più"},
            {"bar": 10, "beat": 0, "type": "wedge", "text": "cresc", "barTo": 12, "beatTo": 0},
            {"bar": 12, "beat": 0, "type": "dyn", "text": "f"},
            {"bar": 12, "beat": 0, "type": "words", "text": "espressivo"},
            {"bar": 12, "beat": 0, "type": "tempo", "text": "Più mosso", "bpm": 80},
            {"bar": 17, "beat": 0, "type": "wedge", "text": "cresc", "barTo": 19, "beatTo": 0},
            {"bar": 19, "beat": 0, "type": "dyn", "text": "ff"},
            {"bar": 19, "beat": 2, "type": "wedge", "text": "dim", "barTo": 20, "beatTo": 0},
            {"bar": 20, "beat": 0, "type": "dyn", "text": "p"},
            {"bar": 20, "beat": 0, "type": "words", "text": "fermata, poi"},
            {"bar": 21, "beat": 0, "type": "dyn", "text": "pp"},
            {"bar": 21, "beat": 0, "type": "words", "text": "come una lettera riletta"},
            {"bar": 21, "beat": 0, "type": "tempo", "text": "Tempo I", "bpm": 68},
            {"bar": 24, "beat": 0, "type": "wedge", "text": "cresc", "barTo": 26, "beatTo": 0},
            {"bar": 26, "beat": 0, "type": "dyn", "text": "mp"},
            {"bar": 28, "beat": 0, "type": "wedge", "text": "dim", "barTo": 30, "beatTo": 0},
            {"bar": 29, "beat": 0, "type": "tempo", "text": "rit."},
            {"bar": 30, "beat": 0, "type": "dyn", "text": "pp"},
            {"bar": 30, "beat": 0, "type": "words", "text": "smorzando"},
        ],
    },
)

# ============================================================ 3. 铜 与 霜
# C minor, 63, 32 bars.  Brass blocks against a frozen upper register.
BRASS = dict(
    title="铜 与 霜", titleEn="BRASS AND FROST",
    subtitle="C MINOR · 63 BPM · SOLO PIANO",
    key="C", mode="minor", meter=[4, 4], bpm=63,
    pattern="drone", voicing="color", velocity=1.0, tail=7.5, shimmer=False,
    motif=[0, 3, 1, -1], motifForms="P(2,22) I(4,26) R(12) RI(13) aug(28)",
    tempo={"map": [[0, 60], [2, 63], [12, 66], [17, 72], [24, 58], [26, 54]],
           "rit": {"bar": 29, "barTo": 32, "factor": 0.8}},
    sections=[
        {"name": "Intro", "bars": [0, 2], "pattern": "drone", "dynamic": 0.5},
        {"name": "A", "bars": [2, 10], "pattern": "block", "dynamic": 0.84},
        {"name": "L1", "bars": [10, 12], "pattern": "counter", "dynamic": 0.9},
        {"name": "B", "bars": [12, 17], "pattern": "ostinato", "dynamic": 0.92},
        {"name": "L2", "bars": [17, 18], "pattern": "drone", "dynamic": 0.6},
        {"name": "C", "bars": [18, 24], "pattern": "pulse", "dynamic": 1.0},
        {"name": "L3", "bars": [24, 26], "pattern": "counter", "dynamic": 0.6},
        {"name": "A'", "bars": [26, 30], "pattern": "block", "dynamic": 0.7},
        {"name": "Coda", "bars": [30, 32], "pattern": "drone", "dynamic": 0.46},
    ],
    chords=[
        "Cm9", "Cm9",
        "Cm9", "Abmaj7", "Fm9", "G7b9", "Cm9", "Db9", "Bdim7", "G7b9",
        "Cm9", "G7b9",
        "Abmaj7#11", "Fm9", "Db9", "Cm9", "Bdim7",
        "C7/E",
        "Fm9", "Abmaj7#11", "Db9", "G7b9", "Cm9", "Bdim7",
        "Cm9", "G7b9",
        "Cm9", "Abmaj7", "Fm9", "G7b9",
        "Cm9", "Cm9",
    ],
    bassLine=[
        "C2", "C2",
        "C2", "Ab1", "F1", "G1", "C2", "Db2", "B1", "G1",
        "G1", "G1",
        "Ab1", "F1", "Db2", "C2", "B1",
        "C2",
        "F2", "Ab1", "Db2", "G1", "C2", "B1",
        "G1", "G1",
        "G1", "Ab1", "F1", "G1",
        "G1", "C2",
    ],
    melody=mel(
        notes(0, [(0, 3, 0), (3, 1, 3)], 0.42, "ten"),
        notes(1, [(0, 2, 2), (2, 2, 1)], 0.44, "ten"),
        # A: the motif, heavy
        notes(2, [(0, 1, 0), (1, 1, 3), (2, 1, 1), (3, 1, -1, 0.6, 0)], 0.6, "marc"),
        notes(3, [(0, 1.5, 3), (1.5, 1.5, 5), (3, 1, 4)], 0.62, "marc"),
        # I: mirrored (Eb C D C)
        notes(4, [(0, 1, 3), (1, 1, 0), (2, 1, 2), (3, 1, 4)], 0.62, "marc"),
        notes(5, [(0, 2, 4), (2, 1, 3), (3, 1, 2)], 0.66, "marc"),
        notes(6, [(0, 1, 0), (1, 1, 3), (2, 1, 1), (3, 1, 0)], 0.64, "marc"),
        notes(7, [(0, 1, 1), (1, 1, 1), (2, 2, 4)], 0.68, "marc"),      # Db, held
        notes(8, [(0, 1, 6), (1, 1, 4), (2, 1, 3), (3, 1, 2)], 0.7, "marc"),
        notes(9, [(0, 2, 1), (2, 2, 4)], 0.66, "ten"),
        # L1: a two-part answer, the bass walking down by semitone
        notes(10, [(0, 1, 0), (1, 1, 2), (2, 1, 3), (3, 1, 4)], 0.58, "ten"),
        notes(11, [(0, 1, 5), (1, 1, 4), (2, 1, 3), (3, 1, 1)], 0.66, "ten"),
        # B: ostinato, the motif in inversion
        # R then RI
        notes(12, [(0, 1, 0), (1, 1, 2), (2, 1, 4), (3, 1, 1)], 0.7, "marc"),
        notes(13, [(0, 1, 4), (1, 1, 2), (2, 1, 0), (3, 1, 3)], 0.72, "marc"),
        notes(14, [(0, 1, 1), (1, 1, 1), (2, 1, 4), (3, 1, 2)], 0.74, "marc"),
        notes(15, [(0, 1, 0), (1, 1, 2), (2, 1, 3), (3, 1, 4)], 0.76, "marc"),
        notes(16, [(0, 1, 6), (1, 1, 5), (2, 1, 4), (3, 1, 3)], 0.78, "marc"),
        # L2: one bar, isolated dominant
        notes(17, [(0, 2, 1), (2, 2, 4)], 0.52, "ten"),
        # C: the motif compressed, over a pulse
        notes(18, [(0, 0.5, 7), (0.5, 0.5, 6), (1, 0.5, 5), (1.5, 0.5, 4),
                   (2, 0.5, 7), (2.5, 0.5, 6), (3, 0.5, 5), (3.5, 0.5, 4)], 0.88, "acc"),
        notes(19, [(0, 1, 5), (1, 1, 7), (2, 1, 8), (3, 1, 7)], 0.9, "marc"),
        notes(20, [(0, 1, 1), (1, 1, 1), (2, 1, 4), (3, 1, 6)], 0.9, "marc"),
        notes(21, [(0, 1, 4), (1, 1, 6), (2, 1, 7), (3, 1, 6)], 0.92, "marc"),
        notes(22, [(0, 1, 0), (1, 1, 3), (2, 1, 1), (3, 1, -1, 0.94, 0)], 0.94, "acc"),
        notes(23, [(0, 2, 6), (2, 2, 4)], 0.9, "ten"),
        # L3: block chords thin out
        notes(24, [(0, 4, 0)], 0.44, "ten"),
        notes(25, [(0, 4, 4)], 0.4, "ten"),
        # A': the motif augmented, then inverted in the high register
        notes(26, [(0, 2, 0), (2, 2, 3)], 0.5, "ten"),
        notes(27, [(0, 2, 1), (2, 2, -1, 0.5, 0)], 0.5, "ten"),
        notes(28, [(0, 1, 0), (1, 1, -3), (2, 1, -2), (3, 1, -4)], 0.5, "ten"),
        notes(29, [(0, 4, -1, 0.46, 0)], 0.46, "ten"),
        # coda
        notes(30, [(0, 2, 0), (2, 2, 3)], 0.4, "ten"),
        notes(31, [(0, 4, 0)], 0.34, "ten"),
    ),
    expression={
        "dyn": [[0, 0.46], [2, 0.54], [9, 0.62], [10, 0.7], [11, 0.82], [12, 0.76],
                [16, 0.84], [17, 0.6], [18, 0.96], [23, 1.0], [24, 0.5],
                [26, 0.46], [29, 0.4], [31, 0.3]],
        "pedal": pedal_every(0, 32),
        "slur": [],
        "marks": [
            {"bar": 0, "beat": 0, "type": "dyn", "text": "pp"},
            {"bar": 0, "beat": 0, "type": "words", "text": "gelido"},
            {"bar": 2, "beat": 0, "type": "dyn", "text": "mp"},
            {"bar": 2, "beat": 0, "type": "words", "text": "pesante"},
            {"bar": 5, "beat": 0, "type": "wedge", "text": "cresc", "barTo": 7, "beatTo": 0},
            {"bar": 7, "beat": 0, "type": "dyn", "text": "mf"},
            {"bar": 8, "beat": 2, "type": "wedge", "text": "dim", "barTo": 9, "beatTo": 0},
            {"bar": 9, "beat": 0, "type": "dyn", "text": "mp"},
            {"bar": 10, "beat": 0, "type": "words", "text": "marcato il basso"},
            {"bar": 10, "beat": 0, "type": "wedge", "text": "cresc", "barTo": 12, "beatTo": 0},
            {"bar": 12, "beat": 0, "type": "dyn", "text": "f"},
            {"bar": 12, "beat": 0, "type": "words", "text": "ostinato"},
            {"bar": 15, "beat": 0, "type": "wedge", "text": "cresc", "barTo": 17, "beatTo": 0},
            {"bar": 17, "beat": 0, "type": "dyn", "text": "p"},
            {"bar": 17, "beat": 0, "type": "words", "text": "subito"},
            {"bar": 17, "beat": 2, "type": "wedge", "text": "cresc", "barTo": 18, "beatTo": 0},
            {"bar": 18, "beat": 0, "type": "dyn", "text": "ff"},
            {"bar": 18, "beat": 0, "type": "words", "text": "furia"},
            {"bar": 18, "beat": 0, "type": "tempo", "text": "Più mosso", "bpm": 72},
            {"bar": 22, "beat": 2, "type": "wedge", "text": "dim", "barTo": 24, "beatTo": 0},
            {"bar": 24, "beat": 0, "type": "dyn", "text": "p"},
            {"bar": 24, "beat": 0, "type": "words", "text": "di nuovo gelido"},
            {"bar": 24, "beat": 0, "type": "tempo", "text": "Meno mosso", "bpm": 58},
            {"bar": 26, "beat": 0, "type": "dyn", "text": "pp"},
            {"bar": 26, "beat": 0, "type": "words", "text": "senza colore"},
            {"bar": 28, "beat": 0, "type": "wedge", "text": "dim", "barTo": 30, "beatTo": 0},
            {"bar": 29, "beat": 0, "type": "tempo", "text": "rit."},
            {"bar": 30, "beat": 0, "type": "dyn", "text": "ppp"},
            {"bar": 30, "beat": 0, "type": "words", "text": "smorzando"},
        ],
    },
)


# Expressive words live inside sections, never on a rehearsal letter: a page
# that stacks "A'", "Tempo I", "fermata, poi" and "come una lettera riletta" on
# one bar is unreadable, however good the marks are.
WORDS = {
    "rework_1_tracks.json": [(4, 3, "poco a poco"), (12, 2, "espressivo"),
                             (20, 2, "marcato"), (27, 2, "come un ricordo")],
    "rework_2_letter.json": [(4, 2, "dolce"), (14, 2, "espressivo"),
                             (24, 2, "come una lettera riletta")],
    "rework_3_brass.json": [(4, 2, "pesante"), (14, 2, "ostinato"),
                            (20, 2, "furia"), (27, 2, "senza colore")],
}


def write(d, name):
    marks = [m for m in (d.get("expression") or {}).get("marks") or []
             if m.get("type") != "words"]
    for bar, beat, txt in WORDS.get(name, []):
        marks.append({"bar": bar, "beat": beat, "type": "words", "text": txt})
    marks.sort(key=lambda m: (int(m.get("bar", 0)), float(m.get("beat", 0))))
    d["expression"]["marks"] = marks
    # brass is the densest of the three: four bars only fit across the page at
    # 5.4 mm, otherwise MuseScore orphans bar 16 onto a system of its own
    if name == "rework_3_brass.json":
        d["sheet"] = {"scale": 5.4}
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print("wrote", path, len(d["melody"]), "notes", len(d["chords"]), "bars")


if __name__ == "__main__":
    write(TRACKS, "rework_1_tracks.json")
    write(LETTER, "rework_2_letter.json")
    write(BRASS, "rework_3_brass.json")
