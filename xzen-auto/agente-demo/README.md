# Agente demo xzen Auto — WhatsApp desde anuncios de Meta

Agente de IA que atiende a quienes escriben por WhatsApp desde los anuncios de xzen Auto,
**se presenta como la propia demostración del sistema**, resuelve dudas, envía el video y agenda
una llamada en el calendario de GoHighLevel (subcuenta **Xzen Auto**, `8SiKgyVuy9KVUIx1Y1RT`).

## Anuncios detectados (Meta)
Campaña `XZEN_AgenciaViajes` · objetivo Engagement · destino **WhatsApp** (Click-to-WhatsApp).

| ID anuncio | Nombre | Vertical |
|---|---|---|
| 52613806312397 | XZEN_AgenciaViajes_Flyer1 | agencia_viajes |
| 52613807534997 | XZEN_AgenciaViajes_VideoXime | agencia_viajes |
| 52613807845997 | XZEN_AgenciaViajes_VideoCarlos1 | agencia_viajes |
| 52613808070397 | XZEN_AgenciaViajes_VideoCarlos2 | agencia_viajes |
| _(futuros)_ | Muebles | tienda_muebles |

## Cómo se sabe de qué anuncio viene
En los anuncios Click-to-WhatsApp, **el primer mensaje** del cliente trae un bloque `referral`
con `source_type: "ad"` y `source_id` = **ID del anuncio**. Solo llega en ese primer mensaje, así que:

1. En el primer mensaje se lee `source_id` → se busca en `enrutamiento-anuncios.json` → vertical.
2. La vertical se **guarda en el contacto de GHL** (tag `demo-agencia-viajes` + campo
   personalizado `vertical_demo`).
3. En los mensajes siguientes se lee la vertical del contacto, no del anuncio.
4. Sin `referral` o ID desconocido → vertical `general` (pregunta el giro del negocio).

## Flujo (n8n)
```
WhatsApp entrante ──► Webhook n8n
   │
   ├─ ¿Contacto existe en GHL? ── no ─► crear contacto
   ├─ ¿Tiene vertical? ── no ─► leer referral.source_id ─► mapa de anuncios ─► guardar tag/campo
   │
   ├─ Switch por vertical ──► agencia_viajes │ tienda_muebles (inactivo) │ general
   │
   └─ AI Agent (prompt de la vertical + memoria por teléfono)
        herramientas:
          • consultar_disponibilidad  → GET  /calendars/{id}/free-slots
          • agendar_cita              → POST /calendars/events/appointments
          • enviar_video              → mensaje con link de YouTube
          • pasar_a_humano            → tag "atender-humano" + pausa del bot
   │
   └─ Respuesta ──► WhatsApp (vía GHL Conversations o Cloud API)
```

Añadir muebles = meter sus IDs en `enrutamiento-anuncios.json`, completar
`prompts/tienda-muebles.md` y poner `activo: true`. No hay que tocar el flujo.

## Archivos
- `enrutamiento-anuncios.json` — mapa anuncio → vertical, video y tag.
- `prompts/agencia-viajes.md` — instrucciones del agente para agencias de viajes.
- `prompts/tienda-muebles.md` — plantilla lista para cuando existan los anuncios de muebles.
- `prompts/general.md` — mensajes sin anuncio identificado.
- `simulacion-conversacion.md` — ejemplo de cómo hablaría el agente.

## Pendiente de confirmar
Los marcadores `{{...}}` de los prompts se rellenan con las respuestas del cliente
(nombre del agente, política de precios, etc.).
