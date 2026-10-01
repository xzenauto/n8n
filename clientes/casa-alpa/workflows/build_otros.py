import json, uuid, secrets, os

SB = {"supabaseApi": {"id": "QIVohgUOAGTuwYd1", "name": "XzenAuto"}}
GHL = {"httpHeaderAuth": {"id": "Xs2385W5NO5TjT2V", "name": "GHL - PIT - Alpa"}}
SBURL = "https://fllhjemdhohsewqwzrpc.supabase.co/rest/v1"
GHLURL = "https://services.leadconnectorhq.com"
LOC = "iYgqtO9TzgsM2X4hzyhj"
PIPELINE = "KRqZz6ozuHtbiISHH4Cd"
GANADO = "609487d9-c097-4896-9151-1eed75d723ca"

# ruta secreta del webhook de Shopify (se conserva entre builds)
tok_file = "shopify_path_token"  # archivo local, no versionado
if not os.path.exists(tok_file):
    open(tok_file, "w").write(secrets.token_hex(12))
TOK = open(tok_file).read().strip()


class WF:
    def __init__(self):
        self.nodes, self.conns = [], {}

    def add(self, name, type_, params, pos, ver=1, creds=None, **extra):
        n = {"parameters": params, "name": name, "type": type_, "typeVersion": ver, "position": pos, "id": str(uuid.uuid4())}
        if creds:
            n["credentials"] = creds
        n.update(extra)
        self.nodes.append(n)

    def code(self, name, js, pos, **extra):
        self.add(name, "n8n-nodes-base.code", {"jsCode": js.strip()}, pos, 2, **extra)

    def http(self, name, method, url, pos, creds="sb", body=None, prefer=None, version=None, **extra):
        p = {"method": method, "url": url, "options": {}}
        if creds == "sb":
            p.update({"authentication": "predefinedCredentialType", "nodeCredentialType": "supabaseApi"}); c = SB
        else:
            p.update({"authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth"}); c = GHL
        hdr = []
        if creds == "ghl":
            hdr += [{"name": "Version", "value": version or "2021-07-28"}, {"name": "Accept", "value": "application/json"}]
        if body is not None:
            hdr.append({"name": "Content-Type", "value": "application/json"})
        if prefer:
            hdr.append({"name": "Prefer", "value": prefer})
        p["sendHeaders"] = True
        p["headerParameters"] = {"parameters": hdr}
        if body is not None:
            p.update({"sendBody": True, "specifyBody": "json", "jsonBody": body})
        self.add(name, "n8n-nodes-base.httpRequest", p, pos, 4.2, c, **extra)

    def ifn(self, name, expr, pos):
        self.add(name, "n8n-nodes-base.if", {
            "conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                           "conditions": [{"id": str(uuid.uuid4()), "leftValue": expr,
                                           "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
                           "combinator": "and"}, "looseTypeValidation": True, "options": {}}, pos, 2.2)

    def link(self, a, b, out=0):
        c = self.conns.setdefault(a, {}).setdefault("main", [])
        while len(c) <= out:
            c.append([])
        c[out].append({"node": b, "type": "main", "index": 0})

    def chain(self, *names):
        for a, b in zip(names, names[1:]):
            self.link(a, b)

    def dump(self, name, fn):
        json.dump({"name": name, "nodes": self.nodes, "connections": self.conns,
                   "settings": {"executionOrder": "v1", "timezone": "America/Mexico_City"}},
                  open(fn, "w"), ensure_ascii=False, indent=1)


# =================================================================== pedido pagado
w = WF()
P = "$('Code - Parsear Pedido').first().json"
w.add("Nota", "n8n-nodes-base.stickyNote", {"content": "## Pedido pagado en Shopify → GHL\nConfigura en Shopify: **Configuración → Notificaciones → Webhooks → Crear webhook**, evento *Pago de pedido*, formato JSON, URL de este webhook (ruta secreta, no la compartas).\n\nSólo procesa pedidos ligados a un contacto de GHL: por el atributo `ghl_contact_id` del link de Vale o, si no viene, por el teléfono del pedido.", "height": 260, "width": 520}, [-60, -320], 1)
w.add("Webhook - Shopify Pedido Pagado", "n8n-nodes-base.webhook",
      {"httpMethod": "POST", "path": f"casa-alpa-shopify-pedido-{TOK}", "options": {}}, [0, 0], 2, webhookId=str(uuid.uuid4()))
w.code("Code - Parsear Pedido", r"""
const o = $json.body || {};
const attrs = Object.fromEntries((o.note_attributes || []).map(a => [a.name, a.value]));
const sa = o.shipping_address || {};
const tel = String(sa.phone || o.phone || o.customer?.phone || o.billing_address?.phone || '').replace(/\D/g, '');
let e164 = null;
if (tel.length === 10) e164 = '+52' + tel;
else if (tel.length === 12 && tel.startsWith('52')) e164 = '+' + tel;
else if (tel.length === 13 && tel.startsWith('521')) e164 = '+52' + tel.slice(3);
else if (tel.length > 10) e164 = '+' + tel;
const direccion = [sa.name, sa.address1, sa.address2, [sa.zip, sa.city].filter(Boolean).join(' '), sa.province, sa.country, sa.phone ? 'Tel. ' + sa.phone : null].filter(Boolean).join('\n');
const items = (o.line_items || []).map(li => `${li.quantity}x ${li.title}${li.variant_title ? ' (' + li.variant_title + ')' : ''} — $${Number(li.price).toLocaleString('es-MX')}`);
return [{ json: {
  order_id: String(o.id || ''),
  order_name: o.name || ('#' + (o.order_number || o.id)),
  financial_status: o.financial_status,
  total: Number(o.total_price || 0),
  envio: Number(o.total_shipping_price_set?.shop_money?.amount || 0),
  contact_id: attrs.ghl_contact_id || null,
  link_id: attrs.vale_link_id || null,
  telefono: e164,
  email: o.email || o.customer?.email || null,
  nombre: o.customer?.first_name || sa.first_name || '',
  direccion: direccion || '(sin dirección de envío)',
  items,
  valido: !!o.id && ['paid', 'partially_paid'].includes(o.financial_status)
} }];
""", [220, 0])
w.ifn("IF - Pedido Valido", "={{ $json.valido }}", [440, 0])
w.http("Supabase - Ya Procesado", "GET", f"={SBURL}/casa_alpa_links_pago?shopify_order_id=eq.{{{{ $json.order_id }}}}&select=id", [660, 0], alwaysOutputData=True)
w.ifn("IF - Es Nuevo", "={{ !$json.id }}", [880, 0])
w.ifn("IF - Trae Contact ID", f"={{{{ !!{P}.contact_id }}}}", [1100, 0])
w.http("GHL - Buscar por Telefono", "GET",
       f"={GHLURL}/contacts/search/duplicate?locationId={LOC}&number={{{{ encodeURIComponent({P}.telefono || '') }}}}&email={{{{ encodeURIComponent({P}.email || '') }}}}",
       [1320, 120], "ghl", alwaysOutputData=True, onError="continueRegularOutput")
w.code("Code - Resolver Contacto", r"""
const p = $('Code - Parsear Pedido').first().json;
const encontrado = $json.contact?.id || null;
const contact_id = p.contact_id || encontrado;
if (!contact_id) return [];  // pedido de la tienda que no viene de un contacto de GHL: nada que hacer
return [{ json: { ...p, contact_id } }];
""", [1540, 0])
w.http("GHL - Buscar Opportunity", "GET", f"={GHLURL}/opportunities/search?location_id={LOC}&contact_id={{{{ $json.contact_id }}}}&pipeline_id={PIPELINE}", [1760, 0], "ghl")
w.code("Code - Opp", r"""
const p = $('Code - Resolver Contacto').first().json;
const o = ($json.opportunities || [])[0] || null;
return [{ json: { ...p, opportunity_id: o?.id || null } }];
""", [1980, 0])
w.ifn("IF - Hay Opp", "={{ !!$json.opportunity_id }}", [2200, 0])
R = "$('Code - Opp').first().json"
w.http("GHL - Ganar Opportunity", "PUT", f"={GHLURL}/opportunities/{{{{ $json.opportunity_id }}}}", [2420, -100], "ghl",
       body=f"={{{{ JSON.stringify({{ pipelineId: '{PIPELINE}', pipelineStageId: '{GANADO}', status: 'won', monetaryValue: $json.total }}) }}}}")
w.http("GHL - Crear Opp Ganada", "POST", f"{GHLURL}/opportunities/", [2420, 100], "ghl",
       body=f"={{{{ JSON.stringify({{ pipelineId: '{PIPELINE}', locationId: '{LOC}', contactId: $json.contact_id, name: ($json.nombre || 'Cliente') + ' ' + $json.order_name, pipelineStageId: '{GANADO}', status: 'won', monetaryValue: $json.total }}) }}}}")
w.http("GHL - Etiqueta Compro", "POST", f"={GHLURL}/contacts/{{{{ {R}.contact_id }}}}/tags", [2640, 0], "ghl",
       body="={{ JSON.stringify({ tags: ['compro-shopify'] }) }}", onError="continueRegularOutput")
w.http("GHL - Nota Pedido", "POST", f"={GHLURL}/contacts/{{{{ {R}.contact_id }}}}/notes", [2860, 0], "ghl",
       body=f"""={{{{ JSON.stringify({{ body: '🛒 Pedido pagado en Shopify ' + {R}.order_name + '\\nTotal: $' + {R}.total.toLocaleString('es-MX') + ({R}.envio ? ' (envío $' + {R}.envio.toLocaleString('es-MX') + ')' : '') + '\\n\\nProductos:\\n' + {R}.items.join('\\n') + '\\n\\nDirección de envío:\\n' + {R}.direccion }}) }}}}""",
       onError="continueRegularOutput")
w.http("GHL - Tarea Envio", "POST", f"={GHLURL}/contacts/{{{{ {R}.contact_id }}}}/tasks", [3080, 0], "ghl",
       body=f"""={{{{ JSON.stringify({{ title: 'Preparar envío pedido ' + {R}.order_name, body: {R}.items.join('\\n') + '\\n\\nEnviar a:\\n' + {R}.direccion, dueDate: $now.plus({{ days: 1 }}).toUTC().toISO(), completed: false }}) }}}}""",
       onError="continueRegularOutput")
w.http("Supabase - Marcar Link Pagado", "PATCH",
       f"""={SBURL}/casa_alpa_links_pago?{{{{ {R}.link_id ? 'id=eq.' + {R}.link_id : 'contact_id=eq.' + {R}.contact_id + '&estado=eq.enviado' }}}}""",
       [3300, 0], body=f"""={{{{ JSON.stringify({{ estado: 'pagado', shopify_order_id: {R}.order_id, shopify_order_name: {R}.order_name, pagado_at: $now.toISO() }}) }}}}""",
       prefer="return=minimal", alwaysOutputData=True)
w.http("Supabase - Prospecto Compro", "PATCH", f"={SBURL}/casa_alpa_prospectos?contact_id=eq.{{{{ {R}.contact_id }}}}", [3520, 0],
       body="={{ JSON.stringify({ etapa: 'compro', seguimiento_pendiente: false, updated_at: $now.toISO() }) }}",
       prefer="return=representation", alwaysOutputData=True)
w.http("GHL - Avisar Cliente", "POST", f"{GHLURL}/conversations/messages", [3740, 0], "ghl", version="2021-04-15",
       body=f"""={{{{ JSON.stringify({{ type: $json.canal || 'WhatsApp', contactId: {R}.contact_id, message: '¡Muchas gracias' + ({R}.nombre ? ', ' + {R}.nombre : '') + '! 🎉 Ya recibimos tu pago del pedido ' + {R}.order_name + '. Nuestro equipo va a preparar tu envío y te avisamos en cuanto salga 🏡' }}) }}}}""",
       onError="continueRegularOutput")
w.chain("Webhook - Shopify Pedido Pagado", "Code - Parsear Pedido", "IF - Pedido Valido", "Supabase - Ya Procesado", "IF - Es Nuevo", "IF - Trae Contact ID")
w.link("IF - Trae Contact ID", "Code - Resolver Contacto", 0)
w.link("IF - Trae Contact ID", "GHL - Buscar por Telefono", 1)
w.link("GHL - Buscar por Telefono", "Code - Resolver Contacto")
w.chain("Code - Resolver Contacto", "GHL - Buscar Opportunity", "Code - Opp", "IF - Hay Opp")
w.link("IF - Hay Opp", "GHL - Ganar Opportunity", 0)
w.link("IF - Hay Opp", "GHL - Crear Opp Ganada", 1)
w.link("GHL - Ganar Opportunity", "GHL - Etiqueta Compro")
w.link("GHL - Crear Opp Ganada", "GHL - Etiqueta Compro")
w.chain("GHL - Etiqueta Compro", "GHL - Nota Pedido", "GHL - Tarea Envio", "Supabase - Marcar Link Pagado", "Supabase - Prospecto Compro", "GHL - Avisar Cliente")
w.dump("Casa Alpa - Pedido pagado Shopify → GHL", "pedido.json")

# =================================================================== recordatorio
w = WF()
w.add("Nota", "n8n-nodes-base.stickyNote", {"content": "## Recordatorio de link no pagado\nCada hora busca links enviados hace 20–23.5 h sin pagar (dentro de la ventana de 24 h de WhatsApp/Messenger) y manda un único recordatorio. No lo manda si el cliente escribió en las últimas 2 h o si está con un asesor.", "height": 220, "width": 460}, [-60, -300], 1)
w.add("Cada hora", "n8n-nodes-base.scheduleTrigger", {"rule": {"interval": [{"field": "hours", "hoursInterval": 1, "triggerAtMinute": 23}]}}, [0, 0], 1.2)
w.http("Supabase - Links Pendientes", "GET",
       f"={SBURL}/casa_alpa_links_pago?estado=eq.enviado&recordatorio_enviado=eq.false&created_at=lt.{{{{ $now.minus({{ hours: 20 }}).toUTC().toISO() }}}}&created_at=gt.{{{{ $now.minus({{ hours: 23, minutes: 30 }}).toUTC().toISO() }}}}&select=id,contact_id,url,items,total",
       [220, 0])
w.add("Loop", "n8n-nodes-base.splitInBatches", {"options": {}}, [440, 0], 3)
w.http("Supabase - Prospecto", "GET", f"={SBURL}/casa_alpa_prospectos?contact_id=eq.{{{{ $json.contact_id }}}}&select=nombre,canal,etapa", [660, 100], alwaysOutputData=True)
w.http("Supabase - Ultimo Mensaje", "GET", f"={SBURL}/casa_alpa_mensajes?contact_id=eq.{{{{ $('Loop').first().json.contact_id }}}}&order=id.desc&limit=1&select=created_at", [880, 100], alwaysOutputData=True)
w.code("Code - Decidir", r"""
const l = $('Loop').first().json;
const p = $('Supabase - Prospecto').first().json || {};
const ult = $json.created_at ? new Date($json.created_at) : null;
const reciente = ult && (Date.now() - ult.getTime()) < 2 * 3600 * 1000;
const enviar = !reciente && !['handoff', 'compro'].includes(p.etapa);
const nombre = (p.nombre || '').split(' ')[0];
const prod = (l.items || []).map(i => i.producto).join(', ');
return [{ json: { id: l.id, contact_id: l.contact_id, canal: p.canal || 'WhatsApp', enviar,
  mensaje: `Hola${nombre ? ' ' + nombre : ''} 😊 ¿Pudiste revisar tu link para ${prod || 'tu pedido'}? Te lo dejo de nuevo por si acaso:\n${l.url}\nSi te surge cualquier duda con el pago o el envío, aquí estoy 🙌` } }];
""", [1100, 100])
w.ifn("IF - Enviar", "={{ $json.enviar }}", [1320, 100])
w.http("GHL - Enviar Recordatorio", "POST", f"{GHLURL}/conversations/messages", [1540, 0], "ghl", version="2021-04-15",
       body="={{ JSON.stringify({ type: $json.canal, contactId: $json.contact_id, message: $json.mensaje }) }}", onError="continueRegularOutput")
w.http("Supabase - Marcar Recordatorio", "PATCH", f"={SBURL}/casa_alpa_links_pago?id=eq.{{{{ $('Code - Decidir').first().json.id }}}}", [1760, 100],
       body="={{ JSON.stringify({ recordatorio_enviado: true }) }}", prefer="return=minimal", alwaysOutputData=True)
w.http("Supabase - Guardar en Historial", "POST", f"{SBURL}/casa_alpa_mensajes", [1980, 100],
       body="={{ JSON.stringify({ contact_id: $('Code - Decidir').first().json.contact_id, rol: 'vale', contenido: $('Code - Decidir').first().json.mensaje, procesado: true }) }}",
       prefer="return=minimal", alwaysOutputData=True)
w.chain("Cada hora", "Supabase - Links Pendientes", "Loop")
w.link("Loop", "Supabase - Prospecto", 1)
w.chain("Supabase - Prospecto", "Supabase - Ultimo Mensaje", "Code - Decidir", "IF - Enviar")
w.link("IF - Enviar", "GHL - Enviar Recordatorio", 0)
w.link("IF - Enviar", "Supabase - Marcar Recordatorio", 1)
w.link("GHL - Enviar Recordatorio", "Supabase - Marcar Recordatorio")
w.link("Supabase - Marcar Recordatorio", "Supabase - Guardar en Historial")
w.link("Supabase - Guardar en Historial", "Loop")
w.dump("Casa Alpa - Recordatorio link de pago", "recordatorio.json")
print("ok")
