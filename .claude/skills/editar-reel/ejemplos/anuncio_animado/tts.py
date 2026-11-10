"""Locución con Kokoro-82M (ONNX, voces españolas em_alex / ef_dora / em_santa) sin red.
Uso: tts.py modelo.onnx dir_voces guion.json salida_dir [voz] [velocidad]
Genera una frase por archivo + voz.wav concatenada + tiempos.json (inicio/fin de cada bloque y frase)."""
import sys, json, re, os, wave
import numpy as np
from kokoro_onnx import Kokoro

MODEL, VDIR, GUION, OUT = sys.argv[1:5]
VOICE = sys.argv[5] if len(sys.argv) > 5 else "em_alex"
SPEED = float(sys.argv[6]) if len(sys.argv) > 6 else 1.05
LANG = sys.argv[7] if len(sys.argv) > 7 else "es-419"
SUBS = [("presento Xzen", "presento, Zen"), ("Xzen", "Zen"), (" app", " ap"), ("PÁDEL", "pádel"), ("WhatsApp", "guatsap")]
os.makedirs(OUT, exist_ok=True)

# voices.npz a partir de los .bin (510 x 1 x 256 float32)
npz = os.path.join(OUT, "voices.npz")
vs = {f[:-4]: np.fromfile(os.path.join(VDIR, f), dtype=np.float32).reshape(-1, 1, 256)
      for f in os.listdir(VDIR) if f.endswith(".bin")}
np.savez(npz, **vs)
k = Kokoro(MODEL, npz)
def fix(x):
    for a, b in SUBS: x = x.replace(a, b)
    return x
SR = 24000
GAP_FRASE, GAP_BLOQUE = 0.18, 0.42

audio, tiempos, t = [], [], 0.35
audio.append(np.zeros(int(0.35 * SR), np.float32))
for b in json.load(open(GUION)):
    frases = [f.strip() for f in re.split(r"(?<=[.?!])\s+", b["txt"]) if f.strip()]
    blo = {"id": b["id"], "t0": t, "frases": []}
    for i, f in enumerate(frases):
        say = b.get("say", {}).get(f, f)
        s, sr = k.create(fix(say), voice=VOICE, speed=SPEED, lang=LANG)
        s = np.asarray(s, np.float32)
        # recorta silencios de los extremos
        nz = np.where(np.abs(s) > 0.01)[0]
        s = s[max(0, nz[0] - 240): nz[-1] + 480] if len(nz) else s
        blo["frases"].append({"txt": f, "t0": t, "t1": t + len(s) / SR})
        audio.append(s); t += len(s) / SR
        g = GAP_FRASE if i < len(frases) - 1 else GAP_BLOQUE
        audio.append(np.zeros(int(g * SR), np.float32)); t += g
    blo["t1"] = t
    tiempos.append(blo)
a = np.concatenate(audio)
a = a / (np.abs(a).max() + 1e-9) * 0.9
with wave.open(os.path.join(OUT, "voz.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((a * 32767).astype(np.int16).tobytes())
json.dump(tiempos, open(os.path.join(OUT, "tiempos.json"), "w"), ensure_ascii=False, indent=1)
print("voz", round(t, 2), "s", VOICE)
