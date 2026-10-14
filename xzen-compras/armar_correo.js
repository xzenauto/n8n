// Normaliza lo que manda GHL (Order Submitted / Payment Received / webhook de prueba) y arma el correo
const b = $json.body || {};
const cd = b.customData || {};
const pick = (...v) => v.find(x => x !== undefined && x !== null && String(x).trim() !== '');
const order = b.order || b.payment || {};
const items = order.line_items || order.lineItems || b.line_items || b.products || [];
const productos = (Array.isArray(items) ? items : [])
  .map(i => `${i.qty || i.quantity || 1} × ${i.title || i.name || i.product_name || 'Producto'}${i.price ? ' — $' + i.price : ''}`);
const producto = pick(cd.producto, b.product_name, b.productName, productos.join('\n'), 'Sin detalle de producto');
const monto = pick(cd.monto, order.total_price, order.amount, order.total, b.amount, b.total, '');
const moneda = pick(cd.moneda, order.currency, b.currency, 'MXN');
const nombre = pick(cd.nombre, b.full_name, [b.first_name, b.last_name].filter(Boolean).join(' '), b.contact_name, 'Cliente sin nombre');
const correo = pick(cd.correo, b.email, '—');
const telefono = pick(cd.telefono, b.phone, '—');
const contactoId = pick(b.contact_id, b.contactId, '');
const esPrueba = !!(b.prueba || cd.prueba);
const fecha = new Date().toLocaleString('es-MX', { timeZone: 'America/Mexico_City' });
const esc = s => String(s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const link = contactoId ? `https://app.gohighlevel.com/v2/location/8SiKgyVuy9KVUIx1Y1RT/contacts/detail/${contactoId}` : '';
const asunto = `${esPrueba ? '[PRUEBA] ' : ''}🛒 Nueva compra en Xzen Auto — ${nombre}${monto !== '' ? ' ($' + monto + ' ' + moneda + ')' : ''}`;
const html = `<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#222">
<h2 style="margin:0 0 12px">${esPrueba ? '[PRUEBA] ' : ''}Nueva compra en Xzen Auto</h2>
<table cellpadding="6" style="border-collapse:collapse">
<tr><td><b>Cliente</b></td><td>${esc(nombre)}</td></tr>
<tr><td><b>Correo</b></td><td>${esc(correo)}</td></tr>
<tr><td><b>Teléfono</b></td><td>${esc(telefono)}</td></tr>
<tr><td valign="top"><b>Producto</b></td><td>${esc(producto).replace(/\n/g, '<br>')}</td></tr>
<tr><td><b>Monto</b></td><td>${monto !== '' ? '$' + esc(monto) + ' ' + esc(moneda) : '—'}</td></tr>
<tr><td><b>Fecha</b></td><td>${fecha}</td></tr>
</table>
${link ? `<p><a href="${link}">Ver contacto en GHL</a></p>` : ''}
</div>`;
return [{ json: { asunto, html } }];
