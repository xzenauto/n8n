# Maripino — agente de WhatsApp de xzen Auto

Atiende por WhatsApp (coexistencia en GHL, subcuenta **Xzen Auto** `8SiKgyVuy9KVUIx1Y1RT`) a quienes
escriben desde los anuncios de Meta: conoce al prospecto, guarda sus respuestas en el CRM, envía el
video y agenda una llamada en el calendario **Agencia 24/7 Rs Viajes** (`0YwJGtf0m8eI5hEacRMb`).

Flujo en n8n: **Maripino · Agente WhatsApp xzen Auto** (`ukexs4vDn2P6XA4Q`), webhook
`https://n8n.srv964593.hstgr.cloud/webhook/xzen-maripino`, llamado desde el flujo de GHL
"Webhook xzen" (disparador *El cliente ha respondido*).

## Anuncios → giro
| ID anuncio | Nombre en el CRM | Giro |
|---|---|---|
| 52613806312397 | Agencia Flyer | agencia_viajes |
| 52613807534997 | Agencia Xime | agencia_viajes |
| 52613807845997 | Agencia Carlos1 | agencia_viajes |
| 52613808070397 | Agencia Carlos2 | agencia_viajes |
| _(próximamente)_ | Muebles | tienda_muebles (preparado, inactivo) |

GHL guarda el ID del anuncio en el contacto (`attributionSource.adId`); el flujo lo lee de ahí.
**Solo responde a contactos que vienen de un anuncio** (o con la etiqueta `test-maripino` para
pruebas; la tiene el contacto de pruebas Carlos +34 638 76 07 11): la coexistencia también importa los contactos personales del WhatsApp.

## Qué hace en cada mensaje
1. Espera 12 s y junta los mensajes que el cliente mande seguidos (responde una sola vez).
2. Si el contacto tiene la etiqueta `atencion-personalizada` o `maripino-off`, no contesta
   (`maripino-off` sirve para apagar a Maripino a mano en un contacto concreto).
3. Primer contacto → crea la oportunidad en el pipeline **XzenAuto**, columna **Nuevo lead**, y guarda
   el campo **Anuncio de origen** + etiquetas `maripino`, `demo-agencia-viajes`.
4. Maripino (OpenAI gpt-4.1, trata de usted) conversa con el historial real de WhatsApp de GHL y pregunta:
   desde dónde contacta, si invierte en anuncios de Facebook y cuántos leads recibe por semana.
5. Envía las respuestas de una en una y guarda en GHL:
   - Campos: *Desde dónde nos contacta*, *Invierte en anuncios de Facebook*, *Leads estimados por semana*.
   - Nombre, negocio y correo cuando los da.
   - Etiquetas: `video-enviado`, `cita-agendada`, `atencion-personalizada`.
   Al enviar el video le pide que lo vea y nos cuente qué le pareció; si en **1 hora** no responde,
   le escribe una sola vez: «¿Pudo ver el video? Nos encantaría saber qué le pareció» (etiqueta `video-recordatorio`).
6. Cita agendada (herramientas `consultar_disponibilidad` / `agendar_cita`, verificada con la respuesta real
   del calendario) → oportunidad a **Agendado** y correo a xzenauto@gmail.com con fecha y hora y los datos del lead.
7. Atención personalizada → oportunidad a la columna **Atención personalizada**, nota en el contacto
   y correo a xzenauto@gmail.com (Gmail Xzen). Desde ahí el bot deja de responder a ese contacto.
8. Si OpenAI falla → mensaje cortés al cliente y pasa a atención personalizada.

## Añadir muebles
En `enrutamiento-anuncios.json` agregar los IDs con `"vertical": "tienda_muebles"`, poner el video
y `"activo": true`; revisar `prompts/tienda-muebles.md`. Luego `python3 n8n/generar_flujos.py` y
subir `n8n/maripino-agente.json` (PUT `/api/v1/workflows/ukexs4vDn2P6XA4Q`).

## Pruebas sin enviar nada
POST al webhook con `"simulacion": true`: corre el agente y consulta el calendario, pero no envía
WhatsApp ni escribe en GHL. Ejemplo:
```json
{"contact_id": "<id>", "simulacion": true, "message": {"type": 19, "body": "Hola"},
 "historial": [{"rol": "cliente", "texto": "..."}, {"rol": "maripino", "texto": "..."}]}
```

## Archivos
- `enrutamiento-anuncios.json` — anuncio → giro, video y etiqueta.
- `prompts/*.md` — instrucciones por giro (se insertan en el flujo al generarlo).
- `n8n/generar_flujos.py` — genera `n8n/maripino-agente.json` (y el de configuración de campos).
- `simulacion-conversacion.md` — conversación real de prueba.
