"""Inserta B-rolls sobre el plano principal 4:3 (1440x1080). Horizontal: llena el 4:3 (recorte
central + zoom lento). Vertical: entero en el centro sobre una copia desenfocada.
Uso: broll43.py aroll.mkv inserts.json salida.mkv   inserts = [[src, ss, t0, t1, "h"|"v"], ...]"""
import json, subprocess, sys
A, INS, OUT = sys.argv[1:4]
ins = json.load(open(INS))
TM = "zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
args, fc, prev = ["-i", A], [], "0:v"
for k, (src, ss, t0, t1, kind) in enumerate(ins):
    d = t1 - t0; n = round(d * 30)
    hdr = "arib" in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer",
                                    "-of", "csv=p=0", src], capture_output=True, text=True).stdout
    args += ["-ss", str(ss), "-t", str(d + 0.5), "-i", src]
    pre = f"[{k + 1}:v]{TM + ',' if hdr else ''}fps=30,setpts=PTS-STARTPTS,eq=saturation=0.92"
    if kind == "h":
        fc.append(f"{pre},scale=-2:2160:flags=lanczos,crop=2880:2160,zoompan=z='1+0.04*on/{n}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1440x1080:fps=30,"
                  f"trim=end_frame={n},setpts=PTS-STARTPTS+{t0}/TB,format=yuv420p[b{k}]")
    else:
        fc.append(f"{pre},split[s{k}][f{k}];[s{k}]scale=1440:-2,crop=1440:1080:0:(ih-1080)/2,gblur=sigma=40,eq=brightness=-0.18[bg{k}];"
                  f"[f{k}]scale=-2:1080:flags=lanczos[fg{k}];[bg{k}][fg{k}]overlay=(W-w)/2:0,trim=end_frame={n},"
                  f"setpts=PTS-STARTPTS+{t0}/TB,format=yuv420p[b{k}]")
    fc.append(f"[{prev}][b{k}]overlay=enable='between(t,{t0},{t1 - 0.001})':eof_action=pass[o{k}]"); prev = f"o{k}"
fc.append(f"[{prev}]format=yuv420p[v]")
subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "0:a",
                "-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", "-c:a", "copy", OUT], check=True)
print("montado:", OUT)
