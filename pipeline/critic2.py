#!/usr/bin/env python3
"""critic2 — score a piece on the things a listener actually complains about.

critic.py (v1) measured melody only: step ratio, range, dynamic spread,
density contrast, motif repeats, novelty. It had no term at all for harmony,
texture, bass line or rhythm — and it weighted "mostly stepwise" at 0.20, so a
piece could score 100 while being the ninth variation of the same nocturne.

This version keeps the useful v1 terms, adds the four missing ones, and stops
treating stepwise motion as an end in itself.

    python3 critic2.py --history ../scores a.json b.json c.json
    python3 critic2.py --history ../scores a.json b.json --out best.json

Higher is better, 100 is a piece with something to say.
"""
import argparse, collections, glob, json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import score_loader as SL
from critic import _band, _hist, _cos_dist

TRIADS = ("", "m", "dim", "aug")


def _chord_label(name, root_pc, scale):
    """diatonic | dominant | chromatic, judged against the written mode."""
    pcs = SL.parse_chord(name)
    dia = {(root_pc + s) % 12 for s in scale}
    outside = {pc for pc in pcs if pc not in dia}
    if not outside:
        return "diatonic"
    lead = (root_pc + 11) % 12
    if pcs[0] == (root_pc + 7) % 12 and outside <= {lead}:
        return "dominant"           # V with a raised leading tone: functional
    return "chromatic"


def _is_colour(name):
    body = name.split("/")[0]
    m = re.match(r"^([A-G][#b]?)(.*)$", body.strip())
    return bool(m) and m.group(2) not in TRIADS


def _iclass(d):
    a = abs(d)
    return 0 if a <= 2 else (1 if a <= 4 else (2 if a <= 7 else 3))


def _motif_forms(degseq, motif=None):
    """How many of P / I / R / RI of the piece's own motif come back.

    Measured in scale steps, not semitones: the motif is written in degrees and
    its inversion is taken in degrees too. Mirroring degrees is not the same as
    mirroring semitones when the mode is uneven, and tonal answers are the
    normal practice anyway.
    """
    if motif and len(motif) >= 2:
        m = tuple(motif[i + 1] - motif[i] for i in range(len(motif) - 1))
    elif len(degseq) >= 4:
        m = tuple(degseq[i + 1] - degseq[i] for i in range(3))
    else:
        return 0
    n = len(m)
    forms = {"P": m,                                  # as written
             "I": tuple(-x for x in m),               # mirrored in degrees
             "R": tuple(-x for x in reversed(m)),     # backwards, intervals negated
             "RI": tuple(reversed(m))}                # backwards
    hit = set()
    for i in range(len(degseq) - n):
        w = tuple(degseq[i + j + 1] - degseq[i + j] for j in range(n))
        for k, f in forms.items():
            if w == f:
                hit.add(k)
    return len(hit)


def metrics(path):
    with open(path) as f:
        sc = json.load(f)
    ev = SL.build(path, 0)
    mel = sorted([e for e in ev if e["part"] == "melody"], key=lambda e: e["beat"])
    if len(mel) < 8:
        return None

    meter = sc.get("meter", [4, 4])
    bpb = meter[0] * 4.0 / meter[1]
    nbars = len(sc["chords"])
    secs = sc.get("sections") or []
    scale = SL.SCALES[sc.get("mode", "minor")]
    root_pc = SL.NOTE_PC[sc.get("key", "A")]

    pitches = [e["midi"] for e in mel]
    iv = [pitches[i + 1] - pitches[i] for i in range(len(pitches) - 1)]
    leap = sum(1 for d in iv if abs(d) >= 5) / max(1, len(iv))
    classes = len({_iclass(d) for d in iv})

    # --- motif: intervals AND durations, so a rhythmic hook counts ----------
    # window length follows the declared motif, otherwise a link note counts
    # as part of the shape and every occurrence misses by one
    rows = sorted(sc.get("melody") or [], key=lambda r: (int(r[0]), float(r[1])))
    degseq = [int(r[3]) for r in rows]
    wn = 3
    if sc.get("motif") and len(sc["motif"]) >= 2:
        wn = len(sc["motif"]) - 1
    stream = [(iv[i], round(mel[i]["dur"], 2)) for i in range(len(iv))]
    grams = [tuple(stream[i:i + wn]) for i in range(len(stream) - wn + 1)]
    motif_rep = max(collections.Counter(grams).values()) if grams else 0

    # --- texture -----------------------------------------------------------
    pats = {sc.get("pattern", "nocturne")}
    pats |= {s.get("pattern") for s in secs if s.get("pattern")}
    pats.discard(None)

    # --- bass line ---------------------------------------------------------
    bass = [e for e in ev if e["part"] == "bass"]
    bpos = len({round((e["beat"] % bpb) / bpb, 2) for e in bass})
    bpitch = len({e["midi"] for e in bass}) / max(1, nbars)

    # --- harmony -----------------------------------------------------------
    labels = [_chord_label(c, root_pc, scale) for c in sc["chords"]]
    n_chrom = labels.count("chromatic")
    n_dom = labels.count("dominant")
    chrom = (n_chrom + 0.5 * n_dom) / max(1, nbars)
    colour = sum(1 for c in sc["chords"] if _is_colour(c)) / max(1, nbars)
    quals = set()
    for c in sc["chords"]:
        mm = re.match(r"^([A-G][#b]?)(.*)$", c.split("/")[0].strip())
        if mm:
            quals.add(mm.group(2))

    # --- density contrast across sections (all parts, not just melody) ------
    per_bar = collections.Counter(int(e["beat"] // bpb) for e in ev)
    dens = [per_bar.get(b, 0) for b in range(nbars)]
    if secs:
        means = []
        for s in secs:
            b = s.get("bars") or [0, nbars]
            seg = dens[b[0]:min(b[1], nbars)]
            if seg:
                means.append(sum(seg) / len(seg))
        contrast = (max(means) / max(1e-6, min(means))) if means else 1.0
    else:
        nz = [d for d in dens if d > 0]
        contrast = (max(nz) / max(1, min(nz))) if nz else 1.0

    return dict(
        motif=motif_rep,
        forms=_motif_forms(degseq, sc.get("motif")),
        leap=leap,
        classes=classes,
        span=max(pitches) - min(pitches),
        dyn=max(e["vel"] for e in mel) - min(e["vel"] for e in mel),
        npat=len(pats),
        pats=sorted(pats),
        bpos=bpos,
        bpitch=bpitch,
        colour=colour,
        nqual=len(quals),
        chrom=chrom,
        contrast=contrast,
        last_deg=sc["melody"][-1][3] if sc.get("melody") else -1,
        last_dur=sc["melody"][-1][2] if sc.get("melody") else 0,
        iv=iv,
        nbars=nbars,
    )


def _texture_sig(sc):
    pats = {sc.get("pattern", "nocturne")}
    pats |= {s.get("pattern") for s in (sc.get("sections") or []) if s.get("pattern")}
    pats.discard(None)
    return pats


def score_piece(path, hist=None):
    m = metrics(path)
    if m is None:
        return None, None, None, 0.0

    novelty = 1.0
    if hist:
        with open(path) as f:
            pats = _texture_sig(json.load(f))
        nov = []
        for h in hist:
            d_iv = _cos_dist(_hist(m["iv"]), h["iv"])
            a, b = pats, h["pats"]
            jac = 1.0 - len(a & b) / max(1, len(a | b))
            nov.append(0.6 * d_iv + 0.4 * jac)
        novelty = min(nov)

    parts = {
        "动机辨识": (_band(m["motif"], 3, 8, 2.0), 0.13),
        "动机变形": (_band(m["forms"], 3, 4, 1.0), 0.11),
        "音程多样": (0.5 * _band(m["classes"], 3, 4, 1.0) + 0.5 * _band(m["leap"], 0.10, 0.38, 0.12), 0.10),
        "音域": (_band(m["span"], 12, 26, 8), 0.05),
        "力度层次": (min(1.0, m["dyn"] / 0.35), 0.09),
        "织体变化": (_band(m["npat"], 3, 6, 1.5), 0.10),
        "低音独立": (0.5 * _band(m["bpos"], 2, 5, 1.0) + 0.5 * _band(m["bpitch"], 0.25, 0.85, 0.20), 0.09),
        "和声色彩": (0.5 * _band(m["nqual"], 4, 9, 2.0) + 0.5 * _band(m["colour"], 0.35, 0.95, 0.25), 0.11),
        "离调密度": (min(1.0, m["chrom"] / 0.12), 0.08),
        "密度对比": (min(1.0, max(0.0, (m["contrast"] - 1.0) / 0.5)), 0.07),
        "终止式": (1.0 if (m["last_deg"] % 7 == 0 and m["last_dur"] >= 2.5) else 0.0, 0.03),
        "新颖度": (1.0 if not hist else _band(novelty, 0.25, 0.60, 0.18), 0.04),
    }
    total = sum(v * w for v, w in parts.values())
    if parts["终止式"][0] == 0:
        total *= 0.75
    return total, {k: v for k, (v, w) in parts.items()}, m, novelty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidates", nargs="+")
    ap.add_argument("--history", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    hist = []
    if a.history:
        for p in sorted(glob.glob(os.path.join(a.history, "*.json"))):
            try:
                mm = metrics(p)
                if mm:
                    with open(p) as f:
                        mm["pats"] = _texture_sig(json.load(f))
                    hist.append(mm)
            except Exception:
                pass

    rows = []
    for p in a.candidates:
        try:
            total, detail, m, nov = score_piece(p, hist)
        except Exception as e:
            print(f"{os.path.basename(p)}  FAILED: {e}")
            continue
        if total is None:
            continue
        rows.append((total, p, detail, m, nov))

    if not rows:
        print("no usable candidate")
        return 1

    rows.sort(reverse=True, key=lambda r: r[0])
    keys = list(rows[0][2].keys())
    print(f"\n{'candidate':<26}{'score':>7}  " + " ".join(f"{k:>5}" for k in keys))
    for total, p, d, m, nov in rows:
        print(f"{os.path.basename(p):<26}{total * 100:7.1f}  " + " ".join(f"{d[k]:5.2f}" for k in keys))
    print()
    for total, p, d, m, nov in rows:
        print(f"{os.path.basename(p):<26} 动机 {m['motif']}次/{m['forms']}形  "
              f"大跳 {m['leap']:.0%} 织体 {m['npat']}种({','.join(m['pats'])})  "
              f"色彩 {m['nqual']}种/{m['colour']:.0%} 离调 {m['chrom']:.0%}  低音 {m['bpos']}位/{m['bpitch']:.2f}  "
              f"力度差 {m['dyn']:.2f}  距离 {nov:.2f}")

    best = rows[0]
    print(f"\nWINNER: {best[1]}  ({best[0] * 100:.1f})")
    if a.out:
        with open(best[1]) as f:
            data = f.read()
        with open(a.out, "w") as f:
            f.write(data)
        print(f"copied -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
