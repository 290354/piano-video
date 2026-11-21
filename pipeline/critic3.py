#!/usr/bin/env python3
"""critic3 — the four things the last batch was still missing.

critic2 fixed texture, bass and colour, but a listener still heard:
  (1) hard cuts between sections — no link, no crescendo into the turn;
  (2) returns that restate the tune instead of developing it;
  (3) harmony that is colourful in name but not in function (no secondary
      dominants, no borrowed chords, no tension curve);
  (4) no performance layer — dynamics, wedges, pedal, articulation.

This scores those four, 0-100 each, and prints the evidence. It does not
replace critic2: run both.

    python3 critic3.py scores/rework_1_tracks.json
    python3 critic3.py --all scores/*.json
"""
import argparse, glob, json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import score_loader as SL

NOTE = SL.NOTE_PC
MAJOR_TRIAD = {0, 4, 7}
MINOR_TRIAD = {0, 3, 7}


def _root(name):
    m = re.match(r"^([A-G][#b]?)", name.strip())
    return NOTE[m.group(1)] if m else None


def _quality(name):
    body = name.split("/")[0].strip()
    m = re.match(r"^[A-G][#b]?(.*)$", body)
    return (m.group(1) if m else "") or ""


def _pcs(name):
    try:
        return set(SL.parse_chord(name))
    except Exception:
        return set()


def _is_dom7(name):
    """A dominant-seventh shape: major third + minor seventh above the root."""
    r = _root(name)
    if r is None:
        return False
    ivs = {(pc - r) % 12 for pc in _pcs(name)}
    return 4 in ivs and 10 in ivs


def _is_major(name):
    r = _root(name)
    if r is None:
        return False
    ivs = {(pc - r) % 12 for pc in _pcs(name)}
    return 4 in ivs and 3 not in ivs


def _is_minor(name):
    r = _root(name)
    if r is None:
        return False
    ivs = {(pc - r) % 12 for pc in _pcs(name)}
    return 3 in ivs and 4 not in ivs


def _diatonic_pcs(key, mode):
    scale = SL.SCALES.get(mode, SL.SCALES["minor"])
    r = NOTE[key]
    return {(r + s) % 12 for s in scale}


def _chord_tones_of_degree(key, mode, deg):
    scale = SL.SCALES.get(mode, SL.SCALES["minor"])
    r = NOTE[key]
    root = (r + scale[deg % 7]) % 12
    third = (r + scale[(deg + 2) % 7]) % 12
    fifth = (r + scale[(deg + 4) % 7]) % 12
    return root, third, fifth


# --------------------------------------------------------------- 1. bridges
def bridge_score(sc, ev):
    """Evidence that a section change is grown into, not cut to."""
    secs = sc.get("sections") or []
    if len(secs) < 2:
        return 0.0, "no sections"
    meter = sc.get("meter", [4, 4])
    bpb = meter[0] * 4.0 / meter[1]
    chords = sc["chords"]
    nbars = len(chords)
    per_bar = collections.Counter(int(e["beat"] // bpb) for e in ev)
    bass_at = {}
    for e in ev:
        if e["part"] == "bass":
            bass_at.setdefault(int(e["beat"] // bpb), e["midi"])
    dyn_pts = [(float(b), float(v)) for b, v in
               ((sc.get("expression") or {}).get("dyn") or [])]
    marks = (sc.get("expression") or {}).get("marks") or []

    total, detail = 0.0, []
    edges = [s["bars"][0] for s in secs if s.get("bars") and s["bars"][0] > 0]
    if not edges:
        return 0.0, "no internal edge"
    for b in edges:
        pts = 0.0
        # (a) an explicit link section whose texture differs from both sides
        prev = next((s for s in secs if s.get("bars", [0, 0])[1] == b), None)
        link = next((s for s in secs if s.get("bars", [0, 0])[0] == b), None)
        after = next((s for s in secs if s.get("bars", [0, 0])[0] == (link or {}).get("bars", [0, 0])[1]), None)
        if prev and link and after:
            llen = link["bars"][1] - link["bars"][0]
            lp = link.get("pattern")
            if llen <= 2 and lp and lp != prev.get("pattern") and lp != after.get("pattern"):
                pts += 0.30
                detail.append(f"bar{b}:link")
            else:
                # this edge closes a link section rather than opening one
                plen = prev["bars"][1] - prev["bars"][0]
                pp = next((s for s in secs if s.get("bars", [0, 0])[1] == prev["bars"][0]), None)
                if (plen <= 2 and prev.get("pattern")
                        and prev.get("pattern") != (pp or {}).get("pattern")
                        and prev.get("pattern") != link.get("pattern")):
                    pts += 0.30
                    detail.append(f"bar{b}:link-out")
        # (b) a written crescendo/diminuendo that lands on the edge
        for m in marks:
            if m.get("type") == "wedge":
                b0, b1 = int(m.get("bar", 0)), int(m.get("barTo", 0))
                if b0 < b and b1 >= b - 1:
                    pts += 0.20
                    detail.append(f"bar{b}:wedge")
                    break
        # (c) dynamic curve actually moves in the two bars before the edge
        seg = [v for (bar, v) in dyn_pts if b - 3 <= bar <= b + 1]
        if len(set(round(v, 3) for v in seg)) >= 2:
            pts += 0.15
            detail.append(f"bar{b}:dyn-slope")
        # (d) bass approaches by step (<= 2 semitones) or holds
        b0 = bass_at.get(b - 1)
        b1 = bass_at.get(b)
        if b0 is not None and b1 is not None and abs(b1 - b0) <= 2:
            pts += 0.20
            detail.append(f"bar{b}:bass-step")
        # (e) density does not jump more than 40% across the edge
        d0 = per_bar.get(b - 1, 0)
        d1 = per_bar.get(b, 0)
        if d0 and abs(d1 - d0) / d0 <= 0.6:
            pts += 0.15
            detail.append(f"bar{b}:density-ok")
        total += min(1.0, pts)
    return total / len(edges), "; ".join(detail)


# ------------------------------------------------------------ 2. development
def _mel_sequence(sc, lo, hi):
    rows = [r for r in (sc.get("melody") or []) if lo <= int(r[0]) < hi]
    rows.sort(key=lambda r: (int(r[0]), float(r[1])))
    return [int(r[3]) + 7 * int(r[4]) for r in rows]      # degree in a single octave axis


def _similarity(a, b):
    """Longest common subsequence ratio, insensitive to length."""
    if not a or not b:
        return 0.0
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(m):
            dp[i + 1][j + 1] = dp[i][j] + 1 if a[i] == b[j] else max(dp[i][j + 1], dp[i + 1][j])
    return 2.0 * dp[n][m] / (n + m)


def develop_score(sc):
    secs = [s for s in (sc.get("sections") or []) if s.get("bars")]
    if len(secs) < 3:
        return 0.0, "too few sections"
    theme = secs[0]
    tseq = _mel_sequence(sc, theme["bars"][0], theme["bars"][1])
    returns = [s for s in secs[1:] if re.search(r"'|2|返|再现|return", str(s.get("name", "")), re.I)]
    if not returns:
        return 0.0, "no return section"
    sims = []
    for s in returns:
        rseq = _mel_sequence(sc, s["bars"][0], s["bars"][1])
        sims.append(_similarity(tseq, rseq))
    sim = max(sims)
    # similarity 1.0 = literal restatement (0 points), 0.35-0.65 = developed
    if sim >= 0.85:
        pts = 0.0
    elif sim >= 0.65:
        pts = 0.55
    elif sim >= 0.35:
        pts = 1.0
    else:
        pts = 0.75                                     # too far: not a return any more
    # extra credit for a written motif-form annotation
    forms = str(sc.get("motifForms") or "")
    if forms:
        n = len([x for x in re.split(r"[,/ ]+", forms) if x])
        pts = min(1.0, pts + 0.08 * max(0, n - 2))
    return pts, f"return similarity {sim:.2f}"


# --------------------------------------------------------------- 3. tension
def tension_map(sc):
    """Per-bar harmonic tension, plus a list of functional colour events."""
    key = sc.get("key", "A")
    mode = sc.get("mode", "minor")
    dia = _diatonic_pcs(key, mode)
    chords = sc["chords"]
    n = len(chords)
    out = [0.0] * n
    events = []
    for i, name in enumerate(chords):
        r = _root(name)
        if r is None:
            continue
        pcs = _pcs(name)
        q = _quality(name)
        t = 0.0
        # secondary dominant: dominant 7 whose root is a fifth above the next root
        if i + 1 < n and _is_dom7(name):
            nr = _root(chords[i + 1])
            if nr is not None:
                if nr == (r + 5) % 12:
                    t += 2.0
                    events.append((i, "V/x"))
                elif nr == (r + 11) % 12:              # tritone sub resolving down a semitone
                    t += 2.0
                    events.append((i, "tritone-sub"))
        # neapolitan: major triad (or dominant) a semitone above the tonic
        if r == (NOTE[key] + 1) % 12 and (_is_major(name) or _is_dom7(name)):
            t += 2.0
            events.append((i, "neapolitan"))
        # borrowed: a major triad on a degree that is minor in the mode
        deg = (r - NOTE[key]) % 12
        if _is_major(name) and deg in (3, 8, 10) and mode in ("minor", "dorian"):
            t += 1.2
            events.append((i, "borrowed"))
        if _is_major(name) and mode == "major" and deg in (5, 10):
            t += 1.2
            events.append((i, "borrowed"))
        # diminished seventh anywhere
        if "dim7" in q:
            t += 1.5
            events.append((i, "dim7"))
        # chromatic notes against the mode
        outside = len([pc for pc in pcs if pc not in dia])
        t += 0.45 * outside
        out[i] = t
    return out, events


def tension_score(sc):
    tmap, events = tension_map(sc)
    n = len(tmap)
    if not n:
        return 0.0, 0
    functional = {"V/x", "tritone-sub", "bII7", "neapolitan"}
    nfun = len([e for e in events if e[1] in functional])
    density = nfun / n
    # climax: the loudest section should also be the tensest
    secs = sc.get("sections") or []
    climax_ok = 0.0
    if secs:
        loud = max(secs, key=lambda s: float(s.get("dynamic", 0)))
        b0, b1 = loud.get("bars", [0, n])
        seg = tmap[b0:min(b1, n)]
        rest = tmap[:b0] + tmap[b1:]
        if seg and rest and max(seg) >= sorted(rest)[int(0.75 * len(rest))]:
            climax_ok = 1.0
    pts = 0.55 * min(1.0, density / 0.22) + 0.25 * min(1.0, len(events) / 6) + 0.20 * climax_ok
    return pts, len(events)


# ----------------------------------------------------------- 4. expression
def expression_score(sc):
    expr = sc.get("expression") or {}
    nbars = len(sc["chords"])
    marks = expr.get("marks") or []
    ped = expr.get("pedal") or []
    dyn = expr.get("dyn") or []
    arts = 0
    for r in sc.get("melody") or []:
        if len(r) > 7 and str(r[7]):
            arts += 1
    kinds = {m.get("type") for m in marks}
    per_bar = len(marks) / max(1, nbars)
    ped_per = len(ped) / max(1, nbars)
    art_ratio = arts / max(1, len(sc.get("melody") or []))
    have = 0.0
    have += 0.30 * min(1.0, per_bar / 0.9)             # marks per bar
    have += 0.25 * min(1.0, ped_per / 0.6)             # pedal changes per bar
    have += 0.15 * min(1.0, len(dyn) / 8.0)            # curve resolution
    have += 0.15 * min(1.0, art_ratio / 0.18)          # articulated notes
    have += 0.15 * min(1.0, len(kinds - {None}) / 4.0)  # variety of mark types
    return have, f"marks {len(marks)}/{nbars}bar, pedal {len(ped)}, arts {art_ratio:.0%}"


# --------------------------------------------------------------------- main
def evaluate(path):
    with open(path) as f:
        sc = json.load(f)
    ev = SL.build(path)
    b, bd = bridge_score(sc, ev)
    d, dd = develop_score(sc)
    t, te = tension_score(sc)
    x, xd = expression_score(sc)
    total = 100.0 * (0.30 * b + 0.28 * d + 0.22 * t + 0.20 * x)
    return dict(total=total, bridge=b, develop=d, tension=t, expr=x,
                bridge_ev=bd, develop_ev=dd, tension_ev=te, expr_ev=xd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    files = []
    for p in a.files:
        files.extend(sorted(glob.glob(p)) if "*" in p else [p])
    print(f"\n{'file':<28}{'total':>7}{'bridge':>8}{'develop':>9}{'tension':>9}{'expr':>7}")
    for p in files:
        try:
            r = evaluate(p)
        except Exception as e:
            print(f"{os.path.basename(p):<28}  FAILED {e}")
            continue
        print(f"{os.path.basename(p):<28}{r['total']:7.1f}{r['bridge']*100:8.0f}"
              f"{r['develop']*100:9.0f}{r['tension']*100:9.0f}{r['expr']*100:7.0f}")
        print(f"    bridge: {r['bridge_ev']}")
        print(f"    develop: {r['develop_ev']} | tension events {r['tension_ev']} | {r['expr_ev']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
