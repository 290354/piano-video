#!/usr/bin/env python3
"""Score a written piece before rendering it.

The pipeline has no ear, so this file is the substitute: it turns the things a
listener would notice into numbers computed from the score itself.

    python3 critic.py --history ../scores a.json b.json c.json
    python3 critic.py --history ../scores a.json b.json --out best.json

Higher is better, 100 is a well-formed piece. The point is not the absolute
number — it is the ranking between candidates written in the same minute.
"""
import argparse, glob, json, math, os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import score_loader


def _build(path):
    ev = score_loader.build(path, 0)
    with open(path) as f:
        sc = json.load(f)
    return sc, ev


def _band(x, lo, hi, soft):
    """1 inside [lo, hi], falling off linearly outside"""
    if lo <= x <= hi:
        return 1.0
    d = (lo - x) if x < lo else (x - hi)
    return max(0.0, 1.0 - d / soft)


def _melody_metrics(ev, sc):
    mel = sorted([e for e in ev if e["part"] == "melody"], key=lambda e: e["beat"])
    if len(mel) < 8:
        return None
    pitches = [e["midi"] for e in mel]
    iv = [pitches[i + 1] - pitches[i] for i in range(len(pitches) - 1)]
    step_ratio = sum(1 for d in iv if abs(d) <= 2) / max(1, len(iv))
    span = max(pitches) - min(pitches)
    distinct = len(set(pitches))

    # recurring 4-note interval shapes = a motif the listener can remember
    shapes = [tuple(iv[i:i + 3]) for i in range(len(iv) - 2)]
    cnt = collections.Counter(shapes)
    # how often the most recognisable shape comes back — not the total of all
    # repeats, which punishes pieces that develop several ideas
    motif_hits = max([v for k, v in cnt.items() if any(k)] or [0])

    # section contrast: mean notes per bar inside each written section
    meter = sc.get("meter", [4, 4])
    bpb = meter[0] * 4.0 / meter[1]
    per_bar = collections.Counter(int(e["beat"] // bpb) for e in mel)
    bars = len(sc["chords"])
    dens = [per_bar.get(b, 0) for b in range(bars)]
    secs = sc.get("sections") or []
    if secs:
        means = []
        for s in secs:
            b = s.get("bars") or [0, bars]
            seg = dens[b[0]:min(b[1], bars)]
            if seg:
                means.append(sum(seg) / len(seg))
        contrast = (max(means) / max(1e-6, min(means))) if means else 1.0
    else:
        nz = [d for d in dens if d > 0]
        contrast = (max(nz) / max(1, min(nz))) if nz else 1.0

    return dict(
        step_ratio=step_ratio,
        span=span,
        distinct=distinct,
        dyn=max(e["vel"] for e in mel) - min(e["vel"] for e in mel),
        contrast=contrast,
        motif=motif_hits,
        mean_pitch=sum(pitches) / len(pitches),
        last_deg=sc["melody"][-1][3] if sc.get("melody") else -1,
        last_dur=sc["melody"][-1][2] if sc.get("melody") else 0,
        intervals=iv,
        dens=dens,
    )


def _hist(iv):
    c = collections.Counter()
    for d in iv:
        c[max(-12, min(12, d))] += 1
    n = sum(c.values()) or 1
    return {k: v / n for k, v in c.items()}


def _cos_dist(a, b):
    keys = set(a) | set(b)
    if not keys:
        return 1.0
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    na = math.sqrt(sum(v * v for v in a.values())) or 1e-9
    nb = math.sqrt(sum(v * v for v in b.values())) or 1e-9
    return 1.0 - dot / (na * nb)


def score_piece(path, history=()):
    sc, ev = _build(path)
    m = _melody_metrics(ev, sc)
    if m is None:
        return None, {"error": "melody too short"}

    hist = _hist(m["intervals"])
    novelty = 1.0
    if history:
        novelty = min(_cos_dist(hist, _hist(h)) for h in history)

    parts = {
        "级进率": (_band(m["step_ratio"], 0.55, 0.82, 0.30), 0.20),
        "音域": (_band(m["span"], 12, 26, 8), 0.10),
        "音高多样性": (min(1.0, m["distinct"] / 10.0), 0.10),
        "力度层次": (min(1.0, m["dyn"] / 0.30), 0.15),
        "密度对比": (_band(m["contrast"], 1.35, 2.6, 0.5), 0.15),
        "动机重复": (_band(m["motif"], 3, 6, 1.5), 0.15),
        "新颖度": (min(1.0, novelty / 0.22), 0.10),
        "终止式": (1.0 if (m["last_deg"] % 7 == 0 and m["last_dur"] >= 2.5) else 0.0, 0.05),
    }
    total = sum(v * w for v, w in parts.values())
    if parts["终止式"][0] == 0:
        total *= 0.72                     # a piece that does not cadence is a sketch

    return total, {k: v for k, (v, w) in parts.items()}, m, novelty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidates", nargs="+")
    ap.add_argument("--history", default=None, help="directory of previous scores")
    ap.add_argument("--out", default=None, help="copy the winner here")
    a = ap.parse_args()

    hist = []
    if a.history:
        for p in sorted(glob.glob(os.path.join(a.history, "*.json"))):
            try:
                _, ev = _build(p)
                mel = sorted([e for e in ev if e["part"] == "melody"], key=lambda e: e["beat"])
                hist.append(_hist([mel[i + 1]["midi"] - mel[i]["midi"] for i in range(len(mel) - 1)]))
            except Exception:
                pass

    rows, best = [], None
    for p in a.candidates:
        try:
            total, detail, m, nov = score_piece(p, hist)
        except Exception as e:
            print(f"{os.path.basename(p)}  FAILED: {e}")
            continue
        if total is None:
            continue
        rows.append((total, p, detail, m, nov))
        if best is None or total > best[0]:
            best = rows[-1]

    if not rows:
        print("no usable candidate")
        return 1

    rows.sort(reverse=True, key=lambda r: r[0])
    keys = list(rows[0][2].keys())
    print(f"\n{'候选':<28}{'总分':>6}  " + "  ".join(f"{k:>6}" for k in keys))
    for total, p, detail, m, nov in rows:
        print(f"{os.path.basename(p):<28}{total*100:6.1f}  " + "  ".join(f"{detail[k]:6.2f}" for k in keys))
    print()
    for total, p, detail, m, nov in rows:
        print(f"{os.path.basename(p):<28} 级进 {m['step_ratio']:.0%}  音域 {m['span']}半音  "
              f"音数/小节 {min(m['dens'])}–{max(m['dens'])}  力度差 {m['dyn']:.2f}  与旧作距离 {nov:.2f}")

    print(f"\nWINNER: {best[1]}  ({best[0]*100:.1f})")
    if a.out:
        with open(best[1]) as f:
            data = f.read()
        with open(a.out, "w") as f:
            f.write(data)
        print(f"copied -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
