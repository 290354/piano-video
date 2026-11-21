#!/usr/bin/env python3
#!/usr/bin/env python3
"""make_sheet.py — score.json -> engraved MusicXML (grand staff).

    python3 tools/make_sheet.py scores/daily_20261121.json out/sheet/daily_20261121.musicxml

Then open the .musicxml in MuseScore Studio and export PDF / .mscz, or run
    mscore3 -o out/sheet/daily_20261121.pdf out/sheet/daily_20261121.musicxml


The notes are NOT re-derived: they come from pipeline/score_loader.build(),
the same function the video renderer uses, so the sheet matches the audio.

What the engraver reads
-----------------------
* notes / chords / tied notes        -> pitches, ties across bar lines
* sec[7] articulation                -> <staccato/> <tenuto/> <accent/> <strong-accent/>
* expression.dyn                     -> <dynamics> + <wedge> at the sampled bars
* expression.marks (words / tempo)    -> <direction><words> / <direction><metronome>
* expression.pedal                   -> <pedal type="start|stop"/> per bar, adjacent
                                        spans merged so Ped. and * never share a beat
* sections                          -> <rehearsal> letters, <print new-page> at midpoint

Known engraving trade-offs (MuseScore 3.6 headless)
---------------------------------------------------
* <slur> makes 3.6 drop an entire voice, so slurs are only written when the
  score sets "slurEngine": "musicxml". Legato is carried by the pedal + tenuto.
* ties / slurs / articulations must live in ONE <notations> element; splitting
  them silently loses the second group.
* <work> / <identification> before <movement-title> demotes the import and
  kills dynamics, so only <movement-title> is emitted.
"""
import json, os, re, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import score_loader as SL

DIV = 24                     # divisions per quarter note (exact sixths & triplets)
GRID = 3                     # smallest value the note table can spell (32nd)
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SHARP_SPELL = {0: ("C", 0), 1: ("C", 1), 2: ("D", 0), 3: ("D", 1), 4: ("E", 0),
               5: ("F", 0), 6: ("F", 1), 7: ("G", 0), 8: ("G", 1), 9: ("A", 0),
               10: ("A", 1), 11: ("B", 0)}
FLAT_SPELL = {0: ("C", 0), 1: ("D", -1), 2: ("D", 0), 3: ("E", -1), 4: ("E", 0),
              5: ("F", 0), 6: ("G", -1), 7: ("G", 0), 8: ("A", -1), 9: ("A", 0),
              10: ("B", -1), 11: ("B", 0)}
MAJOR_FIFTHS = {"C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5, "F#": 6, "C#": 7,
                "F": -1, "Bb": -2, "Eb": -3, "Ab": -4, "Db": -5, "Gb": -6, "Cb": -7}
MINOR_FIFTHS = {"A": 0, "E": 1, "B": 2, "F#": 3, "C#": 4, "G#": 5, "D#": 6, "A#": 7,
                "D": -1, "G": -2, "C": -3, "F": -4, "Bb": -5, "Eb": -6, "Ab": -7}
LETTERS = ["C", "D", "E", "F", "G", "A", "B"]
MINOR_STEPS = [0, 2, 3, 5, 7, 8, 10]
MAJOR_STEPS = [0, 2, 4, 5, 7, 9, 11]
# units -> (type, dots, time-modification actual/normal) for DIV=24
NOTE_UNITS = [(96, "whole", 0, None), (72, "half", 1, None), (64, "whole", 0, (3, 2)),
              (48, "half", 0, None), (36, "quarter", 1, None), (32, "half", 0, (3, 2)),
              (24, "quarter", 0, None), (18, "eighth", 1, None), (16, "quarter", 0, (3, 2)),
              (12, "eighth", 0, None), (9, "16th", 1, None), (8, "eighth", 0, (3, 2)),
              (6, "16th", 0, None), (3, "32nd", 0, None)]
UNIT_TYPE = {u: (t, d, tm) for u, t, d, tm in NOTE_UNITS}


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


DORIAN_STEPS = [0, 2, 3, 5, 7, 9, 10]      # minor third, major sixth


def spelling_table(key, mode):
    """pc -> (step, alter) following the key signature, including chromatic notes."""
    if mode == "dorian":
        fifths = MAJOR_FIFTHS[key] - 2       # D dorian shares C major's signature
        steps = DORIAN_STEPS
    elif mode == "minor":
        fifths, steps = MINOR_FIFTHS[key], MINOR_STEPS
    else:
        fifths, steps = MAJOR_FIFTHS[key], MAJOR_STEPS
    root_pc = PC[key[0]]
    tonic_letter = LETTERS.index(key[0])
    table = {}
    for i in range(7):
        letter = LETTERS[(tonic_letter + i) % 7]
        target = (root_pc + steps[i]) % 12
        alter = (target - PC[letter]) % 12
        if alter > 6:
            alter -= 12
        table[target] = (letter, alter)
    fallback = FLAT_SPELL if fifths <= 0 else SHARP_SPELL   # no sharps in the signature -> flats read better
    for pc in range(12):
        if pc not in table:
            table[pc] = fallback[pc]
    return fifths, table


def pitch_xml(midi, table):
    pc = midi % 12
    step, alter = table[pc]
    octv = (midi - alter - PC[step]) // 12 - 1
    a = f"<alter>{alter}</alter>" if alter else ""
    return f"<step>{step}</step>{a}<octave>{octv}</octave>"


def split_units(total):
    """Decompose a duration into notatable values (largest first).

    Anything that survives the table is emitted as one block rather than
    dropped: a lost unit here shifts every following note in the bar.
    """
    out, left = [], total
    while left > 0:
        for u, _, _, _ in NOTE_UNITS:
            if u <= left:
                out.append(u)
                left -= u
                break
        else:
            out.append(left)
            left = 0
    return out or [GRID]


def qgrid(u):
    """Snap to the notation grid so durations always sum to the bar length."""
    return int(round(u / GRID)) * GRID


def type_xml(units):
    t, dots, tm = UNIT_TYPE.get(units, ("quarter", 0, None))
    out = f"<type>{t}</type>" + "<dot/>" * dots
    if tm:
        out += (f"<time-modification><actual-notes>{tm[0]}</actual-notes>"
                f"<normal-notes>{tm[1]}</normal-notes></time-modification>")
    return out


ART_XML = {"stacc": "<staccato/>", "ten": "<tenuto/>", "acc": "<accent/>",
           "marc": "<strong-accent/>"}


def serialize(voice, staff, start_u, dur_u, pitches, tie_in=False, tie_out=False,
              table=None, art="", slur_in=False, slur_out=False):
    """Emit one or more <note> elements; split non-notatable durations with ties.

    Everything notational about a note (tie, slur, articulation) has to live in
    a single <notations> element — two of them and MuseScore silently drops the
    second, which is how the first batch of sheets lost every slur.
    """
    chunks = split_units(dur_u)
    nodes, pos = [], start_u
    for idx, cu in enumerate(chunks):
        tie_s = tie_in or idx > 0
        tie_e = tie_out or idx < len(chunks) - 1
        for j, midi in enumerate(pitches):
            head = ["<note>"]
            if j > 0:
                head.append("<chord/>")
            head.append(f"<pitch>{pitch_xml(midi, table)}</pitch>")
            # tie_s means "continued from the previous note": that is a stop
            if tie_s:
                head.append('<tie type="stop"/>')
            if tie_e:
                head.append('<tie type="start"/>')
            head.append(f"<duration>{cu}</duration>")
            head.append(f"<voice>{voice}</voice>")
            head.append(type_xml(cu))
            head.append(f"<staff>{staff}</staff>")
            nots = []
            if tie_s:
                nots.append('<tied type="stop"/>')
            if tie_e:
                nots.append('<tied type="start"/>')
            if j == 0:
                if slur_out and idx == 0:
                    nots.append('<slur type="start" number="1"/>')
                if slur_in and idx == 0:
                    nots.append('<slur type="stop" number="1"/>')
                # tenuto is the unmarked default for a sustained line: printing
                # it on every melody note buries the page in dashes, so only
                # the marks that change the attack get engraved.
                if art in ART_XML and art != "ten" and idx == 0:
                    nots.append(f"<articulations>{ART_XML[art]}</articulations>")
            if nots:
                head.append("<notations>" + "".join(nots) + "</notations>")
            head.append("</note>")
            nodes.append("".join(head))
        pos += cu
    return "".join(nodes)


def rest_xml(voice, staff, units, measure=False):
    if measure:
        return (f'<note><rest measure="yes"/><duration>{units}</duration>'
                f"<voice>{voice}</voice><staff>{staff}</staff></note>")
    return (f"<note><rest/><duration>{units}</duration><voice>{voice}</voice>"
            f"{type_xml(units)}<staff>{staff}</staff></note>")


def clean_title(t):
    """CJK titles need an em space between glyphs: MuseScore's title style
    kerns them into one another otherwise (four-character titles were
    unreadable at 24 pt)."""
    raw = re.sub(r"\s+", " ", t.strip())
    cjk = [c for c in raw if c != " "]
    if cjk and all("\u2e80" <= c <= "\u9fff" for c in cjk):
        return "\u2003".join(cjk)
    return raw.replace(" ", "\u2009")


DYN_XML = {"pp": 24, "p": 34, "mp": 52, "mf": 70, "f": 88, "ff": 104,
           "fp": 62, "sf": 96, "sfz": 102, "sfp": 70}
DYN_TAG = set(DYN_XML)


def _dir_xml(inner, staff=1, offset=0, placement="below", sound=""):
    off = f"<offset>{offset}</offset>" if offset else ""
    st = f"<staff>{staff}</staff>" if staff else ""
    return (f'<direction placement="{placement}"><direction-type>{inner}'
            f"</direction-type>{off}{st}{sound}</direction>")


def expression_directions(sc, bpb):
    """bar -> [(offset_units, xml), ...] for the written performance marks.

    Pedalling is derived from expression.pedal (the same spans the renderer
    uses), so the sheet and the recording always agree about where the damper
    is down.
    """
    expr = sc.get("expression") or {}
    out = {}

    def put(bar, beat, inner, staff=1, placement="below", sound=""):
        b = int(bar) + int(beat // bpb)
        bt = beat % bpb
        out.setdefault(b, []).append((qgrid(bt * DIV), inner, staff, placement, sound))

    for m in expr.get("marks") or []:
        t = str(m.get("type", ""))
        txt = str(m.get("text", ""))
        b, bt = int(m.get("bar", 0)), float(m.get("beat", 0))
        if t == "dyn":
            tag = txt if txt in DYN_TAG else "mf"
            put(b, bt, f"<dynamics><{tag}/></dynamics>", 1, "below",
                f'<sound dynamics="{DYN_XML.get(tag, 70)}"/>')
        elif t == "wedge":
            kind = "crescendo" if txt.lower().startswith("c") else "diminuendo"
            put(b, bt, f'<wedge type="{kind}" number="1"/>')
            put(int(m.get("barTo", b + 1)), float(m.get("beatTo", 0)),
                '<wedge type="stop" number="1"/>')
        elif t == "words":
            put(b, bt, f'<words font-style="italic">{esc(txt)}</words>', 1, "above")
        elif t == "tempo":
            bpm = m.get("bpm")
            if bpm:
                # a metronome mark instead of a word: fewer collisions with the
                # rehearsal letter that usually sits on the same bar
                put(b, bt, f"<metronome><beat-unit>quarter</beat-unit>"
                           f"<per-minute>{int(bpm)}</per-minute></metronome>", 1, "above",
                    f'<sound tempo="{bpm}"/>')
            else:
                put(b, bt, f'<words font-style="italic">{esc(txt)}</words>', 1, "above")
        elif t == "rehearsal":
            put(b, bt, f"<rehearsal>{esc(txt)}</rehearsal>", 1, "above")

    spans = []
    for it in expr.get("pedal") or []:
        b, bt, du = (list(it) + [0, 0, 0])[:3]
        spans.append((float(b) + float(bt) / bpb, float(du) / bpb))
    spans.sort()
    # back-to-back spans mean the pedal is re-struck, not lifted; engrave the
    # merged span once instead of writing Ped. up / Ped. down at the same beat
    merged = []
    for start, length in spans:
        if merged and abs(merged[-1][1] - start) < 1e-6:
            merged[-1][1] = start + length
        else:
            merged.append([start, start + length])
    for start, end in merged:
        put(int(start // 1), (start % 1) * bpb, '<pedal type="start"/>', 2, "below")
        put(int(end // 1), (end % 1) * bpb, '<pedal type="stop"/>', 2, "below")
    return out


def build_xml(score_path):
    sc = json.load(open(score_path))
    ev = SL.build(score_path)
    meter = sc.get("meter", [4, 4])
    bpb = meter[0] * 4.0 / meter[1]
    nbars = len(sc["chords"])
    bar_u = int(round(bpb * DIV))
    fifths, table = spelling_table(sc["key"], sc.get("mode", "minor"))
    # MusicXML has no <mode>dorian</mode>; the signature already carries it
    xml_mode = "minor" if sc.get("mode", "minor") in ("minor", "harmonic_minor", "dorian") else "major"
    sections = sc.get("sections") or []

    voices = {1: [], 2: [], 3: []}
    for e in ev:
        if e["part"] == "melody":
            voices[1].append(e)
        elif e["part"] == "bass":
            voices[2].append(e)
        elif e["part"] == "harmony":
            voices[3].append(e)
        # 'sparkle' is an octave-doubling effect, not a written line

    # absolute position -> units, merge same-onset notes into chords, clip overlaps
    parsed = {}
    for v, lst in voices.items():
        groups = {}
        for e in lst:
            s = qgrid(e["beat"] * DIV)
            groups.setdefault(s, []).append(e)
        seq = []
        for s in sorted(groups):
            g = groups[s]
            dur = qgrid(max(x["dur"] for x in g) * DIV)
            seq.append({"start": s, "dur": max(GRID, dur),
                        "pitches": sorted({int(x["midi"]) for x in g}),
                        "art": next((x.get("art") for x in g if x.get("art")), "")})
        for i in range(len(seq) - 1):
            seq[i]["dur"] = min(seq[i]["dur"], max(GRID, qgrid(seq[i + 1]["start"] - seq[i]["start"])))
        parsed[v] = seq

    # split every note at bar lines
    per_bar = {}
    for v, seq in parsed.items():
        for n in seq:
            s, dur = n["start"], n["dur"]
            end_all = nbars * bar_u
            while dur > 0:
                bar = s // bar_u
                if bar >= nbars:
                    break
                local = s - bar * bar_u
                take = min(dur, bar_u - local)
                tin = s != n["start"]
                # never leave a tie pointing past the end of the piece
                tout = (take < dur) and (s + take < end_all)
                per_bar.setdefault(bar, {}).setdefault(v, []).append(
                    {"u": local, "dur": take, "p": n["pitches"],
                     "tin": tin, "tout": tout, "art": n.get("art", "") if s == n["start"] else ""})
                s += take
                dur -= take

    # absorb sub-1/12-beat gaps (staccato offsets from the renderer) into the note
    for bar, vd in per_bar.items():
        for v, notes in vd.items():
            notes.sort(key=lambda x: x["u"])
            for i in range(len(notes) - 1):
                gap = notes[i + 1]["u"] - (notes[i]["u"] + notes[i]["dur"])
                if 0 < gap <= GRID and not notes[i]["tout"]:
                    notes[i]["dur"] += gap
            if notes:
                gap = bar_u - (notes[-1]["u"] + notes[-1]["dur"])
                if 0 < gap <= GRID and not notes[-1]["tout"]:
                    notes[-1]["dur"] += gap

    pat = sc.get("pattern", "nocturne")
    if meter == [6, 8] or pat == "block":
        max_per = 4
    elif nbars > 24:
        max_per = 4                     # 32-bar pieces breathe at 4 bars a line
    else:
        max_per = 5
    systems = (nbars + max_per - 1) // max_per
    base, rem = divmod(nbars, systems)
    sizes = [base + (1 if i < rem else 0) for i in range(systems)]
    breaks, acc = [], 0
    for sz in sizes[:-1]:
        acc += sz
        breaks.append(acc)
    # the page turn has to land on a system break, otherwise a 30-bar piece
    # turns the page in the middle of a line and MuseScore invents an extra
    # one-bar system on the next page
    page_break = None
    if nbars > 24 and breaks:
        page_break = min(breaks, key=lambda b: abs(b - nbars / 2.0))
    # Vertical fill: MuseScore 3 only honours maxSystemDistance when vertical
    # justification is on, which a headless -S export does not do, so the gap
    # between systems has to be stated outright. Without it four systems sit in
    # the top half of the page and leave the bottom half blank.
    page_systems = systems // 2 if nbars > 24 else systems
    sys_dist = max(200, min(340, int(1200 / max(1, page_systems))))
    # a dense piece needs a slightly smaller staff or four bars will not fit
    # across the page and MuseScore orphans the last bar onto a new system
    scale = float((sc.get("sheet") or {}).get("scale", 5.5))
    expr_dirs = expression_directions(sc, bpb)
    manual_dyn_bars = {int(m.get("bar", -1)) for m in
                       ((sc.get("expression") or {}).get("marks") or [])
                       if m.get("type") == "dyn"}
    slur_start, slur_stop = set(), set()
    # a slur endpoint must sit on a note onset; if the score writes a beat
    # inside a tied note, snap outward to the nearest real attack, otherwise
    # MuseScore leaves the spanner open and drops the rest of the voice
    mel_on = sorted({int(round(e["beat"] * DIV)) for e in ev if e["part"] == "melody"})
    def snap_slur(pos, forward):
        if not mel_on:
            return None
        if forward:
            for x in mel_on:
                if x >= pos - 1:
                    return x
            return mel_on[-1]
        prev = None
        for x in mel_on:
            if x <= pos + 1:
                prev = x
            else:
                break
        return prev if prev is not None else mel_on[0]
    # MuseScore 3's MusicXML reader drops the whole voice as soon as it meets a
    # <slur>, whatever the numbering or placement (verified on 3.6.2). Legato
    # is therefore written as a word mark; pass "slurEngine": "musicxml" to
    # force the slur elements back in for other engravers.
    if (sc.get("expression") or {}).get("slurEngine") == "musicxml":
        for it in ((sc.get("expression") or {}).get("slur") or []):
            b0, bt0, b1, bt1 = (list(it) + [0, 0, 0, 0])[:4]
            p0 = int(round((float(b0) * bpb + float(bt0)) * DIV))
            p1 = int(round((float(b1) * bpb + float(bt1)) * DIV))
            s0, s1 = snap_slur(p0, True), snap_slur(p1, False)
            if s0 is not None and s1 is not None and s1 > s0:
                slur_start.add(s0)
                slur_stop.add(s1)
    for bar, vd in per_bar.items():
        for v, notes in vd.items():
            for n in notes:
                if n["tout"]:
                    nxt = sorted(vd.get(bar + 1, {}).get(v, []), key=lambda x: x["u"])
                    if not (nxt and nxt[0]["u"] == 0 and nxt[0]["p"] == n["p"]):
                        n["tout"] = False
                if n["tin"]:
                    prv = sorted(vd.get(bar - 1, {}).get(v, []), key=lambda x: x["u"])
                    if not (prv and prv[-1]["u"] + prv[-1]["dur"] == bar_u
                            and prv[-1]["p"] == n["p"]):
                        n["tin"] = False

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" '
           '"http://www.musicxml.org/dtds/partwise.dtd">',
           '<score-partwise version="3.1">',
           f"<movement-title>{esc(clean_title(sc['title']))}</movement-title>",
           '<part-list><score-part id="P1"><part-name>Piano</part-name>'
           '<score-instrument id="P1-I1"><instrument-name>Piano</instrument-name>'
           "</score-instrument>"
           '<midi-instrument id="P1-I1"><midi-channel>1</midi-channel>'
           "<midi-program>1</midi-program><volume>78</volume>"
           "</midi-instrument></score-part></part-list>",
           "<defaults>"
           f"<scaling><millimeters>{scale}</millimeters><tenths>40</tenths></scaling>"
           "<page-layout><page-height>1683</page-height><page-width>1190</page-width>"
           '<page-margins type="both"><left-margin>52</left-margin><right-margin>52</right-margin>'
           "<top-margin>48</top-margin><bottom-margin>48</bottom-margin></page-margins>"
           "</page-layout>"
           "<staff-layout><staff-distance>74</staff-distance></staff-layout>"
           f"<system-layout><system-distance>{sys_dist}</system-distance></system-layout>"
           "</defaults>",
           '<part id="P1">']

    for bar in range(nbars):
        out.append(f'<measure number="{bar + 1}">')
        if page_break is not None and bar == page_break:
            out.append('<print new-page="yes"/>')
        elif bar in breaks:
            out.append('<print new-system="yes"/>')
        if bar == 0:
            out.append("<attributes>"
                       f"<divisions>{DIV}</divisions>"
                       f"<key><fifths>{fifths}</fifths><mode>{xml_mode}</mode></key>"
                       f"<time><beats>{meter[0]}</beats><beat-type>{meter[1]}</beat-type></time>"
                       "<staves>2</staves>"
                       '<clef number="1"><sign>G</sign><line>2</line></clef>'
                       '<clef number="2"><sign>F</sign><line>4</line></clef>'
                       '<staff-details number="1"><staff-lines>5</staff-lines></staff-details>'
                       '<staff-details number="2"><staff-lines>5</staff-lines></staff-details>'
                       "</attributes>")
            out.append("<direction placement=\"above\">"
                       "<direction-type><metronome><beat-unit>quarter</beat-unit>"
                       f"<per-minute>{sc['bpm']}</per-minute></metronome></direction-type>"
                       f'<sound tempo="{sc["bpm"]}"/></direction>')

        # tempo changes / rehearsal marks / dynamics
        tempo_map = {int(b): v for b, v in (sc.get("tempo", {}).get("map") or [])}
        rit = sc.get("tempo", {}).get("rit") or {}
        for s in sections:
            if s["bars"][0] == bar and (s["bars"][1] - s["bars"][0]) > 1:
                out.append('<direction placement="above"><direction-type>'
                           f"<rehearsal>{esc(s['name'])}</rehearsal></direction-type></direction>")
                if s["bars"][0] not in manual_dyn_bars:
                    dyn = float(s.get("dynamic", 1.0))
                    mark = "mf" if dyn >= 0.99 else ("mp" if dyn >= 0.92 else "p")
                    out.append('<direction placement="below"><direction-type>'
                               f"<dynamics><{mark}/></dynamics></direction-type>"
                               f"<staff>1</staff>"
                               f'<sound dynamics="{DYN_XML[mark]}"/></direction>')
        if bar in tempo_map and bar > 0:
            out.append('<direction placement="above"><direction-type><metronome>'
                       "<beat-unit>quarter</beat-unit>"
                       f"<per-minute>{tempo_map[bar]}</per-minute></metronome>"
                       f'</direction-type><sound tempo="{tempo_map[bar]}"/></direction>')
        if rit and int(rit.get("bar", -1)) == bar:
            out.append('<direction placement="above"><direction-type>'
                       '<words font-style="italic">rit.</words></direction-type></direction>')
        # written expression: dynamics, wedges, pedal, tempo words
        for off, inner, st, pl, snd in sorted(expr_dirs.get(bar, []), key=lambda x: x[0]):
            out.append(_dir_xml(inner, st, off, pl, snd))

        for v, staff in ((1, 1), (2, 2), (3, 2)):
            notes = sorted(per_bar.get(bar, {}).get(v, []), key=lambda x: x["u"])
            if not notes:
                continue
            pos = 0
            for n in notes:
                if n["u"] > pos:
                    for chunk in split_units(n["u"] - pos):
                        out.append(rest_xml(v, staff, chunk))
                abs_u = bar * bar_u + n["u"]
                out.append(serialize(v, staff, n["u"], n["dur"], n["p"],
                                     n["tin"], n["tout"], table,
                                     n.get("art", ""),
                                     v == 1 and abs_u in slur_stop,
                                     v == 1 and abs_u in slur_start))
                pos = n["u"] + n["dur"]
            if pos < bar_u:
                for chunk in split_units(bar_u - pos):
                    out.append(rest_xml(v, staff, chunk))
            if v != 3:
                out.append(f"<backup><duration>{bar_u}</duration></backup>")
        out.append("</measure>")
    out.append("</part></score-partwise>")
    return "\n".join(out)


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    xml = build_xml(src)
    open(dst, "w", encoding="utf-8").write(xml)
    print("wrote", dst, len(xml), "bytes")
