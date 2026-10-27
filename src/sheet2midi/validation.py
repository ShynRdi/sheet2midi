from __future__ import annotations

import tempfile
from dataclasses import asdict
from pathlib import Path

from .models import ValidationReport, ValidationWarning
from .musicxml import _child, _children, _local, _text, merge_scores, parse_root


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
                    cursor -= int(_text(item, "duration", "0") or "0")
                elif kind == "forward":
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
                    duration = int(_text(item, "duration", "0") or "0")
                    if _child(item, "chord") is None:
                        last_note_start = cursor
                        cursor += duration
                        note_end = cursor
                    else:
                        note_end = last_note_start + duration
                    maximum = max(maximum, note_end)

                    staff = int(_text(item, "staff", "1") or "1")
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

            if len(staff_maximum) > 1:
                for staff, maximum_for_staff in sorted(staff_maximum.items()):
                    staff_actual = maximum_for_staff / divisions
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
    }
