"""Recursos gráficos animados sobre el vídeo (tarjetas que ilustran lo que se dice).
Uso: recursos.py entrada.mkv timeline.json salida.mkv
timeline.json = {"col_x": 0.20, "col_y": 0.40, "scale": 1.0, "gradient": true, "items": [ {...}, ... ]}
Cada item: {"type": ..., "t0": seg, "t1": seg, ...}. Tipos:
  chat      title, msgs: [[t, texto, hora], ...]              mensajes entrantes que van llegando
  comments  title, msgs: [[t, nombre, texto], ...]            comentarios de una publicación
  timer     title, sub, to_min (minutos), dur                  contador "sin responder" en rojo
  alert     text, sub                                          ✕ rojo (cliente perdido)
  badge     big, sub, color ("yellow"|"green"|"red"), icon ("clock"|"up"|None)
  checklist title, items: [[t, texto], ...], thumbs (bool)    lista que se va marcando
  flow      title, steps: [[t, texto], ...]                    pasos con flecha; el último en verde
  bars      title, rows: [[etiqueta, valor], ...], tag         barras que crecen (tag "EJEMPLO")
  cta       pre, word, post                                    llamada a la acción con palabra clave
Las tarjetas entran con un pop suave (0,4 s) y salen con fundido (0,25 s)."""
import json, math, subprocess, sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BEBAS = os.path.join(HERE, "fonts", "BebasNeue-Regular.ttf")
INTER = os.path.join(HERE, "fonts", "Inter.ttf")
SS = 2                                     # supermuestreo para bordes suaves
CARD_W = 440
YELLOW, GREEN, RED = (255, 210, 60), (52, 199, 110), (235, 77, 70)
WHITE, GREY, DARK = (255, 255, 255), (165, 168, 176), (20, 20, 24)
_fc = {}


def font(size, weight=500, bebas=False):
    k = (size, weight, bebas)
    if k in _fc: return _fc[k]
    f = ImageFont.truetype(BEBAS if bebas else INTER, int(size * SS))
    if not bebas:
        try:
            vals = []
            for ax in f.get_variation_axes():
                nm = ax["name"].decode() if isinstance(ax["name"], bytes) else ax["name"]
                v = weight if nm == "Weight" else (min(32, size) if "Optical" in nm else ax["default"])
                vals.append(min(ax["maximum"], max(ax["minimum"], v)))
            f.set_variation_by_axes(vals)
        except Exception:
            pass
    _fc[k] = f
    return f


def ease_out_back(p):
    c1 = 1.4; c3 = c1 + 1
    return 1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2


def ease(p):
    p = min(1, max(0, p)); return p * p * (3 - 2 * p)


def S(v): return int(round(v * SS))


def text_w(d, txt, f): return d.textlength(txt, font=f) / SS


def wrap(d, txt, f, maxw):
    words, lines, cur = txt.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if cur and text_w(d, t, f) > maxw: lines.append(cur); cur = w
        else: cur = t
    if cur: lines.append(cur)
    return lines


def base(h):
    im = Image.new("RGBA", (S(CARD_W), S(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, S(CARD_W) - 1, S(h) - 1], S(26), fill=(18, 18, 22, 236), outline=(255, 255, 255, 34), width=S(1.5))
    return im, d


def header(d, title, y=26, dot=None):
    f = font(21, 600)
    x = 30
    if dot is not None:
        d.ellipse([S(x), S(y + 4), S(x + 14), S(y + 18)], fill=dot); x += 24
    d.text((S(x), S(y)), title.upper(), font=f, fill=GREY)
    return y + 44


def icon_check(d, cx, cy, r, col=GREEN, p=1.0):
    d.ellipse([S(cx - r), S(cy - r), S(cx + r), S(cy + r)], fill=col)
    if p > 0:
        pts = [(cx - r * 0.45, cy + r * 0.02), (cx - r * 0.12, cy + r * 0.35), (cx + r * 0.48, cy - r * 0.32)]
        d.line([(S(x), S(y)) for x, y in pts], fill=WHITE, width=S(max(2, r * 0.22)), joint="curve")


def icon_x(d, cx, cy, r, col=RED):
    d.ellipse([S(cx - r), S(cy - r), S(cx + r), S(cy + r)], fill=col)
    k = r * 0.38
    for a, b in (((cx - k, cy - k), (cx + k, cy + k)), ((cx - k, cy + k), (cx + k, cy - k))):
        d.line([(S(a[0]), S(a[1])), (S(b[0]), S(b[1]))], fill=WHITE, width=S(r * 0.2))


def icon_clock(d, cx, cy, r, col=RED, ang=0.0):
    d.ellipse([S(cx - r), S(cy - r), S(cx + r), S(cy + r)], outline=col, width=S(r * 0.16))
    d.line([(S(cx), S(cy)), (S(cx), S(cy - r * 0.55))], fill=col, width=S(r * 0.14))
    d.line([(S(cx), S(cy)), (S(cx + r * 0.6 * math.sin(ang)), S(cy - r * 0.6 * math.cos(ang)))], fill=col, width=S(r * 0.12))


def icon_up(d, cx, cy, r, col=GREEN):
    d.ellipse([S(cx - r), S(cy - r), S(cx + r), S(cy + r)], fill=col)
    k = r * 0.45
    d.polygon([(S(cx), S(cy - k)), (S(cx + k), S(cy + k * 0.2)), (S(cx - k), S(cy + k * 0.2))], fill=WHITE)
    d.rectangle([S(cx - k * 0.32), S(cy), S(cx + k * 0.32), S(cy + k)], fill=WHITE)


def icon_chat(d, cx, cy, r, col=WHITE, bg=GREEN):
    d.ellipse([S(cx - r), S(cy - r), S(cx + r), S(cy + r)], fill=col)
    d.polygon([(S(cx - r * 0.75), S(cy + r * 0.45)), (S(cx - r * 1.05), S(cy + r * 1.05)), (S(cx - r * 0.2), S(cy + r * 0.85))], fill=col)
    for k in (-0.42, 0, 0.42):
        d.ellipse([S(cx + k * r - r * 0.11), S(cy - r * 0.11), S(cx + k * r + r * 0.11), S(cy + r * 0.11)], fill=bg)


def pop(p):  # escala de aparición de un elemento interno
    return 0.0 if p <= 0 else min(1.0, ease_out_back(min(1, p / 0.3)))


def paste_scaled(im, el, x, y, sc, alpha=1.0):
    """Pega `el` (RGBA, ya a escala SS) centrado en (x+w/2, y+h/2) con escala sc."""
    if sc <= 0.01 or alpha <= 0.01: return
    w, h = el.size
    e = el.resize((max(1, int(w * sc)), max(1, int(h * sc))), Image.LANCZOS) if abs(sc - 1) > 0.01 else el
    if alpha < 1:
        a = np.array(e); a[..., 3] = (a[..., 3] * alpha).astype(np.uint8); e = Image.fromarray(a)
    im.alpha_composite(e, (int(S(x) + (w - e.width) / 2), int(S(y) + (h - e.height) / 2)))


# ---------------------------------------------------------------- tipos de tarjeta
def card_chat(it, lt):
    """msgs: [t, texto, hora] o [t, texto, hora, "r"] (burbuja a la derecha = respuesta propia).
    dot: color del punto de la cabecera ("red"|"green"|"grey"); count: contador rojo de mensajes."""
    msgs = it["msgs"]; fb = font(23, 500); ft = font(16, 500)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    blocks = []
    for m in msgs:
        lines = wrap(tmp, m[1], fb, CARD_W - 130)
        blocks.append((lines, m[2], 22 + 30 * len(lines) + 4, len(m) > 3 and m[3] == "r"))
    h = 70 + sum(b[2] + (30 if b[1] else 12) for b in blocks) + 10
    im, d = base(h)
    n = sum(1 for m in msgs if lt >= m[0] - it["t0"])
    dot = {"red": RED, "green": GREEN, "grey": GREY}.get(it.get("dot"), RED if n else GREY)
    title = it.get("title", "Mensajes nuevos")
    y = header(d, title, dot=dot)
    if n and it.get("count", True):
        bx = 30 + text_w(d, title.upper(), font(21, 600)) + 36
        d.ellipse([S(bx), S(24), S(bx + 28), S(52)], fill=RED)
        s = str(n); d.text((S(bx + 14 - text_w(d, s, font(17, 700)) / 2), S(28)), s, font=font(17, 700), fill=WHITE)
    for m, (lines, hora, bh, right) in zip(msgs, blocks):
        p = lt - (m[0] - it["t0"])
        bw = max(text_w(d, l, fb) for l in lines) + 36
        el = Image.new("RGBA", (S(bw + 10), S(bh + 26)), (0, 0, 0, 0)); e = ImageDraw.Draw(el)
        bg, fg = ((34, 120, 84, 255), WHITE) if right else ((236, 236, 240, 255), (25, 25, 30))
        e.rounded_rectangle([0, 0, S(bw), S(bh)], S(18), fill=bg)
        for k, l in enumerate(lines): e.text((S(18), S(12 + 30 * k)), l, font=fb, fill=fg)
        if hora: e.text((S(6), S(bh + 4)), hora, font=ft, fill=GREY)
        paste_scaled(im, el, CARD_W - 30 - bw - 10 if right else 30, y, pop(p), min(1, max(0, p) / 0.15))
        y += bh + (30 if hora else 12)
    return im


def card_comments(it, lt):
    fb = font(21, 500); fn = font(19, 700)
    h = 70 + 78 * len(it["msgs"]) + 10
    im, d = base(h)
    y = header(d, it.get("title", "Comentarios"))
    cols = [(240, 140, 90), (110, 160, 240), (180, 120, 220), (90, 190, 160)]
    for k, (t, name, txt) in enumerate(it["msgs"]):
        p = lt - (t - it["t0"])
        el = Image.new("RGBA", (S(CARD_W - 50), S(70)), (0, 0, 0, 0)); e = ImageDraw.Draw(el)
        e.ellipse([0, S(4), S(44), S(48)], fill=cols[k % 4])
        e.text((S(22 - text_w(e, name[0], font(20, 700)) / 2), S(13)), name[0], font=font(20, 700), fill=WHITE)
        e.rounded_rectangle([S(56), 0, S(56 + max(text_w(e, txt, fb), text_w(e, name, fn)) + 32), S(64)], S(16), fill=(44, 44, 52))
        e.text((S(72), S(7)), name, font=fn, fill=WHITE)
        e.text((S(72), S(33)), txt, font=fb, fill=(225, 225, 230))
        paste_scaled(im, el, 28, y, pop(p), min(1, max(0, p) / 0.15))
        y += 78
    return im


def card_timer(it, lt):
    h = 250
    im, d = base(h)
    header(d, it.get("title", "Sin responder"), dot=RED)
    p = ease(lt / it.get("dur", 1.4))
    m = int(it["to_min"] * p)
    big = f"{m // 60} H {m % 60:02d} MIN" if m >= 60 else f"{m} MIN"
    icon_clock(d, 72, 128, 38, RED, ang=lt * 5)
    d.text((S(130), S(88)), big, font=font(74, bebas=True), fill=RED)
    for k, l in enumerate(wrap(d, it.get("sub", "y el cliente sigue esperando"), font(21, 500), CARD_W - 60)):
        d.text((S(30), S(186 + 28 * k)), l, font=font(21, 500), fill=(220, 220, 226))
    return im


def card_alert(it, lt):
    fb = font(30, 700)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    lines = wrap(tmp, it["text"], fb, CARD_W - 140)
    h = max(150, 60 + 40 * len(lines) + 40)
    im, d = base(h)
    sc = pop(lt - 0.15)
    el = Image.new("RGBA", (S(84), S(84)), (0, 0, 0, 0)); icon_x(ImageDraw.Draw(el), 42, 42, 38)
    paste_scaled(im, el, 22, h / 2 - 42, sc)
    y = h / 2 - (40 * len(lines) + 30) / 2
    for k, l in enumerate(lines): d.text((S(122), S(y + 40 * k)), l, font=fb, fill=WHITE)
    d.text((S(122), S(y + 40 * len(lines) + 2)), it.get("sub", "").upper(), font=font(18, 700), fill=RED)
    return im


def card_badge(it, lt):
    col = {"yellow": YELLOW, "green": GREEN, "red": RED}[it.get("color", "yellow")]
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    size = it.get("size", 150)
    while size > 40 and text_w(tmp, it["big"], font(size, bebas=True)) + (80 if it.get("icon") else 0) > CARD_W - 64:
        size -= 4
    it = dict(it, size=size)
    fbig = font(size, bebas=True)
    subl = wrap(tmp, it.get("sub", ""), font(24, 600), CARD_W - 60) if it.get("sub") else []
    bh = it.get("size", 150) * 0.86
    h = 50 + bh + 30 * len(subl) + 40
    im, d = base(h)
    ic = it.get("icon")
    bw = text_w(d, it["big"], fbig) + (80 if ic else 0)
    x = (CARD_W - bw) / 2
    if ic:
        r = 32
        el = Image.new("RGBA", (S(2 * r + 4), S(2 * r + 4)), (0, 0, 0, 0)); e = ImageDraw.Draw(el)
        {"clock": lambda: icon_clock(e, r + 2, r + 2, r, col, ang=lt * 4), "up": lambda: icon_up(e, r + 2, r + 2, r, col),
         "x": lambda: icon_x(e, r + 2, r + 2, r, col), "check": lambda: icon_check(e, r + 2, r + 2, r, col)}[ic]()
        paste_scaled(im, el, x, 38 + bh / 2 - r, pop(lt - 0.1)); x += 80
    d.text((S(x), S(34)), it["big"], font=fbig, fill=col)
    for k, l in enumerate(subl):
        d.text((S((CARD_W - text_w(d, l, font(24, 600))) / 2), S(44 + bh + 30 * k)), l, font=font(24, 600), fill=WHITE)
    return im


def card_checklist(it, lt):
    fb = font(25, 600)
    rows = it["items"]
    h = 76 + 62 * len(rows) + 14
    im, d = base(h)
    y = header(d, it.get("title", ""))
    thumbs = [(196, 160, 120), (120, 140, 160), (210, 200, 185), (150, 110, 90)]
    for k, (t, txt) in enumerate(rows):
        p = lt - (t - it["t0"])
        el = Image.new("RGBA", (S(CARD_W - 50), S(54)), (0, 0, 0, 0)); e = ImageDraw.Draw(el)
        if it.get("thumbs"):
            e.rounded_rectangle([0, S(2), S(50), S(50)], S(10), fill=thumbs[k % 4])
            e.rounded_rectangle([S(10), S(18), S(40), S(36)], S(5), fill=(255, 255, 255, 120))
        else:
            icon_check(e, 24, 26, 20)
        e.text((S(68), S(9)), txt, font=fb, fill=WHITE)
        paste_scaled(im, el, 28, y, pop(p), min(1, max(0, p) / 0.15))
        y += 62
    return im


def card_flow(it, lt):
    fb = font(24, 600)
    st = it["steps"]
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    L = [wrap(tmp, s[1], fb, CARD_W - 130) for s in st]
    hs = [max(56, 30 * len(l) + 22) for l in L]
    h = 76 + sum(hs) + 34 * (len(st) - 1) + 16
    im, d = base(h)
    y = header(d, it.get("title", ""))
    for k, ((t, _), lines, sh) in enumerate(zip(st, L, hs)):
        p = lt - (t - it["t0"])
        last = k == len(st) - 1
        if k > 0 and p > 0:           # flecha desde el paso anterior
            a = ease(p / 0.3)
            d.line([(S(55), S(y - 34)), (S(55), S(y - 34 + 26 * a))], fill=GREY, width=S(3))
            if a >= 1: d.polygon([(S(47), S(y - 12)), (S(63), S(y - 12)), (S(55), S(y - 2))], fill=GREY)
        el = Image.new("RGBA", (S(CARD_W - 40), S(sh)), (0, 0, 0, 0)); e = ImageDraw.Draw(el)
        col = GREEN if last else (60, 60, 70)
        e.ellipse([S(3), S(sh / 2 - 24), S(51), S(sh / 2 + 24)], fill=col)
        num = str(k + 1); e.text((S(27 - text_w(e, num, font(22, 700)) / 2), S(sh / 2 - 15)), num, font=font(22, 700), fill=WHITE)
        for j, l in enumerate(lines):
            e.text((S(72), S(sh / 2 - 15 * len(lines) + 30 * j - 2)), l, font=fb, fill=GREEN if last else WHITE)
        paste_scaled(im, el, 28, y, pop(p), min(1, max(0, p) / 0.15))
        y += sh + 34
    return im


def card_bars(it, lt):
    rows = it["rows"]; fl = font(21, 600)
    h = 80 + 64 * len(rows) + 16
    im, d = base(h)
    header(d, it.get("title", ""))
    if it.get("tag"):
        tw = text_w(d, it["tag"], font(14, 700)) + 20
        d.rounded_rectangle([S(CARD_W - 30 - tw), S(24), S(CARD_W - 30), S(48)], S(12), fill=(60, 60, 70))
        d.text((S(CARD_W - 20 - tw), S(28)), it["tag"], font=font(14, 700), fill=GREY)
    mx = max(r[1] for r in rows); best = max(range(len(rows)), key=lambda k: rows[k][1])
    y = 80
    for k, (lab, val) in enumerate(rows):
        p = ease((lt - 0.25 - 0.12 * k) / 0.7)
        d.text((S(30), S(y)), lab, font=fl, fill=WHITE)
        bw = (CARD_W - 60 - 70) * val / mx * p
        d.rounded_rectangle([S(30), S(y + 30), S(CARD_W - 100), S(y + 50)], S(10), fill=(44, 44, 52))
        if bw > 4: d.rounded_rectangle([S(30), S(y + 30), S(30 + bw), S(y + 50)], S(10), fill=YELLOW if k == best else (150, 150, 160))
        v = f"{int(round(val * p))}{it.get('unit', '')}"
        d.text((S(CARD_W - 88), S(y + 24)), v, font=font(24, 700), fill=YELLOW if k == best else WHITE)
        y += 64
    return im


def card_cta(it, lt):
    h = 300
    im, d = base(h)
    f1 = font(25, 600)
    d.text((S((CARD_W - text_w(d, it["pre"], f1)) / 2), S(30)), it["pre"], font=f1, fill=WHITE)
    sz = 84
    while text_w(d, it["word"], font(sz, bebas=True)) + 120 > CARD_W - 50: sz -= 4
    fw = font(sz, bebas=True); ww = text_w(d, it["word"], fw)
    pw = ww + 120; px = (CARD_W - pw) / 2; py = 82
    pulse = 0.5 + 0.5 * math.sin(lt * 5)
    if lt > 0.4:                                  # anillo que late alrededor del botón
        g = 4 + 8 * pulse
        d.rounded_rectangle([S(px - g), S(py - g), S(px + pw + g), S(py + 104 + g)], S(52 + g), outline=GREEN + (int(90 * (1 - pulse)) + 40,), width=S(3))
    d.rounded_rectangle([S(px), S(py), S(px + pw), S(py + 104)], S(52), fill=GREEN)
    icon_chat(d, px + 50, py + 50, 22, WHITE, GREEN)
    d.text((S(px + 88), S(py + 14 + (84 - sz) * 0.45)), it["word"], font=fw, fill=WHITE)
    f3 = font(25, 600)
    d.text((S((CARD_W - text_w(d, it["post"], f3)) / 2), S(212)), it["post"], font=f3, fill=(220, 220, 226))
    return im


KIND = {"chat": card_chat, "comments": card_comments, "timer": card_timer, "alert": card_alert, "badge": card_badge,
        "checklist": card_checklist, "flow": card_flow, "bars": card_bars, "cta": card_cta}
ANIMATED = {"timer", "bars", "cta", "flow", "chat", "comments", "checklist", "alert", "badge"}


def main():
    inp, tl_path, out = sys.argv[1:4]
    TL = json.load(open(tl_path))
    o = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                            "stream=width,height:format=duration", "-of", "json", inp]))
    W, H = o["streams"][0]["width"], o["streams"][0]["height"]; dur = float(o["format"]["duration"]); fps = 30
    cx, cy = TL.get("col_x", 0.20) * W, TL.get("col_y", 0.40) * H
    K = TL.get("scale", 1.0) * H / 1080          # tamaño de las tarjetas
    grad = np.zeros((H, W, 4), np.uint8)
    if TL.get("gradient", True):
        y = np.arange(H) / H; a = np.clip((y - 0.60) / 0.18, 0, 1); a = a * a * (3 - 2 * a) * 0.6
        grad[..., 3] = (a * 255).astype(np.uint8)[:, None]
    gimg = Image.fromarray(grad, "RGBA")
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-i", inp, "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                           "-r", str(fps), "-i", "-", "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]",
                           "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", "-c:a", "copy", out],
                          stdin=subprocess.PIPE)
    last_key, last = None, None
    for i in range(math.ceil(dur * fps)):
        t = i / fps
        act = [it for it in TL["items"] if it["t0"] <= t < it["t1"]]
        if not act:
            key = "g"
        else:
            key = tuple((id(it), round(t, 3) if (it["type"] in ("cta", "timer") or t - it["t0"] < 4.0 or t > it["t1"] - 0.3) else "s") for it in act)
        if key != last_key:
            canvas = gimg.copy()
            for it in act:
                lt = t - it["t0"]
                card = KIND[it["type"]](it, lt)
                pin = min(1, lt / 0.4); pout = min(1, (it["t1"] - t) / 0.25)
                sc = 0.9 + 0.1 * ease_out_back(pin) if pin < 1 else 1.0
                al = min(ease(pin * 1.6), ease(pout))
                dy = 26 * (1 - ease(pin)) - 10 * (1 - ease(pout))
                c = card.resize((int(card.width / SS * sc * K), int(card.height / SS * sc * K)), Image.LANCZOS)
                if al < 1:
                    arr = np.array(c); arr[..., 3] = (arr[..., 3] * al).astype(np.uint8); c = Image.fromarray(arr)
                x = it.get("x", cx / W) * W - c.width / 2; y = it.get("y", cy / H) * H - c.height / 2 + dy
                canvas.alpha_composite(c, (int(x), int(y)))
            last = canvas.tobytes(); last_key = key
        ff.stdin.write(last)
    ff.stdin.close(); ff.wait(); print("recursos:", out)


if __name__ == "__main__":
    main()
