"""Texto POV en la franja negra superior (1080x1920, vídeo 16:9 centrado en y=656..1264)."""
from PIL import Image, ImageDraw, ImageFont
F = "/home/user/n8n/.claude/skills/editar-reel/fonts/BebasNeue-Regular.ttf"
W, H, TOP = 1080, 1920, 656
LINES = [[("POV:", True), ("EMPIEZAS", False), ("A", False), ("CENTRARTE", False)],
         [("EN", False), ("TU", True), ("NEGOCIO", True), ("Y", False), ("LA", False), ("VIDA", False)],
         [("SUENA", False), ("ASÍ...", False)]]
f = ImageFont.truetype(F, 96); gap = 24; lh = 104
im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
y = TOP - 56 - lh * len(LINES)
for line in LINES:
    ws = [f.getbbox(t)[2] - f.getbbox(t)[0] for t, _ in line]
    x = (W - sum(ws) - gap * (len(ws) - 1)) / 2
    for (t, hl), wd in zip(line, ws):
        d.text((x - f.getbbox(t)[0], y), t, font=f, fill=(255, 210, 60, 255) if hl else (255, 255, 255, 255)); x += wd + gap
    y += lh
im.save("titulo.png")
