"""Configura la subcuenta de GHL (idempotente): pipeline, carpetas de campos, campos y tags.
Uso: GHL_API_KEY=... GHL_LOCATION_ID=... python3 ghl_setup.py  -> escribe ghl_ids.json"""
import json, os, urllib.request

B = "https://services.leadconnectorhq.com"
L = os.environ["GHL_LOCATION_ID"]
HDR = {"Authorization": f"Bearer {os.environ['GHL_API_KEY']}", "Version": "2021-07-28",
       "Content-Type": "application/json", "Accept": "application/json", "User-Agent": "agencia-viajes-setup/1.0 curl/8"}

def api(method, path, body=None):
    req = urllib.request.Request(B + path, method=method, headers=HDR,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} -> {e.code} {e.read().decode()[:300]}")

PIPELINE = "Ventas Viajes"
STAGES = [
    "🤖 Nuevo – Lucía recopilando",
    "⏳ Datos incompletos – sin respuesta",
    "✅ Datos completos",
    "🔥 Datos completos – viaja en menos de 15 días",
    "🙋 Atención humana",
    "📩 Cotización enviada",
    "💬 Cliente respondió / negociando",
    "💳 Apartado / pagos en curso",
    "✈️ Pagado – viaje confirmado",
    "🏁 Viaje completado",
    "❌ Perdido / frío",
]

T, D, N, LT = "TEXT", "DATE", "NUMERICAL", "LARGE_TEXT"
def vuelos(tramo):
    out = []
    for i in (1, 2, 3):
        p = f"{tramo} V{i}"
        out += [(f"{p} - Aerolínea y número", T), (f"{p} - Ruta (origen → destino)", T),
                (f"{p} - Salida (fecha y hora)", T), (f"{p} - Llegada (fecha y hora)", T)]
    return out

FOLDERS = {
    "1. Datos IA (Lucía)": [
        ("IA Destino", T), ("IA Fecha salida", D), ("IA Fecha regreso", D), ("IA Fechas (texto)", T),
        ("IA Adultos", N), ("IA Niños", N), ("IA Edades niños", T), ("IA Promo de interés", T),
        ("IA Ad ID", T), ("IA Canal de origen", T), ("IA Viaja en menos de 15 días", T),
        ("IA Resumen conversación", LT),
    ],
    "2. Cotización (Ventas)": [
        ("Cot Vendedora", T), ("Cot Fecha de envío", D), ("Cot Destino", T), ("Cot Hotel", T),
        ("Cot Plan de alimentos", T), ("Cot Habitaciones", T), ("Cot Monto total MXN", N),
        ("Cot Incluye", LT), ("Cot Link o archivo", T), ("Cot Vigencia", D), ("Cot Notas", LT),
    ],
    "3. Vuelos": vuelos("Ida") + [("Ida - Clave de reservación", T)]
               + vuelos("Regreso") + [("Regreso - Clave de reservación", T), ("Vuelos - Equipaje incluido", T)],
    "4. Pagos": [("Pago Precio total MXN", N), ("Pago Anticipo MXN", N), ("Pago Saldo pendiente MXN", N),
                 ("Pago Método", T)]
               + [x for i in range(1, 7) for x in ((f"Pago {i} - Fecha límite", D), (f"Pago {i} - Monto MXN", N),
                                                    (f"Pago {i} - Estatus", ("SINGLE_OPTIONS", ["Pendiente", "Pagado"])))],
    "5. Datos definitivos del viaje": [
        ("Viaje Destino", T), ("Viaje Fecha salida", D), ("Viaje Fecha regreso", D), ("Viaje Hotel", T),
        ("Viaje Check-in", D), ("Viaje Check-out", D), ("Viaje Confirmación hotel", T),
        ("Viaje Plan de alimentos", T), ("Viaje Habitaciones", T), ("Viaje Pasajeros", LT),
        ("Viaje Traslados", T), ("Viaje Tours y extras", LT), ("Viaje Seguro", T),
        ("Viaje Notas para el cliente", LT),
    ],
}

TAGS = ["ia-pausada", "seguimiento-pausado", "datos-completos", "urgente-15-dias",
        "escalado-humano", "cotizacion-enviada", "cliente-recurrente", "lucia"]

ids = {"locationId": L}

# Pipeline
pipes = api("GET", f"/opportunities/pipelines?locationId={L}")["pipelines"]
pipe = next((p for p in pipes if p["name"] == PIPELINE), None)
if not pipe:
    pipe = api("POST", "/opportunities/pipelines", {"locationId": L, "name": PIPELINE,
               "showInFunnel": True, "showInPieChart": True,
               "stages": [{"name": s, "position": i} for i, s in enumerate(STAGES)]})["pipeline"]
ids["pipelineId"] = pipe["id"]
ids["stages"] = {s["name"]: s["id"] for s in pipe["stages"]}

# Carpetas y campos
existing = api("GET", f"/locations/{L}/customFields?model=all")["customFields"]
by_name = {(f.get("documentType"), f["name"]): f for f in existing}
ids["folders"], ids["fields"] = {}, {}
for folder, fields in FOLDERS.items():
    fo = by_name.get(("folder", folder)) or api("POST", f"/locations/{L}/customFields",
            {"name": folder, "model": "contact", "documentType": "folder"})["customFieldFolder"]
    ids["folders"][folder] = fo["id"]
    for name, dtype in fields:
        f = by_name.get(("field", name))
        if not f:
            body = {"name": name, "model": "contact", "parentId": fo["id"]}
            if isinstance(dtype, tuple):
                body["dataType"], body["options"] = dtype
            else:
                body["dataType"] = dtype
            f = api("POST", f"/locations/{L}/customFields", body)["customField"]
        ids["fields"][name] = {"id": f["id"], "key": f["fieldKey"]}

# Tags
have = {t["name"] for t in api("GET", f"/locations/{L}/tags")["tags"]}
for t in TAGS:
    if t not in have:
        api("POST", f"/locations/{L}/tags", {"name": t})
ids["tags"] = TAGS

# Usuarias
ids["users"] = {u["firstName"]: u["id"] for u in api("GET", f"/users/?locationId={L}")["users"]}

json.dump(ids, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ghl_ids.json"), "w"),
          ensure_ascii=False, indent=2)
print(f"OK pipeline={ids['pipelineId']} stages={len(ids['stages'])} campos={len(ids['fields'])} users={ids['users']}")
