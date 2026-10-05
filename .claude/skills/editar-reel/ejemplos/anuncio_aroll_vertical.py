"""Fragmentos del VSL → plano vertical 1080x1920 desde el 4K, en una sola remuestra.
Plano alterno normal / cerrado (+12 %) en cada corte y zoom lento con la cara como punto fijo."""
import cv2, json, numpy as np, subprocess
W4, H4, OW, OH, FPS = 3840, 2160, 1080, 1920, 30
clips = json.load(open("clips.json")); face = json.load(open("face.json"))
fx, fy = face["x"], face["y"]
CW, CH = H4 * 9 / 16, H4                        # ventana 9:16 a altura completa (1215 x 2160)
L0 = min(max(fx - CW / 2, 0), W4 - CW)          # ventana base centrada en la cara
ZOOM_RATE, ZOOM_MAX, PUNCH = 0.012, 0.10, 1.12
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
                        "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p", "-c:v", "libx264", "-preset", "ultrafast",
                        "-qp", "0", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "aroll_v.mkv"], stdin=subprocess.PIPE)
total = 0
for ci, (s, e) in enumerate(clips):
    n = round((e - s) * FPS)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{s:.3f}", "-i", "src.mp4", "-frames:v", str(n),
                            "-vf", "scale=in_color_matrix=bt709:in_range=tv,format=rgb24", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    z0 = PUNCH if ci % 2 else 1.0
    for k in range(n):
        b = dec.stdout.read(W4 * H4 * 3)
        if len(b) < W4 * H4 * 3: b = last
        last = b
        img = np.frombuffer(b, np.uint8).reshape(H4, W4, 3)
        z = z0 * (1 + min(ZOOM_MAX, ZOOM_RATE * k / FPS))
        cw, ch = CW / z, CH / z
        x = fx - (fx - L0) / z; y = fy - fy / z          # la cara se queda en el mismo punto de pantalla
        x = min(max(x, 0), W4 - cw); y = min(max(y, 0), H4 - ch)
        crop = img[int(y):int(y + ch) + 1, int(x):int(x + cw) + 1]
        enc.stdin.write(cv2.resize(crop, (OW, OH), interpolation=cv2.INTER_AREA).tobytes())
    dec.wait(); total += n
    print(f"fragmento {ci + 1}/{len(clips)} ({n} fotogramas)", flush=True)
enc.stdin.close(); enc.wait()
# audio: mismos fragmentos con fundidos de 15 ms para que no haya chasquidos en los cortes
parts = []
for i, (s, e) in enumerate(clips):
    n = round((e - s) * FPS) / FPS
    parts.append(f"[0:a]atrim=start={s:.3f}:duration={n:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.015,afade=t=out:st={n - 0.015:.4f}:d=0.015[a{i}]")
graph = ";".join(parts) + ";" + "".join(f"[a{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=0:a=1[a]"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "src.mp4", "-filter_complex", graph, "-map", "[a]", "-c:a", "pcm_s16le", "audio_resumen.wav"], check=True)
print("listo", total / FPS, "s")
