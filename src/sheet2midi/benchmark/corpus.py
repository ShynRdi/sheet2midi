from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ..pipeline import convert
from .metrics import EvaluationResult, evaluate_scores


@dataclass(frozen=True)
class CorpusCase:
    id: str
    category: str
    ground_truth: Path
    image: Path


@dataclass(frozen=True)
class CaseResult:
    id: str
    category: str
    status: str
    metrics: EvaluationResult | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        if self.metrics is not None:
            payload["metrics"] = self.metrics.to_dict()
        return payload


def load_manifest(path: Path) -> list[CorpusCase]:
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    root = path.parent
    cases: list[CorpusCase] = []
    for item in payload["cases"]:
        cases.append(
            CorpusCase(
                id=item["id"],
                category=item["category"],
                ground_truth=root / item["ground_truth"],
                image=root / item["image"],
            )
        )
    return cases


def _mean(results: list[CaseResult], metric: str) -> float:
    values = [getattr(item.metrics, metric) for item in results if item.metrics is not None]
    return sum(values) / len(values) if values else 0.0


def _write_markdown_report(summary: dict, output: Path) -> None:
    lines = [
        "# Sheet2MIDI OMR benchmark",
        "",
        "| Case | Category | Status | Note F1 | Onset F1 | Duration | Part | Staff |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for case in summary["cases"]:
        metrics = case.get("metrics")
        if metrics is None:
            lines.append(
                f"| {case['id']} | {case['category']} | {case['status']} | - | - | - | - | - |"
            )
            if case.get("error"):
                lines.append("")
                lines.append(f"> {case['id']}: `{case['error']}`")
            continue
        lines.append(
            "| {id} | {category} | {status} | {note:.3f} | {onset:.3f} | "
            "{duration:.3f} | {part:.3f} | {staff:.3f} |".format(
                id=case["id"],
                category=case["category"],
                status=case["status"],
                note=metrics["note_f1"],
                onset=metrics["onset_f1"],
                duration=metrics["duration_accuracy"],
                part=metrics["part_accuracy"],
                staff=metrics["staff_accuracy"],
            )
        )

    lines.extend(
        [
            "",
            f"Successful cases: **{summary['successful_cases']}/{summary['total_cases']}**",
            f"Mean note F1: **{summary['mean_note_f1']:.3f}**",
            f"Mean onset F1: **{summary['mean_onset_f1']:.3f}**",
            f"Mean duration accuracy: **{summary['mean_duration_accuracy']:.3f}**",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_corpus(
    manifest: Path,
    output_dir: Path,
    *,
    engine: str = "auto",
    track_mode: str = "staff",
) -> dict:
    cases = load_manifest(manifest)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[CaseResult] = []

    for case in cases:
        if not case.image.is_file():
            results.append(
                CaseResult(case.id, case.category, "missing-image", error=str(case.image))
            )
            continue
        try:
            result = convert(
                case.image,
                output_dir / case.id,
                engine=engine,
                track_mode=track_mode,
            )
            metrics = evaluate_scores(case.ground_truth, result.musicxml)
            results.append(CaseResult(case.id, case.category, "ok", metrics=metrics))
        except Exception as exc:  # benchmark should report every case
            results.append(CaseResult(case.id, case.category, "error", error=str(exc)))

    successful = [item for item in results if item.metrics is not None]
    summary = {
        "cases": [item.to_dict() for item in results],
        "successful_cases": len(successful),
        "total_cases": len(results),
        "mean_note_f1": _mean(successful, "note_f1"),
        "mean_onset_f1": _mean(successful, "onset_f1"),
        "mean_duration_accuracy": _mean(successful, "duration_accuracy"),
    }
    json_output = output_dir / "benchmark.json"
    json_output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_markdown_report(summary, output_dir / "benchmark.md")
    return summary
