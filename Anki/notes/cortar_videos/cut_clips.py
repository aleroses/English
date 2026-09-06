#!/usr/bin/env python3
"""
cut_clips.py (v2 - pasada única, sin seeking)

Paso 2 del pipeline Anki-Video: toma el CSV generado por parse_srt_preview.py
y el archivo de vídeo original, corta un clip por cada oración y genera el
.tsv final listo para importar en Anki.

CAMBIO DE ENFOQUE respecto a la v1: en vez de "saltar" (-ss) a cada punto de
corte por separado (lo cual depende de los timestamps internos del
contenedor y puede acumular error en archivos con PTS poco confiables),
esta versión decodifica el episodio en UNA SOLA PASADA CONTINUA desde el
inicio, y usa filtros "split"/"trim" para producir todos los clips de esa
misma pasada. El corte se basa en tiempo realmente decodificado (igual a lo
que ves al reproducir el archivo normal), no en saltos.

Trade-off: es más lento por corrida completa (decodifica todo el episodio
una vez), pero es inmune al desfase acumulativo, y de hecho es más eficiente
que la v1 para el episodio completo (una decodificación en vez de cientos).

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


def build_single_pass_command(video_path, jobs, width, height, crf, audio_bitrate, max_time):
    """jobs: lista de dicts {index, start, end, output_path}.
    Construye UN comando ffmpeg que decodifica el vídeo una sola vez y
    produce todos los clips de 'jobs' usando split + trim/atrim."""
    n = len(jobs)

    video_labels = [f"v{j['index']}" for j in jobs]
    audio_labels = [f"a{j['index']}" for j in jobs]

    filter_parts = []
    filter_parts.append(
        "[0:v:0]split=" + str(n) + "".join(f"[{lbl}]" for lbl in video_labels)
    )
    filter_parts.append(
        "[0:a:0]asplit=" + str(n) + "".join(f"[{lbl}]" for lbl in audio_labels)
    )

    for j, vlbl in zip(jobs, video_labels):
        duration = j["end"] - j["start"]
        filter_parts.append(
            f"[{vlbl}]trim=start={j['start']:.3f}:duration={duration:.3f},"
            f"setpts=PTS-STARTPTS,scale={width}:{height}[out_{vlbl}]"
        )
    for j, albl in zip(jobs, audio_labels):
        duration = j["end"] - j["start"]
        filter_parts.append(
            f"[{albl}]atrim=start={j['start']:.3f}:duration={duration:.3f},"
            f"asetpts=PTS-STARTPTS[out_{albl}]"
        )

    filter_complex = ";".join(filter_parts)

    cmd = ["ffmpeg", "-y", "-t", f"{max_time:.3f}", "-i", video_path,
           "-filter_complex", filter_complex]

    for j, vlbl, albl in zip(jobs, video_labels, audio_labels):
        cmd += [
            "-map", f"[out_{vlbl}]",
            "-map", f"[out_{albl}]",
            "-c:v", "libvpx-vp9",
            "-crf", str(crf),
            "-b:v", "0",
            "-deadline", "good",
            "-cpu-used", "3",
            "-c:a", "libopus",
            "-b:a", audio_bitrate,
            j["output_path"],
        ]

    cmd += ["-loglevel", "error"]
    return cmd


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
    parser.add_argument("--padding", type=float, default=0.0,
                         help="Segundos de margen antes/después (default: 0.0)")
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

    jobs = []
    tsv_rows = []
    skipped = 0

    for i, (sentence, (start, end)) in enumerate(zip(sentences, windows), start=1):
        filename = f"{args.series_name}_{args.episode_label}_Line_{i:04d}.webm"
        output_path = os.path.join(args.output_dir, filename)
        tsv_rows.append((sentence["text"], filename))

        if os.path.exists(output_path) and not args.overwrite:
            skipped += 1
            continue

        jobs.append({
            "index": i,
            "start": start,
            "end": end,
            "output_path": output_path,
        })

    print(f"Líneas totales:      {len(sentences)}")
    print(f"Ya existían (omitidas): {skipped}")
    print(f"Por generar:         {len(jobs)}")

    generated = 0
    errors = 0

    if jobs:
        max_time = max(j["end"] for j in jobs) + 1.0
        print(f"\nDecodificando el episodio en una sola pasada hasta el segundo {max_time:.1f}...")
        cmd = build_single_pass_command(
            args.video, jobs, args.width, args.height, args.crf, args.audio_bitrate, max_time
        )
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print("\n[ERROR] ffmpeg falló en la pasada completa:")
            print(result.stderr.strip()[-2000:])
        else:
            for j in jobs:
                if os.path.exists(j["output_path"]) and os.path.getsize(j["output_path"]) > 0:
                    generated += 1
                else:
                    errors += 1
                    print(f"  [ERROR] No se generó: {j['output_path']}")

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