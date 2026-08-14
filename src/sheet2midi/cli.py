from __future__ import annotations

import argparse
import json
from pathlib import Path

from .midi import render_midi
from .omr import backend_status
from .pipeline import convert
from .validation import validate_musicxml


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

    midi_parser = sub.add_parser("midi", help="Render existing MusicXML/MXL to MIDI")
    midi_parser.add_argument("source", type=Path)
    midi_parser.add_argument("--output", "-o", type=Path, default=Path("score.mid"))
    midi_parser.add_argument("--track-mode", choices=["staff", "part"], default="staff")

    validate_parser = sub.add_parser("validate", help="Validate MusicXML structure")
    validate_parser.add_argument("source", type=Path)

    sub.add_parser("backends", help="Show installed OMR backends")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "backends":
        print(json.dumps(backend_status(), indent=2))
    elif args.command == "validate":
        print(json.dumps(validate_musicxml(args.source).to_dict(), indent=2))
    elif args.command == "midi":
        output = render_midi(args.source, args.output, args.track_mode)
        print(output)
    elif args.command == "convert":
        result = convert(args.source, args.output, args.engine, args.track_mode)
        print(json.dumps({
            "musicxml": str(result.musicxml),
            "midi": str(result.midi),
            "validation": str(result.validation_json),
        }, indent=2))


if __name__ == "__main__":
    main()
