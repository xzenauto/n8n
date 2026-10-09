"""Pista de efectos "movimiento de cámara": whoosh suave (ruido filtrado que sube y baja)
en cada zoom-in/cambio de plano. Discreto: se mezcla muy por debajo de la voz.
Uso: sfx_whoosh.py <duración_s> salida.wav t1 t2 ...   (t = segundo en que arranca el zoom)"""
import numpy as np, sys, wave
SR = 48000
DUR = float(sys.argv[1]); OUT = sys.argv[2]; TIMES = [float(x) for x in sys.argv[3:]]
N = int(DUR * SR)
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(3)
def whoosh(length=0.55, peak=0.6):
    n = int(length * SR); t = np.arange(n) / n
    x = rng.standard_normal(n)
    # paso banda que barre de grave a medio-agudo (filtro de un polo variable, dos pasadas)
    fc = 300 + 2200 * np.sin(np.pi * np.minimum(1, t / peak) / 2) ** 2
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.zeros(n); z = 0.0
    for i in range(n):
        z = (1 - a[i]) * x[i] + a[i] * z; y[i] = z
    y = y - np.convolve(y, np.ones(40) / 40, "same")    # quita el retumbe grave
    env = np.where(t < peak, (t / peak) ** 2, np.exp(-(t - peak) / (1 - peak) * 4))
    return y * env / (np.abs(y * env).max() + 1e-9)
for k, t0 in enumerate(TIMES):
    w = whoosh(0.5 + 0.1 * (k % 2))
    i = int(max(0, t0 - 0.18) * SR); j = min(N, i + len(w))
    pan = np.linspace(0.75, 1.0, j - i) if k % 2 else np.linspace(1.0, 0.75, j - i)   # leve barrido estéreo
    L[i:j] += w[:j - i] * pan; R[i:j] += w[:j - i] * pan[::-1]
mix = np.stack([L, R], 1) * 0.5
with wave.open(OUT, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
print("whoosh x", len(TIMES), "→", OUT)
