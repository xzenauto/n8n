---
name: editar-reel
description: Edita un reel/vídeo corto con el estilo guardado del usuario (gancho en letra grande, subtítulos Bebas Neue palabra a palabra junto a la cara, palabras clave en amarillo, zoom lento en el plano principal, B-roll con palabra centrada, color cinematográfico suave). Úsalo cuando el usuario diga "toca editar un reel", "edita este reel", "con mi estilo de reels" o similar.
---

# Editar reel — estilo guardado

Estilo extraído del reel de referencia (instagram.com/reel/Dd-J7SAhTC5, 57 s, 16:9).
Contesta siempre en español.

## 1. Cómo es el estilo

**Subtítulos (lo más característico)**
- **Configuración fija elegida por el usuario (no cambiarla sin que lo pida):**
  - Tipografía **Bebas Neue** (mayúsculas estrechas, incluida en `fonts/`), blanca.
  - Tamaño: **5 % del alto** del frame (se subió desde 3,5 % por feedback: costaba leerlos).
  - **Gancho (primera frase o dos) en grande**: 16 % del alto, frase completa en varias
    líneas, en el lado de la pantalla que la cara deja libre durante toda la frase
    (opción `--hook <segundo en que acaba el gancho>`). Sobre B-roll, palabra a palabra
    grande y centrada. "Cuanto más llamativo y grande, mejor".
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
