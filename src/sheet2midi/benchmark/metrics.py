from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from ..models import NoteEvent
from ..musicxml import parse_events


@dataclass(frozen=True)
class EvaluationResult:
    reference_notes: int
    predicted_notes: int
    onset_matches: int
    strict_matches: int
    onset_precision: float
    onset_recall: float
    onset_f1: float
    note_precision: float
    note_recall: float
    note_f1: float
    duration_accuracy: float
    mean_onset_error_quarters: float
    mean_duration_error_quarters: float
    part_accuracy: float
    staff_accuracy: float
    voice_accuracy: float
    onset_tolerance_quarters: float
    duration_tolerance_quarters: float

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0 if numerator == 0 else 0.0
    return numerator / denominator


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _best_match(
    reference: NoteEvent,
    candidates: list[NoteEvent],
    used: set[int],
    onset_tolerance: float,
) -> tuple[int, NoteEvent] | None:
    compatible: list[tuple[float, int, NoteEvent]] = []
    for index, candidate in enumerate(candidates):
        if index in used or candidate.pitch != reference.pitch:
            continue
        onset_error = abs(candidate.start_quarters - reference.start_quarters)
        if onset_error <= onset_tolerance:
            compatible.append((onset_error, index, candidate))
    if not compatible:
        return None
    _, index, candidate = min(compatible, key=lambda item: item[0])
    return index, candidate


def evaluate_scores(
    reference_path: Path,
    predicted_path: Path,
    *,
    onset_tolerance_quarters: float = 0.125,
    duration_tolerance_quarters: float = 0.125,
) -> EvaluationResult:
    reference, _, _, _ = parse_events(Path(reference_path))
    predicted, _, _, _ = parse_events(Path(predicted_path))

    used: set[int] = set()
    onset_matches = 0
    strict_matches = 0
    duration_matches = 0
    onset_error_sum = 0.0
    duration_error_sum = 0.0
    part_matches = 0
    staff_matches = 0
    voice_matches = 0

    for expected in reference:
        matched = _best_match(expected, predicted, used, onset_tolerance_quarters)
        if matched is None:
            continue
        index, actual = matched
        used.add(index)
        onset_matches += 1
        onset_error = abs(actual.start_quarters - expected.start_quarters)
        duration_error = abs(actual.duration_quarters - expected.duration_quarters)
        onset_error_sum += onset_error
        duration_error_sum += duration_error
        if duration_error <= duration_tolerance_quarters:
            duration_matches += 1
            strict_matches += 1
        if actual.part_name == expected.part_name:
            part_matches += 1
        if actual.staff == expected.staff:
            staff_matches += 1
        if actual.voice == expected.voice:
            voice_matches += 1

    onset_precision = _ratio(onset_matches, len(predicted))
    onset_recall = _ratio(onset_matches, len(reference))
    note_precision = _ratio(strict_matches, len(predicted))
    note_recall = _ratio(strict_matches, len(reference))

    return EvaluationResult(
        reference_notes=len(reference),
        predicted_notes=len(predicted),
        onset_matches=onset_matches,
        strict_matches=strict_matches,
        onset_precision=onset_precision,
        onset_recall=onset_recall,
        onset_f1=_f1(onset_precision, onset_recall),
        note_precision=note_precision,
        note_recall=note_recall,
        note_f1=_f1(note_precision, note_recall),
        duration_accuracy=_ratio(duration_matches, onset_matches),
        mean_onset_error_quarters=(onset_error_sum / onset_matches if onset_matches else 0.0),
        mean_duration_error_quarters=(
            duration_error_sum / onset_matches if onset_matches else 0.0
        ),
        part_accuracy=_ratio(part_matches, onset_matches),
        staff_accuracy=_ratio(staff_matches, onset_matches),
        voice_accuracy=_ratio(voice_matches, onset_matches),
        onset_tolerance_quarters=onset_tolerance_quarters,
        duration_tolerance_quarters=duration_tolerance_quarters,
    )
