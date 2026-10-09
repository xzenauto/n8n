"""Pista inspiracional instrumental original (libre de derechos), generada por síntesis.
C – G – Am – F a 80 BPM: piano en arpegios + pad cálido; entran bajo y bombo suave ("latido"),
y al final una melodía de campanitas. Más calmada y emotiva que musica_motivacional.py.
Uso: musica_inspiracional.py <duración_s> salida.wav"""
import numpy as np, sys, wave
SR, BPM = 48000, 80
DUR = float(sys.argv[1]); OUT = sys.argv[2]
beat = 60 / BPM; bar = 4 * beat
N = int((DUR + 4) * SR)
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(11)
f = lambda midi: 440 * 2 ** ((midi - 69) / 12)
CH = [[48, 52, 55], [43, 47, 50], [45, 48, 52], [41, 45, 48]]   # C G Am F
ROOT = [36, 31, 33, 29]
MEL = [[76, 74, 72, 74], [74, 71, 74, 79], [72, 76, 79, 76], [77, 76, 72, 69]]   # campanitas
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
    for det in (-0.1, 0.0, 0.1):
        for h in range(1, 5):
            x += np.sin(2 * np.pi * freq * 2 ** (det / 12) * h * t + rng.random() * 6) / h ** 2
    return x * env_adsr(len(t), 1.2, 0.5, 0.85, 1.2) / 9
def piano(freq, dur=1.6, vel=1.0):
    t = np.arange(int(dur * SR)) / SR
    x = sum(np.sin(2 * np.pi * freq * h * t) * np.exp(-t * (1.6 + h * 1.8)) / h ** 1.3 for h in range(1, 7))
    return x * np.minimum(1, t * 300) * vel
def bell(freq, dur=2.0):
    t = np.arange(int(dur * SR)) / SR
    x = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 2.76 * t) * np.exp(-t * 6)
    return x * np.exp(-t * 2.2) * np.minimum(1, t * 500)
def kick():
    t = np.arange(int(0.4 * SR)) / SR
    ph = 2 * np.pi * np.cumsum(42 + 60 * np.exp(-t * 28)) / SR
    return np.sin(ph) * np.exp(-t * 8)
nbars = int(np.ceil(DUR / bar)) + 1
for b in range(nbars):
    t0 = b * bar; c = b % 4
    lvl = 0 if t0 < 2 * bar else (1 if t0 < 6 * bar else 2)
    for note in CH[c]:
        add(pad(f(note + 12), bar + 1.2), t0, 0.95, 1.0)
    arp = [CH[c][0] + 12, CH[c][1] + 12, CH[c][2] + 12, CH[c][0] + 24, CH[c][2] + 12, CH[c][1] + 12, CH[c][2] + 12, CH[c][0] + 24]
    for k in range(8):                                  # piano en corcheas, acento en 1 y 3
        vel = (0.22 if k in (0, 4) else 0.15) * (1.0 if lvl else 0.85)
        add(piano(f(arp[k])) * vel, t0 + k * beat / 2, 1.0 if k % 2 else 0.7, 0.7 if k % 2 else 1.0)
    add(piano(f(ROOT[c] + 12), 2.5) * 0.18, t0)        # mano izquierda
    if lvl >= 1:                                        # bajo + bombo suave (latido)
        tb = np.arange(int(bar * 0.98 * SR)) / SR
        add(np.sin(2 * np.pi * f(ROOT[c]) * tb) * env_adsr(len(tb), 0.05, 0.3, 0.6, 0.3) * 0.28, t0)
        for k in (0, 2): add(kick() * 0.45, t0 + k * beat)
    if lvl >= 2:                                        # melodía de campanitas
        for k, m in enumerate(MEL[c]): add(bell(f(m)) * 0.07, t0 + k * beat, 0.8 if k % 2 else 1.0, 1.0 if k % 2 else 0.8)
ir_t = np.arange(int(2.0 * SR)) / SR                     # reverb larga: sensación de espacio
ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 3.0); ir[0] = 0; ir /= np.abs(ir).sum() / 6
def conv(x): n = len(x) + len(ir); return np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[:len(x)]
L = L + 0.45 * conv(L); R = R + 0.45 * conv(R)
mix = np.stack([L, R], 1)[: int(DUR * SR)]
fade = int(2.5 * SR); mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
mix[: int(0.5 * SR)] *= np.linspace(0, 1, int(0.5 * SR))[:, None]
mix = np.tanh(mix / np.abs(mix).max() * 1.1) * 0.89
with wave.open(OUT, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print("música", DUR, "s →", OUT)
