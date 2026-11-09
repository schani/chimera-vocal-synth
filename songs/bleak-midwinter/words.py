"""verse tokens -> words with the hymn's syllable counts"""
import os
from abcparse import parse
HERE = os.path.dirname(os.path.abspath(__file__))
CHIMERA = os.environ.get("CHIMERA") or os.path.join(HERE, "../../target/release/chimera")
def verse_words(toks):
    words, cur = [], []
    for t in toks:
        if t[0] != "syl":
            continue
        cur.append(t[1])
        if not t[2]:
            words.append(cur); cur = []
    return words
if __name__ == "__main__":
    import sys, json, subprocess
    _, verses = parse(os.path.join(HERE, "In_The_Bleak_MidWinter-Cranham.abc"))
    for k, v in enumerate(verses, 1):
        ws = verse_words(v)
        text = " ".join("".join(w) for w in ws)
        out = json.loads(subprocess.check_output([CHIMERA, "syllables", text]))
        got, cur = [], 0
        for s in out:
            cur += 1
            if s["wordEnd"]:
                got.append(cur); cur = 0
        bad = [("".join(w), len(w), g) for w, g in zip(ws, got) if len(w) != g]
        print(k, len(ws), "words", len(got), "dict words", "mismatch:", bad)
