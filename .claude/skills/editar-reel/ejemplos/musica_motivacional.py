"""Pista motivacional instrumental original (libre de derechos), generada por síntesis.
Am – F – C – G a 100 BPM. Estructura en capas que crece con el discurso."""
import numpy as np, sys, wave
SR, BPM = 48000, 100
DUR = float(sys.argv[1]); OUT = sys.argv[2]
beat = 60 / BPM; bar = 4 * beat
N = int((DUR + 3) * SR)
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(7)
f = lambda midi: 440 * 2 ** ((midi - 69) / 12)
CH = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]   # Am F C G
ROOT = [45, 41, 48, 43]
def add(sig, t0, gl=1.0, gr=1.0):
    i = int(t0 * SR); j = min(N, i + len(sig))
    if j > i: L[i:j] += sig[:j - i] * gl; R[i:j] += sig[:j - i] * gr
def env_adsr(n, a, d, s, r):
    e = np.ones(n) * s; A, D, Rr = int(a * SR), int(d * SR), int(r * SR)
    e[:A] = np.linspace(0, 1, A); e[A:A + D] = np.linspace(1, s, len(e[A:A + D]))
    if Rr: e[-Rr:] *= np.linspace(1, 0, Rr)
    return e
def pad(freq, dur):
    t = np.arange(int(dur * SR)) / SR; x = np.zeros_like(t)
    for det in (-0.12, 0.0, 0.12):                      # tres osciladores desafinados
        for h in range(1, 7):                           # sierra filtrada (pocos armónicos)
            x += np.sin(2 * np.pi * freq * 2 ** (det / 12) * h * t + rng.random() * 6) / h ** 1.6
    return x * env_adsr(len(t), 0.6, 0.3, 0.8, 0.8) / 8
def pluck(freq, dur=0.9):
    t = np.arange(int(dur * SR)) / SR
    x = sum(np.sin(2 * np.pi * freq * h * t) * np.exp(-t * (3 + h * 2.5)) / h for h in range(1, 6))
    return x * np.minimum(1, t * 400)
def kick():
    t = np.arange(int(0.35 * SR)) / SR
    ph = 2 * np.pi * np.cumsum(45 + 90 * np.exp(-t * 30)) / SR
    return np.sin(ph) * np.exp(-t * 9)
def clap():
    t = np.arange(int(0.25 * SR)) / SR; n = rng.standard_normal(len(t))
    n = np.convolve(n, [1, -0.9], "same")               # quita graves
    n = np.convolve(n, np.ones(5) / 5, "same")          # suaviza agudos
    return n * np.exp(-t * 22) * 0.12
def hat():
    t = np.arange(int(0.06 * SR)) / SR; n = rng.standard_normal(len(t))
    n = n - np.convolve(n, np.ones(6) / 6, "same")      # solo agudos
    return n * np.exp(-t * 80) * 0.035
nbars = int(np.ceil(DUR / bar)) + 1
pump = np.ones(N)
for b in range(nbars):
    t0 = b * bar; c = b % 4
    intensity = 0 if t0 < 2 * bar else (1 if t0 < 6 * bar else (2 if t0 < 10 * bar else 3))
    for note in CH[c]:                                  # pad
        add(pad(f(note), bar + 0.8), t0, 0.9, 1.0)
    arp = CH[c] + [CH[c][0] + 12, CH[c][1] + 12, CH[c][2] + 12, CH[c][1] + 12, CH[c][0] + 12]
    for k in range(8):                                  # piano en corcheas, paneo alterno
        add(pluck(f(arp[k] + 12)) * (0.16 if intensity else 0.12), t0 + k * beat / 2, 1.0 if k % 2 else 0.6, 0.6 if k % 2 else 1.0)
    if intensity >= 1:                                  # bajo + bombo
        for k in range(4):
            tb = np.arange(int(beat * 0.95 * SR)) / SR
            add(np.sin(2 * np.pi * f(ROOT[c]) * tb) * env_adsr(len(tb), 0.01, 0.1, 0.7, 0.1) * 0.35, t0 + k * beat)
            if k in (0, 2) or intensity >= 2:
                add(kick() * 0.7, t0 + k * beat)
                i = int((t0 + k * beat) * SR); w = int(0.25 * SR)
                pump[i:i + w] = np.minimum(pump[i:i + w], 0.55 + 0.45 * np.linspace(0, 1, len(pump[i:i + w])))
    if intensity >= 2:                                  # palmas en 2 y 4
        for k in (1, 3): add(clap(), t0 + k * beat, 0.9, 1.0)
    if intensity >= 3:                                  # charles en corcheas
        for k in range(8): add(hat(), t0 + k * beat / 2 + 0.01, 0.7 if k % 2 else 1.0, 1.0 if k % 2 else 0.7)
# reverb sencilla (cola de ruido decreciente) para dar aire
ir_t = np.arange(int(1.2 * SR)) / SR
ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 4.5); ir[0] = 0; ir /= np.abs(ir).sum() / 6
def conv(x): n = len(x) + len(ir); return np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[:len(x)]
L = (L + 0.35 * conv(L)) * pump; R = (R + 0.35 * conv(R)) * pump
mix = np.stack([L, R], 1)[: int(DUR * SR)]
fade = int(2.0 * SR); mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
mix[: int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))[:, None]
mix = np.tanh(mix / np.abs(mix).max() * 1.2) * 0.89
with wave.open(OUT, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print("música", DUR, "s →", OUT)
