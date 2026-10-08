# Apoyos visuales: (inicio, fin, tipo, fuente, segundo de inicio)
#  tipo "card"  = maqueta de anuncio (PNG) sobre el plano desenfocado
#  tipo "vert"  = B-roll vertical a la izquierda sobre fondo desenfocado
#  tipo "h"     = B-roll horizontal a pantalla completa
VISUALS = [
    (2.30, 5.40, "card", "ad_europa", 0),                 # te dijeron que con anuncios de Facebook ibas a vender
    (7.27, 10.43, "card", "ad_cancun", 0),                # para Facebook, tus clientes son los que dan clic
    (16.47, 18.37, "h", "chat_viajes", 6.0),              # cuáles sí nos compraron y cuáles no (CRM)
    (18.37, 21.10, "vert", "reporte_meta_ganados", 0.0),  # automatización que le dice a Facebook…
    (21.10, 23.33, "vert", "leads_ganados", 1.0),         # …cuando un cliente sí nos compró
    (24.60, 27.03, "card", "ad_resultados", 0),           # Meta optimiza la inversión
    (27.03, 29.36, "vert", "leads_ganados", 4.0),         # más clientes como los que sí compraron
]
BROLL = [(a, b, None, 0) for a, b, *_ in VISUALS]        # para el render del plano principal
EMPHASIS = [1.54, 5.58, 6.60, 11.48, 12.88, 14.42, 30.06, 31.36]
JUMPS_A = [10.43, 12.67]                                  # cortes que quedan en plano principal
HOOK_END = 2.30
