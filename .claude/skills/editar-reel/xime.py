"""Formato "edición Xime" (vertical 9:16): subtítulos palabra a palabra encima de la cabeza
(Nunito Black blanco con sombra suave; lo importante en MAYÚSCULAS y amarillo) + "globitos" visuales
(tarjetas blancas tipo cristal, píldoras, lista de requisitos que se va marcando, calendario, chat, CTA).

Uso: xime.py entrada.mp4 words.json plan.json salida.mkv [--prev t1,t2,... hoja.png]
  words.json: palabras de Whisper [{word,start,end}, ...] (se pueden corregir a mano).
  plan.json:
  {
   "keywords": ["requisitos", "14", "noviembre", "completos"],   # palabras en MAYÚSCULAS amarillas
   "sub_y": null,               # null = automático encima de la cabeza; o fracción de la altura (0.38)
   "sub_words": 2,              # palabras por golpe (1–3)
   "hide_subs": [[t0, t1]],     # tramos sin subtítulos (p. ej. mientras hay una tarjeta grande)
   "items": [
     {"type": "pill",  "t0": 1.0, "t1": 3.0, "text": "Tiempo perdido", "emoji": "⏱️", "style": "dark|yellow|white|red|green"},
     {"type": "lista", "t0": 4.0, "t1": 12.0, "title": "Requisitos", "emoji": "📋",
                       "items": [[4.5, "Pasaporte vigente"], [6.0, "Permiso firmado"]]},     # cada ítem entra y se marca ✅
     {"type": "fecha", "t0": 12.5, "t1": 15.0, "day": "14", "month": "NOV", "label": "Fecha límite"},
     {"type": "card",  "t0": 15.0, "t1": 18.0, "emoji": "👵👴", "title": "Con los abuelos", "text": "Los tíos también pueden viajar"},
     {"type": "chat",  "t0": 18.0, "t1": 21.0, "name": "Administración", "msgs": [["¿Me reenvías la factura?", 0], ["¡Hola! ¿Cuándo...?", 1]]},
     {"type": "cta",   "t0": 50.0, "t1": 56.0, "text": "Comenta VIAJE", "emoji": "👇", "sub": "Te escribo al privado"}
   ]
  }
  Posición: cada item admite "y" (fracción de alto del centro, por defecto 0.17) y "x" (0.5)."""
import sys, os, json, math, re, subprocess, unicodedata
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
F900 = os.path.join(HERE, "fonts", "nunito-latin-900-normal.woff")
F800 = os.path.join(HERE, "fonts", "nunito-latin-800-normal.woff")
INTER = os.path.join(HERE, "fonts", "Inter.ttf")
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
YEL, DARK, WHITE = (255, 216, 77), (24, 28, 38), (255, 255, 255)
GREEN_WA, RED = (37, 160, 100), (230, 70, 70)

SRC, WORDS, PLAN, OUT = sys.argv[1:5]
PREV = None
if "--prev" in sys.argv:
    k = sys.argv.index("--prev"); PREV = ([float(x) for x in sys.argv[k + 1].split(",")], sys.argv[k + 2])
plan = json.load(open(PLAN)); words = json.load(open(WORDS))

pr = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                         "stream=width,height,r_frame_rate:format=duration", "-of", "json", SRC]))
sw, sh = pr["streams"][0]["width"], pr["streams"][0]["height"]
fps = eval(pr["streams"][0]["r_frame_rate"]); DUR = float(pr["format"]["duration"])
W, H = 1080, 1920                                  # salida
U = W / 1080                                       # unidad de escala

def norm(w): return re.sub(r"[^a-z0-9ñ]", "", unicodedata.normalize("NFD", w.lower()).encode("ascii", "ignore").decode())
KEYS = {norm(k) for k in plan.get("keywords", [])}

# ------------------------------------------------------------ utilidades
def ease(p): p = min(max(p, 0), 1); return 1 - (1 - p) ** 3
def back(p):
    p = min(max(p, 0), 1); c = 1.9; return 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2
def env(t, t0, t1, fi=.22, fo=.22):
    if t < t0 or t > t1: return 0.0
    return min(ease((t - t0) / fi), ease((t1 - t) / fo))
@lru_cache(None)
def font(path, size): return ImageFont.truetype(path, size)
@lru_cache(None)
def emoji_img(s, size):
    """emoji a color (Noto solo trae tamaño 109)"""
    f = ImageFont.truetype(EMOJI, 109); b = f.getbbox(s)
    im = Image.new("RGBA", (b[2] - b[0] + 8, b[3] - b[1] + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - b[0], 4 - b[1]), s, font=f, embedded_color=True)
    r = size / 109; return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)
@lru_cache(None)
def rrect(w, h, r, fill, ss=3):
    im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], r * ss, fill=fill)
    return im.resize((w, h), Image.LANCZOS)
def with_shadow(im, blur=18, op=90, dy=10):
    pad = blur * 2; sh_ = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    a = im.getchannel("A").point(lambda v: v * op // 255)
    sh_.paste(Image.new("RGBA", im.size, (0, 0, 0, 255)), (pad, pad + dy), a)
    sh_ = sh_.filter(ImageFilter.GaussianBlur(blur)); sh_.alpha_composite(im, (pad, pad)); return sh_
def put(fr, im, cx, cy, sc=1.0, a=1.0):
    if a <= .01 or sc <= .02: return
    if abs(sc - 1) > .005: im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BILINEAR)
    if a < .995: im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    x0, y0 = int(cx - im.width / 2), int(cy - im.height / 2)
    c0x, c0y = max(0, -x0), max(0, -y0); c1x, c1y = min(im.width, W - x0), min(im.height, H - y0)
    if c1x > c0x and c1y > c0y: fr.alpha_composite(im.crop((c0x, c0y, c1x, c1y)), (x0 + c0x, y0 + c0y))
def tw(s, f): return f.getlength(s)

# ------------------------------------------------------------ subtítulos
@lru_cache(None)
def sub_img(txt_):
    """golpe de 1–3 palabras; las clave en MAYÚSCULAS amarillas y un poco más grandes"""
    parts = []
    for w in txt_.split(" "):
        k = norm(w) in KEYS
        parts.append((w.upper() if k else w, YEL if k else WHITE, int((112 if k else 96) * U)))
    sp = 22 * U; tot = sum(tw(p, font(F900, s)) for p, _, s in parts) + sp * (len(parts) - 1)
    hh = int(200 * U); im = Image.new("RGBA", (int(tot + 80 * U), hh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    x = 40 * U
    for p, c, s in parts:
        f = font(F900, s); d.text((x, hh * .66), p, font=f, fill=c, anchor="ls", stroke_width=0); x += tw(p, f) + sp
    # sombra suave (sin contorno) como en el ejemplo
    # "sub_shadow" (0–255) más alto en fondos claros (pared blanca)
    op = int(plan.get("sub_shadow", 150)); sh_ = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh_.paste((0, 0, 0, 255), (0, 0), im.getchannel("A")); out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    for blur, k in ((14 * U, op / 255), (4 * U, op / 255 * .55)):
        g = sh_.filter(ImageFilter.GaussianBlur(blur)); g.putalpha(g.getchannel("A").point(lambda v: int(min(255, v * k * 1.6))))
        out.alpha_composite(g, (0, int(4 * U)))
    out.alpha_composite(im); return out

NW = int(plan.get("sub_words", 2)); CH = []
i = 0
while i < len(words):
    grp = [words[i]]
    while len(grp) < NW and i + len(grp) < len(words):
        w = words[i + len(grp)]
        if grp[-1]["word"].strip()[-1:] in ".,?!:" or w["start"] - grp[-1]["end"] > .35: break
        if norm(w["word"]) in KEYS or norm(grp[-1]["word"]) in KEYS: break        # lo importante va solo
        grp.append(w)
    CH.append([grp[0]["start"], grp[-1]["end"], " ".join(re.sub(r"[.,:;]+$", "", x["word"].strip()) for x in grp)])
    i += len(grp)
for k in range(len(CH)):
    nxt = CH[k + 1][0] if k + 1 < len(CH) else DUR
    CH[k][1] = nxt if nxt - CH[k][1] < .5 else CH[k][1] + .15

# posición automática encima de la cabeza (MediaPipe, cada 0.5 s, suavizado)
def face_tops():
    if plan.get("sub_y") is not None: return None
    try:
        import mediapipe as mp
        det = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=.5)
    except Exception: return None
    ts = np.arange(0, DUR, .5); tops = []
    for t in ts:
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", SRC, "-frames:v", "1", "-vf", "scale=360:-2",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        hh = len(raw) // (360 * 3)
        if hh == 0: tops.append(np.nan); continue
        r = det.process(np.frombuffer(raw, np.uint8).reshape(hh, 360, 3))
        if r.detections:
            b = r.detections[0].location_data.relative_bounding_box; tops.append(b.ymin - b.height * .45)
        else: tops.append(np.nan)
    tops = np.array(tops); ok = ~np.isnan(tops)
    if not ok.any(): return None
    tops = np.interp(ts, ts[ok], tops[ok])
    tops = np.convolve(np.pad(tops, 3, mode="edge"), np.ones(7) / 7, "valid")
    return ts, np.clip(tops - .06, .22, .62)
FT = face_tops()
def sub_y(t):
    if FT is None: return (plan.get("sub_y") or .38) * H
    return float(np.interp(t, FT[0], FT[1])) * H

# ------------------------------------------------------------ globitos
@lru_cache(None)
def pill(text, emoji, style, size=54):
    bg, fg = {"dark": (DARK + (235,), WHITE), "yellow": (YEL + (255,), DARK), "white": ((255, 255, 255, 240), DARK),
              "red": (RED + (255,), WHITE), "green": (GREEN_WA + (255,), WHITE)}[style]
    f = font(F900, int(size * U)); e = emoji_img(emoji, int(size * 1.05 * U)) if emoji else None
    w = int(tw(text, f) + 70 * U + (e.width + 18 * U if e else 0)); h = int(size * 1.9 * U)
    im = rrect(w, h, h // 2, bg).copy(); d = ImageDraw.Draw(im); x = 35 * U
    if e: im.alpha_composite(e, (int(x), h // 2 - e.height // 2)); x += e.width + 18 * U
    d.text((x, h / 2), text, font=f, fill=fg, anchor="lm"); return with_shadow(im, 16, 70, 8)
@lru_cache(None)
def card(emoji, title, text):
    e0 = emoji_img(emoji, int(96 * U)); ft = font(F900, int(60 * U)); fx = font(F800, int(40 * U))
    need = 120 * U + e0.width + max(tw(title, ft), tw(text, fx) if text else 0)           # ancho según el texto
    if need > 1000 * U: ft = font(F900, int(60 * U * (1000 * U - 120 * U - e0.width) / (need - 120 * U - e0.width) + .5))
    w = int(min(1000 * U, max(600 * U, need)))
    lines = wrap(text, fx, w - 120 * U - e0.width) if text else []
    h = int(max(190 * U, 70 * U + 70 * U + 52 * U * len(lines)))
    im = rrect(w, h, int(42 * U), (255, 255, 255, 238)).copy(); d = ImageDraw.Draw(im)
    e = emoji_img(emoji, int(96 * U)); im.alpha_composite(e, (int(40 * U), h // 2 - e.height // 2))
    tx = int(80 * U + e.width); y = h / 2 - (35 * U + 26 * U * len(lines))
    d.text((tx, y), title, font=ft, fill=DARK, anchor="lt")
    for k, ln in enumerate(lines): d.text((tx, y + 78 * U + 52 * U * k), ln, font=fx, fill=(95, 100, 115), anchor="lt")
    return with_shadow(im)
def wrap(s, f, maxw):
    out, cur = [], ""
    for w in s.split():
        if cur and tw(cur + " " + w, f) > maxw: out.append(cur); cur = w
        else: cur = (cur + " " + w).strip()
    return out + ([cur] if cur else [])
@lru_cache(None)
def fecha(day, month, label):
    w, h = int(330 * U), int(360 * U); im = rrect(w, h, int(44 * U), (255, 255, 255, 245)).copy(); d = ImageDraw.Draw(im)
    top = rrect(w, int(110 * U), int(44 * U), RED + (255,)); im.alpha_composite(top.crop((0, 0, w, int(110 * U))), (0, 0))
    d.rectangle([0, int(70 * U), w, int(110 * U)], fill=RED)
    d.text((w / 2, 56 * U), month.upper(), font=font(F900, int(62 * U)), fill=WHITE, anchor="mm")
    d.text((w / 2, 220 * U), day, font=font(F900, int(170 * U)), fill=DARK, anchor="mm")
    if label: d.text((w / 2, 322 * U), label, font=font(F800, int(34 * U)), fill=(110, 115, 130), anchor="mm")
    return with_shadow(im)
def lista(it, t):
    """tarjeta de requisitos: los ítems entran en su tiempo y se marcan con ✅ al entrar el siguiente (o a los 0.6 s)"""
    w = int(900 * U); rowh = int(92 * U); n = len(it["items"]); h = int(150 * U + rowh * n)
    im = rrect(w, h, int(44 * U), (255, 255, 255, 240)).copy(); d = ImageDraw.Draw(im)
    e = emoji_img(it.get("emoji", "📋"), int(66 * U)); im.alpha_composite(e, (int(40 * U), int(38 * U)))
    d.text((int(60 * U + e.width), int(74 * U)), it.get("title", "Requisitos"), font=font(F900, int(62 * U)), fill=DARK, anchor="lm")
    for k, (ti, txt_) in enumerate(it["items"]):
        y = int(150 * U + rowh * k + rowh / 2)
        if t < ti: continue
        a = ease((t - ti) / .25); xoff = int((1 - a) * 40 * U)
        col = tuple(int(255 - (255 - c) * a) for c in DARK)
        nxt = it["items"][k + 1][0] if k + 1 < n else ti + .6
        done = t >= min(nxt, ti + .9)
        bx = int(50 * U) + xoff
        if done:
            p = back((t - min(nxt, ti + .9)) / .3); ck = emoji_img("✅", int(58 * U * (.4 + .6 * p)))
            im.alpha_composite(ck, (bx + int(29 * U) - ck.width // 2, y - ck.height // 2))
        else:
            d.rounded_rectangle([bx, y - 29 * U, bx + 58 * U, y + 29 * U], int(14 * U), outline=(200, 204, 214), width=int(5 * U))
        d.text((bx + 90 * U, y), txt_, font=font(F800, int(50 * U)), fill=col, anchor="lm")
    return with_shadow(im)
@lru_cache(None)
def chat(name, msgs):
    w = int(860 * U); f = font(F800, int(36 * U)); hd = int(110 * U)
    rows = [(wrap(m, f, w * .62), me) for m, me in msgs]; h = hd + int(30 * U) + sum(int(46 * U * len(l) + 50 * U) for l, _ in rows)
    im = rrect(w, h, int(36 * U), (236, 229, 221, 245)).copy(); d = ImageDraw.Draw(im)
    top = rrect(w, hd + 40, int(36 * U), (7, 94, 84, 255)); im.alpha_composite(top.crop((0, 0, w, hd)), (0, 0))
    d.ellipse([30 * U, 22 * U, 96 * U, 88 * U], fill=(200, 215, 210))
    d.text((63 * U, 55 * U), name[:2].upper(), font=font(F900, int(28 * U)), fill=(7, 94, 84), anchor="mm")
    d.text((115 * U, 55 * U), name, font=font(F900, int(40 * U)), fill=WHITE, anchor="lm"); y = hd + 24 * U
    for lines, me in rows:
        bw = max(tw(l, f) for l in lines) + 44 * U; bh = 46 * U * len(lines) + 26 * U
        x = w - bw - 30 * U if me else 30 * U
        d.rounded_rectangle([x, y, x + bw, y + bh], int(20 * U), fill=(217, 253, 211) if me else WHITE)
        for k, l in enumerate(lines): d.text((x + 22 * U, y + 13 * U + 46 * U * k), l, font=f, fill=DARK)
        y += bh + 24 * U
    return with_shadow(im)
def cta(it):
    a = pill(it["text"], it.get("emoji", "👇"), "yellow", 64)
    if not it.get("sub"): return a
    b = pill(it["sub"], it.get("sub_emoji", "💬"), "white", 40)
    im = Image.new("RGBA", (max(a.width, b.width), a.height + b.height - int(40 * U)), (0, 0, 0, 0))
    im.alpha_composite(a, ((im.width - a.width) // 2, 0)); im.alpha_composite(b, ((im.width - b.width) // 2, a.height - int(40 * U)))
    return im

def draw_items(fr, t):
    for it in plan.get("items", []):
        t0, t1 = it["t0"], it["t1"]; a = env(t, t0, t1)
        if a <= 0: continue
        typ = it["type"]
        if typ == "pill": im = pill(it["text"], it.get("emoji"), it.get("style", "dark"), it.get("size", 54))
        elif typ == "card": im = card(it.get("emoji", "✨"), it["title"], it.get("text", ""))
        elif typ == "fecha": im = fecha(it["day"], it["month"], it.get("label", ""))
        elif typ == "lista": im = lista(it, t)
        elif typ == "chat": im = chat(it["name"], tuple((m, bool(me)) for m, me in it["msgs"]))
        elif typ == "cta": im = cta(it)
        else: continue
        p = back((t - t0) / .4); sc = .55 + .45 * p
        if typ == "cta": sc *= 1 + .025 * math.sin((t - t0) * 5)
        flo = 6 * U * math.sin((t - t0) * 2.2)                       # flota suavemente
        put(fr, im, it.get("x", .5) * W, it.get("y", .17) * H + flo, sc, a)

def subs(fr, t):
    for t0, t1, s in plan.get("hide_subs", []):
        if t0 <= t < t1: return
    for t0, t1, s in CH:
        if t0 <= t < t1:
            p = back((t - t0) / .18); put(fr, sub_img(s), W / 2, sub_y(t), .8 + .2 * p, ease((t - t0) / .08)); return

def frame(base, t):
    fr = base.convert("RGBA"); draw_items(fr, t); subs(fr, t); return fr.convert("RGB")

# ------------------------------------------------------------ render
vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
if PREV:
    ts, out = PREV; ims = []
    for t in ts:
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(t), "-i", SRC, "-frames:v", "1", "-vf", vf, "-f", "rawvideo",
                              "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        ims.append(frame(Image.frombytes("RGB", (W, H), raw), t).resize((270, 480)))
    sheet = Image.new("RGB", (270 * min(6, len(ims)), 480 * ((len(ims) + 5) // 6)))
    for k, im in enumerate(ims): sheet.paste(im, ((k % 6) * 270, (k // 6) * 480))
    sheet.save(out); sys.exit()
dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", SRC, "-vf", vf + f",fps={fps}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                        "-i", SRC, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-qp", "0", "-preset", "ultrafast", "-c:a", "copy", OUT],
                       stdin=subprocess.PIPE)
n = 0
while True:
    raw = dec.stdout.read(W * H * 3)
    if len(raw) < W * H * 3: break
    enc.stdin.write(frame(Image.frombytes("RGB", (W, H), raw), n / fps).tobytes()); n += 1
    if n % 300 == 0: print(n, flush=True)
enc.stdin.close(); enc.wait(); print("ok", n, "frames →", OUT)
