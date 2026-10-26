#!/usr/bin/env python3
"""Genera los flujos de n8n del agente Maripino (xzen Auto).

Uso: python3 generar_flujos.py  -> escribe maripino-agente.json y maripino-configuracion.json
"""
import json
import uuid
from pathlib import Path

AQUI = Path(__file__).parent
CONFIG = json.loads((AQUI.parent / "enrutamiento-anuncios.json").read_text())

LOCATION_ID = "8SiKgyVuy9KVUIx1Y1RT"
CALENDAR_ID = "0YwJGtf0m8eI5hEacRMb"
GHL = "https://services.leadconnectorhq.com"
CRED_GHL = {"httpHeaderAuth": {"id": "u8Ru07QTVPNb28I6", "name": "GHL - PIT - XzenAuto"}}
CRED_OPENAI = {"openAiApi": {"id": "W5zBaQ7k25sn9YQz", "name": "RsViaje Independencia"}}
CRED_GMAIL = {"gmailOAuth2": {"id": "giX4xhnEUL2ltIcE", "name": "Gmail Xzen"}}
CTX = "$('Contexto y enrutamiento').first().json"


def nodo(nombre, tipo, version, pos, params, cred=None, **extra):
    n = {
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, "maripino/" + nombre)),
        "name": nombre,
        "type": tipo,
        "typeVersion": version,
        "position": pos,
        "parameters": params,
    }
    if cred:
        n["credentials"] = cred
    n.update(extra)
    return n


def ghl(nombre, pos, metodo, url, cuerpo=None, query=None, version_api="2021-07-28",
        herramienta=None, **extra):
    """Petición a la API v2 de GoHighLevel (nodo normal o herramienta del agente)."""
    p = {
        "method": metodo,
        "url": url,
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendHeaders": True,
        "headerParameters": {"parameters": [
            {"name": "Version", "value": version_api},
            {"name": "Accept", "value": "application/json"},
        ]},
        "options": {},
    }
    if query:
        p["sendQuery"] = True
        p["queryParameters"] = {"parameters": [{"name": k, "value": v} for k, v in query.items()]}
    if cuerpo:
        p["sendBody"] = True
        p["specifyBody"] = "json"
        p["jsonBody"] = cuerpo
    tipo = "n8n-nodes-base.httpRequest"
    if herramienta:
        tipo = "n8n-nodes-base.httpRequestTool"
        p = {"descriptionType": "manual", "toolDescription": herramienta, **p}
    return nodo(nombre, tipo, 4.2, pos, p, CRED_GHL, **extra)


# ---------------------------------------------------------------- IDs de GHL (subcuenta Xzen Auto)
CFG = {
    "locationId": LOCATION_ID,
    "calendarId": CALENDAR_ID,
    "pipelineId": "aCNhCRpOOyTfbHBPplyl",  # XzenAuto
    "etapas": {
        "nuevo": "fe64e5e5-f19a-4c8a-af74-20d0d2c12868",  # Nuevo lead (primera columna)
        "agendado": "467bd371-b731-4bf6-892d-da5d4c2f31d0",  # Agendado
        "atencion": "e5701f60-f46f-4a9f-a64b-590068028c12",  # Atención personalizada
    },
    "etapaAtencion": "atencion personalizada",  # se busca por nombre en el pipeline
    "campos": {
        "anuncio": "hKffpuqKs9ks9zY54O4a",  # Anuncio de origen
        "ubicacion": "KT0jJ23FRgNojKiQ88YG",  # Desde dónde nos contacta
        "inversion": "FI2NXz4DYljZ0RhkCqmf",  # Invierte en anuncios de Facebook
        "leads": "Pu2Gi0cSBV3gdMGKpWZr",  # Leads estimados por semana
    },
    "correoAviso": "xzenauto@gmail.com",
}

rutas = json.loads(json.dumps(CONFIG))
for v in rutas["verticales"].values():
    v["instrucciones"] = (AQUI.parent / v.pop("prompt")).read_text().strip()
rutas.pop("_descripcion", None)
CFG_JS = "const CFG = " + json.dumps(CFG, ensure_ascii=False) + ";\nconst RUTAS = " + json.dumps(
    rutas, ensure_ascii=False) + ";\n"

# ---------------------------------------------------------------- código
NORMALIZAR = r"""// Webhook del flujo de GHL "Cliente respondió" (WhatsApp).
const b = $json.body ?? $json;
const contactId = b.contact_id || b.contactId || b.customData?.contact_id || b.contact?.id;
if (!contactId) return [];
// Solo mensajes de WhatsApp (tipo 19). "Contacto creado" no trae mensaje: lo ignoramos.
const tipo = Number(b.message?.type);
if (b.simulacion !== true && (!b.message || (tipo && tipo !== 19))) return [];
const attr = b.contact?.lastAttributionSource || b.contact?.attributionSource || b.attributionSource || {};
return [{ json: {
  contactId: String(contactId),
  texto: String(b.message?.body ?? b.customData?.mensaje ?? '').trim(),
  adId: attr.adId || null,
  recibidoEn: new Date().toISOString(),
  // Pruebas: {"simulacion": true, "historial": [{"rol": "cliente"|"maripino", "texto": "..."}]}
  simulacion: b.simulacion === true,
  historialSimulado: Array.isArray(b.historial) ? b.historial : null,
} }];
"""

ANALIZAR = CFG_JS + r"""
const ent = $('Normalizar entrada').first().json;
const contacto = $('GHL contacto').first().json.contact ?? {};
const opps = $('GHL oportunidades').first().json.opportunities ?? [];
const opp = opps.find((o) => o.pipelineId === CFG.pipelineId) ?? null;
const tags = (contacto.tags ?? []).map((t) => String(t).toLowerCase());
const limpio = (s) => String(s ?? '').trim();

// 1. Con una persona del equipo o apagado a mano (etiqueta maripino-off): Maripino no contesta.
if (tags.includes('atencion-personalizada') || tags.includes('maripino-off')) return [];

// 2. ¿Viene de un anuncio? Solo atendemos leads de anuncios (la coexistencia trae también contactos personales).
const fuentes = [contacto.attributionSource, contacto.lastAttributionSource, ...(contacto.attributions ?? [])];
let anuncioId = [ent.adId, ...fuentes.map((a) => a?.adId)].find((id) => id && RUTAS.anuncios[id]) ?? null;
if (!anuncioId) {
  const texto = JSON.stringify(contacto);
  anuncioId = Object.keys(RUTAS.anuncios).find((id) => texto.includes(id)) ?? null;
}
const esPrueba = tags.includes('test-maripino') || ent.simulacion;
if (!anuncioId && !tags.includes('maripino') && !esPrueba) return [];
const anuncio = anuncioId ? RUTAS.anuncios[anuncioId] : null;

let vertical = anuncio?.vertical ?? (esPrueba ? 'agencia_viajes' : RUTAS.vertical_por_defecto);
if (!RUTAS.verticales[vertical]?.activo) vertical = RUTAS.vertical_por_defecto;
const conf = RUTAS.verticales[vertical];

// 3. Campos del contacto.
const valor = (id) => {
  const v = (contacto.customFields ?? []).find((c) => c.id === id)?.value;
  return Array.isArray(v) ? v.join(', ') : limpio(v);
};
const valores = Object.fromEntries(Object.entries(CFG.campos).map(([k, id]) => [k, valor(id)]));
const anuncioTexto = anuncio ? `${anuncio.nombre} (${anuncioId})` : (valores.anuncio || 'Prueba / sin anuncio');

// 4. Conversación de WhatsApp y agrupado de ráfagas.
let historial = [];
let nuevos = [];
// Pruebas: en contactos test-maripino se puede inyectar el historial (también en modo real).
if (ent.simulacion || (esPrueba && ent.historialSimulado)) {
  historial = (ent.historialSimulado ?? []).map((m) => ({ rol: m.rol === 'cliente' ? 'Cliente' : 'Maripino', texto: limpio(m.texto) }));
  nuevos = [ent.texto];
} else {
  let msgs = [];
  try { const m = $('GHL mensajes').first().json.messages; msgs = (m && (m.messages || m)) || []; } catch (e) {}
  if (!Array.isArray(msgs)) msgs = [];
  msgs = msgs.filter((m) => /WHATSAPP/.test(m.messageType ?? '')).sort((a, b) => new Date(a.dateAdded) - new Date(b.dateAdded));
  // Si después de este mensaje llegó otro, lo atiende la ejecución de ese otro mensaje.
  // Si ya hubo una respuesta posterior (bot o persona), no contestamos de nuevo.
  let mio = -1;
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].direction === 'inbound' && limpio(msgs[i].body) === ent.texto) { mio = i; break; }
  }
  if (mio >= 0 && msgs.slice(mio + 1).length > 0) return [];
  let corte = msgs.length;
  while (corte > 0 && msgs[corte - 1].direction === 'inbound') corte--;
  nuevos = msgs.slice(corte).map((m) => limpio(m.body) || '[audio, imagen o archivo sin texto]');
  historial = msgs.slice(Math.max(0, corte - 20), corte)
    .map((m) => ({ rol: m.direction === 'inbound' ? 'Cliente' : 'xzen Auto', texto: limpio(m.body) }))
    .filter((m) => m.texto);
  if (!nuevos.length) nuevos = [ent.texto || '[mensaje sin texto]'];
}

const ahora = new Date().toLocaleString('es-MX', { timeZone: 'America/Mexico_City', dateStyle: 'full', timeStyle: 'short' });
const p = (v) => v || 'PENDIENTE';
const dias = Array.from({ length: 14 }, (_, i) => new Date(Date.now() + i * 864e5).toLocaleDateString('es-MX',
  { timeZone: 'America/Mexico_City', weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }));
const prompt = `# Fecha y hora actual (Ciudad de México)
${ahora}

# Calendario (úselo siempre para nombrar los días; no calcule días de la semana)
${dias.join('\n')}

# Datos del cliente en el CRM
- Nombre: ${limpio(contacto.firstName) || 'desconocido'}${contacto.companyName ? `\n- Negocio: ${contacto.companyName}` : ''}${contacto.email ? `\n- Correo: ${contacto.email}` : ''}
- Anuncio de origen: ${anuncioTexto}
- Desde dónde nos contacta: ${p(valores.ubicacion)}
- ¿Invierte en anuncios de Facebook?: ${p(valores.inversion)}
- Leads estimados por semana: ${p(valores.leads)}
- Video ya enviado: ${tags.includes('video-enviado') ? 'sí' : 'no'}
- Cita ya agendada: ${tags.includes('cita-agendada') ? 'sí' : 'no'}

${conf.instrucciones}

# Video del sistema
${conf.video_demo}

# Conversación previa
${historial.length ? historial.map((m) => `${m.rol}: ${m.texto}`).join('\n') : '(es el primer mensaje del cliente)'}

# Mensaje(s) nuevo(s) del cliente
${nuevos.join('\n')}`;

return [{ json: {
  contactId: ent.contactId,
  simulacion: ent.simulacion,
  nombre: limpio(contacto.firstName),
  email: limpio(contacto.email),
  negocio: limpio(contacto.companyName),
  tags,
  anuncioId,
  anuncioTexto,
  vertical,
  tagVertical: conf.tag_ghl,
  valores,
  oportunidadId: opp?.id ?? null,
  etapaActual: opp?.pipelineStageId ?? null,
  crearOportunidad: !opp && !ent.simulacion,
  prompt,
} }];
"""

SYSTEM = """Eres Maripino, asistente virtual de xzen Auto. Atiendes por WhatsApp a dueños y gerentes de negocios que escribieron desde un anuncio de Facebook/Instagram.

# Personalidad
- Siempre trata de USTED al cliente. Amigable, cálido y profesional.
- Español de México. Mensajes cortos (máximo 3-4 líneas cada uno), como en WhatsApp.
- Una sola pregunta por turno. Emojis con moderación (uno o dos como máximo).
- No diga que la conversación es una demostración ni haga simulaciones o juegos de rol.

# Objetivo de la conversación
1. Salude con calidez, preséntese como Maripino de xzen Auto y pregunte su nombre si no lo tiene.
2. Conózcalo con estas preguntas, de forma natural y una por turno, solo las que sigan PENDIENTES en el CRM:
   a) ¿Desde dónde nos contacta? (ciudad / estado / país)
   b) ¿Actualmente invierte en anuncios de Facebook?
   c) ¿Cuántos leads o consultas recibe aproximadamente a la semana?
   Comente brevemente cada respuesta (con empatía, conectándola con lo que hace el sistema) antes de seguir.
   Si responde que NO invierte en anuncios de Facebook, coméntele con naturalidad que en nuestro curso tenemos
   un apartado donde enseñamos a pautar en Facebook para conseguir leads.
3. Resuelva sus dudas con lo que hace el sistema (sección de instrucciones del giro).
4. Envíe el video del sistema (una sola vez) y pídale que lo vea y nos cuente qué le pareció.
   En ese mismo turno no proponga todavía la llamada: espere su opinión del video.
5. Cuando comente el video (o si antes pide agendar), invítelo a una llamada con el equipo de xzen Auto y agéndela.

# Curso de xzen Auto (lo que incluye)
- Cómo pautar en Facebook para conseguir leads.
- Formación para el dueño y sus agentes de venta: cómo usar el sistema, cómo funciona el agente virtual
  y cómo opera todo lo que implementemos en su negocio.
Menciónelo cuando venga al caso (si no invierte en anuncios, si le preocupa que su equipo no sepa usar el
sistema, o si pregunta por capacitación). No invente precio, duración, modalidad ni otros detalles del curso;
si pregunta más, dígale que se lo explican en la llamada.

# Precios
Nunca dé precios, rangos ni planes. El precio depende de las necesidades de su negocio y se presenta en la llamada, con una propuesta a su medida.

# Cómo agendar
1. Use consultar_disponibilidad y ofrezca 2 o 3 horarios concretos en hora de Ciudad de México (si el cliente está en otra zona horaria, aclárelo). Nunca invente horarios.
2. Cuando elija horario, pida en un solo mensaje lo que falte: nombre completo, nombre de su negocio y correo.
   NO llame a agendar_cita hasta tener los tres datos dichos por el cliente.
3. Agende con agendar_cita usando EXACTAMENTE el inicio de un horario devuelto por consultar_disponibilidad.
4. Solo si agendar_cita respondió correctamente (devuelve un id), confirme día y hora y dígale que le llegará la confirmación.
   Si respondió con error, discúlpese, consulte de nuevo la disponibilidad y ofrezca otros horarios.
5. Si en el CRM dice "Cita ya agendada: sí", NO vuelva a agendar: confirme la cita existente y resuelva dudas.
   Si quiere cambiarla o cancelarla, márquelo para atención personalizada.
Si todavía no quiere agendar, pregúntele si le puede escribir en un par de días.

# Atención personalizada
Si el cliente pide hablar con una persona, está molesto, o pregunta algo que no puede responder con certeza, marque atencion_personalizada = true, explique el motivo y dígale que alguien del equipo le escribirá en breve.

# Formato de salida
- mensajes: 1 a 3 mensajes de WhatsApp para el cliente, en orden.
- datos: lo que el cliente haya dicho en la conversación (cadena vacía si no lo sabe):
  ubicacion, invierte_anuncios (p. ej. "Sí, unos $5,000 al mes" o "No"), leads_semana (p. ej. "150"),
  nombre_completo, negocio (el nombre propio, p. ej. "Viajes Horizonte"; nunca el giro como "agencia de viajes"), email.
- video_enviado: true si en esta respuesta incluye el link del video.
- cita_agendada: true solo si agendar_cita respondió correctamente en este turno.
- atencion_personalizada / motivo_atencion: ver arriba.
- resumen: una línea con el estado del prospecto para el equipo.

# Reglas
- No invente funciones, integraciones, clientes, casos de éxito ni resultados.
- Nunca repita una pregunta que ya tenga respuesta en el CRM o en la conversación.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "mensajes": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 3},
        "datos": {
            "type": "object",
            "properties": {k: {"type": "string"} for k in
                           ["ubicacion", "invierte_anuncios", "leads_semana", "nombre_completo", "negocio", "email"]},
            "required": ["ubicacion", "invierte_anuncios", "leads_semana", "nombre_completo", "negocio", "email"],
        },
        "video_enviado": {"type": "boolean"},
        "cita_agendada": {"type": "boolean"},
        "atencion_personalizada": {"type": "boolean"},
        "motivo_atencion": {"type": "string"},
        "resumen": {"type": "string"},
    },
    "required": ["mensajes", "datos", "video_enviado", "cita_agendada", "atencion_personalizada",
                 "motivo_atencion", "resumen"],
}

FALLBACK = r"""// Maripino falló (modelo caído, límite de iteraciones…): respuesta cortés y pasa con una persona.
return [{ json: { output: {
  mensajes: ['Permítame un momento, en breve una persona de nuestro equipo le escribe por aquí 🙏'],
  datos: {}, video_enviado: false, cita_agendada: false,
  atencion_personalizada: true, motivo_atencion: 'Error del agente automático', resumen: 'Error del agente',
} } }];
"""

PREPARAR = r"""const out = $input.first().json.output ?? {};
const c = $('Analizar').first().json;
let mensajes = (Array.isArray(out.mensajes) ? out.mensajes : [out.mensajes])
  .map((m) => String(m ?? '').trim()).filter(Boolean).slice(0, 3);
if (!mensajes.length) mensajes = ['Permítame un momento y le confirmo 🙏'];

// Cita: se toma de la respuesta real de agendar_cita, no de lo que diga el modelo.
let cita = null;
for (const paso of $input.first().json.intermediateSteps ?? []) {
  if (paso.action?.tool !== 'agendar_cita') continue;
  let obs = paso.observation;
  try { obs = typeof obs === 'string' ? JSON.parse(obs) : obs; } catch (e) {}
  if (Array.isArray(obs)) obs = obs[0];
  // La respuesta de GHL no trae la hora; el correo la consulta después con el id de la cita.
  if (obs?.id && !obs.error && !obs.statusCode) cita = { id: obs.id, inicio: obs.startTime ?? null };
}
// Video enviado: solo si algún mensaje lleva de verdad el link de YouTube.
const videoEnviado = mensajes.some((m) => /youtu\.?be/i.test(m));
return [{ json: { mensajes, out, cita, videoEnviado, contactId: c.contactId, simulacion: c.simulacion } }];
"""

ITEMS = r"""const s = $input.first().json;
return s.mensajes.map((mensaje) => ({ json: { mensaje, contactId: s.contactId } }));
"""

PLAN_CRM = CFG_JS + r"""
const c = $('Analizar').first().json;
const salida = $('Preparar salida').first().json;
const out = salida.out;
const d = out.datos ?? {};
const citaOk = !!salida.cita;
const limpio = (s) => String(s ?? '').trim();

const customFields = [];
const poner = (clave, v) => { v = limpio(v); if (v && v !== c.valores[clave]) customFields.push({ id: CFG.campos[clave], field_value: v }); };
poner('ubicacion', d.ubicacion);
poner('inversion', d.invierte_anuncios);
poner('leads', d.leads_semana);
if (!c.valores.anuncio) poner('anuncio', c.anuncioTexto);

let oportunidadNueva = null;
try { oportunidadNueva = $('GHL crear oportunidad').first().json.opportunity?.id ?? null; } catch (e) {}

const contacto = {};
if (customFields.length) contacto.customFields = customFields;
// El correo va en una petición aparte: si ya existe en otro contacto, GHL rechaza la petición entera.
const email = limpio(d.email).includes('@') && !c.email ? limpio(d.email) : null;
if (limpio(d.negocio) && !c.negocio) contacto.companyName = limpio(d.negocio);
const partes = limpio(d.nombre_completo).split(/\s+/).filter(Boolean);
if (partes.length > 1) { contacto.firstName = partes[0]; contacto.lastName = partes.slice(1).join(' '); }

const tags = ['maripino', c.tagVertical];
if (salida.videoEnviado) tags.push('video-enviado');
if (citaOk) tags.push('cita-agendada');
if (out.atencion_personalizada) tags.push('atencion-personalizada');

return [{ json: {
  contactId: c.contactId,
  contacto,
  hayCambiosContacto: Object.keys(contacto).length > 0,
  email,
  tags,
  oportunidadId: c.oportunidadId ?? oportunidadNueva,
  etapaActual: c.etapaActual,
  citaAgendada: citaOk,
  cita: salida.cita,
  atencion: !!out.atencion_personalizada,
  motivo: limpio(out.motivo_atencion),
  resumen: limpio(out.resumen),
} }];
"""

ETAPA = CFG_JS + r"""
const plan = $('Plan CRM').first().json;
const norm = (s) => String(s ?? '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').trim();
const pipe = ($json.pipelines ?? []).find((p) => p.id === CFG.pipelineId);
const atencion = pipe?.stages?.find((s) => norm(s.name).includes(CFG.etapaAtencion))?.id ?? CFG.etapas.atencion;
let destino = null;
if (plan.atencion) destino = atencion;
else if (plan.citaAgendada) destino = CFG.etapas.agendado;
return [{ json: { ...plan, destino, moverOportunidad: !!(destino && plan.oportunidadId && destino !== plan.etapaActual),
  faltaColumnaAtencion: plan.atencion && !atencion } }];
"""

CORREO = r"""const p = $('Etapa destino').first().json;
const c = $('Analizar').first().json;
const out = $('Preparar salida').first().json;
const enlace = `https://app.gohighlevel.com/v2/location/8SiKgyVuy9KVUIx1Y1RT/contacts/detail/${p.contactId}`;
return [{ json: {
  asunto: `Maripino: ${c.nombre || 'Un prospecto'} necesita atención personalizada`,
  cuerpo: [
    `${c.nombre || 'Un prospecto'} pidió atención personalizada por WhatsApp.`,
    '',
    `Motivo: ${p.motivo || 'sin especificar'}`,
    `Resumen: ${p.resumen || '-'}`,
    `Anuncio de origen: ${c.anuncioTexto}`,
    `Desde dónde nos contacta: ${c.valores.ubicacion || '-'}`,
    `Invierte en anuncios de Facebook: ${c.valores.inversion || '-'}`,
    `Leads por semana: ${c.valores.leads || '-'}`,
    '',
    'Últimos mensajes:',
    c.prompt.split('# Conversación previa')[1] ?? '',
    'Respuesta de Maripino:',
    ...out.mensajes,
    '',
    p.faltaColumnaAtencion ? '⚠️ No existe la columna "Atención personalizada" en el pipeline XzenAuto; créala para que la oportunidad se mueva sola.' : '',
    `Contacto en GHL: ${enlace}`,
  ].join('\n'),
} }];
"""

RECORDATORIO = r"""// ¿Sigue sin responder desde que le mandamos el video?
const contacto = $('Recordatorio · contacto').first().json.contact ?? {};
const tags = (contacto.tags ?? []).map((t) => String(t).toLowerCase());
if (['atencion-personalizada', 'maripino-off', 'video-recordatorio'].some((t) => tags.includes(t))) return [];
let msgs = [];
try { const m = $json.messages; msgs = (m && (m.messages || m)) || []; } catch (e) {}
if (!Array.isArray(msgs)) msgs = [];
msgs = msgs.filter((m) => /WHATSAPP/.test(m.messageType ?? '')).sort((a, b) => new Date(a.dateAdded) - new Date(b.dateAdded));
let video = -1;
msgs.forEach((m, i) => { if (m.direction === 'outbound' && /youtu\.?be/.test(m.body ?? '')) video = i; });
if (video < 0 || msgs.slice(video + 1).some((m) => m.direction === 'inbound')) return [];
const nombre = String(contacto.firstName ?? '').trim();
return [{ json: {
  contactId: contacto.id,
  mensaje: `${nombre ? `Hola, ${nombre}. ` : 'Hola. '}¿Pudo ver el video? 😊 Nos encantaría saber qué le pareció.`,
} }];
"""

CORREO_CITA = r"""const p = $('Etapa destino').first().json;
const c = $('Analizar').first().json;
const d = $('Preparar salida').first().json.out.datos ?? {};
const contacto = $('GHL contacto').first().json.contact ?? {};
const f = (iso) => new Date(iso).toLocaleString('es-MX', { timeZone: 'America/Mexico_City', dateStyle: 'full', timeStyle: 'short' });
const apt = $('GHL datos cita').first().json;
const inicio = apt.appointment?.startTime ?? apt.event?.startTime ?? apt.startTime ?? p.cita?.inicio;
const cuando = inicio ? f(inicio) + ' (hora de Ciudad de México)' : 'ver calendario';
const v = (a, b) => (String(a ?? '').trim() || String(b ?? '').trim() || '-');
const nombre = v(d.nombre_completo, [contacto.firstName, contacto.lastName].filter(Boolean).join(' '));
const negocio = v(d.negocio, contacto.companyName);
return [{ json: {
  asunto: `📅 Nueva llamada agendada: ${nombre} (${negocio}) · ${cuando}`,
  cuerpo: [
    'Maripino agendó una llamada.',
    '',
    `Cuándo: ${cuando}`,
    `Calendario: Agencia 24/7 Rs Viajes`,
    '',
    'Datos del lead',
    `- Nombre: ${nombre}`,
    `- Negocio: ${negocio}`,
    `- Teléfono: ${v(contacto.phone)}`,
    `- Correo: ${v(d.email, contacto.email)}`,
    `- Anuncio de origen: ${c.anuncioTexto}`,
    `- Desde dónde nos contacta: ${v(d.ubicacion, c.valores.ubicacion)}`,
    `- Invierte en anuncios de Facebook: ${v(d.invierte_anuncios, c.valores.inversion)}`,
    `- Leads estimados por semana: ${v(d.leads_semana, c.valores.leads)}`,
    '',
    `Resumen: ${p.resumen || '-'}`,
    '',
    `Contacto en GHL: https://app.gohighlevel.com/v2/location/8SiKgyVuy9KVUIx1Y1RT/contacts/detail/${p.contactId}`,
  ].join('\n'),
} }];
"""


def si(nombre, pos, expresion):
    return nodo(nombre, "n8n-nodes-base.if", 2.2, pos, {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
            "conditions": [{"id": str(uuid.uuid5(uuid.NAMESPACE_URL, nombre)), "leftValue": expresion,
                            "rightValue": "", "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
            "combinator": "and",
        },
        "options": {},
    })


A = "$('Analizar').first().json"
nodos = [
    nodo("Mensaje WhatsApp (GHL)", "n8n-nodes-base.webhook", 2, [0, 300],
         {"httpMethod": "POST", "path": "xzen-maripino", "options": {}},
         webhookId=str(uuid.uuid5(uuid.NAMESPACE_URL, "maripino/webhook"))),
    nodo("Normalizar entrada", "n8n-nodes-base.code", 2, [200, 300], {"jsCode": NORMALIZAR}),
    nodo("Esperar ráfaga (12 s)", "n8n-nodes-base.wait", 1.1, [400, 300],
         {"amount": "={{ $json.simulacion ? 1 : 12 }}", "unit": "seconds"},
         webhookId=str(uuid.uuid5(uuid.NAMESPACE_URL, "maripino/wait"))),
    ghl("GHL contacto", [600, 300], "GET",
        "=" + GHL + "/contacts/{{ $('Normalizar entrada').first().json.contactId }}"),
    ghl("GHL oportunidades", [800, 300], "GET", GHL + "/opportunities/search",
        query={"location_id": LOCATION_ID, "contact_id": "={{ $('Normalizar entrada').first().json.contactId }}",
               "pipeline_id": CFG["pipelineId"]}),
    ghl("GHL conversación", [1000, 300], "GET", GHL + "/conversations/search",
        query={"locationId": LOCATION_ID, "contactId": "={{ $('Normalizar entrada').first().json.contactId }}",
               "limit": "1"}),
    ghl("GHL mensajes", [1200, 300], "GET",
        "=" + GHL + "/conversations/{{ ($json.conversations || [])[0]?.id || 'sin-conversacion' }}/messages",
        query={"limit": "40"}, onError="continueRegularOutput", alwaysOutputData=True),
    nodo("Analizar", "n8n-nodes-base.code", 2, [1400, 300], {"jsCode": ANALIZAR}),
    si("¿Primer contacto?", [1600, 300], "={{ $json.crearOportunidad }}"),
    ghl("GHL crear oportunidad", [1800, 120], "POST", GHL + "/opportunities/",
        cuerpo="={{ JSON.stringify({ locationId: '" + LOCATION_ID + "', pipelineId: '" + CFG["pipelineId"] + "',"
               " pipelineStageId: '" + CFG["etapas"]["nuevo"] + "', status: 'open', contactId: $json.contactId,"
               " name: ($json.nombre || 'Prospecto') + ' · ' + $json.anuncioTexto }) }}",
        onError="continueRegularOutput"),
    ghl("GHL guardar anuncio", [2000, 120], "PUT", "=" + GHL + "/contacts/{{ " + A + ".contactId }}",
        cuerpo="={{ JSON.stringify({ tags: [...new Set([...(" + A + ".tags), 'maripino', " + A + ".tagVertical])],"
               " customFields: [{ id: '" + CFG["campos"]["anuncio"] + "', field_value: " + A + ".anuncioTexto }] }) }}",
        onError="continueRegularOutput"),
    nodo("Maripino", "@n8n/n8n-nodes-langchain.agent", 3.1, [2260, 300], {
        "promptType": "define",
        "text": "={{ " + A + ".prompt }}",
        "hasOutputParser": True,
        "options": {"systemMessage": SYSTEM, "maxIterations": 8, "returnIntermediateSteps": True},
    }, retryOnFail=True, onError="continueErrorOutput"),
    nodo("OpenAI", "@n8n/n8n-nodes-langchain.lmChatOpenAi", 1.2, [2060, 560], {
        "model": {"__rl": True, "mode": "list", "value": "gpt-4.1"},
        "options": {"temperature": 0.4},
    }, CRED_OPENAI),
    nodo("Salida estructurada", "@n8n/n8n-nodes-langchain.outputParserStructured", 1.2, [2220, 560], {
        "schemaType": "manual", "inputSchema": json.dumps(SCHEMA, ensure_ascii=False, indent=2),
    }),
    ghl("consultar_disponibilidad", [2380, 560], "GET", GHL + "/calendars/" + CALENDAR_ID + "/free-slots",
        query={"startDate": "={{ $now.toMillis() }}", "endDate": "={{ $now.plus({ days: 10 }).toMillis() }}",
               "timezone": "America/Mexico_City"},
        version_api="2021-04-15",
        herramienta="Consulta los horarios libres para la llamada con xzen Auto en los próximos 10 días. Devuelve, por fecha, los inicios de cada horario en hora de Ciudad de México.",
        onError="continueRegularOutput"),
    ghl("agendar_cita", [2540, 560], "POST", GHL + "/calendars/events/appointments",
        cuerpo="={{ JSON.stringify({ calendarId: '" + CALENDAR_ID + "', locationId: '" + LOCATION_ID + "',"
               " contactId: " + A + ".contactId, appointmentStatus: 'confirmed', toNotify: true,"
               " title: 'Llamada xzen Auto · ' + $fromAI('nombre_completo', 'Nombre completo del cliente (nombre y apellido)', 'string') + ' (' + $fromAI('negocio', 'Nombre propio del negocio del cliente', 'string') + ') · ' + $fromAI('email', 'Correo electrónico del cliente', 'string'),"
               " startTime: $fromAI('inicio', 'Inicio exacto de un horario devuelto por consultar_disponibilidad, ISO 8601 con zona, p. ej. 2026-10-28T16:30:00-06:00', 'string') }) }}",
        version_api="2021-04-15",
        herramienta="Agenda la llamada con xzen Auto en el horario elegido por el cliente. Requiere nombre completo, negocio y correo REALES dados por el cliente (nunca los invente ni los deje vacíos) y un horario devuelto por consultar_disponibilidad. Úsela una sola vez por cliente.",
        onError="continueRegularOutput"),
    nodo("Respuesta de respaldo", "n8n-nodes-base.code", 2, [2500, 460], {"jsCode": FALLBACK}),
    nodo("Preparar salida", "n8n-nodes-base.code", 2, [2700, 300], {"jsCode": PREPARAR}),
    si("¿Es real? (no simulación)", [2900, 300], "={{ !$json.simulacion }}"),
    nodo("Separar mensajes", "n8n-nodes-base.code", 2, [3100, 300], {"jsCode": ITEMS}),
    ghl("GHL enviar WhatsApp", [3300, 300], "POST", GHL + "/conversations/messages",
        cuerpo="={{ JSON.stringify({ type: 'WhatsApp', contactId: $json.contactId, message: $json.mensaje }) }}",
        onError="continueRegularOutput"),
    nodo("Plan CRM", "n8n-nodes-base.code", 2, [3500, 300], {"jsCode": PLAN_CRM}),
    si("¿Datos nuevos?", [3700, 300], "={{ $json.hayCambiosContacto }}"),
    ghl("GHL actualizar contacto", [3900, 200], "PUT", "=" + GHL + "/contacts/{{ $json.contactId }}",
        cuerpo="={{ JSON.stringify($json.contacto) }}", onError="continueRegularOutput"),
    si("¿Hay correo nuevo?", [3900, 420], "={{ !!$('Plan CRM').first().json.email }}"),
    ghl("GHL guardar correo", [4000, 420], "PUT", "=" + GHL + "/contacts/{{ $('Plan CRM').first().json.contactId }}",
        cuerpo="={{ JSON.stringify({ email: $('Plan CRM').first().json.email }) }}", onError="continueRegularOutput"),
    ghl("GHL etiquetas", [4100, 300], "POST", "=" + GHL + "/contacts/{{ $('Plan CRM').first().json.contactId }}/tags",
        cuerpo="={{ JSON.stringify({ tags: $('Plan CRM').first().json.tags }) }}", onError="continueRegularOutput",
        executeOnce=True),
    ghl("GHL pipelines", [4300, 300], "GET", GHL + "/opportunities/pipelines", query={"locationId": LOCATION_ID},
        onError="continueRegularOutput", alwaysOutputData=True),
    nodo("Etapa destino", "n8n-nodes-base.code", 2, [4500, 300], {"jsCode": ETAPA}),
    si("¿Mover oportunidad?", [4700, 300], "={{ $json.moverOportunidad }}"),
    ghl("GHL mover oportunidad", [4900, 200], "PUT", "=" + GHL + "/opportunities/{{ $json.oportunidadId }}",
        cuerpo="={{ JSON.stringify({ pipelineId: '" + CFG["pipelineId"] + "', pipelineStageId: $json.destino }) }}",
        onError="continueRegularOutput"),
    si("¿Atención personalizada?", [5100, 300], "={{ $('Etapa destino').first().json.atencion }}"),
    nodo("Armar aviso", "n8n-nodes-base.code", 2, [5300, 200], {"jsCode": CORREO}),
    ghl("GHL nota", [5500, 200], "POST", "=" + GHL + "/contacts/{{ $('Etapa destino').first().json.contactId }}/notes",
        cuerpo="={{ JSON.stringify({ body: $json.asunto + '\\n\\n' + $json.cuerpo }) }}", onError="continueRegularOutput"),
    nodo("Correo a xzenauto@gmail.com", "n8n-nodes-base.gmail", 2.2, [5700, 200], {
        "sendTo": CFG["correoAviso"], "subject": "={{ $('Armar aviso').first().json.asunto }}", "emailType": "text",
        "message": "={{ $('Armar aviso').first().json.cuerpo }}", "options": {"appendAttribution": False},
    }, CRED_GMAIL, onError="continueRegularOutput"),
    # Cita agendada: aviso por correo con la cita y los datos del lead.
    si("¿Cita agendada?", [5300, 700], "={{ $('Etapa destino').first().json.citaAgendada }}"),
    ghl("GHL datos cita", [5400, 700], "GET", "=" + GHL + "/calendars/events/appointments/{{ $('Etapa destino').first().json.cita.id }}",
        version_api="2021-04-15", onError="continueRegularOutput", alwaysOutputData=True),
    nodo("Armar correo cita", "n8n-nodes-base.code", 2, [5600, 700], {"jsCode": CORREO_CITA}),
    nodo("Correo cita a xzenauto@gmail.com", "n8n-nodes-base.gmail", 2.2, [5700, 700], {
        "sendTo": CFG["correoAviso"], "subject": "={{ $json.asunto }}", "emailType": "text",
        "message": "={{ $json.cuerpo }}", "options": {"appendAttribution": False},
    }, CRED_GMAIL, onError="continueRegularOutput"),
    # Recordatorio: 1 hora después de enviar el video, si no ha respondido.
    si("¿Envió el video?", [5300, 460], "={{ $('Preparar salida').first().json.videoEnviado === true }}"),
    # 1 hora; en contactos de prueba (etiqueta test-maripino) 1 minuto para poder probarlo.
    nodo("Esperar 1 hora", "n8n-nodes-base.wait", 1.1, [5500, 460],
         {"amount": "={{ $('Analizar').first().json.tags.includes('test-maripino') ? 1 : 60 }}", "unit": "minutes"},
         webhookId=str(uuid.uuid5(uuid.NAMESPACE_URL, "maripino/wait-video"))),
    ghl("Recordatorio · contacto", [5700, 460], "GET",
        "=" + GHL + "/contacts/{{ $('Plan CRM').first().json.contactId }}"),
    ghl("Recordatorio · conversación", [5900, 460], "GET", GHL + "/conversations/search",
        query={"locationId": LOCATION_ID, "contactId": "={{ $('Plan CRM').first().json.contactId }}", "limit": "1"}),
    ghl("Recordatorio · mensajes", [6100, 460], "GET",
        "=" + GHL + "/conversations/{{ ($json.conversations || [])[0]?.id || 'sin-conversacion' }}/messages",
        query={"limit": "40"}, onError="continueRegularOutput", alwaysOutputData=True),
    nodo("¿Sin respuesta al video?", "n8n-nodes-base.code", 2, [6300, 460], {"jsCode": RECORDATORIO}),
    ghl("GHL enviar recordatorio", [6500, 460], "POST", GHL + "/conversations/messages",
        cuerpo="={{ JSON.stringify({ type: 'WhatsApp', contactId: $json.contactId, message: $json.mensaje }) }}",
        onError="continueRegularOutput"),
    ghl("GHL etiqueta recordatorio", [6700, 460], "POST",
        "=" + GHL + "/contacts/{{ $('¿Sin respuesta al video?').first().json.contactId }}/tags",
        cuerpo='{"tags": ["video-recordatorio"]}', onError="continueRegularOutput"),
]

con = {}


def une(a, b, tipo="main", salida=0):
    con.setdefault(a, {}).setdefault(tipo, [])
    while len(con[a][tipo]) <= salida:
        con[a][tipo].append([])
    con[a][tipo][salida].append({"node": b, "type": tipo, "index": 0})


cadena = ["Mensaje WhatsApp (GHL)", "Normalizar entrada", "Esperar ráfaga (12 s)", "GHL contacto",
          "GHL oportunidades", "GHL conversación", "GHL mensajes", "Analizar", "¿Primer contacto?"]
for a, b in zip(cadena, cadena[1:]):
    une(a, b)
une("¿Primer contacto?", "GHL crear oportunidad", salida=0)
une("GHL crear oportunidad", "GHL guardar anuncio")
une("GHL guardar anuncio", "Maripino")
une("¿Primer contacto?", "Maripino", salida=1)
une("Maripino", "Preparar salida", salida=0)
une("Maripino", "Respuesta de respaldo", salida=1)
une("Respuesta de respaldo", "Preparar salida")
une("Preparar salida", "¿Es real? (no simulación)")
une("¿Es real? (no simulación)", "Separar mensajes", salida=0)
for a, b in [("Separar mensajes", "GHL enviar WhatsApp"), ("GHL enviar WhatsApp", "Plan CRM"),
             ("Plan CRM", "¿Datos nuevos?"), ("GHL actualizar contacto", "¿Hay correo nuevo?"),
             ("GHL guardar correo", "GHL etiquetas"),
             ("GHL etiquetas", "GHL pipelines"), ("GHL pipelines", "Etapa destino"),
             ("Etapa destino", "¿Mover oportunidad?"), ("GHL mover oportunidad", "¿Atención personalizada?"),
             ("Armar aviso", "GHL nota"), ("GHL nota", "Correo a xzenauto@gmail.com")]:
    une(a, b)
une("¿Datos nuevos?", "GHL actualizar contacto", salida=0)
une("¿Datos nuevos?", "¿Hay correo nuevo?", salida=1)
une("¿Hay correo nuevo?", "GHL guardar correo", salida=0)
une("¿Hay correo nuevo?", "GHL etiquetas", salida=1)
une("¿Mover oportunidad?", "GHL mover oportunidad", salida=0)
une("¿Mover oportunidad?", "¿Atención personalizada?", salida=1)
une("¿Atención personalizada?", "Armar aviso", salida=0)
une("¿Atención personalizada?", "¿Cita agendada?", salida=1)
une("¿Cita agendada?", "GHL datos cita", salida=0)
une("GHL datos cita", "Armar correo cita")
une("Armar correo cita", "Correo cita a xzenauto@gmail.com")
une("Correo cita a xzenauto@gmail.com", "¿Envió el video?")
une("¿Cita agendada?", "¿Envió el video?", salida=1)
une("¿Envió el video?", "Esperar 1 hora", salida=0)
for a, b in [("Esperar 1 hora", "Recordatorio · contacto"), ("Recordatorio · contacto", "Recordatorio · conversación"),
             ("Recordatorio · conversación", "Recordatorio · mensajes"),
             ("Recordatorio · mensajes", "¿Sin respuesta al video?"),
             ("¿Sin respuesta al video?", "GHL enviar recordatorio"),
             ("GHL enviar recordatorio", "GHL etiqueta recordatorio")]:
    une(a, b)
une("OpenAI", "Maripino", "ai_languageModel")
une("Salida estructurada", "Maripino", "ai_outputParser")
for t in ["consultar_disponibilidad", "agendar_cita"]:
    une(t, "Maripino", "ai_tool")

# Envío de mensajes de uno en uno con pausa, como una persona.
for n in nodos:
    if n["name"] == "GHL enviar WhatsApp":
        n["parameters"]["options"] = {"batching": {"batch": {"batchSize": 1, "batchInterval": 2000}}}

agente = {"name": "Maripino · Agente WhatsApp xzen Auto", "nodes": nodos, "connections": con,
          "settings": {"executionOrder": "v1", "timezone": "America/Mexico_City"}}


# ---------------------------------------------------------------- configuración (una sola vez)
CREAR_CAMPOS = r"""const quiero = ['Anuncio de origen', 'Desde dónde nos contacta', 'Invierte en anuncios de Facebook', 'Leads estimados por semana'];
const existentes = ($json.customFields ?? []).map((f) => f.name.trim().toLowerCase());
return quiero.filter((n) => !existentes.includes(n.toLowerCase())).map((name) => ({ json: { name } }));
"""
cfg_nodos = [
    nodo("Ejecutar una vez", "n8n-nodes-base.manualTrigger", 1, [0, 0], {}),
    ghl("GHL · Campos actuales", [220, 0], "GET", GHL + "/locations/" + LOCATION_ID + "/customFields",
        query={"model": "contact"}),
    nodo("Campos que faltan", "n8n-nodes-base.code", 2, [440, 0], {"jsCode": CREAR_CAMPOS}),
    ghl("GHL · Crear campo", [660, 0], "POST", GHL + "/locations/" + LOCATION_ID + "/customFields",
        cuerpo="={{ JSON.stringify({ name: $json.name, dataType: 'TEXT', model: 'contact' }) }}"),
]
cfg_con = {}
for a, b in [("Ejecutar una vez", "GHL · Campos actuales"), ("GHL · Campos actuales", "Campos que faltan"),
             ("Campos que faltan", "GHL · Crear campo")]:
    cfg_con[a] = {"main": [[{"node": b, "type": "main", "index": 0}]]}
configuracion = {"name": "Maripino · Configuración GHL", "nodes": cfg_nodos, "connections": cfg_con,
                 "settings": {"executionOrder": "v1"}}

for nombre, wf in [("maripino-agente.json", agente), ("maripino-configuracion.json", configuracion)]:
    (AQUI / nombre).write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n")
    print("escrito", nombre, len(wf["nodes"]), "nodos")
