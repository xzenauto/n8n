"""Plano principal 4:3 (1440x1080) desde el 2880x2160 original en una sola remuestra:
plano normal / cerrado alterno en cada corte + zoom lento + zoom-ins de énfasis (cara fija).
Uso: aroll43.py src.mov faces.json plan.json salida.mkv"""
import cv2, json, numpy as np, subprocess, sys
SRC, FACES, PLAN, OUT = sys.argv[1:5]
P = json.load(open(PLAN))
W4, H4, OW, OH, FPS = 2880, 2160, 1440, 1080, 30
ZOOM_RATE, ZOOM_MAX, PUNCH = 0.010, 1.08, 1.10
EMPH_STEP, EMPH_TIME = 0.07, 0.35
faces = [r for r in json.load(open(FACES)) if r[1] is not None]
fx = float(np.median([r[1] for r in faces])); fy = float(np.median([r[2] for r in faces]))
starts = sorted({0.0, *P["cuts"]})
def seg(t):
    k = max(i for i, s in enumerate(starts) if s <= t + 1e-6); return k, starts[k]
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-vf", "scale=in_color_matrix=bt709:in_range=tv,format=rgb24",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS),
                        "-i", "-", "-i", SRC, "-map", "0:v", "-map", "1:a", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                        "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", "-color_primaries", "bt709", "-color_trc", "bt709",
                        "-colorspace", "bt709", "-c:a", "pcm_s16le", "-shortest", OUT], stdin=subprocess.PIPE)
i = 0
while True:
    b = dec.stdout.read(W4 * H4 * 3)
    if len(b) < W4 * H4 * 3: break
    img = np.frombuffer(b, np.uint8).reshape(H4, W4, 3)
    t = i / FPS; k, s0 = seg(t)
    z = (PUNCH if k % 2 else 1.0) * min(ZOOM_MAX, 1 + ZOOM_RATE * (t - s0))
    for e in P["emphasis"]:
        if s0 <= e <= t:
            p = min(1.0, (t - e) / EMPH_TIME); z *= 1 + EMPH_STEP * p * p * (3 - 2 * p)
    z = min(z, 1.35)
    x = min(max(fx - fx / z, 0), W4 - W4 / z); y = min(max(fy - fy / z, 0), H4 - H4 / z)
    M = np.float32([[1 / z, 0, x], [0, 1 / z, y]])
    out = cv2.warpAffine(img, M, (W4, H4), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
    enc.stdin.write(cv2.resize(out, (OW, OH), interpolation=cv2.INTER_AREA).tobytes())
    i += 1
enc.stdin.close(); enc.wait(); print("listo", OUT, i, "fotogramas")
