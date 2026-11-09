"""patch_score.py <score.mxl> <out.musicxml>: the score's MusicXML with words on P2's three
wordless chants (measures 21, 25, 29: two sung notes each, "Thun-der!")."""
import re, sys, zipfile

mxl, out_f = sys.argv[1:3]
z = zipfile.ZipFile(mxl)
root = re.search(r'full-path="([^"]+)"', z.read("META-INF/container.xml").decode()).group(1)
x = z.read(root).decode("utf-8")
a = x.index('<part id="P2">'); b = x.index("</part>", a)
part = x[a:b]

def fix(m):
    meas = m.group(0)
    sung = [n for n in re.finditer(r"<note[ >].*?</note>", meas, re.S) if "<rest" not in n.group(0)]
    assert len(sung) == 2, (meas[:40], len(sung))
    for n, (syl, txt) in reversed(list(zip(sung, [("begin", "Thun"), ("end", "der!")]))):
        s = n.group(0).replace("</note>", f'<lyric number="1"><syllabic>{syl}</syllabic><text>{txt}</text></lyric></note>')
        meas = meas[:n.start()] + s + meas[n.end():]
    return meas

for num in (21, 25, 29):
    part, k = re.subn(r'<measure number="%d"[ >].*?</measure>' % num, fix, part, count=1, flags=re.S)
    assert k == 1, num
open(out_f, "w", encoding="utf-8").write(x[:a] + part + x[b:])
print(out_f)
