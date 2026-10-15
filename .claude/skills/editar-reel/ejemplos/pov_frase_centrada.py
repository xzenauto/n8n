"""Frase centrada en pantalla (1080x1920) con sombra suave: línea 1 y línea 2 en PNG separados."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
F = "/home/user/n8n/.claude/skills/editar-reel/fonts/BebasNeue-Regular.ttf"
W, H = 1080, 1920
LINES = [[("LA", False), ("DISCIPLINA", True)], [("GANA", False), ("AL", False), ("TALENTO", True)]]
f = ImageFont.truetype(F, 150); gap = 30; lh = 150
y0 = H / 2 - lh * len(LINES) / 2 - 18
for n, line in enumerate(LINES):
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(txt)
    ws = [f.getbbox(t)[2] - f.getbbox(t)[0] for t, _ in line]
    x = (W - sum(ws) - gap * (len(ws) - 1)) / 2; y = y0 + n * lh
    for (t, hl), wd in zip(line, ws):
        d.text((x - f.getbbox(t)[0], y), t, font=f, fill=(255, 210, 60, 255) if hl else (255, 255, 255, 255)); x += wd + gap
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh.putalpha(txt.getchannel("A").point(lambda v: v * 0.75))
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    out = Image.alpha_composite(sh, txt); out.save(f"linea{n + 1}.png")
