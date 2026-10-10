"""Reel POV v2 solo B-roll a compás (sin repetir clips). 9:16 con el plano 16:9 centrado.
Los clips verticales se recortan a una franja 16:9 (yc = centro de la franja, fracción del alto)."""
import subprocess, sys, os
R = sys.argv[1]
BPM, PHASE = 106.890, 0.0987
beat = 60 / BPM; half = 2 * beat
TM = "zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
GRADE = "eq=contrast=0.96:saturation=0.9:gamma=1.02,colorbalance=rs=0.02:bs=-0.02:rh=0.03:bh=-0.03"
B, N, E = f"{R}/reel2/broll", f"{R}/reel4/nuevos", f"{R}/reel10/in"
SHOTS = [  # (nombre, archivo, inicio, medios compases, yc vertical | None, ignorar rotación)
    ("starbucks", f"{B}/starbucks.mov", 3.0, 2, 0.45, False),
    ("trabajando_aeropuerto", f"{N}/trabajando_aeropuerto.mov", 0.0, 2, 0.42, False),
    ("volando", f"{N}/volando.mov", 2.0, 2, 0.58, False),
    ("eeuu1", f"{E}/eeuu1.mov", 0.5, 2, None, True),           # ← entra el beat
    ("eeuu3", f"{E}/eeuu3.mov", 2.0, 1, None, False),
    ("eeuu4", f"{E}/eeuu4.mov", 0.8, 1, None, False),
    ("gym", f"{B}/gym.mov", 1.0, 1, None, False),
    ("gym2", f"{B}/gym2.mov", 2.0, 1, None, False),
    ("piernas_gimnasio", f"{N}/piernas_gimnasio.mov", 0.0, 1, 0.45, False),
    ("llamada_santi", f"{B}/llamada_santi.mov", 0.8, 1, None, False),
    ("viajando2", f"{N}/viajando2.mp4", 1.2, 2, 0.52, False),
    ("paseando", f"{N}/paseando.mov", 0.8, 1, 0.45, False),
    ("eeuu2", f"{E}/eeuu2.mov", 0.3, 1, None, True),
    ("reunion_vertical", f"{B}/reunion_vertical.mov", 4.0, 1, 0.55, False),
    ("cafe_cafeteria", f"{B}/cafe_cafeteria.mov", 3.0, 1, None, False),
    ("trabajando_cafe", f"{B}/trabajando_cafe.mov", 2.0, 2, None, False),
    ("familia", f"{N}/familia.mov", 0.3, 2, 0.50, False),
    ("trabajando_xime_vertical", f"{B}/trabajando_xime_vertical.mov", 6.6, 2, 0.50, False),
]
os.makedirs("shots", exist_ok=True)
lst, acc = [], 0
for k, (name, src, ss, nh, yc, noauto) in enumerate(SHOTS):
    n = round((acc + nh) * half * 30) - round(acc * half * 30); acc += nh
    dur = n / 30
    probe = lambda e: subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", e, "-of", "csv=p=0", src],
                                     capture_output=True, text=True).stdout
    hdr = "arib" in probe("stream=color_transfer")
    clip = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                                capture_output=True, text=True).stdout)
    speed = min(1.0, (clip - ss - 0.03) / dur)
    crop = f"crop=iw:iw*9/16:0:'min(max(ih*{yc}-iw*9/32,0),ih-iw*9/16)'," if yc is not None else ""
    z0, z1 = (1.0, 1.06) if k % 2 == 0 else (1.06, 1.0)
    vf = (f"{TM + ',' if hdr else ''}setpts=(PTS-STARTPTS)/{speed},fps=30,{crop}{GRADE},"
          f"scale=2160:1216:flags=lanczos,zoompan=z='{z0}+({z1}-{z0})*on/{n}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x608:fps=30,"
          f"setsar=1,format=yuv420p")
    out = f"shots/{k:02d}.mkv"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *(["-noautorotate"] if noauto else []), "-ss", str(ss), "-i", src, "-an",
                    "-vf", vf, "-frames:v", str(n), "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", out], check=True)
    lst.append(f"file '{out}'")
    print(f"{k:02d} {name:26s} {dur:.2f}s {'hdr' if hdr else 'sdr'} vel {speed:.3f}")
open("shots.txt", "w").write("\n".join(lst) + "\n")
print("TOTAL", round(acc * half, 3))
