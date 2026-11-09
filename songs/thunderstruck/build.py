"""Thunderstruck from the user's MuseScore arrangement (out/score-patched.musicxml, from patch_score.py: P2's three
wordless "Thun-der" chants given their words). Writes, into out/:
- lead.json, p2_1..3.json, p3_1..3.json (+ .body): melody files at bpm 60 (beats = seconds) on the
  score's tempo map, from tools/musicxml-to-notes.ts output (P1/P2/P3.json at 140 bpm), with the
  rock voice: belt (pressure, pressed, bright), twang, the false folds held narrow; the backing parts
  as gang vocals.
- band-score.mid (the arrangement's own instruments) and band-electric.mid (distorted guitars,
  picked bass, and a plain rock beat added where the bass plays: the score has no drum kit)."""
import json, os, sys
import mido
from music21 import converter, tempo

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
s = converter.parse(f"{OUT}/score-patched.musicxml")
marks = sorted((float(m.getOffsetBySite(s.flatten())), float(m.number)) for m in s.flatten().getElementsByClass(tempo.MetronomeMark))
marks = [m for i, m in enumerate(marks) if i == 0 or m[0] != marks[i - 1][0]]

def sec(b):
    """quarter beats -> seconds on the score's tempo map"""
    t, (pb, bpm) = 0.0, marks[0]
    for ob, nb in marks[1:]:
        if b <= ob:
            break
        t += (ob - pb) * 60 / bpm
        pb, bpm = ob, nb
    return t + (b - pb) * 60 / bpm

LEAD = 0.5  # s of silence before beat 0 (consonants land before the beat)
ROCK = {"source": {"pressure": 14, "tension": 0.8, "brightness": 0.6, "roughness": 0.3},
        "artic": {"epilarynx": 0.6, "ventricular": 0.5}, "vibrato": 18}
GANG = {"source": {"pressure": 13, "tension": 0.75, "brightness": 0.55, "roughness": 0.35},
        "artic": {"epilarynx": 0.4, "ventricular": 0.4}, "vibrato": 10}

def retime(m, cents=0.0, ms=0.0, extra=None):
    assert abs(m["bpm"] - 140) < 1e-6
    b, notes = 0.0, []
    for midi, beats in m["notes"]:
        notes.append([midi + cents / 100 if midi > 0 else midi, sec(b + beats) - sec(b)])
        b += beats
    t0 = m.get("t0", 0.0) * 140 / 60  # the tool's t0 is in seconds at 140
    out = {k: v for k, v in m.items() if k not in ("notes", "bpm", "t0")}
    out.update({"bpm": 60, "t0": LEAD + sec(t0) + ms / 1000, "notes": notes})
    out.update(extra or {})
    return out

jobs = []
p1 = json.load(open(f"{OUT}/P1.json"))
json.dump(retime(p1, extra=ROCK), open(f"{OUT}/lead.json", "w")); jobs.append(("lead", "male"))
for part in ("P2", "P3"):
    m = json.load(open(f"{OUT}/{part}.json"))
    for i, (body, cents, ms) in enumerate([("male", 0, 0), ("mix:0.1,0", 9, 16), ("mix:0.05,0.05", -8, -12)], 1):
        name = f"{part.lower()}_{i}"
        json.dump(retime(m, cents, ms, GANG), open(f"{OUT}/{name}.json", "w")); jobs.append((name, body))
open(f"{OUT}/jobs.txt", "w").write("".join(f"{n} {b}\n" for n, b in jobs))
end = sec(568.0)
json.dump({"lead": LEAD, "end": LEAD + end}, open(f"{OUT}/timing.json", "w"))

# ---- the band as MIDI, on the same timeline (LEAD of silence first)
TPB = 480
def band(path, programs, drums):
    mf = mido.MidiFile(ticks_per_beat=TPB)
    meta = mido.MidiTrack(); mf.tracks.append(meta)
    meta.append(mido.MetaMessage("set_tempo", tempo=int(LEAD * 1e6), time=0))  # one beat of lead-in = LEAD s
    t_prev = 0
    for ob, bpm in marks:
        at = (1 + ob) * TPB
        meta.append(mido.MetaMessage("set_tempo", tempo=int(60e6 / bpm), time=int(at - t_prev))); t_prev = at
    ch = 0
    for p in s.parts:
        name = p.partName
        if name not in programs:
            continue
        prog, vel, chan = programs[name]
        if chan is None:
            chan = ch; ch += 1
            if ch == 9: ch += 1
        ev = []
        for n in p.flatten().notes:
            if n.tie and n.tie.type in ("stop", "continue"):
                continue
            on = (1 + float(n.getOffsetInHierarchy(s))) * TPB
            dur = float(n.quarterLength)
            nx = n
            while nx.tie and nx.tie.type in ("start", "continue"):
                nx = nx.next("Note") or nx.next("Chord")
                if nx is None: break
                dur += float(nx.quarterLength)
            off = on + max(0.05, dur * (0.9 if chan != 9 else 0.25)) * TPB
            keys = [x.midi for x in n.pitches] if (n.isChord or hasattr(n, "pitch")) else [prog]
            if chan == 9:
                keys = [prog]
            for k in keys:
                ev += [(int(on), 1, k), (int(off), 0, k)]
        tr = mido.MidiTrack(); mf.tracks.append(tr)
        if chan != 9:
            tr.append(mido.Message("program_change", channel=chan, program=prog, time=0))
        t = 0
        for at, kind, k in sorted(ev, key=lambda e: (e[0], e[1])):
            tr.append(mido.Message("note_on", channel=chan, note=k, velocity=vel if kind else 0, time=at - t)); t = at
    if drums:
        # a plain rock beat in every bar where the bass plays: kick 1 & 3, snare 2 & 4, hat eighths
        bass = next(p for p in s.parts if p.partName == "Electric Bass")
        bars = sorted({int(float(n.getOffsetInHierarchy(s)) // 4) for n in bass.flatten().notes})
        ev = []
        for bar in bars:
            for q in range(8):
                at = (1 + bar * 4 + q * 0.5) * TPB
                hits = [(42, 70 if q % 2 else 85)]
                if q in (0, 4): hits.append((36, 110))
                if q in (2, 6): hits.append((38, 105))
                if q == 0 and (bar == bars[0] or bar - 1 not in bars): hits.append((49, 100))
                for k, v in hits:
                    ev += [(int(at), 1, k, v), (int(at + TPB * 0.2), 0, k, 0)]
        tr = mido.MidiTrack(); mf.tracks.append(tr); t = 0
        for at, kind, k, v in sorted(ev, key=lambda e: (e[0], e[1])):
            tr.append(mido.Message("note_on", channel=9, note=k, velocity=v if kind else 0, time=at - t)); t = at
    mf.save(path)
    print(path, round(mf.length, 1), "s")

band(f"{OUT}/band-score.mid", {"Banjo": (105, 92, None), "Acoustic Guitar": (25, 80, None), "Melodica": (22, 78, None),
                               "Electric Bass": (33, 100, None), "Metal Castanets": (67, 70, 9), "Anvil": (53, 90, 9)}, False)
band(f"{OUT}/band-electric.mid", {"Banjo": (29, 95, None), "Acoustic Guitar": (30, 88, None), "Melodica": (29, 88, None),
                                  "Electric Bass": (34, 105, None), "Metal Castanets": (42, 55, 9), "Anvil": (53, 90, 9)}, True)
print("jobs", jobs, "end", round(LEAD + end, 1), "s")
