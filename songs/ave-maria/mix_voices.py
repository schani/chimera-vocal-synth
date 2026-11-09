"""mix_voices.py <melody.wav[,more.wav...]> <accomp dir> <out.wav>: the sung melody centred and on
top (several singers: the first loudest, the others a little softer and either side of it), the
three voices that sing the piano part (bass, alto, descant) spread behind it, in a hall."""
import sys, numpy as np
from scipy.io import wavfile

sop_f, acc, out_f = sys.argv[1:4]
FS = 48000
PARTS = {"bass": (0.25, 0.42), "alto": (-0.45, 0.36), "descant": (0.5, 0.30)}  # pan, level re the melody

def load(f):
    fs, x = wavfile.read(f); assert fs == FS
    return x.astype(float) / 32768
def active_rms(x):
    fr = x[: len(x) // 4800 * 4800].reshape(-1, 4800); r = np.sqrt((fr ** 2).mean(1))
    r = r[r > r.max() * 0.05]; return np.sqrt((r ** 2).mean())
def pan(x, p):
    a = (p + 1) * np.pi / 4; return np.stack([np.cos(a) * x, np.sin(a) * x], 1)

mel_files = sop_f.split(",")
MEL_PAN_LVL = [(0.0, 1.0), (-0.15, 0.85), (0.15, 0.6)]
tracks = {f"mel{i}": load(f) for i, f in enumerate(mel_files)} | {p: load(f"{acc}/{p}.wav") for p in PARTS}
n = max(len(x) for x in tracks.values()) + 4 * FS
def pad(x):
    y = np.zeros(n); y[: len(x)] = x; return y
dry = np.zeros((n, 2))
for i in range(len(mel_files)):
    pn, lvl = MEL_PAN_LVL[i]
    dry += lvl * pan(pad(tracks[f"mel{i}"]) / active_rms(tracks[f"mel{i}"]), pn)
for p, (pn, lvl) in PARTS.items():
    dry += lvl * pan(pad(tracks[p]) / active_rms(tracks[p]), pn)

rng = np.random.default_rng(3); L = int(3.0 * FS); t = np.arange(L) / FS
def ir():
    h = rng.standard_normal(L); h = np.convolve(h, np.ones(16) / 16, mode="same") * np.exp(-t * 2.2)
    h *= np.minimum(1, t / 0.05); h = np.concatenate([np.zeros(int(0.025 * FS)), h])[:L]
    return h / np.sqrt((h ** 2).sum())
N = 1 << int(np.ceil(np.log2(n + L)))
wet = np.stack([np.fft.irfft(np.fft.rfft(dry[:, c], N) * np.fft.rfft(ir(), N))[:n] for c in (0, 1)], 1)
wet *= np.sqrt((dry ** 2).mean() / (wet ** 2).mean())
mix = 0.7 * dry + 0.55 * wet
mix *= 0.89 / np.abs(mix).max()
wavfile.write(out_f, FS, (mix * 32767).astype(np.int16))
print(out_f, f"{n / FS:.1f} s")
