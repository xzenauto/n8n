# Casa Alpa — Vale (asesora IA) v2

Respaldo y documentación de lo que corre en producción (n8n `n8n.srv964593.hstgr.cloud`, Supabase `fllhjemdhohsewqwzrpc`, GHL subcuenta `iYgqtO9TzgsM2X4hzyhj`).

## Workflows en n8n

| Workflow | ID | Qué hace |
|---|---|---|
| Vale - Casa Alpa (Asesora IA) | `4uL8xM5E6yI7bMWd` | Atiende los mensajes que manda GHL al webhook `/webhook/vale-casa-alpa` |
| Casa Alpa - Sync variantes Shopify | `kMHpWnZ7SiWtLsJh` | Diario 6:17: lee `casaalpa.mx/products.json` y actualiza precios/variantes/disponibilidad en `casa_alpa_variantes` |
| Casa Alpa - Pedido pagado Shopify → GHL | `tP8yassgq4k1vmgL` | Webhook de Shopify "Pago de pedido": gana la oportunidad, etiqueta `compro-shopify`, nota con productos y dirección, tarea "Preparar envío", avisa al cliente |
| Casa Alpa - Recordatorio link de pago | `amLZt7elV0Q0E9eP` | Cada hora: links enviados hace 20–23.5 h sin pagar → un recordatorio |

`workflows/vale_v1_original.json` es la versión anterior (sin datos fijados) por si hay que regresar.
Los `build_*.py` generan los JSON; el token secreto de la ruta del webhook de Shopify no se versiona.

## Flujo de Vale

1. **Entrada**: canal según `message.type` de GHL (11 FB, 18 IG, 19 WhatsApp). Se guarda el mensaje, espera 8 s y sólo la última ejecución responde (agrupa ráfagas).
2. **Pausa**: no responde si la oportunidad está en *Agente personal* o *Cliente ganado*, o si el contacto tiene la etiqueta `vale-pausada`.
3. **Contexto**: prospecto, anuncio de origen (`casa_alpa_anuncios_muebles.ad_id`), último link de pago, FAQs del Google Doc e historial (`casa_alpa_mensajes`, persistente).
4. **Agente** (gpt-4.1) con salida estructurada y tools: `buscar_catalogo` (RPC), `actualizar_prospecto`, `generar_link_pago` (RPC). Si el agente falla, manda un mensaje cortés y pasa con un asesor.
5. **Envío**: mensajes con pausa y fotos de producto (datos desde Supabase, no del modelo).
6. **CRM**: etapa y resumen en Supabase; la oportunidad sólo avanza (Explorando → Interesado → Cotización enviada); en handoff va a *Agente personal* con etiqueta `vale-handoff`, tarea y nota. Si un mensaje no se pudo entregar, también se crea el handoff.

## Link de pago

`casa_alpa_generar_link_pago` arma un carrito de Shopify: `https://casaalpa.mx/cart/{variant_id}:{cantidad}?attributes[ghl_contact_id]=…&attributes[vale_link_id]=…`.
El cliente paga y captura su dirección en el checkout de Shopify. Al pagarse, el webhook de Shopify liga el pedido con el contacto por esos atributos (o por teléfono/email si no vienen).

## Pruebas

Para reiniciar un contacto de prueba: ponerle la etiqueta `test-vale` en GHL y escribir `Borrar`. Borra oportunidades, contacto y sus datos en Supabase. Sin la etiqueta, "Borrar" es un mensaje normal.

## Supabase

`supabase/01_vale_v2_esquema.sql`, `02_funciones.sql`, `03_etapas.sql`: cambios aplicados el 2026-10-01.
