"""Pista de "pops" suaves para la entrada de recursos gráficos.
Uso: sfx_pop.py <duración_s> salida.wav t1 t2 ..."""
import numpy as np, sys, wave
SR = 48000
DUR = float(sys.argv[1]); OUT = sys.argv[2]; TIMES = [float(x) for x in sys.argv[3:]]
N = int(DUR * SR); L = np.zeros(N)
t = np.arange(int(0.09 * SR)) / SR
f = 780 * np.exp(-t * 18) + 380
pop = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 45) * np.minimum(1, t * 2000)
for t0 in TIMES:
    i = int(t0 * SR); j = min(N, i + len(pop)); L[i:j] += pop[:j - i]
mix = np.stack([L, L], 1) * 0.5
with wave.open(OUT, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
print("pops x", len(TIMES), "→", OUT)
