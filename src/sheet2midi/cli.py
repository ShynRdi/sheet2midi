from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark.corpus import run_corpus
from .benchmark.metrics import evaluate_scores
from .midi import render_midi
from .musicxml import (
    inspect_irregular_measures,
    inspect_measure_timelines,
    inspect_rhythm_runs,
)
from .omr import backend_status
from .pipeline import convert
from .validation import validate_musicxml, validate_musicxml_pages


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sheet2midi")
    sub = parser.add_subparsers(dest="command", required=True)

    convert_parser = sub.add_parser("convert", help="Convert sheet image/PDF to MusicXML + MIDI")
    convert_parser.add_argument("source", type=Path)
    convert_parser.add_argument("--output", "-o", type=Path, default=Path("out"))
    convert_parser.add_argument(
        "--engine", choices=["auto", "homr", "oemer", "audiveris"], default="auto"
    )
    convert_parser.add_argument("--track-mode", choices=["staff", "part"], default="staff")
    convert_parser.add_argument(
        "--keep-intermediates",
        action="store_true",
        help="Keep per-page OMR MusicXML outputs for debugging",
    )

    midi_parser = sub.add_parser("midi", help="Render existing MusicXML/MXL to MIDI")
    midi_parser.add_argument("source", type=Path)
    midi_parser.add_argument("--output", "-o", type=Path, default=Path("score.mid"))
    midi_parser.add_argument("--track-mode", choices=["staff", "part"], default="staff")
    midi_parser.add_argument(
        "--repair-staff-serialization",
        action="store_true",
        help="Experimentally repair only measures classified as staff serialization errors",
    )

    validate_parser = sub.add_parser("validate", help="Validate MusicXML structure")
    validate_parser.add_argument("source", type=Path)

    validate_pages_parser = sub.add_parser(
        "validate-pages",
        help="Validate multiple MusicXML pages with inherited score context",
    )
    validate_pages_parser.add_argument("sources", nargs="+", type=Path)

    inspect_parser = sub.add_parser(
        "inspect-measures",
        help="Inspect MusicXML cursor, backup, voice, and staff timelines",
    )
    inspect_parser.add_argument("source", type=Path)
    inspect_parser.add_argument("measures", nargs="+")
    inspect_parser.add_argument("--part-id")

    irregular_parser = sub.add_parser(
        "inspect-irregular",
        help="Summarize rhythmic evidence for suspicious MusicXML measures",
    )
    irregular_parser.add_argument("source", type=Path)
    irregular_parser.add_argument("measures", nargs="+")
    irregular_parser.add_argument("--part-id")

    rhythm_parser = sub.add_parser(
        "inspect-rhythm-runs",
        help="Find contiguous short-note rhythm runs for manual review",
    )
    rhythm_parser.add_argument("source", type=Path)
    rhythm_parser.add_argument("measures", nargs="+")
    rhythm_parser.add_argument("--part-id")
    rhythm_parser.add_argument("--min-notes", type=int, default=5)
    rhythm_parser.add_argument("--max-duration", type=float, default=0.5)

    evaluate_parser = sub.add_parser("evaluate", help="Compare predicted MusicXML to ground truth")
    evaluate_parser.add_argument("reference", type=Path)
    evaluate_parser.add_argument("prediction", type=Path)
    evaluate_parser.add_argument("--onset-tolerance", type=float, default=0.125)
    evaluate_parser.add_argument("--duration-tolerance", type=float, default=0.125)

    benchmark_parser = sub.add_parser("benchmark", help="Run OMR over the benchmark corpus")
    benchmark_parser.add_argument("manifest", type=Path)
    benchmark_parser.add_argument("--output", "-o", type=Path, default=Path("benchmark-out"))
    benchmark_parser.add_argument(
        "--engine", choices=["auto", "homr", "oemer", "audiveris"], default="auto"
    )
    benchmark_parser.add_argument("--track-mode", choices=["staff", "part"], default="staff")

    sub.add_parser("backends", help="Show installed OMR backends")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "backends":
        print(json.dumps(backend_status(), indent=2))
    elif args.command == "validate":
        print(json.dumps(validate_musicxml(args.source).to_dict(), indent=2))
    elif args.command == "validate-pages":
        print(json.dumps(validate_musicxml_pages(args.sources), indent=2))
    elif args.command == "inspect-measures":
        print(
            json.dumps(
                inspect_measure_timelines(
                    args.source,
                    args.measures,
                    part_id=args.part_id,
                ),
                indent=2,
            )
        )
    elif args.command == "inspect-irregular":
        print(
            json.dumps(
                inspect_irregular_measures(
                    args.source,
                    args.measures,
                    part_id=args.part_id,
                ),
                indent=2,
            )
        )
    elif args.command == "inspect-rhythm-runs":
        print(
            json.dumps(
                inspect_rhythm_runs(
                    args.source,
                    args.measures,
                    part_id=args.part_id,
                    min_notes=args.min_notes,
                    max_duration_quarters=args.max_duration,
                ),
                indent=2,
            )
        )
    elif args.command == "midi":
        output = render_midi(
            args.source,
            args.output,
            args.track_mode,
            repair_staff_serialization=args.repair_staff_serialization,
        )
        print(output)
    elif args.command == "evaluate":
        result = evaluate_scores(
            args.reference,
            args.prediction,
            onset_tolerance_quarters=args.onset_tolerance,
            duration_tolerance_quarters=args.duration_tolerance,
        )
        print(json.dumps(result.to_dict(), indent=2))
    elif args.command == "benchmark":
        result = run_corpus(
            args.manifest,
            args.output,
            engine=args.engine,
            track_mode=args.track_mode,
        )
        print(json.dumps(result, indent=2))
    elif args.command == "convert":
        result = convert(
            args.source,
            args.output,
            args.engine,
            args.track_mode,
            keep_intermediates=args.keep_intermediates,
        )
        print(
            json.dumps(
                {
                    "musicxml": str(result.musicxml),
                    "midi": str(result.midi),
                    "validation": str(result.validation_json),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
