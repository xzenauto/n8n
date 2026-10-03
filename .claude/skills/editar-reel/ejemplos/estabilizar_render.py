"""A-roll estabilizado contra el encuadre de referencia + recorte fijo + zoom lento,
todo en una sola remuestra desde el 4K original. Salida 1080p sin pérdida."""
import cv2, json, numpy as np, subprocess
from plan import BROLL, DUR
W4, H4, OW, OH, FPS = 3840, 2160, 1920, 1080, 30
BASE = 1.08                       # recorte fijo para ocultar bordes de la estabilización
ZOOM_RATE, ZOOM_MAX = 0.012, 1.10 # zoom lento del estilo
CUTS = [1.8, 3.97, 4.3, 9.1, 10.3, 12.47, 14.1, 16.43, 17.73, 19.67, 21.87, 22.03, 24.1, 28.1, 29.17, 31.0]
stab = json.load(open("stab.json")); faces = json.load(open("faces_all.json"))
N = len(stab)
# suavizado leve dentro de cada toma (no a través de los cortes): quita ruido de estimación
seg_id = np.searchsorted(np.array(CUTS) * FPS, np.arange(N), side="right")
P = np.array(stab)[:, :4]
Ps = P.copy()
for i in range(N):
    j = [k for k in range(max(0, i - 3), min(N, i + 4)) if seg_id[k] == seg_id[i]]
    Ps[i] = np.median(P[j], axis=0)
# tramos de A-roll (el zoom lento arranca de nuevo en cada uno)
starts = [0.0] + [b for a, b, *_ in BROLL]
def aroll_start(t):
    return max(s for s in starts if s <= t + 1e-6)
# punto fijo del zoom: cara (mediana) en coordenadas de la referencia
fx = np.median([r[1] for r in faces if r[1] is not None]); fy = np.median([r[2] for r in faces if r[1] is not None])
def ref_from_frame(i):
    s, a, tx, ty = Ps[i]
    return np.array([[s * np.cos(a), -s * np.sin(a), tx], [s * np.sin(a), s * np.cos(a), ty], [0, 0, 1]])
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", "main.mov", "-vf", "scale=in_color_matrix=bt709:in_range=tv,format=rgb24",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS),
                        "-i", "-", "-i", "main.mov", "-map", "0:v", "-map", "1:a",
                        "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                        "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", "-color_primaries", "bt709",
                        "-color_trc", "bt709", "-colorspace", "bt709", "-c:a", "copy", "aroll_estable.mkv"], stdin=subprocess.PIPE)
for i in range(N):
    buf = dec.stdout.read(W4 * H4 * 3)
    if len(buf) < W4 * H4 * 3: break
    img = np.frombuffer(buf, np.uint8).reshape(H4, W4, 3)
    t = i / FPS
    z = BASE * min(ZOOM_MAX, 1 + ZOOM_RATE * (t - aroll_start(t)))
    # salida(4K) -> referencia: zoom de factor z con punto fijo en la cara
    Zinv = np.array([[1 / z, 0, fx * (1 - 1 / z)], [0, 1 / z, fy * (1 - 1 / z)], [0, 0, 1]])
    M = np.linalg.inv(ref_from_frame(i)) @ Zinv          # salida -> fotograma original
    out4 = cv2.warpAffine(img, M[:2], (W4, H4), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
    enc.stdin.write(cv2.resize(out4, (OW, OH), interpolation=cv2.INTER_AREA).tobytes())
    if i % 150 == 0: print("fotograma", i, "/", N, flush=True)
enc.stdin.close(); enc.wait()
print("listo")
