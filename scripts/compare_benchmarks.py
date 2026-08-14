#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

METRICS = ("note_f1", "onset_f1", "duration_accuracy")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def case_map(payload: dict) -> dict[str, dict]:
    return {case["id"]: case for case in payload["cases"]}


def fmt(value: float) -> str:
    return f"{value:.3f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two Sheet2MIDI benchmark runs")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--baseline-name", default="full-page")
    parser.add_argument("--candidate-name", default="cropped")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    baseline = load(args.baseline)
    candidate = load(args.candidate)
    base_cases = case_map(baseline)
    candidate_cases = case_map(candidate)

    lines = [
        "# OMR preprocessing comparison",
        "",
        (
            "| Case | Full-page Note F1 | Cropped Note F1 | Δ | "
            "Full-page Onset F1 | Cropped Onset F1 | Δ |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for case_id in sorted(set(base_cases) & set(candidate_cases)):
        base_metrics = base_cases[case_id].get("metrics")
        new_metrics = candidate_cases[case_id].get("metrics")
        if not base_metrics or not new_metrics:
            continue
        note_delta = new_metrics["note_f1"] - base_metrics["note_f1"]
        onset_delta = new_metrics["onset_f1"] - base_metrics["onset_f1"]
        lines.append(
            f"| {case_id} | {fmt(base_metrics['note_f1'])} | "
            f"{fmt(new_metrics['note_f1'])} | {note_delta:+.3f} | "
            f"{fmt(base_metrics['onset_f1'])} | {fmt(new_metrics['onset_f1'])} | "
            f"{onset_delta:+.3f} |"
        )

    lines.extend(
        [
            "",
            f"**{args.baseline_name} mean onset F1:** {baseline['mean_onset_f1']:.3f}",
            f"**{args.candidate_name} mean onset F1:** {candidate['mean_onset_f1']:.3f}",
            f"**Δ onset F1:** {candidate['mean_onset_f1'] - baseline['mean_onset_f1']:+.3f}",
            "",
            f"**{args.baseline_name} mean note F1:** {baseline['mean_note_f1']:.3f}",
            f"**{args.candidate_name} mean note F1:** {candidate['mean_note_f1']:.3f}",
            f"**Δ note F1:** {candidate['mean_note_f1'] - baseline['mean_note_f1']:+.3f}",
            "",
            f"**{args.baseline_name} mean duration accuracy:** "
            f"{baseline['mean_duration_accuracy']:.3f}",
            f"**{args.candidate_name} mean duration accuracy:** "
            f"{candidate['mean_duration_accuracy']:.3f}",
        ]
    )

    report = "\n".join(lines) + "\n"
    print(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
