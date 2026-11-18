"""Genera index.html (un solo archivo, con fotos embebidas) a partir de src/app.html."""
import base64, pathlib
root = pathlib.Path(__file__).parent
html = (root / "src/app.html").read_text(encoding="utf-8")
imgs = {
    "__IMG_FACHADA__": "fachada-ixtapa-c.webp",
    "__IMG_ALBERCA__": "piscinas-ixtapa-m.webp",
    "__IMG_GASTRO__": "gastronomia-ixtapa-d.webp",
    "__IMG_ACTIVIDADES__": "actividadesentretenimiento-en-alberca.webp",
}
for key, name in imgs.items():
    data = base64.b64encode((root / "src/img" / name).read_bytes()).decode()
    html = html.replace(key, "data:image/webp;base64," + data)
(root / "index.html").write_text(html, encoding="utf-8")
print("index.html", len(html) // 1024, "KB")
