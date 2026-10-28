from __future__ import annotations

import tempfile
from dataclasses import asdict
from pathlib import Path

from .models import MeasureDiagnostic, ValidationReport, ValidationWarning
from .musicxml import _child, _children, _local, _text, merge_scores, parse_root


def _measure_diagnostic(
    *,
    part_id: str,
    number: str,
    actual: float,
    expected: float,
    staff_end_quarters: dict[int, float],
    note_count: int,
    backup_count: int,
    forward_count: int,
    staff_transition_count: int,
    voice_transition_count: int,
    time_modification_count: int,
    tuplet_notation_count: int,
    tolerance_quarters: float,
) -> MeasureDiagnostic | None:
    if abs(actual - expected) <= tolerance_quarters:
        return None

    reasons: list[str] = []
    classification = "strict_meter_mismatch"

    has_multiple_staves = len(staff_end_quarters) > 1
    has_tuplet_metadata = time_modification_count > 0 or tuplet_notation_count > 0
    severely_overfull = actual >= expected * 2
    dense_passage = note_count >= 12

    if has_multiple_staves and backup_count == 0 and staff_transition_count > 0:
        classification = "possible_staff_serialization_error"
        reasons.append(
            "multiple staves are serialized on one cursor without any backup"
        )
    elif has_tuplet_metadata or (severely_overfull and dense_passage):
        classification = "possible_irregular_passage"
        if has_tuplet_metadata:
            reasons.append("MusicXML contains tuplet or time-modification metadata")
        if severely_overfull and dense_passage:
            reasons.append("measure is densely notated and at least twice the expected duration")
    elif has_multiple_staves:
        values = list(staff_end_quarters.values())
        if max(values) - min(values) > tolerance_quarters:
            classification = "possible_staff_alignment_error"
            reasons.append("staff end positions diverge within the measure")

    if not reasons:
        reasons.append("measure duration differs from the active time signature")

    return MeasureDiagnostic(
        part_id=part_id,
        measure=number,
        classification=classification,
        actual_quarters=actual,
        expected_quarters=expected,
        staff_end_quarters={
            str(staff): end for staff, end in sorted(staff_end_quarters.items())
        },
        note_count=note_count,
        backup_count=backup_count,
        forward_count=forward_count,
        staff_transition_count=staff_transition_count,
        voice_transition_count=voice_transition_count,
        time_modification_count=time_modification_count,
        tuplet_notation_count=tuplet_notation_count,
        reasons=reasons,
    )


def validate_musicxml(path: Path, tolerance_quarters: float = 0.01) -> ValidationReport:
    try:
        root = parse_root(path)
    except Exception as exc:
        return ValidationReport(
            valid_xml=False,
            warnings=[ValidationWarning("invalid_xml", str(exc))],
        )

    score_type = _local(root.tag)
    report = ValidationReport(valid_xml=True, score_type=score_type)
    if score_type != "score-partwise":
        report.warnings.append(
            ValidationWarning(
                "unsupported_score_type",
                f"Expected score-partwise MusicXML, got {score_type}",
            )
        )
        return report

    for part in _children(root, "part"):
        part_id = part.attrib.get("id", "")
        divisions = 1
        beats = 4
        beat_type = 4
        for measure_index, measure in enumerate(_children(part, "measure")):
            cursor = 0
            maximum = 0
            staff_maximum: dict[int, int] = {}
            note_count = 0
            backup_count = 0
            forward_count = 0
            staff_transition_count = 0
            voice_transition_count = 0
            previous_staff: int | None = None
            previous_voice: str | None = None
            time_modification_count = 0
            tuplet_notation_count = 0

            for attributes in _children(measure, "attributes"):
                div_text = _text(attributes, "divisions")
                if div_text:
                    divisions = max(1, int(div_text))
                time = _child(attributes, "time")
                if time is not None:
                    beats = int(_text(time, "beats", "4") or "4")
                    beat_type = int(_text(time, "beat-type", "4") or "4")

            last_note_start = 0
            for item in measure:
                kind = _local(item.tag)
                if kind == "backup":
                    backup_count += 1
                    cursor -= int(_text(item, "duration", "0") or "0")
                elif kind == "forward":
                    forward_count += 1
                    cursor += int(_text(item, "duration", "0") or "0")
                    maximum = max(maximum, cursor)
                    staff_text = _text(item, "staff")
                    if staff_text:
                        staff = int(staff_text)
                        staff_maximum[staff] = max(
                            staff_maximum.get(staff, 0),
                            cursor,
                        )
                elif kind == "note":
                    note_count += 1
                    if _child(item, "time-modification") is not None:
                        time_modification_count += 1
                    notations = _child(item, "notations")
                    if notations is not None:
                        tuplet_notation_count += len(_children(notations, "tuplet"))

                    duration = int(_text(item, "duration", "0") or "0")
                    if _child(item, "chord") is None:
                        last_note_start = cursor
                        cursor += duration
                        note_end = cursor
                    else:
                        note_end = last_note_start + duration
                    maximum = max(maximum, note_end)

                    staff = int(_text(item, "staff", "1") or "1")
                    voice = _text(item, "voice", "1") or "1"
                    if previous_staff is not None and staff != previous_staff:
                        staff_transition_count += 1
                    if previous_voice is not None and voice != previous_voice:
                        voice_transition_count += 1
                    previous_staff = staff
                    previous_voice = voice
                    staff_maximum[staff] = max(
                        staff_maximum.get(staff, 0),
                        note_end,
                    )

            actual = maximum / divisions
            expected = beats * (4 / beat_type)
            number = measure.attrib.get("number", str(measure_index + 1))
            implicit = measure.attrib.get("implicit") == "yes"
            is_first = measure_index == 0
            if implicit or is_first:
                continue

            if abs(actual - expected) > tolerance_quarters:
                report.warnings.append(
                    ValidationWarning(
                        "measure_duration_mismatch",
                        f"Measure duration is {actual:g} quarter notes; expected {expected:g}",
                        part_id=part_id,
                        measure=number,
                    )
                )

            staff_end_quarters = {
                staff: maximum_for_staff / divisions
                for staff, maximum_for_staff in staff_maximum.items()
            }

            if len(staff_maximum) > 1:
                for staff, staff_actual in sorted(staff_end_quarters.items()):
                    if abs(staff_actual - expected) <= tolerance_quarters:
                        continue
                    report.warnings.append(
                        ValidationWarning(
                            "staff_duration_mismatch",
                            (
                                f"Staff {staff} duration is {staff_actual:g} quarter notes; "
                                f"expected {expected:g}"
                            ),
                            part_id=part_id,
                            measure=number,
                        )
                    )

            diagnostic = _measure_diagnostic(
                part_id=part_id,
                number=number,
                actual=actual,
                expected=expected,
                staff_end_quarters=staff_end_quarters,
                note_count=note_count,
                backup_count=backup_count,
                forward_count=forward_count,
                staff_transition_count=staff_transition_count,
                voice_transition_count=voice_transition_count,
                time_modification_count=time_modification_count,
                tuplet_notation_count=tuplet_notation_count,
                tolerance_quarters=tolerance_quarters,
            )
            if diagnostic is not None:
                report.diagnostics.append(diagnostic)

    return report


def validate_musicxml_pages(
    paths: list[Path],
    tolerance_quarters: float = 0.01,
) -> dict:
    if not paths:
        raise ValueError("At least one MusicXML page is required")

    page_measure_counts: list[int] = []
    normalized_paths = [Path(path) for path in paths]
    for path in normalized_paths:
        root = parse_root(path)
        if _local(root.tag) != "score-partwise":
            raise ValueError(f"Expected score-partwise MusicXML, got {_local(root.tag)} in {path}")
        parts = _children(root, "part")
        if not parts:
            raise ValueError(f"No parts found in {path}")
        page_measure_counts.append(len(_children(parts[0], "measure")))

    with tempfile.TemporaryDirectory(prefix="sheet2midi-validate-pages-") as tmp:
        merged = merge_scores(normalized_paths, Path(tmp) / "merged.musicxml")
        report = validate_musicxml(merged, tolerance_quarters=tolerance_quarters)

    boundaries: list[tuple[int, int, int]] = []
    offset = 0
    for page_index, count in enumerate(page_measure_counts, start=1):
        boundaries.append((offset + 1, offset + count, page_index))
        offset += count

    warnings: list[dict] = []
    for warning in report.warnings:
        payload = asdict(warning)
        payload["page"] = None
        payload["page_measure"] = None
        if warning.measure and warning.measure.isdigit():
            global_measure = int(warning.measure)
            for start, end, page_index in boundaries:
                if start <= global_measure <= end:
                    payload["page"] = page_index
                    payload["page_measure"] = str(global_measure - start + 1)
                    break
        warnings.append(payload)

    diagnostics: list[dict] = []
    for diagnostic in report.diagnostics:
        payload = asdict(diagnostic)
        payload["page"] = None
        payload["page_measure"] = None
        if diagnostic.measure.isdigit():
            global_measure = int(diagnostic.measure)
            for start, end, page_index in boundaries:
                if start <= global_measure <= end:
                    payload["page"] = page_index
                    payload["page_measure"] = str(global_measure - start + 1)
                    break
        diagnostics.append(payload)

    pages = [
        {
            "page": index,
            "source": str(path),
            "measure_count": count,
        }
        for index, (path, count) in enumerate(
            zip(normalized_paths, page_measure_counts, strict=True),
            start=1,
        )
    ]
    return {
        "valid_xml": report.valid_xml,
        "score_type": report.score_type,
        "pages": pages,
        "warnings": warnings,
        "warning_count": len(warnings),
        "diagnostics": diagnostics,
        "diagnostic_count": len(diagnostics),
    }
