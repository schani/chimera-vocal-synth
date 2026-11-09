"""Schubert, Ave Maria D 839 (Mutopia 1054): melody files for `chimera render notes` and a pedalled
piano MIDI, from LilyPond's event-listener output (<out>/ly/score-voice.notes, score-unnamed-staff.notes)
and its MIDI (<out>/ly/score.midi). Usage: build.py [out]. Everything shares the MIDI's timeline: score moment 0 = one quarter in."""
import json, os, re, sys
import mido
from german import syllable, melisma

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
LY = os.path.join(OUT, "ly")
os.makedirs(OUT, exist_ok=True)
mid = mido.MidiFile(f"{LY}/score.midi")
TPB = mid.ticks_per_beat
tempo = next(x.tempo for x in mid.tracks[0] if x.type == "set_tempo")
BPM = 60e6 / tempo
T0 = 60 / BPM  # the MIDI's leading partial quarter

# ---- melody: notes (moment in whole notes, grace offset, midi, length) and the syllable moments
notes, ties = [], set()
for line in open(f"{LY}/score-voice.notes"):
    p = line.rstrip("\n").split("\t")
    m, g = (p[0].split("-") + ["0"])[:2]
    m, g = float(m), float(g)
    if p[1] == "note":
        notes.append({"at": m, "grace": g, "midi": int(p[2]), "len": float(p[4])})
    elif p[1] == "tie":
        ties.add(m)
syl = []  # (moment, text, continues word)
for line in open(f"{LY}/score-unnamed-staff.notes"):
    p = line.rstrip("\n").split("\t")
    if p[1] == "lyric":
        syl.append([float(p[0]), p[2], False])
    elif p[1] == "hyphen":
        syl[-1][2] = True

# each syllable (by moment) -> the engine's syllable, in sung German
spelled = {m: syllable(text, not cont) for m, text, cont in syl}
assert len(spelled) == len(syl), "two syllables at one moment"

# realize graces: appoggiatura (one grace before a note >= 1/8) takes half the main note on the beat;
# other graces take up to half the previous note, before the beat
main = [n for n in notes if n["grace"] == 0]
graces = [n for n in notes if n["grace"] > 0]
events = []  # [start, end, midi, syllable moment or None]
for n in main:
    events.append([n["at"], n["at"] + n["len"], n["midi"], n["at"] if n["at"] in spelled else None])
events.sort()
for at in sorted({g["at"] for g in graces}):
    gs = sorted((g for g in graces if g["at"] == at), key=lambda g: -g["grace"])
    k = next(i for i, e in enumerate(events) if abs(e[0] - at) < 1e-9)
    e = events[k]
    if len(gs) == 1 and e[1] - e[0] >= 0.125 - 1e-9:
        half = (e[1] - e[0]) / 2
        events.insert(k, [e[0], e[0] + half, gs[0]["midi"], e[3]])
        e[0], e[3] = e[0] + half, None
    else:
        prev = events[k - 1]
        span = min(sum(g["len"] for g in gs), (prev[1] - prev[0]) / 2)
        prev[1] -= span
        t = prev[1]
        new = []
        for i, g in enumerate(gs):
            new.append([t, t + span / len(gs), g["midi"], e[3] if i == 0 else None])
            t += span / len(gs)
        e[3] = None
        events[k:k] = new
# ties: merge the note after a tie into the tied note
merged = []
for e in events:
    if merged and any(abs(merged[-1][0] - t) < 1e-9 for t in ties) and merged[-1][2] == e[2] and abs(merged[-1][1] - e[0]) < 1e-9:
        merged[-1][1] = e[1]
        continue
    merged.append(e)
events = merged

# notes list with rests (beats); one syllable per sounding note, melisma notes carry the vowel on
out_notes, syls, t = [], [], 0.0
for s0, e, p, sm in events:
    if s0 > t + 1e-9:
        out_notes.append([0, (s0 - t) * 4])
    out_notes.append([p, (e - s0) * 4])
    if sm is not None:
        syls.append(dict(spelled[sm]))
    else:
        m = melisma(syls[-1])
        m["phraseEnd"], syls[-1]["phraseEnd"] = syls[-1]["phraseEnd"], False  # the breath after the run
        syls.append(m)
    t = e
used = sum(1 for e in events if e[3] is not None)
assert used == len(syl), (used, len(syl))
words, cur = [], ""
for m, text, cont in syl:
    cur += text + ("-" if cont else "")
    if not cont:
        words.append(cur); cur = ""
lyr = " ".join(words)
melody = {"bpm": BPM, "t0": T0, "vibrato": 40, "lyrics": lyr, "syllables": syls, "notes": out_notes}
for body, shift in (("female", 0), ("male", -12), ("child", 0)):
    mm = dict(melody, notes=[[p + shift if p > 0 else p, b] for p, b in out_notes])
    json.dump(mm, open(f"{OUT}/voice-{body}.json", "w"))
print(f"bpm {BPM:.2f}, {len(events)} notes, {len(syl)} syllables, {sum(b for _, b in out_notes):.1f} beats")

# ---- piano: the MIDI's piano tracks, sustain pedal re-taken on every beat (the source has none)
pm = mido.MidiFile(ticks_per_beat=TPB)
pm.tracks.append(mid.tracks[0])
pm.tracks += [mid.tracks[2], mid.tracks[3]]
end = max(sum(x.time for x in tr) for tr in mid.tracks)
ped, tick = mido.MidiTrack(), 0
abs_ev = []
for b in range(1, end // TPB + 1):
    on = b * TPB
    abs_ev += [(on + 8, 0), (on + 40, 127)]
for at, v in sorted(abs_ev):
    ped.append(mido.Message("control_change", channel=1, control=64, value=v, time=at - tick)); tick = at
pm.tracks.append(ped)
# the piano tracks use channels 1 and 2: pedal both
ch = sorted({x.channel for tr in pm.tracks for x in tr if x.type == "note_on"})
pm.tracks[-1] = mido.MidiTrack()
merged_ped = sorted([(at, c, v) for at, v in abs_ev for c in ch])
tick = 0
for at, c, v in merged_ped:
    pm.tracks[-1].append(mido.Message("control_change", channel=c, control=64, value=v, time=at - tick)); tick = at
pm.save(f"{OUT}/piano.mid")
print("piano channels", ch, "length", round(pm.length, 1), "s")
