import subprocess, json, numpy as np
from PIL import Image
TM = open("tm_best.txt").read().split(",eq=")[0]
# (inicio, fin en el anuncio, clip, segundo de inicio en el clip)
BROLL = [
    (1.85, 4.40, "chat_viajes", 1.0),       # le va a responder en segundos (pantalla del sistema)
    (22.60, 25.30, "starbucks3", 3.0),      # lo único que van a tener que hacer es cotizar
    (28.40, 30.60, "angustiado_cafe", 1.0), # se acabó el perder tiempo preguntando…
    (37.80, 40.30, "reunion", 6.0),         # lo va a transferir a nuestro agente de ventas
    (42.20, 44.80, "chat_viajes", 6.0),     # base de datos completa
]
def sat(path, t, vf):
    o = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1", "-vf", (vf + "," if vf else "") + "scale=480:270",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.array(Image.frombytes("RGB", (480, 270), o).convert("HSV"))[..., 1].mean()
main = np.mean([sat("src.mp4", t, "") for t in (40, 52, 82, 175, 262, 270)])
print("saturación principal", round(main, 1))
inputs, chains = ["-i", "aroll_v.mkv", "-i", "audio_resumen.wav"], []
last = "0:v"
for k, (a, b, clip, off) in enumerate(BROLL):
    f = min(1.0, max(0.65, main / sat(f"broll/{clip}.mov", off + 0.5, TM)))
    eq = f",eq=saturation={f:.2f}" if f < 0.99 else ""
    print(clip, "saturación ×", round(f, 2))
    inputs += ["-ss", str(off), "-t", f"{b - a:.3f}", "-i", f"broll/{clip}.mov"]
    i = k + 2
    chains.append(
        f"[{i}:v]{TM}{eq},fps=30,split[f{k}][g{k}];"
        f"[g{k}]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,gblur=sigma=40,eq=brightness=-0.12[bg{k}];"
        f"[f{k}]scale=1080:-2:flags=lanczos[fg{k}];"
        f"[bg{k}][fg{k}]overlay=0:(H-h)/2,setpts=PTS-STARTPTS+{a}/TB,format=yuv420p[br{k}];"
        f"[{last}][br{k}]overlay=0:0:eof_action=pass:enable='between(t,{a},{b - 0.001})'[v{k}]")
    last = f"v{k}"
graph = ";".join(chains)
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", f"[{last}]", "-map", "1:a",
                "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", "-c:a", "pcm_s16le", "-shortest", "montado_v.mkv"], check=True)
json.dump([[a, b] for a, b, *_ in BROLL], open("broll_ranges.json", "w"))
