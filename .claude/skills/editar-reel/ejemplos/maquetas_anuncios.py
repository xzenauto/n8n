"""Maquetas de anuncios (agencia ficticia) y clips animados sobre el plano desenfocado."""
import sys, os, json, math, subprocess, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plan import VISUALS
FONT = "/home/user/n8n/.claude/skills/editar-reel/fonts/Inter.ttf"
def F(px, w=500):
    f = ImageFont.truetype(FONT, px); f.set_variation_by_axes([min(32, px * 0.6), w]); return f
CW, CH = 600, 960
INK, GREY, LINE, BLUE = (20, 22, 26), (101, 103, 107), (228, 230, 235), (24, 119, 242)
def base_card():
    im = Image.new("RGBA", (CW, CH), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, CW - 1, CH - 1), 28, fill=(255, 255, 255, 255)); return im, d
def header(im, d, y=24):
    d.ellipse((24, y, 76, y + 52), fill=(0, 150, 170))
    d.text((50, y + 27), "VH", font=F(20, 800), fill="white", anchor="mm")
    d.text((90, y + 4), "Viajes Horizonte", font=F(23, 700), fill=INK)
    d.text((90, y + 32), "Publicidad", font=F(18, 400), fill=GREY)
    for k in range(3): d.ellipse((CW - 52 + k * 10, y + 22, CW - 46 + k * 10, y + 28), fill=GREY)
    return y + 70
def wrap(d, text, font, maxw):
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw or not cur: cur = t
        else: out.append(cur); cur = w
    return out + [cur]
def photo(path, w, h):
    p = Image.open(path).convert("RGB"); r = max(w / p.width, h / p.height)
    p = p.resize((round(p.width * r), round(p.height * r)), Image.LANCZOS)
    x, y = (p.width - w) // 2, (p.height - h) // 2
    return p.crop((x, y, x + w, y + h))
def ad(path, copy, title, price, cta, out):
    im, d = base_card(); y = header(im, d)
    for ln in wrap(d, copy, F(21, 400), CW - 48): d.text((24, y), ln, font=F(21, 400), fill=INK); y += 29
    y += 10; ph = photo(path, CW, 560); im.paste(ph, (0, y)); y += 560
    yb = y
    d.rectangle((0, y, CW, y + 118), fill=(242, 243, 245))
    d.text((24, y + 14), "VIAJESHORIZONTE.MX", font=F(15, 500), fill=GREY)
    d.text((24, y + 38), title, font=F(24, 700), fill=INK)
    d.text((24, y + 72), price, font=F(20, 500), fill=GREY)
    bw = d.textlength(cta, font=F(19, 700)) + 36
    d.rounded_rectangle((CW - 24 - bw, y + 34, CW - 24, y + 84), 10, fill=(228, 230, 235))
    d.text((CW - 24 - bw / 2, y + 59), cta, font=F(19, 700), fill=INK, anchor="mm")
    y += 136
    d.text((24, y), "1,2 mil Me gusta  ·  248 comentarios  ·  96 compartidos", font=F(17, 400), fill=GREY)
    d.line((24, y + 40, CW - 24, y + 40), fill=LINE, width=2)
    for k, t in enumerate(("Me gusta", "Comentar", "Enviar")):
        d.text((CW / 6 + k * CW / 3, y + 66), t, font=F(19, 600), fill=GREY, anchor="mm")
    im.save(out); return (CW - 24 - bw / 2, yb + 59)   # centro del botón (para el "clic")
def resultados(out):
    im, d = base_card(); y = header(im, d)
    d.text((24, y + 4), "Campaña · Paquetes Cancún", font=F(26, 800), fill=INK)
    d.text((24, y + 42), "Optimización: Compras (API de Conversiones)", font=F(18, 500), fill=GREY)
    y += 96
    rows = [("Compras", "12", "31", "+158 %", (36, 160, 90)), ("Costo por compra", "$412", "$268", "−35 %", (36, 160, 90)),
            ("Clics que solo piden info", "71 %", "38 %", "−33 pts", (36, 160, 90))]
    for name, a, b, delta, col in rows:
        d.rounded_rectangle((24, y, CW - 24, y + 120), 16, fill=(246, 247, 249))
        d.text((44, y + 18), name, font=F(20, 600), fill=GREY)
        d.text((44, y + 52), a, font=F(34, 700), fill=(160, 163, 168)); aw = d.textlength(a, font=F(34, 700))
        d.text((60 + aw, y + 58), "→", font=F(28, 600), fill=GREY)
        d.text((104 + aw, y + 52), b, font=F(34, 800), fill=INK)
        dw = d.textlength(delta, font=F(22, 800)) + 28
        light = tuple(int(255 - (255 - c) * 0.16) for c in col)          # color sólido (sin transparencia)
        d.rounded_rectangle((CW - 44 - dw, y + 58, CW - 44, y + 98), 20, fill=light)
        d.text((CW - 44 - dw / 2, y + 78), delta, font=F(22, 800), fill=col, anchor="mm")
        y += 136
    # mini gráfico de compras por semana (sube tras activar la API)
    gx0, gy0, gx1, gy1 = 44, y + 20, CW - 44, y + 220
    vals = [3, 4, 3, 5, 4, 8, 11, 13, 16, 19]
    d.line((gx0, gy1, gx1, gy1), fill=LINE, width=2)
    pts = [(gx0 + i * (gx1 - gx0) / (len(vals) - 1), gy1 - v / 20 * (gy1 - gy0)) for i, v in enumerate(vals)]
    xa = pts[4][0] + (pts[5][0] - pts[4][0]) / 2
    d.line((xa, gy0, xa, gy1), fill=(180, 184, 190), width=2)
    d.text((xa + 8, gy0), "API activada", font=F(16, 600), fill=GREY)
    d.line(pts, fill=BLUE, width=5, joint="curve")
    for p in pts: d.ellipse((p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5), fill=BLUE)
    d.text((44, gy1 + 14), "Compras por semana", font=F(17, 500), fill=GREY)
    d.rounded_rectangle((CW - 150, 30, CW - 24, 64), 17, fill=(255, 237, 200))
    d.text((CW - 87, 47), "EJEMPLO", font=F(16, 800), fill=(170, 110, 0), anchor="mm")
    im.save(out)
btn_eu = ad("foto_europa.png", "¿Soñando con Europa? Te armamos el viaje completo: vuelo, hotel y traslados. Escríbenos y cotiza hoy.",
            "Europa 12 días · vuelo + hotel", "Desde $24,999 MXN", "Enviar mensaje", "ad_europa.png")
btn_cn = ad("foto_avion.png", "Tu próximo viaje empieza aquí. Paquetes todo incluido con meses sin intereses.",
            "Cancún todo incluido", "4 noches desde $8,999 MXN", "Más información", "ad_cancun.png")
resultados("ad_resultados.png")
json.dump({"ad_europa": btn_eu, "ad_cancun": btn_cn}, open("botones.json", "w"))
# ---- clips animados: plano desenfocado + tarjeta que entra desde abajo (izquierda) ----
W, H, FPS = 1920, 1080, 30
def shadowed(card):
    pad = 40; sh = Image.new("RGBA", (card.width + 2 * pad, card.height + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 12, pad + card.width, pad + card.height + 12), 28, fill=(0, 0, 0, 140))
    sh = sh.filter(ImageFilter.GaussianBlur(18)); sh.alpha_composite(card, (pad, pad)); return sh, pad
for a, b, kind, name, off in VISUALS:
    if kind != "card": continue
    card = Image.open(f"{name}.png"); sc = 0.98 * H / card.height * 0.98
    card = card.resize((round(card.width * sc), round(card.height * sc)), Image.LANCZOS)
    cimg, pad = shadowed(card)
    cx, cy = int(W * 0.30), H // 2
    n = round((b - a) * FPS)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-i", "aroll.mkv", "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", "-pix_fmt", "yuv420p", f"clip_{name}.mkv"], stdin=subprocess.PIPE)
    btn = json.load(open("botones.json")).get(name)
    for i in range(n):
        buf = dec.stdout.read(W * H * 3)
        if len(buf) < W * H * 3: buf = last
        last = buf
        bg = cv2.GaussianBlur(np.frombuffer(buf, np.uint8).reshape(H, W, 3), (0, 0), 28)
        bg = (bg.astype(np.float32) * 0.55).astype(np.uint8)
        fr = Image.fromarray(bg).convert("RGBA"); t = i / FPS
        p = min(1, t / 0.4); e = 1 - (1 - p) ** 3                         # entrada suave
        lay = cimg.copy()
        if e < 1: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * e)))
        x = cx - cimg.width // 2; y = cy - cimg.height // 2 + int((1 - e) * 90)
        fr.alpha_composite(lay, (x, max(0, y)) if y >= 0 else (x, 0))
        if name == "ad_cancun" and btn and 1.2 <= t <= 2.2:              # "clic" en el botón
            k = (t - 1.2) / 1.0; bx = x + pad + btn[0] * sc; by = y + pad + btn[1] * sc
            dr = ImageDraw.Draw(fr); r = 18 + 60 * k
            dr.ellipse((bx - r, by - r, bx + r, by + r), outline=(255, 255, 255, int(255 * (1 - k))), width=6)
            dr.ellipse((bx - 16, by - 16, bx + 16, by + 16), fill=(255, 255, 255, int(200 * (1 - k * 0.6))))
        enc.stdin.write(fr.convert("RGB").tobytes())
    enc.stdin.close(); enc.wait(); dec.wait()
    print("clip", name, n, "fotogramas")
