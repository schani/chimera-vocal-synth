"""Holst, 'Cranham' (In the Bleak Midwinter), English Hymnal 1906 SATB, all five verses, a cappella:
one melody file per singer for `chimera render notes`, from Open Hymnal's ABC.

- Soprano: the verse's syllables in order; "*"/"_" carry the vowel on; a verse number alone on the
  optional pickup is a rest. Alto, tenor, bass: a soprano syllable that starts on their note is
  theirs, else they carry the vowel on; a note a soprano syllable starts inside is split. When the
  sopranos sing the pickup, the lower parts sing it too, on their next pitch.
- Time: q = 66, a breath of one beat between verses, a slight rit. at each verse end and a broad
  one with a held last chord at the end. Files are at bpm 60 (beats = seconds).
- Several singers per part, each a different body blend, detuned and offset a little."""
import json, subprocess, sys, os
from abcparse import parse

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out")
CHIMERA = os.environ.get("CHIMERA") or os.path.join(HERE, "../../target/release/chimera")
os.makedirs(OUT, exist_ok=True)
voices, verses = parse(os.path.join(HERE, "In_The_Bleak_MidWinter-Cranham.abc"))
PARTS = {"soprano": "S1V1", "alto": "S1V2", "tenor": "S2V1", "bass": "S2V2"}
RESPELL = {"our": "owr", "beloved": "be-luv-id"}  # the dictionary says 2 syllables / 2 syllables
VERSE_BEATS, GAP = 64.0, 1.0
SINGERS = {  # (body, cents, ms, vibrato cents)
    "soprano": [("female", 0, 0, 38), ("mix:0.85,0.1", 6, 14, 30), ("child", -5, -9, 22)],
    "alto": [("female", 0, 6, 34), ("mix:0.85,0", -6, -11, 28), ("mix:0.7,0", 5, 17, 30)],
    "tenor": [("male", 0, 0, 34), ("mix:0.15,0", 6, 12, 28), ("mix:0.08,0.05", -5, -15, 30)],
    "bass": [("male", 0, 8, 30), ("mix:0.05,0", -6, -8, 26), ("male", 5, 19, 32)],
}

# ---- tempo: seconds per beat over the global beat axis
Q = 60 / 66
def spb(b):
    k, local = divmod(b, VERSE_BEATS + GAP)
    s = Q
    if k < 4 and local > VERSE_BEATS - 4:  # each verse's last bar broadens a little
        s *= 1 + 0.18 * (local - (VERSE_BEATS - 4)) / 4
    if k == 4 and local > VERSE_BEATS - 10:  # the last line broadens more
        s *= 1 + 0.55 * min(1, (local - (VERSE_BEATS - 10)) / 9)
    if k == 4 and local > VERSE_BEATS - 3:  # and the last chord is held
        s *= 1.6
    return s
TABLE, acc, step = [0.0], 0.0, 1 / 64
for i in range(int(5 * (VERSE_BEATS + GAP) / step) + 2):
    acc += spb(i * step) * step
    TABLE.append(acc)
def sec(b):
    i = b / step; j = int(i)
    return TABLE[j] + (TABLE[j + 1] - TABLE[j]) * (i - j)


def verse_syllables(toks):
    """the dictionary's syllables for the verse's sung tokens, shown with the hymn's spelling"""
    words, cur = [], []
    for t in toks:
        if t[0] == "syl":
            cur.append(t[1])
            if not t[2]:
                words.append(cur); cur = []
    def spoken(w):
        bare = "".join(w).strip(",.;:?!").lower()
        punct = "".join(w)[len("".join(w).rstrip(",.;:?!")):]
        return RESPELL.get(bare, "".join(w).rstrip(",.;:?!")) + punct
    out = json.loads(subprocess.check_output([CHIMERA, "syllables", " ".join(spoken(w) for w in words)]))
    flat = [p for w in words for p in w]
    assert len(out) == len(flat), (len(out), len(flat))
    for s, text in zip(out, flat):
        s["text"] = text.rstrip(",.;:?!")
    return out


def melisma(prev):
    return {"text": "~", "onset": [], "nucleus": dict(prev["nucleus"]), "coda": [], "melisma": True,
            "wordEnd": prev["wordEnd"], "phraseEnd": False}


def part_events(part, toks, syls):
    """[(onset, len, midi, syllable index | None)] for one verse; None = carries the vowel on"""
    sop = voices["S1V1"]
    k, at_syl = 0, {}
    for n, t in zip(sop, toks):
        if t[0] == "syl":
            at_syl[n.onset] = k; k += 1
    if part == "S1V1":
        ev = []
        for n, t in zip(sop, toks):
            if t[0] == "blank":
                continue
            ev.append([n.onset, n.len, n.midi, at_syl.get(n.onset) if t[0] == "syl" else None])
        return ev
    notes = [n for n in voices[part] if n.midi > 0]
    ev = []
    if 0.0 in at_syl and notes[0].onset > 0:  # the sopranos' pickup: everyone sings it
        ev.append([0.0, notes[0].onset, notes[0].midi, at_syl[0.0]])
    for n in notes:
        cuts = sorted(o for o in at_syl if n.onset < o < n.onset + n.len - 1e-9)
        edges = [n.onset] + cuts + [n.onset + n.len]
        for a, b in zip(edges, edges[1:]):
            ev.append([a, b - a, n.midi, at_syl.get(a)])
    return ev


def build_part(part):
    """all verses: [(global beat, beats, midi, syllable dict)]"""
    out = []
    for v, toks in enumerate(verses):
        syls = verse_syllables(toks)
        base = v * (VERSE_BEATS + GAP)
        for on, ln, midi, si in part_events(PARTS_INV[part], toks, syls):
            if si is None and out and out[-1][2] == midi and abs(out[-1][0] + out[-1][1] - (base + on)) < 1e-9:
                out[-1][1] += ln  # a held vowel on the same pitch: one note
                continue
            if si is None:
                s = melisma(out[-1][3])
                s["phraseEnd"], out[-1][3]["phraseEnd"] = out[-1][3]["phraseEnd"], False
            else:
                s = dict(syls[si])
            out.append([base + on, ln, midi, s])
    return out


PARTS_INV = {k: v for k, v in PARTS.items()}
LEAD = 1.0
for part, singers in SINGERS.items():
    ev = build_part(part)
    for i, (body, cents, ms, vib) in enumerate(singers):
        notes, syls, t = [], [], 0.0
        for b, ln, midi, s in ev:
            s0, s1 = sec(b), sec(b + ln)
            if s0 > t + 1e-6:
                notes.append([0, s0 - t])
            notes.append([midi + cents / 100, s1 - s0])
            syls.append(s)
            t = s1
        mel = {"bpm": 60, "t0": LEAD + ms / 1000, "vibrato": vib, "syllables": syls, "notes": notes,
               "lyrics": " ".join(s["text"] for s in syls if s["text"] != "~")}
        json.dump(mel, open(f"{OUT}/{part}{i + 1}.json", "w"))
        open(f"{OUT}/{part}{i + 1}.body", "w").write(body)
    print(part, len(ev), "notes,", f"{sec(ev[-1][0] + ev[-1][1]):.1f} s")

# verse starts and the end (s, on the singers' timeline), for the mix's dynamics
json.dump({"lead": LEAD, "verses": [LEAD + sec(v * (VERSE_BEATS + GAP)) for v in range(5)],
           "lastLine": LEAD + sec(4 * (VERSE_BEATS + GAP) + VERSE_BEATS - 10), "end": LEAD + sec(5 * (VERSE_BEATS + GAP) - GAP)},
          open(f"{OUT}/timing.json", "w"))
