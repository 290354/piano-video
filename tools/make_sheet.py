#!/usr/bin/env python3
#!/usr/bin/env python3
"""make_sheet.py — score.json -> engraved MusicXML (grand staff).

    python3 tools/make_sheet.py scores/daily_20261121.json out/sheet/daily_20261121.musicxml

Then open the .musicxml in MuseScore Studio and export PDF / .mscz, or run
    mscore3 -o out/sheet/daily_20261121.pdf out/sheet/daily_20261121.musicxml


The notes are NOT re-derived: they come from pipeline/score_loader.build(),
the same function the video renderer uses, so the sheet matches the audio.
"""
import json, os, re, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import score_loader as SL

DIV = 24                     # divisions per quarter note (exact sixths & triplets)
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


def spelling_table(key, mode):
    """pc -> (step, alter) following the key signature, including chromatic notes."""
    fifths = (MINOR_FIFTHS if mode == "minor" else MAJOR_FIFTHS)[key]
    root_pc = PC[key[0]]
    steps = MINOR_STEPS if mode == "minor" else MAJOR_STEPS
    tonic_letter = LETTERS.index(key[0])
    table = {}
    for i in range(7):
        letter = LETTERS[(tonic_letter + i) % 7]
        target = (root_pc + steps[i]) % 12
        alter = (target - PC[letter]) % 12
        if alter > 6:
            alter -= 12
        table[target] = (letter, alter)
    fallback = FLAT_SPELL if fifths < 0 else SHARP_SPELL
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
    """Decompose a duration into notatable values (largest first)."""
    out, left = [], total
    while left > 0:
        for u, _, _, _ in NOTE_UNITS:
            if u <= left:
                out.append(u)
                left -= u
                break
        else:
            break
    return out or [1]


def type_xml(units):
    t, dots, tm = UNIT_TYPE.get(units, ("quarter", 0, None))
    out = f"<type>{t}</type>" + "<dot/>" * dots
    if tm:
        out += (f"<time-modification><actual-notes>{tm[0]}</actual-notes>"
                f"<normal-notes>{tm[1]}</normal-notes></time-modification>")
    return out


def serialize(voice, staff, start_u, dur_u, pitches, tie_in=False, tie_out=False,
              table=None):
    """Emit one or more <note> elements; split non-notatable durations with ties."""
    chunks = split_units(dur_u)
    nodes, pos, first = [], start_u, True
    for idx, cu in enumerate(chunks):
        tie_s = tie_in or idx > 0
        tie_e = tie_out or idx < len(chunks) - 1
        for j, midi in enumerate(pitches):
            head = ["<note>"]
            if j > 0:
                head.append("<chord/>")
            head.append(f"<pitch>{pitch_xml(midi, table)}</pitch>")
            if tie_s:
                head.append('<tie type="start"/>')
            if tie_e:
                head.append('<tie type="stop"/>')
            head.append(f"<duration>{cu}</duration>")
            head.append(f"<voice>{voice}</voice>")
            head.append(type_xml(cu))
            head.append(f"<staff>{staff}</staff>")
            if tie_s or tie_e:
                nt = ('<tied type="stop"/>' if tie_e else "") + \
                     ('<tied type="start"/>' if tie_s else "")
                head.append(f"<notations>{nt}</notations>")
            head.append("</note>")
            nodes.append("".join(head))
        pos += cu
        first = False
    return "".join(nodes)


def rest_xml(voice, staff, units, measure=False):
    if measure:
        return (f'<note><rest measure="yes"/><duration>{units}</duration>'
                f"<voice>{voice}</voice><staff>{staff}</staff></note>")
    return (f"<note><rest/><duration>{units}</duration><voice>{voice}</voice>"
            f"{type_xml(units)}<staff>{staff}</staff></note>")


def clean_title(t):
    return re.sub(r"\s+", " ", t.strip()).replace(" ", "\u2009")


def build_xml(score_path):
    sc = json.load(open(score_path))
    ev = SL.build(score_path)
    meter = sc.get("meter", [4, 4])
    bpb = meter[0] * 4.0 / meter[1]
    nbars = len(sc["chords"])
    bar_u = int(round(bpb * DIV))
    fifths, table = spelling_table(sc["key"], sc.get("mode", "minor"))
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
            s = int(round(e["beat"] * DIV))
            groups.setdefault(s, []).append(e)
        seq = []
        for s in sorted(groups):
            g = groups[s]
            dur = int(round(max(x["dur"] for x in g) * DIV))
            seq.append({"start": s, "dur": max(1, dur),
                        "pitches": sorted({int(x["midi"]) for x in g})})
        for i in range(len(seq) - 1):
            seq[i]["dur"] = min(seq[i]["dur"], max(1, seq[i + 1]["start"] - seq[i]["start"]))
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
                     "tin": tin, "tout": tout})
                s += take
                dur -= take

    # absorb sub-1/12-beat gaps (staccato offsets from the renderer) into the note
    for bar, vd in per_bar.items():
        for v, notes in vd.items():
            notes.sort(key=lambda x: x["u"])
            for i in range(len(notes) - 1):
                gap = notes[i + 1]["u"] - (notes[i]["u"] + notes[i]["dur"])
                if 0 < gap <= 2 and not notes[i]["tout"]:
                    notes[i]["dur"] += gap
            if notes:
                gap = bar_u - (notes[-1]["u"] + notes[-1]["dur"])
                if 0 < gap <= 2 and not notes[-1]["tout"]:
                    notes[-1]["dur"] += gap

    pat = sc.get("pattern", "nocturne")
    max_per = 4 if meter == [6, 8] else (5 if pat in ("arpeggio", "block") else 6)
    systems = (nbars + max_per - 1) // max_per
    base, rem = divmod(nbars, systems)
    sizes = [base + (1 if i < rem else 0) for i in range(systems)]
    breaks, acc = [], 0
    for sz in sizes[:-1]:
        acc += sz
        breaks.append(acc)
    sys_dist = max(120, min(260, int(1040 / max(1, systems))))
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" '
           '"http://www.musicxml.org/dtds/partwise.dtd">',
           '<score-partwise version="3.1">',
           f"<work><work-title>{esc(clean_title(sc['title']))}</work-title></work>",
           f"<movement-title>{esc(clean_title(sc['title']))}</movement-title>",
           "<identification>",
           '<creator type="composer">piano-video · 生成式钢琴</creator>',
           '<encoding><software>piano-video sheet generator</software>'
           f"<encoding-date>{sc.get('date', '')}</encoding-date></encoding>",
           "</identification>",
           '<part-list><score-part id="P1"><part-name>Piano</part-name>'
           '<score-instrument id="P1-I1"><instrument-name>Piano</instrument-name>'
           "</score-instrument>"
           '<midi-instrument id="P1-I1"><midi-channel>1</midi-channel>'
           "<midi-program>1</midi-program><volume>78</volume>"
           "</midi-instrument></score-part></part-list>",
           "<defaults>"
           "<scaling><millimeters>5.2</millimeters><tenths>40</tenths></scaling>"
           "<page-layout><page-height>1683</page-height><page-width>1190</page-width>"
           '<page-margins type="both"><left-margin>52</left-margin><right-margin>52</right-margin>'
           "<top-margin>48</top-margin><bottom-margin>48</bottom-margin></page-margins>"
           "</page-layout>"
           "<system-layout><system-margins><left-margin>0</left-margin>"
           "<right-margin>0</right-margin></system-margins>"
           f"<system-distance>{sys_dist}</system-distance>"
           f"<top-system-distance>{max(120, sys_dist - 40)}</top-system-distance>"
           "</system-layout>"
           "<staff-layout><staff-distance>62</staff-distance></staff-layout>"
           "</defaults>",
           '<part id="P1">']

    # page / staff layout
    out.append('<credit page="1"><credit-type>subtitle</credit-type>'
               f'<credit-words default-x="595" default-y="1500" justify="center" '
               f'valign="top" font-size="11">{esc(sc.get("titleEn", "").upper())}'
               f"　·　{esc(sc['key'])} {esc(sc.get('mode', 'minor'))}"
               f"　·　{sc['bpm']} BPM</credit-words></credit>")

    for bar in range(nbars):
        out.append(f'<measure number="{bar + 1}">')
        if bar in breaks:
            out.append('<print new-system="yes"/>')
        if bar == 0:
            out.append("<attributes>"
                       f"<divisions>{DIV}</divisions>"
                       f"<key><fifths>{fifths}</fifths><mode>{sc.get('mode', 'minor')}</mode></key>"
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
            if s["bars"][0] == bar:
                out.append('<direction placement="above"><direction-type>'
                           f"<rehearsal>{esc(s['name'])}</rehearsal></direction-type></direction>")
                dyn = float(s.get("dynamic", 1.0))
                mark = "mf" if dyn >= 0.99 else ("mp" if dyn >= 0.92 else "p")
                out.append('<direction placement="below"><direction-type>'
                           f"<dynamics><{mark}/></dynamics></direction-type>"
                           f"<staff>1</staff></direction>")
        if bar in tempo_map and bar > 0:
            out.append('<direction placement="above"><direction-type><metronome>'
                       "<beat-unit>quarter</beat-unit>"
                       f"<per-minute>{tempo_map[bar]}</per-minute></metronome>"
                       f'</direction-type><sound tempo="{tempo_map[bar]}"/></direction>')
        if rit and int(rit.get("bar", -1)) == bar:
            out.append('<direction placement="above"><direction-type>'
                       '<words font-style="italic">rit.</words></direction-type></direction>')

        for v, staff in ((1, 1), (2, 2), (3, 2)):
            notes = sorted(per_bar.get(bar, {}).get(v, []), key=lambda x: x["u"])
            if not notes:
                continue
            pos = 0
            for n in notes:
                if n["u"] > pos:
                    for chunk in split_units(n["u"] - pos):
                        out.append(rest_xml(v, staff, chunk))
                out.append(serialize(v, staff, n["u"], n["dur"], n["p"],
                                     n["tin"], n["tout"], table))
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
