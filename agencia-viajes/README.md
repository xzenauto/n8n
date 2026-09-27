# Agencia Prueba – Lucía, agente de viajes con IA

Sistema de atención y ventas para agencia de viajes con **n8n + Supabase + Google Sheets + GoHighLevel (GHL)**.

## Qué hace

1. **Lucía** (IA) atiende 24/7 por WhatsApp, Instagram, Facebook, TikTok y chat web, y recopila:
   destino, fechas (pregunta una sola vez), adultos, niños y edades de los niños.
   - Entiende notas de voz (Whisper) e imágenes (capturas de anuncios).
   - Si el cliente llega por un anuncio de Meta (ad_id), le presenta la promo; si ya venció, ofrece hasta 3 vigentes.
   - Solo da precios de promos activas, textuales, recalcando días en que aplican y "sujeto a disponibilidad".
   - Escala a humano (columna **🙋 Atención humana**) ante quejas, visas, cambios de reservación, etc.
   - Si el cliente ya viajó antes, lo reconoce y abre una nueva oportunidad.
2. Con los datos completos mueve la tarjeta a **✅ Datos completos** (o **🔥 viaja en menos de 15 días**) y registra el lead en Google Sheets.
3. Seguimientos automáticos (solo L–V 9:00–18:00 y sáb 10:00–14:00, redactados por IA):
   - Datos incompletos: 5 h, 20 h y 48 h; a las 72 h pasa a **❌ Perdido / frío**.
   - Cotización enviada: 5 h, 10 h, 20 h y 48 h. Se cortan en cuanto el cliente responde (pasa a **💬 Cliente respondió**).
4. Recordatorios: de cada pago pendiente y del viaje, **1 día antes** (si cae en domingo, se envía el sábado).
5. Si WhatsApp rechaza un mensaje (ventana de 24 h), se crea una **tarea en GHL** para la vendedora con el texto listo para copiar.

## Piezas

| Pieza | Dónde |
|---|---|
| Workflow **Lucía – Conversación (Agencia Prueba)** | n8n, webhook `https://n8n.srv964593.hstgr.cloud/webhook/lucia-agencia-prueba` |
| Workflow **Lucía – Seguimientos y recordatorios** | n8n, cada 15 min |
| Workflow **Lucía – Sincronizar promos (Sheets → Supabase)** | n8n, cada 15 min |
| Google Sheet **Agencia Prueba – Promos y Leads** | Drive de xzenauto (`1lrw1EK-laBq-QJkHUxQGr7fN7b-OD7bqE57nDR_qKx0`) |
| Tablas `viajes_*` y funciones RPC | Supabase, proyecto XzenAuto (`sql/`) |
| Pipeline **Ventas Viajes**, 5 carpetas de campos, tags, usuarias | GHL, subcuenta Agencia Prueba (`ghl_setup.py`, `ghl_ids.json`) |

Regenerar y publicar los workflows: `python3 build_workflows.py` (requiere `N8N_API_URL` y `N8N_API_KEY`).
`--forzar-horario` ignora el horario hábil (solo para pruebas; no dejarlo publicado así).

## Configuración pendiente en GHL (solo desde la interfaz)

### 1. Enviar los mensajes entrantes a Lucía (obligatorio)
*Automatización → Workflows → Crear → Empezar desde cero*
- **Disparador:** *Customer Replied* (Cliente respondió). Canal: todos.
- **Acción:** *Webhook* → método **POST** → URL `https://n8n.srv964593.hstgr.cloud/webhook/lucia-agencia-prueba`
- Guardar y **Publicar**.

### 2. Avisar a las vendedoras cuando hay lead listo
*Workflow nuevo*
- **Disparador:** *Pipeline Stage Changed* → Pipeline "Ventas Viajes" → etapas "✅ Datos completos", "🔥 Datos completos – viaja en menos de 15 días" y "🙋 Atención humana".
- **Acción:** *Internal Notification* (en la app y por correo) → Nathalie, Michelle y Paulina.
  Mensaje sugerido: `Nuevo lead listo: {{contact.name}} – {{contact.ia_destino}} ({{contact.ia_fecha_salida}})`.

### 3. Comentarios en Facebook / Instagram (y TikTok si tu cuenta lo permite)
*Workflow nuevo* → Disparador *Facebook/Instagram – Comment(s) on a post* → Acción *Reply in comments*:
`¡Hola! ✈️ Te enviamos la info por mensaje privado 😊` + Acción *Send Instagram/Facebook DM*: `¡Hola! Soy Lucía 🌴 ¿Qué destino o promoción te interesa?`
Cuando el cliente responde el DM, Lucía continúa sola.

### 4. Canales
Conectar en *Configuración → Integraciones*: WhatsApp (LeadConnector), Facebook, Instagram y TikTok.
Si GHL tiene activado su propio **Conversation AI** en esta subcuenta, desactivarlo para que no conteste en paralelo.

## Operación diaria (para las vendedoras)

| Quiero… | Hago… |
|---|---|
| Tomar un lead | Asignarme la oportunidad en la columna ✅ o 🔥 |
| Que empiecen los seguimientos de la cotización | Llenar la carpeta **2. Cotización** y mover la tarjeta a **📩 Cotización enviada** |
| Pausar los seguimientos de un cliente | Agregar el tag `seguimiento-pausado` (quitarlo para reactivar) |
| Reiniciar los seguimientos de cotización | Mover la tarjeta fuera y de nuevo a **📩 Cotización enviada** |
| Que Lucía deje de contestar a un cliente | Tag `ia-pausada` (quitarlo para reactivar) |
| Recordatorios de pago | Llenar **4. Pagos** (fecha límite, monto y estatus "Pendiente") y tener la tarjeta en **💳 Apartado** o **✈️ Pagado** |
| Recordatorio de viaje | Llenar **5. Datos definitivos del viaje** y **3. Vuelos** (si aplica) |
| Ver mensajes que Lucía no pudo enviar | Tareas del contacto "📲 Enviar mensaje manual" |

## Promos (para el equipo de marketing)
Llenar la pestaña **Promos** del Sheet (instrucciones en la pestaña *Instrucciones*). En máximo 15 minutos Lucía ya las conoce.
Poner en `ad_ids` el/los ID de anuncio de Meta (Administrador de anuncios → columna "Identificador del anuncio").
