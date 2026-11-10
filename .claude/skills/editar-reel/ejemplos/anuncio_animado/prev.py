"""Hoja de fotogramas sin renderizar el vídeo entero.
Uso: prev.py guion.json tiempos.json words.json dir_capturas x t1,t2,... hoja.png"""
import sys, os, runpy
ARGS = list(sys.argv)
sys.argv = ["anim.py"] + ARGS[1:6] + ["x.mkv"]
g = runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "anim.py"), run_name="lib")
from PIL import Image
ts = [float(x) for x in ARGS[6].split(",")]
ims = [g["frame"](t).convert("RGB").resize((480, 360)) for t in ts]
cols = 4; sheet = Image.new("RGB", (480 * cols, 360 * ((len(ims) + cols - 1) // cols)))
for k, im in enumerate(ims): sheet.paste(im, ((k % cols) * 480, (k // cols) * 360))
sheet.save(ARGS[7]); print("END", g["END"])
