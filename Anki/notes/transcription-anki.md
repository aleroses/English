# Crear tarjetas de transcripción

[Mi NUEVA forma favorita de usar Anki - Cómo hacer tarjetas de transcripción](https://youtu.be/8RYJok5Ma0Y)

## Teniendo un deck existente

Para este ejemplo tenemos un deck que se creó para estudiar vocabulario, el cual incluye audios, lo que nos servirá para crear otro deck que solo tenga audios los cuales debemos transcribir.

1. Importar un mazo que tenga audios (Refold EN1K)
2. Seleccionar el deck a modificar
3. Browse y seleccionar todo `Ctrl + A`
4. Clic derecho sobre lo seleccionado
5. Notes y Change Note Type
6. Seleccionar Transcription Cards
7. Dejar estas opciones de la siguiente manera
	
	Fields
	
	|Current          |New                  |
	|-----------------|---------------------|
	|Example Sentence |Example Sentence     |
	|Translation      |Sentence Translation |
	|sentence_audio   |sentence_audio       |
	|Image (optional) |Image                |
	
	Templates
	
	|Current     |New                   |
	|------------|----------------------|
	|Refold EN1K |SentenceTranscription |
	
	Save

8. ⚙️ Cambiar nombre: Refold EN1K Transcription
9. ⚙️ Options: Transcription Cards (Save)

## Teniendo un video mp3

En este ejemplo crearemos tarjetas con audios teniendo como fuente un `audio.mp3` y sus `subtitulos.srt` el cual debemos descargar de cualquier fuente.

Descarga el código Python que hará la magia.

> Nota: Este script de Python solo funciona con archivos mp3 y srt.

[Transcription Anki Decks Downloadable Resources](https://zenith-raincoat-5cf.notion.site/Transcription-Anki-Decks-Downloadable-Resources-1314fa7e6fbd80a9ac06eb465a7d46b7)

`notranslatesentenceify.py`

```py
import os
import pysrt
import csv
import subprocess
import random

# Prompt the user for input file paths
srt_file = input("Enter the path to the SRT file: ")
audio_file = input("Enter the path to the MP3 file: ")
output_dir = 'output_files'  # Directory where you want to save individual MP3s

# Ensure output directory exists
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Extract the base name of the audio file (without extension)
audio_base_name = os.path.splitext(os.path.basename(audio_file))[0]

# Generate a random 6-digit code for this audio file
random_code = '{:06d}'.format(random.randint(0, 999999))

# Parse the SRT file
subs = pysrt.open(srt_file)

# Create a unique TSV filename
tsv_file = f'{audio_base_name}_{random_code}_output_sentences.tsv'
with open(tsv_file, 'w', newline='', encoding='utf-8') as tsvfile:
    tsvwriter = csv.writer(tsvfile, delimiter='\t')
    tsvwriter.writerow(['Filename', 'AudioTag', 'Sentence'])

    # Iterate over each subtitle entry
    for i, sub in enumerate(subs):
        start_time = sub.start.ordinal / 1000.0  # Convert to seconds (from milliseconds)
        duration = (sub.end.ordinal - sub.start.ordinal) / 1000.0  # Duration in seconds

        # Extend the duration by X seconds
        duration += 0.3

        # Define the output MP3 filename with the required format
        output_filename = f'{audio_base_name}_Line_{i+1}_{random_code}.mp3'
        output_mp3 = os.path.join(output_dir, output_filename)

        # Use ffmpeg to extract the specific audio segment, re-encoding it
        ffmpeg_command = [
            'ffmpeg', '-i', audio_file, '-ss', str(start_time), '-t', str(duration),
            '-acodec', 'mp3', output_mp3, '-y'  # Re-encode to MP3 format
        ]
        subprocess.run(ffmpeg_command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

        # Prepare the audio tag
        audio_tag = f'[sound:{output_filename}]'

        # Get the original sentence
        sentence = sub.text
        sentence = sub.text.replace('\n', ' ')

        # Write the data to the TSV file
        tsvwriter.writerow([output_filename, audio_tag, sentence])

print("Process completed! Check the output directory and TSV file.")
```

`sentenceify.py`

```py
import os
import pysrt
import csv
import subprocess
import random
import openai

# Prompt the user for input file paths
srt_file = input("Enter the path to the SRT file: ")
audio_file = input("Enter the path to the MP3 file: ")
output_dir = 'output_files'  # Directory where you want to save individual MP3s

# Ensure output directory exists
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Extract the base name of the audio file (without extension)
audio_base_name = os.path.splitext(os.path.basename(audio_file))[0]

# Generate a random 6-digit code for this audio file
random_code = '{:06d}'.format(random.randint(0, 999999))

# Read OpenAI API key from 'api_key.txt'
with open('api_key.txt', 'r') as f:
    api_key = f.read().strip()

# Parse the SRT file
subs = pysrt.open(srt_file)

# Create a unique TSV filename
tsv_file = f'{audio_base_name}_{random_code}_output_sentences.tsv'
with open(tsv_file, 'w', newline='', encoding='utf-8') as tsvfile:
    tsvwriter = csv.writer(tsvfile, delimiter='\t')
    tsvwriter.writerow(['Filename', 'AudioTag', 'Sentence', 'Translation'])

    # Iterate over each subtitle entry
    for i, sub in enumerate(subs):
        start_time = sub.start.ordinal / 1000.0  # Convert to seconds (from milliseconds)
        duration = (sub.end.ordinal - sub.start.ordinal) / 1000.0  # Duration in seconds

        # Extend the duration by X seconds
        duration += 0.3

        # Define the output MP3 filename with the required format
        output_filename = f'{audio_base_name}_Line_{i+1}_{random_code}.mp3'
        output_mp3 = os.path.join(output_dir, output_filename)

        # Use ffmpeg to extract the specific audio segment, re-encoding it
        ffmpeg_command = [
            'ffmpeg', '-i', audio_file, '-ss', str(start_time), '-t', str(duration),
            '-acodec', 'mp3', output_mp3, '-y'  # Re-encode to MP3 format
        ]
        subprocess.run(ffmpeg_command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

        # Prepare the audio tag
        audio_tag = f'[sound:{output_filename}]'

        # Get the original sentence
        sentence = sub.text
        sentence = sub.text.replace('\n', ' ')

        # Translate the sentence into English using OpenAI API
        prompt = f"Translate the following text into English:\n\n{sentence}"
        client = openai.OpenAI(api_key=api_key)

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a translator that translates any given text into English."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.5
            )
            translation = response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error translating sentence {i+1}: {e}")
            translation = "Translation error."

        # Write the data to the TSV file
        tsvwriter.writerow([output_filename, audio_tag, sentence, translation])

print("Process completed! Check the output directory and TSV file.")
```

En la web del enlace haz clic sobre los archivos y luego clic derecho en  `Save Page As`. Este código se encargará de cortar el audio en pequeños fragmentos.

1. Renombra el archivo.mp3 por algo simple y que te haga sentido
	- ankitutorial.mp3
2. Clic derecho dentro de la carpeta que contiene tu mp3 y los scripts
3. Open in terminal
4. Escribe: python3 notranslatesentenceify.py 
	- Para autocompletar el nombre del archivo solo escribe las primeras letras y luego presiona tabulador.
5. Enter
6. Ahora te pide la ruta del .srt
	- En linux solo copia el archivo `ankitutorial.srt` y dentro de la terminal
	- Clic derecho pegar, eso añade la ruta
7. Ahora te pide la ruta del .mp3
	- En linux tambien puedes arrastrar el archivo dentro de la terminal y esto copiará la ruta
8. Enter
9. Esto crea una carpeta llamada `output_files`

Si quieres ajustar que tanto se corta el audio puedes probar cambiando esto, dentro del código:

`notranslatesentenceify.py`

```py
        # Extend the duration by X seconds
        duration += 0.1 👈🏼👀
```

Esto es útil si los subtítulso no están perfectamente alineados.

> Nota: Para este ejemplo se usa `notranslatesentenceify.py`, ya que el otro necesita una API_KEY de OpenIA que es de paga. En caso de querer traducciones usa el de paga.

Si usaste `sentenceify.py` puedes cambiar el idioma:

`sentenceify.py`

```py
        # Translate the sentence into English using OpenAI API
        prompt = f"Translate the following text into English👈🏼👀:\n\n{sentence}" 
```

10. Crea un nuevo mazo
	- Create Deck: Ale's Video Transcription Deck
11. ⚙️ Options
12. Transcription Cards
13. Save
14. Abre la ubicación de los archivos que usa Anki
	- En mi caso: `/home/ale/.local/share/Anki2/User 1/collection.media/`
15. Copia o Corta el contenido de `output_files`
16. Pégalo dentro de la ubicación anterior
17. Importa el archivo .tsv que se generó
18. Import file
	- Busca el archivo `ankitutorial_472539_output_sentences.tsv`
	- El nombre cambia según lo que le pusiste
19. Allow HTML infiles: Activalo

Import options

|Notetype |Transcription Cards|
|--------------|--------------|
|Notetype|Transcription Cards|
|Deck |Ale's Video Transcription Deck|
|Existing notes |Update |
|Match scope |Notetype|

Field mapping

|Example Sentence     |3: Sentence   |
|---------------------|--------------|
|Sentence Translation |(Nothing)     |
|sentence_audio       |2: AudioTag   |
|Image                |(Nothing)     |
|Tags                 |(Nothing)     |

20. Import

⚙️