#!/usr/bin/env python3
"""critic4 — the three things the second batch was still doing wrong.

critic2 fixed texture/bass/colour; critic3 fixed links, development, function
and the performance layer. A listener still heard:

  (1) one form for all three — quiet intro, rise, block-chord climax at three
      quarters, slower return, fade. The narrative was predictable, and every
      piece ended by disappearing.
  (2) the left hand as scenery — a fixed figure standing for an image, hard
      switches at bar lines, block chords at every climax with the earlier
      material thrown away, almost no interwoven lines.
  (3) harmony that leans sideways — local mixture and passing accidentals, no
      distant key, so nothing ever arrives from far away.

This scores those three, 0-100 each, and prints the evidence.
It does not replace critic2/critic3: run all three.

    python3 critic4.py scores/rework_1_tracks.json
    python3 critic4.py scores/*.json
"""
import argparse, glob, json, math, os, sys

PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
      "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
MAJOR = [0, 2, 4, 5, 7, 9, 11]
MINOR = [0, 2, 3, 5, 7, 8, 10]
DORIAN = [0, 2, 3, 5, 7, 9, 10]
SCALES = {"major": MAJOR, "minor": MINOR, "dorian": DORIAN, "harmonic_minor": [0, 2, 3, 5, 7, 8, 11]}


def root_of(name):
    n = name.split("/")[0].strip()
    for k in sorted(PC, key=len, reverse=True):
        if n.startswith(k):
            return PC[k]
    return None


def quality_of(name):
    n = name.split("/")[0].strip()
    for k in sorted(PC, key=len, reverse=True):
        if n.startswith(k):
            return n[len(k):]
    return ""


def fifth_dist(a, b):
    """Distance on the circle of fifths, 0-6 (6 = tritone)."""
    d = (b - a) % 12
    return {0: 0, 7: 1, 2: 2, 9: 3, 4: 4, 11: 5, 6: 6, 1: 5, 8: 4, 3: 3, 10: 2, 5: 1}[d]


# ---------------------------------------------------------------- 1. the form
def form_score(sc):
    secs = sc.get("sections") or []
    nbars = len(sc["chords"])
    if not secs:
        return 0.0, "no sections"
    pts, ev = 0.0, []

    # (a) how the piece ends. A fade is a default, not a decision.
    ending = str(sc.get("ending", "fade"))
    pts += 1.0 * {"cut": 1.0, "ring": 1.0, "fade": 0.25}.get(ending, 0.4)
    ev.append(f"ending {ending}")

    # (b) where the peak sits. 0.72-0.78 is the template's slot.
    dyn = [(int(b), float(v)) for b, v in ((sc.get("expression") or {}).get("dyn") or [])]
    peak_bar, peak_v = max(dyn, key=lambda x: x[1]) if dyn else (0, 1.0)
    pos = peak_bar / max(1, nbars)
    off = abs(pos - 0.75)
    pts += 1.0 * min(1.0, off / 0.25)
    ev.append(f"peak bar {peak_bar + 1} ({pos:.0%} through)")

    # (c) what the return does. Slower + softer alone is the old trick.
    names = [s.get("name", "") for s in secs]
    ret = next((s for s in secs if s.get("name", "").replace("’", "'") in ("A'", "A′")), None)
    first = next((s for s in secs if s.get("name") == "A"), None)
    if ret and first:
        slow = ret.get("bpm") is not None and first.get("bpm") is not None and ret["bpm"] < first["bpm"]
        newkey = (ret.get("key") or sc.get("key")) != (first.get("key") or sc.get("key"))
        newtex = (ret.get("texture") or ret.get("pattern")) != (first.get("texture") or first.get("pattern"))
        moved = 0.0 + (0.4 if newtex else 0.0) + (0.4 if newkey else 0.0)
        moved += 0.2 if not slow else 0.0
        pts += 1.0 * moved
        ev.append(f"return texture={ret.get('texture') or ret.get('pattern')} "
                  f"key={ret.get('key') or sc.get('key')} slow={slow}")
    else:
        pts += 0.6                      # no literal return at all is also a choice
        ev.append("no literal return")

    # (d) bonus: the shape is not one ramp — it drops hard somewhere
    drops = sum(1 for i in range(1, len(dyn)) if dyn[i][1] < dyn[i - 1][1] - 0.25)
    ev.append(f"{drops} hard drops")
    return min(1.0, pts / 3.0 + min(0.10, 0.05 * drops)), "; ".join(ev)


# --------------------------------------------------------- 2. real counterpoint
def _rows(sc, key):
    out = []
    for r in sc.get(key) or []:
        bar, beat, dur, deg = int(r[0]), float(r[1]), float(r[2]), int(r[3])
        octv = int(r[4]) if len(r) > 4 else 0
        out.append((bar, beat, dur, deg, octv))
    return out


def _pitched(sc, rows, key=None, mode=None):
    """Degree rows -> MIDI, using the tonic in force for that bar."""
    secs = sc.get("sections") or []
    hk, hm = sc["key"], sc.get("mode", "minor")
    out = []
    for bar, beat, dur, deg, octv in rows:
        k, mo = hk, hm
        for sec in secs:
            b = sec.get("bars") or [0, 10 ** 9]
            if b[0] <= bar < b[1]:
                k, mo = sec.get("key", hk), sec.get("mode", hm)
                break
        sc_ = SCALES.get(mo, MINOR)
        out.append((bar, beat, dur, 12 * (octv + 5) + PC[k] + sc_[deg % 7] + 12 * (deg // 7)))
    return out


def _ivs(voice, n=4):
    """Semitone interval signature of n consecutive notes, transposition-free."""
    return [voice[i + 1][3] - voice[i][3] for i in range(min(n, len(voice) - 1))]


def counterpoint_score(sc):
    bpb = sc["meter"][0] * 4.0 / sc["meter"][1]
    nbars = len(sc["chords"])
    mel = _pitched(sc, _rows(sc, "melody"))
    cnt = _pitched(sc, _rows(sc, "counter"))
    left = [(int(r[0]), float(r[1]), float(r[2]), int(r[3])) for r in (sc.get("left") or [])]
    for v in (mel, cnt):
        v.sort(key=lambda r: (r[0], r[1]))
    left.sort(key=lambda r: (r[0], r[1]))
    pts, ev = 0.0, []

    voices = [("mel", mel), ("cnt", cnt), ("left", left)]
    voices = [v for v in voices if len(v[1]) >= 4]

    def imit(a, b):
        hits = 0
        for i in range(len(a) - 3):
            sig = _ivs(a[i:i + 4])
            for j in range(len(b) - 3):
                if _ivs(b[j:j + 4]) == sig:
                    dt = (b[j][0] * bpb + b[j][1]) - (a[i][0] * bpb + a[i][1])
                    if 0.2 <= abs(dt) <= 8:
                        hits += 1
                        break
        return hits

    pairs = []
    for i in range(len(voices)):
        for j in range(i + 1, len(voices)):
            pairs.append((imit(voices[i][1], voices[j][1]), voices[i], voices[j]))
    pairs.sort(key=lambda x: (-x[0], -(len(x[1][1]) + len(x[2][1]))))
    hits, (n1, v1), (n2, v2) = pairs[0] if pairs else (0, ("-", []), ("-", []))

    # (a) two independent written lines
    pts += 0.18 if v2 else 0.0
    share = len({b for b, *_ in v2}) / max(1, nbars) if v2 else 0.0
    pts += 0.14 * min(1.0, share / 0.5)
    ev.append(f"{n1}/{n2} {len(v1)}/{len(v2)} notes, second over {share:.0%} of bars")

    # (b) imitation: same interval shape in both voices, offset in time
    pts += min(0.30, 0.03 * hits)
    ev.append(f"{hits} imitations")

    # (c) contrary motion, bar by bar
    by_a, by_b = {}, {}
    for bar, beat, dur, midi in v1:
        by_a.setdefault(bar, []).append(midi)
    for bar, beat, dur, midi in v2:
        by_b.setdefault(bar, []).append(midi)
    contra = same = 0
    for bar in sorted(set(by_a) & set(by_b)):
        a, b = by_a[bar], by_b[bar]
        if len(a) >= 2 and len(b) >= 2:
            da, db = a[-1] - a[0], b[-1] - b[0]
            if da and db:
                contra += 1 if da * db < 0 else 0
                same += 1 if da * db > 0 else 0
    ratio = contra / max(1, contra + same)
    pts += 0.18 * ratio
    ev.append(f"contrary {contra}/{contra + same}")

    # (d) rhythmic independence
    o1 = {(b, round(t, 3)) for b, t, *_ in v1}
    o2 = {(b, round(t, 3)) for b, t, *_ in v2}
    indep = len(o2 - o1) / max(1, len(o2))
    pts += 0.12 * indep
    ev.append(f"independent onsets {indep:.0%}")

    # (e) at the peak, is it block chords with nobody else speaking?
    dyn = [(int(b), float(v)) for b, v in ((sc.get("expression") or {}).get("dyn") or [])]
    peak_bar = max(dyn, key=lambda x: x[1])[0] if dyn else 0
    lo, hi = max(0, peak_bar - 2), min(nbars, peak_bar + 2)
    attacks = {}
    for b, t, d, midi in left:
        if lo <= b < hi:
            attacks[(b, round(t, 2))] = attacks.get((b, round(t, 2)), 0) + 1
    others = [b * bpb + t for b, t, *_ in mel + cnt if lo <= b < hi]
    solo = sum(1 for (b, t), n in attacks.items()
               if n >= 3 and not any(abs(o - (b * bpb + t)) < 0.26 for o in others))
    wall = solo / max(1, len(attacks))
    pts += 0.08 if wall < 0.5 else 0.0
    ev.append(f"peak solo-chords {wall:.0%}")
    return min(1.0, pts), "; ".join(ev)


# ------------------------------------------------------------- 3. key distance
def distance_score(sc):
    tonic = PC[sc["key"]]
    mode = sc.get("mode", "minor")
    scale = set(SCALES.get(mode, MINOR))
    chords = sc["chords"]
    secs = sc.get("sections") or []
    pts, ev = 0.0, []

    # (a) a section in a key far from home
    far = []
    for s in secs:
        k = s.get("key")
        if not k:
            continue
        d = fifth_dist(tonic, PC[k])
        far.append((s.get("name"), k, d))
    best = max([d for _, _, d in far], default=0)
    pts += min(0.35, best / 6 * 0.35)
    ev.append("sections " + (", ".join(f"{n}:{k}({d})" for n, k, d in far) or "none"))

    # (b) chords whose roots sit a third or a tritone from the tonic
    near, distant = 0, []
    for i, c in enumerate(chords):
        r = root_of(c)
        if r is None:
            continue
        d = fifth_dist(tonic, r)
        rel = (r - tonic) % 12
        if d >= 4 or rel in (3, 4, 6, 8, 9):
            distant.append((i + 1, c, d))
        else:
            near += 1
    pts += min(0.35, len(distant) / max(1, len(chords)) / 0.30 * 0.35)
    ev.append(f"{len(distant)} distant roots")

    # (c) harmony outside the home scale
    outs = 0
    for c in chords:
        r = root_of(c)
        if r is None:
            continue
        if (r - tonic) % 12 not in scale:
            outs += 1
    pts += min(0.15, outs / max(1, len(chords)) / 0.25 * 0.15)
    ev.append(f"{outs} out-of-scale roots")

    # (d) the piece does not end at home: progressive tonality is a statement
    last = root_of(chords[-1])
    d_last = fifth_dist(tonic, last) if last is not None else 0
    pts += min(0.15, d_last / 6 * 0.15)
    ev.append(f"ends on {chords[-1]} (fifths {d_last})")
    return min(1.0, pts), "; ".join(ev)


def evaluate(path):
    sc = json.load(open(path))
    f, fe = form_score(sc)
    c, ce = counterpoint_score(sc)
    d, de = distance_score(sc)
    total = (0.34 * f + 0.33 * c + 0.33 * d) * 100
    return dict(total=total, form=f, counter=c, dist=d,
                form_ev=fe, counter_ev=ce, dist_ev=de)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    files = []
    for p in a.files:
        files.extend(sorted(glob.glob(p)) if "*" in p else [p])
    print(f"\n{'file':<28}{'total':>7}{'form':>7}{'counter':>9}{'distance':>10}")
    for p in files:
        try:
            r = evaluate(p)
        except Exception as e:
            print(f"{os.path.basename(p):<28}  FAILED {e}")
            continue
        print(f"{os.path.basename(p):<28}{r['total']:7.1f}{r['form']*100:7.0f}"
              f"{r['counter']*100:9.0f}{r['dist']*100:10.0f}")
        print(f"    form: {r['form_ev']}")
        print(f"    counter: {r['counter_ev']}")
        print(f"    distance: {r['dist_ev']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
