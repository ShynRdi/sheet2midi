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
        "mean_note_f1": (
            sum(item.metrics.note_f1 for item in successful) / len(successful)
            if successful
            else 0.0
        ),
        "mean_onset_f1": (
            sum(item.metrics.onset_f1 for item in successful) / len(successful)
            if successful
            else 0.0
        ),
    }
    (output_dir / "benchmark.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
