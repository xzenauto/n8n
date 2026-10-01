import json, os, time, urllib.request, sys

N8N = os.environ["N8N_API_URL"]
KEY = os.environ["N8N_API_KEY"]
TEST = f"{N8N}/webhook/casa-alpa-test-{open('/tmp/claude-0/wf/test_tok').read().strip()}"
VALE = f"{N8N}/webhook/vale-casa-alpa"
WF = "4uL8xM5E6yI7bMWd"
OUT = "/tmp/claude-0/wf/transcripciones.jsonl"


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=90).read() or "{}")


def api(path):
    req = urllib.request.Request(f"{N8N}/api/v1{path}", headers={"X-N8N-API-KEY": KEY})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def ultima_ejecucion():
    d = api(f"/executions?workflowId={WF}&limit=1")["data"]
    return int(d[0]["id"]) if d else 0


def esperar(desde, timeout=240):
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(4)
        d = api(f"/executions?workflowId={WF}&limit=5")["data"]
        nuevas = [e for e in d if int(e["id"]) > desde and e.get("status") not in ("running", "waiting", "new")]
        corriendo = api(f"/executions?workflowId={WF}&status=running&limit=5")["data"] + api(f"/executions?workflowId={WF}&status=waiting&limit=5")["data"]
        ahora = time.time()
        def edad(e):
            from datetime import datetime
            return ahora - datetime.fromisoformat(e["startedAt"].replace("Z", "+00:00")).timestamp()
        corriendo = [e for e in corriendo if int(e["id"]) > desde and edad(e) < 150]
        if nuevas and not corriendo:
            return sorted(nuevas, key=lambda e: int(e["id"]))
    return []


def leer(eid):
    ex = api(f"/executions/{eid}?includeData=true")
    rd = ex["data"]["resultData"]["runData"]
    pe = rd.get("Code - Plan Envio")
    if not pe:
        return None, ex["status"], ex["data"]["resultData"].get("lastNodeExecuted")
    j = pe[0]["data"]["main"][0][0]["json"]
    tools = {k: len(v) for k, v in rd.items() if k in ("buscar_catalogo", "cotizar_producto", "generar_link_pago", "actualizar_prospecto")}
    return {"mensajes": j["mensajes"], "fotos": [f.get("producto") for f in j["fotos"]], "etapa": j["out"].get("etapa"),
            "handoff": j["out"].get("handoff_motivo"), "tools": tools}, ex["status"], ex["data"]["resultData"].get("lastNodeExecuted")


ESCENARIOS = [
    {"slug": "lucia", "nombre": "Lucía", "ad_id": "120210000000000001", "turnos": [
        ["Hola! Vi su anuncio del comedor"],
        ["Soy Lucía"],
        ["Somos 6 en casa, pero a veces vienen mis papás y seríamos 8"],
        ["El espacio es como de 3.5 x 3 metros. Me gustan los tonos de madera claros"],
        ["Me gusta la KELSO, ¿de qué material es? ¿aguanta uso diario con niños?"],
        ["Va, me late la KELSO para 8 personas. ¿Cuánto sale?"],
        ["Perfecto, ¿me mandas el link para comprarla?"],
    ]},
    {"slug": "roberto", "nombre": "Roberto", "ad_id": None, "turnos": [
        ["Buenas tardes, ¿cuánto cuestan las salas?"],
        ["Roberto. Es para la sala de mi depa, somos 2 y tenemos un perro"],
        ["Grises de preferencia, algo moderno"],
        ["¿Tienes más fotos del love Italia?"],
        ["Me quedo con el love, el de 177. ¿Precio?"],
        ["Ok, ¿aceptan meses sin intereses?"],
        ["Mándame el link porfa"],
    ]},
    {"slug": "fernanda", "nombre": "Fernanda", "ad_id": None, "turnos": [
        ["Hola, busco una cama king size", "algo minimalista"],
        ["Fernanda 😊"],
        ["Me gusta la Kross. ¿En cuánto tiempo llega a Monterrey?"],
    ]},
    {"slug": "jorge", "nombre": "Jorge", "ad_id": None, "turnos": [
        ["Hola, quiero un espejo redondo para mi recibidor"],
        ["Jorge. Mi casa es estilo moderno"],
        ["Me gusta el Zoe, ¿cuánto cuesta?"],
        ["Si me llevo 3 ¿me haces descuento?"],
    ]},
    {"slug": "mariana", "nombre": "Mariana", "ad_id": "120210000000000002", "turnos": [
        ["hola", "vi la sala del anuncio", "¿todavía la tienen?"],
        [""],
        ["Perdón, te mando audio sin querer. Me llamo Mariana, quiero la sala para 6 personas aprox"],
    ]},
]

solo = sys.argv[1:] or [e["slug"] for e in ESCENARIOS]
for esc in ESCENARIOS:
    if esc["slug"] not in solo:
        continue
    c = post(TEST, {"accion": "crear_contacto", "nombre": esc["nombre"], "slug": esc["slug"] + str(int(time.time()) % 10000)})
    cid = (c.get("contact") or {}).get("id")
    print(f"\n######## {esc['nombre']} -> contacto {cid}", flush=True)
    if not cid:
        print("no se pudo crear:", c, flush=True)
        continue
    with open(OUT, "a") as f:
        f.write(json.dumps({"escenario": esc["slug"], "contact_id": cid, "tipo": "contacto"}, ensure_ascii=False) + "\n")
    for turno in esc["turnos"]:
        desde = ultima_ejecucion()
        for i, msg in enumerate(turno):
            body = {"contact_id": cid, "full_name": esc["nombre"] + " Prueba Vale", "first_name": esc["nombre"],
                    "tags": "test-vale, simulacion-vale", "location": {"id": "iYgqtO9TzgsM2X4hzyhj"},
                    "message": {"type": 19, "body": msg},
                    "contact": {"attributionSource": {"medium": "facebook" if esc["ad_id"] else "direct", "adId": esc["ad_id"]}}}
            post(VALE, body)
            if i < len(turno) - 1:
                time.sleep(2)
        exs = esperar(desde)
        res = None
        for e in exs:
            r, st, last = leer(e["id"])
            if r:
                res = (e["id"], r, st, last)
        print(f"\n👤 {' / '.join(m or '[audio]' for m in turno)}", flush=True)
        if not res:
            print(f"   (sin respuesta) ejecuciones={[ (e['id'], e['status']) for e in exs]}", flush=True)
            continue
        eid, r, st, last = res
        for m in r["mensajes"]:
            print(f"💬 {m}", flush=True)
        if r["fotos"]:
            print(f"🖼  {r['fotos']}", flush=True)
        print(f"   [exec {eid} {st} | etapa={r['etapa']} | tools={r['tools']}{' | handoff: ' + r['handoff'] if r['handoff'] else ''}]", flush=True)
        with open(OUT, "a") as f:
            f.write(json.dumps({"escenario": esc["slug"], "contact_id": cid, "cliente": turno, "exec": eid, **r}, ensure_ascii=False) + "\n")
