"""Genera y publica en n8n los workflows de la agencia (Lucía).

Uso:
  N8N_API_URL=... N8N_API_KEY=... python3 build_workflows.py            # genera JSON en workflows/ y publica
  python3 build_workflows.py --solo-json                                  # solo genera JSON
Los IDs de GHL se leen de ghl_ids.json (generado por ghl_setup.py).
"""
import json, os, sys, uuid, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
IDS = json.load(open(os.path.join(AQUI, "ghl_ids.json"), encoding="utf-8"))

# ---------------------------------------------------------------- constantes
SB = "https://fllhjemdhohsewqwzrpc.supabase.co/rest/v1/rpc/"
GHL = "https://services.leadconnectorhq.com"
SHEET_ID = "1lrw1EK-laBq-QJkHUxQGr7fN7b-OD7bqE57nDR_qKx0"
MODELO = "gpt-4.1-mini"
AGENCIA = "Agencia Prueba"

CRED_SB = {"supabaseApi": {"id": "QIVohgUOAGTuwYd1", "name": "XzenAuto"}}
CRED_OAI = {"openAiApi": {"id": "W5zBaQ7k25sn9YQz", "name": "RsViaje Independencia"}}
CRED_GHL = {"httpHeaderAuth": {"id": "XfOfsH6da3CzpPt9", "name": "GHL - Agencia Prueba (API Lucía)"}}
CRED_SHEETS = {"googleSheetsOAuth2Api": {"id": "5tVcEyMfkgXjzc9v", "name": "Xzen_Pruebas"}}

ST = IDS["stages"]
S = {  # alias cortos de columnas
    "nuevo": ST["🤖 Nuevo – Lucía recopilando"],
    "incompletos": ST["⏳ Datos incompletos – sin respuesta"],
    "completos": ST["✅ Datos completos"],
    "urgente": ST["🔥 Datos completos – viaja en menos de 15 días"],
    "humano": ST["🙋 Atención humana"],
    "cotizacion": ST["📩 Cotización enviada"],
    "respondio": ST["💬 Cliente respondió / negociando"],
    "apartado": ST["💳 Apartado / pagos en curso"],
    "pagado": ST["✈️ Pagado – viaje confirmado"],
    "completado": ST["🏁 Viaje completado"],
    "perdido": ST["❌ Perdido / frío"],
}
CFG = {
    "locationId": IDS["locationId"],
    "pipelineId": IDS["pipelineId"],
    "S": S,
    "F": {k: v["id"] for k, v in IDS["fields"].items()},
    "agencia": AGENCIA,
    "modelo": MODELO,
}
CFG_JS = "const CFG = " + json.dumps(CFG, ensure_ascii=False) + ";\n"

# ---------------------------------------------------------------- helpers de nodos
def _id():
    return str(uuid.uuid4())

class WF:
    def __init__(self, name):
        self.name, self.nodes, self.conn = name, [], {}

    def add(self, name, type_, version, params, pos, creds=None, **extra):
        n = {"id": _id(), "name": name, "type": type_, "typeVersion": version,
             "position": list(pos), "parameters": params}
        if creds:
            n["credentials"] = creds
        n.update(extra)
        self.nodes.append(n)
        return name

    def link(self, a, b, out=0):
        self.conn.setdefault(a, {"main": []})
        while len(self.conn[a]["main"]) <= out:
            self.conn[a]["main"].append([])
        self.conn[a]["main"][out].append({"node": b, "type": "main", "index": 0})

    def chain(self, *names):
        for a, b in zip(names, names[1:]):
            self.link(a, b)

    def json(self):
        return {"name": self.name, "nodes": self.nodes, "connections": self.conn,
                "settings": {"executionOrder": "v1", "timezone": "America/Mexico_City",
                             "saveDataErrorExecution": "all", "saveDataSuccessExecution": "all",
                             "availableInMCP": True}}


def code(wf, name, js, pos, each=False, **extra):
    p = {"jsCode": js}
    if each:
        p["mode"] = "runOnceForEachItem"
    return wf.add(name, "n8n-nodes-base.code", 2, p, pos, **extra)


def rpc(wf, name, fn, body_expr, pos, **extra):
    return wf.add(name, "n8n-nodes-base.httpRequest", 4.2, {
        "method": "POST", "url": SB + fn,
        "authentication": "predefinedCredentialType", "nodeCredentialType": "supabaseApi",
        "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify(" + body_expr + ") }}",
        "options": {}}, pos, CRED_SB, **extra)


def ghl(wf, name, method, url_expr, pos, body_expr=None, query=None, **extra):
    p = {"method": method, "url": "=" + GHL + url_expr,
         "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
         "sendHeaders": True,
         "headerParameters": {"parameters": [{"name": "Version", "value": "2021-07-28"},
                                             {"name": "Accept", "value": "application/json"}]},
         "options": {}}
    if query:
        p["sendQuery"] = True
        p["queryParameters"] = {"parameters": [{"name": k, "value": v} for k, v in query]}
    if body_expr:
        p["sendBody"] = True
        p["specifyBody"] = "json"
        p["jsonBody"] = "={{ JSON.stringify(" + body_expr + ") }}"
    return wf.add(name, "n8n-nodes-base.httpRequest", 4.2, p, pos, CRED_GHL, **extra)


def openai(wf, name, body_expr, pos, **extra):
    return wf.add(name, "n8n-nodes-base.httpRequest", 4.2, {
        "method": "POST", "url": "https://api.openai.com/v1/chat/completions",
        "authentication": "predefinedCredentialType", "nodeCredentialType": "openAiApi",
        "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify(" + body_expr + ") }}",
        "options": {"timeout": 90000}}, pos, CRED_OAI,
        retryOnFail=True, maxTries=3, waitBetweenTries=3000, **extra)


def cond_bool(expr):
    return {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
            "conditions": [{"id": _id(), "leftValue": "={{ " + expr + " }}", "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
            "combinator": "and"}, "options": {}}


def if_(wf, name, expr, pos):
    return wf.add(name, "n8n-nodes-base.if", 2.2, cond_bool(expr), pos)


def switch(wf, name, expr, keys, pos):
    rules = [{"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                             "conditions": [{"id": _id(), "leftValue": "={{ " + expr + " }}", "rightValue": k,
                                             "operator": {"type": "string", "operation": "equals"}}],
                             "combinator": "and"},
              "renameOutput": True, "outputKey": k} for k in keys]
    return wf.add(name, "n8n-nodes-base.switch", 3.2, {"rules": {"values": rules}, "options": {}}, pos)


CONTINUAR = {"onError": "continueRegularOutput"}

# ---------------------------------------------------------------- JS compartido
JS_FECHAS = r"""
const OFFSET = -6; // CDMX sin horario de verano
function hoyCdmx() { return new Date(Date.now() + OFFSET * 3600e3).toISOString().slice(0, 10); }
function fechaCampo(v) { // valor de campo DATE de GHL -> 'YYYY-MM-DD'
  if (v === null || v === undefined || v === '') return null;
  if (typeof v === 'number' || /^\d{10,}$/.test(String(v))) {
    const d = new Date(Number(v));
    return (d.getUTCHours() === 0 ? d : new Date(d.getTime() + OFFSET * 3600e3)).toISOString().slice(0, 10);
  }
  const s = String(v);
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10);
  const m = s.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})/);
  if (m) return `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}`;
  const d = new Date(s); return isNaN(d) ? null : d.toISOString().slice(0, 10);
}
const MESES = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
const DIAS = ['domingo','lunes','martes','miércoles','jueves','viernes','sábado'];
function fechaLarga(iso) { const d = new Date(iso + 'T12:00:00Z'); return `${DIAS[d.getUTCDay()]} ${d.getUTCDate()} de ${MESES[d.getUTCMonth()]}`; }
function diasEntre(a, b) { return Math.round((new Date(b + 'T12:00:00Z') - new Date(a + 'T12:00:00Z')) / 864e5); }
"""

# ============================================================== 1. LUCÍA – CONVERSACIÓN
def wf_conversacion():
    wf = WF("Lucía – Conversación (Agencia Prueba)")
    X, Y = 0, 300
    wf.add("Mensaje entrante GHL", "n8n-nodes-base.webhook", 2.1,
           {"httpMethod": "POST", "path": "lucia-agencia-prueba", "responseMode": "onReceived", "options": {}},
           (X, Y), webhookId=_id())
    code(wf, "Normalizar entrada", r"""
const j = $input.first().json; const b = j.body || j;
const id = b.contact_id || b.contactId || (b.contact && b.contact.id) || (b.customData && b.customData.contact_id);
if (!id) return [];
return [{ json: { contact_id: String(id) } }];
""", (X + 220, Y))
    rpc(wf, "SB registrar mensaje", "viajes_registrar_mensaje", "{ p_contact_id: $json.contact_id }", (X + 440, Y))
    wf.add("Esperar ráfaga (15 s)", "n8n-nodes-base.wait", 1.1, {"resume": "timeInterval", "amount": 15, "unit": "seconds"}, (X + 660, Y), webhookId=_id())
    rpc(wf, "SB ¿es el último?", "viajes_es_ultimo",
        "{ p_contact_id: $('Normalizar entrada').item.json.contact_id, p_token: $('SB registrar mensaje').item.json.token }",
        (X + 880, Y))
    if_(wf, "¿Último mensaje?", "$json.es_ultimo", (X + 1100, Y))
    cid = "{{ $('Normalizar entrada').item.json.contact_id }}"
    ghl(wf, "GHL contacto", "GET", "/contacts/" + cid, (X + 1320, Y))
    ghl(wf, "GHL oportunidades", "GET", "/opportunities/search", (X + 1540, Y),
        query=[("location_id", CFG["locationId"]), ("contact_id", "=" + cid),
               ("pipeline_id", CFG["pipelineId"]), ("status", "all"), ("limit", "20")])
    ghl(wf, "GHL conversación", "GET", "/conversations/search", (X + 1760, Y),
        query=[("locationId", CFG["locationId"]), ("contactId", "=" + cid), ("limit", "1")])
    ghl(wf, "GHL mensajes", "GET", "/conversations/{{ ($json.conversations || [])[0]?.id || 'sin-conversacion' }}/messages",
        (X + 1980, Y), query=[("limit", "40")], **CONTINUAR)
    rpc(wf, "SB contexto", "viajes_get_contexto", "{ p_contact_id: $('Normalizar entrada').item.json.contact_id }",
        (X + 2200, Y))

    code(wf, "Analizar", CFG_JS + JS_FECHAS + r"""
const cid = $('Normalizar entrada').first().json.contact_id;
const contact = $('GHL contacto').first().json.contact || {};
const opps = $('GHL oportunidades').first().json.opportunities || [];
const conv = ($('GHL conversación').first().json.conversations || [])[0] || null;
let msgs = [];
try { const m = $('GHL mensajes').first().json.messages; msgs = (m && (m.messages || m)) || []; } catch (e) {}
if (!Array.isArray(msgs)) msgs = [];
const ctx = $('SB contexto').first().json || {};
const contacto = ctx.contacto || {};
const tags = (contact.tags || []).map(t => String(t).toLowerCase());

const TIPOS = { TYPE_WHATSAPP: 'WhatsApp', TYPE_INSTAGRAM: 'IG', TYPE_FACEBOOK: 'FB', TYPE_SMS: 'SMS',
  TYPE_LIVE_CHAT: 'Live_Chat', TYPE_WEBCHAT: 'Live_Chat', TYPE_TIKTOK: 'TikTok', TYPE_EMAIL: 'Email' };
const canalDe = t => TIPOS[t] || (/INSTAGRAM/.test(t) ? 'IG' : /FACEBOOK/.test(t) ? 'FB' : /TIKTOK/.test(t) ? 'TikTok' : null);
msgs = msgs.filter(m => canalDe(m.messageType || '')).sort((a, b) => new Date(a.dateAdded) - new Date(b.dateAdded));
const desde = contacto.ultimo_procesado_en ? new Date(contacto.ultimo_procesado_en) : new Date(0);
const nuevos = msgs.filter(m => m.direction === 'inbound' && new Date(m.dateAdded) > desde);
const historial = msgs.filter(m => !nuevos.includes(m)).slice(-30);
const ultimo = nuevos[nuevos.length - 1] || msgs[msgs.length - 1] || {};
const canal = canalDe(ultimo.messageType || '') || contacto.canal || 'WhatsApp';

// Oportunidad abierta en el pipeline (las de viaje completado / perdido ya no cuentan)
const abiertas = opps.filter(o => o.status === 'open' && ![CFG.S.completado, CFG.S.perdido].includes(o.pipelineStageId))
  .sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0));
const opp = abiertas[0] || null;

// Anuncio de Meta (ad_id) -> promo
function buscarAds(o, out, d) {
  if (!o || d > 6) return out;
  if (Array.isArray(o)) { o.forEach(x => buscarAds(x, out, d + 1)); return out; }
  if (typeof o === 'object') for (const [k, v] of Object.entries(o)) {
    const kk = k.toLowerCase().replace(/[^a-z]/g, '');
    if (['adid', 'sourceid', 'utmadid', 'fbadid', 'adsourceid', 'ctwaadid'].includes(kk) && (typeof v === 'string' || typeof v === 'number')) out.add(String(v));
    else if (v && typeof v === 'object') buscarAds(v, out, d + 1);
  }
  return out;
}
const body = $('Mensaje entrante GHL').first().json.body || {};
const adIds = [...buscarAds([contact.attributionSource, contact.lastAttributionSource, contact.attributions,
  nuevos.map(m => m.meta), body], new Set(), 0)];
const ads = ctx.ads || {};
const promos = ctx.promos || [];
const leads = ctx.leads || [];
const leadActual = opp ? leads.find(l => l.ghl_opportunity_id === opp.id) || null : null;
const adMatch = adIds.map(a => ads[a] && { ad: a, ...ads[a] }).filter(Boolean);
let promoAnuncio = null, promoVencida = null, adId = leadActual?.ad_id || null;
const mVig = adMatch.find(x => x.vigente);
if (mVig) { promoAnuncio = promos.find(p => p.id === mVig.id) || null; adId = mVig.ad; }
else if (adMatch[0]) { promoVencida = adMatch[0]; adId = adMatch[0].ad; }
if (!promoAnuncio && leadActual?.promo_id) promoAnuncio = promos.find(p => p.id === leadActual.promo_id) || null;
if (!adId && adIds.length) adId = adIds[0];

// Adjuntos
const AUDIO = /\.(ogg|oga|opus|mp3|m4a|wav|aac|amr|weba|webm|mpeg)(\?|$)/i, IMG = /\.(jpe?g|png|webp|gif)(\?|$)/i;
const audios = [], imagenes = [], otros = [];
for (const m of nuevos) for (const u of (m.attachments || [])) {
  if (AUDIO.test(u)) audios.push({ url: u }); else if (IMG.test(u)) imagenes.push(u); else otros.push(u);
}

let accion;
if (!nuevos.length) accion = 'ignorar';
else if (tags.includes('ia-pausada')) accion = 'pausada';
else if (!opp || [CFG.S.nuevo, CFG.S.incompletos].includes(opp.pipelineStageId)) accion = 'lucia';
else if (opp.pipelineStageId === CFG.S.cotizacion) accion = 'cliente_respondio';
else accion = 'vendedora';

const nombre = contact.firstName || contact.contactName || contact.name || '';
return [{ json: {
  accion, contact_id: cid, nombre, nombre_completo: [contact.firstName, contact.lastName].filter(Boolean).join(' ') || contact.contactName || '',
  telefono: contact.phone || '', canal, conversation_id: conv?.id || null,
  opportunity_id: opp?.id || null, stage_id: opp?.pipelineStageId || null,
  procesado_hasta: nuevos.length ? nuevos[nuevos.length - 1].dateAdded : null,
  nuevos: nuevos.map(m => ({ body: m.body || '', attachments: m.attachments || [], fecha: m.dateAdded })),
  historial: historial.map(m => ({ rol: m.direction === 'inbound' ? 'user' : 'assistant', texto: m.body || '' })).filter(m => m.texto.trim()),
  ad_id: adId, promo_anuncio: promoAnuncio, promo_vencida: promoVencida, promos,
  lead_actual: leadActual, anteriores: leads.filter(l => !opp || l.ghl_opportunity_id !== opp.id).slice(0, 3),
  audios, imagenes, otros, transcripciones: [], hoy: hoyCdmx(), tags,
}}];
""", (X + 2420, Y))

    switch(wf, "Acción", "$json.accion", ["lucia", "cliente_respondio", "vendedora", "pausada"], (X + 2640, Y))

    # --- Cliente respondió a la cotización
    Y2 = Y + 300
    ghl(wf, "GHL mover a Cliente respondió", "PUT", "/opportunities/{{ $json.opportunity_id }}", (X + 2860, Y2),
        body_expr="{ pipelineStageId: '" + S["respondio"] + "' }", **CONTINUAR)
    rpc(wf, "SB marcar procesado (respondió)", "viajes_marcar_procesado",
        "{ p_contact_id: $('Analizar').item.json.contact_id, p_hasta: $('Analizar').item.json.procesado_hasta, p_motivo: 'cliente_respondio' }",
        (X + 3080, Y2))
    wf.link("Acción", "GHL mover a Cliente respondió", 1)
    wf.link("GHL mover a Cliente respondió", "SB marcar procesado (respondió)")
    # --- Vendedora a cargo / IA pausada: solo registrar
    Y3 = Y + 500
    rpc(wf, "SB marcar procesado", "viajes_marcar_procesado",
        "{ p_contact_id: $json.contact_id, p_hasta: $json.procesado_hasta, p_motivo: $json.accion }", (X + 2860, Y3))
    wf.link("Acción", "SB marcar procesado", 2)
    wf.link("Acción", "SB marcar procesado", 3)

    # --- Lucía atiende
    if_(wf, "¿Trae audios?", "$json.audios.length > 0", (X + 2860, Y))
    wf.link("Acción", "¿Trae audios?", 0)
    Ya = Y - 250
    code(wf, "Separar audios", "return $input.first().json.audios.map(a => ({ json: a }));", (X + 3080, Ya), each=False)
    wf.add("Descargar audio", "n8n-nodes-base.httpRequest", 4.2,
           {"url": "={{ $json.url }}", "options": {"response": {"response": {"responseFormat": "file"}}}},
           (X + 3300, Ya), **CONTINUAR)
    wf.add("Transcribir audio", "n8n-nodes-base.httpRequest", 4.2, {
        "method": "POST", "url": "https://api.openai.com/v1/audio/transcriptions",
        "authentication": "predefinedCredentialType", "nodeCredentialType": "openAiApi",
        "sendBody": True, "contentType": "multipart-form-data",
        "bodyParameters": {"parameters": [
            {"parameterType": "formBinaryData", "name": "file", "inputDataFieldName": "data"},
            {"name": "model", "value": "whisper-1"}, {"name": "language", "value": "es"}]},
        "options": {}}, (X + 3520, Ya), CRED_OAI, **CONTINUAR)
    code(wf, "Unir transcripciones", r"""
const base = $('Analizar').first().json;
const t = $input.all().map(i => i.json.text).filter(Boolean);
return [{ json: { ...base, transcripciones: t } }];
""", (X + 3740, Ya))
    wf.chain("Separar audios", "Descargar audio", "Transcribir audio", "Unir transcripciones")
    wf.link("¿Trae audios?", "Separar audios", 0)

    code(wf, "Preparar prompt", CFG_JS + r"""
const a = $input.first().json;
const fmtPromo = p => p ? JSON.stringify({ id: p.id, destino: p.destino, hotel: p.hotel, titulo: p.titulo,
  vender_hasta: p.vigencia_hasta, fechas_de_viaje: [p.viaje_desde, p.viaje_hasta], noches: p.noches, plan: p.plan,
  dias_que_aplica: p.dias_aplica, precio_desde_mxn: p.precio_desde, precio_detalle: p.precio_detalle,
  precios_menores: p.precios_menores, incluye: p.incluye, condiciones: p.condiciones, texto_original: p.descripcion }) : 'ninguna';
const l = a.lead_actual || {};
const datos = { destino: l.destino || null, fecha_salida: l.fecha_salida || null, fecha_regreso: l.fecha_regreso || null,
  fechas_texto: l.fechas_texto || null, fechas_sin_definir: !!l.fechas_sin_definir, adultos: l.adultos ?? null,
  ninos: l.ninos ?? null, edades_ninos: l.edades_ninos || null };
const anteriores = (a.anteriores || []).map(x => `- ${x.destino || 'destino no definido'}${x.fecha_salida ? ' (salida ' + x.fecha_salida + ')' : ''}, etapa: ${x.etapa}`).join('\n') || 'ninguno';

const system = `Eres Lucía, asesora virtual de viajes de "${CFG.agencia}", agencia de viajes en México. Hoy es ${a.hoy} (hora de Ciudad de México).
Destinos principales: playas de México (Ixtapa, Cancún, Puerto Vallarta, Los Cabos), Colombia y Latinoamérica, Estados Unidos, Disney, Europa y Japón; también cruceros, tours y paquetes a la medida.

PERSONALIDAD: cercana, cálida y profesional. Tuteas al cliente. Incluye 1 o 2 emojis de viajes en cada mensaje (✈️🌴🏖️🧳🌎🗺️🏨☀️). Mensajes cortos (máximo 5 líneas; si describes promos puedes usar viñetas), una o dos preguntas por mensaje. Solo español. Saluda con "¡Hola!" solo en el primer mensaje de la conversación.

TU ÚNICA MISIÓN es recopilar los datos para que una asesora de ventas prepare la cotización:
1. Destino
2. Fechas de viaje (salida y regreso). Pregunta UNA sola vez si tiene fechas estimadas; si no sabe o no quiere dar fechas, NO insistas: marca fechas_sin_definir=true.
3. Número de adultos
4. Número de niños (0 si no viajan niños)
5. Edad de cada niño (solo si viajan niños)
No pidas nombre, teléfono ni correo. No preguntes presupuesto, hotel ni otros datos.

PROMOCIONES (reglas estrictas):
- Solo puedes dar precios de las promociones ACTIVAS listadas abajo, copiando los datos tal cual (precio, para cuántas personas, qué incluye, fechas y días en que aplica, precios de menores, condiciones).
- Cada vez que menciones una promo incluye SIEMPRE: el precio y a qué corresponde (por ejemplo "por habitación para 2 adultos"), las fechas o días en que aplica (por ejemplo, si es de lunes a jueves, aclara que en fin de semana el precio cambia), los precios o condiciones para menores si los hay, y la frase "sujeto a disponibilidad".
- NUNCA calcules totales, NUNCA inventes precios, descuentos, disponibilidad ni promociones. Para cualquier otro precio di que una asesora le enviará su cotización personalizada.
- Si el cliente viene de un anuncio con promo vigente, preséntale esa promo al inicio y luego pide los datos que falten.
- Si la promo del anuncio ya terminó, díselo con amabilidad y ofrécele hasta 3 promos vigentes del mismo destino (o, si no hay, hasta 3 promos vigentes de otros destinos, si existen).
- Si el cliente pregunta por un destino que tiene promos vigentes, puedes mencionarlas (máximo 3).
- Si el primer mensaje es genérico ("info", "precio", "me interesa", un comentario de un video), pregunta amablemente qué destino o promoción le interesa.

PASAR A HUMANO (escalar=true) si: el cliente está molesto o se queja, pide hablar con una persona, pregunta por visas o requisitos migratorios específicos, quiere cambiar/cancelar/pagar una reservación existente, o pide algo que no puedes resolver. En ese caso responde con calidez que una asesora le atenderá personalmente en breve.

CUANDO TENGAS TODOS LOS DATOS: confirma con un resumen breve (destino, fechas, adultos, niños y edades) y dile que una asesora le enviará su cotización muy pronto (horario de atención: lunes a viernes 9:00 a 18:00 y sábados 10:00 a 14:00). No hagas más preguntas.

CLIENTE RECURRENTE: si tiene viajes anteriores, salúdalo con gusto de volver a atenderlo y menciona su viaje anterior de forma natural (por ejemplo, "¿Qué tal te fue en Cancún?").

FECHAS: convierte fechas relativas a formato AAAA-MM-DD usando la fecha de hoy. Si no dice el año, usa la próxima vez que ocurra esa fecha. Si solo da un mes o una temporada ("en diciembre", "Semana Santa"), guárdalo en fechas_texto.

FORMATO DEL CAMPO "respuesta": texto listo para WhatsApp, cálido, con 1 o 2 emojis de viajes, sin firmar.

Devuelve SIEMPRE el estado COMPLETO de los datos (los ya registrados más lo nuevo). Si el cliente corrige algo, usa lo más reciente.

DATOS YA REGISTRADOS: ${JSON.stringify(datos)}
NOMBRE DEL CLIENTE: ${a.nombre || 'desconocido'}
VIAJES ANTERIORES DEL CLIENTE:
${anteriores}
PROMO DEL ANUNCIO POR EL QUE LLEGÓ: ${fmtPromo(a.promo_anuncio)}
${a.promo_vencida ? 'PROMO DEL ANUNCIO YA TERMINADA: ' + a.promo_vencida.titulo + ' (' + a.promo_vencida.destino + ')' : ''}
PROMOCIONES ACTIVAS HOY:
${(a.promos || []).map(fmtPromo).join('\n') || 'No hay promociones activas.'}`;

const messages = [{ role: 'system', content: system }];
for (const h of a.historial) messages.push({ role: h.rol, content: h.texto.slice(0, 2000) });
let texto = a.nuevos.map(n => n.body).filter(Boolean).join('\n');
if (a.transcripciones.length) texto += '\n[Nota de voz transcrita]: ' + a.transcripciones.join(' ');
if (a.audios.length && !a.transcripciones.length) texto += '\n[El cliente envió una nota de voz que no se pudo escuchar; pídele amablemente que lo escriba]';
if (a.imagenes.length) texto += '\n[El cliente envió ' + a.imagenes.length + ' imagen(es); si es un anuncio o captura, identifica la promo o destino]';
if (a.otros.length) texto += '\n[El cliente envió un archivo adjunto]';
const content = [{ type: 'text', text: texto.trim() || '(mensaje sin texto)' }];
for (const u of a.imagenes.slice(0, 3)) content.push({ type: 'image_url', image_url: { url: u } });
messages.push({ role: 'user', content });

const N = t => ({ type: [t, 'null'] });
const schema = { type: 'object', additionalProperties: false,
  required: ['respuesta','destino','fecha_salida','fecha_regreso','fechas_texto','fechas_sin_definir','adultos','ninos','edades_ninos','promo_id','escalar','motivo_escalado','resumen'],
  properties: { respuesta: { type: 'string' }, destino: N('string'), fecha_salida: N('string'), fecha_regreso: N('string'),
    fechas_texto: N('string'), fechas_sin_definir: { type: 'boolean' }, adultos: N('integer'), ninos: N('integer'),
    edades_ninos: { type: ['array', 'null'], items: { type: 'integer' } }, promo_id: N('string'),
    escalar: { type: 'boolean' }, motivo_escalado: N('string'),
    resumen: { type: 'string', description: 'Resumen de 1-2 líneas del interés del cliente para la asesora' } } };

return [{ json: { ...a, request: { model: CFG.modelo, temperature: 0.4, messages,
  response_format: { type: 'json_schema', json_schema: { name: 'turno_lucia', strict: true, schema } } } } }];
""", (X + 3960, Y))
    wf.link("¿Trae audios?", "Preparar prompt", 1)
    wf.link("Unir transcripciones", "Preparar prompt")
    openai(wf, "OpenAI Lucía", "$json.request", (X + 4180, Y))

    code(wf, "Procesar respuesta", CFG_JS + JS_FECHAS + r"""
const a = $('Preparar prompt').first().json;
let r;
const resp = $input.first().json;
try { r = JSON.parse(resp.choices[0].message.content); } catch (e) { throw new Error('Respuesta de OpenAI inválida: ' + JSON.stringify(resp).slice(0, 500)); }
const prev = a.lead_actual || {};
const v = (x, y) => (x === null || x === undefined || x === '') ? (y ?? null) : x;
const iso = s => (s && /^\d{4}-\d{2}-\d{2}$/.test(s)) ? s : null;
const d = {
  destino: v(r.destino, prev.destino), fecha_salida: iso(v(r.fecha_salida, prev.fecha_salida)),
  fecha_regreso: iso(v(r.fecha_regreso, prev.fecha_regreso)), fechas_texto: v(r.fechas_texto, prev.fechas_texto),
  fechas_sin_definir: !!(r.fechas_sin_definir || prev.fechas_sin_definir), adultos: v(r.adultos, prev.adultos),
  ninos: v(r.ninos, prev.ninos), edades_ninos: (r.edades_ninos && r.edades_ninos.length) ? r.edades_ninos : (prev.edades_ninos || null),
};
if (d.ninos === 0) d.edades_ninos = [];
const promoId = v(r.promo_id, prev.promo_id) || (a.promo_anuncio && a.promo_anuncio.id) || null;
const promo = (a.promos || []).find(p => p.id === promoId) || null;

// Completitud (regla de negocio, no depende del modelo)
const falta = [];
if (!d.destino) falta.push('destino');
if (!(d.fecha_salida || d.fechas_texto || d.fechas_sin_definir)) falta.push('fechas');
if (!(d.adultos >= 1)) falta.push('adultos');
if (d.ninos === null || d.ninos === undefined) falta.push('niños');
else if (d.ninos > 0 && !(d.edades_ninos && d.edades_ninos.length >= d.ninos)) falta.push('edades de los niños');
const escalar = !!r.escalar;
const completo = !falta.length && !escalar;
const dias = d.fecha_salida ? diasEntre(a.hoy, d.fecha_salida) : null;
const urgente = completo && dias !== null && dias >= 0 && dias < 15;
const etapa = escalar ? 'humano' : completo ? (urgente ? 'urgente' : 'completos') : 'nuevo';
const stageId = CFG.S[etapa];

const F = CFG.F, cf = [];
const put = (k, val) => { if (F[k] && val !== null && val !== undefined && val !== '') cf.push({ id: F[k], field_value: val }); };
put('IA Destino', d.destino); put('IA Fecha salida', d.fecha_salida); put('IA Fecha regreso', d.fecha_regreso);
put('IA Fechas (texto)', d.fechas_texto || (d.fechas_sin_definir ? 'Sin fechas definidas' : null));
put('IA Adultos', d.adultos); put('IA Niños', d.ninos);
put('IA Edades niños', d.ninos > 0 ? (d.edades_ninos || []).join(', ') : (d.ninos === 0 ? 'N/A' : null));
put('IA Promo de interés', promo ? `${promo.titulo} (${promo.id})` : null); put('IA Ad ID', a.ad_id);
put('IA Canal de origen', a.canal); put('IA Viaja en menos de 15 días', completo ? (urgente ? 'Sí' : 'No') : null);
put('IA Resumen conversación', [r.resumen, escalar && r.motivo_escalado ? 'ESCALADO: ' + r.motivo_escalado : null].filter(Boolean).join('\n'));

const tags = ['lucia'];
if (completo) tags.push('datos-completos');
if (urgente) tags.push('urgente-15-dias');
if (escalar) tags.push('escalado-humano', 'ia-pausada');
const nuevaOpp = !a.opportunity_id;
if (nuevaOpp && (a.anteriores || []).length) tags.push('cliente-recurrente');
const quitar = nuevaOpp ? ['datos-completos', 'urgente-15-dias', 'escalado-humano', 'cotizacion-enviada'] : [];

let respuesta = (r.respuesta || '').trim();
if (completo && !(prev.datos_completos)) {
  // Quitar preguntas finales y cerrar con el mensaje estándar
  const partes = respuesta.split(/(?<=[.!?])\s+/);
  while (partes.length && /\?\s*\S{0,3}$/.test(partes[partes.length - 1])) partes.pop();
  respuesta = (partes.join(' ').trim() + '\n\n✅ ¡Listo! Ya tengo todo lo necesario. Una de nuestras asesoras te enviará tu cotización muy pronto ✈️ (horario: lunes a viernes 9:00–18:00 y sábados 10:00–14:00).').trim();
}
const nombreOpp = `${a.nombre_completo || a.nombre || 'Cliente'} – ${d.destino || 'Viaje'}`;
const oppBody = nuevaOpp
  ? { pipelineId: CFG.pipelineId, locationId: CFG.locationId, contactId: a.contact_id, name: nombreOpp, status: 'open', pipelineStageId: stageId }
  : { pipelineStageId: stageId, name: nombreOpp };

return [{ json: { contact_id: a.contact_id, canal: a.canal, respuesta,
  datos: d, falta, completo, urgente, escalar, etapa, stage_id: stageId, promo_id: promo ? promo.id : null,
  custom_fields: cf, tags, quitar, opp_method: nuevaOpp ? 'POST' : 'PUT',
  opp_url: nuevaOpp ? '/opportunities/' : '/opportunities/' + a.opportunity_id, opp_body: oppBody,
  resumen: r.resumen, motivo_escalado: r.motivo_escalado, procesado_hasta: a.procesado_hasta,
  conversation_id: a.conversation_id, nombre: a.nombre_completo || a.nombre, telefono: a.telefono, ad_id: a.ad_id } }];
""", (X + 4400, Y))

    wf.add("GHL oportunidad (crear/mover)", "n8n-nodes-base.httpRequest", 4.2, {
        "method": "={{ $json.opp_method }}", "url": "=" + GHL + "{{ $json.opp_url }}",
        "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
        "sendHeaders": True, "headerParameters": {"parameters": [{"name": "Version", "value": "2021-07-28"}]},
        "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.opp_body) }}",
        "options": {}}, (X + 4620, Y), CRED_GHL)
    P = "$('Procesar respuesta').item.json"
    ghl(wf, "GHL enviar respuesta", "POST", "/conversations/messages", (X + 4840, Y),
        body_expr="{ type: " + P + ".canal, contactId: " + P + ".contact_id, message: " + P + ".respuesta }",
        **CONTINUAR)
    ghl(wf, "GHL guardar campos", "PUT", "/contacts/{{ $('Procesar respuesta').item.json.contact_id }}", (X + 5060, Y),
        body_expr="{ customFields: " + P + ".custom_fields }", **CONTINUAR)
    ghl(wf, "GHL quitar tags viejos", "DELETE", "/contacts/{{ $('Procesar respuesta').item.json.contact_id }}/tags",
        (X + 5280, Y), body_expr="{ tags: " + P + ".quitar.length ? " + P + ".quitar : ['-'] }", **CONTINUAR)
    ghl(wf, "GHL agregar tags", "POST", "/contacts/{{ $('Procesar respuesta').item.json.contact_id }}/tags",
        (X + 5500, Y), body_expr="{ tags: " + P + ".tags }", **CONTINUAR)
    rpc(wf, "SB guardar turno", "viajes_guardar_turno", "{ p: { ..." + P + ".datos, contact_id: " + P + ".contact_id, "
        "opportunity_id: $('GHL oportunidad (crear/mover)').item.json.opportunity?.id || $('GHL oportunidad (crear/mover)').item.json.id, "
        "nombre: " + P + ".nombre, telefono: " + P + ".telefono, canal: " + P + ".canal, "
        "conversation_id: " + P + ".conversation_id, procesado_hasta: " + P + ".procesado_hasta, "
        "ad_id: " + P + ".ad_id, promo_id: " + P + ".promo_id, datos_completos: " + P + ".completo, "
        "urgente: " + P + ".urgente, etapa: " + P + ".etapa, resumen: " + P + ".resumen, escalar: " + P + ".escalar, "
        "respuesta_enviada: !$('GHL enviar respuesta').item.json.error } }", (X + 5720, Y))
    if_(wf, "¿Recién completado?", "$json.recien_completado", (X + 5940, Y))
    code(wf, "Fila reporte Leads", r"""
const p = $('Procesar respuesta').first().json, d = p.datos;
return [{ json: {
  fecha_registro: new Date(Date.now() - 6 * 3600e3).toISOString().replace('T', ' ').slice(0, 16),
  ghl_contact_id: p.contact_id, nombre: p.nombre, telefono: p.telefono, canal: p.canal, destino: d.destino,
  fecha_salida: d.fecha_salida || '', fecha_regreso: d.fecha_regreso || '',
  fechas_texto: d.fechas_texto || (d.fechas_sin_definir ? 'Sin fechas definidas' : ''),
  adultos: d.adultos, ninos: d.ninos, edades_ninos: (d.edades_ninos || []).join(', '),
  promo_id: p.promo_id || '', ad_id: p.ad_id || '', urgente: p.urgente ? 'Sí' : 'No', etapa: p.etapa, resumen_ia: p.resumen || '' } }];
""", (X + 6160, Y - 100))
    wf.add("Sheets agregar lead", "n8n-nodes-base.googleSheets", 4.6, {
        "operation": "append",
        "documentId": {"__rl": True, "value": SHEET_ID, "mode": "id"},
        "sheetName": {"__rl": True, "value": "Leads", "mode": "name"},
        "columns": {"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [], "schema": []},
        "options": {}}, (X + 6380, Y - 100), CRED_SHEETS, **CONTINUAR)

    wf.chain("Mensaje entrante GHL", "Normalizar entrada", "SB registrar mensaje", "Esperar ráfaga (15 s)",
             "SB ¿es el último?", "¿Último mensaje?")
    wf.link("¿Último mensaje?", "GHL contacto", 0)
    wf.chain("GHL contacto", "GHL oportunidades", "GHL conversación", "GHL mensajes", "SB contexto", "Analizar", "Acción")
    wf.chain("Preparar prompt", "OpenAI Lucía", "Procesar respuesta", "GHL oportunidad (crear/mover)",
             "GHL enviar respuesta", "GHL guardar campos", "GHL quitar tags viejos", "GHL agregar tags",
             "SB guardar turno", "¿Recién completado?")
    wf.link("¿Recién completado?", "Fila reporte Leads", 0)
    wf.link("Fila reporte Leads", "Sheets agregar lead")
    return wf


# ============================================================== 2. SYNC PROMOS
def wf_promos():
    wf = WF("Lucía – Sincronizar promos (Sheets → Supabase)")
    wf.add("Cada 15 minutos", "n8n-nodes-base.scheduleTrigger", 1.2,
           {"rule": {"interval": [{"field": "minutes", "minutesInterval": 15}]}}, (0, 300))
    wf.add("Leer promos del Sheet", "n8n-nodes-base.googleSheets", 4.6, {
        "documentId": {"__rl": True, "value": SHEET_ID, "mode": "id"},
        "sheetName": {"__rl": True, "value": "Promos", "mode": "name"},
        "options": {"outputFormatting": {"values": {"general": "UNFORMATTED_VALUE", "date": "SERIAL_NUMBER"}}}},
        (220, 300), CRED_SHEETS, alwaysOutputData=True)
    code(wf, "Normalizar filas", r"""
function fecha(v) {
  if (v === null || v === undefined || v === '') return null;
  if (typeof v === 'number') return new Date(Date.UTC(1899, 11, 30) + v * 864e5).toISOString().slice(0, 10);
  const s = String(v).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10);
  const m = s.match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2,4})$/);
  if (m) { const y = m[3].length === 2 ? '20' + m[3] : m[3]; return `${y}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}`; }
  return null;
}
const F = ['vigencia_desde', 'vigencia_hasta', 'viaje_desde', 'viaje_hasta'];
const rows = $input.all().map(i => i.json).filter(r => r && String(r.id_promo || '').trim())
  .map(r => { const o = {}; for (const [k, v] of Object.entries(r)) o[k.trim()] = (v === null || v === undefined) ? '' : String(v);
    for (const f of F) o[f] = fecha(r[f]) || ''; return o; });
return [{ json: { rows } }];
""", (440, 300))
    rpc(wf, "SB sincronizar promos", "viajes_sync_promos", "{ p_rows: $json.rows }", (660, 300))
    wf.chain("Cada 15 minutos", "Leer promos del Sheet", "Normalizar filas", "SB sincronizar promos")
    return wf


# ============================================================== 3. SEGUIMIENTOS Y RECORDATORIOS
def wf_motor():
    wf = WF("Lucía – Seguimientos y recordatorios (Agencia Prueba)")
    wf.add("Cada 15 minutos", "n8n-nodes-base.scheduleTrigger", 1.2,
           {"rule": {"interval": [{"field": "minutes", "minutesInterval": 15}]}}, (0, 600))

    # ---- A. Programar seguimientos de cotización
    ghl(wf, "GHL opps en Cotización enviada", "GET", "/opportunities/search", (220, 0),
        query=[("location_id", CFG["locationId"]), ("pipeline_id", CFG["pipelineId"]),
               ("pipeline_stage_id", S["cotizacion"]), ("status", "open"), ("limit", "100")])
    code(wf, "Series de cotización", r"""
const opps = $input.first().json.opportunities || [];
const items = opps.map(o => ({ contact_id: o.contactId || (o.contact && o.contact.id), opportunity_id: o.id,
  desde: o.lastStageChangeAt || o.updatedAt || o.createdAt, nombre: (o.contact && o.contact.name) || o.name }))
  .filter(x => x.contact_id);
return [{ json: { items } }];
""", (440, 0))
    rpc(wf, "SB programar cotización", "viajes_programar_cotizacion", "{ p_items: $json.items }", (660, 0))
    wf.link("Cada 15 minutos", "GHL opps en Cotización enviada")
    wf.chain("GHL opps en Cotización enviada", "Series de cotización", "SB programar cotización")

    # ---- B. Recordatorios de pago y de viaje
    ghl(wf, "GHL opps abiertas", "GET", "/opportunities/search", (220, 300),
        query=[("location_id", CFG["locationId"]), ("pipeline_id", CFG["pipelineId"]),
               ("status", "open"), ("limit", "100")])
    code(wf, "Filtrar pagos y viajes", CFG_JS + r"""
const opps = ($input.first().json.opportunities || []).filter(o => [CFG.S.apartado, CFG.S.pagado].includes(o.pipelineStageId));
return opps.map(o => ({ json: { contact_id: o.contactId || (o.contact && o.contact.id), opportunity_id: o.id,
  stage_id: o.pipelineStageId, nombre: (o.contact && o.contact.name) || o.name } })).filter(i => i.json.contact_id);
""", (440, 300))
    ghl(wf, "GHL contacto (recordatorios)", "GET", "/contacts/{{ $json.contact_id }}", (660, 300), **CONTINUAR)
    code(wf, "Armar recordatorios", CFG_JS + JS_FECHAS + r"""
const base = $('Filtrar pagos y viajes').all().map(i => i.json);
const out = { contactos: [], items: [], completar: [] };
const hoy = hoyCdmx();
$input.all().forEach((it, i) => {
  const o = base[i]; const c = it.json.contact; if (!o || !c) return;
  const val = {}; for (const f of (c.customFields || [])) val[f.id] = f.value;
  const g = n => val[CFG.F[n]];
  out.contactos.push(o.contact_id);
  const etapa = o.stage_id === CFG.S.pagado ? 'pagado' : 'apartado';
  for (let n = 1; n <= 6; n++) {
    const fecha = fechaCampo(g(`Pago ${n} - Fecha límite`));
    const estatus = String(g(`Pago ${n} - Estatus`) || '').toLowerCase();
    if (fecha && estatus !== 'pagado') out.items.push({ contact_id: o.contact_id, opportunity_id: o.opportunity_id,
      nombre: o.nombre, etapa, tipo: 'pago', referencia: `Pago ${n}`, fecha });
  }
  const salida = fechaCampo(g('Viaje Fecha salida'));
  if (salida) out.items.push({ contact_id: o.contact_id, opportunity_id: o.opportunity_id, nombre: o.nombre, etapa,
    tipo: 'viaje', referencia: 'viaje', fecha: salida });
  const regreso = fechaCampo(g('Viaje Fecha regreso'));
  if (o.stage_id === CFG.S.pagado && regreso && regreso < hoy) out.completar.push(o.opportunity_id);
});
return [{ json: out }];
""", (880, 300))
    rpc(wf, "SB sincronizar recordatorios", "viajes_sync_recordatorios",
        "{ p_contactos: $json.contactos, p_items: $json.items }", (1100, 300))
    code(wf, "Viajes terminados", "return ($('Armar recordatorios').first().json.completar || []).map(id => ({ json: { opportunity_id: id } }));",
         (1320, 300))
    ghl(wf, "GHL mover a Viaje completado", "PUT", "/opportunities/{{ $json.opportunity_id }}", (1540, 300),
        body_expr="{ pipelineStageId: '" + S["completado"] + "' }", **CONTINUAR)
    wf.link("Cada 15 minutos", "GHL opps abiertas")
    wf.chain("GHL opps abiertas", "Filtrar pagos y viajes", "GHL contacto (recordatorios)", "Armar recordatorios",
             "SB sincronizar recordatorios", "Viajes terminados", "GHL mover a Viaje completado")

    # ---- C. Enviar lo que toca
    Y = 700
    code(wf, "¿Horario hábil?", r"""
const d = new Date(Date.now() - 6 * 3600e3); const dia = d.getUTCDay(), h = d.getUTCHours() + d.getUTCMinutes() / 60;
const abierto = __FORZAR__ || (dia >= 1 && dia <= 5 && h >= 9 && h < 18) || (dia === 6 && h >= 10 && h < 14);
return abierto ? [{ json: { abierto } }] : [];
""", (220, Y))
    rpc(wf, "SB tomar pendientes", "viajes_tomar_pendientes", "{ p_limit: 25 }", (440, Y))
    code(wf, "Quitar vacíos", "return $input.all().filter(i => i.json && i.json.id);", (550, Y + 120))
    ghl(wf, "GHL contacto (envío)", "GET", "/contacts/{{ $json.contact_id }}", (660, Y), **CONTINUAR)
    ghl(wf, "GHL oportunidad (envío)", "GET",
        "/opportunities/{{ $('Quitar vacíos').item.json.opportunity_id || 'sin-oportunidad' }}", (880, Y), **CONTINUAR)
    code(wf, "Decidir envío", CFG_JS + JS_FECHAS + r"""
const p = $('Quitar vacíos').item.json;
const c = $('GHL contacto (envío)').item.json.contact || null;
const o = $json.opportunity || null;
const val = {}; for (const f of ((c && c.customFields) || [])) val[f.id] = f.value;
const g = n => { const v = val[CFG.F[n]]; return (v === undefined || v === null) ? '' : String(v).trim(); };
const tags = ((c && c.tags) || []).map(t => String(t).toLowerCase());
const stage = o && o.status === 'open' ? o.pipelineStageId : null;
const nombre = (c && (c.firstName || c.contactName)) || p.nombre || '';
const r = { tabla: p.tabla, id: p.id, lead_id: p.lead_id, contact_id: p.contact_id, tipo: p.tipo, numero: p.numero,
  canal: p.canal || 'WhatsApp', opportunity_id: p.opportunity_id, assigned_to: (o && o.assignedTo) || null,
  nombre, accion: 'cancelar', estado: 'cancelado', error: null, texto: '', nueva_etapa: null, etapa: null };
const cancelar = motivo => { r.error = motivo; return { json: r }; };
if (!c) return cancelar('contacto no encontrado');

if (p.tabla === 'seguimiento') {
  if (tags.includes('seguimiento-pausado')) return cancelar('seguimientos pausados por la vendedora');
  if (p.tipo === 'datos') {
    if (![CFG.S.nuevo, CFG.S.incompletos].includes(stage)) return cancelar('el lead ya no está recopilando datos');
    if (tags.includes('ia-pausada')) return cancelar('IA pausada');
    if (p.numero === 99) { r.accion = 'mover'; r.estado = 'enviado'; r.texto = '(sin respuesta: movido a Perdido / frío)';
      r.nueva_etapa = CFG.S.perdido; r.etapa = 'perdido'; return { json: r }; }
    if (p.numero === 1) { r.nueva_etapa = CFG.S.incompletos; r.etapa = 'datos_incompletos'; }
  } else if (stage !== CFG.S.cotizacion) return cancelar('el lead ya no está en Cotización enviada');
  const l = p.lead || {};
  const falta = [];
  if (!l.destino) falta.push('destino');
  if (!(l.fecha_salida || l.fechas_texto || l.fechas_sin_definir)) falta.push('fechas aproximadas');
  if (!l.adultos) falta.push('cuántos adultos viajan');
  if (l.ninos === null || l.ninos === undefined) falta.push('si viajan niños');
  else if (l.ninos > 0 && !((l.edades_ninos || []).length >= l.ninos)) falta.push('edades de los niños');
  r.accion = 'ia';
  r.contexto = p.tipo === 'datos'
    ? { datos: { destino: l.destino, fecha_salida: l.fecha_salida, fechas_texto: l.fechas_texto, adultos: l.adultos, ninos: l.ninos, edades_ninos: l.edades_ninos }, falta }
    : { cotizacion: { destino: g('Cot Destino') || l.destino, hotel: g('Cot Hotel'), plan: g('Cot Plan de alimentos'),
        monto_total_mxn: g('Cot Monto total MXN'), incluye: g('Cot Incluye'), vendedora: g('Cot Vendedora'),
        vigencia: fechaCampo(g('Cot Vigencia')) } };
  return { json: r };
}

// ---- Recordatorios
if (![CFG.S.apartado, CFG.S.pagado].includes(stage)) return cancelar('la oportunidad ya no está en pagos/viaje');
const evento = new Date(new Date(p.fecha_evento).getTime() - 6 * 3600e3).toISOString().slice(0, 10);
const cuando = diasEntre(hoyCdmx(), evento) === 1 ? 'mañana' : 'el ' + fechaLarga(evento);
if (p.tipo === 'pago') {
  const n = (p.referencia || '').replace(/\D/g, '');
  if (String(g(`Pago ${n} - Estatus`)).toLowerCase() === 'pagado') return cancelar('pago ya marcado como Pagado');
  const monto = Number(g(`Pago ${n} - Monto MXN`) || 0);
  const destino = g('Viaje Destino') || g('Cot Destino') || (p.lead && p.lead.destino) || 'tu viaje';
  r.texto = `¡Hola${nombre ? ' ' + nombre : ''}! 👋 Te recuerdo que ${cuando} vence tu ${p.referencia.toLowerCase()}` +
    (monto ? ` por $${monto.toLocaleString('es-MX')} MXN` : '') + ` de tu viaje a ${destino} 🧳✨\n` +
    `Si ya lo realizaste, compártenos tu comprobante por aquí para registrarlo 🙌 ¡Gracias!`;
} else {
  const L = [];
  const add = (e, t, v) => { if (v) L.push(`${e} ${t}: ${v}`); };
  const destino = g('Viaje Destino') || g('Cot Destino') || (p.lead && p.lead.destino) || '';
  add('🏨', 'Hotel', g('Viaje Hotel'));
  const ci = fechaCampo(g('Viaje Check-in')), co = fechaCampo(g('Viaje Check-out'));
  if (ci || co) L.push(`📅 Check-in: ${ci ? fechaLarga(ci) : '-'} | Check-out: ${co ? fechaLarga(co) : '-'}`);
  add('🔖', 'Confirmación del hotel', g('Viaje Confirmación hotel'));
  add('🍽️', 'Plan', g('Viaje Plan de alimentos'));
  add('🛏️', 'Habitaciones', g('Viaje Habitaciones'));
  add('👥', 'Pasajeros', g('Viaje Pasajeros'));
  for (const tramo of ['Ida', 'Regreso']) {
    const vs = [];
    for (let i = 1; i <= 3; i++) {
      const pre = `${tramo} V${i} - `; const a = g(pre + 'Aerolínea y número'), ru = g(pre + 'Ruta (origen → destino)');
      const s = g(pre + 'Salida (fecha y hora)'), ll = g(pre + 'Llegada (fecha y hora)');
      if (a || ru || s) vs.push(`   ${i}. ${[a, ru].filter(Boolean).join(' · ')}${s ? ' | Sale: ' + s : ''}${ll ? ' | Llega: ' + ll : ''}`);
    }
    if (vs.length) L.push(`✈️ Vuelo${vs.length > 1 ? 's' : ''} de ${tramo.toLowerCase()}:\n` + vs.join('\n'));
    add('🔑', `Clave de reservación (${tramo.toLowerCase()})`, g(`${tramo} - Clave de reservación`));
  }
  add('🧳', 'Equipaje', g('Vuelos - Equipaje incluido'));
  add('🚐', 'Traslados', g('Viaje Traslados'));
  add('🎟️', 'Tours y extras', g('Viaje Tours y extras'));
  add('🛡️', 'Seguro de viaje', g('Viaje Seguro'));
  add('📝', 'Notas', g('Viaje Notas para el cliente'));
  const hayVuelo = L.some(x => x.startsWith('✈️'));
  r.texto = `¡Hola${nombre ? ' ' + nombre : ''}! 🌴 ${cuando.charAt(0).toUpperCase() + cuando.slice(1)} comienza tu viaje${destino ? ' a ' + destino : ''} ✈️\nAquí tienes el resumen de tu viaje:\n\n` +
    (L.join('\n') || 'Tu asesora te compartirá los detalles finales.') +
    `\n\n✅ Lleva tu identificación oficial${hayVuelo ? ' (pasaporte vigente si es internacional) y llega al aeropuerto con 2 horas de anticipación (3 horas en vuelos internacionales)' : ''}.\n¡Te deseamos un viaje increíble! 🧳✨`;
}
r.accion = 'plantilla';
return { json: r };
""", (1100, Y), each=True)
    switch(wf, "Tipo de envío", "$json.accion", ["ia", "plantilla", "mover", "cancelar"], (1320, Y))

    # IA: generar texto del seguimiento
    ghl(wf, "GHL conversación (seg)", "GET", "/conversations/search", (1540, Y - 200),
        query=[("locationId", CFG["locationId"]), ("contactId", "={{ $json.contact_id }}"), ("limit", "1")], **CONTINUAR)
    ghl(wf, "GHL mensajes (seg)", "GET",
        "/conversations/{{ ($json.conversations || [])[0]?.id || 'sin-conversacion' }}/messages", (1760, Y - 200),
        query=[("limit", "20")], **CONTINUAR)
    code(wf, "Prompt seguimiento", CFG_JS + r"""
const r = $('Decidir envío').item.json;
let msgs = []; try { const m = $json.messages; msgs = (m && (m.messages || m)) || []; } catch (e) {}
if (!Array.isArray(msgs)) msgs = [];
const hist = msgs.filter(m => m.body && /WHATSAPP|INSTAGRAM|FACEBOOK|SMS|CHAT|TIKTOK/.test(m.messageType || ''))
  .sort((a, b) => new Date(a.dateAdded) - new Date(b.dateAdded)).slice(-12)
  .map(m => `${m.direction === 'inbound' ? 'Cliente' : 'Agencia'}: ${m.body.slice(0, 500)}`).join('\n');
const guia = r.tipo === 'datos'
  ? `Es el seguimiento ${r.numero} de 3 a un cliente que dejó de responder mientras recopilábamos sus datos de viaje. Datos que faltan: ${r.contexto.falta.join(', ') || 'ninguno'}. Datos que ya tenemos: ${JSON.stringify(r.contexto.datos)}. Retoma la conversación de forma natural y pide lo que falta.${r.numero === 3 ? ' Es el último seguimiento: cierra con amabilidad diciendo que aquí estaremos cuando quiera retomar.' : ''}`
  : `Es el seguimiento ${r.numero} de 4 a un cliente al que su asesora ya le envió una cotización y no ha respondido. Datos de la cotización: ${JSON.stringify(r.contexto.cotizacion)}. ${['Pregunta con amabilidad si pudo revisar su cotización.', 'Pregunta si tiene dudas o si quiere ajustar algo (fechas, hotel, número de personas).', 'Menciona que los precios y la disponibilidad pueden cambiar pronto, sin presionar.', 'Último seguimiento: ofrece opciones alternativas si la cotización no le convenció y deja la puerta abierta.'][r.numero - 1] || ''}`;
const system = `Eres Lucía, del equipo de "${CFG.agencia}", agencia de viajes en México. Tono cercano, tuteas, usas 1 o 2 emojis de viajes. Solo español. Escribe ÚNICAMENTE el texto del mensaje de WhatsApp (máximo 3 líneas), sin comillas ni explicaciones. No inventes precios, disponibilidad ni datos que no estén aquí. No repitas textualmente mensajes anteriores.`;
return { json: { ...r, request: { model: CFG.modelo, temperature: 0.7, messages: [
  { role: 'system', content: system },
  { role: 'user', content: `Nombre del cliente: ${r.nombre || 'desconocido'}\n${guia}\n\nÚltimos mensajes de la conversación:\n${hist || '(sin historial)'}` } ] } } };
""", (1980, Y - 200), each=True)
    openai(wf, "OpenAI seguimiento", "$json.request", (2200, Y - 200), **CONTINUAR)
    code(wf, "Texto IA", r"""
const r = $('Prompt seguimiento').item.json;
const t = (($json.choices || [])[0]?.message?.content || '').trim().replace(/^"|"$/g, '');
const { request, ...resto } = r;
if (!t) return { json: { ...resto, accion: 'error', estado: 'fallido', error: 'OpenAI no generó texto' } };
return { json: { ...resto, texto: t } };
""", (2420, Y - 200), each=True)
    if_(wf, "¿Hay texto?", "!!$json.texto", (2640, Y - 200))

    ghl(wf, "GHL enviar mensaje", "POST", "/conversations/messages", (2860, Y),
        body_expr="{ type: $json.canal, contactId: $json.contact_id, message: $json.texto }", **CONTINUAR)
    wf.add("Esperar entrega (20 s)", "n8n-nodes-base.wait", 1.1, {"resume": "timeInterval", "amount": 20, "unit": "seconds"},
           (2970, Y + 150), webhookId=_id())
    ghl(wf, "GHL estado del mensaje", "GET", "/conversations/messages/{{ $json.messageId || 'sin-id' }}", (3000, Y + 300), **CONTINUAR)
    code(wf, "Resultado envío", r"""
const d = $('Decidir envío').item.json;
let base = null; try { base = $('Texto IA').item.json; } catch (e) {}
if (!base || base.id !== d.id) base = d;
const envio = $('GHL enviar mensaje').item.json;
const msg = ($json && $json.message) || {};
const errEnvio = envio.error ? String(envio.error.message || envio.error) : null;
const errEntrega = (String(msg.status || '').toLowerCase() === 'failed' || String(msg.status || '').toLowerCase() === 'undelivered') ? String(msg.error || msg.status) : null;
const fallo = !!(errEnvio || errEntrega);
return { json: { ...base, estado: fallo ? 'manual' : 'enviado',
  error: fallo ? ('No se pudo entregar automáticamente (' + String(errEnvio || errEntrega).slice(0, 200) + '). Se creó tarea para envío manual.') : null } };
""", (3080, Y), each=True)
    if_(wf, "¿Envío manual?", "$json.estado === 'manual'", (3300, Y))
    ghl(wf, "GHL tarea envío manual", "POST", "/contacts/{{ $json.contact_id }}/tasks", (3520, Y - 150),
        body_expr="{ title: '📲 Enviar mensaje manual (' + $json.canal + ')', body: 'Lucía no pudo enviar este mensaje automáticamente (posible ventana de 24 h de WhatsApp). Cópialo y envíalo desde el celular:\\n\\n' + $json.texto, "
                  "dueDate: new Date(Date.now() + 3600e3).toISOString(), completed: false, ...($json.assigned_to ? { assignedTo: $json.assigned_to } : {}) }",
        **CONTINUAR)
    if_(wf, "¿Mover etapa?", "!!$('Resultado envío').item.json.nueva_etapa", (3740, Y))
    ghl(wf, "GHL mover etapa", "PUT", "/opportunities/{{ $('Resultado envío').item.json.opportunity_id }}", (3960, Y - 150),
        body_expr="{ pipelineStageId: $('Resultado envío').item.json.nueva_etapa }", **CONTINUAR)
    code(wf, "Resultado final", r"""
const d = $('Decidir envío').item.json;
let r = null; try { r = $('Resultado envío').item.json; } catch (e) {}
if (!r || r.id !== d.id) { r = null; try { r = $('Texto IA').item.json; } catch (e) {} }
if (!r || r.id !== d.id) r = d;
return { json: { tabla: r.tabla, id: r.id, lead_id: r.lead_id, contact_id: r.contact_id, estado: r.estado,
  mensaje: r.texto || null, error: r.error || null, etapa: r.estado === 'enviado' ? r.etapa : null } };
""", (4180, Y), each=True)
    rpc(wf, "SB registrar resultado", "viajes_marcar_envio", "{ p_items: [$json] }", (4400, Y))
    wf.link("Resultado final", "SB registrar resultado")

    wf.link("Cada 15 minutos", "¿Horario hábil?")
    wf.chain("¿Horario hábil?", "SB tomar pendientes", "Quitar vacíos", "GHL contacto (envío)", "GHL oportunidad (envío)",
             "Decidir envío", "Tipo de envío")
    wf.link("Tipo de envío", "GHL conversación (seg)", 0)
    wf.chain("GHL conversación (seg)", "GHL mensajes (seg)", "Prompt seguimiento", "OpenAI seguimiento", "Texto IA", "¿Hay texto?")
    wf.link("¿Hay texto?", "GHL enviar mensaje", 0)
    wf.link("¿Hay texto?", "Resultado final", 1)
    wf.link("Tipo de envío", "GHL enviar mensaje", 1)
    wf.chain("GHL enviar mensaje", "Esperar entrega (20 s)", "GHL estado del mensaje", "Resultado envío", "¿Envío manual?")
    wf.link("¿Envío manual?", "GHL tarea envío manual", 0)
    wf.link("¿Envío manual?", "¿Mover etapa?", 1)
    wf.link("GHL tarea envío manual", "¿Mover etapa?")
    wf.link("¿Mover etapa?", "GHL mover etapa", 0)
    wf.link("¿Mover etapa?", "Resultado final", 1)
    wf.link("GHL mover etapa", "Resultado final")
    wf.link("Tipo de envío", "Mover (cierre)", 2)
    ghl(wf, "Mover (cierre)", "PUT", "/opportunities/{{ $json.opportunity_id }}", (1540, Y + 250),
        body_expr="{ pipelineStageId: $json.nueva_etapa }", **CONTINUAR)
    wf.link("Mover (cierre)", "Resultado final")
    wf.link("Tipo de envío", "Resultado final", 3)
    return wf


# ---------------------------------------------------------------- publicar
def publicar(wf_json):
    base, key = os.environ["N8N_API_URL"].rstrip("/"), os.environ["N8N_API_KEY"]
    H = {"X-N8N-API-KEY": key, "Content-Type": "application/json", "User-Agent": "curl/8"}

    def call(method, path, body=None):
        req = urllib.request.Request(base + "/api/v1" + path, method=method, headers=H,
                                     data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            raise SystemExit(f"{method} {path} -> {e.code} {e.read().decode()[:500]}")

    existentes = call("GET", "/workflows?limit=250")["data"]
    previo = next((w for w in existentes if w["name"] == wf_json["name"]), None)
    if previo:
        # conservar los webhookId existentes para no cambiar la URL del webhook
        viejos = {n["name"]: n.get("webhookId") for n in call("GET", f"/workflows/{previo['id']}")["nodes"]}
        for n in wf_json["nodes"]:
            if viejos.get(n["name"]):
                n["webhookId"] = viejos[n["name"]]
        res = call("PUT", f"/workflows/{previo['id']}", wf_json)
    else:
        res = call("POST", "/workflows", wf_json)
    return res["id"]


if __name__ == "__main__":
    FORZAR = "--forzar-horario" in sys.argv
    os.makedirs(os.path.join(AQUI, "workflows"), exist_ok=True)
    salida = {}
    for fn, archivo in [(wf_conversacion, "lucia_conversacion.json"), (wf_promos, "sync_promos.json"),
                        (wf_motor, "seguimientos_recordatorios.json")]:
        wf = fn().json()
        for n in wf["nodes"]:
            if n["type"] == "n8n-nodes-base.code":
                n["parameters"]["jsCode"] = n["parameters"]["jsCode"].replace("__FORZAR__", "true" if FORZAR else "false")
        json.dump(wf, open(os.path.join(AQUI, "workflows", archivo), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        if "--solo-json" not in sys.argv:
            salida[wf["name"]] = publicar(wf)
    print(json.dumps(salida, ensure_ascii=False, indent=2))
