import json, sys
p = sys.argv[1]; w = json.load(open(p))
out = []; i = 0
while i < len(w):
    x = w[i]
    if x["w"].lower() == "número" and i + 1 < len(w) and w[i+1]["w"].rstrip(",") in "123":
        n = w[i+1]["w"].rstrip(",")
        out.append({"w": f"[#{n}]", "s": x["s"], "e": w[i+1]["e"], "hl": True, "scale": 1.5}); i += 2; continue
    if x["w"] == "72" and w[i+1]["w"] == "%":
        out.append({"w": "72%", "s": x["s"], "e": w[i+1]["e"]}); i += 2; continue
    out.append(x); i += 1
HL = {"automatizaciones": 0.98, "tiempo": 5.64, "dinero.": 6.32, "prospectos.": 7.80, "tiempo,": 10.54,
      "comprar": 13.04, "inmediata": 15.18, "competencia.": 17.02, "abandonados.": 19.54, "72%": 23.76,
      "clientes": 25.30, "estadísticas.": 29.56, "vendedores": 31.60, "cierre?": 34.06, "dinero": 35.26,
      "artificial": 39.36, "venta.": 42.66, "información?": 44.46}
for x in out:
    if x["w"] in HL and abs(x["s"] - HL[x["w"]]) < 0.05: x["hl"] = True
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=0)
print(sum(1 for x in out if x.get("hl")), "hl")
