#!/usr/bin/env python3
"""Subtítulos estilo "reel cinematográfico" (ver SKILL.md).

Palabras finas y blancas que aparecen una a una a la altura de los ojos,
repartidas a izquierda y derecha de la cara. En planos sin cara (B-roll)
se muestra una sola palabra centrada.

Uso:
  python3 reel_subs.py entrada.mp4 salida.mp4 [--words words.json] [--grade]
                       [--model small] [--crf 18]

  --words  JSON con [{"w": "palabra", "s": inicio, "e": fin}, ...]; si no se
           pasa, se transcribe con Whisper (necesita openaipublic.azureedge.net).
  --grade  aplica la corrección de color del estilo.
  --broll  tramos de B-roll "1.8-3.0,4.5-6.5": en ellos siempre palabra única centrada.
  --dump   solo transcribe y guarda words.json para revisarlo/corregirlo.
"""
import argparse, json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "Inter.ttf")

# ---------------------------------------------------------------- estilo
SIZE_H = 0.037        # tamaño de letra relativo a la altura del frame
BROLL_SCALE = 1.25    # palabra única en B-roll, algo más grande
WEIGHT = 300          # Inter Light
WORD_GAP = 0.55       # espacio extra entre palabras (en em)
FACE_GAP = 0.30       # separación texto-cara (en anchos de cara)
FADE = 0.08           # entrada de cada palabra (s)
MAX_WORDS = 5         # palabras máximas por bloque
MAX_GAP = 0.45        # silencio que fuerza bloque nuevo (s)
GRADE = "eq=contrast=0.96:saturation=0.9:gamma=1.02,colorbalance=rs=0.02:bs=-0.02:rh=0.03:bh=-0.03"


def probe(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate:format=duration", "-of", "json", path])
    j = json.loads(out)
    st = j["streams"][0]
    n, d = map(int, st["r_frame_rate"].split("/"))
    return st["width"], st["height"], n / d, float(j["format"]["duration"])


def transcribe(path, model):
    import whisper
    wav = path + ".16k.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
    r = whisper.load_model(model).transcribe(wav, language="es", word_timestamps=True, fp16=False)
    os.remove(wav)
    return [{"w": w["word"].strip(), "s": w["start"], "e": w["end"]} for s in r["segments"] for w in s["words"]]


def chunks(words):
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= MAX_WORDS or w["s"] - cur[-1]["e"] > MAX_GAP
                    or cur[-1]["w"][-1:] in ".?!,;:"):
            out.append(cur); cur = []
        cur.append(w)
    if cur: out.append(cur)
    return out


def faces(path, W, H, fps, dur, step=0.2):
    """Cara principal muestreada cada `step` s → lista (t, cx, cy_ojos, ancho) o None."""
    import cv2
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    sw = 640
    sh = round(H * sw / W)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={1/step},scale={sw}:{sh}",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    res, i = [], 0
    while True:
        buf = p.stdout.read(sw * sh)
        if len(buf) < sw * sh: break
        g = np.frombuffer(buf, np.uint8).reshape(sh, sw)
        fs = casc.detectMultiScale(g, 1.1, 6, minSize=(sw // 18, sw // 18))
        if len(fs):
            x, y, w, h = max(fs, key=lambda f: f[2] * f[3])
            k = W / sw
            res.append((i * step, (x + w / 2) * k, (y + h * 0.42) * k, w * k))
        else:
            res.append((i * step, None))
        i += 1
    # suavizado: mediana de ventana corta y relleno de huecos aislados
    out = []
    for j, r in enumerate(res):
        win = [q for q in res[max(0, j - 2): j + 3] if q[1] is not None]
        if len(win) >= 2:
            out.append((r[0], float(np.median([q[1] for q in win])), float(np.median([q[2] for q in win])),
                        float(np.median([q[3] for q in win]))))
        else:
            out.append((r[0], None))
    return out, step


class Renderer:
    def __init__(s, W, H):
        s.W, s.H = W, H
        s.size = round(H * SIZE_H)
        s.f = s.font(s.size)
        s.fb = s.font(round(s.size * BROLL_SCALE))
        s.cache = {}

    def font(s, px):
        f = ImageFont.truetype(FONT, px)
        f.set_variation_by_axes([min(32, max(14, px * 0.6)), WEIGHT])
        return f

    def word_img(s, txt, big=False):
        txt = txt.strip(".,;:!?¿¡\"“”«»") or txt   # sin puntuación, como el original
        key = (txt, big)
        if key in s.cache: return s.cache[key]
        f = s.fb if big else s.f
        l, t, r, b = f.getbbox(txt)
        pad = round(f.size * 0.4)
        w, h = r - l + 2 * pad, round(f.size * 1.5) + 2 * pad
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - l, pad), txt, font=f, fill=(0, 0, 0, 110))
        sh = sh.filter(ImageFilter.GaussianBlur(max(1, f.size * 0.08)))
        im.alpha_composite(sh, (0, max(1, round(f.size * 0.03))))
        ImageDraw.Draw(im).text((pad - l, pad), txt, font=f, fill=(255, 255, 255, 255))
        s.cache[key] = (im, pad, f)
        return s.cache[key]

    def layout(s, chunk, face):
        """Posición (x, y_centro) de cada palabra del bloque."""
        imgs = [s.word_img(w["w"], big=face is None) for w in chunk]
        f = imgs[0][2]
        gap = f.size * WORD_GAP
        widths = [im.width - 2 * pad for im, pad, _ in imgs]
        if face is None:   # B-roll → una palabra centrada (se gestiona en draw)
            return [(s.W / 2 - wd / 2, s.H * 0.5) for wd in widths]
        cx, ey, fw = face
        n = len(chunk)
        left_n = math.ceil(n / 2) if n > 1 else n
        lw = sum(widths[:left_n]) + gap * (left_n - 1)
        rw = sum(widths[left_n:]) + gap * max(0, n - left_n - 1)
        lx_end = cx - fw * (0.5 + FACE_GAP)
        rx = cx + fw * (0.5 + FACE_GAP)
        margin = s.W * 0.04
        if lx_end - lw < margin or rx + rw > s.W - margin:
            # sin sitio a los lados → todo en un lado o centrado encima de la cabeza
            total = sum(widths) + gap * (n - 1)
            if cx - fw * (0.5 + FACE_GAP) - total >= margin:
                lx_end, left_n = cx - fw * (0.5 + FACE_GAP), n; lw = total
            elif cx + fw * (0.5 + FACE_GAP) + total <= s.W - margin:
                left_n = 0; rw = total
            else:
                x = max(margin, min(s.W - margin - total, cx - total / 2))
                y = ey - fw * 1.1
                pos = []
                for wd in widths:
                    pos.append((x, y)); x += wd + gap
                return pos
        pos, x = [], lx_end - lw
        for i, wd in enumerate(widths):
            if i == left_n: x = rx
            pos.append((x, ey)); x += wd + gap
        return pos

    def frame(s, t, chunk, face):
        canvas = Image.new("RGBA", (s.W, s.H), (0, 0, 0, 0))
        vis = [w for w in chunk if t >= w["s"] - 0.03]
        if not vis: return None
        if face is None:
            vis = vis[-1:]       # B-roll: solo la palabra actual
            pos = s.layout(vis, None)
        else:
            pos = s.layout(chunk, face)[:len(vis)]
        for w, (x, y) in zip(vis, pos):
            im, pad, f = s.word_img(w["w"], big=face is None)
            a = min(1, (t - (w["s"] - 0.03)) / FADE)
            if a < 1:
                arr = np.array(im); arr[..., 3] = (arr[..., 3] * a).astype(np.uint8); im = Image.fromarray(arr)
            canvas.alpha_composite(im, (round(x - pad), round(y - pad - f.size * 0.75)))
        return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out", nargs="?")
    ap.add_argument("--words"); ap.add_argument("--model", default="small")
    ap.add_argument("--grade", action="store_true"); ap.add_argument("--dump", action="store_true")
    ap.add_argument("--crf", default="18")
    ap.add_argument("--broll", default="", help="tramos de B-roll 'ini-fin,ini-fin' (s): palabra centrada")
    a = ap.parse_args()

    W, H, fps, dur = probe(a.inp)
    words = json.load(open(a.words)) if a.words else transcribe(a.inp, a.model)
    if a.dump or not a.out:
        json.dump(words, open(os.path.splitext(a.inp)[0] + ".words.json", "w"), ensure_ascii=False, indent=1)
        print("words.json guardado"); return
    print(f"{len(words)} palabras · detectando caras…", file=sys.stderr)
    fc, step = faces(a.inp, W, H, fps, dur)
    cks = chunks(words)
    R = Renderer(W, H)

    broll = [tuple(map(float, r.split("-"))) for r in a.broll.split(",") if r]

    def face_at(t):
        if any(b0 <= t < b1 for b0, b1 in broll): return None
        i = min(len(fc) - 1, int(t / step))
        r = fc[i]
        return None if r[1] is None else r[1:]

    def chunk_at(t):
        for i, c in enumerate(cks):
            end = cks[i + 1][0]["s"] - 0.03 if i + 1 < len(cks) else c[-1]["e"] + 0.6
            end = min(end, c[-1]["e"] + 0.8)
            if c[0]["s"] - 0.03 <= t < end: return i, c
        return None, None

    filt = (f"[0:v]{GRADE}[g];[g][1:v]overlay=0:0:format=auto,format=yuv420p[v]" if a.grade
            else "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]")
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-stats", "-y", "-i", a.inp, "-f", "rawvideo", "-pix_fmt", "rgba",
                           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-filter_complex", filt, "-map", "[v]",
                           "-map", "0:a?", "-c:v", "libx264", "-preset", "medium", "-crf", a.crf,
                           "-c:a", "copy", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    empty = bytes(W * H * 4)
    last_key, last_buf = None, empty
    n = math.ceil(dur * fps)
    for i in range(n):
        t = i / fps
        ci, c = chunk_at(t)
        face = face_at(t) if c else None
        if c:
            vis = sum(1 for w in c if t >= w["s"] - 0.03)
            fading = any(0 <= t - (w["s"] - 0.03) < FADE for w in c)
            fkey = None if face is None else tuple(round(v / 6) for v in face)
            key = (ci, vis, fkey, round(t, 3) if fading else None)
        else:
            key = None
        if key != last_key:
            img = R.frame(t, c, face) if c else None
            last_buf = img.tobytes() if img is not None else empty
            last_key = key
        ff.stdin.write(last_buf)
    ff.stdin.close(); ff.wait()
    print("listo:", a.out)


if __name__ == "__main__":
    main()
