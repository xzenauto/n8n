"""Plano principal 1080p desde el 4K en una sola remuestra: alterna plano normal / cerrado
en cada corte (saltos de postura) + zoom lento con la cara como punto fijo."""
import cv2, json, numpy as np, subprocess
from plan import BROLL
W4, H4, OW, OH, FPS = 3840, 2160, 1920, 1080, 30
JUMPS = [2.43, 15.03, 23.93, 32.03, 43.93, 47.3]          # cortes que quedan en plano principal
ZOOM_RATE, ZOOM_MAX, PUNCH = 0.012, 1.10, 1.10
faces = json.load(open("faces_all.json"))
fx = float(np.median([r[1] for r in faces if r[1] is not None])); fy = float(np.median([r[2] for r in faces if r[1] is not None]))
starts = sorted({0.0, *[b for a, b, *_ in BROLL], *JUMPS})
def seg(t):
    k = max(i for i, s in enumerate(starts) if s <= t + 1e-6); return k, starts[k]
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", "main.mov", "-vf", "scale=in_color_matrix=bt709:in_range=tv,format=rgb24",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS),
                        "-i", "-", "-i", "main.mov", "-map", "0:v", "-map", "1:a", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                        "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", "-color_primaries", "bt709", "-color_trc", "bt709",
                        "-colorspace", "bt709", "-c:a", "copy", "aroll.mkv"], stdin=subprocess.PIPE)
i = 0
while True:
    b = dec.stdout.read(W4 * H4 * 3)
    if len(b) < W4 * H4 * 3: break
    img = np.frombuffer(b, np.uint8).reshape(H4, W4, 3)
    t = i / FPS; k, s0 = seg(t)
    z = (PUNCH if k % 2 else 1.0) * min(ZOOM_MAX, 1 + ZOOM_RATE * (t - s0))
    cw, ch = W4 / z, H4 / z
    x = min(max(fx - fx / z, 0), W4 - cw); y = min(max(fy - fy / z, 0), H4 - ch)
    M = np.float32([[1 / z, 0, x], [0, 1 / z, y]])            # salida 4K -> original
    out4 = cv2.warpAffine(img, M, (W4, H4), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
    enc.stdin.write(cv2.resize(out4, (OW, OH), interpolation=cv2.INTER_AREA).tobytes())
    i += 1
enc.stdin.close(); enc.wait(); print("listo", i, "fotogramas")
