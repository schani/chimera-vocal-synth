"""mix.py <dir>: the choir (soprano1..3, alto1..3, tenor1..3, bass1..3 .wav) placed S A T B from left
to right in a long, dark church tail, with verse dynamics. Writes <dir>/choir.wav."""
import sys, json, numpy as np
from scipy.io import wavfile

D = sys.argv[1]
FS = 48000
tm = json.load(open(f"{D}/timing.json"))
PAN = {"soprano": -0.55, "alto": -0.2, "tenor": 0.2, "bass": 0.55}
LEVEL = {"soprano": 1.0, "alto": 0.95, "tenor": 0.95, "bass": 1.0}

tracks = {}
for p in PAN:
    for i in (1, 2, 3):
        fs, x = wavfile.read(f"{D}/{p}{i}.wav"); assert fs == FS
        tracks[(p, i)] = x.astype(float) / 32768
n = max(len(x) for x in tracks.values()) + int(5 * FS)

def active_rms(x):
    fr = x[: len(x) // 4800 * 4800].reshape(-1, 4800)
    r = np.sqrt((fr ** 2).mean(1)); r = r[r > r.max() * 0.05]
    return np.sqrt((r ** 2).mean())

dry = np.zeros((n, 2))
for (p, i), x in tracks.items():
    pan = PAN[p] + (i - 2) * 0.12  # a section spreads a little
    a = (pan + 1) * np.pi / 4
    y = np.zeros(n); y[: len(x)] = x * LEVEL[p] / active_rms(x)
    dry[:, 0] += np.cos(a) * y; dry[:, 1] += np.sin(a) * y

# verse dynamics: v1 mp, v2 mf, v3 p, v4 pp, v5 p, growing on the last line, the last chord dying away
t = np.arange(n) / FS
levels = [0.75, 1.0, 0.62, 0.5, 0.6]
g = np.full(n, levels[0])
for v, start in enumerate(tm["verses"]):
    g = np.where(t >= start - 0.4, levels[v], g)
grow = np.clip((t - tm["lastLine"]) / 6, 0, 1)
g = g + (0.95 - g) * grow * (t < tm["end"] - 4)
fade = np.clip((t - (tm["end"] - 4)) / 4, 0, 1)
g = np.where(t >= tm["end"] - 4, 0.95 - 0.45 * fade, g)
k = int(0.6 * FS); g = np.convolve(g, np.ones(k) / k, mode="same")  # no steps
dry *= g[:, None]

# church: 4.5 s decorrelated tail (high frequencies die first), 30 ms pre-delay, sparse early reflections
rng = np.random.default_rng(11)
L = int(4.5 * FS); tt = np.arange(L) / FS
def ir():
    lo = rng.standard_normal(L); hi = rng.standard_normal(L)
    lo = np.convolve(lo, np.ones(24) / 24, mode="same")  # dark band
    h = lo * np.exp(-tt * 1.6) * 3.0 + hi * np.exp(-tt * 4.5) * 0.35
    h *= np.minimum(1, tt / 0.08)
    h = np.concatenate([np.zeros(int(0.03 * FS)), h])[:L]
    for d, a in [(0.021, .5), (0.037, .35), (0.053, .3), (0.071, .2)]:
        h[int((d + rng.uniform(0, .004)) * FS)] += a
    return h / np.sqrt((h ** 2).sum())
N = 1 << int(np.ceil(np.log2(n + L)))
wet = np.stack([np.fft.irfft(np.fft.rfft(dry[:, c], N) * np.fft.rfft(ir(), N))[:n] for c in (0, 1)], 1)
wet *= np.sqrt((dry ** 2).mean()) / np.sqrt((wet ** 2).mean())
out = 0.62 * dry + 0.75 * wet
out *= 0.89 / np.abs(out).max()
end = int((tm["end"] + 4.5) * FS)
wavfile.write(f"{D}/choir.wav", FS, (out[:end] * 32767).astype(np.int16))
print(f"{D}/choir.wav {end / FS:.1f} s")
