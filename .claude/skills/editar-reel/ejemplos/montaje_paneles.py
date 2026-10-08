import subprocess, json, sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
from plan import VISUALS
TM = open("tm_best.txt").read().split(",eq=")[0]
SRC = {"reporte_meta_ganados": "../broll_in/reporte_meta_ganados.mov", "leads_ganados": "../broll_in/leads_ganados.mov",
       "chat_viajes": "broll/chat_viajes.mov"}
def sat(path, t, vf):
    o = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1", "-vf", (vf + "," if vf else "") + "scale=480:270",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.array(Image.frombytes("RGB", (480, 270), o).convert("HSV"))[..., 1].mean()
main = np.mean([sat("aroll.mkv", t, "") for t in (1, 6, 11, 14, 31)])
FPS = 30; fr = lambda t: round(t * FPS)
inputs, parts, k, cur = ["-i", "aroll.mkv"], [], 1, 0
for a, b, kind, name, off in VISUALS:
    A, B = fr(a), fr(b)
    if A > cur: parts.append(f"[0:v]trim=start_frame={cur}:end_frame={A},setpts=PTS-STARTPTS,format=yuv420p[p{len(parts)}]")
    if kind == "card":
        inputs += ["-i", f"clip_{name}.mkv"]; chain = f"[{k}:v]format=yuv420p,trim=end_frame={B-A},setpts=PTS-STARTPTS"
    else:
        inputs += ["-ss", str(off), "-i", SRC[name]]
        f = min(1.0, max(0.65, main / sat(SRC[name], off + 0.5, TM))); eq = f",eq=saturation={f:.2f}" if f < 0.99 else ""
        print(name, "saturación ×", round(f, 2))
        if kind == "h":
            chain = f"[{k}:v]{TM}{eq},scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,fps=30,format=yuv420p,trim=end_frame={B-A},setpts=PTS-STARTPTS"
        else:   # vertical: clip a la izquierda (centro en 30 % del ancho) sobre copia desenfocada
            chain = (f"[{k}:v]{TM}{eq},fps=30,split[f{k}][g{k}];"
                     f"[g{k}]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,gblur=sigma=40,eq=brightness=-0.15[bg{k}];"
                     f"[f{k}]scale=-2:1000:flags=lanczos[fg{k}];"
                     f"[bg{k}][fg{k}]overlay=x=1920*0.30-w/2:y=(H-h)/2,format=yuv420p,trim=end_frame={B-A},setpts=PTS-STARTPTS")
    parts.append(chain + f"[p{len(parts)}]"); k += 1; cur = B
parts.append(f"[0:v]trim=start_frame={cur},setpts=PTS-STARTPTS,format=yuv420p[p{len(parts)}]")
n = len(parts)
graph = ";".join(parts) + ";" + "".join(f"[p{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]"
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[v]", "-map", "0:a",
                "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", "-c:a", "copy", "montado.mkv"], check=True)
print("montado ok")
