---
name: editar-reel
description: Edita un reel/vídeo corto con el estilo guardado del usuario (subtítulos finos palabra a palabra junto a la cara, B-roll con palabra centrada, color cinematográfico suave). Úsalo cuando el usuario diga "toca editar un reel", "edita este reel", "con mi estilo de reels" o similar.
---

# Editar reel — estilo guardado

Estilo extraído del reel de referencia (instagram.com/reel/Dd-J7SAhTC5, 57 s, 16:9).
Contesta siempre en español.

## 1. Cómo es el estilo

**Subtítulos (lo más característico)**
- Tipografía sans-serif **fina** (Inter Light 300, incluida en `fonts/`), blanca, sin caja ni
  contorno, solo una sombra muy suave. Tamaño pequeño: ~3,7 % del alto del frame.
- **Sin puntuación** y en minúsculas salvo inicio de frase y nombres propios.
- Las palabras **aparecen una a una** según se dicen (fundido de 80 ms) y se acumulan en
  bloques de 2–5 palabras; el bloque desaparece entero cuando empieza el siguiente.
- Espaciado amplio entre palabras (~0,55 em extra): se lee "aireado".
- **Posición: a la altura de los ojos, repartidas a los lados de la cara** — la primera
  mitad del bloque a la izquierda de la cabeza y el resto a la derecha
  (p. ej. `sin saber realmente  [cara]  si`). Nunca tapan la cara.
- **Planos sin cara (B-roll)**: una sola palabra cada vez, centrada en mitad del plano y
  un poco más grande (×1,25). Funciona como palabra clave: "instantáneamente",
  "networking", "desesperados", "relaciones".

**Montaje**
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
   `pip install openai-whisper pillow numpy "opencv-python-headless<5"`
   (OpenCV 5 ya no trae el detector de caras Haar).
3. **Transcribir y revisar**:
   `python3 reel_subs.py entrada.mp4 --dump` → genera `entrada.words.json`.
   Revisa nombres propios y palabras mal transcritas y corrígelas en el JSON
   (mantén los tiempos).
4. **Proponer al usuario** (antes de renderizar) los puntos de B-roll si tiene clips
   extra, y confirmar el formato: el original es **16:9**; si el material es vertical
   9:16, el script usa la misma lógica (cuando no hay sitio a los lados de la cara,
   coloca el bloque centrado encima de la cabeza).
5. **Montaje** (si hay que cortar o meter B-roll): cortes secos con ffmpeg
   (`-ss/-to` + concat), quitando silencios > 0,3 s. Monta primero y subtitula después,
   sobre el vídeo ya montado.
6. **Render**:
   `python3 reel_subs.py montado.mp4 final.mp4 --words montado.words.json --grade`
7. **Revisión**: extrae 4–6 fotogramas en una sola hoja (`tile`) y comprueba que el
   texto no tapa caras ni se sale del encuadre antes de entregar.
8. **Entrega**: el chat solo admite archivos pequeños (un vídeo de ~40 MB ya falló).
   Opciones probadas: subirlo a una rama de este repositorio (máx. 100 MB por archivo;
   partir con `ffmpeg -f segment` si hace falta) o pedir al usuario un destino.

## 3. Ajustes rápidos (constantes al principio de `reel_subs.py`)

| Constante | Valor | Qué controla |
|---|---|---|
| `SIZE_H` | 0.037 | tamaño de letra (fracción del alto) |
| `WEIGHT` | 300 | grosor de la fuente (100–900) |
| `WORD_GAP` | 0.55 | espacio extra entre palabras |
| `FACE_GAP` | 0.30 | separación entre texto y cara |
| `MAX_WORDS` | 5 | palabras por bloque |
| `BROLL_SCALE` | 1.25 | tamaño de la palabra en B-roll |
