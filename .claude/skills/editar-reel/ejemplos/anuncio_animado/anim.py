"""Anuncio motion-graphics 4:3 (1440x1080) de una app, con locución TTS.
Uso: anim.py guion.json tiempos.json words.json dir_capturas salida.mkv [t_ini t_fin]
Todo se dibuja con PIL; los sprites estáticos se cachean."""
import sys, json, re, math, subprocess, unicodedata, difflib, os
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

GUION, TIEMPOS, WORDS, CAPS, OUT = sys.argv[1:6]
W, H, FPS = 1440, 1080, 30
SKILL = "/home/user/n8n/.claude/skills/editar-reel"
BEBAS = f"{SKILL}/fonts/BebasNeue-Regular.ttf"
INTER = "/usr/share/fonts/opentype/inter/Inter-{}.otf"
NAVY, NAVY2, NAVYL = (20, 33, 61), (9, 16, 33), (34, 52, 92)
GOLD, GOLDL = (201, 162, 76), (240, 200, 96)
CREAM, WHITE, GRAY = (246, 244, 239), (255, 255, 255), (170, 182, 205)
GREEN, WAG, RED = (46, 170, 98), (37, 211, 102), (226, 72, 72)

# ---------------------------------------------------------------- tiempos
guion = json.load(open(GUION)); tiempos = {b["id"]: b for b in json.load(open(TIEMPOS))}
wwords = json.load(open(WORDS))
def norm(w): return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", w.lower()).encode("ascii", "ignore").decode())
TOK = []                                     # (bloque, frase_idx, texto, t0, t1)
for b in guion:
    for fi, fr in enumerate(tiempos[b["id"]]["frases"]):
        for w in fr["txt"].split(): TOK.append([b["id"], fi, w, None, None])
A = [norm(x[2]) for x in TOK]; B = [norm(w["word"]) for w in wwords]
for blk in difflib.SequenceMatcher(None, A, B, autojunk=False).get_matching_blocks():
    for k in range(blk.size):
        TOK[blk.a + k][3] = wwords[blk.b + k]["start"]; TOK[blk.a + k][4] = wwords[blk.b + k]["end"]
# interpola los no emparejados dentro de su frase
for i, tk in enumerate(TOK):
    if tk[3] is None:
        fr = tiempos[tk[0]]["frases"][tk[1]]
        same = [j for j, x in enumerate(TOK) if x[0] == tk[0] and x[1] == tk[1]]
        prev = [j for j in same if j < i and TOK[j][3] is not None]
        nxt = [j for j in same if j > i and TOK[j][3] is not None]
        a_t, a_i = (TOK[prev[-1]][4], prev[-1]) if prev else (fr["t0"], same[0] - 1)
        b_t, b_i = (TOK[nxt[0]][3], nxt[0]) if nxt else (fr["t1"], same[-1] + 1)
        f = (i - a_i) / (b_i - a_i); tk[3] = a_t + (b_t - a_t) * f; tk[4] = tk[3] + 0.25
for tk in TOK:                               # whisper puede desplazarse: acota a la frase
    fr = tiempos[tk[0]]["frases"][tk[1]]; tk[3] = min(max(tk[3], fr["t0"]), fr["t1"])
def T(bid, key, occ=0, d=0.0):
    k = norm(key); c = 0
    for tk in TOK:
        if tk[0] == bid and norm(tk[2]).startswith(k):
            if c == occ: return tk[3] + d
            c += 1
    raise KeyError(f"{bid}:{key}")
S0 = {b: tiempos[b]["t0"] for b in tiempos}; S1 = {b: tiempos[b]["t1"] for b in tiempos}
END = S1["cta"] + 1.6

# ---------------------------------------------------------------- utilidades gráficas
@lru_cache(None)
def font(kind, size):
    return ImageFont.truetype(BEBAS if kind == "bebas" else INTER.format(kind), size)
def ease(p): p = min(max(p, 0), 1); return 1 - (1 - p) ** 3
def back(p):
    p = min(max(p, 0), 1); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2
def env(t, t0, t1=None, fi=0.3, fo=0.3):
    """alpha de entrada/salida"""
    if t < t0: return 0.0
    a = ease((t - t0) / fi)
    if t1 is not None: a *= 1 - ease((t - (t1 - fo)) / fo) if t > t1 - fo else 1
    return max(0.0, min(1.0, a))

@lru_cache(None)
def rrect(w, h, r, fill, outline=None, ow=0, ss=3):
    im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], r * ss, fill=fill, outline=outline, width=ow * ss)
    return im.resize((w, h), Image.LANCZOS)
@lru_cache(None)
def circle(r, fill, outline=None, ow=0, ss=3):
    im = Image.new("RGBA", (2 * r * ss, 2 * r * ss), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, 2 * r * ss - 1, 2 * r * ss - 1], fill=fill, outline=outline, width=ow * ss)
    return im.resize((2 * r, 2 * r), Image.LANCZOS)
@lru_cache(None)
def txt(s, kind, size, col):
    f = font(kind, size); b = f.getbbox(s)
    im = Image.new("RGBA", (b[2] - b[0] + 4, b[3] - b[1] + 4), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((2 - b[0], 2 - b[1]), s, font=f, fill=col)
    return im
@lru_cache(None)
def txt_line(s, kind, size, col, kcol=None, gap=None):
    """línea con palabras clave marcadas con *asteriscos*"""
    f = font(kind, size); sp = gap if gap is not None else f.getlength(" ")
    parts = [(w.strip("*"), kcol if w.startswith("*") else col) for w in s.split()]
    asc, desc = f.getmetrics(); hh = asc + desc
    ww = int(sum(f.getlength(p) for p, _ in parts) + sp * (len(parts) - 1)) + 4
    im = Image.new("RGBA", (ww, hh), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 2
    for p, c in parts: d.text((x, 0), p, font=f, fill=c); x += f.getlength(p) + sp
    return im

def put(fr, im, x, y, sc=1.0, a=1.0, anchor="mm"):
    if a <= 0.003 or sc <= 0.01: return
    if abs(sc - 1) > 0.004:
        im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BILINEAR)
    if a < 0.997:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    x0 = int(round(x - (im.width / 2 if anchor[0] == "m" else 0 if anchor[0] == "l" else im.width)))
    y0 = int(round(y - (im.height / 2 if anchor[1] == "m" else 0 if anchor[1] == "t" else im.height)))
    cx0, cy0 = max(0, -x0), max(0, -y0)
    cx1, cy1 = min(im.width, fr.width - x0), min(im.height, fr.height - y0)
    if cx1 <= cx0 or cy1 <= cy0: return
    fr.alpha_composite(im.crop((cx0, cy0, cx1, cy1)), (x0 + cx0, y0 + cy0))

@lru_cache(None)
def shadow(w, h, r, blur=22, op=110):
    pad = blur * 2; im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([pad, pad + 10, pad + w, pad + h + 10], r, fill=(0, 0, 0, op))
    return im.filter(ImageFilter.GaussianBlur(blur))

# ---------------------------------------------------------------- iconos
def ic_check(d, cx, cy, r, col=WHITE, w=None):
    w = w or max(3, r // 4)
    d.line([(cx - r * .5, cy + r * .02), (cx - r * .12, cy + r * .4), (cx + r * .55, cy - r * .38)], fill=col, width=int(w), joint="curve")
@lru_cache(None)
def icon(name, r, bg=GOLD, fg=NAVY):
    ss = 3; R = r * ss
    im = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, 2 * R - 1, 2 * R - 1], fill=bg); c = R; lw = max(2, int(R * .11))
    if name == "check": ic_check(d, c, c, R * .9, fg, lw * 1.4 // 1)
    elif name == "cal":
        d.rounded_rectangle([c - R * .5, c - R * .4, c + R * .5, c + R * .5], R * .1, outline=fg, width=lw)
        d.line([(c - R * .5, c - R * .12), (c + R * .5, c - R * .12)], fill=fg, width=lw)
        for dx in (-.25, .25): d.line([(c + R * dx, c - R * .55), (c + R * dx, c - R * .3)], fill=fg, width=lw)
    elif name == "court":
        d.rectangle([c - R * .35, c - R * .55, c + R * .35, c + R * .55], outline=fg, width=lw)
        d.line([(c - R * .35, c), (c + R * .35, c)], fill=fg, width=lw)
        d.line([(c, c - R * .3), (c, c + R * .3)], fill=fg, width=lw // 2 + 1)
        d.line([(c - R * .35, c - R * .3), (c + R * .35, c - R * .3)], fill=fg, width=lw // 2 + 1)
        d.line([(c - R * .35, c + R * .3), (c + R * .35, c + R * .3)], fill=fg, width=lw // 2 + 1)
    elif name == "tap":
        d.ellipse([c - R * .22, c - R * .5, c + R * .22, c - R * .06], outline=fg, width=lw)
        d.rounded_rectangle([c - R * .22, c - R * .3, c + R * .22, c + R * .55], R * .2, fill=fg)
    elif name == "pair":
        for dx in (-.25, .25):
            d.ellipse([c + R * (dx - .17), c - R * .45, c + R * (dx + .17), c - R * .1], fill=fg)
            d.pieslice([c + R * (dx - .3), c - R * .02, c + R * (dx + .3), c + R * .6], 180, 360, fill=fg)
    elif name == "level":
        for k, hh in enumerate((.3, .55, .8)):
            x = c - R * .45 + k * R * .33; d.rectangle([x, c + R * .45 - R * hh, x + R * .22, c + R * .45], fill=fg)
    elif name == "ticket":
        d.rounded_rectangle([c - R * .55, c - R * .32, c + R * .55, c + R * .32], R * .08, outline=fg, width=lw)
        d.line([(c + R * .15, c - R * .3), (c + R * .15, c + R * .3)], fill=fg, width=lw // 2 + 1)
    elif name == "wallet":
        d.rounded_rectangle([c - R * .55, c - R * .38, c + R * .55, c + R * .42], R * .12, outline=fg, width=lw)
        d.rounded_rectangle([c + R * .1, c - R * .1, c + R * .55, c + R * .16], R * .06, fill=fg)
    elif name == "bell":
        d.pieslice([c - R * .42, c - R * .5, c + R * .42, c + R * .35], 180, 360, fill=fg)
        d.rectangle([c - R * .42, c - R * .08, c + R * .42, c + R * .3], fill=fg)
        d.polygon([(c - R * .55, c + R * .32), (c + R * .55, c + R * .32), (c + R * .42, c + R * .15), (c - R * .42, c + R * .15)], fill=fg)
        d.ellipse([c - R * .12, c + R * .36, c + R * .12, c + R * .58], fill=fg)
    elif name == "trophy":
        d.pieslice([c - R * .38, c - R * .7, c + R * .38, c + R * .2], 0, 180, fill=fg)
        d.rectangle([c - R * .07, c + R * .15, c + R * .07, c + R * .4], fill=fg)
        d.rounded_rectangle([c - R * .3, c + R * .38, c + R * .3, c + R * .52], R * .05, fill=fg)
        d.arc([c - R * .62, c - R * .45, c - R * .2, c - R * .02], 90, 270, fill=fg, width=lw)
        d.arc([c + R * .2, c - R * .45, c + R * .62, c - R * .02], 270, 90, fill=fg, width=lw)
    elif name == "gift":
        d.rectangle([c - R * .5, c - R * .15, c + R * .5, c + R * .5], fill=fg)
        d.rectangle([c - R * .58, c - R * .35, c + R * .58, c - R * .12], fill=fg)
        d.rectangle([c - R * .07, c - R * .35, c + R * .07, c + R * .5], fill=bg)
        d.ellipse([c - R * .4, c - R * .62, c - R * .02, c - R * .32], outline=fg, width=lw)
        d.ellipse([c + R * .02, c - R * .62, c + R * .4, c - R * .32], outline=fg, width=lw)
    elif name == "shield":
        d.polygon([(c, c - R * .6), (c + R * .5, c - R * .38), (c + R * .42, c + R * .2), (c, c + R * .6), (c - R * .42, c + R * .2), (c - R * .5, c - R * .38)], fill=fg)
    elif name == "phone":
        d.rounded_rectangle([c - R * .3, c - R * .55, c + R * .3, c + R * .55], R * .1, outline=fg, width=lw)
        d.line([(c - R * .1, c + R * .4), (c + R * .1, c + R * .4)], fill=fg, width=lw)
    elif name == "plus":
        d.line([(c - R * .45, c), (c + R * .45, c)], fill=fg, width=lw * 2); d.line([(c, c - R * .45), (c, c + R * .45)], fill=fg, width=lw * 2)
    elif name == "clubs":
        for dx, dy in ((-.28, -.25), (.28, -.25), (0, .28)):
            d.rounded_rectangle([c + R * (dx - .2), c + R * (dy - .2), c + R * (dx + .2), c + R * (dy + .2)], R * .05, fill=fg)
    return im.resize((2 * r, 2 * r), Image.LANCZOS)

# ---------------------------------------------------------------- fondo
def make_bg():
    bw, bh = W + 160, H + 120
    y, x = np.mgrid[0:bh, 0:bw]
    d = np.sqrt(((x - bw * .62) / bw) ** 2 + ((y - bh * .42) / bh) ** 2)
    k = np.clip(d / .75, 0, 1)[..., None]
    arr = np.array(NAVY, float) * (1 - k) + np.array(NAVY2, float) * k
    im = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
    ov = Image.new("RGBA", (bw, bh), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    # pista de pádel en perspectiva muy tenue
    cx, cy = bw * .62, bh * .55; col = GOLD + (26,)
    pts = [(cx - 520, cy + 420), (cx + 520, cy + 420), (cx + 300, cy - 380), (cx - 300, cy - 380)]
    d.polygon(pts, outline=col, width=3)
    d.line([(cx - 410, cy + 20), (cx + 410, cy + 20)], fill=GOLD + (34,), width=4)
    for f in (.28, .72):
        y0 = cy - 380 + 800 * f; half = 300 + 220 * f
        d.line([(cx - half, y0), (cx + half, y0)], fill=col, width=2)
    d.line([(cx, cy - 380 + 800 * .28), (cx, cy - 380 + 800 * .72)], fill=col, width=2)
    rng = np.random.default_rng(4)
    for _ in range(60):
        px, py, r = rng.uniform(0, bw), rng.uniform(0, bh), rng.uniform(1, 2.6)
        d.ellipse([px - r, py - r, px + r, py + r], fill=GOLDL + (int(rng.uniform(20, 70)),))
    return Image.alpha_composite(im, ov)
BG = make_bg()

# ---------------------------------------------------------------- capturas / teléfono
SW, SH = 360, 779; SCALE = SW / 780
def cap(name):
    im = Image.open(os.path.join(CAPS, name)).convert("RGB")
    if im.height < 1688:                       # hojas inferiores: cabecera de la app + hoja
        base = Image.new("RGB", (780, 1688), CREAM)
        base.paste(Image.open(os.path.join(CAPS, "i-002.png")).convert("RGB").crop((0, 0, 780, 150)), (0, 0))
        base.paste(im, (0, 150)); im = base
    return im.resize((SW, SH), Image.LANCZOS).convert("RGBA")
CAPS_ = {n: cap(n) for n in ["i-002.png", "i-007.png", "i-011.png", "i-015.png", "i-019.png", "i-022.png", "i-025.png",
                             "i-026.png", "i-027.png", "i-028.png", "i-032.png", "i-035.png", "i-038.png", "i-041.png"]}
def recolor(im, rgb):
    """cambia el azul marino de la cabecera por otro color de marca (club ficticio)"""
    a = np.array(im).astype(float); src = np.array(NAVY, float)
    dist = np.sqrt(((a[..., :3] - src) ** 2).sum(-1)); m = np.clip(1 - dist / 60, 0, 1)[..., None]
    a[..., :3] = a[..., :3] * (1 - m) + np.array(rgb, float) * m
    return Image.fromarray(a.astype(np.uint8))
BEZ = 13; PW, PH = SW + 2 * BEZ, SH + 2 * BEZ
MASK = rrect(SW, SH, 40, (255, 255, 255, 255)).getchannel("A")
FRAME = rrect(PW, PH, 52, (8, 12, 22, 255), (70, 82, 110, 255), 2)
PSHADOW = shadow(PW, PH, 52, 26, 150)

def phone_img(screen):
    im = FRAME.copy(); sc = screen.copy(); sc.putalpha(MASK); im.alpha_composite(sc, (BEZ, BEZ))
    d = ImageDraw.Draw(im); d.rounded_rectangle([PW / 2 - 50, BEZ + 8, PW / 2 + 50, BEZ + 30], 11, fill=(8, 12, 22))
    return im

# pantalla: secuencia de (t, captura) con fundido + overlays
SCREENS = []           # (t, nombre)
HL = []                # (t0, t1, (x0,y0,x1,y1) en coords 780x1688)
TAPS = []              # (t, (x,y))
NOTIF = []             # (t0, t1, título, sub)
def scr(t, n): SCREENS.append((t, n))
def hl(t0, t1, box): HL.append((t0, t1, box))
def tap(t, xy): TAPS.append((t, xy))
def screen_at(t):
    seq = sorted(SCREENS); cur = seq[0][1]; prev = None; tc = -9
    for ts, n in seq:
        if t >= ts: prev, cur, tc = cur, n, ts
    im = CAPS_[cur].copy()
    if prev and prev != cur and t - tc < .35:            # la nueva sube como hoja
        p = ease((t - tc) / .35); base = CAPS_[prev].copy()
        nw = CAPS_[cur].copy(); nw.putalpha(int(255 * min(1, p * 1.6)))
        base.alpha_composite(nw, (0, int((1 - p) * 90))); im = base
    for t0, t1, (x0, y0, x1, y1) in HL:             # foco: oscurece el resto de la pantalla
        a = env(t, t0, t1, .25, .25)
        if a > 0:
            ov = Image.new("RGBA", (SW, SH), (10, 16, 30, int(120 * a)))
            ImageDraw.Draw(ov).rounded_rectangle([x0 * SCALE - 6, y0 * SCALE - 6, x1 * SCALE + 6, y1 * SCALE + 6], 12, fill=(0, 0, 0, 0))
            im.alpha_composite(ov)
    d = ImageDraw.Draw(im)
    for t0, t1, (x0, y0, x1, y1) in HL:
        a = env(t, t0, t1, .25, .25)
        if a > 0:
            pul = .5 + .5 * math.sin((t - t0) * 6); g = 4 + 3 * pul
            d.rounded_rectangle([x0 * SCALE - g, y0 * SCALE - g, x1 * SCALE + g, y1 * SCALE + g], 12,
                                outline=GOLDL + (int(255 * a),), width=5)
    for ts, (x, y) in TAPS:
        if 0 <= t - ts < .6:
            p = (t - ts) / .6; r = 10 + 34 * ease(p); al = int(200 * (1 - p))
            d.ellipse([x * SCALE - r, y * SCALE - r, x * SCALE + r, y * SCALE + r], outline=(255, 255, 255, al), width=4)
            if p < .35: d.ellipse([x * SCALE - 12, y * SCALE - 12, x * SCALE + 12, y * SCALE + 12], fill=(255, 255, 255, 170))
    for t0, t1, ti, sub in NOTIF:
        a = env(t, t0, t1, .35, .3)
        if a > 0:
            p = back((t - t0) / .45) if t < t0 + .45 else 1
            card = notif_card(ti, sub); y = -card.height + (52 + card.height) * p
            if t > t1 - .3: y = 52 - (52 + card.height) * ease((t - (t1 - .3)) / .3)
            put(im, card, SW / 2, y, anchor="mt")
    return im

@lru_cache(None)
def notif_card(ti, sub):
    w, h = SW - 22, 82; im = rrect(w, h, 18, (255, 255, 255, 250)).copy()
    im.alpha_composite(icon("bell", 22, NAVY, GOLDL), (12, 19))
    d = ImageDraw.Draw(im)
    d.text((66, 15), ti, font=font("Bold", 19), fill=NAVY); d.text((66, 44), sub, font=font("Medium", 15), fill=(90, 98, 115))
    d.text((w - 46, 15), "ahora", font=font("Medium", 13), fill=(140, 146, 160))
    return im

# ---------------------------------------------------------------- piezas izquierda
LX = 92
@lru_cache(None)
def header_img(num, title):
    t = txt(title, "bebas", 92, WHITE); c = circle(36, GOLD + (255,))
    im = Image.new("RGBA", (t.width + 100, 92), (0, 0, 0, 0)); im.alpha_composite(c, (0, 8))
    n = txt(str(num), "bebas", 54, NAVY); im.alpha_composite(n, (36 - n.width // 2, 44 - n.height // 2 + 1))
    im.alpha_composite(t, (92, 46 - t.height // 2)); return im
def header(fr, t, t0, t1, num, title):
    a = env(t, t0, t1, .35, .3); dx = (1 - ease((t - t0) / .45)) * -40
    put(fr, header_img(num, title), LX + dx, 120, a=a, anchor="lm")
    # subrayado dorado
    if a > 0:
        w = int(160 * ease((t - t0 - .15) / .5)); d = ImageDraw.Draw(fr)
        if w > 2: d.rounded_rectangle([LX + 92, 172, LX + 92 + w, 178], 3, fill=GOLD + (int(255 * a),))

@lru_cache(None)
def step_img(num, title, sub, done=False):
    w = 700; h = 108 if sub else 84
    im = rrect(w, h, 22, NAVYL + (235,)).copy()
    ic = icon("check", 26, GREEN, WHITE) if done else icon(num, 26) if not str(num).isdigit() else None
    if ic is None:
        c = circle(26, GOLD + (255,)); im.alpha_composite(c, (18, h // 2 - 26))
        n = txt(str(num), "bebas", 38, NAVY); im.alpha_composite(n, (44 - n.width // 2, h // 2 - n.height // 2 + 1))
    else: im.alpha_composite(ic, (18, h // 2 - 26))
    tt = txt(title, "bebas", 58, WHITE); im.alpha_composite(tt, (88, (14 if sub else h // 2 - tt.height // 2)))
    if sub:
        s = txt(sub, "Medium", 25, GRAY); im.alpha_composite(s, (89, 70))
    return im
def step(fr, t, t0, t1, y, num, title, sub=None, done_t=None):
    EVENTS.add(round(t0, 2)); a = env(t, t0, t1, .25, .3)
    if a <= 0: return
    p = back((t - t0) / .45); sc = .85 + .15 * p
    done = done_t is not None and t >= done_t
    put(fr, step_img(num, title, sub, done), LX + 350, y, sc=sc, a=a)

@lru_cache(None)
def pill(s, bg, fg, size=40, padx=26, h=64, ic=None):
    t = txt(s, "bebas", size, fg); extra = (h - 14 + 10) if ic else 0
    im = rrect(t.width + 2 * padx + extra, h, h // 2, bg + (255,)).copy()
    if ic: im.alpha_composite(icon(ic, (h - 14) // 2, fg, bg), (8, 7))
    im.alpha_composite(t, (padx + extra, h // 2 - t.height // 2 + 1)); return im
EVENTS = set()
def popin(fr, t, t0, t1, im, x, y, anchor="mm"):
    EVENTS.add(round(t0, 2)); a = env(t, t0, t1, .2, .3)
    if a <= 0: return
    put(fr, im, x, y, sc=.6 + .4 * back((t - t0) / .4), a=a, anchor=anchor)

# ---------------------------------------------------------------- subtítulos
KEY = {norm(k) for k in "whatsapp niveles torneos movil siete dia pistas hueco pareja nivel bonos saldo cuatro aviso "
       "sube baja nueve cien fuerte resultado confirma premios puntos panel recargas permisos minuto app clubes marca padel xzen".split()}
SUBS = []
for b in guion:
    if b["id"] == "hook": continue
    for fi, frs in enumerate(tiempos[b["id"]]["frases"]):
        toks = [x for x in TOK if x[0] == b["id"] and x[1] == fi]
        ch = []
        for i, tk in enumerate(toks):
            ch.append(tk)
            L = sum(len(x[2]) + 1 for x in ch)
            end = tk[2][-1] in ",.:?!" or i == len(toks) - 1
            if end or len(ch) >= 4 or L > 24:
                SUBS.append([ch[0][3], None, " ".join(("*" if norm(x[2]) in KEY else "") + x[2].upper().rstrip(",.:") for x in ch)])
                ch = []
for i, s in enumerate(SUBS):
    s[1] = SUBS[i + 1][0] if i + 1 < len(SUBS) and SUBS[i + 1][0] - s[0] < 1.2 else s[0] + 1.4
    if i + 1 < len(SUBS): s[1] = min(s[1], SUBS[i + 1][0])
def subtitles(fr, t):
    for t0, t1, s in SUBS:
        if t0 <= t < t1 and t < S1["multi"] + .2:
            im = txt_line(s.replace("¿", "").replace("?", ""), "bebas", 64, WHITE, GOLDL)
            p = ease((t - t0) / .12); put(fr, im, W / 2, 1012, sc=.94 + .06 * p, a=p)

# ---------------------------------------------------------------- guion visual
# fondo: chat caótico del gancho
CHAT = [("¿Quién juega mañana?", 0), ("Yo!! a qué hora?", 1), ("Falta uno para las 19:00", 0), ("¿Alguien de 3ª?", 0),
        ("Yo pago la pista y me pasan", 1), ("Al final no puedo :(", 0), ("¿Quién lleva pelotas?", 1), ("Somos 5??", 0),
        ("¿Cuánto era cada uno?", 1), ("Me apunto si es a las 20", 0)]
@lru_cache(None)
def bubble(s, me):
    f = font("Medium", 26); w = int(f.getlength(s)) + 40
    im = rrect(w, 58, 18, ((220, 248, 198, 255) if me else (255, 255, 255, 255))).copy()
    ImageDraw.Draw(im).text((20, 13), s, font=f, fill=(25, 30, 40)); return im
rng = np.random.default_rng(7)
CHATPOS = [(rng.uniform(80, 1100), 120 + k * 88 + rng.uniform(-20, 20), rng.uniform(0, 6)) for k in range(len(CHAT))]

def logo_img(size):
    a = txt("Xzen", "Bold", size, WHITE); b = txt("Pádel", "Bold", size, GOLDL); ic = icon("court", int(size * .62), GOLD, NAVY)
    im = Image.new("RGBA", (ic.width + 24 + a.width + int(size * .25) + b.width, max(ic.height, a.height) + 4), (0, 0, 0, 0))
    im.alpha_composite(ic, (0, (im.height - ic.height) // 2)); x = ic.width + 24
    im.alpha_composite(a, (x, (im.height - a.height) // 2)); x += a.width + int(size * .25)
    im.alpha_composite(b, (x, (im.height - b.height) // 2)); return im
LOGO_BIG = logo_img(120); LOGO_MID = logo_img(84)

# ---- eventos de pantalla del teléfono
scr(0, "i-002.png")
scr(T("reserva", "tocas", d=.45), "i-007.png"); tap(T("reserva", "tocas", d=.05), (300, 660))
hl(T("reserva", "eliges"), T("reserva", "pistas") - .1, (8, 187, 772, 300))
hl(T("reserva", "pistas"), T("reserva", "tocas"), (0, 495, 780, 830))
hl(T("reserva", "hueco", d=.3), T("reserva", "pareja", 0) - .1, (405, 1385, 752, 1562))
scr(T("reserva", "pareja", 0, -.3), "i-011.png")
hl(T("reserva", "pareja", 0), T("reserva", "nivel") - .1, (402, 1058, 714, 1190))
hl(T("reserva", "nivel"), S1["reserva"], (574, 292, 716, 340))
scr(S0["pago"] + .05, "i-026.png")
hl(T("pago", "bonos"), T("pago", "saldo"), (20, 660, 520, 840))
hl(T("pago", "saldo"), T("pago", "cuatro") - .1, (20, 200, 760, 345))
scr(T("pago", "cuatro", d=-.2), "i-007.png")
NOTIF.append((T("pago", "aviso", d=-.1), S1["pago"] - .05, "Partido completo · 4/4", "Pista 1 · Mar 10 · 10:30"))
scr(S0["nivel"] + .05, "i-015.png")
hl(T("nivel", "nueve"), T("nivel", "fuerte") - .2, (20, 190, 760, 540))
hl(T("nivel", "fuerte"), S1["nivel"], (20, 700, 760, 860))
scr(S0["result"] + .05, "i-019.png")
hl(S0["result"] + .4, T("result", "confirma") - .45, (280, 1150, 720, 1375))
scr(T("result", "confirma", d=-.4), "i-022.png"); tap(T("result", "confirma", d=.25), (200, 1565))
hl(T("result", "confirma"), S1["result"], (28, 1495, 378, 1640))
scr(S0["torneos"] + .05, "i-025.png")
scr(T("torneos", "saldo", d=-.15), "i-026.png")
scr(T("torneos", "puntos", d=-.15), "i-027.png")
scr(S0["club"] + .05, "i-028.png")
scr(T("club", "recargas", d=-.15), "i-035.png")
scr(T("club", "resultados", d=-.15), "i-028.png")
hl(T("club", "resultados"), T("club", "premios") - .1, (20, 760, 760, 955))
hl(T("club", "premios"), T("club", "niveles") - .1, (20, 1075, 760, 1345))
scr(T("club", "niveles", d=-.15), "i-035.png")
hl(T("club", "niveles"), T("club", "torneos") - .1, (20, 640, 760, 1170))
scr(T("club", "torneos", d=-.15), "i-038.png")
scr(S0["multi"] + .05, "i-002.png")

PHONE_IN = T("intro", "app", d=-.3)
CLUB_B = recolor(phone_img(CAPS_["i-002.png"]), (16, 92, 70)); CLUB_C = recolor(phone_img(CAPS_["i-002.png"]), (120, 30, 48))

def phone_pose(t):
    """(x, y, escala, alpha)"""
    if t < PHONE_IN: return None
    x = 1085 + 520 * (1 - ease((t - PHONE_IN) / .6)); y, sc = 500, 1.08
    if t > S0["multi"]:
        p = ease((t - S0["multi"]) / .6); x = x + (W / 2 - x) * p; sc = 1.08 - .26 * p; y = 500 + 40 * p
    a = 1.0
    if t > S0["cta"]: a = 1 - ease((t - S0["cta"]) / .4)
    return x, y, sc, a

# ---------------------------------------------------------------- render por fotograma
def frame(t):
    ox = 80 + 40 * math.sin(t * .12); oy = 60 + 30 * math.cos(t * .09)
    fr = BG.crop((int(ox), int(oy), int(ox) + W, int(oy) + H)).copy()
    d = ImageDraw.Draw(fr)

    # --- GANCHO
    if t < S0["intro"] + .7:
        out = ease((t - S0["intro"]) / .6)
        for k, ((s, me), (x, y, ph)) in enumerate(zip(CHAT, CHATPOS)):
            tk = .1 + k * .3
            if t < tk: continue
            a = env(t, tk, None, .2) * (1 - out) * .55
            jx = 6 * math.sin(t * 3 + ph); jy = 4 * math.cos(t * 2.4 + ph) - out * 300 * (1 if k % 2 else -1)
            put(fr, bubble(s, me), x + jx, y + jy, sc=.8 + .2 * back((t - tk) / .3), a=a, anchor="lm")
        # badge 99+
        if t > 1.0:
            put(fr, pill("99+", RED, WHITE, 40, 18, 58), 1300, 110, sc=.6 + .4 * back((t - 1.0) / .3), a=1 - out)
        scrim = int(150 * (1 - out)); fr.alpha_composite(Image.new("RGBA", (W, H), NAVY2 + (scrim,)))
        lines = [["¿TU", "CLUB", "DE", "PÁDEL"], ["TODAVÍA", "ORGANIZA", "LOS", "PARTIDOS"], ["POR", "WHATSAPP?"]]
        hw = [x for x in TOK if x[0] == "hook"]; idx = 0
        for li, ln in enumerate(lines):
            f = font("bebas", 150 if li == 2 else 112); ws = [f.getlength(w) for w in ln]; sp = f.getlength(" ")
            x = W / 2 - (sum(ws) + sp * (len(ln) - 1)) / 2; y = [300, 430, 590][li]
            for w, wl in zip(ln, ws):
                tw = hw[idx][3] - .05; idx += 1
                if t >= tw:
                    p = back((t - tw) / .25); a = env(t, tw, None, .1) * (1 - out)
                    col = WAG if "WHATSAPP" in w else (GOLDL if w in ("PÁDEL",) else WHITE)
                    put(fr, txt(w, "bebas", 150 if li == 2 else 112, col), x + wl / 2, y, sc=.7 + .3 * p, a=a)
                x += wl + sp

    # --- INTRO: logo + chips
    if S0["intro"] <= t < S1["intro"] + .4:
        t0 = S0["intro"] + .1
        p = back((t - t0) / .55); a = env(t, t0, S1["intro"] + .4, .25, .35)
        mv = ease((t - PHONE_IN) / .6)
        x = W / 2 + (LX + LOGO_BIG.width * .62 / 2 - W / 2) * mv; y = H / 2 - 30 + (150 - H / 2 + 30) * mv
        put(fr, LOGO_BIG, x, y, sc=(.6 + .4 * p) * (1 - .38 * mv), a=a)
        if mv < .5:
            put(fr, txt("LA APP DE TU CLUB", "bebas", 60, GRAY), W / 2, H / 2 + 80, a=a * (1 - 2 * mv) * env(t, t0 + .5, None, .3))
        for k, (w, s, ic) in enumerate([("niveles", "RESERVA POR NIVELES", "level"), ("torneos", "TORNEOS", "trophy"), ("pagar", "PAGO DESDE EL MÓVIL", "phone")]):
            tw = T("intro", w, d=-.1)
            popin(fr, t, tw, S1["intro"] + .4, pill(s, NAVYL, WHITE, 52, 30, 86, ic), LX, 340 + k * 120, anchor="lm")

    # --- 1 RESERVA
    if S0["reserva"] - .1 <= t < S1["reserva"] + .3:
        a0, a1 = S0["reserva"], S1["reserva"] + .3
        header(fr, t, a0, a1, 1, "RESERVA EN 3 TOQUES")
        ys = [268, 390, 512, 634, 756]
        step(fr, t, T("reserva", "eliges", d=-.1), a1, ys[0], "cal", "ELIGE EL DÍA", "Hoy o hasta 7 días de antelación", T("reserva", "pistas"))
        step(fr, t, T("reserva", "pistas", d=-.1), a1, ys[1], "court", "MIRA LAS PISTAS LIBRES", "Franjas de 90 min con 4 huecos", T("reserva", "tocas"))
        step(fr, t, T("reserva", "tocas", d=-.1), a1, ys[2], "tap", "TOCA UN HUECO", "Y ya estás dentro", T("reserva", "pareja"))
        step(fr, t, T("reserva", "pareja", 0, -.1), a1, ys[3], "pair", "SOLO O CON PAREJA", "Cada uno paga su parte", T("reserva", "nivel"))
        step(fr, t, T("reserva", "nivel", d=-.1), a1, ys[4], "level", "SOLO PARTIDOS DE TU NIVEL", "Juegas con 3ª C y 3ª B")
        popin(fr, t, T("reserva", "siete", d=-.05), a1, pill("7 DÍAS DE ANTELACIÓN", GOLD, NAVY, 40, 24, 62), LX + 350, 862)

    # --- 2 PAGO
    if S0["pago"] - .1 <= t < S1["pago"] + .3:
        a0, a1 = S0["pago"], S1["pago"] + .3
        header(fr, t, a0, a1, 2, "SE PAGA SOLO")
        tb, ts = T("pago", "bonos", d=-.1), T("pago", "saldo", d=-.1)
        popin(fr, t, tb, a1, money_card("ticket", "1º  CON TU BONO", "1 bono disponible"), LX + 350, 290)
        if t > ts - .3:   # flecha
            p = ease((t - ts + .3) / .35); ax = LX + 350
            d.line([(ax, 362), (ax, 362 + 64 * p)], fill=GOLD + (int(255 * env(t, ts - .3, a1)),), width=6)
            if p > .9: d.polygon([(ax - 14, 418), (ax + 14, 418), (ax, 436)], fill=GOLD + (int(255 * env(t, ts - .3, a1)),))
            put(fr, txt("SI NO TIENES", "bebas", 34, GRAY), ax + 30, 398, a=env(t, ts - .2, a1), anchor="lm")
        popin(fr, t, ts, a1, money_card("wallet", "2º  CON TU SALDO", "Saldo disponible $1,500"), LX + 350, 510)
        tc = T("pago", "cuatro", d=-.1)
        put(fr, txt("JUGADORES", "bebas", 40, GRAY), LX, 640, a=env(t, tc, a1), anchor="lm")
        for k, ini in enumerate(["DH", "ML", "FR", "RS"]):
            tk = tc + .18 * k
            popin(fr, t, tk, a1, avatar(ini), LX + 50 + k * 120, 730)
        tf = tc + .9
        popin(fr, t, tf, a1, pill("4/4 · PARTIDO COMPLETO", GREEN, WHITE, 40, 24, 62, "check"), LX, 840, anchor="lm")

    # --- 3 NIVEL
    if S0["nivel"] - .1 <= t < S1["nivel"] + .3:
        a0, a1 = S0["nivel"], S1["nivel"] + .3
        header(fr, t, a0, a1, 3, "TU NIVEL SE MUEVE")
        tn = T("nivel", "nueve", d=-.1)
        LV = ["4C", "4B", "4A", "3C", "3B", "3A", "2B", "2A", "1A"]
        for k, s in enumerate(LV):
            tk = tn + .06 * k
            popin(fr, t, tk, a1, lvl_chip(s, k == 4), LX + 36 + k * 76, 300)
        tc = T("nivel", "cero", d=-.1)
        a = env(t, tc - .2, a1)
        if a > 0:
            bw = 664; p = ease((t - tc) / 1.6); pct = int(round(100 * p))
            put(fr, rrect(bw, 26, 13, (255, 255, 255, 40)), LX, 420, a=a, anchor="lm")
            if p > .02: put(fr, rrect(max(26, int(bw * p)), 26, 13, GOLD + (255,)), LX, 420, a=a, anchor="lm")
            put(fr, txt(f"{pct} %", "bebas", 78, GOLDL), LX + bw, 362, a=a, anchor="rm")
            put(fr, txt("PROGRESO EN 3ª B", "bebas", 38, GRAY), LX, 366, a=a, anchor="lm")
            if p >= 1: popin(fr, t, tc + 1.6, a1, pill("SUBES A 3ª A", GREEN, WHITE, 38, 22, 58, "plus"), LX + bw, 480, anchor="rm")
        tu = T("nivel", "sube", d=-.1)
        tf = T("nivel", "fuerte", d=-.15)
        popin(fr, t, tf, a1, result_table(), LX + 350, 690)

    # --- 4 RESULTADO
    if S0["result"] - .1 <= t < S1["result"] + .3:
        a0, a1 = S0["result"], S1["result"] + .3
        header(fr, t, a0, a1, 4, "RESULTADOS SIN LÍOS")
        popin(fr, t, S0["result"] + .25, a1, scoreboard(), LX + 350, 420)
        tc = T("result", "confirma", d=-.05)
        if t >= tc:
            p = back((t - tc) / .35); a = env(t, tc, a1, .1)
            put(fr, stamp(), LX + 350, 690, sc=1.6 - .6 * p, a=a)

    # --- 5 TORNEOS, CARTERA
    if S0["torneos"] - .1 <= t < S1["torneos"] + .3:
        a0, a1 = S0["torneos"], S1["torneos"] + .3
        header(fr, t, a0, a1, 5, "TORNEOS Y CARTERA")
        for k, (w, ic, ti, sub) in enumerate([("torneos", "trophy", "TORNEOS", "Inscripción en pareja, se cobra del saldo"),
                                              ("saldo", "wallet", "SALDO Y BONOS", "Bonos más baratos que pagar suelto"),
                                              ("puntos", "gift", "PUNTOS = PREMIOS", "Overgrip, saldo, partidos gratis")]):
            tw = T("torneos", w, d=-.1)
            if w == "torneos": tw = S0["torneos"] + .1
            step(fr, t, tw, a1, 310 + k * 175, ic, ti, sub)

    # --- 6 CLUB
    if S0["club"] - .1 <= t < S1["club"] + .3:
        a0, a1 = S0["club"], S1["club"] + .3
        header(fr, t, a0, a1, 6, "PANEL DEL CLUB")
        items = [("recargas", "RECARGAS EN RECEPCIÓN"), ("resultados", "RESULTADOS POR REVISAR"), ("premios", "PREMIOS POR ENTREGAR"),
                 ("niveles", "NIVELES Y PERMISOS"), ("torneos", "TORNEOS EN UN MINUTO")]
        for k, (w, s) in enumerate(items):
            tw = T("club", w, d=-.1)
            step(fr, t, tw, a1, 270 + k * 108, "check", s, None)
        tp = T("club", "panel", d=-.1)
        popin(fr, t, tp, a1, pill("SOLO PARA EL PERSONAL", GOLD, NAVY, 40, 24, 62, "shield"), LX, 840, anchor="lm")

    # --- teléfonos laterales (multi-club)
    if S0["multi"] <= t < S1["multi"] + .4:
        tv = T("multi", "varios", d=-.1); a = env(t, tv, S1["multi"] + .4, .3, .4)
        if a > 0:
            p = ease((t - tv) / .6)
            for im, sgn in ((CLUB_B, -1), (CLUB_C, 1)):
                put(fr, PSHADOW, W / 2 + sgn * 330 * p, 545, sc=.68, a=a * .8)
                put(fr, im, W / 2 + sgn * 330 * p, 540, sc=.68, a=a)

    # --- teléfono principal
    pose = phone_pose(t)
    if pose:
        x, y, sc, a = pose
        put(fr, PSHADOW, x, y + 8, sc=sc, a=a * .9)
        put(fr, phone_img(screen_at(t)), x, y, sc=sc, a=a)

    # --- etiquetas multi
    if S0["multi"] <= t < S1["multi"] + .4:
        a1 = S1["multi"] + .4
        for k, (w, s, ic) in enumerate([("movil", "DESDE EL MÓVIL", "phone"), ("instala", "SE INSTALA COMO APP", "plus"), ("varios", "MULTI-CLUB · TU MARCA", "clubs")]):
            tw = T("multi", w, d=-.1)
            popin(fr, t, tw, a1, pill(s, GOLD if k == 2 else NAVYL, NAVY if k == 2 else WHITE, 40, 22, 64, ic), [250, 720, 1190][k], 72)

    # --- CTA
    if t >= S0["cta"] - .1:
        t0 = S0["cta"]
        put(fr, LOGO_MID, W / 2, 300, sc=.6 + .4 * back((t - t0) / .5), a=env(t, t0, None, .3))
        put(fr, txt_line("¿QUIERES *XZEN *PÁDEL EN TU CLUB?", "bebas", 92, WHITE, GOLDL), W / 2, 450, a=env(t, t0 + .3, None, .3),
            sc=.8 + .2 * back((t - t0 - .3) / .4))
        tw = T("cta", "escribenos", d=-.1)
        if t >= tw:
            p = back((t - tw) / .45); btn = cta_btn()
            ring = ((t - tw) % 1.2) / 1.2
            put(fr, rrect(btn.width + 40, btn.height + 40, (btn.height + 40) // 2, (0, 0, 0, 0), GOLDL + (255,), 4),
                W / 2, 640, sc=1 + .12 * ring, a=(1 - ring) * .8 * env(t, tw + .3, None))
            put(fr, btn, W / 2, 640, sc=(.6 + .4 * p) * (1 + .03 * math.sin((t - tw) * 6)), a=env(t, tw, None, .15))
            put(fr, txt("Y te contamos cómo tenerla en tu club", "Medium", 30, GRAY), W / 2, 760, a=env(t, tw + .5, None, .3))

    subtitles(fr, t)
    # fundido final
    if t > END - .5: fr.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * ease((t - END + .5) / .5)))))
    return fr

# piezas adicionales
@lru_cache(None)
def money_card(ic, ti, sub):
    w, h = 700, 124; im = rrect(w, h, 22, NAVYL + (240,)).copy()
    im.alpha_composite(icon(ic, 34), (22, h // 2 - 34))
    im.alpha_composite(txt(ti, "bebas", 56, WHITE), (110, 18)); im.alpha_composite(txt(sub, "Medium", 24, GRAY), (111, 80))
    return im
@lru_cache(None)
def avatar(ini):
    im = circle(46, NAVYL + (255,), GOLD + (255,), 4).copy(); s = txt(ini, "Bold", 30, WHITE)
    im.alpha_composite(s, (46 - s.width // 2, 46 - s.height // 2)); return im
@lru_cache(None)
def lvl_chip(s, cur):
    im = rrect(68, 68, 14, (GOLD + (255,)) if cur else (NAVYL + (255,)), (GOLDL + (255,)) if cur else None, 3 if cur else 0).copy()
    tt = txt(s, "bebas", 38, NAVY if cur else WHITE); im.alpha_composite(tt, (34 - tt.width // 2, 34 - tt.height // 2 + 1)); return im
@lru_cache(None)
def result_table():
    w, h = 700, 250; im = rrect(w, h, 22, NAVYL + (240,)).copy(); d = ImageDraw.Draw(im)
    f = font("SemiBold", 25); fb = font("bebas", 44)
    d.text((26, 20), "RESULTADO", font=font("bebas", 34), fill=GRAY); d.text((420, 20), "GANAS", font=font("bebas", 34), fill=GRAY)
    d.text((540, 20), "PIERDES", font=font("bebas", 34), fill=GRAY)
    rows = [("2-0 con mucha diferencia", "+15 %", "−8 %"), ("2-1 en el tercer set", "+7 %", "−3 %"), ("Rival más fuerte", "× 1,3", "× 0,7")]
    for k, (a, b, c) in enumerate(rows):
        y = 72 + k * 58
        if k == 2: d.rounded_rectangle([12, y - 8, w - 12, y + 48], 12, fill=GOLD + (60,), outline=GOLD, width=2)
        d.text((26, y + 4), a, font=f, fill=WHITE); d.text((420, y), b, font=fb, fill=(90, 220, 140)); d.text((540, y), c, font=fb, fill=(240, 120, 120))
    return im
@lru_cache(None)
def scoreboard():
    w, h = 700, 270; im = rrect(w, h, 22, (255, 255, 255, 250)).copy(); d = ImageDraw.Draw(im)
    d.text((28, 22), "PISTA 1 · DOM 8 NOV", font=font("bebas", 36), fill=(110, 118, 135))
    for k, s in enumerate(["SET 1", "SET 2"]): d.text((430 + k * 110, 22), s, font=font("bebas", 34), fill=(110, 118, 135))
    for r, (name, sc, win) in enumerate([("Jugador Demo / Regina", ("6", "6"), True), ("Mariana / Jorge", ("3", "4"), False)]):
        y = 82 + r * 88
        d.text((28, y + 18), name, font=font("SemiBold", 28), fill=NAVY)
        for k, v in enumerate(sc):
            d.rounded_rectangle([420 + k * 110, y, 500 + k * 110, y + 74], 12, fill=NAVY if win else (236, 238, 243))
            ff = font("bebas", 60); vw = ff.getlength(v)
            d.text((460 + k * 110 - vw / 2, y + 8), v, font=ff, fill=GOLDL if win else NAVY)
    return im
@lru_cache(None)
def stamp():
    im = pill("CONFIRMADO POR LA OTRA PAREJA", GREEN, WHITE, 42, 26, 70, "check"); return im.rotate(-4, Image.BICUBIC, expand=True)
@lru_cache(None)
def cta_btn():
    a = txt("ESCRÍBENOS", "bebas", 64, NAVY); b = txt("PÁDEL", "bebas", 96, NAVY)
    w = a.width + b.width + 110; h = 130; im = rrect(w, h, 65, GOLDL + (255,)).copy()
    im.alpha_composite(a, (44, h // 2 - a.height // 2 + 4)); im.alpha_composite(b, (44 + a.width + 22, h // 2 - b.height // 2 + 2))
    return im

# ---------------------------------------------------------------- salida
if __name__ == "__main__":
    ti = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
    tf = float(sys.argv[7]) if len(sys.argv) > 7 else END
    if OUT.endswith(".png"):
        for k, tt in enumerate(np.arange(ti, tf, (tf - ti) / 12 if tf > ti else 1)[:12]):
            frame(float(tt)).convert("RGB").save(OUT.replace(".png", f"_{k:02d}.png"))
        sys.exit()
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-qp", "0", "-preset", "ultrafast", OUT], stdin=subprocess.PIPE)
    n = int(round((tf - ti) * FPS))
    for i in range(n):
        p.stdin.write(frame(ti + i / FPS).convert("RGB").tobytes())
        if i % 300 == 0: print(i, "/", n, flush=True)
    p.stdin.close(); p.wait(); print("END", END)
    ev = sorted(EVENTS); pops = [e for i, e in enumerate(ev) if i == 0 or e - ev[i - 1] > .12]
    json.dump({"end": END, "pops": pops, "whoosh": [PHONE_IN] + [S0[b] for b in ["reserva", "pago", "nivel", "result", "torneos", "club", "multi", "cta"]]},
              open(OUT + ".events.json", "w"))
