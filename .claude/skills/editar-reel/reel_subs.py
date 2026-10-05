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
  --cuts   cortes del plano principal "12.3,20.1": cada plano usa una posición fija.
  Palabras clave: añade "hl": true a la palabra en words.json → sale en amarillo.
  --hook   segundo en que acaba el gancho: hasta ahí, frases completas en letra grande.
  --dump   solo transcribe y guarda words.json para revisarlo/corregirlo.
"""
import argparse, json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "BebasNeue-Regular.ttf")   # elegida por el usuario (7A)

# ---------------------------------------------------------------- estilo
SIZE_H = 0.05         # tamaño de letra relativo a la altura del frame (feedback: más legible)
HOOK_H = 0.16         # tamaño del gancho (primera frase): grande y llamativo
HOOK_MAX_WORDS = 8    # el gancho se muestra como una frase completa
BROLL_SCALE = 1.25    # palabra única en B-roll, algo más grande
WEIGHT = 400          # solo afecta a fuentes variables (Bebas Neue es estática)
WORD_GAP = 0.55       # espacio extra entre palabras (en em)
FACE_GAP = 0.45       # separación texto-cara (en anchos de cara)
FADE = 0.08           # entrada de cada palabra (s)
MAX_WORDS = 5         # palabras máximas por bloque
MAX_GAP = 0.45        # silencio que fuerza bloque nuevo (s)
VERTICAL = False      # formato 9:16 (anuncios / reels verticales): subtítulos centrados bajo la cara
SIZE_V = 0.045        # tamaño de letra en vertical (relativo al alto)
HOOK_V = 0.075        # tamaño del gancho en vertical
SUB_Y_V = 0.70        # altura de los subtítulos en vertical
SHADOW = False        # sin sombra (preferencia del usuario)
HL_COLOR = (255, 210, 60)   # amarillo para palabras clave ("hl": true en words.json)
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


def chunks(words, cuts=(), hook_end=0.0):
    """Bloques de palabras. Antes de `hook_end` (gancho) los bloques son frases completas."""
    out, cur = [], []
    for w in words:
        crosses = cur and any(cur[0]["s"] - 0.05 < c <= w["s"] + 0.05 for c in cuts)
        in_hook = cur and cur[0]["s"] < hook_end
        if not cur:
            brk = False
        elif in_hook:
            brk = len(cur) >= HOOK_MAX_WORDS or cur[-1]["w"][-1:] in ".?!" or crosses or w["s"] >= hook_end
        else:
            brk = (len(cur) >= MAX_WORDS or w["s"] - cur[-1]["e"] > MAX_GAP
                   or cur[-1]["w"][-1:] in ".?!,;:" or crosses)
        if cur and brk:
            out.append(cur); cur = []
        cur.append(w)
    if cur: out.append(cur)
    return out


def faces(path, W, H, fps, dur, step=0.2):
    """Cara principal muestreada cada `step` s → lista (t, cx, cy_ojos, ancho) o None.
    Usa MediaPipe (modelo de largo alcance: aguanta perfiles y caras pequeñas)."""
    import mediapipe as mp
    det = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
    sw = 960
    sh = round(H * sw / W)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={1/step},scale={sw}:{sh}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    res, i = [], 0
    while True:
        buf = p.stdout.read(sw * sh * 3)
        if len(buf) < sw * sh * 3: break
        img = np.frombuffer(buf, np.uint8).reshape(sh, sw, 3)
        r = det.process(img)
        if r.detections:
            d = max(r.detections, key=lambda d: d.location_data.relative_bounding_box.width)
            bb = d.location_data.relative_bounding_box
            res.append((i * step, (bb.xmin + bb.width / 2) * W, (bb.ymin + bb.height * 0.42) * H, bb.width * W))
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
        s.size = round(H * (SIZE_V if VERTICAL else SIZE_H))
        s.f = s.font(s.size)
        s.fb = s.font(round(s.size * BROLL_SCALE))
        s.fh = s.font(round(H * (HOOK_V if VERTICAL else HOOK_H)))
        s.cache = {}

    def font(s, px):
        f = ImageFont.truetype(FONT, px)
        try:
            axes = f.get_variation_axes()
        except Exception:
            axes = None          # fuente estática: el grosor viene en el propio archivo
        if axes:
            vals = []
            for ax in axes:
                name = ax["name"].decode() if isinstance(ax["name"], bytes) else ax["name"]
                v = WEIGHT if name == "Weight" else (px * 0.6 if "Optical" in name else ax["default"])
                vals.append(min(ax["maximum"], max(ax["minimum"], v)))
            f.set_variation_by_axes(vals)
        return f

    def word_img(s, txt, big=False, hl=False, hook=False):
        txt = txt.strip(".,;:!?¿¡\"“”«»") or txt   # sin puntuación, como el original
        key = (txt, big, hl, hook)
        if key in s.cache: return s.cache[key]
        f = s.fh if hook else (s.fb if big else s.f)
        l, t, r, b = f.getbbox(txt)
        pad = round(f.size * 0.4)
        w, h = r - l + 2 * pad, round(f.size * 1.5) + 2 * pad
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        if SHADOW: ImageDraw.Draw(sh).text((pad - l, pad), txt, font=f, fill=(0, 0, 0, 220 if big else 170))
        sh = sh.filter(ImageFilter.GaussianBlur(max(1, f.size * 0.12)))
        im.alpha_composite(sh, (0, max(1, round(f.size * 0.03))))
        im.alpha_composite(sh, (0, 0))
        ImageDraw.Draw(im).text((pad - l, pad), txt, font=f, fill=(HL_COLOR if hl else (255, 255, 255)) + (255,))
        s.cache[key] = (im, pad, f)
        return s.cache[key]

    def layout(s, chunk, face):
        """Posición (x, y_centro) de cada palabra del bloque."""
        imgs = [s.word_img(w["w"], big=face is None) for w in chunk]
        f = imgs[0][2]
        gap = f.size * WORD_GAP
        widths = [im.width - 2 * pad for im, pad, _ in imgs]
        if face is None or face == "low":   # B-roll → una palabra centrada (o en el tercio inferior)
            return [(s.W / 2 - wd / 2, s.H * (0.78 if face == "low" else 0.5)) for wd in widths]
        if face == "top":  # plano principal sin cara detectada → arriba, centrado
            total = sum(widths) + gap * (len(widths) - 1)
            x, pos = s.W / 2 - total / 2, []
            for wd in widths:
                pos.append((x, s.H * 0.14)); x += wd + gap
            return pos
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

    def layout_block(s, chunk, yc, hook=False, maxw=0.86):
        """Bloque centrado en varias líneas (modo vertical)."""
        imgs = [s.word_img(w["w"], hl=w.get("hl", False), hook=hook) for w in chunk]
        f = imgs[0][2]
        gap, lh = f.size * 0.3, f.size * 1.08
        widths = [im.width - 2 * pad for im, pad, _ in imgs]
        x0, x1 = s.W * (1 - maxw) / 2, s.W * (1 + maxw) / 2
        lines, cur, cw = [], [], 0
        for i, wd in enumerate(widths):
            add = wd + (gap if cur else 0)
            if cur and cw + add > x1 - x0:
                lines.append((cur, cw)); cur, cw = [], 0; add = wd
            cur.append(i); cw += add
        if cur: lines.append((cur, cw))
        y = yc - lh * (len(lines) - 1) / 2
        pos = [None] * len(chunk)
        for idx, lw in lines:
            x = s.W / 2 - lw / 2
            for i in idx:
                pos[i] = (x, y); x += widths[i] + gap
            y += lh
        return pos

    def layout_hook(s, chunk, face):
        """Gancho: frase grande en varias líneas en el lado libre de la cara (o centrada)."""
        imgs = [s.word_img(w["w"], hl=w.get("hl", False), hook=True) for w in chunk]
        f = imgs[0][2]
        gap, lh = f.size * 0.28, f.size * 1.02
        widths = [im.width - 2 * pad for im, pad, _ in imgs]
        margin = s.W * 0.05
        if face is None or face == "top":
            x0, x1, align, yc = margin, s.W - margin, "center", s.H * (0.5 if face is None else 0.3)
        else:
            if len(face) == 4:     # recorrido de la cara durante toda la frase
                lb, rb, ey, _ = face
            else:
                cx, ey, fw = face
                lb, rb = cx - fw * (0.5 + FACE_GAP), cx + fw * (0.5 + FACE_GAP)
            lfree = lb - margin
            rfree = s.W - margin - rb
            if max(lfree, rfree) < s.W * 0.3:
                x0, x1, align, yc = margin, s.W - margin, "center", s.H * 0.2
            elif rfree >= lfree:
                x0, x1, align, yc = s.W - margin - rfree, s.W - margin, "left", max(ey, s.H * 0.32)
            else:
                x0, x1, align, yc = margin, margin + lfree, "right", max(ey, s.H * 0.32)
        lines, cur, cw = [], [], 0
        for i, wd in enumerate(widths):
            add = wd + (gap if cur else 0)
            if cur and cw + add > x1 - x0:
                lines.append((cur, cw)); cur, cw = [], 0; add = wd
            cur.append(i); cw += add
        if cur: lines.append((cur, cw))
        y = yc - lh * (len(lines) - 1) / 2
        y = max(margin + f.size * 0.6, min(s.H - margin - lh * (len(lines) - 1), y))
        pos = [None] * len(chunk)
        for idx, lw in lines:
            x = x0 if align == "left" else (x1 - lw if align == "right" else (x0 + x1) / 2 - lw / 2)
            for i in idx:
                pos[i] = (x, y); x += widths[i] + gap
            y += lh
        return pos

    def frame(s, t, chunk, face, hook=False):
        canvas = Image.new("RGBA", (s.W, s.H), (0, 0, 0, 0))
        vis = [w for w in chunk if t >= w["s"] - 0.03]
        if not vis: return None
        broll = face is None or face == "low"
        if VERTICAL:            # 9:16: bloque completo centrado; gancho arriba, resto bajo la cara
            pos = s.layout_block(chunk, s.H * (0.17 if hook else SUB_Y_V), hook=hook)[:len(vis)]
            broll = False
        elif hook and broll:
            vis = vis[-1:]       # gancho sobre B-roll: palabra actual, grande y centrada
            pos = s.layout_hook(vis, None)
            if face == "low": pos = [(x, s.H * 0.78) for x, _ in pos]
        elif hook:
            pos = s.layout_hook(chunk, face)[:len(vis)]
        elif broll:
            vis = vis[-1:]       # B-roll: solo la palabra actual
            pos = s.layout(vis, face)
        else:
            pos = s.layout(chunk, face)[:len(vis)]
        for w, (x, y) in zip(vis, pos):
            im, pad, f = s.word_img(w["w"], big=broll, hl=w.get("hl", False), hook=hook)
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
    ap.add_argument("--crf", default="15")
    ap.add_argument("--preset", default="slow")
    ap.add_argument("--hook", type=float, default=0.0, help="fin del gancho (s): esas frases salen en grande")
    ap.add_argument("--broll", default="", help="tramos de B-roll 'ini-fin,ini-fin' (s): palabra centrada")
    ap.add_argument("--font", help="archivo .ttf (por defecto fonts/BebasNeue-Regular.ttf)")
    ap.add_argument("--weight", type=int, help="grosor para fuentes variables (100–900)")
    ap.add_argument("--size", type=float, help="tamaño de letra relativo al alto (p. ej. 0.045)")
    ap.add_argument("--no-shadow", action="store_true", help="sin sombra")
    ap.add_argument("--vertical", action="store_true", help="formato 9:16: subtítulos centrados bajo la cara")
    ap.add_argument("--cuts", default="", help="cortes extra del A-roll 't1,t2' (s): nueva posición fija")
    a = ap.parse_args()
    global FONT, WEIGHT, SIZE_H, SHADOW, VERTICAL, MAX_WORDS
    if a.font: FONT = a.font
    if a.weight: WEIGHT = a.weight
    if a.size: SIZE_H = a.size
    if a.no_shadow: SHADOW = False
    if a.vertical: VERTICAL, MAX_WORDS = True, 4

    W, H, fps, dur = probe(a.inp)
    words = json.load(open(a.words)) if a.words else transcribe(a.inp, a.model)
    if a.dump or not a.out:
        json.dump(words, open(os.path.splitext(a.inp)[0] + ".words.json", "w"), ensure_ascii=False, indent=1)
        print("words.json guardado"); return
    print(f"{len(words)} palabras · detectando caras…", file=sys.stderr)
    fc, step = faces(a.inp, W, H, fps, dur)
    broll = [tuple(map(float, r.split("-"))) for r in a.broll.split(",") if r]
    cuts = sorted({t for r in broll for t in r} | {float(c) for c in a.cuts.split(",") if c})
    cks = chunks(words, cuts, a.hook)
    hook_ids = {i for i, c in enumerate(cks) if c[0]["s"] < a.hook}
    R = Renderer(W, H)

    # Cada plano (tramo entre cortes) recibe UNA posición de cara fija: la mediana de todas
    # las detecciones del plano. Así los subtítulos no se mueven aunque la persona se mueva.
    bounds = [0.0] + cuts + [dur + 1]
    shot_face = []
    for s0, s1 in zip(bounds, bounds[1:]):
        det = [r for r in fc if s0 <= r[0] < s1 and r[1] is not None]
        tot = [r for r in fc if s0 <= r[0] < s1]
        is_broll = any(b0 <= (s0 + s1) / 2 < b1 for b0, b1 in broll)
        if is_broll or not tot or len(det) < 0.4 * len(tot):
            shot_face.append(None)
        else:
            shot_face.append(tuple(float(np.median([r[k] for r in det])) for k in (1, 2, 3)))

    def shot_of(t):
        for k, (s0, s1) in enumerate(zip(bounds, bounds[1:])):
            if s0 <= t < s1: return k
        return len(shot_face) - 1

    def chunk_end(i):
        c = cks[i]
        end = cks[i + 1][0]["s"] - 0.03 if i + 1 < len(cks) else c[-1]["e"] + 0.6
        return min(end, c[-1]["e"] + 0.8)

    # Posición de cada bloque: se calcula una vez y no cambia mientras el bloque está en pantalla.
    anchors = []
    for i, c in enumerate(cks):
        t0, t1 = c[0]["s"] - 0.03, chunk_end(i)
        k = shot_of(t0)
        s0, s1 = bounds[k], bounds[k + 1]
        ws = c[0]["s"]
        if any(b0 - 0.05 <= ws < b1 - 0.05 for b0, b1 in broll):
            det = [r for r in fc if t0 - 0.1 <= r[0] <= t1 + 0.1 and r[1] is not None]
            busy = any(abs(r[1] - W / 2) < W * 0.25 + r[3] / 2 and abs(r[2] - H / 2) < H * 0.15 + r[3] * 0.7 for r in det)
            anchors.append("low" if busy else None); continue   # B-roll → palabra centrada (o abajo si hay cara)                       # B-roll → palabra centrada
        det = [r for r in fc if t0 - 0.1 <= r[0] <= t1 + 0.1 and r[1] is not None]
        shot = shot_face[k]
        if not det:
            anchors.append(shot if shot else "top"); continue    # sin cara → arriba, nunca encima
        if i in hook_ids:   # gancho: zona que la cara ocupa en algún momento de la frase
            g = 0.5 + FACE_GAP
            anchors.append((min(r[1] - r[3] * g for r in det), max(r[1] + r[3] * g for r in det),
                            float(np.median([r[2] for r in det])), 0)); continue
        cf = tuple(float(np.median([r[j] for r in det])) for j in (1, 2, 3))
        if shot and math.hypot(cf[0] - shot[0], cf[1] - shot[1]) < 0.4 * shot[2]:
            cf = shot                                            # plano quieto → misma posición siempre
        anchors.append(cf)

    def face_at(t, ci):
        return anchors[ci]

    def chunk_at(t):
        for i, c in enumerate(cks):
            if c[0]["s"] - 0.03 <= t < chunk_end(i): return i, c
        return None, None

    filt = (f"[0:v]{GRADE}[g];[g][1:v]overlay=0:0:format=auto,format=yuv420p[v]" if a.grade
            else "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]")
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-stats", "-y", "-i", a.inp, "-f", "rawvideo", "-pix_fmt", "rgba",
                           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-filter_complex", filt, "-map", "[v]",
                           "-map", "0:a?", "-c:v", "libx264", "-preset", a.preset, "-crf", a.crf, "-profile:v", "high",
                           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    empty = bytes(W * H * 4)
    last_key, last_buf = None, empty
    n = math.ceil(dur * fps)
    for i in range(n):
        t = i / fps
        ci, c = chunk_at(t)
        face = face_at(t, ci) if c else None
        if c:
            vis = sum(1 for w in c if t >= w["s"] - 0.03)
            fading = any(0 <= t - (w["s"] - 0.03) < FADE for w in c)
            key = (ci, vis, face, round(t, 3) if fading else None)
        else:
            key = None
        if key != last_key:
            img = R.frame(t, c, face, hook=ci in hook_ids) if c else None
            last_buf = img.tobytes() if img is not None else empty
            last_key = key
        ff.stdin.write(last_buf)
    ff.stdin.close(); ff.wait()
    print("listo:", a.out)


if __name__ == "__main__":
    main()
