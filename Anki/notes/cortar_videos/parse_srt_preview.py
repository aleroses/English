#!/usr/bin/env python3
"""
parse_srt_preview.py

Paso 1 del pipeline Anki-Video: parsea un .srt SDH, agrupa fragmentos de
subtítulo en oraciones completas y filtra bloques que son solo efectos de
sonido / etiquetas de hablante sin diálogo. NO corta vídeo todavía — solo
genera una tabla (CSV) para que revises que la agrupación es correcta.

Uso:
    python3 parse_srt_preview.py S01E01.srt -o S01E01_preview.csv
    python3 parse_srt_preview.py S01E01.srt -o S01E01_preview.csv --min-duration 1.0 --min-words 2

Columnas del CSV de salida:
    line_number, start, end, duration_sec, text
"""

import argparse
import csv
import re
import sys

TIME_RE = re.compile(
    r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})'
)
SENTENCE_END_RE = re.compile(r'["\']?[.!?]["\']?\s*$')


def timestamp_to_seconds(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def seconds_to_timestamp(total_seconds):
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"


def parse_srt_blocks(path):
    """Devuelve una lista de dicts: {start, end, raw_text} por bloque SRT."""
    with open(path, encoding="utf-8-sig") as f:
        content = f.read()

    raw_blocks = re.split(r'\n\s*\n', content.strip())
    blocks = []

    for raw_block in raw_blocks:
        lines = [l for l in raw_block.strip("\n").split("\n")]
        ts_idx = None
        for i, line in enumerate(lines):
            if "-->" in line:
                ts_idx = i
                break
        if ts_idx is None:
            continue

        m = TIME_RE.search(lines[ts_idx])
        if not m:
            continue

        h1, m1, s1, ms1, h2, m2, s2, ms2 = m.groups()
        start = timestamp_to_seconds(h1, m1, s1, ms1)
        end = timestamp_to_seconds(h2, m2, s2, ms2)

        text_lines = lines[ts_idx + 1:]
        raw_text = " ".join(l.strip() for l in text_lines if l.strip())

        blocks.append({"start": start, "end": end, "raw_text": raw_text})

    return blocks


def clean_text(raw_text):
    """Quita etiquetas (efectos de sonido / hablante) entre () y []."""
    cleaned = re.sub(r"\([^)]*\)", "", raw_text)
    cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # El SDH suele dejar un espacio antes de la puntuación (ej. "again ?").
    # Lo quitamos para que quede "again?" como se escribe normalmente.
    cleaned = re.sub(r"\s+([?.!,;:])", r"\1", cleaned)
    return cleaned


def normalize_case(text):
    """ALL CAPS -> sentence case. Limitación conocida: nombres propios
    quedarán en minúscula salvo que empiecen oración; se puede mejorar
    luego con una lista de excepciones (nombres de personajes, etc.)."""
    text = text.lower()

    # "i" / "i'm" / "i've" / "i'll" / "i'd" -> "I" / "I'm" / ...
    text = re.sub(r"\bi\b", "I", text)
    text = re.sub(r"\bi'(m|ve|ll|d)\b", lambda m: "I'" + m.group(1), text)

    # Mayúscula al inicio del texto y después de . ! ?
    def cap(match):
        return match.group(1) + match.group(2).upper()

    text = re.sub(r"(^|[.!?]\s+)([a-z])", cap, text)
    return text


def group_into_sentences(blocks):
    """Agrupa bloques consecutivos hasta encontrar puntuación de cierre.
    Descarta bloques que quedan vacíos tras limpiar (solo efectos de sonido).
    Devuelve (sentences, discarded_count)."""
    sentences = []
    discarded = 0

    buffer_parts = []
    buffer_start = None
    buffer_end = None

    for block in blocks:
        cleaned = clean_text(block["raw_text"])

        if not cleaned:
            discarded += 1
            continue

        if buffer_start is None:
            buffer_start = block["start"]

        buffer_parts.append(cleaned)
        buffer_end = block["end"]

        if SENTENCE_END_RE.search(cleaned):
            combined = " ".join(buffer_parts)
            sentences.append({
                "start": buffer_start,
                "end": buffer_end,
                "text": normalize_case(combined),
            })
            buffer_parts = []
            buffer_start = None

    # Flush de lo que quede sin cerrar al final del archivo
    if buffer_parts:
        combined = " ".join(buffer_parts)
        sentences.append({
            "start": buffer_start,
            "end": buffer_end,
            "text": normalize_case(combined),
        })

    return sentences, discarded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("srt_path", help="Ruta al archivo .srt de entrada")
    parser.add_argument("-o", "--output", default="preview.csv",
                         help="Ruta del CSV de salida (default: preview.csv)")
    parser.add_argument("--min-duration", type=float, default=0.0,
                         help="Descarta oraciones más cortas que N segundos (default: 0, sin filtro)")
    parser.add_argument("--min-words", type=int, default=0,
                         help="Descarta oraciones con menos de N palabras (default: 0, sin filtro)")
    args = parser.parse_args()

    blocks = parse_srt_blocks(args.srt_path)
    sentences, discarded = group_into_sentences(blocks)

    total_before_filter = len(sentences)
    filtered = []
    skipped_by_filter = 0

    for s in sentences:
        duration = s["end"] - s["start"]
        word_count = len(s["text"].split())
        if duration < args.min_duration or word_count < args.min_words:
            skipped_by_filter += 1
            continue
        filtered.append(s)

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["line_number", "start", "end", "duration_sec", "text"])
        for i, s in enumerate(filtered, start=1):
            duration = round(s["end"] - s["start"], 3)
            writer.writerow([
                i,
                seconds_to_timestamp(s["start"]),
                seconds_to_timestamp(s["end"]),
                duration,
                s["text"],
            ])

    print(f"Bloques SRT leídos:              {len(blocks)}")
    print(f"Bloques descartados (sin texto): {discarded}  (solo efectos de sonido)")
    print(f"Oraciones agrupadas:             {total_before_filter}")
    if args.min_duration > 0 or args.min_words > 0:
        print(f"Descartadas por filtro (--min-duration/--min-words): {skipped_by_filter}")
    print(f"Oraciones finales en CSV:        {len(filtered)}")
    print(f"\nCSV generado: {args.output}")


if __name__ == "__main__":
    main()