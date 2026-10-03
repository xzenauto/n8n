import subprocess, json
TM = open("tm_best.txt").read().split(",eq=")[0]          # HLG → SDR calibrado (hable, npl 203)
SAT = json.load(open("sat.json"))
NORM = "scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,fps=30,setsar=1,format=yuv420p"
BROLL = [
    (1.83, 2.98, "gym2", 0.5), (4.57, 6.50, "gym", 0.4), (9.27, 10.44, "reunion", 3.0),
    (18.15, 19.62, "terraza", 0.8), (19.62, 20.80, "gym", 2.6), (21.95, 24.10, "gym2", 2.6),
    (25.91, 27.80, "reunion2", 4.0),
]
FPS = 30; fr = lambda t: round(t * FPS)
FACES = json.load(open("aroll_faces.json"))
ZOOM_RATE, ZOOM_MAX = 0.012, 1.10     # zoom lento: +1,2 % por segundo, máximo 10 %
def zoom(a):
    """Zoom lento hacia la cara del plano principal que empieza en `a` (punto fijo = cara)."""
    seg = min(FACES, key=lambda f: abs(f[0] - a))
    px, py = (960, 540) if seg[0] == 0 else (seg[2], seg[3])   # 1er plano: se mueve → centro
    px, py = 2 * px, 2 * py                                   # coordenadas en 4K
    z = f"min({ZOOM_MAX},1+{ZOOM_RATE}*on/{FPS})"
    return (f",scale=3840:2160:flags=lanczos,zoompan=z='{z}':x='{px}*(1-1/zoom)':y='{py}*(1-1/zoom)'"
            f":d=1:s=1920x1080:fps={FPS},format=yuv420p")
inputs, parts, k, cur = ["-i", "main2.mp4"], [], 1, 0
for a, b, clip, off in BROLL:
    A, B = fr(a), fr(b)
    if A > cur:
        parts.append(f"[0:v]trim=start_frame={cur}:end_frame={A},setpts=PTS-STARTPTS,{TM},{NORM}{zoom(cur / FPS)}[p{len(parts)}]")
    inputs += ["-ss", str(off), "-i", f"broll/{clip}.mov"]
    sat = SAT.get(clip, 1.0)
    eq = f",eq=saturation={sat}" if sat < 0.99 else ""
    parts.append(f"[{k}:v]{TM}{eq},{NORM},trim=end_frame={B-A},setpts=PTS-STARTPTS[p{len(parts)}]")
    k += 1; cur = B
parts.append(f"[0:v]trim=start_frame={cur},setpts=PTS-STARTPTS,{TM},{NORM}{zoom(cur / FPS)}[p{len(parts)}]")
n = len(parts)
graph = ";".join(parts) + ";" + "".join(f"[p{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]"
# intermedio SIN pérdida (qp 0) para no recomprimir dos veces
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[v]", "-map", "0:a",
                "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", "-c:a", "copy", "montado3.mkv"], check=True)
