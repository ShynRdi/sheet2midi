from __future__ import annotations

from pathlib import Path

from .models import ValidationReport, ValidationWarning
from .musicxml import _child, _children, _local, _text, parse_root


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
