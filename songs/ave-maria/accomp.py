"""Ave Maria's piano part sung by three voices, on the melody's timeline (score moment 0 = one
quarter into the MIDI; ly/score-up.notes and score-down.notes from LilyPond's event listener):
- bass (male): the left hand's octaves, the upper note (an octave up below F2), one "doo" each;
- alto (darker female): the right hand's lower notes, each beat's five-note ripple on one "loo";
- descant (child): the right hand's upper notes, the same way.
The final chords give the alto their lowest note and the descant their highest.
usage: accomp.py <out dir> (run in the folder holding ly/)"""
import json, os, sys
from collections import defaultdict

OUT = sys.argv[1] if len(sys.argv) > 1 else "out3"
os.makedirs(OUT, exist_ok=True)
BPM, T0 = 26.0, 60 / 26.0  # as build.py: the MIDI's tempo and its leading partial quarter


def chords(path):
    ch = defaultdict(list)
    for line in open(path):
        p = line.rstrip("\n").split("\t")
        if p[1] == "note":
            ch[float(p[0])].append((int(p[2]), float(p[4])))
    return sorted(ch.items())


def melody(events, word):
    """events [(moment, length, midi)] -> render-notes melody: a new `word` after every rest,
    the vowel carried on ("~") through notes that follow without one"""
    notes, toks, t = [], [], 0.0
    for at, ln, midi in events:
        if at > t + 1e-9:
            notes.append([0, (at - t) * 4])
        toks.append("~" if toks and at <= t + 1e-9 else word)
        notes.append([midi, ln * 4])
        t = at + ln
    return {"bpm": BPM, "t0": T0, "vibrato": 20, "lyrics": " ".join(toks), "notes": notes}


up, down = chords("ly/score-up.notes"), chords("ly/score-down.notes")
alto = [(at, ns[0][1], min(m for m, _ in ns)) for at, ns in up]
alto = [(at, ln, m + 12 if m < 55 else m) for at, ln, m in alto]
descant = [(at, ns[0][1], max(m for m, _ in ns)) for at, ns in up]
bass = [(at, ns[0][1], max(m for m, _ in ns)) for at, ns in down]
bass = [(at, ln, m + 12 if m < 41 else m) for at, ln, m in bass]
for name, ev, word in (("bass", bass, "doo"), ("alto", alto, "loo"), ("descant", descant, "loo")):
    m = melody(ev, word)
    json.dump(m, open(f"{OUT}/{name}.json", "w"))
    pitches = [n for n, _ in m["notes"] if n > 0]
    print(f"{name}: {len(pitches)} notes, {m['lyrics'].count(word)} words, midi {min(pitches)}-{max(pitches)}")
