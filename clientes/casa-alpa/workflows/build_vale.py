import json, uuid

SB = {"supabaseApi": {"id": "QIVohgUOAGTuwYd1", "name": "XzenAuto"}}
GHL = {"httpHeaderAuth": {"id": "Xs2385W5NO5TjT2V", "name": "GHL - PIT - Alpa"}}
OPENAI = {"openAiApi": {"id": "W5zBaQ7k25sn9YQz", "name": "RsViaje Independencia"}}
GDOCS = {"googleDocsOAuth2Api": {"id": "ORwHJE7sVAVFVhq5", "name": "Xzen_Pruebas"}}
SBURL = "https://fllhjemdhohsewqwzrpc.supabase.co/rest/v1"
GHLURL = "https://services.leadconnectorhq.com"
PIPELINE = "KRqZz6ozuHtbiISHH4Cd"
STAGES = {
    "nuevo": "b0ab308c-3935-4f75-8d77-0b123bedf5fb",
    "explorando": "eca26d5a-d2d8-4dde-a90c-f681a5e94bce",
    "handoff": "b12a3f00-b4f9-4837-9320-aa2d9ec37a2b",  # Agente personal
    "interesado": "5ae1232b-c666-4cf7-8c99-c7d767be2e50",
    "link_enviado": "461063e0-5d88-4db0-acff-b199a25eaee9",  # Cotización enviada
    "ganado": "609487d9-c097-4896-9151-1eed75d723ca",
    "perdido": "a3031a8d-94f0-401a-8f4b-d9a36b6f8cfb",
}
N = "$('Code - Normalizar Entrada').first().json"
CTX = "$('Code - Construir Contexto').first().json"

nodes, conns = [], {}


def add(name, type_, params, pos, ver=1, creds=None, **extra):
    n = {"parameters": params, "name": name, "type": type_, "typeVersion": ver, "position": pos, "id": str(uuid.uuid4())}
    if creds:
        n["credentials"] = creds
    n.update(extra)
    nodes.append(n)
    return name


def link(a, b, out=0, kind="main", inp=0):
    c = conns.setdefault(a, {}).setdefault(kind, [])
    while len(c) <= out:
        c.append([])
    c[out].append({"node": b, "type": kind, "index": inp})


def code(name, js, pos, **extra):
    return add(name, "n8n-nodes-base.code", {"jsCode": js.strip()}, pos, 2, **extra)


def http(name, method, url, pos, creds="sb", body=None, prefer=None, version=None, tool_desc=None, **extra):
    p = {"method": method, "url": url, "options": {}}
    if creds == "sb":
        p.update({"authentication": "predefinedCredentialType", "nodeCredentialType": "supabaseApi"})
        c = SB
    elif creds == "ghl":
        p.update({"authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth"})
        c = GHL
    else:
        c = None
    hdr = []
    if creds == "ghl":
        hdr += [{"name": "Version", "value": version or "2021-07-28"}, {"name": "Accept", "value": "application/json"}]
    if body is not None:
        hdr.append({"name": "Content-Type", "value": "application/json"})
    if prefer:
        hdr.append({"name": "Prefer", "value": prefer})
    if hdr:
        p["sendHeaders"] = True
        p["headerParameters"] = {"parameters": hdr}
    if body is not None:
        p["sendBody"] = True
        p["specifyBody"] = "json"
        p["jsonBody"] = body
    t = "n8n-nodes-base.httpRequest"
    if tool_desc:
        t = "n8n-nodes-base.httpRequestTool"
        p["toolDescription"] = tool_desc
    return add(name, t, p, pos, 4.2, c, **extra)


def ifnode(name, left, op, pos, right=None, typ="boolean"):
    cond = {"id": str(uuid.uuid4()), "leftValue": left, "operator": op}
    if right is not None:
        cond["rightValue"] = right
    return add(name, "n8n-nodes-base.if", {
        "conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                       "conditions": [cond], "combinator": "and"},
        "looseTypeValidation": True, "options": {}}, pos, 2.2)


TRUE_OP = {"type": "boolean", "operation": "true", "singleValue": True}

# ---------------------------------------------------------------- notas
def note(name, content, pos, w, h, color=None):
    p = {"content": content, "height": h, "width": w}
    if color:
        p["color"] = color
    add(name, "n8n-nodes-base.stickyNote", p, pos, 1)

note("Nota - Entrada", "## 1. ENTRADA\nGHL manda aquí cada mensaje entrante. Se normaliza el canal (por `message.type`: 11=FB, 18=IG, 19=WhatsApp) y se agrupan ráfagas: se guarda el mensaje, se esperan 8 s y sólo la última ejecución responde con todos los mensajes juntos.\n\n**Reset de pruebas:** escribir `Borrar` sólo funciona si el contacto tiene la etiqueta `test-vale`.", [-2200, -120], 900, 300)
note("Nota - Contexto", "## 2. CONTEXTO\nProspecto en Supabase, contacto y oportunidad en GHL, anuncio de origen, último link de pago e historial de conversación (persistente en `casa_alpa_mensajes`).\n\nVale no responde si la oportunidad está en **Agente personal** o **Cliente ganado**, o si el contacto tiene la etiqueta `vale-pausada`.", [-1100, -120], 1500, 300)
note("Nota - Agente", "## 3. VALE\nTools: `buscar_catalogo` (RPC con filtros reales y precios de Shopify), `actualizar_prospecto`, `generar_link_pago` (carrito Shopify con contact_id). Las FAQs (Google Doc) se leen una vez por mensaje y van en el contexto.\nSalida estructurada: mensajes, productos_a_mostrar (ids), etapa, handoff_motivo, resumen.", [560, -120], 700, 300)
note("Nota - Salida", "## 4. ENVÍO\nMensajes uno por uno con pausa, luego fotos de producto (datos reales desde Supabase, no del modelo).", [1360, -120], 900, 300)
note("Nota - CRM", "## 5. CRM\nGuarda etapa/resumen en Supabase, mueve la oportunidad (sólo hacia adelante; handoff siempre), pone valor cuando hay link, etiqueta y crea tarea + nota para el equipo en handoff.", [2380, -120], 1100, 300)

# ---------------------------------------------------------------- entrada
add("Webhook - Mensaje Entrante", "n8n-nodes-base.webhook",
    {"httpMethod": "POST", "path": "vale-casa-alpa", "options": {}}, [-2200, 300], 2,
    webhookId="1628655e-4fdc-41a6-81e2-3f999ae4a8ae")

code("Code - Normalizar Entrada", r"""
const b = $json.body || {};
const tipo = Number(b.message?.type);
const porTipo = { 11: 'FB', 18: 'IG', 19: 'WhatsApp', 2: 'SMS', 5: 'Live_Chat' };
const attr = b.contact?.lastAttributionSource || b.contact?.attributionSource || b.attributionSource || {};
let canal = porTipo[tipo];
if (!canal) {
  // Sin tipo: sólo es Messenger/IG si hay un PSID de página; un anuncio de Facebook que abre WhatsApp también dice medium=facebook
  if (attr.pSid && attr.medium === 'instagram') canal = 'IG';
  else if (attr.pSid && attr.medium === 'facebook') canal = 'FB';
  else canal = 'WhatsApp';
}
const tags = String(b.tags || '').toLowerCase().split(',').map(t => t.trim()).filter(Boolean);
const texto = String(b.message?.body || '').trim();
return [{ json: {
  contact_id: b.contact_id,
  nombre: b.full_name || [b.first_name, b.last_name].filter(Boolean).join(' '),
  first_name: b.first_name || '',
  telefono: b.phone || null,
  location_id: b.location?.id || 'iYgqtO9TzgsM2X4hzyhj',
  canal,
  ad_id: attr.adId || null,
  medium: attr.medium || null,
  es_test: tags.includes('test-vale'),
  texto: texto || '[El cliente mandó un audio, imagen o archivo sin texto]',
  es_borrar: texto.toLowerCase() === 'borrar'
} }];
""", [-1980, 300])

ifnode("IF - Reset de prueba", "={{ $json.es_borrar && $json.es_test }}", TRUE_OP, [-1760, 300])

# ---- reset (sólo contactos con etiqueta test-vale)
http("Reset - Buscar Opps", "GET", f"={GHLURL}/opportunities/search?location_id={{{{ $json.location_id }}}}&contact_id={{{{ $json.contact_id }}}}", [-1540, 60], "ghl", alwaysOutputData=True)
code("Reset - Lista Opps", "return ($json.opportunities || []).map(o => ({ json: { id: o.id } }));", [-1320, 60])
http("Reset - Borrar Opp", "DELETE", f"={GHLURL}/opportunities/{{{{ $json.id }}}}", [-1100, 60], "ghl", onError="continueRegularOutput")
http("Reset - Borrar Supabase", "DELETE", f"={SBURL}/casa_alpa_prospectos?contact_id=eq.{{{{ {N}.contact_id }}}}", [-1540, 200], "sb", prefer="return=minimal", executeOnce=True, alwaysOutputData=True)
http("Reset - Borrar Mensajes", "DELETE", f"={SBURL}/casa_alpa_mensajes?contact_id=eq.{{{{ {N}.contact_id }}}}", [-1320, 200], "sb", prefer="return=minimal", executeOnce=True, alwaysOutputData=True)
http("Reset - Borrar Links", "DELETE", f"={SBURL}/casa_alpa_links_pago?contact_id=eq.{{{{ {N}.contact_id }}}}", [-1100, 200], "sb", prefer="return=minimal", executeOnce=True, alwaysOutputData=True)
http("Reset - Borrar Contacto GHL", "DELETE", f"={GHLURL}/contacts/{{{{ {N}.contact_id }}}}", [-880, 200], "ghl", executeOnce=True, onError="continueRegularOutput")

# ---- buffer anti-ráfaga
http("Supabase - Guardar Mensaje Entrante", "POST", f"{SBURL}/casa_alpa_mensajes", [-1540, 420], "sb",
     body="={{ JSON.stringify({ contact_id: $json.contact_id, rol: 'cliente', contenido: $json.texto }) }}",
     prefer="return=representation")
add("Wait - Agrupar Mensajes", "n8n-nodes-base.wait", {"amount": 8, "unit": "seconds"}, [-1320, 420], 1.1,
    webhookId=str(uuid.uuid4()))
http("Supabase - Mensajes Pendientes", "GET",
     f"={SBURL}/casa_alpa_mensajes?contact_id=eq.{{{{ {N}.contact_id }}}}&rol=eq.cliente&procesado=eq.false&order=id.asc",
     [-1100, 420], "sb", alwaysOutputData=True)
code("Code - Debounce", r"""
const mio = $('Supabase - Guardar Mensaje Entrante').first().json.id;
const pend = $input.all().map(i => i.json).filter(m => m && m.id);
if (!pend.length) return [];
const ultimo = Math.max(...pend.map(m => m.id));
// Si llegó otro mensaje después del mío, esa ejecución responde por todos
if (ultimo !== mio) return [];
return [{ json: { ids: pend.map(m => m.id), primer_id: Math.min(...pend.map(m => m.id)), texto: pend.map(m => m.contenido).join('\n') } }];
""", [-880, 420])
http("Supabase - Marcar Procesados", "PATCH", f"={SBURL}/casa_alpa_mensajes?id=in.({{{{ $json.ids.join(',') }}}})", [-660, 420], "sb",
     body='={{ JSON.stringify({ procesado: true }) }}', prefer="return=minimal", alwaysOutputData=True)

# ---------------------------------------------------------------- contexto
add("Supabase - Buscar Prospecto", "n8n-nodes-base.supabase", {
    "operation": "getAll", "tableId": "casa_alpa_prospectos", "limit": 1, "matchType": "allFilters",
    "filters": {"conditions": [{"keyName": "contact_id", "condition": "eq", "keyValue": f"={{{{ {N}.contact_id }}}}"}]}},
    [-440, 420], 1, SB, alwaysOutputData=True)
ifnode("IF - Existe Prospecto", "={{ !!$json.contact_id }}", TRUE_OP, [-220, 420])
add("Supabase - Crear Prospecto", "n8n-nodes-base.supabase", {
    "tableId": "casa_alpa_prospectos",
    "fieldsUi": {"fieldValues": [
        {"fieldId": "contact_id", "fieldValue": f"={{{{ {N}.contact_id }}}}"},
        {"fieldId": "nombre", "fieldValue": f"={{{{ {N}.nombre }}}}"},
        {"fieldId": "telefono", "fieldValue": f"={{{{ {N}.telefono }}}}"},
        {"fieldId": "canal", "fieldValue": f"={{{{ {N}.canal }}}}"},
        {"fieldId": "ad_id", "fieldValue": f"={{{{ {N}.ad_id }}}}"},
        {"fieldId": "origen_anuncio", "fieldValue": f"={{{{ {N}.ad_id ? 'anuncio ' + {N}.ad_id : ({N}.medium || 'directo') }}}}"},
        {"fieldId": "etapa", "fieldValue": "explorando"},
        {"fieldId": "created_at", "fieldValue": "={{ $now.toISO() }}"},
    ]}}, [0, 520], 1, SB)
http("GHL - Contacto", "GET", f"={GHLURL}/contacts/{{{{ {N}.contact_id }}}}", [220, 420], "ghl", executeOnce=True)
http("GHL - Buscar Opportunity", "GET",
     f"={GHLURL}/opportunities/search?location_id={{{{ {N}.location_id }}}}&contact_id={{{{ {N}.contact_id }}}}&pipeline_id={PIPELINE}",
     [440, 420], "ghl")
ifnode("IF - Existe Opportunity", "={{ ($json.opportunities || []).length > 0 }}", TRUE_OP, [660, 420])
http("GHL - Crear Opportunity", "POST", f"{GHLURL}/opportunities/", [880, 520], "ghl",
     body=f"={{{{ JSON.stringify({{ pipelineId: '{PIPELINE}', locationId: {N}.location_id, contactId: {N}.contact_id, name: {N}.nombre || 'Prospecto Casa Alpa', pipelineStageId: '{STAGES['nuevo']}', status: 'open' }}) }}}}")
code("Code - Opportunity", r"""
const j = $json;
const o = j.opportunity || (j.opportunities || [])[0] || {};
return [{ json: { opportunity_id: o.id || null, stage_id: o.pipelineStageId || null, status: o.status || null, monetary_value: o.monetaryValue || 0 } }];
""", [1100, 420])
ifnode("IF - Vale Activa", f"""={{{{ !['{STAGES['handoff']}', '{STAGES['ganado']}'].includes($json.stage_id) && !(($('GHL - Contacto').first().json.contact?.tags) || []).map(t => t.toLowerCase()).includes('vale-pausada') }}}}""", TRUE_OP, [1320, 420])
http("Supabase - Historial", "GET",
     f"={SBURL}/casa_alpa_mensajes?contact_id=eq.{{{{ {N}.contact_id }}}}&id=lt.{{{{ $('Code - Debounce').first().json.primer_id }}}}&order=id.desc&limit=20&select=rol,contenido,created_at",
     [1540, 420], "sb", alwaysOutputData=True, executeOnce=True)
http("Supabase - Anuncio", "GET",
     f"={SBURL}/casa_alpa_anuncios_muebles?ad_id=eq.{{{{ {N}.ad_id || 'ninguno' }}}}&select=nombre_campana,categoria,casa_alpa_catalogo(nombre)",
     [1760, 420], "sb", alwaysOutputData=True, executeOnce=True)
http("Supabase - Ultimo Link", "GET",
     f"={SBURL}/casa_alpa_links_pago?contact_id=eq.{{{{ {N}.contact_id }}}}&order=created_at.desc&limit=1&select=items,total,estado,created_at",
     [1980, 420], "sb", alwaysOutputData=True, executeOnce=True)

code("Code - Construir Contexto", r"""
const n = $('Code - Normalizar Entrada').first().json;
const p = $('Supabase - Buscar Prospecto').first().json || {};
const opp = $('Code - Opportunity').first().json;
const nuevos = $('Code - Debounce').first().json.texto;
const hist = $('Supabase - Historial').all().map(i => i.json).filter(m => m && m.rol).reverse();
const ad = $('Supabase - Anuncio').all().map(i => i.json).find(a => a && a.categoria);
const ln = $('Supabase - Ultimo Link').all().map(i => i.json).find(l => l && l.estado);
const faqs = String($('Google Docs - FAQs').first().json.content || '').replace(/[\u000b\r]+/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
const fecha = $now.setZone('America/Mexico_City').toFormat("cccc d 'de' LLLL yyyy, HH:mm", { locale: 'es' });

const datos = [
  `Nombre: ${p.nombre || n.nombre || 'desconocido'}`,
  `Categorías de interés: ${(p.categorias_interes || []).join(', ') || 'sin definir'}`,
  `Presupuesto: ${p.presupuesto ? '$' + Number(p.presupuesto).toLocaleString('es-MX') : 'sin definir'}`,
  `Estilo/color: ${p.estilo_color || 'sin definir'}`,
  `Ciudad/CP: ${[p.ciudad, p.codigo_postal].filter(Boolean).join(' ') || 'sin definir'}`,
  `Etapa: ${p.etapa || 'explorando'}`,
  p.resumen ? `Resumen previo: ${p.resumen}` : null,
].filter(Boolean).join('\n');

const anuncio = ad
  ? `Llegó por el anuncio "${ad.nombre_campana}" (categoría ${ad.categoria}${ad.casa_alpa_catalogo?.nombre ? ', producto ' + ad.casa_alpa_catalogo.nombre : ''}).`
  : 'No llegó por un anuncio identificado.';
const link = ln
  ? `Último link de pago: ${ln.estado} — ${(ln.items || []).map(i => `${i.cantidad}x ${i.producto}${i.variante ? ' (' + i.variante + ')' : ''}`).join(', ')} — total $${Number(ln.total).toLocaleString('es-MX')} (${ln.created_at}).`
  : 'No se le ha mandado link de pago.';
const conv = hist.length
  ? hist.map(m => `${m.rol === 'cliente' ? 'Cliente' : 'Vale'}: ${m.contenido}`).join('\n')
  : '(primera conversación)';

const prompt = `## CONTEXTO (no lo cites literal)
Fecha y hora en Morelia: ${fecha}
Canal: ${n.canal}
${datos}
${anuncio}
${link}

## INFORMACIÓN DEL NEGOCIO (FAQs oficiales; si algo no está aquí, no lo sabes)
${faqs || '(no disponible)'}

## CONVERSACIÓN PREVIA (antigua → reciente)
${conv}

## MENSAJE(S) NUEVO(S) DEL CLIENTE
${nuevos}`;

return [{ json: {
  prompt,
  contact_id: n.contact_id,
  canal: n.canal,
  location_id: n.location_id,
  opportunity_id: opp.opportunity_id,
  stage_id: opp.stage_id,
  monetary_value: opp.monetary_value,
  nombre: p.nombre || n.nombre,
} }];
""", [2200, 420])

# ---------------------------------------------------------------- agente
prompt = open("prompt_vale.md", encoding="utf-8").read()
add("Vale - AI Agent", "@n8n/n8n-nodes-langchain.agent", {
    "promptType": "define", "text": "={{ $json.prompt }}", "hasOutputParser": True,
    "options": {"systemMessage": prompt, "maxIterations": 8}}, [2440, 420], 3.1,
    retryOnFail=True, maxTries=2, waitBetweenTries=2000, onError="continueErrorOutput")
add("OpenAI Chat Model", "@n8n/n8n-nodes-langchain.lmChatOpenAi",
    {"model": "gpt-4.1", "options": {"temperature": 0.2}}, [2300, 700], 1, OPENAI)
schema = {
    "type": "object",
    "properties": {
        "mensajes": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 4},
        "productos_a_mostrar": {"type": "array", "items": {"type": "string"}, "maxItems": 2,
                                 "description": "producto_id de buscar_catalogo"},
        "etapa": {"type": "string", "enum": ["explorando", "interesado", "link_enviado", "handoff"]},
        "handoff_motivo": {"type": "string"},
        "resumen": {"type": "string"},
    },
    "required": ["mensajes", "productos_a_mostrar", "etapa", "handoff_motivo", "resumen"],
}
add("Structured Output Parser", "@n8n/n8n-nodes-langchain.outputParserStructured",
    {"schemaType": "manual", "inputSchema": json.dumps(schema, ensure_ascii=False, indent=2)}, [3000, 700], 1.2)

http("buscar_catalogo", "POST", f"{SBURL}/rpc/casa_alpa_buscar_catalogo", [2440, 700], "sb",
     tool_desc="Busca muebles disponibles en el catálogo de Casa Alpa con precios reales de la tienda (por variante). Úsala siempre antes de recomendar o cotizar.",
     body="""={{ JSON.stringify({
  p_categoria: $fromAI('categoria', 'comedor, sala, recamara o decoracion; vacío para buscar en todo', 'string', '') || null,
  p_presupuesto_max: $fromAI('presupuesto_max', 'presupuesto máximo en pesos; 0 si no se sabe', 'number', 0) || null,
  p_personas: $fromAI('personas', 'número de personas/plazas que necesita; 0 si no aplica', 'number', 0) || null,
  p_color: $fromAI('color', 'color o acabado deseado (ej. nogal, gris); vacío si no importa', 'string', '') || null,
  p_texto: $fromAI('texto', 'nombre o palabra del producto (ej. kelso, cama); vacío si no aplica', 'string', '') || null
}) }}""")
http("generar_link_pago", "POST", f"{SBURL}/rpc/casa_alpa_generar_link_pago", [2580, 700], "sb",
     tool_desc="Genera el link de pago (carrito de la tienda en línea) para lo que el cliente decidió comprar. El cliente paga y captura su dirección de envío ahí. Devuelve url y total.",
     body=f"""={{{{ JSON.stringify({{
  p_contact_id: {CTX}.contact_id,
  p_opportunity_id: {CTX}.opportunity_id,
  p_items: (v => typeof v === 'string' ? JSON.parse(v) : v)($fromAI('items', 'Lista JSON de lo que compra, ej. [{{"variante_id": 43495824097493, "cantidad": 1}}]. variante_id exacto de buscar_catalogo.', 'json'))
}}) }}}}""")
http("actualizar_prospecto", "PATCH", f"={SBURL}/casa_alpa_prospectos?contact_id=eq.{{{{ {CTX}.contact_id }}}}", [2720, 700], "sb",
     prefer="return=minimal",
     tool_desc="Guarda datos del prospecto en cuanto los detectes. Manda sólo los campos que conoces; los demás vacíos/0.",
     body="""={{ JSON.stringify(Object.fromEntries(Object.entries({
  nombre: $fromAI('nombre', 'nombre del cliente', 'string', ''),
  categorias_interes: ($fromAI('categorias_interes', 'lista COMPLETA de categorías de interés separadas por coma: comedor, sala, recamara, decoracion', 'string', '') || '').split(',').map(s => s.trim()).filter(Boolean),
  presupuesto: $fromAI('presupuesto', 'presupuesto en pesos, 0 si no se sabe', 'number', 0),
  estilo_color: $fromAI('estilo_color', 'estilo o color preferido', 'string', ''),
  ciudad: $fromAI('ciudad', 'ciudad del cliente', 'string', ''),
  codigo_postal: $fromAI('codigo_postal', 'código postal', 'string', ''),
  updated_at: new Date().toISOString()
}).filter(([k, v]) => v !== '' && v !== 0 && v !== null && !(Array.isArray(v) && v.length === 0)))) }}""")
add("Google Docs - FAQs", "n8n-nodes-base.googleDocs", {
    "operation": "get",
    "documentURL": "https://docs.google.com/document/d/15xlTHaH8_RUQCT4BuWTnMxPGYZ0lBLWRXHLq83IAgR8/edit?tab=t.0"},
    [2090, 600], 2, GDOCS, executeOnce=True, alwaysOutputData=True, onError="continueRegularOutput")

# ---------------------------------------------------------------- salida
code("Code - Fallback Agente", r"""
// Vale falló (modelo caído, límite de iteraciones, etc.): respuesta cortés y pasa con un asesor
return [{ json: { output: {
  mensajes: ['Déjame revisarlo con mi compañera para darte el dato exacto, en un momento te escribe 🙌'],
  productos_a_mostrar: [], etapa: 'handoff',
  handoff_motivo: 'Vale no pudo responder automáticamente: ' + String($json.error?.message || $json.error || 'error del agente').slice(0, 200),
  resumen: ''
} } }];
""", [2660, 600])
code("Code - Preparar Salida", r"""
const out = $input.first().json.output || {};
const c = $('Code - Construir Contexto').first().json;
let mensajes = (Array.isArray(out.mensajes) ? out.mensajes : [out.mensajes]).map(m => String(m || '').trim()).filter(Boolean).slice(0, 4);
if (!mensajes.length) mensajes = ['Dame un segundito y te confirmo 🙏'];
return mensajes.map(m => ({ json: { mensaje: m, contact_id: c.contact_id, canal: c.canal, out } }));
""", [2880, 420])
http("Supabase - Guardar Respuesta", "POST", f"{SBURL}/casa_alpa_mensajes", [3100, 240], "sb",
     body="={{ JSON.stringify({ contact_id: $('Code - Construir Contexto').first().json.contact_id, rol: 'vale', contenido: ($('HTTP - Enviar Mensaje GHL').all().some(i => i.json.error) ? '[NO ENTREGADO] ' : '') + $('Code - Preparar Salida').all().map(i => i.json.mensaje).join('\\n'), procesado: true }) }}",
     prefer="return=minimal", executeOnce=True)
add("Loop - Enviar Mensajes", "n8n-nodes-base.splitInBatches", {"options": {}}, [3100, 420], 3)
http("HTTP - Enviar Mensaje GHL", "POST", f"{GHLURL}/conversations/messages", [3320, 540], "ghl", version="2021-04-15",
     body="={{ JSON.stringify({ type: $json.canal, contactId: $json.contact_id, message: $json.mensaje }) }}", onError="continueRegularOutput")
add("Wait - Simular Escritura", "n8n-nodes-base.wait", {"amount": 2, "unit": "seconds"}, [3540, 540], 1.1,
    webhookId=str(uuid.uuid4()))
ifnode("IF - Hay Productos", "={{ ($('Code - Preparar Salida').first().json.out.productos_a_mostrar || []).filter(Boolean).length > 0 }}", TRUE_OP, [3320, 300])
http("Supabase - Datos Productos", "GET",
     f"""={SBURL}/casa_alpa_catalogo?id=in.({{{{ ($('Code - Preparar Salida').first().json.out.productos_a_mostrar || []).filter(id => /^[0-9a-f-]{{36}}$/i.test(id)).slice(0, 2).join(',') || '00000000-0000-0000-0000-000000000000' }}}})&activo=eq.true&select=id,nombre,foto_url,descripcion_corta,precio,casa_alpa_variantes(precio,disponible)""",
     [3540, 200], "sb", executeOnce=True)
code("Code - Mensaje Producto", r"""
const c = $('Code - Construir Contexto').first().json;
return $input.all().map(i => i.json).filter(p => p && p.id && p.foto_url).map(p => {
  const precios = (p.casa_alpa_variantes || []).filter(v => v.disponible).map(v => Number(v.precio));
  const desde = precios.length ? Math.min(...precios) : Number(p.precio);
  const varios = precios.length > 1 && Math.max(...precios) !== desde;
  return { json: {
    contact_id: c.contact_id, canal: c.canal, foto_url: p.foto_url,
    mensaje: [p.nombre, p.descripcion_corta, `${varios ? 'Desde ' : ''}$${desde.toLocaleString('es-MX')}`].filter(Boolean).join('\n')
  } };
});
""", [3760, 200])
http("HTTP - Enviar Producto GHL", "POST", f"{GHLURL}/conversations/messages", [3980, 200], "ghl", version="2021-04-15",
     body="={{ JSON.stringify({ type: $json.canal, contactId: $json.contact_id, message: $json.mensaje, attachments: [$json.foto_url] }) }}",
     onError="continueRegularOutput")

# ---------------------------------------------------------------- CRM
code("Code - Plan CRM", rf"""
const out = $('Code - Preparar Salida').first().json.out || {{}};
const c = $('Code - Construir Contexto').first().json;
const S = {json.dumps(STAGES)};
const orden = [S.nuevo, S.explorando, S.interesado, S.link_enviado];
const fallos = $('HTTP - Enviar Mensaje GHL').all().filter(i => i.json.error).map(i => String(i.json.error.message || i.json.error).slice(0, 160));
const noEntregado = fallos.length > 0;
if (noEntregado) {{
  out.etapa = 'handoff';
  out.handoff_motivo = 'No se pudo entregar la respuesta de Vale (' + fallos[0] + '). Contestar manualmente. ' + (out.handoff_motivo || '');
}}
const etapa = ['explorando', 'interesado', 'link_enviado', 'handoff'].includes(out.etapa) ? out.etapa : 'explorando';
const objetivo = S[etapa];
let mover = false;
if (etapa === 'handoff') mover = c.stage_id !== S.handoff;
else mover = orden.indexOf(objetivo) > orden.indexOf(c.stage_id);
const tags = etapa === 'handoff' ? ['vale-handoff'] : etapa === 'link_enviado' ? ['vale-link-pago'] : [];
return [{{ json: {{
  contact_id: c.contact_id, opportunity_id: c.opportunity_id, nombre: c.nombre,
  etapa, resumen: out.resumen || '', handoff_motivo: out.handoff_motivo || '',
  stage_destino: mover ? objetivo : null, tags,
  es_handoff: etapa === 'handoff', es_link: etapa === 'link_enviado'
}} }}];
""", [3540, 760], executeOnce=True)
http("Supabase - Ultimo Link (CRM)", "GET",
     f"={SBURL}/casa_alpa_links_pago?contact_id=eq.{{{{ $json.contact_id }}}}&estado=eq.enviado&order=created_at.desc&limit=1&select=total,items,url",
     [3760, 760], "sb", alwaysOutputData=True, executeOnce=True)
add("Supabase - Guardar Estado Final", "n8n-nodes-base.supabase", {
    "operation": "update", "tableId": "casa_alpa_prospectos", "matchType": "allFilters",
    "filters": {"conditions": [{"keyName": "contact_id", "condition": "eq", "keyValue": "={{ $('Code - Plan CRM').first().json.contact_id }}"}]},
    "fieldsUi": {"fieldValues": [
        {"fieldId": "etapa", "fieldValue": "={{ $('Code - Plan CRM').first().json.etapa }}"},
        {"fieldId": "resumen", "fieldValue": "={{ $('Code - Plan CRM').first().json.resumen }}"},
        {"fieldId": "canal", "fieldValue": "={{ $('Code - Construir Contexto').first().json.canal }}"},
        {"fieldId": "opportunity_id", "fieldValue": "={{ $('Code - Plan CRM').first().json.opportunity_id }}"},
        {"fieldId": "seguimiento_pendiente", "fieldValue": "={{ $('Code - Plan CRM').first().json.es_handoff }}"},
        {"fieldId": "updated_at", "fieldValue": "={{ $now.toISO() }}"},
    ]}}, [3980, 760], 1, SB, executeOnce=True, alwaysOutputData=True)
http("HTTP - Actualizar Opportunity GHL", "PUT", f"={GHLURL}/opportunities/{{{{ $('Code - Plan CRM').first().json.opportunity_id }}}}", [4200, 760], "ghl",
     body=f"""={{{{ JSON.stringify(Object.assign(
  {{ pipelineId: '{PIPELINE}' }},
  $('Code - Plan CRM').first().json.stage_destino ? {{ pipelineStageId: $('Code - Plan CRM').first().json.stage_destino }} : {{}},
  $('Code - Plan CRM').first().json.es_link && $('Supabase - Ultimo Link (CRM)').first().json.total ? {{ monetaryValue: Number($('Supabase - Ultimo Link (CRM)').first().json.total) }} : {{}}
)) }}}}""", executeOnce=True, onError="continueRegularOutput", alwaysOutputData=True)
ifnode("IF - Hay Etiquetas", "={{ $('Code - Plan CRM').first().json.tags.length > 0 }}", TRUE_OP, [4420, 760])
http("GHL - Agregar Etiquetas", "POST", f"={GHLURL}/contacts/{{{{ $('Code - Plan CRM').first().json.contact_id }}}}/tags", [4640, 660], "ghl",
     body="={{ JSON.stringify({ tags: $('Code - Plan CRM').first().json.tags }) }}", executeOnce=True, onError="continueRegularOutput")
ifnode("IF - Es Handoff", "={{ $('Code - Plan CRM').first().json.es_handoff }}", TRUE_OP, [4860, 660])
http("GHL - Tarea Handoff", "POST", f"={GHLURL}/contacts/{{{{ $('Code - Plan CRM').first().json.contact_id }}}}/tasks", [5080, 560], "ghl",
     body="""={{ JSON.stringify({
  title: 'Atender a ' + ($('Code - Plan CRM').first().json.nombre || 'cliente') + ' (Vale lo pasó)',
  body: 'Motivo: ' + $('Code - Plan CRM').first().json.handoff_motivo + '\\n\\nResumen: ' + $('Code - Plan CRM').first().json.resumen,
  dueDate: $now.plus({ hours: 1 }).toUTC().toISO(),
  completed: false
}) }}""", executeOnce=True, onError="continueRegularOutput")
http("GHL - Nota Handoff", "POST", f"={GHLURL}/contacts/{{{{ $('Code - Plan CRM').first().json.contact_id }}}}/notes", [5300, 560], "ghl",
     body="""={{ JSON.stringify({ body: '🤖 Vale pasó la conversación a un asesor.\\nMotivo: ' + $('Code - Plan CRM').first().json.handoff_motivo + '\\nResumen: ' + $('Code - Plan CRM').first().json.resumen }) }}""",
     executeOnce=True, onError="continueRegularOutput")

# ---------------------------------------------------------------- conexiones
link("Webhook - Mensaje Entrante", "Code - Normalizar Entrada")
link("Code - Normalizar Entrada", "IF - Reset de prueba")
link("IF - Reset de prueba", "Reset - Buscar Opps", 0)
link("IF - Reset de prueba", "Reset - Borrar Supabase", 0)
link("Reset - Buscar Opps", "Reset - Lista Opps")
link("Reset - Lista Opps", "Reset - Borrar Opp")
link("Reset - Borrar Supabase", "Reset - Borrar Mensajes")
link("Reset - Borrar Mensajes", "Reset - Borrar Links")
link("Reset - Borrar Links", "Reset - Borrar Contacto GHL")
link("IF - Reset de prueba", "Supabase - Guardar Mensaje Entrante", 1)
link("Supabase - Guardar Mensaje Entrante", "Wait - Agrupar Mensajes")
link("Wait - Agrupar Mensajes", "Supabase - Mensajes Pendientes")
link("Supabase - Mensajes Pendientes", "Code - Debounce")
link("Code - Debounce", "Supabase - Marcar Procesados")
link("Supabase - Marcar Procesados", "Supabase - Buscar Prospecto")
link("Supabase - Buscar Prospecto", "IF - Existe Prospecto")
link("IF - Existe Prospecto", "GHL - Contacto", 0)
link("IF - Existe Prospecto", "Supabase - Crear Prospecto", 1)
link("Supabase - Crear Prospecto", "GHL - Contacto")
link("GHL - Contacto", "GHL - Buscar Opportunity")
link("GHL - Buscar Opportunity", "IF - Existe Opportunity")
link("IF - Existe Opportunity", "Code - Opportunity", 0)
link("IF - Existe Opportunity", "GHL - Crear Opportunity", 1)
link("GHL - Crear Opportunity", "Code - Opportunity")
link("Code - Opportunity", "IF - Vale Activa")
link("IF - Vale Activa", "Supabase - Historial", 0)
link("Supabase - Historial", "Supabase - Anuncio")
link("Supabase - Anuncio", "Supabase - Ultimo Link")
link("Supabase - Ultimo Link", "Google Docs - FAQs")
link("Google Docs - FAQs", "Code - Construir Contexto")
link("Code - Construir Contexto", "Vale - AI Agent")
link("OpenAI Chat Model", "Vale - AI Agent", kind="ai_languageModel")
link("Structured Output Parser", "Vale - AI Agent", kind="ai_outputParser")
for t in ["buscar_catalogo", "generar_link_pago", "actualizar_prospecto"]:
    link(t, "Vale - AI Agent", kind="ai_tool")
link("Vale - AI Agent", "Code - Preparar Salida", 0)
link("Vale - AI Agent", "Code - Fallback Agente", 1)
link("Code - Fallback Agente", "Code - Preparar Salida")
link("Code - Preparar Salida", "Loop - Enviar Mensajes")
link("Loop - Enviar Mensajes", "IF - Hay Productos", 0)
link("Loop - Enviar Mensajes", "Code - Plan CRM", 0)
link("Loop - Enviar Mensajes", "Supabase - Guardar Respuesta", 0)
link("Loop - Enviar Mensajes", "HTTP - Enviar Mensaje GHL", 1)
link("HTTP - Enviar Mensaje GHL", "Wait - Simular Escritura")
link("Wait - Simular Escritura", "Loop - Enviar Mensajes")
link("IF - Hay Productos", "Supabase - Datos Productos", 0)
link("Supabase - Datos Productos", "Code - Mensaje Producto")
link("Code - Mensaje Producto", "HTTP - Enviar Producto GHL")
link("Code - Plan CRM", "Supabase - Ultimo Link (CRM)")
link("Supabase - Ultimo Link (CRM)", "Supabase - Guardar Estado Final")
link("Supabase - Guardar Estado Final", "HTTP - Actualizar Opportunity GHL")
link("HTTP - Actualizar Opportunity GHL", "IF - Hay Etiquetas")
link("IF - Hay Etiquetas", "GHL - Agregar Etiquetas", 0)
link("GHL - Agregar Etiquetas", "IF - Es Handoff")
link("IF - Es Handoff", "GHL - Tarea Handoff", 0)
link("GHL - Tarea Handoff", "GHL - Nota Handoff")

wf = {"name": "Vale - Casa Alpa (Asesora IA)", "nodes": nodes, "connections": conns,
      "settings": {"executionOrder": "v1", "availableInMCP": True, "timezone": "America/Mexico_City"}}
json.dump(wf, open("vale_v2.json", "w"), ensure_ascii=False, indent=1)
print(len(nodes), "nodos")
