#!/usr/bin/env python3
"""
cut_clips.py

Paso 2 del pipeline Anki-Video: toma el CSV generado por parse_srt_preview.py
y el archivo de vídeo original, corta un clip por cada oración (con padding
de seguridad) y genera el .tsv final listo para importar en Anki.

Uso (prueba rápida, solo 5 líneas):
    python3 cut_clips.py \
        --video "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv" \
        --csv S01E01_preview.csv \
        --series-name Todd_McFarlanes_Spawn_Anki_Video \
        --episode-label S01-Ep01 \
        --limit 5

Uso completo (todo el episodio):
    python3 cut_clips.py \
        --video "Todd.McFarlanes.Spawn.S01E01.1080p.HMAX.WEB-DL.DD2.0.H.264-SLiGNOME.mkv" \
        --csv S01E01_preview.csv \
        --series-name Todd_McFarlanes_Spawn_Anki_Video \
        --episode-label S01-Ep01

Salida:
    output_files/Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_Line_0001.webm ...
    Todd_McFarlanes_Spawn_Anki_Video_S01-Ep01_anki.tsv
"""

import argparse
import csv
import subprocess
import sys
import os


def parse_timestamp(ts):
    """'HH:MM:SS.mmm' -> segundos (float)."""
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def load_sentences(csv_path):
    sentences = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sentences.append({
                "start": parse_timestamp(row["start"]),
                "end": parse_timestamp(row["end"]),
                "text": row["text"],
            })
    return sentences


def compute_padded_windows(sentences, padding):
    """Aplica padding pero sin invadir el espacio de la línea vecina."""
    n = len(sentences)
    windows = []
    for i, s in enumerate(sentences):
        prev_end = sentences[i - 1]["end"] if i > 0 else None
        next_start = sentences[i + 1]["start"] if i < n - 1 else None

        padded_start = s["start"] - padding
        if padded_start < 0:
            padded_start = 0.0
        if prev_end is not None:
            padded_start = max(padded_start, prev_end)

        padded_end = s["end"] + padding
        if next_start is not None:
            padded_end = min(padded_end, next_start)

        windows.append((padded_start, padded_end))
    return windows


def run_ffmpeg_cut(video_path, start, duration, output_path, width, height, crf, audio_bitrate):
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-i", video_path,
        "-t", f"{duration:.3f}",
        "-map", "0:v:0",
        "-map", "0:a:0",
        "-vf", f"scale={width}:{height}",
        "-c:v", "libvpx-vp9",
        "-crf", str(crf),
        "-b:v", "0",
        "-deadline", "good",
        "-cpu-used", "3",
        "-c:a", "libopus",
        "-b:a", audio_bitrate,
        "-loglevel", "error",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def print_progress(current, total, bar_len=30):
    filled = int(bar_len * current / total)
    bar = "█" * filled + "░" * (bar_len - filled)
    pct = int(100 * current / total)
    sys.stdout.write(f"\r  [{bar}] {pct}%")
    sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, help="Ruta al .mkv original")
    parser.add_argument("--csv", required=True, help="CSV generado por parse_srt_preview.py")
    parser.add_argument("--series-name", required=True,
                         help="Ej: Todd_McFarlanes_Spawn_Anki_Video")
    parser.add_argument("--episode-label", required=True,
                         help="Ej: S01-Ep01")
    parser.add_argument("--output-dir", default="output_files")
    parser.add_argument("--tsv-out", default=None,
                         help="Default: {series-name}_{episode-label}_anki.tsv")
    parser.add_argument("--padding", type=float, default=0.25,
                         help="Segundos de margen antes/después (default: 0.25)")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--crf", type=int, default=32)
    parser.add_argument("--audio-bitrate", default="96k")
    parser.add_argument("--limit", type=int, default=None,
                         help="Procesar solo las primeras N líneas (prueba rápida)")
    parser.add_argument("--overwrite", action="store_true",
                         help="Regenerar clips que ya existen")
    args = parser.parse_args()

    if args.tsv_out is None:
        args.tsv_out = f"{args.series_name}_{args.episode_label}_anki.tsv"

    os.makedirs(args.output_dir, exist_ok=True)

    sentences = load_sentences(args.csv)
    if args.limit:
        sentences = sentences[:args.limit]

    windows = compute_padded_windows(sentences, args.padding)

    print(f"Líneas a procesar: {len(sentences)}")

    generated = 0
    skipped = 0
    errors = 0
    tsv_rows = []

    for i, (sentence, (start, end)) in enumerate(zip(sentences, windows), start=1):
        filename = f"{args.series_name}_{args.episode_label}_Line_{i:04d}.webm"
        output_path = os.path.join(args.output_dir, filename)

        if os.path.exists(output_path) and not args.overwrite:
            skipped += 1
            tsv_rows.append((sentence["text"], filename))
            print_progress(i, len(sentences))
            continue

        duration = end - start
        ok, stderr = run_ffmpeg_cut(
            args.video, start, duration, output_path,
            args.width, args.height, args.crf, args.audio_bitrate,
        )

        if ok:
            generated += 1
            tsv_rows.append((sentence["text"], filename))
        else:
            errors += 1
            print(f"\n  [ERROR] Línea {i}: {stderr.strip()[:200]}")

        print_progress(i, len(sentences))

    print()  # newline tras la barra de progreso

    with open(args.tsv_out, "w", encoding="utf-8", newline="") as f:
        for text, filename in tsv_rows:
            f.write(f"{text}\t\t[sound:{filename}]\n")

    total_size = sum(
        os.path.getsize(os.path.join(args.output_dir, fn))
        for _, fn in tsv_rows
        if os.path.exists(os.path.join(args.output_dir, fn))
    )

    print(f"\nGenerados: {generated}")
    print(f"Omitidos (ya existían): {skipped}")
    print(f"Errores: {errors}")
    print(f"Tamaño total de clips: {total_size / (1024*1024):.1f} MB")
    print(f"\nTSV generado: {args.tsv_out}")
    print(f"Clips en: {args.output_dir}/")


if __name__ == "__main__":
    main()