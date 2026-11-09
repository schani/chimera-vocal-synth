"""mix.py <band.wav> <out.wav>: lead vocal centred and on top, the two gang-vocal parts spread
left and right, a short bright plate on the voices, a gentle compressor on the lead."""
import os, sys, numpy as np
from scipy.io import wavfile

band_f, out_f = sys.argv[1:3]
FS = 48000
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
fs, band = wavfile.read(band_f); band = band.astype(float) / 32768
def mono(name):
    fs, x = wavfile.read(f"{D}/{name}.wav"); assert fs == FS
    return x.astype(float) / 32768
n = len(band) + FS
def pad(x):
    y = np.zeros(n); y[: min(n, len(x))] = x[:n]; return y
def active_rms(x):
    x = x if x.ndim == 1 else x.mean(1)
    fr = x[: len(x) // 4800 * 4800].reshape(-1, 4800); r = np.sqrt((fr ** 2).mean(1))
    r = r[r > r.max() * 0.05]; return np.sqrt((r ** 2).mean())
def pan(x, p):
    a = (p + 1) * np.pi / 4; return np.stack([np.cos(a) * x, np.sin(a) * x], 1)
def compress(x, thr=0.5, ratio=3.0, att=0.005, rel=0.12):
    env, g = 0.0, np.empty_like(x); a, r = np.exp(-1 / (att * FS)), np.exp(-1 / (rel * FS))
    ax = np.abs(x)
    # envelope at 1 kHz control rate, then interpolated (fast enough in numpy)
    k = 48; ctl = ax[: len(ax) // k * k].reshape(-1, k).max(1); e = np.empty_like(ctl)
    for i, v in enumerate(ctl):
        env = a ** k * env + (1 - a ** k) * v if v > env else r ** k * env + (1 - r ** k) * v; e[i] = env
    e = np.repeat(e, k); e = np.pad(e, (0, len(x) - len(e)), mode="edge")
    over = np.maximum(e / thr, 1.0)
    return x / over ** (1 - 1 / ratio)

lead = pad(mono("lead")); lead = compress(lead / np.abs(lead).max())
gang = {p: [pad(mono(f"{p}_{i}")) for i in (1, 2, 3)] for p in ("p2", "p3")}
vox = pan(lead / active_rms(lead), 0.0)
for p, side in (("p2", -1), ("p3", 1)):
    for i, x in enumerate(gang[p]):
        vox += 0.42 * pan(x / active_rms(x), side * (0.35 + 0.2 * i))
# plate: 1.1 s bright tail, 20 ms pre-delay
rng = np.random.default_rng(5); L = int(1.1 * FS); t = np.arange(L) / FS
N = 1 << int(np.ceil(np.log2(n + L)))
def ir():
    h = rng.standard_normal(L) * np.exp(-t * 5.5); h[: int(0.02 * FS)] = 0; return h / np.sqrt((h ** 2).sum())
wet = np.stack([np.fft.irfft(np.fft.rfft(vox[:, c], N) * np.fft.rfft(ir(), N))[:n] for c in (0, 1)], 1)
vox = vox + 0.22 * wet * np.sqrt((vox ** 2).mean() / (wet ** 2).mean())
B = np.zeros((n, 2)); B[: len(band)] = band
g = active_rms(B) / active_rms(vox) * 10 ** (4.0 / 20)  # voices 4 dB over the band
mix = B + g * vox
mix *= 0.89 / np.abs(mix).max()
wavfile.write(out_f, FS, (mix * 32767).astype(np.int16))
print(out_f, f"{n / FS:.1f} s")
