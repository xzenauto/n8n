import subprocess, json
from plan import BROLL
TM = open("tm_best.txt").read().split(",eq=")[0]
SAT = json.load(open("sat.json"))
NORM = "scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,fps=30,setsar=1,format=yuv420p"
FPS = 30; fr = lambda t: round(t * FPS)
inputs, parts, k, cur = ["-i", "aroll_estable.mkv"], [], 1, 0
for a, b, clip, off in BROLL:
    A, B = fr(a), fr(b)
    if A > cur:
        parts.append(f"[0:v]trim=start_frame={cur}:end_frame={A},setpts=PTS-STARTPTS,format=yuv420p[p{len(parts)}]")
    inputs += ["-ss", str(off), "-i", f"broll/{clip}.mov"]
    info = SAT[clip]
    pre = TM + "," if info["hdr"] else ""
    eq = f",eq=saturation={info['sat']}" if info["sat"] < 0.99 else ""
    parts.append(f"[{k}:v]{pre}{NORM}{eq},trim=end_frame={B-A},setpts=PTS-STARTPTS[p{len(parts)}]")
    k += 1; cur = B
parts.append(f"[0:v]trim=start_frame={cur},setpts=PTS-STARTPTS,format=yuv420p[p{len(parts)}]")
n = len(parts)
graph = ";".join(parts) + ";" + "".join(f"[p{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]"
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[v]", "-map", "0:a",
                "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", "-c:a", "copy", "montado.mkv"], check=True)
