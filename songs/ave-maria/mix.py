"""mix.py <piano.wav> <voice.wav> <out.wav> [voice over piano, dB]: voice in a small hall over the piano."""
import sys, numpy as np
from scipy.io import wavfile

piano_f, voice_f, out_f = sys.argv[1:4]
over = float(sys.argv[4]) if len(sys.argv) > 4 else 7.0
fs, p = wavfile.read(piano_f); p = p.astype(float) / 32768
fs2, v = wavfile.read(voice_f); v = v.astype(float) / 32768
assert fs == fs2 == 48000
if v.ndim == 1:
    v = v[:, None]
n = max(len(p), len(v) + int(2.5 * fs))
P = np.zeros((n, 2)); P[: len(p)] = p
V = np.zeros(n); V[: len(v)] = v[:, 0]

def active_rms(x):
    x = x if x.ndim == 1 else x.mean(1)
    fr = x[: len(x) // 4800 * 4800].reshape(-1, 4800)
    r = np.sqrt((fr ** 2).mean(1)); r = r[r > r.max() * 0.05]
    return np.sqrt((r ** 2).mean())

# hall: decorrelated stereo noise tails (2.2 s), a pre-delay, early reflections
rng = np.random.default_rng(3)
L = int(2.2 * fs); t = np.arange(L) / fs
def ir():
    h = rng.standard_normal(L) * np.exp(-t * 3.0) * np.minimum(1, t / 0.02)
    lp = np.exp(-np.arange(L) / 6.0); h = np.convolve(h, lp[:40] / lp[:40].sum())[:L]  # darker tail
    return h
irs = [ir(), ir()]
for d, g in [(0.017, .35), (0.029, .25), (0.041, .18)]:
    irs[0][int(d * fs)] += g; irs[1][int((d + 0.004) * fs)] += g
N = 1 << int(np.ceil(np.log2(n + L)))
VF = np.fft.rfft(V, N)
wet = np.stack([np.fft.irfft(VF * np.fft.rfft(h / np.abs(h).sum() * 40, N))[:n] for h in irs], 1)
Vs = 0.8 * V[:, None] + 0.25 * wet / (np.abs(wet).max() + 1e-9) * np.abs(V).max()

g = active_rms(P) / active_rms(Vs) * 10 ** (over / 20)
mix = P + g * Vs
mix *= 0.89 / np.abs(mix).max()
wavfile.write(out_f, fs, (mix * 32767).astype(np.int16))
print(f"{out_f}: {n / fs:.1f} s, voice gain {g:.2f}")
