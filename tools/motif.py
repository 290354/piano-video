#!/usr/bin/env python3
"""motif.py — build melodies from a motif and its transformations.

A motif is a list of (degree_offset, duration) pairs, relative to the first
note. Degrees count scale steps (0 = tonic, 1 = next scale tone, ...), the same
unit score.json uses, so a transposed motif stays inside the mode.

    M = [(0, 1), (4, 1), (2, .5), (1, .5)]      # F C Ab G in F minor
    rows = emit(M, bar=0, beat=0, deg0=0, octv=0, vel=.62, bpb=3)
    rows += emit(shift(M, 2), bar=4, beat=0, deg0=0, octv=0, vel=.7, bpb=3)
    rows += emit(invert(M), bar=8, beat=0, deg0=2, octv=0, vel=.55, bpb=3)
"""
import json


def shift(m, k):
    """Same shape, starting k scale steps higher."""
    return [(d + k, du) for d, du in m]


def invert(m):
    """Mirror around the first note: a rising fourth becomes a falling fourth."""
    return [(-d, du) for d, du in m]


def retro(m):
    return list(reversed(m))


def retro_invert(m):
    return [(-d, du) for d, du in reversed(m)]


def augment(m, k=2.0):
    """Stretch the rhythm, keep the intervals — the motif at half speed."""
    return [(d, du * k) for d, du in m]


def diminish(m, k=2.0):
    return [(d, du / k) for d, du in m]


def sequence(m, start_deg, steps, count, gap=0):
    """A rising sequence: repeat the motif `count` times, moving `steps` each time."""
    return [shift(m, start_deg + i * steps) for i in range(count)]


def emit(m, bar, beat, deg0, octv, vel, bpb=4.0, acc=None):
    """Lay a motif on the grid, wrapping to the next bar when it runs over.

    Returns score.json melody rows: [bar, beat, dur, degree, octave, velocity]
    plus an optional seventh element for a semitone inflection.
    """
    out, b, t = [], int(bar), float(beat)
    while t >= bpb:
        b += int(t // bpb)
        t -= bpb * int(t // bpb)
    for d, dur in m:
        row = [b, round(t, 3), round(float(dur), 3), int(deg0 + d), int(octv), round(float(vel), 3)]
        if acc:
            row.append(int(acc))
        out.append(row)
        t += dur
        while t >= bpb - 1e-9:
            b += 1
            t -= bpb
    return out


def stack(*rows):
    """Concatenate melody rows from several emit() calls."""
    out = []
    for r in rows:
        out.extend(r)
    return out
