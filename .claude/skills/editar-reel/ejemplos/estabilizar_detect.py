"""Calcula, para cada fotograma, la transformación (similaridad) que lo alinea con un
encuadre de referencia usando SOLO el fondo (la persona se enmascara)."""
import cv2, json, numpy as np, subprocess, sys
SRC, REF_T = "main.mov", float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
W4, H4 = 3840, 2160
SW, SH = 1280, 720; K = W4 / SW
faces = json.load(open("faces_all.json"))
def frames():
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-vf", f"scale={SW}:{SH}", "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(SW * SH)
        if len(b) < SW * SH: return
        yield np.frombuffer(b, np.uint8).reshape(SH, SW)
def mask_for(i):
    m = np.full((SH, SW), 255, np.uint8)
    r = faces[min(i, len(faces) - 1)]
    if r[1] is not None:
        cx, cy, fw = r[1] / K, r[2] / K, r[3] / K
        cv2.rectangle(m, (int(cx - 1.9 * fw), int(cy - 1.0 * fw)), (int(cx + 1.9 * fw), SH), 0, -1)  # cabeza + cuerpo
    return m
orb = cv2.ORB_create(4000)
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
allf = list(frames())
ref_i = round(REF_T * 30)
kr, dr = orb.detectAndCompute(allf[ref_i], mask_for(ref_i))
out = []
for i, g in enumerate(allf):
    k, d = orb.detectAndCompute(g, mask_for(i))
    M, inl = None, 0
    if d is not None and len(k) > 20:
        ms = sorted(bf.match(d, dr), key=lambda m: m.distance)[:800]
        if len(ms) >= 12:
            src = np.float32([k[m.queryIdx].pt for m in ms]); dst = np.float32([kr[m.trainIdx].pt for m in ms])
            M, msk = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=2.0)
            inl = int(msk.sum()) if msk is not None else 0
    if M is None:
        out.append(None)
    else:
        s = float(np.hypot(M[0, 0], M[1, 0])); a = float(np.arctan2(M[1, 0], M[0, 0]))
        out.append([s, a, float(M[0, 2] * K), float(M[1, 2] * K), inl])   # traslación en píxeles 4K
json.dump(out, open("stab.json", "w"))
ok = [o for o in out if o]
print("fotogramas", len(out), "sin alinear", len(out) - len(ok))
print("escala", round(min(o[0] for o in ok), 4), round(max(o[0] for o in ok), 4),
      "giro(º)", round(np.degrees(min(o[1] for o in ok)), 2), round(np.degrees(max(o[1] for o in ok)), 2))
print("dx", round(min(o[2] for o in ok)), round(max(o[2] for o in ok)), "dy", round(min(o[3] for o in ok)), round(max(o[3] for o in ok)))
print("inliers min/mediana", min(o[4] for o in ok), int(np.median([o[4] for o in ok])))
for t in (1.7, 1.9, 4.2, 4.4, 10.2, 10.4, 14.0, 14.2, 24.0, 24.2):
    o = out[round(t * 30)]; print(t, [round(v, 3) for v in o])
