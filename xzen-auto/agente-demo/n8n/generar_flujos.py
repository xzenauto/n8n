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
CRED_SUPABASE = {"supabaseApi": {"id": "QIVohgUOAGTuwYd1", "name": "XzenAuto"}}
SUPABASE = "https://fllhjemdhohsewqwzrpc.supabase.co/rest/v1/rpc/"
# Buffer de mensajes en Supabase (tabla maripino_buffer, ver supabase/maripino_buffer.sql).
# Activar solo cuando la tabla y sus funciones existan.
USAR_BUFFER = False
# Credencial "Facebook Graph API" con un token de Meta con permiso ads_read (se crea a mano en n8n).
CRED_META = {"facebookGraphApi": {"id": None, "name": "Meta Ads XzenAuto"}}
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
        "cita": "KZIraI4WWxYrTv7FaRql",  # Cita agendada (fecha y hora)
    },
    # Todos estos campos están en la carpeta de campos de contacto "Maripino · xzen Auto" (xuN41xy4vPvelwkG0zpP).
    "correoAviso": "xzenauto@gmail.com",
}

rutas = json.loads(json.dumps(CONFIG))
for v in rutas["verticales"].values():
    v["instrucciones"] = (AQUI.parent / v.pop("prompt")).read_text().strip()
rutas.pop("_descripcion", None)
rutas.pop("_textos_anuncio", None)
CFG_JS = "const CFG = " + json.dumps(CFG, ensure_ascii=False) + ";\nconst RUTAS = " + json.dumps(
    rutas, ensure_ascii=False) + ";\n"

# ---------------------------------------------------------------- código
ROBOT_JS = r"""// Sin caritas: cualquier emoji de cara o gesto se cambia por 🤖, y solo queda un robot por mensaje.
const soloRobots = (t) => String(t ?? '')
  .replace(/[\u{1F600}-\u{1F64F}\u{1F910}-\u{1F92F}\u{1F970}-\u{1F97A}\u{1F9D0}\u{263A}\u{1F44D}\u{1F44F}\u{1F64C}\u{1F64F}\u{1F389}]️?/gu, '🤖')
  .replace(/🤖/gu, ((primero) => () => (primero ? ((primero = false), '🤖') : ''))(true))
  .replace(/[ \t]{2,}/g, ' ').replace(/ ([?.!,])/g, '$1').trim();
"""

NOMBRE_JS = r"""// Nombre para saludar: el de pila si parece de persona; vacío si el nombre del perfil parece de negocio.
const nombreParaSaludo = (n) => {
  const t = String(n ?? '').replace(/[^\p{L}\s'.-]/gu, ' ').replace(/\s+/g, ' ').trim();
  if (!t) return '';
  const bajo = t.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  if (/\b(viaj|tour|travel|agencia|turism|bienestar|natural|grupo|servicio|tienda|mueble|hotel|vacacion|express|club|studio|estudio|consultor|empresa|negocio|store|shop|boutique|inc|sa de cv)/.test(bajo)) return '';
  const partes = t.split(' ');
  if (partes.length > 4 || partes[0].length < 2) return '';
  return partes[0].charAt(0).toUpperCase() + partes[0].slice(1).toLowerCase();
};
"""

NORMALIZAR = r"""// Webhook del flujo de GHL "Cliente respondió" (WhatsApp).
const b = $json.body ?? $json;
const contactId = b.contact_id || b.contactId || b.customData?.contact_id || b.contact?.id;
if (!contactId) return [];
// "Contacto creado" no trae mensaje (y en el primer mensaje GHL no dispara "Cliente respondió"):
// en ese caso el texto se lee de la conversación de GHL. Si trae mensaje, solo WhatsApp (tipo 19).
const contactoCreado = !b.message && b.simulacion !== true;
const tipo = Number(b.message?.type);
if (!contactoCreado && tipo && tipo !== 19) return [];
const attr = b.contact?.lastAttributionSource || b.contact?.attributionSource || b.attributionSource || {};
return [{ json: {
  contactId: String(contactId),
  texto: String(b.message?.body ?? b.customData?.mensaje ?? '').trim(),
  adId: attr.adId || null,
  recibidoEn: new Date().toISOString(),
  contactoCreado,
  // Pruebas: {"simulacion": true, "historial": [{"rol": "cliente"|"maripino", "texto": "..."}]}
  simulacion: b.simulacion === true,
  historialSimulado: Array.isArray(b.historial) ? b.historial : null,
} }];
"""

ANALIZAR = CFG_JS + NOMBRE_JS + r"""
const ent = $('Normalizar entrada').first().json;
const contacto = $('GHL contacto').first().json.contact ?? {};
const opps = $('GHL oportunidades').first().json.opportunities ?? [];
const opp = opps.find((o) => o.pipelineId === CFG.pipelineId) ?? null;
const tags = (contacto.tags ?? []).map((t) => String(t).toLowerCase());
const limpio = (s) => String(s ?? '').trim();

// 1. Con una persona del equipo o apagado a mano (etiqueta maripino-off): Maripino no contesta.
if (tags.includes('atencion-personalizada') || tags.includes('maripino-off')) return [];
// Solo atiende leads en la primera columna ("Nuevo lead") o sin oportunidad todavía.
// Si la oportunidad está en otra columna (Contactado, Agendado, Cerrado, Atención personalizada) o ya no está abierta, no habla.
if (opp && (opp.pipelineStageId !== CFG.etapas.nuevo || (opp.status && opp.status !== 'open'))) return [];

// 2. ¿Viene de un anuncio? Solo atendemos leads de anuncios (la coexistencia trae también contactos personales).
const fuentes = [contacto.attributionSource, contacto.lastAttributionSource, ...(contacto.attributions ?? [])];
let anuncioId = [ent.adId, ...fuentes.map((a) => a?.adId)].find((id) => id && RUTAS.anuncios[id]) ?? null;
if (!anuncioId) {
  const texto = JSON.stringify(contacto);
  anuncioId = Object.keys(RUTAS.anuncios).find((id) => texto.includes(id)) ?? null;
}
// Si Meta no mandó el ID del anuncio, el mensaje predeterminado del anuncio también identifica al lead y su giro.
const sinAcentos = (t) => String(t ?? '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
let textosCliente = ent.texto;
try { textosCliente += ' ' + JSON.stringify($('GHL mensajes').first().json.messages ?? ''); } catch (e) {}
textosCliente = sinAcentos(textosCliente);
const verticalPorTexto = Object.entries(RUTAS.verticales)
  .find(([, v]) => v.activo && (v.textos_anuncio ?? []).some((t) => textosCliente.includes(t)))?.[0] ?? null;

const esPrueba = tags.includes('test-maripino') || ent.simulacion;
if (!anuncioId && !verticalPorTexto && !tags.includes('maripino') && !esPrueba) return [];
const anuncio = anuncioId ? RUTAS.anuncios[anuncioId] : null;

let vertical = anuncio?.vertical ?? verticalPorTexto ?? (esPrueba ? 'agencia_viajes' : RUTAS.vertical_por_defecto);
if (!RUTAS.verticales[vertical]?.activo) vertical = RUTAS.vertical_por_defecto;
const conf = RUTAS.verticales[vertical];

// 3. Campos del contacto.
const valor = (id) => {
  const v = (contacto.customFields ?? []).find((c) => c.id === id)?.value;
  return Array.isArray(v) ? v.join(', ') : limpio(v);
};
const valores = Object.fromEntries(Object.entries(CFG.campos).map(([k, id]) => [k, valor(id)]));
const anuncioTexto = anuncio ? `${anuncio.nombre} (${anuncioId})`
  : (valores.anuncio || (verticalPorTexto ? 'Anuncio de Meta (sin ID)' : 'Prueba / sin anuncio'));

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
  const USAR_BUFFER = __USAR_BUFFER__;
  const ultimo = msgs[msgs.length - 1];
  const buffer = USAR_BUFFER ? $('Buffer · tomar').first().json : { textos: [] };
  if (USAR_BUFFER) {
    // El buffer ya garantiza que solo responde la ejecución del último mensaje de la ráfaga.
    // Si mientras esperábamos ya le contestó alguien (otra ejecución o una persona), no respondemos.
    if (ultimo && ultimo.direction === 'outbound' && new Date(ultimo.dateAdded) > new Date(buffer.primero_en)) return [];
    if (!(buffer.textos ?? []).length && (!ultimo || ultimo.direction !== 'inbound')) return [];
  } else {
    // Sin buffer: si después de este mensaje llegó otro, lo atiende la ejecución de ese otro mensaje;
    // si ya hubo una respuesta posterior (bot o persona), no contestamos de nuevo.
    if (ent.contactoCreado && (!ultimo || ultimo.direction !== 'inbound')) return [];
    let mio = -1;
    for (let i = msgs.length - 1; ent.texto && i >= 0; i--) {
      if (msgs[i].direction === 'inbound' && limpio(msgs[i].body) === ent.texto) { mio = i; break; }
    }
    if (mio >= 0 && msgs.slice(mio + 1).length > 0) return [];
  }
  let corte = msgs.length;
  while (corte > 0 && msgs[corte - 1].direction === 'inbound') corte--;
  nuevos = (buffer.textos ?? []).length ? buffer.textos.map(limpio)
    : msgs.slice(corte).map((m) => limpio(m.body) || '[audio, imagen o archivo sin texto]');
  historial = msgs.slice(Math.max(0, corte - 20), corte)
    .map((m) => ({ rol: m.direction === 'inbound' ? 'Cliente' : 'xzen Auto', texto: limpio(m.body) }))
    .filter((m) => m.texto);
  if (!nuevos.length) nuevos = [ent.texto || '[mensaje sin texto]'];
}

const ahora = new Date().toLocaleString('es-MX', { timeZone: 'America/Mexico_City', dateStyle: 'full', timeStyle: 'short' });
const p = (v) => v || 'PENDIENTE';
// Calendario con fecha ISO (para cruzar con los horarios del calendario) y "hoy" / "mañana" marcados.
const dias = Array.from({ length: 14 }, (_, i) => {
  const t = new Date(Date.now() + i * 864e5);
  const iso = t.toLocaleDateString('en-CA', { timeZone: 'America/Mexico_City' });
  const largo = t.toLocaleDateString('es-MX', { timeZone: 'America/Mexico_City', weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  return `${iso} = ${largo}${i === 0 ? ' (HOY)' : i === 1 ? ' (MAÑANA)' : ''}`;
});
const prompt = `# Fecha y hora actual (Ciudad de México)
${ahora}

# Calendario (úselo siempre para nombrar los días; no calcule días de la semana; cruce la fecha ISO de cada horario con esta lista)
${dias.join('\n')}

# Datos del cliente en el CRM
- Nombre para saludar: ${nombreParaSaludo([contacto.firstName, contacto.lastName].filter(Boolean).join(' ')) || `(ninguno: no use nombre al saludar; el perfil se llama "${limpio([contacto.firstName, contacto.lastName].filter(Boolean).join(' ')) || 'sin nombre'}" y parece de negocio o no se sabe)`}${contacto.companyName ? `\n- Negocio: ${contacto.companyName}` : ''}${contacto.email ? `\n- Correo: ${contacto.email}` : ''}
- Anuncio de origen: ${anuncioTexto}
- Desde dónde nos contacta: ${p(valores.ubicacion)}
- ¿Invierte en anuncios de Facebook?: ${p(valores.inversion)}
- Leads estimados por semana: ${p(valores.leads)}
- Video ya enviado: ${tags.includes('video-enviado') ? 'sí' : 'no'}
- Cita ya agendada: ${tags.includes('cita-agendada') ? 'sí' + (valores.cita ? ` (${valores.cita})` : '') : 'no'}${tags.includes('no-asistio') ? `\n- IMPORTANTE: el cliente NO se presentó a su llamada anterior${valores.cita ? ` (${valores.cita})` : ''}. Salúdelo con amabilidad, sin reproches, pregúntele si sigue interesado y, si es así, ofrézcale reagendar la llamada.` : ''}

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
  nombreCompleto: [contacto.firstName, contacto.lastName].map(limpio).filter(Boolean).join(' '),
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
- Para saludar use solo el "Nombre para saludar" del CRM o el nombre que el cliente le diga; si no hay, salude sin nombre (nunca use el nombre de un negocio como si fuera de persona).
- Español de México. Mensajes cortos (máximo 3-4 líneas cada uno), como en WhatsApp.
- Una sola pregunta por turno. Emojis: NUNCA use caritas (😊, 😉, 🙌, 🙏…); si quiere poner un emoji, use el robot 🤖 (máximo uno por mensaje). Para datos prácticos puede usar 📅 o 💻.
- Sea breve: normalmente 1 mensaje y como máximo 2 por turno; no repita en un mensaje lo que ya dijo en otro.
- No responda "¡Perfecto!" o "¡Excelente!" a una respuesta negativa (p. ej. "no invierto"); use algo natural como "Entiendo" o "Gracias por contarme".
- No sea insistente: si el cliente no contestó una pregunta, no la repita en cada mensaje.
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

# Preguntas frecuentes
Úselas SOLO para responder si el cliente lo pregunta; no las mencione por iniciativa propia. Responda breve y con sus palabras.
- ¿Cuántos agentes o usuarios? No hay límite de agentes de ventas ni de cuentas. El agente de IA es uno solo, adaptado a las necesidades de su negocio.
- ¿Qué WhatsApp se conecta? WhatsApp Business. Se pueden conectar varias cuentas, aunque lo óptimo es dejar un número oficial del negocio dedicado a los clientes. Pueden seguir usando WhatsApp en el celular como siempre.
- ¿Celular o computadora? Las dos: hay app para el celular y también se usa desde la computadora.
- ¿Qué canales? WhatsApp, Instagram, Facebook, TikTok y email, todos centralizados en un solo lugar.
- ¿Y los curiosos o "preguntones"? La IA les resuelve las dudas y les recopila todos los datos del viaje (destino, fechas, número de viajeros, presupuesto), así el equipo solo dedica su tiempo a quien ya está listo para cotizar y no a responder lo mismo una y otra vez.
- ¿Me sirve si estoy empezando o tengo pocos leads? Es el mejor momento: empezar con el sistema permite ordenar y optimizar el trabajo desde el primer día, responder rápido a cada viajero y crecer sin saturarse. Es mucho más fácil arrancar con un proceso ordenado que corregirlo cuando ya hay volumen.
- ¿Cómo es la llamada? Por Zoom, de 20 a 30 minutos, con el equipo de xzen Auto. El enlace le llega en la confirmación de la cita. (Nunca diga Google Meet ni otra plataforma.)
- ¿Cuánto tarda la implementación? Entre 3 y 5 días.
- ¿Hay contrato? Sí, con una permanencia inicial de 3 meses.
- ¿Cómo sabe la IA lo de mi agencia? Guardamos toda la información de la agencia y sus promociones en un documento para que la IA responda a los clientes con información real.
- ¿Se conecta con mi sistema de reservas, Amadeus, mi CRM u otra herramienta? No afirme ni niegue: dígale que las integraciones con su sistema se revisan con el equipo en la llamada, según lo que use su agencia.
Si preguntan algo que no esté aquí ni en esta guía, NO lo invente (ni que sí ni que no): dígale que es un buen punto para revisarlo en la llamada con el equipo.

# Precios
Nunca dé precios, rangos ni planes. El precio depende de las necesidades de su negocio y se presenta en la llamada, con una propuesta a su medida.

# Cómo agendar
1. Use consultar_disponibilidad y ofrezca 2 o 3 horarios concretos en hora de Ciudad de México (si el cliente está en otra zona horaria, aclárelo). Nunca invente horarios.
   Nombre cada horario con el día de la semana y la fecha que le corresponden en el Calendario (p. ej. "lunes 2 de noviembre").
   Diga "hoy" o "mañana" SOLO si esa fecha está marcada (HOY) o (MAÑANA) en el Calendario.
   Si el cliente pide un día sin horarios disponibles (p. ej. "mañana"), dígaselo claramente ("mañana ya no tengo espacios") y ofrezca los más cercanos con su día y fecha.
2. Cuando elija horario, pida en un solo mensaje lo que falte: nombre completo, nombre de su negocio y correo.
   NO llame a agendar_cita hasta tener los tres datos dichos por el cliente.
3. Agende con agendar_cita usando EXACTAMENTE el inicio de un horario devuelto por consultar_disponibilidad.
4. Solo si agendar_cita respondió correctamente (devuelve un id), confirme día y hora y dígale que le llegará la confirmación.
   Si respondió error 404 (Not Found): NO es el horario, es que faltan datos. Pida nombre completo (nombre y apellido),
   nombre de su negocio y correo, y agende después con el mismo horario.
   Si respondió otro error, discúlpese, consulte de nuevo la disponibilidad y ofrezca otros horarios.
5. Si en el CRM dice "Cita ya agendada: sí", NO vuelva a agendar ni repita los datos de la cita en cada mensaje.
   (Después de agendar, la conversación la sigue el equipo; usted solo cierra con una despedida breve.)
   Si el cliente solo agradece o se despide, responda con UN mensaje corto y cordial.
   Si quiere cambiarla o cancelarla, márquelo para atención personalizada.
Si todavía no quiere agendar, pregúntele si le puede escribir en un par de días.

# Atención personalizada
Si el cliente pide hablar con una persona, está molesto, o pregunta algo que no puede responder con certeza, marque atencion_personalizada = true, explique el motivo y dígale que alguien del equipo le escribirá en breve.

# Formato de salida
- mensajes: 1 o 2 mensajes de WhatsApp para el cliente, en orden.
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
        "mensajes": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 2},
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
  mensajes: ['Permítame un momento, en breve una persona de nuestro equipo le escribe por aquí 🤖'],
  datos: {}, video_enviado: false, cita_agendada: false,
  atencion_personalizada: true, motivo_atencion: 'Error del agente automático', resumen: 'Error del agente',
} } }];
"""

PREPARAR = ROBOT_JS + r"""const out = $input.first().json.output ?? {};
const c = $('Analizar').first().json;
let mensajes = (Array.isArray(out.mensajes) ? out.mensajes : [out.mensajes])
  .map((m) => soloRobots(m)).filter(Boolean).slice(0, 3);
if (!mensajes.length) mensajes = ['Permítame un momento y le confirmo 🤖'];

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

// Nombre y negocio solo se guardan si aparecen en lo que escribió el cliente (la IA a veces los saca del perfil).
const sinAc = (t) => String(t ?? '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
const lineasCliente = sinAc(c.prompt.split('# Conversación previa')[1] ?? '').split('\n')
  .filter((l, i, a) => l.startsWith('cliente:') || a.slice(0, i).some((x) => x.startsWith('# mensaje(s) nuevo(s)')))
  .join(' ');
const dijo = (v) => limpio(v).length > 1 && lineasCliente.includes(sinAc(limpio(v)));
if (!dijo(d.negocio)) d.negocio = '';
if (!dijo(d.nombre_completo)) d.nombre_completo = '';

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
  // Cuando el cliente dice el nombre de su negocio, la oportunidad pasa a llamarse "Negocio (Nombre)".
  nombreOportunidad: contacto.companyName
    ? `${contacto.companyName} (${[contacto.firstName || c.nombre, contacto.lastName].filter(Boolean).join(' ')})` : null,
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

RECORDATORIO = NOMBRE_JS + r"""// ¿Sigue sin responder desde que le mandamos el video?
const contacto = $('Recordatorio · contacto').first().json.contact ?? {};
const oppRec = ($('Recordatorio · oportunidad').first().json.opportunities ?? [])[0];
if (oppRec && (oppRec.pipelineStageId !== 'fe64e5e5-f19a-4c8a-af74-20d0d2c12868' || (oppRec.status && oppRec.status !== 'open'))) return []; // ya no está en Nuevo lead
const tags = (contacto.tags ?? []).map((t) => String(t).toLowerCase());
if (['atencion-personalizada', 'maripino-off', 'video-recordatorio'].some((t) => tags.includes(t))) return [];
const horaMx = Number(new Date().toLocaleString('en-US', { timeZone: 'America/Mexico_City', hour: 'numeric', hour12: false })) % 24;
if ((horaMx >= 23 || horaMx < 8) && !tags.includes('test-maripino')) return []; // de noche no se escribe
let msgs = [];
try { const m = $json.messages; msgs = (m && (m.messages || m)) || []; } catch (e) {}
if (!Array.isArray(msgs)) msgs = [];
msgs = msgs.filter((m) => /WHATSAPP/.test(m.messageType ?? '')).sort((a, b) => new Date(a.dateAdded) - new Date(b.dateAdded));
let video = -1;
msgs.forEach((m, i) => { if (m.direction === 'outbound' && /youtu\.?be/.test(m.body ?? '')) video = i; });
if (video < 0 || msgs.slice(video + 1).some((m) => m.direction === 'inbound')) return [];
const nombre = nombreParaSaludo([contacto.firstName, contacto.lastName].filter(Boolean).join(' '));
return [{ json: {
  contactId: contacto.id,
  mensaje: `${nombre ? `Hola, ${nombre}. ` : 'Hola. '}¿Pudo ver el video? 🤖 Nos encantaría saber qué le pareció.`,
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
ANALIZAR = ANALIZAR.replace("__USAR_BUFFER__", "true" if USAR_BUFFER else "false")

nodos = [
    nodo("Mensaje WhatsApp (GHL)", "n8n-nodes-base.webhook", 2, [0, 300],
         {"httpMethod": "POST", "path": "xzen-maripino", "options": {}},
         webhookId=str(uuid.uuid5(uuid.NAMESPACE_URL, "maripino/webhook"))),
    nodo("Normalizar entrada", "n8n-nodes-base.code", 2, [200, 300], {"jsCode": NORMALIZAR}),
    nodo("Buffer · guardar", "n8n-nodes-base.httpRequest", 4.2, [300, 300], {
        "method": "POST", "url": SUPABASE + "maripino_buffer_agregar",
        "authentication": "predefinedCredentialType", "nodeCredentialType": "supabaseApi",
        "sendBody": True, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ p_contact_id: $json.contactId, p_texto: $json.texto, p_origen: $json.contactoCreado ? 'contacto_creado' : 'mensaje' }) }}",
        "options": {}}, CRED_SUPABASE),
    nodo("Esperar ráfaga (12 s)", "n8n-nodes-base.wait", 1.1, [400, 300],
         {"amount": "={{ $('Normalizar entrada').first().json.simulacion ? 1 : $('Normalizar entrada').first().json.contactoCreado ? " + ("25" if USAR_BUFFER else "40") + " : 12 }}", "unit": "seconds"},
         webhookId=str(uuid.uuid5(uuid.NAMESPACE_URL, "maripino/wait"))),
    nodo("Buffer · tomar", "n8n-nodes-base.httpRequest", 4.2, [500, 300], {
        "method": "POST", "url": SUPABASE + "maripino_buffer_tomar",
        "authentication": "predefinedCredentialType", "nodeCredentialType": "supabaseApi",
        "sendBody": True, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ p_contact_id: $('Normalizar entrada').first().json.contactId, p_id: $('Buffer · guardar').first().json.id }) }}",
        "options": {}}, CRED_SUPABASE),
    si("¿Último mensaje?", [550, 300], "={{ $json.es_ultimo === true }}"),
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
               " name: $json.nombreCompleto || $json.nombre || 'Prospecto' }) }}",
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
    ghl("agendar_cita", [2540, 560], "POST",
        # Si faltan nombre completo, negocio o un correo válido, se manda a una ruta inexistente: GHL responde
        # "Cannot POST /FALTAN-DATOS..." y Maripino sabe que debe pedirlos antes de agendar.
        "={{ /^\\S+@\\S+\\.\\S+$/.test($fromAI('email', 'Correo electrónico del cliente', 'string').trim())"
        " && $fromAI('nombre_completo', 'Nombre completo del cliente (nombre y apellido)', 'string').trim().split(/\\s+/).length > 1"
        " && $fromAI('negocio', 'Nombre propio del negocio del cliente', 'string').trim().length > 1"
        " ? '" + GHL + "/calendars/events/appointments'"
        " : '" + GHL + "/FALTAN-DATOS-pida-nombre-completo-negocio-y-correo-antes-de-agendar' }}",
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
    ghl("GHL reiniciar seguimientos", [4200, 160], "DELETE",
        "=" + GHL + "/contacts/{{ $('Plan CRM').first().json.contactId }}/tags",
        cuerpo='{"tags": ["seguimiento-1", "seguimiento-2", "seguimiento-3", "no-asistio"]}', onError="continueRegularOutput",
        executeOnce=True),
    ghl("GHL pipelines", [4300, 300], "GET", GHL + "/opportunities/pipelines", query={"locationId": LOCATION_ID},
        onError="continueRegularOutput", alwaysOutputData=True),
    nodo("Etapa destino", "n8n-nodes-base.code", 2, [4500, 300], {"jsCode": ETAPA}),
    si("¿Mover oportunidad?", [4700, 300], "={{ $json.moverOportunidad }}"),
    ghl("GHL mover oportunidad", [4900, 200], "PUT", "=" + GHL + "/opportunities/{{ $json.oportunidadId }}",
        cuerpo="={{ JSON.stringify({ pipelineId: '" + CFG["pipelineId"] + "', pipelineStageId: $json.destino }) }}",
        onError="continueRegularOutput"),
    si("¿Renombrar oportunidad?", [4600, 160], "={{ !!($('Plan CRM').first().json.nombreOportunidad && $('Plan CRM').first().json.oportunidadId) }}"),
    ghl("GHL renombrar oportunidad", [4800, 60], "PUT", "=" + GHL + "/opportunities/{{ $('Plan CRM').first().json.oportunidadId }}",
        cuerpo="={{ JSON.stringify({ name: $('Plan CRM').first().json.nombreOportunidad }) }}", onError="continueRegularOutput"),
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
    ghl("GHL guardar cita", [5500, 820], "PUT", "=" + GHL + "/contacts/{{ $('Etapa destino').first().json.contactId }}",
        cuerpo="={{ (() => { const a = $json.appointment ?? $json; const t = a.startTime ?? $('Etapa destino').first().json.cita?.inicio;"
               " return JSON.stringify({ customFields: [{ id: '" + CFG["campos"]["cita"] + "', field_value: t ? new Date(t).toLocaleString('es-MX',"
               " { timeZone: 'America/Mexico_City', dateStyle: 'full', timeStyle: 'short' }) + ' (hora de Ciudad de México)' : 'Agendada' }] }); })() }}",
        onError="continueRegularOutput"),
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
    ghl("Recordatorio · oportunidad", [5800, 560], "GET", GHL + "/opportunities/search",
        query={"location_id": LOCATION_ID, "contact_id": "={{ $('Plan CRM').first().json.contactId }}", "pipeline_id": CFG["pipelineId"]},
        onError="continueRegularOutput", alwaysOutputData=True),
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


if not USAR_BUFFER:
    nodos = [n for n in nodos if n["name"] not in ("Buffer · guardar", "Buffer · tomar", "¿Último mensaje?")]
cadena = (["Mensaje WhatsApp (GHL)", "Normalizar entrada", "Buffer · guardar", "Esperar ráfaga (12 s)", "Buffer · tomar",
           "¿Último mensaje?", "GHL contacto"] if USAR_BUFFER else
          ["Mensaje WhatsApp (GHL)", "Normalizar entrada", "Esperar ráfaga (12 s)", "GHL contacto"]) + [
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
             ("GHL etiquetas", "GHL reiniciar seguimientos"), ("GHL reiniciar seguimientos", "GHL pipelines"), ("GHL pipelines", "Etapa destino"),
             ("Etapa destino", "¿Mover oportunidad?"), ("GHL mover oportunidad", "¿Renombrar oportunidad?"),
             ("GHL renombrar oportunidad", "¿Atención personalizada?"),
             ("Armar aviso", "GHL nota"), ("GHL nota", "Correo a xzenauto@gmail.com")]:
    une(a, b)
une("¿Datos nuevos?", "GHL actualizar contacto", salida=0)
une("¿Datos nuevos?", "¿Hay correo nuevo?", salida=1)
une("¿Hay correo nuevo?", "GHL guardar correo", salida=0)
une("¿Hay correo nuevo?", "GHL etiquetas", salida=1)
une("¿Mover oportunidad?", "GHL mover oportunidad", salida=0)
une("¿Mover oportunidad?", "¿Renombrar oportunidad?", salida=1)
une("¿Renombrar oportunidad?", "GHL renombrar oportunidad", salida=0)
une("¿Renombrar oportunidad?", "¿Atención personalizada?", salida=1)
une("¿Atención personalizada?", "Armar aviso", salida=0)
une("¿Atención personalizada?", "¿Cita agendada?", salida=1)
une("¿Cita agendada?", "GHL datos cita", salida=0)
une("GHL datos cita", "GHL guardar cita")
une("GHL guardar cita", "Armar correo cita")
une("Armar correo cita", "Correo cita a xzenauto@gmail.com")
une("Correo cita a xzenauto@gmail.com", "¿Envió el video?")
une("¿Cita agendada?", "¿Envió el video?", salida=1)
une("¿Envió el video?", "Esperar 1 hora", salida=0)
for a, b in [("Esperar 1 hora", "Recordatorio · contacto"), ("Recordatorio · contacto", "Recordatorio · oportunidad"),
             ("Recordatorio · oportunidad", "Recordatorio · conversación"),
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


# ---------------------------------------------------------------- seguimientos (cada 15 min)
SEG_CANDIDATOS = NOMBRE_JS + r"""// Leads de Maripino que pueden necesitar seguimiento.
const fuera = ['atencion-personalizada', 'maripino-off', 'cita-agendada', 'seguimiento-3', 'no-asistio'];
// Solo leads cuya oportunidad sigue en la primera columna ("Nuevo lead") o que aún no tienen oportunidad.
const opps = $('GHL oportunidades').first().json.opportunities ?? [];
const fueraDeNuevo = new Set(opps.filter((o) => o.pipelineStageId !== 'fe64e5e5-f19a-4c8a-af74-20d0d2c12868' || (o.status && o.status !== 'open'))
  .map((o) => o.contactId || o.contact?.id));
return ($('GHL leads de Maripino').first().json.contacts ?? [])
  .filter((c) => !fueraDeNuevo.has(c.id))
  .map((c) => ({ id: c.id, nombre: nombreParaSaludo([c.firstName, c.lastName].filter(Boolean).join(' ')), tags: (c.tags ?? []).map((t) => String(t).toLowerCase()) }))
  .filter((c) => c.tags.includes('maripino') && !fuera.some((t) => c.tags.includes(t)))
  .map((c) => ({ json: { contactId: c.id, nombre: c.nombre, tags: c.tags } }));
"""

SEG_DECIDIR = r"""// ¿A quién le toca seguimiento ahora? Horas desde el último mensaje de Maripino sin respuesta: 5, 7 y 12.
const HORAS = [5, 7, 12];
const H = 3600e3;
const candidatos = $('Candidatos').all();
const ahora = Date.now();
const horaMx = Number(new Date().toLocaleString('en-US', { timeZone: 'America/Mexico_City', hour: 'numeric', hour12: false })) % 24;
const silencio = horaMx >= 23 || horaMx < 8;
const salida = [];

$input.all().forEach((item, i) => {
  const c = candidatos[i]?.json;
  if (!c) return;
  const prueba = c.tags.includes('test-maripino');
  const u = prueba ? 60e3 : H; // en pruebas, minutos en lugar de horas
  if (silencio && !prueba) return;

  let msgs = [];
  try { const m = item.json.messages; msgs = (m && (m.messages || m)) || []; } catch (e) {}
  if (!Array.isArray(msgs)) msgs = [];
  msgs = msgs.filter((m) => /WHATSAPP/.test(m.messageType ?? '')).sort((a, b) => new Date(a.dateAdded) - new Date(b.dateAdded));
  const ultimoIn = [...msgs].reverse().find((m) => m.direction === 'inbound');
  if (!ultimoIn) return;
  const tIn = new Date(ultimoIn.dateAdded).getTime();
  const despues = msgs.filter((m) => m.direction === 'outbound' && new Date(m.dateAdded).getTime() > tIn);
  if (!despues.length) return; // aún no le hemos respondido
  if (ahora - tIn > 23.5 * H) return; // fuera de la ventana de 24 h de WhatsApp

  const base = new Date(despues[0].dateAdded).getTime();
  const ultimoOut = new Date(despues[despues.length - 1].dateAdded).getTime();
  // El recordatorio del video cuenta como un seguimiento más.
  const recordatorio = despues.some((m) => /pudo ver el video/i.test(m.body ?? '')) ? 1 : 0;
  const hechos = Math.max([1, 2, 3].filter((k) => c.tags.includes(`seguimiento-${k}`)).length, 0) + recordatorio;
  if (hechos >= HORAS.length) return;
  const paso = hechos + 1;
  if (ahora < base + HORAS[paso - 1] * u) return;
  if (ahora - ultimoOut < (prueba ? 1 : 3) * u) return; // al menos 3 h desde nuestro último mensaje

  const historial = msgs.slice(-16).map((m) => `${m.direction === 'inbound' ? 'Cliente' : 'xzen Auto'}: ${String(m.body ?? '').trim()}`)
    .filter((l) => !l.endsWith(': ')).join('\n');
  salida.push({ json: { contactId: c.contactId, nombre: c.nombre, paso, historial } });
});
return salida;
"""

SEG_PROMPT = """Eres Maripino, asistente virtual de xzen Auto (automatización con IA para negocios, ahora para agencias de viajes).
El cliente dejó de responder por WhatsApp. Escribe UN mensaje corto de seguimiento (máximo 2-3 líneas) para retomar la conversación.
- Trate de USTED al cliente; amigable y profesional; español de México; nada de caritas (😊, 😉…): como mucho un 🤖.
- Retome la conversación con naturalidad, sin repetir textualmente mensajes anteriores.
- NUNCA vuelva a preguntar lo mismo que el último mensaje de xzen Auto (si ya se preguntó por el video, no pregunte otra vez por el video): cambie de ángulo.
- Tono ligero, nada insistente ni de reclamo; no diga "solo quería saber si…" ni "le escribo de nuevo".
- Seguimiento 1: retome con naturalidad lo pendiente. Seguimiento 2: aporte un beneficio concreto del sistema relacionado con lo que contó y vuelva a preguntar. Seguimiento 3 (último): despedida amable, deje la puerta abierta para cuando quiera retomar o agendar la llamada.
- No dé precios (se ven en la llamada). No invente datos. No diga que es un seguimiento automático.
- Responda solo con el texto del mensaje."""

SEG_CUERPO_OPENAI = ("={{ JSON.stringify({ model: 'gpt-4.1', temperature: 0.5, messages: ["
                     "{ role: 'system', content: " + json.dumps(SEG_PROMPT, ensure_ascii=False) + " },"
                     " { role: 'user', content: 'Seguimiento número ' + $json.paso + ' de 3.' + ($json.nombre ? ' Nombre para saludar: ' + $json.nombre + '.' : ' No use nombre al saludar.')"
                     " + '\\n\\nConversación:\\n' + $json.historial } ] }) }}")

SEG_MENSAJE = ROBOT_JS + r"""const d = $('¿Toca seguimiento?').all();
return $input.all().map((item, i) => ({ json: {
  ...d[i].json,
  mensaje: soloRobots(String(item.json.choices?.[0]?.message?.content ?? '').trim().replace(/^"|"$/g, '')),
} })).filter((x) => x.json.mensaje);
"""

seg_nodos = [
    nodo("Cada 15 minutos", "n8n-nodes-base.scheduleTrigger", 1.2, [0, 0],
         {"rule": {"interval": [{"field": "minutes", "minutesInterval": 15}]}}),
    ghl("GHL leads de Maripino", [200, 0], "POST", GHL + "/contacts/search",
        cuerpo=json.dumps({"locationId": LOCATION_ID, "pageLimit": 100,
                           "filters": [{"field": "tags", "operator": "contains", "value": "maripino"}]})),
    ghl("GHL oportunidades", [300, 0], "GET", GHL + "/opportunities/search",
        query={"location_id": LOCATION_ID, "pipeline_id": CFG["pipelineId"], "limit": "100"}, executeOnce=True),
    nodo("Candidatos", "n8n-nodes-base.code", 2, [400, 0], {"jsCode": SEG_CANDIDATOS}),
    ghl("GHL conversación", [600, 0], "GET", GHL + "/conversations/search",
        query={"locationId": LOCATION_ID, "contactId": "={{ $json.contactId }}", "limit": "1"},
        onError="continueRegularOutput", alwaysOutputData=True),
    ghl("GHL mensajes", [800, 0], "GET",
        "=" + GHL + "/conversations/{{ ($json.conversations || [])[0]?.id || 'sin-conversacion' }}/messages",
        query={"limit": "40"}, onError="continueRegularOutput", alwaysOutputData=True),
    nodo("¿Toca seguimiento?", "n8n-nodes-base.code", 2, [1000, 0], {"jsCode": SEG_DECIDIR}),
    nodo("OpenAI redactar", "n8n-nodes-base.httpRequest", 4.2, [1200, 0], {
        "method": "POST", "url": "https://api.openai.com/v1/chat/completions",
        "authentication": "predefinedCredentialType", "nodeCredentialType": "openAiApi",
        "sendBody": True, "specifyBody": "json", "jsonBody": SEG_CUERPO_OPENAI, "options": {},
    }, CRED_OPENAI, onError="continueRegularOutput"),
    nodo("Preparar mensaje", "n8n-nodes-base.code", 2, [1400, 0], {"jsCode": SEG_MENSAJE}),
    ghl("GHL enviar seguimiento", [1600, 0], "POST", GHL + "/conversations/messages",
        cuerpo="={{ JSON.stringify({ type: 'WhatsApp', contactId: $json.contactId, message: $json.mensaje }) }}",
        onError="continueRegularOutput"),
    ghl("GHL etiqueta seguimiento", [1800, 0], "POST",
        "=" + GHL + "/contacts/{{ $('Preparar mensaje').all()[$itemIndex].json.contactId }}/tags",
        cuerpo="={{ JSON.stringify({ tags: ['seguimiento-' + $('Preparar mensaje').all()[$itemIndex].json.paso] }) }}",
        onError="continueRegularOutput"),
]
seg_con = {}
for a, b in zip(seg_nodos, seg_nodos[1:]):
    seg_con[a["name"]] = {"main": [[{"node": b["name"], "type": "main", "index": 0}]]}
seguimientos = {"name": "Maripino · Seguimientos", "nodes": seg_nodos, "connections": seg_con,
                "settings": {"executionOrder": "v1", "timezone": "America/Mexico_City"}}

# ---------------------------------------------------------------- rescate de leads colgados (cada 2 h)
RES_CANDIDATOS = r"""// Conversaciones de WhatsApp cuyo último mensaje es del cliente y nadie ha contestado:
// de hace más de 10 minutos y menos de 23 horas (aún se le puede escribir).
// Entre las 23:00 y las 8:00 no se rescata; lo pendiente sale en la vuelta de las 8:00.
// Maripino decide después si le corresponde (solo leads de anuncios, sin atención personalizada ni maripino-off).
const horaMx = Number(new Date().toLocaleString('en-US', { timeZone: 'America/Mexico_City', hour: 'numeric', hour12: false })) % 24;
if (horaMx >= 23 || horaMx < 8) return [];
const memoria = $getWorkflowStaticData('global');
memoria.vistos = memoria.vistos || {};
const ahora = Date.now();
for (const [k, t] of Object.entries(memoria.vistos)) if (ahora - t > 3 * 864e5) delete memoria.vistos[k];
return ($json.conversations ?? [])
  .filter((c) => c.lastMessageDirection === 'inbound' && /WHATSAPP/.test(c.lastMessageType ?? ''))
  .map((c) => ({ c, t: Number(c.lastMessageDate) || new Date(c.lastMessageDate).getTime() }))
  .filter(({ t }) => ahora - t > 10 * 60e3 && ahora - t < 23 * 3600e3)
  .map(({ c, t }) => ({ clave: `${c.contactId}:${t}`, contactId: c.contactId, nombre: c.fullName || c.contactName || '' }))
  .filter((x) => !memoria.vistos[x.clave])
  .map((x) => ({ json: x }));
"""

RES_MARCAR = r"""// Recuerda lo ya enviado para no rescatarlo dos veces (si el envío falló, se reintenta en la siguiente vuelta).
const memoria = $getWorkflowStaticData('global');
memoria.vistos = memoria.vistos || {};
const cand = $('Candidatos').all();
return $input.all().map((item, i) => {
  if (!item.json.error) memoria.vistos[cand[i].json.clave] = Date.now();
  return { json: { ...cand[i].json, enviado: !item.json.error } };
});
"""

res_nodos = [
    nodo("Cada 2 horas", "n8n-nodes-base.scheduleTrigger", 1.2, [0, 0],
         {"rule": {"interval": [{"field": "cronExpression", "expression": "0 */2 * * *"}]}}),
    ghl("GHL conversaciones sin respuesta", [200, 0], "GET", GHL + "/conversations/search",
        query={"locationId": LOCATION_ID, "lastMessageDirection": "inbound", "sortBy": "last_message_date",
               "sort": "desc", "limit": "100"}),
    nodo("Candidatos", "n8n-nodes-base.code", 2, [400, 0], {"jsCode": RES_CANDIDATOS}),
    nodo("Enviar a Maripino", "n8n-nodes-base.httpRequest", 4.2, [600, 0], {
        "method": "POST", "url": "http://localhost:5678/webhook/xzen-maripino",
        "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify({ contact_id: $json.contactId, rescate: true }) }}",
        "options": {"batching": {"batch": {"batchSize": 1, "batchInterval": 3000}}},
    }, onError="continueRegularOutput"),
    nodo("Marcar visto", "n8n-nodes-base.code", 2, [800, 0], {"jsCode": RES_MARCAR}),
]
res_con = {a["name"]: {"main": [[{"node": b["name"], "type": "main", "index": 0}]]} for a, b in zip(res_nodos, res_nodos[1:])}
rescate = {"name": "Maripino · Rescate de leads sin respuesta", "nodes": res_nodos, "connections": res_con,
           "settings": {"executionOrder": "v1", "timezone": "America/Mexico_City"}}

# ---------------------------------------------------------------- reporte diario (8:00)
IDS_ANUNCIOS = list(CONFIG["anuncios"].keys())
META_CAMPOS = "ad_id,ad_name,spend,impressions,reach,clicks,actions"

REP_REPORTE = CFG_JS + r"""
const tz = 'America/Mexico_City';
const dia = (t) => new Date(t).toLocaleDateString('en-CA', { timeZone: tz });
const hoy = dia(Date.now());
const ayer = dia(Date.now() - 864e5);
const hace7 = Date.now() - 7 * 864e5;
const norm = (s) => String(s ?? '').trim();
const sinAcento = (s) => norm(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
const esc = (s) => String(s ?? '').replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const money = (n) => '$' + Number(n || 0).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const num = (n) => Number(n || 0).toLocaleString('es-MX');

// ---------- Meta
const NOMBRE_AD = Object.fromEntries(Object.entries(RUTAS.anuncios).map(([id, a]) => [id, a.nombre]));
const meta = {};
let metaError = null;
for (const [clave, nodo] of [['ayer', 'Meta ayer'], ['semana', 'Meta 7 días'], ['total', 'Meta total']]) {
  const r = $(nodo).first().json;
  if (r.error || !Array.isArray(r.data)) { metaError = r.error?.message || r.error || 'sin datos'; meta[clave] = null; continue; }
  meta[clave] = r.data.filter((x) => NOMBRE_AD[x.ad_id]).map((x) => {
    const acc = (t) => Number((x.actions ?? []).find((a) => a.action_type === t)?.value || 0);
    return { id: x.ad_id, nombre: NOMBRE_AD[x.ad_id], gasto: Number(x.spend || 0), impresiones: Number(x.impressions || 0),
      alcance: Number(x.reach || 0), clics: Number(x.clicks || 0),
      conversaciones: acc('onsite_conversion.messaging_conversation_started_7d') };
  });
  // Mismo anuncio con varios IDs (p. ej. conjunto duplicado): se suma por nombre.
  meta[clave] = Object.values(meta[clave].reduce((m, x) => {
    const a = m[x.nombre] ??= { id: x.nombre, nombre: x.nombre, gasto: 0, impresiones: 0, alcance: 0, clics: 0, conversaciones: 0 };
    for (const k of ['gasto', 'impresiones', 'alcance', 'clics', 'conversaciones']) a[k] += x[k];
    return m;
  }, {}));
}
const NOMBRES_AD = [...new Set(Object.values(NOMBRE_AD))];
const SIN_ID = 'Anuncio de Meta (sin ID)';
const anuncioDe = (l) => NOMBRE_AD[l.adId] || (/anuncio de meta/i.test(l.anuncioCampo || '') ? SIN_ID : null);
const sum = (arr, k) => (arr ?? []).reduce((s, x) => s + x[k], 0);

// ---------- GHL
const pipes = $('GHL pipelines').first().json.pipelines ?? [];
const pipe = pipes.find((p) => p.id === CFG.pipelineId);
const etapaNombre = Object.fromEntries((pipe?.stages ?? []).map((s) => [s.id, s.name]));
// Lead = contacto nuevo desde el inicio de la campaña que viene de uno de nuestros anuncios, tiene oportunidad
// en el pipeline XzenAuto o lo atiende Maripino. Sin contactos de prueba ni los importados por la coexistencia.
const INICIO = '2026-10-26';
const todasOpps = $('GHL oportunidades').first().json.opportunities ?? [];
const oppDe = (id) => todasOpps.find((o) => (o.contactId || o.contact?.id) === id);
const adDe = (c) => [c.attributionSource?.adId, c.lastAttributionSource?.adId, ...(c.attributions ?? []).map((a) => a?.adId)]
  .find((id) => id && NOMBRE_AD[id]) || Object.keys(NOMBRE_AD).find((id) => JSON.stringify(c.customFields ?? []).includes(id)) || null;
const contactos = $('GHL leads').all().flatMap((i) => i.json.contacts ?? [])
  .filter((c, i, a) => a.findIndex((x) => x.id === c.id) === i)
  .filter((c) => (c.dateAdded ?? '') >= INICIO)
  .filter((c) => !(c.tags ?? []).map((t) => String(t).toLowerCase()).includes('test-maripino'))
  .filter((c) => adDe(c) || oppDe(c.id) || (c.tags ?? []).map((t) => String(t).toLowerCase()).includes('maripino'));
const opps = contactos.map((c) => oppDe(c.id)).filter(Boolean);
const campo = (c, k) => { const v = (c.customFields ?? []).find((f) => f.id === CFG.campos[k])?.value; return Array.isArray(v) ? v.join(', ') : norm(v); };
const tagsDe = (c) => (c.tags ?? []).map((t) => String(t).toLowerCase());

const leads = contactos.map((c) => {
  const o = opps.find((x) => (x.contactId || x.contact?.id) === c.id);
  const adId = adDe(c);
  return { c, o, tags: tagsDe(c), adId, alta: new Date(c.dateAdded).getTime(),
    ciudad: campo(c, 'ubicacion'), inversion: campo(c, 'inversion'), leadsSemana: campo(c, 'leads'), anuncioCampo: campo(c, 'anuncio') };
});
const deAyer = leads.filter((l) => dia(l.alta) === ayer);
const deSemana = leads.filter((l) => l.alta >= hace7);

const estado = (l) => {
  if (l.o?.status === 'won') return 'Ganado';
  if (l.o?.status === 'lost' || l.o?.status === 'abandoned') return 'Perdido';
  if (l.tags.includes('no-asistio')) return 'No asistió a la llamada (reagendar)';
  if (l.tags.includes('cita-agendada') || etapaNombre[l.o?.pipelineStageId] === 'Agendado') return 'Agendado';
  if (l.tags.includes('atencion-personalizada')) return 'Atención personalizada';
  if (l.tags.includes('maripino-off')) return 'Lo atiende el equipo (Maripino apagado)';
  if (l.tags.includes('seguimiento-3')) return 'Perdido (sin respuesta tras 3 seguimientos)';
  if (l.tags.some((t) => t.startsWith('seguimiento-'))) return 'En seguimiento';
  return 'En conversación';
};
const contar = (arr, f) => arr.reduce((m, x) => { const k = f(x); if (k) m[k] = (m[k] || 0) + 1; return m; }, {});
const porEstado = contar(leads, estado);
const porEtapa = contar(leads.filter((l) => l.o), (l) => etapaNombre[l.o.pipelineStageId] || 'Otra');

const ciudadNorm = (s) => { const t = norm(s).split(/[,(]/)[0].trim(); return t ? t.charAt(0).toUpperCase() + t.slice(1).toLowerCase() : ''; };
const ciudades = Object.entries(contar(leads, (l) => ciudadNorm(l.ciudad))).sort((a, b) => b[1] - a[1]).slice(0, 10);
const inversion = contar(leads, (l) => { const v = sinAcento(l.inversion); if (!v) return 'Sin dato'; if (/^(si|sí|yes)\b|invert|invier/.test(v) && !/^no\b/.test(v)) return 'Sí invierte'; if (/^no\b|nunca|todavia no/.test(v)) return 'No invierte'; return 'Sin dato'; });
const volumenes = leads.map((l) => Number(String(l.leadsSemana).replace(/[^\d.]/g, ''))).filter((n) => n > 0);
const volumenMedio = volumenes.length ? Math.round(volumenes.reduce((a, b) => a + b, 0) / volumenes.length) : null;

// ---------- Citas próximas
const eventos = ($('GHL citas').first().json.events ?? []).filter((e) => !/cancel/i.test(e.appointmentStatus || ''))
  .sort((a, b) => new Date(a.startTime) - new Date(b.startTime));
const f = (t) => new Date(t).toLocaleString('es-MX', { timeZone: tz, weekday: 'short', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });

// ---------- HTML
const tabla = (cab, filas) => `<table style="border-collapse:collapse;width:100%;font-size:14px;margin:8px 0 18px">
<tr>${cab.map((h, i) => `<th style="text-align:${i ? 'right' : 'left'};border-bottom:2px solid #1f3b73;padding:6px">${h}</th>`).join('')}</tr>
${filas.map((f) => `<tr>${f.map((v, i) => `<td style="text-align:${i ? 'right' : 'left'};border-bottom:1px solid #e3e6ee;padding:6px">${v}</td>`).join('')}</tr>`).join('')}</table>`;
const h2 = (t) => `<h2 style="color:#1f3b73;font-size:17px;margin:22px 0 6px">${t}</h2>`;
const kpi = (t, v) => `<td style="padding:10px;background:#f2f5fb;border-radius:8px;text-align:center"><div style="font-size:22px;font-weight:bold;color:#1f3b73">${v}</div><div style="font-size:12px;color:#555">${t}</div></td>`;

const leadsPorAd = (arr) => contar(arr, (l) => anuncioDe(l));
const filasMeta = (datos, arrLeads) => {
  const la = leadsPorAd(arrLeads);
  const filas = (datos ?? []).map((x) => [esc(x.nombre), money(x.gasto), num(x.impresiones), num(x.clics), num(x.conversaciones), num(la[x.id] || 0),
    la[x.id] ? money(x.gasto / la[x.id]) : '-']);
  const g = sum(datos, 'gasto'); const tl = arrLeads.filter((l) => NOMBRE_AD[l.adId]).length;
  filas.push(['<b>Total</b>', `<b>${money(g)}</b>`, `<b>${num(sum(datos, 'impresiones'))}</b>`, `<b>${num(sum(datos, 'clics'))}</b>`,
    `<b>${num(sum(datos, 'conversaciones'))}</b>`, `<b>${num(tl)}</b>`, `<b>${tl ? money(g / tl) : '-'}</b>`]);
  return filas;
};
const cabMeta = ['Anuncio', 'Gasto', 'Impresiones', 'Clics', 'Conversaciones', 'Leads (CRM)', 'Costo por lead'];
const agendadosTotal = (porEstado['Agendado'] || 0) + (porEstado['Ganado'] || 0);
const perdidosTotal = (porEstado['Perdido'] || 0) + (porEstado['Perdido (sin respuesta tras 3 seguimientos)'] || 0);
const tasa = leads.length ? Math.round(100 * agendadosTotal / leads.length) + '%' : '-';

const html = `<div style="font-family:Arial,sans-serif;max-width:760px;color:#222">
<h1 style="color:#1f3b73;font-size:21px">Reporte diario xzen Auto · ${ayer}</h1>
<table style="width:100%;border-spacing:8px"><tr>${kpi('Leads ayer', deAyer.length)}${kpi('Leads 7 días', deSemana.length)}${kpi('Leads totales', leads.length)}${kpi('Agendados', agendadosTotal)}${kpi('Perdidos', perdidosTotal)}${kpi('Tasa de agenda', tasa)}</tr></table>
${h2('Leads por anuncio (GHL)')}${tabla(['Anuncio', 'Ayer', '7 días', 'Total'], [...NOMBRES_AD, SIN_ID, null].map((nombre) => {
  const n = (arr) => arr.filter((l) => anuncioDe(l) === nombre).length;
  return [nombre ? esc(nombre) : 'Sin anuncio identificado (orgánico)', num(n(deAyer)), num(n(deSemana)), num(n(leads)), nombre];
}).filter((f) => f[3] !== '0' || NOMBRES_AD.includes(f[4])).map((f) => f.slice(0, 4)))}
${h2('Anuncios · ayer')}${meta.ayer ? tabla(cabMeta, filasMeta(meta.ayer, deAyer)) : `<p style="color:#b00">⚠️ Sin datos de Meta (${esc(metaError)}). Revisa la credencial «Meta Ads XzenAuto» en n8n.</p>`}
${meta.semana ? h2('Anuncios · últimos 7 días') + tabla(cabMeta, filasMeta(meta.semana, deSemana)) : ''}
${meta.total ? h2('Anuncios · desde el inicio') + tabla(cabMeta, filasMeta(meta.total, leads)) : ''}
${h2('Estado de los leads (total)')}${tabla(['Estado', 'Leads'], Object.entries(porEstado).sort((a, b) => b[1] - a[1]).map(([k, v]) => [k, num(v)]))}
${h2('Pipeline XzenAuto')}${tabla(['Columna', 'Oportunidades'], (pipe?.stages ?? []).map((s) => [esc(s.name), num(porEtapa[s.name] || 0)]))}
${h2('Ciudades que más nos contactan')}${ciudades.length ? tabla(['Ciudad', 'Leads'], ciudades.map(([k, v]) => [esc(k), num(v)])) : '<p>Aún sin datos.</p>'}
${h2('¿Invierten en anuncios de Facebook?')}${tabla(['Respuesta', 'Leads'], ['Sí invierte', 'No invierte', 'Sin dato'].map((k) => [k, num(inversion[k] || 0)]))}
<p style="font-size:14px">Volumen medio que declaran: <b>${volumenMedio ? num(volumenMedio) + ' leads por semana' : 'sin datos'}</b>${volumenes.length ? ` (${volumenes.length} respuestas)` : ''}.</p>
${h2('Próximas llamadas agendadas')}${eventos.length ? tabla(['Cuándo', 'Cita'], eventos.slice(0, 15).map((e) => [esc(f(e.startTime)), esc(e.title)])) : '<p>No hay llamadas agendadas en los próximos 7 días.</p>'}
${h2('Leads de los últimos 7 días')}${deSemana.length ? tabla(['Fecha', 'Lead', 'Anuncio', 'Ciudad', 'Estado'], [...deSemana].sort((a, b) => b.alta - a.alta).map((l) => [esc(new Date(l.alta).toLocaleString('es-MX', { timeZone: tz, day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })), esc([l.c.firstName, l.c.lastName].filter(Boolean).join(' ') || l.c.phone), esc(anuncioDe(l) || 'Sin anuncio (orgánico)'), esc(l.ciudad || '-'), estado(l)])) : '<p>No entraron leads en los últimos 7 días.</p>'}
<p style="font-size:12px;color:#777;margin-top:24px">Leads = contactos nuevos desde el ${INICIO} que vienen de nuestros anuncios, tienen oportunidad en XzenAuto o los atiende Maripino (sin contactos de prueba). Conversaciones = conversaciones de mensajería iniciadas según Meta. Perdidos = oportunidades marcadas como perdidas en GHL más leads sin respuesta tras los 3 seguimientos.</p>
</div>`;

return [{ json: { asunto: `📊 xzen Auto · ${ayer}: ${deAyer.length} leads, ${agendadosTotal} agendados en total${meta.ayer ? ', gasto ' + money(sum(meta.ayer, 'gasto')) : ''}`, html } }];
"""


def meta_insights(nombre, pos, preset):
    return nodo(nombre, "n8n-nodes-base.httpRequest", 4.2, pos, {
        "url": "https://graph.facebook.com/v21.0/act_48823661/insights",
        "authentication": "predefinedCredentialType", "nodeCredentialType": "facebookGraphApi",
        "sendQuery": True, "queryParameters": {"parameters": [
            {"name": "level", "value": "ad"}, {"name": "date_preset", "value": preset},
            {"name": "fields", "value": META_CAMPOS}, {"name": "limit", "value": "200"},
            {"name": "filtering", "value": json.dumps([{"field": "ad.id", "operator": "IN", "value": IDS_ANUNCIOS}])},
        ]},
        "options": {},
    }, CRED_META, onError="continueRegularOutput", alwaysOutputData=True)


rep_nodos = [
    nodo("Diario 8:00", "n8n-nodes-base.scheduleTrigger", 1.2, [0, 0],
         {"rule": {"interval": [{"field": "cronExpression", "expression": "0 8 * * *"}]}}),
    meta_insights("Meta ayer", [200, 0], "yesterday"),
    meta_insights("Meta 7 días", [400, 0], "last_7d"),
    meta_insights("Meta total", [600, 0], "maximum"),
    nodo("Páginas", "n8n-nodes-base.code", 2, [800, 0], {"jsCode": "return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((page) => ({ json: { page } }));"}),
    ghl("GHL leads", [1000, 0], "POST", GHL + "/contacts/search",
        cuerpo="={{ JSON.stringify({ locationId: '" + LOCATION_ID + "', pageLimit: 100, page: $json.page,"
               " sort: [{ field: 'dateAdded', direction: 'desc' }] }) }}",
        onError="continueRegularOutput"),
    ghl("GHL oportunidades", [1200, 0], "GET", GHL + "/opportunities/search",
        query={"location_id": LOCATION_ID, "pipeline_id": CFG["pipelineId"], "limit": "100"}, executeOnce=True),
    ghl("GHL pipelines", [1400, 0], "GET", GHL + "/opportunities/pipelines", query={"locationId": LOCATION_ID},
        executeOnce=True),
    ghl("GHL citas", [1600, 0], "GET", GHL + "/calendars/events",
        query={"locationId": LOCATION_ID, "calendarId": CALENDAR_ID, "startTime": "={{ $now.toMillis() }}",
               "endTime": "={{ $now.plus({ days: 7 }).toMillis() }}"},
        version_api="2021-04-15", executeOnce=True, onError="continueRegularOutput", alwaysOutputData=True),
    nodo("Armar reporte", "n8n-nodes-base.code", 2, [1800, 0], {"jsCode": REP_REPORTE}),
    nodo("Enviar reporte", "n8n-nodes-base.gmail", 2.2, [2000, 0], {
        "sendTo": CFG["correoAviso"], "subject": "={{ $json.asunto }}", "emailType": "html",
        "message": "={{ $json.html }}", "options": {"appendAttribution": False},
    }, CRED_GMAIL),
]
rep_con = {a["name"]: {"main": [[{"node": b["name"], "type": "main", "index": 0}]]} for a, b in zip(rep_nodos, rep_nodos[1:])}
reporte = {"name": "Maripino · Reporte diario (correo)", "nodes": rep_nodos, "connections": rep_con,
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

for nombre, wf in [("maripino-agente.json", agente), ("maripino-seguimientos.json", seguimientos),
                   ("maripino-rescate.json", rescate), ("maripino-reporte.json", reporte),
                   ("maripino-configuracion.json", configuracion)]:
    (AQUI / nombre).write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n")
    print("escrito", nombre, len(wf["nodes"]), "nodos")
