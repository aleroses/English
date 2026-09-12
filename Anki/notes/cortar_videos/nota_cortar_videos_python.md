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

**Corre los pasos 1 y 2 (y si quieres el 4) y pégame aquí la salida.** Con eso sabemos exactamente:

- Qué índice de pista usar para audio en inglés y subtítulos en inglés.
- Si necesitamos un paso de OCR extra o podemos ir directo al parseo del SRT.

---

---

Excelente, tenemos toda la información que necesitábamos. Resumen de lo que confirmamos:

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

Muy útil. Ya vemos dos cosas importantes que cambian el diseño del parser, antes de seguir:

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

Antes de escribir ese script, dos decisiones rápidas de tu parte:

---

---

Perfecto. Como no me confirmaste las dos preguntas puntuales, voy a asumir lo más simple y te aviso — son fáciles de cambiar después:

- **Etiquetas de hablante** `(male)`, `(daughter)`: se descartan, dejamos solo el diálogo.
- **Filtrado por duración/longitud**: en este script de _preview_ no filtro nada todavía — quiero que veas la tabla completa primero y decidas visualmente qué tan agresivo conviene ser. Le agrego un flag opcional para que puedas experimentar sin tocar código.

## Cómo probarlo 📌🔥

```bash
python3 parse_srt_preview.py S01E01.srt -o S01E01_preview.csv
```

No requiere librerías externas — solo Python 3 estándar. Te va a imprimir un resumen así:

```
Bloques SRT leídos:              388
Bloques descartados (sin texto): N   (solo efectos de sonido)
Oraciones agrupadas:             M
Oraciones finales en CSV:        M

CSV generado: S01E01_preview.csv
```

## Qué revisar en el CSV resultante

1. **¿Las oraciones quedan completas y con sentido?** (no cortadas a la mitad, no dos oraciones distintas pegadas por error).
2. **¿Los timestamps de inicio/fin corresponden bien** a lo que dirías al escuchar ese fragmento en el vídeo?
3. **¿Quedó algún residuo raro** de las etiquetas `(male)`/`(sirens)` sin limpiar del todo?
4. **¿La normalización de mayúsculas se ve razonable?** Ojo: nombres propios como "Todd McFarlane" van a aparecer en minúscula salvo que empiecen oración — es una limitación conocida del MVP, la podemos mejorar después con una lista de excepciones si te molesta.
5. Abre el CSV en LibreOffice Calc o con `column -s, -t S01E01_preview.csv | less -S` en terminal para verlo cómodo.

Si algo se ve mal (oraciones mal agrupadas, texto residual, etc.), pégame unas líneas del CSV y lo ajustamos aquí antes de pasar al corte de vídeo con ffmpeg.

---

---

Buen ojo — es el típico "espacio antes de puntuación" del estilo de subtitulado británico/SDH. Lo arreglo quitando espacios antes de `. , ! ? ; :`.Corre de nuevo el mismo comando y confirma que "Mr. Stevens?" y "Oh god!" ya quedan pegados correctamente:

```bash
python3 parse_srt_preview.py S01E01.srt -o S01E01_preview.csv
```

## Ahora sí, el siguiente paso: cortar vídeo

Con el parser validado, toca escribir el script que:

1. Lee el CSV de preview (o re-parsea el .srt directamente — a decidir).
2. Para cada oración, corta un clip de vídeo+audio con ffmpeg usando `start`/`end` + un pequeño padding.
3. Extrae también el audio equivalente si decides usar audio solo en vez de vídeo, aunque tu caso pide vídeo recortado.
4. Nombra cada clip según tu convención (`..._Line_0001.webm`).
5. Genera el `.tsv` final con el formato de Anki.
6. Todo esto **solo para S01E01** por ahora — probamos un episodio, revisamos tamaño/calidad, y si todo bien generalizamos a los 18.

Antes de escribir ese script necesito confirmar contigo los parámetros de corte y codificación, para no tener que rehacer 337 clips si algo no te convence:

---

---

Con eso ya tengo todo para el script de corte. Dos decisiones de diseño que agrego por mi cuenta, te las explico:

- **Padding con "clamp" a la línea vecina**: si aplico 250ms de margen y la oración anterior/siguiente está muy cerca en el tiempo, el padding podría "morder" el diálogo de la línea vecina. El script recorta automáticamente el padding para nunca pasarse del final de la línea previa ni del inicio de la siguiente.
- **Modo de prueba (`--limit`)**: para no esperar a que se corten 337 clips solo para revisar 5, el script permite limitar cuántas líneas procesa en esta primera corrida.

## Prueba rápida — solo 5 clips primero 📌🔥

```bash
python3 cut_clips.py \
  --video "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv" \
  --csv S01E01_preview.csv \
  --series-name Todd_McFarlanes_Spawn_Anki_Video \
  --episode-label S01-Ep01 \
  --limit 5
```

Esto te genera 5 clips en `output_files/` y el `.tsv` correspondiente. Revisa:

1. **Abre 2-3 clips** en cualquier reproductor (mpv, vlc) — ¿se ve bien el corte? ¿el audio no está trunco al inicio/final?
2. **Tamaño de cada clip** (`ls -lh output_files/`) — con 480p + CRF 32 deberían quedar razonablemente livianos, pero lo confirmamos con datos reales tuyos.
3. **El `.tsv`** — ábrelo con `cat` o `column -t -s$'\t'` y compara contra tu formato de ejemplo.

Si todo se ve bien, corres el mismo comando sin `--limit` para procesar el episodio completo (412 líneas → ~337 esperadas tras descartar efectos de sonido, según tu ejemplo original).

Avísame qué tal salen esos 5 clips de prueba — tamaño en MB y si el corte/audio se sienten bien — y seguimos con el paso 3: automatizar los 18 episodios y armar el `.zip` final.

---

---

## Traducciones

Con DeepL vas a tener muy buena calidad, y tiene un plan gratuito generoso (500,000 caracteres/mes — de sobra para toda la serie). Vamos a integrarlo en `cut_clips.py`, ya que es el que escribe el `.tsv`, y aprovechamos exactamente ese segundo campo vacío que ya habíamos dejado preparado desde el principio.

### Paso 1: Cuenta y API key

1. Ve a https://www.deepl.com/pro-api y regístrate al plan **DeepL API Free** (tarjeta de crédito no es obligatoria para el plan free, pero puede pedírtela para verificación — no te van a cobrar mientras te quedes dentro del límite gratuito).
2. Una vez dentro, en tu cuenta encuentras la **API key** (termina en `:fx` para el plan free).

### Paso 2: Instalar la librería

```bash
pip install deepl --break-system-packages
```

### Paso 3: Modificar `cut_clips.py`

Agrego traducción automática con **caché local** (para no volver a traducir líneas que ya tradujiste antes, aunque re-ejecutes el script varias veces mientras pruebas):Ahora integro la traducción justo antes de escribir el `.tsv`, en el campo que hasta ahora estaba vacío:

### Cómo usarlo

**Recomendado — la API key como variable de entorno**, para que no quede guardada en el historial de tu terminal (`history`):

```bash
export DEEPL_API_KEY="tu-api-key-aqui"

python3 cut_clips.py \
  --video "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv" \
  --csv S01E01_preview.csv \
  --series-name Todd_McFarlanes_Spawn_Anki_Video \
  --episode-label S01-Ep01 \
  --translate \
  --limit 5
```

Con esto, el `.tsv` te va a quedar así:

```
0001 What would you do if at the moment of death a voice from the darkness offered you a chance to live again?	¿Qué harías si en el momento de la muerte una voz desde la oscuridad te ofreciera la oportunidad de vivir de nuevo?	[sound:..._Line_0001.webm]
```

### Sobre la caché

Se crea un archivo `Todd_McFarlanes_Spawn_Anki_Video_translations_cache.json` junto a tus scripts. Si corres el comando de nuevo (por ejemplo, para procesar el episodio completo después de haber probado con 5 líneas), **no vuelve a gastar cuota** en las líneas que ya tradujo — solo traduce las líneas nuevas. Puedes reutilizar esta misma caché entre episodios distintos si compartes el mismo `--series-name`, ya que probablemente algunas frases se repitan en la serie.

### Un detalle a vigilar

En tu línea 7 vi que quedó una etiqueta `<I>malebolgia,</I>` mezclada en el texto (residuo del subtítulo original en cursiva). DeepL debería traducir igual el contenido, pero puede que la etiqueta quede rara en medio de la traducción. Si ves varias líneas con `<I>`/`</I>` sueltas, dímelo y agrego un paso de limpieza en `parse_srt_preview.py` para quitarlas antes de generar el CSV — se me pasó por alto ese caso al diseñar `clean_text()`.

## Resumen para retomar otro día

**Archivos que ya tienes:**

- `parse_srt_preview.py` — SRT → CSV con oraciones agrupadas.
- `cut_clips.py` — CSV + vídeo → clips `.webm` + `.tsv`.

**Parámetros ya decididos (para no tener que repensarlos):**

- Etiquetas de hablante `(male)`, `(daughter)`, etc. → se descartan, solo queda el diálogo.
- Sin filtro de duración/palabras mínimas todavía (`--min-duration 0 --min-words 0`).
- Resolución 640x480, CRF 32 (VP9), audio Opus 96kbps.
- Padding a definir según lo que confirmes con `--padding 0` — pendiente tu resultado final.

**Flujo paso a paso:**

1. `ffprobe` sobre el episodio para confirmar índices de pistas (ya no hace falta repetir esto salvo que cambie el release/fuente).
2. Extraer subtítulos: `ffmpeg -i episodio.mkv -map 0:2 episodio.srt`
3. Generar preview: `python3 parse_srt_preview.py episodio.srt -o episodio_preview.csv`
4. Revisar el CSV, ajustar tiempos si hace falta (ver arriba).
5. Cortar clips de prueba: `python3 cut_clips.py --video ... --csv ... --series-name ... --episode-label ... --padding 0 --limit 5`
6. Revisar los 5 clips (audio/tamaño).
7. Si todo bien, correr sin `--limit` para el episodio completo.

**Lo que falta por construir (próxima sesión):**

- Automatizar los pasos 1-7 para los 18 episodios de una sola corrida (el `--input ./Spawn` que mostraste en tu ejemplo original).
- Consolidar los 18 `.tsv` (o dejarlos separados, a decidir).
- Empaquetar todo en el `.zip` final con la estructura que definiste.
- Mostrar el resumen de progreso en pantalla (barra de progreso, contador de generados/omitidos/errores) ya replicado por episodio — falta el nivel "por serie".

Cuando confirmes el resultado con `--padding 0`, seguimos con la automatización completa.

## Dónde ajustar los tiempos: depende del tipo de ajuste

- **Ajuste puntual en 1-2 líneas** (una oración específica quedó mal cortada) → edítalo directo en el **CSV** (`S01E01_preview.csv`). Es texto plano, abres con LibreOffice Calc o `nano`/`vim`, cambias `start`/`end` en formato `HH:MM:SS.mmm`, guardas, y corres `cut_clips.py` de nuevo apuntando a ese CSV. Es el input directo del script de corte, así que es el lugar más rápido para probar.

- **El .srt completo está desfasado** (todas las líneas corridas por el mismo offset, típico si mezclaste subtítulo de otro release) → corrígelo en el **.srt** con algún editor de subtítulos (Subtitle Edit, Aegisub) o herramienta CLI, y luego vuelve a correr `parse_srt_preview.py` para regenerar el CSV desde cero.

⚠️ Importante: si editas el CSV a mano y después vuelves a correr `parse_srt_preview.py` sobre el mismo `.srt`, **tu edición se pierde** porque el CSV se regenera. Trátalo como intermedio, no como fuente definitiva — si haces varios ajustes finos que quieres conservar, cópialo a un nombre distinto (ej. `S01E01_preview_corregido.csv`) antes de tocar nada más.

---

---

Dos formas de retomarlo, según cuánto tiempo pase:

## Opción A — Misma conversación (recomendado si es pronto)

Si vuelves en los próximos días y esta conversación sigue disponible en tu historial de Claude, simplemente continúa aquí mismo escribiendo algo como "Ya probé con `--padding 0`, esto es lo que encontré..." — tengo todo el contexto (los dos scripts, las decisiones tomadas, el hallazgo del SDH, etc.) y no hace falta repetir nada.

## Opción B — Conversación nueva (si pasa mucho tiempo o cambias de dispositivo)

Aquí sí conviene un prompt que resuma el estado, porque una conversación nueva no tiene memoria de esta. Te dejo uno listo para copiar y ajustar con tus resultados:

```
Continúo un proyecto que empecé en otra conversación con Claude: generar clips
de vídeo cortados por oración desde episodios de una serie (Spawn, S01-S03,
archivos .mkv en Debian 12), para estudiar listening en Anki.

Ya tengo:
- Confirmado que los .mkv traen 1 pista de vídeo (h264, 1440x1080, DAR 4:3),
  1 pista de audio (AC3 estéreo) y 1 pista de subtítulos SDH en texto plano
  (subrip), todo en inglés, sin necesidad de OCR.
- parse_srt_preview.py: extrae el .srt, agrupa fragmentos de subtítulo en
  oraciones completas (usando puntuación de cierre), descarta bloques que son
  solo efectos de sonido tipo "(sirens)"/"(honking)", quita etiquetas de
  hablante tipo "(male)"/"(daughter)" dejando solo el diálogo, normaliza el
  texto de MAYÚSCULAS a sentence case, y corrige espacios sueltos antes de
  puntuación. Genera un CSV de preview con columnas: line_number, start, end,
  duration_sec, text.
- cut_clips.py: toma ese CSV + el .mkv original, corta un clip .webm por
  oración con ffmpeg (640x480, VP9 CRF 32, audio Opus 96k), con padding
  configurable que se recorta automáticamente para no invadir la línea vecina,
  y genera el .tsv final para Anki con formato:
  texto\t\t[sound:nombre_archivo.webm]
- Adjunto ambos scripts.

Último resultado probado: [pega aquí tus resultados con --padding 0: si quedó
bien, mal, qué ajustaste, tamaño de los clips de prueba, etc.]

Lo que falta:
- Confirmar el padding final para S01E01 completo (no solo 5 líneas de prueba).
- Automatizar todo el flujo para los 18 episodios (S01-S03) en una sola
  corrida de un script tipo:
  python3 generate_anki_video.py --input ./Spawn
- Consolidar/organizar los .tsv por episodio.
- Empaquetar todo en un .zip final con esta estructura:
  Todd_McFarlanes_Spawn_Anki_Video_package_S01-S03.zip
    ├── Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_anki.tsv
    └── output_files/
        └── Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_Line_0001.webm

Ayúdame a seguir desde aquí.
```

**Importante**: en la conversación nueva tendrías que **adjuntar** `parse_srt_preview.py` y `cut_clips.py` (los que ya generamos aquí), porque Claude no puede verlos si no se los subes de nuevo.

Mi sugerencia honesta: si puedes, sigue en esta misma conversación — es más simple y evitas tener que resumir nada.

---

---

## Ejecutar rápidamente

Crear el archivo `S01E01.srt`, en base a este se crea el archivo `S01E01_preview.csv` para editar y corregir manualmente.

```bash
ffmpeg -i "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv" -map 0:2 S01E01.srt

python3 parse_srt_preview.py S01E01.srt -o S01E01_preview.csv --shift -0.4
```

Sin traducción: 

```bash
python3 cut_clips.py \
  --video "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv" \
  --csv S01E01_preview.csv \
  --series-name Todd_McFarlanes_Spawn_Anki_Video \
  --episode-label S01-Ep01 \
  --padding 0 \
  --limit 25
```

Con traducción:

```bash
export DEEPL_API_KEY="lolcat31942:fx"

python3 cut_clips.py \
  --video "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv" \
  --csv S01E01_preview.csv \
  --series-name Todd_McFarlanes_Spawn_Anki_Video \
  --episode-label S01-Ep01 \
  --translate \
  --limit 5
```

No usar:

```bash
ffmpeg -i "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv" -map 0:2 S01E01.srt

python3 parse_srt_preview.py S01E01.srt -o S01E01_preview.csv --shift -0.4

python3 cut_clips.py \
  --video "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv" \
  --csv S01E01_preview.csv \
  --series-name Todd_McFarlanes_Spawn_Anki_Video \
  --episode-label S01-Ep01 \
  --overwrite \
  --limit 5
```

Estructura de la carpeta donde se está trabajando:

```bash
               Todd.McFarlanes.Spawn.S01.1080p.HMAX.WEBRip.DD2.0.x264-SLiGNOME
ale ❯ tree -L 4
.
├── cut_clips.py
├── episodio_info.json
├── output_files
│   ├── Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_Line_0001.webm
│   ├── Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_Line_0002.webm
│   ├── Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_Line_0003.webm
│   ├── Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_Line_.....webm
│   ├── Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_Line_.....webm
│   ├── Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_Line_0048.webm
│   ├── Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_Line_0049.webm
│   └── Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_Line_0050.webm
├── parse_srt_preview.py
├── S01E01_preview.csv
├── S01E01.srt
├── Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_anki.tsv
├── Todd_McFarlanes_Spawn_Anki_Video_translations_cache.json
├── Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv
├── Todd.McFarlanes.Spawn.S01E02.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv
├── Todd.McFarlanes.Spawn.S01E03.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv
├── Todd.McFarlanes.Spawn.S01E04.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv
├── Todd.McFarlanes.Spawn.S01E05.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv
└── Todd.McFarlanes.Spawn.S01E06.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv

2 directories, 63 files
```

Si algún video no se cortó bien, elimínalo de la carpeta `output_files` y vuelve a ejecutar el comando:

```bash
export DEEPL_API_KEY="lolcat39842:fx"

python3 cut_clips.py \
  --video "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv" \
  --csv S01E01_preview.csv \
  --series-name Todd_McFarlanes_Spawn_Anki_Video \
  --episode-label S01-Ep01 \
  --translate \
  --limit 5
```

---

---

Video + Audio

```bash
export DEEPL_API_KEY="4b40ef06-f2e0-4507-80bb-bed8ee506a08:fx"

python3 cut_clips.py \
  --video "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv" \
  --csv S01E01_preview.csv \
  --series-name Todd_McFarlanes_Spawn_Anki_Video \
  --episode-label S01-Ep01 \
  --media both \
  --translate \
  --overwrite \👈🏼👀
  --limit 5
```

Audio

```bash
python3 cut_clips.py \
  --video "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv" \
  --csv S01E01_preview.csv \
  --series-name Todd_McFarlanes_Spawn_Anki_Video \
  --episode-label S01-Ep01 \
  --media audio
```


Si el script tiene `--overwrite \` quítalo si no quieres que vuelva a trabajar en clips ya hechos.
Simplemente quita `--overwrite` cuando quieras el comportamiento de "solo generar lo que falta":



