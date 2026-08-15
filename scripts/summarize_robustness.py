#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize robustness benchmark outputs"
    )
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rows = []
    for result in sorted(args.root.glob("*/benchmark.json")):
        payload = json.loads(result.read_text(encoding="utf-8"))
        rows.append(
            (
                result.parent.name,
                payload["mean_note_f1"],
                payload["mean_onset_f1"],
                payload["mean_duration_accuracy"],
                payload["successful_cases"],
                payload["total_cases"],
            )
        )

    lines = [
        "# Sheet2MIDI robustness matrix",
        "",
        "| Variant | Note F1 | Onset F1 | Duration | Successful |",
        "|---|---:|---:|---:|---:|",
    ]
    for variant, note, onset, duration, successful, total in rows:
        lines.append(
            f"| {variant} | {note:.3f} | {onset:.3f} | {duration:.3f} | "
            f"{successful}/{total} |"
        )
    report = "\n".join(lines) + "\n"
    print(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
