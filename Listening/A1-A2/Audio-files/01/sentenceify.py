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

