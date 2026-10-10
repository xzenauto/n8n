"""Base de datos de B-rolls del usuario: cuántas veces se ha usado cada clip y en qué reels.
Uso:
  brolls_db.py informe                 tabla ordenada por usos (y genera USO_BROLLS.md)
  brolls_db.py sugerir [n] [tema]      los n clips menos usados (opcional: filtrar por tema)
  brolls_db.py registrar <reel> clip1 clip2 ...   apunta un reel entregado
  brolls_db.py nuevo <nombre> <drive_id> <h|v> "<título>" tema1,tema2   añade un clip
Regla: en un mismo reel no se repite ningún clip; entre reels se eligen primero los menos usados
y los que no salieron en los 2 últimos reels."""
import json, sys, os, datetime
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brolls.json")
db = json.load(open(P)); C = db["clips"]
def save(): json.dump(db, open(P, "w"), ensure_ascii=False, indent=1)
def ultimos(n=2):
    rs = sorted({(u["fecha"], u["reel"]) for c in C.values() for u in c["usos"]})
    return {r for _, r in rs[-n:]}
def orden():
    rec = ultimos()
    return sorted(C, key=lambda k: (len(C[k]["usos"]), sum(u["reel"] in rec for u in C[k]["usos"]), k))
cmd = sys.argv[1] if len(sys.argv) > 1 else "informe"
if cmd == "informe":
    rows = ["| Clip | Título en Drive | Orient. | Usos | Último reel |", "|---|---|---|---|---|"]
    for k in sorted(C, key=lambda k: (-len(C[k]["usos"]), k)):
        c = C[k]; last = c["usos"][-1]["reel"] if c["usos"] else "—"
        rows.append(f"| {k} | {c['titulo']} | {'vertical' if c['orientacion'] == 'v' else 'horizontal'} | {len(c['usos'])} | {last} |")
        print(f"{len(c['usos']):3d}  {k:26s} {c['orientacion']}  {last}")
    open(os.path.join(os.path.dirname(P), "USO_BROLLS.md"), "w").write(
        "# Uso de B-rolls\n\nSe actualiza con `brolls_db.py informe`. Más usados arriba.\n\n" + "\n".join(rows) + "\n")
elif cmd == "sugerir":
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10; tema = sys.argv[3].lower() if len(sys.argv) > 3 else None
    for k in [k for k in orden() if not tema or any(tema in t.lower() for t in C[k]["temas"])][:n]:
        print(f"{len(C[k]['usos']):3d}  {k:26s} {C[k]['orientacion']}  {', '.join(C[k]['temas'])}  {C[k]['nota']}")
elif cmd == "registrar":
    reel, clips = sys.argv[2], sys.argv[3:]
    assert len(set(clips)) == len(clips), "hay clips repetidos en el reel"
    for c in clips:
        C[c]["usos"].append({"reel": reel, "fecha": datetime.date.today().isoformat()})
    save(); print("registrado", reel, len(clips), "clips")
elif cmd == "nuevo":
    k, i, o, t, tg = sys.argv[2:7]
    C[k] = {"drive_id": i, "titulo": t, "orientacion": o, "temas": tg.split(","), "nota": "", "usos": []}; save(); print("añadido", k)
