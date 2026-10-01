import json, uuid
SB = {"supabaseApi": {"id": "QIVohgUOAGTuwYd1", "name": "XzenAuto"}}
SBURL = "https://fllhjemdhohsewqwzrpc.supabase.co/rest/v1"
def http_sb(name, method, path, pos, body=None, prefer=None, query=None, extra_opts=None):
    p = {"method": method, "url": SBURL + path, "authentication": "predefinedCredentialType",
         "nodeCredentialType": "supabaseApi", "options": extra_opts or {}}
    hdr = [{"name": "Content-Type", "value": "application/json"}]
    if prefer: hdr.append({"name": "Prefer", "value": prefer})
    p["sendHeaders"] = True; p["headerParameters"] = {"parameters": hdr}
    if body is not None:
        p["sendBody"] = True; p["specifyBody"] = "json"; p["jsonBody"] = body
    return {"parameters": p, "name": name, "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": pos, "credentials": SB, "id": str(uuid.uuid4())}

code_match = r'''
const catalogo = $('Catalogo Supabase').all().map(i => i.json);
const shop = $('Shopify products.json').all().flatMap(i => i.json.products || []);
const norm = s => (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
const imgKey = u => {
  if (!u) return '';
  const f = u.split('?')[0].split('/').pop().toLowerCase();
  return f.replace(/_\d+x\d*(?=\.)/, '').replace(/\.(png|jpe?g|webp)$/, '');
};
const productos = [], variantes = [], sinMatch = [];
for (const c of catalogo) {
  const k = imgKey(c.foto_url);
  let p = shop.find(s => (s.images || []).some(im => imgKey(im.src) === k && k));
  if (!p) p = shop.find(s => norm(s.title) === norm(c.nombre));
  if (!p) p = shop.find(s => norm(s.title).includes(norm(c.nombre)) || norm(c.nombre).includes(norm(s.title)));
  if (!p) { sinMatch.push(c.nombre); continue; }
  productos.push({ id: c.id, shopify_product_id: p.id, shopify_handle: p.handle });
  for (const v of p.variants || []) {
    variantes.push({
      producto_id: c.id,
      shopify_variant_id: v.id,
      titulo: v.title === 'Default Title' ? null : v.title,
      precio: Number(v.price),
      precio_antes: v.compare_at_price ? Number(v.compare_at_price) : null,
      disponible: v.available !== false,
      updated_at: new Date().toISOString()
    });
  }
}
return [{ json: { productos, variantes, sin_match: sinMatch, total_shopify: shop.length } }];
'''

nodes = [
  {"parameters": {"rule": {"interval": [{"field": "cronExpression", "expression": "17 6 * * *"}]}},
   "name": "Diario 6:17", "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.2, "position": [0, 0], "id": str(uuid.uuid4())},
  {"parameters": {"httpMethod": "POST", "path": "casa-alpa-sync-shopify", "responseMode": "lastNode", "options": {}},
   "name": "Webhook - Correr sync", "type": "n8n-nodes-base.webhook", "typeVersion": 2, "position": [0, 200],
   "webhookId": str(uuid.uuid4()), "id": str(uuid.uuid4())},
  {"parameters": {"url": "https://casaalpa.mx/products.json?limit=250", "options": {"response": {"response": {"responseFormat": "json"}}}},
   "name": "Shopify products.json", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2, "position": [220, 100], "id": str(uuid.uuid4())},
  {"parameters": {"operation": "getAll", "tableId": "casa_alpa_catalogo", "returnAll": True},
   "name": "Catalogo Supabase", "type": "n8n-nodes-base.supabase", "typeVersion": 1, "position": [440, 100],
   "credentials": SB, "alwaysOutputData": True, "executeOnce": True, "id": str(uuid.uuid4())},
  {"parameters": {"jsCode": code_match}, "name": "Code - Emparejar", "type": "n8n-nodes-base.code", "typeVersion": 2,
   "position": [660, 100], "executeOnce": True, "id": str(uuid.uuid4())},
  http_sb("Upsert variantes", "POST", "/casa_alpa_variantes?on_conflict=shopify_variant_id", [880, 0],
          body="={{ JSON.stringify($json.variantes) }}", prefer="resolution=merge-duplicates,return=minimal"),
  http_sb("Guardar ids producto", "POST", "/casa_alpa_catalogo?on_conflict=id", [880, 200],
          body="={{ JSON.stringify($('Code - Emparejar').first().json.productos) }}", prefer="resolution=merge-duplicates,return=minimal"),
  {"parameters": {"jsCode": "const r = $('Code - Emparejar').first().json;\nreturn [{ json: { productos_emparejados: r.productos.length, variantes: r.variantes.length, sin_match: r.sin_match, total_shopify: r.total_shopify } }];"},
   "name": "Resumen", "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [1100, 100], "id": str(uuid.uuid4())},
]
conn = {
  "Diario 6:17": {"main": [[{"node": "Shopify products.json", "type": "main", "index": 0}]]},
  "Webhook - Correr sync": {"main": [[{"node": "Shopify products.json", "type": "main", "index": 0}]]},
  "Shopify products.json": {"main": [[{"node": "Catalogo Supabase", "type": "main", "index": 0}]]},
  "Catalogo Supabase": {"main": [[{"node": "Code - Emparejar", "type": "main", "index": 0}]]},
  "Code - Emparejar": {"main": [[{"node": "Upsert variantes", "type": "main", "index": 0}]]},
  "Upsert variantes": {"main": [[{"node": "Guardar ids producto", "type": "main", "index": 0}]]},
  "Guardar ids producto": {"main": [[{"node": "Resumen", "type": "main", "index": 0}]]},
}
json.dump({"name": "Casa Alpa - Sync variantes Shopify", "nodes": nodes, "connections": conn,
           "settings": {"executionOrder": "v1", "availableInMCP": True, "timezone": "America/Mexico_City"}}, open("sync.json", "w"), ensure_ascii=False, indent=1)
