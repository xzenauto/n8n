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

## Campos del contacto (carpeta «Maripino · xzen Auto» en GHL)
Anuncio de origen · Desde dónde nos contacta · Invierte en anuncios de Facebook · Leads estimados por semana ·
Cita agendada (fecha y hora de la llamada, en hora de Ciudad de México).

## Qué hace en cada mensaje
1. Espera 12 s y junta los mensajes que el cliente mande seguidos (responde una sola vez).
2. Si el contacto tiene la etiqueta `atencion-personalizada` o `maripino-off`, no contesta
   (`maripino-off` sirve para apagar a Maripino a mano en un contacto concreto).
3. Primer contacto → crea la oportunidad (con el nombre del lead; al saber su negocio pasa a «Negocio (Nombre)»)
   en el pipeline **XzenAuto**, columna **Nuevo lead**, y guarda
   el campo **Anuncio de origen** + etiquetas `maripino`, `demo-agencia-viajes`.
4. Maripino (OpenAI gpt-4.1, trata de usted) conversa con el historial real de WhatsApp de GHL y pregunta:
   desde dónde contacta, si invierte en anuncios de Facebook y cuántos leads recibe por semana.
5. Envía las respuestas de una en una y guarda en GHL:
   - Campos: *Desde dónde nos contacta*, *Invierte en anuncios de Facebook*, *Leads estimados por semana*.
   - Nombre, negocio y correo cuando los da.
   - Etiquetas: `video-enviado`, `cita-agendada`, `atencion-personalizada`.
   Al enviar el video le pide que lo vea y nos cuente qué le pareció; si en **1 hora** no responde,
   le escribe una sola vez: «¿Pudo ver el video? Nos encantaría saber qué le pareció» (etiqueta `video-recordatorio`).
   En contactos de prueba (`test-maripino`) espera 1 minuto en lugar de 1 hora.
6. Cita agendada (herramientas `consultar_disponibilidad` / `agendar_cita`, verificada con la respuesta real
   del calendario) → oportunidad a **Agendado** y correo a xzenauto@gmail.com con fecha y hora y los datos del lead.
7. Atención personalizada → oportunidad a la columna **Atención personalizada**, nota en el contacto
   y correo a xzenauto@gmail.com (Gmail Xzen). Desde ahí el bot deja de responder a ese contacto.
8. Si OpenAI falla → mensaje cortés al cliente y pasa a atención personalizada.

## Preguntas frecuentes (solo si el cliente pregunta)
Agentes y cuentas sin límite (un solo agente de IA adaptado al negocio) · WhatsApp Business, varias cuentas posibles
(ideal un número oficial) y se sigue usando en el celular · app de celular y computadora · WhatsApp, Instagram,
Facebook, TikTok y email · a los curiosos se les resuelven dudas y se recopilan los datos del viaje · ideal para
agencias que empiezan · llamada por Zoom de 20-30 min con el equipo · implementación de 3 a 5 días · contrato con
permanencia inicial de 3 meses · la información y promociones de la agencia se guardan en un documento.
Lo que no está en la lista (p. ej. integraciones) no lo afirma ni lo niega: lo deja para la llamada.

## Buffer de mensajes (pendiente)
`USAR_BUFFER = False` en `n8n/generar_flujos.py`. Para activarlo: ejecutar `supabase/maripino_buffer.sql` en el
proyecto XzenAuto, poner `USAR_BUFFER = True`, regenerar y subir el flujo.

## Seguimientos (flujo «Maripino · Seguimientos», cada 15 min)
Si el lead no responde al último mensaje de Maripino, le escribe a las **5 h, 7 h y 12 h** un mensaje
redactado por la IA según la conversación (el 3.º es una despedida amable). Reglas:
- Nunca entre las 23:00 y las 08:00 (hora de México); lo pendiente sale a partir de las 8:00, uno a la vez.
- Solo dentro de la ventana de 24 h de WhatsApp desde el último mensaje del cliente.
- No a contactos con `cita-agendada`, `atencion-personalizada` o `maripino-off`.
- Etiquetas `seguimiento-1/2/3`; se borran cuando el cliente vuelve a escribir.
- Contactos `test-maripino`: 5, 7 y 12 minutos, sin horario silencioso.

## Rescate de leads sin respuesta (flujo «Maripino · Rescate de leads sin respuesta», cada 2 h)
Busca en GHL conversaciones de WhatsApp cuyo último mensaje es del cliente (de hace más de 10 min y menos de
23 h) y se las pasa a Maripino, que contesta si es un lead suyo. Entre las 23:00 y las 08:00 no rescata: lo
pendiente sale en la vuelta de las 8:00. Cada mensaje se rescata una sola vez.

## Reporte diario (flujo «Maripino · Reporte diario (correo)», 8:00)
Correo HTML a xzenauto@gmail.com con: anuncios (ayer, 7 días y desde el inicio: gasto, impresiones, clics,
conversaciones, leads y costo por lead), estado de los leads (en conversación, en seguimiento, agendados,
atención personalizada, perdidos), columnas del pipeline, ciudades que más contactan, si invierten en
anuncios de Facebook, volumen medio de leads que declaran, próximas llamadas y leads de ayer.
Las estadísticas de Meta necesitan la credencial **«Meta Ads XzenAuto»** (tipo *Facebook Graph API*, token
con permiso `ads_read` sobre la cuenta publicitaria `act_48823661`) en los nodos *Meta ayer / 7 días / total*.

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
