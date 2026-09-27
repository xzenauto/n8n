# Primero Viajo: pipeline de ventas en GoHighLevel

Pipeline de oportunidades para la agencia de viajes **Primero Viajo**, más un workflow de n8n
(`primero-viajo-pipeline-ghl.json`) que registra los leads en GHL y los mueve entre etapas.

## 1. Pipeline "Ventas Primero Viajo"

| # | Etapa | Clave para n8n | Qué significa | Acción / automatización sugerida en GHL |
|---|-------|----------------|---------------|-----------------------------------------|
| 1 | Nuevo lead | `nuevo_lead` | Llegó por el formulario, WhatsApp, Facebook o el agente Sofía | Asignar asesor; mensaje de bienvenida automático; tarea "Contactar en menos de 15 min" |
| 2 | Contactado | `contactado` | Un asesor ya habló con el cliente | Si no responde en 24 h, secuencia de 3 recordatorios (WhatsApp/SMS/email) |
| 3 | Calificado | `calificado` | Ya se sabe destino, fechas, número de personas y presupuesto | Etiquetas `destino-*`; tarea "Armar cotización" |
| 4 | Cotización enviada | `cotizacion_enviada` | Se mandó la propuesta con precio | Recordatorio a las 48 h: "¿Pudiste revisar tu cotización?" |
| 5 | Seguimiento / negociación | `seguimiento` | Dudas, cambios de hotel o fechas, ajustes de precio | Tarea diaria para el asesor; aviso si pasa más de 7 días sin movimiento |
| 6 | Anticipo pagado ✅ | `anticipo_pagado` | Reserva confirmada (se marca como **ganada**) | Enviar confirmación y recibo; pedir pasaportes y datos de los viajeros |
| 7 | Pago completo / documentos | `pago_completo` | Liquidado; vouchers, boletos y seguro entregados | Enviar itinerario final y checklist de viaje |
| 8 | En viaje | `viaje_en_curso` | El cliente está viajando | Mensaje de buen viaje; contacto de emergencia 24/7 |
| 9 | Post-viaje | `post_viaje` | Ya regresó | Pedir reseña en Google a los 2 días; oferta para referidos a los 30 días |

**Perdido:** no es una etapa. Usa el estado *Lost* de GHL con un motivo (precio, eligió otra agencia,
no respondió, pospuso el viaje). Así el pipeline se mantiene limpio y puedes reactivar los leads
perdidos con una campaña.

### Cómo crearlo en GHL

La API de GHL solo permite **leer** pipelines, no crearlos, así que este paso se hace a mano (unos 2 minutos):

1. En la subcuenta de Primero Viajo ve a **Oportunidades → Pipelines → + Crear pipeline**.
2. Ponle de nombre `Ventas Primero Viajo` y agrega las 9 etapas de la tabla, en ese orden.
3. Guarda y copia el **ID del pipeline** y el **ID de cada etapa**. Los puedes sacar con:
   ```
   GET https://services.leadconnectorhq.com/opportunities/pipelines?locationId=TU_LOCATION_ID
   Authorization: Bearer <token>
   Version: 2021-07-28
   ```

## 2. Workflow de n8n

Importa `primero-viajo-pipeline-ghl.json` en n8n (**Workflows → Import from file**). Tiene dos webhooks:

### `POST /webhook/primeroviajo-lead`: registrar un lead nuevo
Crea o actualiza el contacto (sin duplicar) y abre una oportunidad en **Nuevo lead**.

```json
{
  "nombre": "Ana",
  "apellido": "López",
  "telefono": "+525512345678",
  "email": "ana@correo.com",
  "destino": "Cancún",
  "fechas": "15-20 dic",
  "presupuesto": 45000,
  "origen": "Chat Sofía"
}
```
Responde `{ ok, contactId, opportunityId }`.

### `POST /webhook/primeroviajo-mover-etapa`: cambiar de etapa
```json
{ "opportunityId": "abc123", "etapa": "cotizacion_enviada", "monto": 52000 }
```
- `etapa`: una de las claves de la tabla.
- A partir de `anticipo_pagado`, la oportunidad se marca como **ganada**.
- `{ "opportunityId": "abc123", "perdido": true }` la marca como perdida.

### Configuración
1. **Credencial:** crea una *Private Integration* en GHL (Configuración → Integraciones privadas)
   con los permisos `contacts.write` y `opportunities.write`. En n8n, crea una credencial **Header Auth**
   con nombre `Authorization` y valor `Bearer <token>`, y asígnala a los 3 nodos HTTP "GHL: …".
2. **IDs:** reemplaza `TU_LOCATION_ID`, `TU_PIPELINE_ID` e `ID_ETAPA_1…9` en los nodos Code
   **Config GHL (lead)** y **Mapear etapa**.
3. Si un mismo contacto puede tener varios viajes a la vez, activa en GHL
   *Configuración → Oportunidades → Permitir oportunidades duplicadas*. Si no lo activas, GHL rechaza
   una segunda oportunidad abierta para el mismo contacto en este pipeline.

### Conexión con el agente Sofía (workflow "Agencia viajes")
Cuando Sofía ya tenga nombre, teléfono, destino, fechas y presupuesto, haz un POST a
`/webhook/primeroviajo-lead` con esos datos y `"origen": "Chat Sofía"`. Si el agente detecta a un
cliente molesto, puedes llamar a `mover-etapa` o agregar la etiqueta `escalar-asesor` para que un
workflow de GHL avise al asesor.
