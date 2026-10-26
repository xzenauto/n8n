---
name: editar-reel
description: Edita un reel/vídeo corto con el estilo guardado del usuario (gancho en letra grande, subtítulos Bebas Neue palabra a palabra junto a la cara, palabras clave en amarillo, zoom lento en el plano principal, B-roll con palabra centrada, color cinematográfico suave). Úsalo cuando el usuario diga "toca editar un reel", "edita este reel", "con mi estilo de reels" o similar.
---

# Editar reel — estilo guardado

Estilo extraído del reel de referencia (instagram.com/reel/Dd-J7SAhTC5, 57 s, 16:9).
Contesta siempre en español.

## 0. Base de datos de B-rolls (`brolls/brolls.json` + `brolls/brolls_db.py`)

- Antes de elegir B-rolls ejecuta `python3 brolls/brolls_db.py sugerir 20 [tema]`. Te da los menos
  usados y los que no salieron en los 2 últimos reels, junto con la orientación y notas (rotación errónea, partes inservibles…).
- **Nunca repetir un clip dentro del mismo reel.** Entre reels, priorizar los menos usados.
- Al entregar: `brolls_db.py registrar <nombre_reel> clip1 clip2 …` y después `brolls_db.py informe`
  (regenera `brolls/USO_BROLLS.md`).
- Si el usuario sube clips nuevos a la carpeta de Drive (`carpeta_drive` en el JSON), da de alta cada
  uno con `brolls_db.py nuevo <nombre> <drive_id> <h|v> "<título>" tema1,tema2`.
- Comprueba la rotación de cada clip nuevo con un fotograma. Algunos clips de iPhone traen rotación −90 pero son
  horizontales (EEUU 1 y 2): se leen con `-noautorotate`.
- B-roll vertical en un formato 16:9: se recorta una franja 16:9 centrada en el sujeto (`yc` en
  `ejemplos/pov_broll_montaje.py`). En los reels POV el usuario pidió expresamente gimnasio, viajes, aeropuerto y familia, aunque son verticales.
- En reels POV entregar también la versión **sin texto** (el usuario pone el texto en Instagram).

## 1. Cómo es el estilo

**Subtítulos (lo más característico)**
- **Configuración fija elegida por el usuario (no cambiarla sin que lo pida):**
  - Tipografía **Bebas Neue** (mayúsculas estrechas, incluida en `fonts/`), blanca.
  - Tamaño: **5 % del alto** del frame (se subió desde 3,5 % por feedback: costaba leerlos).
  - **Gancho (primera frase o dos) en grande**: 16 % del alto, frase completa en varias
    líneas, en el lado de la pantalla que la cara deja libre durante toda la frase
    (opción `--hook <segundo en que acaba el gancho>`). Sobre B-roll, palabra a palabra
    grande y centrada. "Cuanto más llamativo y grande, mejor".
    Máximo 3 líneas: si la columna libre junto a la cara es estrecha, el gancho reduce su
    tamaño automáticamente (hasta el 55 %) en vez de salirse de la pantalla.
  - **Sin sombra**, sin caja ni contorno.
  - **Palabras clave en amarillo** (`HL_COLOR` = 255, 210, 60): 1 por bloque como máximo,
    las que llevan el mensaje (temas, beneficios, conceptos: "negocio", "reto físico",
    "mentalidad", "límites"…). Se marcan con `"hl": true` en `words.json` antes de renderizar.
- **Sin puntuación**.
- Las palabras **aparecen una a una** según se dicen (fundido de 80 ms) y se acumulan en
  bloques de 2–5 palabras; el bloque desaparece entero cuando empieza el siguiente.
- Espaciado amplio entre palabras (~0,55 em extra): se lee "aireado".
- **Posición: a la altura de los ojos, repartidas a los lados de la cara** — la primera
  mitad del bloque a la izquierda de la cabeza y el resto a la derecha
  (p. ej. `sin saber realmente  [cara]  si`). Nunca tapan la cara.
- **Planos sin cara (B-roll)**: una sola palabra cada vez, centrada; el script mira la imagen y
  la pone en la franja más oscura (centro, tercio inferior o superior) sin tapar caras. Si todo
  el plano es claro (capturas de pantalla del sistema), el texto pasa a **oscuro** (negro, y
  naranja intenso las palabras clave) — así se lee sin usar sombra. La palabra es
  un poco más grande (×1,25). Funciona como palabra clave: "instantáneamente",
  "networking", "desesperados", "relaciones".

**Montaje**
- **Zoom lento en el plano principal**: cada tramo de A-roll se acerca muy despacio
  (+1,2 % por segundo, máx. 10 %), con la cara como punto fijo para que los subtítulos no
  se desplacen. Se hace en el montaje: escalar a 4K con lanczos y
  `zoompan=z='min(1.10,1+0.012*on/30)':x='PX*(1-1/zoom)':y='PY*(1-1/zoom)':d=1:s=1920x1080:fps=30`
  (PX, PY = cara en coordenadas 4K; mediana del tramo; si la persona camina, centro).
- Ritmo rápido: un corte cada ~2,5 s de media (22 cortes en 57 s), sin silencios.
- Plano principal (A-roll) hablando a cámara con gran angular, alternado con **B-roll
  real del día a día**: reuniones, videollamadas, coche con el equipo, trabajando en
  cafetería, apretones de manos, ciudad. El B-roll ilustra literalmente lo que se dice.
- Arranca directamente con la frase gancho (sin intro ni logo) y termina con la frase
  de cierre, sin pantalla final.
- Voz a ~4,5 palabras/s, clara y en primer plano.

**Color**
- Natural y cinematográfico: contraste algo suave, saturación ligeramente baja, luces
  un pelín cálidas. Filtro aproximado (opción `--grade`):
  `eq=contrast=0.96:saturation=0.9:gamma=1.02,colorbalance=rs=0.02:bs=-0.02:rh=0.03:bh=-0.03`

**Sin**: emojis, cajas de color, subtítulos grandes estilo TikTok, zooms agresivos,
efectos de sonido llamativos ni transiciones elaboradas (cortes secos).

## 2. Flujo de trabajo

1. **Conseguir el vídeo.** Si viene por Google Drive, descárgalo con curl desde
   `https://drive.usercontent.google.com/download?id=<ID>&export=download&confirm=t`
   (nunca con el conector de Drive: mete el archivo en base64 en el contexto).
   Dominios que deben estar permitidos en la red del entorno:
   `drive.usercontent.google.com`, `drive.google.com`, `openaipublic.azureedge.net`.
2. **Dependencias**:
   `pip install openai-whisper pillow numpy "mediapipe==0.10.14"`
   (las versiones nuevas de MediaPipe ya no incluyen el modelo de caras; la 0.10.14 sí).
3. **Transcribir y revisar**:
   `python3 reel_subs.py entrada.mp4 --dump` → genera `entrada.words.json`.
   Revisa nombres propios y palabras mal transcritas y corrígelas en el JSON
   (mantén los tiempos).
4. **Proponer al usuario** (antes de renderizar) los puntos de B-roll si tiene clips
   extra, y confirmar el formato: el original es **16:9**; si el material es vertical
   9:16, el script usa la misma lógica (cuando no hay sitio a los lados de la cara,
   coloca el bloque centrado encima de la cabeza).
5. **Marcar palabras clave**: añade `"hl": true` a las palabras importantes en el JSON
   (aprox. 1 de cada 6–8 palabras; nunca artículos ni muletillas). Enséñale la lista al
   usuario en el resumen final.
6. **Montaje** (si hay que cortar o meter B-roll): cortes secos con ffmpeg
   (`trim` + `concat` por fotogramas), quitando silencios > 0,3 s. Monta primero y
   subtitula después, sobre el vídeo ya montado. **Calidad (el usuario lo exige):**
   - Comprueba con ffprobe si el material es HDR de iPhone (`arib-std-b67`, 10 bits).
     Si lo es, convierte TODO (plano principal y B-rolls) con el mismo filtro calibrado:
     `zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p`
     (es el que más se parece a la exportación SDR del propio usuario).
   - **Saturación de los B-rolls:** mide la saturación media (HSV) de cada B-roll y del
     plano principal tras la conversión; si un B-roll está más saturado, bájala con
     `eq=saturation=principal/b-roll` (entre 0,65 y 1). Nunca la subas.
   - Escala con `flags=lanczos`, B-rolls de 60 fps a 30 con `fps=30`.
   - El montado se guarda **sin pérdida** (`-c:v libx264 -preset ultrafast -qp 0`, .mkv)
     para que solo haya una compresión: la final del script (`--crf 15 --preset slow`).
   - **Grabado a mano (sin trípode) / la toma salta en los cortes** → estabilizar contra un
     encuadre de referencia (efecto trípode), ver `ejemplos/estabilizar_*.py`:
     1. Detectar cara en todos los fotogramas (`faces(..., step=1/30)` → `faces_all.json`).
     2. `estabilizar_detect.py <seg_ref>`: ORB + RANSAC (`estimateAffinePartial2D`) de cada
        fotograma contra el de referencia, **enmascarando a la persona** (cabeza + cuerpo),
        así solo cuenta el fondo. Comprueba inliers (>300) y desplazamientos.
     3. Detectar los cortes (saltos de diferencia de imagen > 4× la mediana) y ponerlos en
        `CUTS`; el suavizado (mediana de 7 fotogramas) nunca cruza un corte.
     4. `estabilizar_render.py`: en UNA sola remuestra desde el original (4K si lo hay):
        estabilización + recorte fijo `BASE=1.08` (oculta bordes) + zoom lento, warp
        `INTER_CUBIC` a 4K y `INTER_AREA` a 1080p. Salida sin pérdida → luego B-rolls.
     5. Verificar: diferencia del fondo antes/después de cada corte (debe bajar >50 %).
   - Si la saturación del plano principal ya es alta, el B-roll solo se baja si la supera.
   - **Cámara fija pero saltos de postura en los cortes** (comprobar con `estabilizar_detect.py`:
     si dx/dy < 2 px no hay que estabilizar): alternar plano normal / cerrado (+10 %) en cada
     corte que quede en plano principal + zoom lento (`ejemplos/aroll_punch_zoom.py`).
   - Usar solo B-rolls **horizontales** (comprobar la rotación con ffprobe: 1920x1080 con
     rotación −90 es vertical).
7. **Render**:
   `python3 reel_subs.py montado.mkv final.mp4 --words montado.words.json --grade --hook 3.0 --broll 1.8-3.0,4.6-6.5`
   (`--broll` con los tramos donde hay B-roll: así siempre sale la palabra centrada aunque
   en el B-roll aparezcan otras caras). Los subtítulos se colocan una vez por bloque y no
   se mueven; en planos quietos todos los bloques comparten posición. Si no hay cara, el
   texto va arriba (nunca encima de la persona). `--font/--size/--no-shadow` solo para
   pruebas: la configuración por defecto ya es la elegida.
8. **Revisión**: extrae 4–6 fotogramas en una sola hoja (`tile`) y comprueba que el
   texto no tapa caras ni se sale del encuadre antes de entregar.
9. **Entrega**: el chat solo admite archivos pequeños (un vídeo de ~40 MB ya falló).
   Opciones probadas: subirlo a una rama de este repositorio (máx. 100 MB por archivo;
   partir con `ffmpeg -f segment` si hace falta) o pedir al usuario un destino.

## 2b. Zoom-ins de énfasis y música (cuando el usuario los pide)

- **Zoom-ins leves para dar dinamismo** (`ejemplos/aroll_zoom_enfasis.py` + `plan_enfasis.py`):
  además del plano alterno en cortes y el zoom lento, en 6–9 frases clave del plano
  principal se acerca +7 % en 0,35 s (ease in-out) y se mantiene hasta el siguiente corte.
  Lista `EMPHASIS` con el segundo de la palabra que arranca la frase clave.
- **Música de fondo motivacional sin letra**: no descargar música (derechos + red). Se
  compone una pista original con `ejemplos/musica_motivacional.py <duración> salida.wav`
  (Am–F–C–G, 100 BPM, capas que crecen: pad+piano → bajo+bombo → palmas → charles).
  Mezcla: música a −23 dB (`volume=0.07`) con *ducking* por la voz
  (`sidechaincompress=threshold=0.015:ratio=4:attack=30:release=450`) y `loudnorm=I=-14`.
  Objetivo: música ≥10 dB por debajo de la voz en las pausas.
- Scripts que leen archivos descargados: ejecutarlos con `python3 -I` desde una carpeta de
  trabajo distinta a la de descargas (scripts en `scripts/`, descargas en `in/`).

## 2c. Apoyos visuales: maquetas de anuncios y B-roll vertical (`ejemplos/*paneles*`, `maquetas_anuncios.py`)

- **Maquetas de anuncios de Facebook/Instagram** cuando el usuario las pide: se diseñan con
  PIL (tarjeta tipo feed: avatar, "Publicidad", texto, foto, barra de título con precio y botón
  CTA, reacciones). Marca **ficticia** ("Viajes Horizonte"), nunca logos/marcas reales.
  Fotos: fotogramas de los propios clips del usuario. Si muestran resultados/métricas
  inventadas → etiqueta **"EJEMPLO"**. Animación: entra desde abajo (0,4 s) a la izquierda
  (centro en 30 % del ancho) sobre el plano principal desenfocado y oscurecido; si se habla
  de "dar clic", animar un toque (círculo) sobre el botón.
- **B-roll vertical que el usuario pide expresamente** (p. ej. pantallas del CRM o de la
  automatización): se coloca entero a la izquierda sobre una copia desenfocada de sí mismo.
- En esos tramos los subtítulos van con `--panel ini-fin,...`: palabra única a la derecha
  (74 % del ancho), en oscuro si el fondo es claro.
- Para separar texto y cara se usa el ancho MÁXIMO de la cara en el bloque (los zooms de
  énfasis la agrandan mientras la frase está en pantalla).

## 2d. Listas numeradas, música inspiracional, whoosh y legibilidad en A-roll

- **Puntos numerados `[#1]`, `[#2]`, `[#3]`** (cuando el vídeo es "las 3 cosas que…"):
  `ejemplos/numerar_puntos.py words.json words.json` junta "Número 1" en una palabra `[#1]`
  con `"hl": true` y `"scale": 1.5` (algo mayor que el resto, en amarillo) y la deja en el
  mismo bloque que el título del punto. Cualquier palabra admite `"scale"` en `words.json`.
- **Cambio de plano por sección**: en una toma única en trípode, cada punto `[#n]` arranca con
  cambio normal/cerrado (`JUMPS` en `ejemplos/plan_secciones.py`, con `aroll_zoom_enfasis.py`)
  y dentro de cada sección 1–2 zoom-ins de énfasis. Pasa esos mismos tiempos a `--cuts`
  (un poco antes de la palabra, p. ej. 6.80 si la palabra empieza en 6.86).
- **Música inspiracional** (más calmada que la motivacional): `ejemplos/musica_inspiracional.py`
  (C–G–Am–F, 80 BPM, piano + pad, latido suave, campanitas al final). Mezcla a `volume=0.09`
  con el mismo ducking.
- **Efecto de sonido de movimiento de cámara**: `ejemplos/sfx_whoosh.py <dur> sfx.wav t1 t2…`
  con los tiempos de cada zoom/cambio de plano; mezclar a `volume=0.10` (picos ≈ −27 dB,
  discreto). Mezcla final:
  `[voz][música con ducking][sfx]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.0:LRA=11`.
- **Fondo claro junto a la cara** (pared beige/blanca): `reel_subs.py` lo detecta solo. El
  grupo de palabras de ese lado se desplaza hacia fuera hasta una zona oscura (p. ej. la
  madera) si cabe; si no, va en oscuro (negro / naranja). El amarillo nunca queda sobre beige.

## 2e. Reel "POV" solo con B-rolls y una canción (`ejemplos/pov_*.py`, `detectar_tempo.py`)

- Formato 9:16 (1080x1920) con el B-roll 16:9 centrado (1080x608, y=656) y franjas negras.
  El texto POV va en la franja de arriba, en Bebas Neue blanca, centrado y pegado al vídeo, con las palabras clave en amarillo.
- Tempo: `detectar_tempo.py cancion.wav` da BPM y fase. Busca el momento en que entra el beat
  fuerte (subida de graves) y empieza 2–3 compases antes, para que el "drop" caiga hacia el segundo 6–7.
- Cortes a compás exacto (1 compás por plano tras el drop, 1–2 antes), fotogramas calculados
  de forma acumulada para que no haya deriva. Empuje lento alterno (1.00↔1.06) en cada plano.
- Mismo tonemap HDR y grade. Fundido de entrada y de salida, `loudnorm=I=-14`.

- **Variante "frase en el centro"** (reel "la disciplina gana al talento"): la frase va centrada en
  la pantalla, encima del vídeo, en Bebas 150 px con sombra difuminada (`ejemplos/pov_frase_centrada.py`).
  La línea 1 está desde el inicio y la línea 2 entra con el beat. El vídeo se oscurece un poco (`eq=brightness=-0.06`).
  Sin canción del usuario: `musica_motivacional.py` (100 BPM, compás de 2,4 s, el beat entra en el
  compás 2 = 4,8 s). Intro con 2 planos de 2 medios compases de intro y luego 1 por plano.

- **Montaje rápido "solo B-roll", sin texto ni música** (versión final del reel de disciplina): el usuario
  pidió cambiar de plano cada 1–2 s (1,2–1,8 s variando) y usar solo clips en los que sale grabando,
  trabajando o entrenando; **nada de viajes**. `montaje.py` con `half = 1.0` y la duración de cada plano en segundos.
  Se exporta sin pista de audio (la música la pone él en la app).

## 2f. Subtítulos centrados fijos, títulos grandes y fotos como B-roll (reel "oferta 90 días")

- **Centrados y estables** (petición del usuario): `--center 0.80`. El bloque va en una línea, centrado
  y a altura fija (sobre el pecho, nunca sobre la cara). En los momentos importantes
  (`--move ini-fin,...`) los subtítulos pasan junto a la cara, con el estilo de siempre.
- **Título de algo importante** (p. ej. el nombre de la oferta): `--title ini-fin`. La frase sale
  completa, centrada y a tamaño de gancho, con "90 días" en amarillo. En el montaje, ese tramo del plano se
  desenfoca y oscurece (`gblur=18`, `eq=brightness=-0.12`, fundidos de 0,15 s) para que se lea como un rótulo.
- **Material 4:3** (2880x2160): recortar a 16:9 (2880x1620) con los ojos al ~38 % del alto
  y aplicar el zoom en una sola remuestra (`aroll.py` del reel 11 = `aroll_zoom_enfasis.py` + recorte).
- **Foto vertical como B-roll** (HEIC del iPhone → `pillow-heif`): a la izquierda sobre una copia
  desenfocada y oscurecida, con zoom lento (1,00 → 1,05). Los subtítulos de ese tramo van con `--panel`.
- **Ropa clara bajo los subtítulos centrados** (camiseta blanca): degradado negro en la parte baja
  del plano (transparente al 62 % del alto → 62 % de opacidad al 76 %), superpuesto antes de
  `reel_subs.py`. Con él, el blanco y el amarillo se leen siempre.
- **Lista "Número 1/2/3" en el estilo centrado**: `numerar_puntos.py` (acepta "1." con punto) +
  `--title` en cada punto ("[#1] Automatiza la atención al cliente") con fondo desenfocado y
  un whoosh discreto al entrar. Si el usuario pide música en ese estilo: `musica_motivacional.py`.
- **Si el vídeo ya trae música, no se añade otra**: solo `loudnorm=I=-14`.

## 3. Anuncios / resúmenes verticales (9:16) a partir de un vídeo largo

Probado con el VSL de agencias de viajes → anuncio de 54 s (`ejemplos/anuncio_*.py`):
1. Transcribir con Whisper **medium** y elegir fragmentos de beneficios (gancho con la
   promesa más fuerte primero; CTA al final), 40–60 s en total. Cortar SIEMPRE entre
   palabras (inicio = palabra − 0,10 s, fin = palabra + 0,15 s, sin pisar la siguiente).
2. Plano vertical desde el 4K en una sola remuestra (`anuncio_aroll_vertical.py`):
   ventana 9:16 a altura completa centrada en la cara, **alternando plano normal y
   cerrado (+12 %) en cada corte** para que los saltos parezcan intencionados, + zoom lento.
   Audio de los mismos fragmentos con fundidos de 15 ms.
3. B-roll horizontal en vertical: el clip entero en el centro sobre una copia suya
   desenfocada (`gblur=40`, algo oscurecida) — no recortar pantallas del sistema.
4. Subtítulos: `reel_subs.py … --vertical --hook <fin gancho>` → bloque completo centrado
   al 70 % del alto (anuncios se ven sin sonido: subtítulos completos), gancho arriba.
5. Audio final AAC normalizado: `loudnorm=I=-14:TP=-1.0:LRA=11`.

## 3b. Anuncios de Meta en 4:3 con recursos gráficos (`recursos.py`, `ejemplos/aroll43.py`, `broll43.py`)

Hecho para los 4 anuncios (agencia de viajes y mueblería, corto y largo). El material llega en 4:3 (2880x2160) y se entrega igual (1440x1080).
1. `aroll43.py src faces.json plan.json aroll.mkv`: una sola remuestra con plano normal/cerrado (+10 %) en
   cada corte, zoom lento y zoom-ins de énfasis (`plan.json` = cuts + emphasis).
2. `broll43.py aroll.mkv inserts.json mont.mkv`: B-roll horizontal a pantalla completa (recorte 4:3) o
   vertical centrado sobre una copia desenfocada. Banco: chat_viajes / chat_muebleria cuando entra "el agente de IA",
   reporte_meta_ganados / leads_ganados cuando habla de medir anuncios y vendedores.
3. `recursos.py mont.mkv timeline.json rec.mkv`: **recursos que ilustran lo que dice** (tarjetas oscuras
   redondeadas, Inter + Bebas, a la izquierda sobre el portátil con `col_x 0.215`, `scale 1.22`, más un degradado
   inferior para los subtítulos). Tipos: chat (mensajes a todas horas), comments (piden precio), timer (sin responder),
   alert (cliente perdido), badge (24/7, TIEMPO PERDIDO, MÁS VENTAS), checklist (lo que pregunta el agente / catálogo),
   flow (cómo funciona), bars (ventas por anuncio o vendedor, etiqueta EJEMPLO), cta (palabra clave + WhatsApp).
   Las líneas de tiempo de ejemplo están en `ejemplos/anuncios_4x3/tl_*.json`.
4. Subtítulos: `reel_subs.py rec.mkv subs.mp4 --grade --hook <fin> --center 0.85 --cuts ...`: bloque centrado abajo
   (los anuncios se ven sin sonido), gancho grande junto a la cara y palabras clave en amarillo.
5. Audio: voz, `musica_motivacional.py` a volume 0.065 con ducking, `sfx_pop.py` (0.10) en cada recurso y
   `sfx_whoosh.py` (0.09) en cada B-roll, `loudnorm=I=-14`.

## 4. Ajustes rápidos (constantes al principio de `reel_subs.py`)

| Constante | Valor | Qué controla |
|---|---|---|
| `SIZE_H` | 0.05 | tamaño de letra (fracción del alto) |
| `FONT` | Bebas Neue | tipografía |
| `SHADOW` | False | sombra bajo el texto |
| `HL_COLOR` | (255, 210, 60) | color de las palabras clave |
| `WORD_GAP` | 0.55 | espacio extra entre palabras |
| `FACE_GAP` | 0.45 | separación entre texto y cara |
| `MAX_WORDS` | 5 | palabras por bloque |
| `BROLL_SCALE` | 1.25 | tamaño de la palabra en B-roll |
| `HOOK_H` | 0.16 | tamaño del gancho |
