# Cortar videos en Linux

Vamos a inspeccionar el primer episodio para saber exactamente qué tenemos antes de tocar nada.

## Paso 1: Verificar que ffmpeg/ffprobe están instalados

```bash
ffmpeg -version && ffprobe -version
```

Si no están instalados:

```bash
sudo apt update && sudo apt install ffmpeg
```

Tambien necesitamos instalar `python`

## Paso 2: Inspeccionar el contenedor completo del episodio

Esto te dice todas las pistas (vídeo, audio, subtítulos) con su índice, códec e idioma:

```bash
ffprobe -v error -show_entries stream=index,codec_type,codec_name,codec_tag_string:stream_tags=language,title -of default=noprint_wrappers=0 "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv"
```

Esto es lo importante: el `codec_name` de la pista de subtítulos te dice si es texto o imagen:

| codec_name          | Tipo                    | ¿Se puede extraer a texto directo? |
| ------------------- | ----------------------- | ---------------------------------- |
| `subrip`            | SRT texto               | Sí                                 |
| `ass` / `ssa`       | ASS texto (con estilos) | Sí                                 |
| `hdmv_pgs_subtitle` | PGS (imagen)            | No, necesita OCR                   |
| `dvd_subtitle`      | VobSub (imagen)         | No, necesita OCR                   |

## Paso 3: Versión más legible con `-show_streams` en JSON (opcional, más completo)

Si prefieres ver todo con más detalle (bitrate, resolución del vídeo, canales de audio):

```bash
ffprobe -v error -print_format json -show_format -show_streams "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv" > episodio_info.json
```

Luego puedes revisar `episodio_info.json` con `less` o `cat`, o pásamelo aquí y lo interpreto contigo.

## Paso 4: Si el subtítulo es texto — extraerlo de prueba 📌🔥

Supongamos que la pista de subtítulos en inglés es el índice `2` (lo confirmas con el resultado del Paso 2). Pruébalo así:

```bash
ffmpeg -i "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv" -map 0:2 S01E01.srt
```

Si te da un `.srt` válido con texto legible, vas por buen camino y avanzamos directo al parseo.

## Paso 5: Si el subtítulo es de imagen (PGS/VobSub)

No entres en pánico — es común en rips de Blu-ray/HMAX. En ese caso hay que usar OCR (por ejemplo `PGS-to-SRT` o `SubtitleEdit` vía Wine, o el proyecto `pgsrip` que usa Tesseract). Te armo esa parte solo si resulta ser el caso — no quiero añadir complejidad innecesaria si no la necesitas.

---

**Corre los pasos 1 y 2 (y si quieres el 4)** Con eso sabemos exactamente:

- Qué índice de pista usar para audio en inglés y subtítulos en inglés.
- Si necesitamos un paso de OCR extra o podemos ir directo al parseo del SRT.

---

---

Teniendo toda la información que necesitábamos. Resumen de lo que confirmamos:

| Pista      | Códec                             | Detalle                                                  |
| ---------- | --------------------------------- | -------------------------------------------------------- |
| Vídeo      | h264, 1440x1080 (DAR 4:3)         | Un único idioma (eng)                                    |
| Audio      | AC3, estéreo, 384kbps             | Un único idioma (eng) — no hay que elegir entre doblajes |
| Subtítulos | **subrip (texto)**, marcado `SDH` | Un único idioma/pista, ya extraído a `.srt`              |

Esto simplifica mucho el proyecto: no necesitamos OCR, no necesitamos lógica para elegir pista de audio/subtítulo entre varias — solo hay una de cada una. Y como es SDH ("Subtitles for the Deaf and Hard-of-hearing"), va a traer descripciones de sonido tipo `[music playing]`, `[door creaks]`, `(GASPS)`, etc. que **no** queremos como líneas de diálogo para Anki — hay que filtrarlas.

## Paso 6: Revisar el contenido real del .srt

Antes de decidir el filtro, necesito ver cómo luce el texto real. Corre esto y pégame el resultado:

```bash
head -60 S01E01.srt
```

Y para hacernos una idea rápida de qué patrones de "efectos de sonido" aparecen (útil para armar el filtro después):

```bash
grep -E '\[.*\]|\(.*\)' S01E01.srt | sort -u | head -40
```

También quiero ver cuántas líneas de diálogo reales hay vs. ruido, y cómo son los intervalos de tiempo entre líneas consecutivas (para decidir el padding y si conviene fusionar líneas muy cercanas):

```bash
grep -c '\-\->' S01E01.srt
```

(Esto cuenta cuántos bloques de subtítulo hay en total — el JSON dice 388, pero conviene confirmar.)

## Qué esperamos ver y por qué importa

- **Líneas de diálogo puras** → van directo al TSV.
- **Líneas con solo efectos** (`[MUSIC]`, `(SCREAMING)`) → se descartan completamente.
- **Líneas mixtas** (`(SIGHS) I can't believe this.`) → hay que decidir si limpiamos el texto (quitar la anotación y dejar solo el diálogo) o descartamos la línea entera. Mi sugerencia: limpiar y quedarnos con el diálogo, siempre que quede texto hablado real.
- **Nombres de personajes en mayúsculas al inicio** (`JOHN: Get down!`) — algunos SDH los incluyen. Si aparecen, hay que decidir si los quitamos del audio-texto o los dejamos como contexto.

Pega la salida de esos tres comandos y con eso diseñamos el filtro de limpieza antes de tocar el corte de vídeo.

---

---

Vemos dos cosas importantes que cambian el diseño del parser, antes de seguir:

## Hallazgo 1: El texto está en MAYÚSCULAS

Todo el diálogo viene en `ALL CAPS` (típico de SDH). Para las tarjetas de Anki esto se ve raro y no ayuda al listening (en inglés real nadie "lee" en mayúsculas). Propongo normalizar a "sentence case" al generar el TSV — el vídeo/audio no se toca, solo el texto que ves en la tarjeta.

## Hallazgo 2: Las oraciones están partidas en varios bloques de subtítulo

Mira los bloques 1-3:

```
1: WHAT WOULD YOU DO / IF AT THE MOMENT OF DEATH
2: A VOICE FROM / THE DARKNESS
3: OFFERED YOU A CHANCE / TO LIVE AGAIN ?
```

Esto es **una sola oración completa** ("What would you do if at the moment of death a voice from the darkness offered you a chance to live again?") repartida en 3 bloques de tiempo distintos. Si cortamos por bloque SRT, cada clip te daría 2-3 palabras sueltas — inútil para listening. Necesitamos **agrupar bloques consecutivos hasta encontrar puntuación de cierre** (`.`, `?`, `!`) y usar el timestamp de inicio del primer bloque + timestamp de fin del último bloque como el corte real.

Esto es un cambio de diseño razonable pero importante, así que antes de asumirlo del todo quiero confirmar el patrón con más contexto.

## Hallazgo 3: Etiquetas entre paréntesis en minúscula — ¿qué son exactamente?

`( daughter )`, `( male )`, `( wife )`, `( sirens )`, `( honking )` — mezclan dos cosas distintas:

- Unas parecen **etiquetas de hablante fuera de cámara** (`daughter`, `male`, `wife` — indican quién habla, típico en SDH).
- Otras son **efectos de sonido reales** (`sirens`, `honking`, `helicopter buzzing`, `telephone dialing`) — sin diálogo, hay que descartarlas.

Necesito ver cómo aparecen en el archivo real (¿en su propia línea, o antes del diálogo en la misma línea?) para saber si las quito por completo o solo la etiqueta dejando el diálogo. Corre esto:

```bash
grep -n -B1 -A2 '( sirens )\|( honking )\|( male )\|( daughter )' S01E01.srt
```

## Paso extra: confirmar que casi todo termina en puntuación de cierre

Para que el agrupamiento por oración funcione bien, quiero saber cuántos bloques _no_ terminan en `.`, `?`, `!`, `"` — eso nos dice si el criterio de agrupación es confiable en todo el episodio o si hay casos raros (créditos, interjecciones sueltas, etc.):

```bash
grep -v '\-\->' S01E01.srt | grep -v '^[0-9]*$' | grep -v '^$' | grep -vE '[.?!"]\s*$' | wc -l
```

```bash
grep -v '\-\->' S01E01.srt | grep -v '^[0-9]*$' | grep -v '^$' | grep -vE '[.?!"]\s*$' | head -20
```

Con estos tres resultados ya tenemos claro cómo estructurar el parser: normalización de mayúsculas, agrupamiento de oraciones multi-bloque, y filtro de efectos de sonido vs. etiquetas de hablante.

---

---

Ya tenemos todo lo necesario. Los tres hallazgos confirman el diseño:

## Diseño confirmado

**1. Agrupación por oración** — Confirmado: 366 de las líneas de texto no terminan en `.?!"`, es decir, la gran mayoría de bloques SRT son fragmentos de una oración más larga. Agruparemos bloques consecutivos hasta toparnos con puntuación de cierre, usando el timestamp de inicio del primer bloque del grupo y el timestamp de fin del último.

**2. Etiquetas entre paréntesis — regla simple sin necesidad de vocabulario**: Viendo los ejemplos, la regla no depende de si es "sirens" o "male" (no necesitamos una lista de palabras). Es puramente estructural:

- `( male ) LET HIM GO.` → quito la etiqueta, me quedo con `Let him go.`
- `( sirens )` seguido de bloque vacío → si **no queda texto** después de quitar la etiqueta, descarto el bloque completo (es un efecto de sonido puro).

Esto es robusto y no requiere mantener un diccionario de "sonidos vs. hablantes".

**3. Normalización de texto**: mayúsculas → sentence case, para que se vea como inglés natural en la tarjeta.

## Antes de cortar vídeo — un paso intermedio de seguridad

Como pediste empezar pequeño: en vez de ir directo a cortar 337 clips de vídeo, el primer script solo debe **parsear y agrupar el .srt**, mostrando en una tabla (o CSV) el resultado: número de línea, inicio, fin, duración, texto final. Así revisas que el agrupamiento de oraciones y el filtro de efectos de sonido funcionan bien **antes** de gastar tiempo/CPU cortando vídeo. Si algo se ve mal, lo ajustamos ahí, sin haber tocado ffmpeg todavía.

---

---

Se asume lo más simple — son fáciles de cambiar después:

- **Etiquetas de hablante** `(male)`, `(daughter)`: se descartan, dejamos solo el diálogo.
- **Filtrado por duración/longitud**: en este script de _preview_ no filtro nada todavía — quiero que veas la tabla completa primero y decidas visualmente qué tan agresivo conviene ser. Le agrego un flag opcional para que puedas experimentar sin tocar código.

## Probar rápidamente 📌🔥

Estructura básica

```text
.  
├── core  
│   ├── clip_engine.py  
│   └── subtitle_parser.py  
├── cut_clips.py  
├── data # Ruta que se añade a los scripts 
│   └── Spawn_S01  
│       ├── S01E01 # Añadir video original aquí! 
│       └── S01E02    
├── parse_srt_preview.py  
├── LICENSE  
└── README.md
```

### 1. Extraer los subtítulos y crear el archivo de previsualización

Abre una terminal en el directorio donde se encuentran los scripts y el archivo de vídeo.

Primero, selecciona el episodio que deseas procesar:

```bash
# Directorio raíz donde se almacenan los datos de la serie
SERIES_DIR="data/Spawn_S01"

# Identificador del episodio a procesar
EPISODE="S01E01"

# Ruta de la carpeta específica del episodio actual
EPISODE_DIR="$SERIES_DIR/$EPISODE"

# Buscar el archivo de vídeo del episodio y guardar su ruta exacta en una variable
VIDEO1=$(ls "$EPISODE_DIR"/Todd.McFarlanes.Spawn.${EPISODE}*.mkv)

# Ruta y nombre del archivo CSV de previsualización que se va a generar
CSV1="$EPISODE_DIR/${EPISODE}_preview.csv"

# Extraer la pista de subtítulos del archivo de vídeo (pista 0:2) a un archivo .srt
ffmpeg -i "$VIDEO1" -map 0:2 "$EPISODE_DIR/${EPISODE}.srt"

# Convertir el .srt a un archivo CSV para previsualización y ajustar los tiempos (-0.4s)
python3 parse_srt_preview.py "$EPISODE_DIR/${EPISODE}.srt" -o "$CSV1" --shift -0.4
```

El archivo `.csv` generado permite revisar los subtítulos antes de crear los clips definitivos.

Si algún subtítulo comienza o termina demasiado pronto o demasiado tarde, puedes modificar manualmente los tiempos en este archivo.

### 2. Generar clips de vídeo + audio

Paso 1: Cuenta y API key

1. Ve a https://www.deepl.com/pro-api y regístrate al plan **DeepL API Free** (tarjeta de crédito no es obligatoria para el plan free).
2. Una vez dentro, en tu cuenta encuentras la **API key** (termina en `:fx` para el plan free).

Paso 2: Instalar la librería

```bash
pip install deepl --break-system-packages
```

**No publiques tu API key en GitHub.** Utiliza una variable de entorno o un mecanismo seguro para almacenarla.

```bash
# DEEPL API: Clave de la API de DeepL para habilitar la traducción del texto
export DEEPL_API_KEY="YOUR_DEEPL_API_KEY"

# Generar los clips (vídeo y audio) e interactuar con la API de traducción
python3 cut_clips.py \
  --video "$VIDEO1" \
  --csv "$CSV1" \
  --series-name Todd_McFarlanes_Spawn_Anki_Video \
  --episode-label S01E01 \
  --output-dir "$EPISODE_DIR/output_files" \
  --tsv-out "$EPISODE_DIR/Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_anki.tsv" \
  --translation-cache "$SERIES_DIR/translations_cache.json" \
  --media both \
  --translate \
  --limit 5
```

El parámetro `--limit 5` permite realizar primero una prueba con un número reducido de clips.

Una vez comprobado que los clips se generan correctamente, aumenta el valor de `--limit` para continuar procesando el episodio.

☣️☢️ Importante 🔥☠️

Debes cambiar los nombres de los archivos descritos en las líneas a ejecutar, según estés trabajando.

### 3. Continuar la numeración en el siguiente episodio

Cuando termines de procesar un episodio, puedes obtener el ID del último clip generado:

```bash
# Obtener el ID del último clip generado
tail -n1 Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_anki.tsv | cut -f1

# Obtener el ID del último clip
LAST_ID=$(tail -n1 Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_anki.tsv | cut -f1)

# Calcular el siguiente ID
NEXT_START=$((10#$LAST_ID + 1))
echo "$NEXT_START"
```

```bash
# Obtener el ID del último clip generado
tail -n1 "$EPISODE_DIR/Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_anki.tsv" | cut -f1

# Obtener el ID del último clip
LAST_ID=$(tail -n1 "$EPISODE_DIR/Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_anki.tsv" | cut -f1)

# Calcular el siguiente ID
NEXT_START=$((10#$LAST_ID + 1))
echo "$NEXT_START"
```

> **Nota:** si este es el primer episodio que procesas, `--start-index` no es necesario.

### 4. Procesar el siguiente episodio

Por ejemplo, para procesar el episodio `S01E02`:

```bash
# Directorio raíz donde se almacenan los datos de la serie
SERIES_DIR="data/Spawn_S01"

# Identificador del episodio a procesar
EPISODE="S01E02"

# Ruta de la carpeta específica del episodio actual
EPISODE_DIR="$SERIES_DIR/$EPISODE"

# Buscar el archivo de vídeo del episodio y guardar su ruta exacta en una variable
VIDEO2=$(ls "$EPISODE_DIR"/Todd.McFarlanes.Spawn.${EPISODE}*.mkv)

# Ruta y nombre del archivo CSV de previsualización que se va a generar
CSV2="$EPISODE_DIR/${EPISODE}_preview.csv"

# Extraer la pista de subtítulos del archivo de vídeo (pista 0:2) a un archivo .srt
ffmpeg -i "$VIDEO2" -map 0:2 "$EPISODE_DIR/${EPISODE}.srt"

# Convertir el .srt a un archivo CSV para previsualización y ajustar los tiempos (-0.4s)
python3 parse_srt_preview.py "$EPISODE_DIR/${EPISODE}.srt" -o "$CSV2" --shift -0.4
```

Después, genera los clips:

```bash
python3 cut_clips.py \
  --video "$VIDEO2" \
  --csv "$CSV2" \
  --series-name Todd_McFarlanes_Spawn_Anki_Video \
  --episode-label S01E02 \
  --output-dir "$EPISODE_DIR/output_files" \
  --tsv-out "$EPISODE_DIR/Todd_McFarlanes_Spawn_Anki_Video_S01-Ep02_anki.tsv" \
  --translation-cache "$SERIES_DIR/translations_cache.json" \
  --start-index "$NEXT_START" \
  --media both \
  --translate \
  --limit 5
```

El parámetro `--start-index` permite continuar la numeración de los clips desde el episodio anterior.

### 5. Generar únicamente audio

Si solo necesitas los archivos de audio, utiliza `--media audio`:

```bash
python3 cut_clips.py \
  --video "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv" \
  --csv S01E01_preview.csv \
  --series-name Todd_McFarlanes_Spawn_Anki_Video \
  --episode-label S01-Ep01 \
  --media audio
  
  
python3 cut_clips.py \
  --video "$VIDEO1" \
  --csv "$CSV1" \
  --series-name Todd_McFarlanes_Spawn_Anki_Video \
  --episode-label S01E01 \
  --output-dir "$EPISODE_DIR/output_files" \
  --tsv-out "$EPISODE_DIR/Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_anki.tsv" \
  --translation-cache "$SERIES_DIR/translations_cache.json" \
  --media audio \
  --translate \
  --limit 5
```

### 6. Corregir un clip generado incorrectamente

Si algún clip no se generó correctamente:

1. Elimina el clip correspondiente de la carpeta `output_files`.
2. Abre el archivo `.csv`.
3. Corrige manualmente los tiempos o el texto.
4. Vuelve a ejecutar el comando de generación.

No es necesario volver a procesar los clips que ya son correctos.

⚠️ Importante: si editas el CSV a mano y después vuelves a correr `parse_srt_preview.py` sobre el mismo `.srt`, **tu edición se pierde** porque el CSV se regenera. Trátalo como intermedio, no como fuente definitiva — si haces varios ajustes finos que quieres conservar, cópialo a un nombre distinto (ej. `S01E01_preview_corregido.csv`) antes de tocar nada más.

### Estructura del proyecto después del procesamiento

Después de procesar un episodio, la estructura del directorio será similar a esta:

```text
.  
├── core  
│   ├── clip_engine.py  
│   ├── __pycache__  
│   │   ├── clip_engine.cpython-311.pyc  
│   │   └── subtitle_parser.cpython-311.pyc  
│   └── subtitle_parser.py  
├── cut_clips.py  
├── data  
│   └── Spawn_S01  
│       ├── S01E01  
│       │   ├── output_files  
│       │   │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01E01_Line_0001.mp3  
│       │   │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01E01_Line_0001.webm  
│       │   │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01E01_Line_0002.mp3  
│       │   │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01E01_Line_0002.webm  
│       │   │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01E01_Line_0003.mp3  
│       │   │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01E01_Line_0003.webm  
│       │   │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01E01_Line_0004.mp3  
│       │   │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01E01_Line_0004.webm  
│       │   │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01E01_Line_0005.mp3  
│       │   │   └── Todd_McFarlanes_Spawn_Anki_Video_S01E01_Line_0005.webm  
│       │   ├── S01E01_preview.csv  
│       │   ├── S01E01.srt  
│       │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_anki.tsv  
│       │   └── Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv  
│       ├── S01E02  
│       │   ├── output_files  
│       │   │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01E02_Line_0006.mp3  
│       │   │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01E02_Line_0006.webm  
│       │   │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01E02_Line_0007.mp3  
│       │   │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01E02_Line_0007.webm  
│       │   │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01E02_Line_0008.mp3  
│       │   │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01E02_Line_0008.webm  
│       │   │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01E02_Line_0009.mp3  
│       │   │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01E02_Line_0009.webm  
│       │   │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01E02_Line_0010.mp3  
│       │   │   └── Todd_McFarlanes_Spawn_Anki_Video_S01E02_Line_0010.webm  
│       │   ├── S01E02_preview.csv  
│       │   ├── S01E02.srt  
│       │   ├── Todd_McFarlanes_Spawn_Anki_Video_S01-Ep02_anki.tsv  
│       │   └── Todd.McFarlanes.Spawn.S01E02.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv  
│       └── translations_cache.json  
├── parse_srt_preview.py  
├── LICENSE  
└── README.md
```

## Flujo de trabajo

1. `ffprobe` sobre el episodio para confirmar índices de pistas (ya no hace falta repetir esto salvo que cambie el release/fuente).
2. Extraer subtítulos: `ffmpeg -i episodio.mkv -map 0:2 episodio.srt`
3. Generar preview: `python3 parse_srt_preview.py episodio.srt -o episodio_preview.csv`
4. Revisar el CSV, ajustar tiempos si hace falta (ver arriba).
5. Cortar clips de prueba: `python3 cut_clips.py --video ... --csv ... --series-name ... --episode-label ... --padding 0 --limit 5`
6. Revisar los 5 clips (audio/tamaño).
7. Si todo bien, correr sin `--limit` para el episodio completo.

En resumen, el flujo de trabajo es:

```text
Video (.mkv)
     │
     ▼
Subtítulos (.srt)
     │
     ▼
Previsualización y corrección
     │
     ▼
CSV (.csv)
     │
     ├──────────────► Traducción DeepL
     │
     ▼
Corte de clips
     │
     ├──► Vídeo (.webm)
     └──► Audio
     │
     ▼
TSV para Anki
```

- `parse_srt_preview.py` — SRT → CSV con oraciones agrupadas.
- `cut_clips.py` — CSV + vídeo → clips `.webm` + `.tsv`.
- Resolución 640x480, CRF 32 (VP9), audio Opus 96kbps.

El archivo TSV generado contiene la información necesaria para importar los clips y textos en Anki.

### Sobre la caché

Se crea un archivo `Todd_McFarlanes_Spawn_Anki_Video_translations_cache.json` junto a tus scripts. Si corres el comando de nuevo (por ejemplo, para procesar el episodio completo después de haber probado con 5 líneas), **no vuelve a gastar cuota** en las líneas que ya tradujo — solo traduce las líneas nuevas. Puedes reutilizar esta misma caché entre episodios distintos si compartes el mismo `--series-name`, ya que probablemente algunas frases se repitan en la serie.

---
---



Si el script tiene `--overwrite \` quítalo si no quieres que vuelva a trabajar en clips ya hechos.
Simplemente quita `--overwrite` cuando quieras el comportamiento de "solo generar lo que falta":


---

---

### Tareas pendientes

copiar ultimo codigo y probarlo


1. Colocar nombre del capitulo en el tsv para visualizarlo en anki. Se pueda encontrar usando este comando pero si no tiene ese dato dejar la columna del tsv en blanco o darme alternativas.

```bash
ffprobe -v error -show_entries format_tags=title -of default=noprint_wrappers=1:nokey=1 "data/Spawn_S01/S01E01/Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv"
```

2. Para empezar a trabajar con la serie spawn primero debí analizar la data interna de los mkv, pero eso es un analizis manual previo antes de empezar a cortar. Ahora, como deberiamos hacer para integrar esto y estandarizar este analisis sin tener que hacerlo manualmente para que funcione con otras clases de idiomas, subtitulos y variantes que quizá no estoy tomando en cuenta? recordemos que haciamos:

ffprobe -v error -show_entries stream=index,codec_type,codec_name,codec_tag_string:stream_tags=language,title -of default=noprint_wrappers=0 "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv"

ffprobe -v error -print_format json -show_format -show_streams "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv" > episodio_info.json

ffmpeg -i "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv" -map 0:2 S01E01.srt

grep -E '\[.*\]|\(.*\)' S01E01.srt | sort -u | head -40

grep -c '\-\->' S01E01.srt

grep -n -B1 -A2 '( sirens )\|( honking )\|( male )\|( daughter )' S01E01.srt

grep -v '\-\->' S01E01.srt | grep -v '^[0-9]*$' | grep -v '^$' | grep -vE '[.?!"]\s*$' | wc -l

grep -v '\-\->' S01E01.srt | grep -v '^[0-9]*$' | grep -v '^$' | grep -vE '[.?!"]\s*$' | head -20









