"""Reel solo B-roll a compás: 9:16 con el clip 16:9 centrado y franjas negras."""
import subprocess, sys, os
B = sys.argv[1]; B2 = sys.argv[2]
BPM, PHASE = 106.890, 0.0987
beat = 60 / BPM; bar = 4 * beat
START = PHASE + 84 * beat            # compás 21 de la canción (47,25 s); el beat fuerte entra en el compás 24
TM = "zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
GRADE = "eq=contrast=0.96:saturation=0.9:gamma=1.02,colorbalance=rs=0.02:bs=-0.02:rh=0.03:bh=-0.03"
SHOTS = [  # (clip, inicio en el clip, compases)
    ("abriendo_compu", 0.6, 1),
    ("starbucks3", 2.0, 2),
    ("chat_viajes", 1.5, 1),      # ← entra el beat
    ("reunion", 3.0, 1),
    ("llamada_santi", 0.5, 1),
    ("terraza", 1.0, 1),
    ("chat_muebleria", 2.0, 1),
    ("cafe_cafeteria", 2.5, 1),
    ("starbucks2", 4.0, 1),
    ("reunion2", 5.0, 1),
    ("trabajando_cafe", 1.5, 1),
    ("tomando_cafe", 0.0, 1),
]
os.makedirs("shots", exist_ok=True)
lst = []
acc = 0
for k, (name, ss, nb) in enumerate(SHOTS):
    src = f"{B}/{name}.mov" if name != "tomando_cafe" else f"{B2}/tomando_cafe.mov"
    dur = nb * bar
    n = round((acc + nb) * bar * 30) - round(acc * bar * 30); acc += nb   # sin deriva: cortes en el compás exacto
    hdr = "arib" in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer",
                                    "-of", "csv=p=0", src], capture_output=True, text=True).stdout
    clip = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                                capture_output=True, text=True).stdout)
    speed = min(1.0, (clip - ss - 0.05) / dur)          # si el clip es un pelín corto, se ralentiza lo justo
    z1 = 1.06 if k % 2 == 0 else 1.0                    # empuje lento: alterna acercar / alejar
    z0 = 1.0 if k % 2 == 0 else 1.06
    zexpr = f"{z0}+({z1}-{z0})*on/{n}"
    vf = (f"{TM + ',' if hdr else ''}setpts=(PTS-STARTPTS)/{speed},fps=30,{GRADE},"
          f"scale=2160:1216:flags=lanczos,zoompan=z='{zexpr}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x608:fps=30,"
          f"trim=end_frame={n},setsar=1,format=yuv420p")
    out = f"shots/{k:02d}.mkv"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(ss), "-i", src, "-an", "-vf", vf, "-frames:v", str(n),
                    "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", out], check=True)
    lst.append(f"file '{out}'")
    print(name, f"{dur:.2f}s", "hdr" if hdr else "sdr", f"vel {speed:.3f}")
open("shots.txt", "w").write("\n".join(lst) + "\n")
total = sum(nb for *_, nb in SHOTS) * bar
print("START", round(START, 3), "TOTAL", round(total, 3))
