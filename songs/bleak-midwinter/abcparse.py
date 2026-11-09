"""The subset of ABC that Open Hymnal's 'In The Bleak MidWinter' (Cranham) uses: four voices, notes
with accidentals/octaves/lengths, rests, ties (".-" is an optional tie: one verse sings two
syllables, another holds), slurs, decorations; and the soprano's verse lines (w:).
parse(path) -> {voice: [Note]}, [verses: [tokens]] where a Note has onset/len in quarter beats."""
import re
from dataclasses import dataclass, field

STEP = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
KEY_F = {"B": -1}


@dataclass
class Note:
    onset: float
    len: float
    midi: int  # 0: rest
    tie: bool = False  # tied (or optionally tied) to the next note
    optional: bool = False  # the pickup written !()! (sung only by verses that put a syllable on it)


NOTE = re.compile(r"(\^|_|=)?([A-Ga-g])([,']*)(\d*)(/?)(\d*)")


def parse_body(text):
    notes, t, acc = [], 0.0, {}
    i, optional_next = 0, False
    while i < len(text):
        c = text[i]
        if c == "!":
            j = text.index("!", i + 1)
            optional_next = text[i + 1:j] == "()"
            i = j + 1
        elif c == "[" and re.match(r"\[[A-Z]:", text[i:]):
            i = text.index("]", i) + 1
        elif c == "|":
            acc = {}
            i += 1
        elif c in "zx":
            m = re.match(r"[zx](\d*)(/?)(\d*)", text[i:])
            d = length(m.group(1), m.group(2), m.group(3))
            notes.append(Note(t, d, 0))
            t += d
            i += m.end()
        elif text.startswith(".-", i) or c == "-":
            notes[-1].tie = True
            i += 2 if c == "." else 1
        elif c in "^_=ABCDEFGabcdefg":
            m = NOTE.match(text, i)
            a, letter, octs, num, slash, den = m.groups()
            up = letter.upper()
            pitch = 60 + STEP[up] + (12 if letter.islower() else 0) + 12 * octs.count("'") - 12 * octs.count(",")
            key = (up, octs, letter.islower())
            if a:
                acc[key] = {"^": 1, "_": -1, "=": 0}[a]
            pitch += acc.get(key, KEY_F.get(up, 0))
            d = length(num, slash, den)
            notes.append(Note(t, d, pitch, optional=optional_next))
            optional_next = False
            t += d
            i = m.end()
        else:  # slurs, dots, spaces, ]
            i += 1
    return notes


def length(num, slash, den):
    n = float(num) if num else 1.0
    if slash:
        n /= float(den) if den else 2.0
    return n


def lyric_tokens(line):
    """w: line -> tokens: ("syl", text, continues_word) | ("skip",) | ("hold",) | ("blank",)"""
    out = []
    for word in line.split():
        word = word.replace("~", " ")
        if re.fullmatch(r"\d+\.\s*", word):
            out.append(("blank",))
            continue
        word = re.sub(r"^\d+\.\s*", "", word)
        while word:
            if word[0] == "*":
                out.append(("skip",)); word = word[1:]
            elif word[0] == "_":
                out.append(("hold",)); word = word[1:]
            else:
                m = re.match(r"([^\-_*]+)(-?)", word)
                out.append(("syl", m.group(1), bool(m.group(2))))
                word = word[m.end():]
    return out


def parse(path):
    bodies, verses = {}, {}
    cur = None
    for raw in open(path, encoding="utf-8", errors="replace"):
        line = raw.split("%", 1)[0].rstrip() if not raw.startswith("w:") else raw.rstrip("\n")
        m = re.match(r"\[V:\s*(\w+)\]\s*(.*)", line)
        if m:
            cur = m.group(1)
            bodies.setdefault(cur, []).append(m.group(2))
            if cur == "S1V1":
                k = 0
        elif line.startswith("w:") and cur == "S1V1":
            k += 1
            verses.setdefault(k, []).extend(lyric_tokens(line[2:]))
    voices = {v: parse_body(" | ".join(b)) for v, b in bodies.items()}
    return voices, [verses[k] for k in sorted(verses)]


if __name__ == "__main__":
    import sys
    vs, ve = parse(sys.argv[1])
    for v, ns in vs.items():
        print(v, len(ns), "notes", sum(n.len for n in ns), "beats", [n.midi for n in ns][:16])
    for k, toks in enumerate(ve, 1):
        print(k, len(toks), [t[1] if t[0] == "syl" else t[0] for t in toks][:20])
