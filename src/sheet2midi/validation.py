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
            attributes = _child(measure, "attributes")
            if attributes is not None:
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
                elif kind == "note":
                    duration = int(_text(item, "duration", "0") or "0")
                    if _child(item, "chord") is None:
                        last_note_start = cursor
                        cursor += duration
                        maximum = max(maximum, cursor)
                    else:
                        maximum = max(maximum, last_note_start + duration)

            actual = maximum / divisions
            expected = beats * (4 / beat_type)
            number = measure.attrib.get("number", str(measure_index + 1))
            implicit = measure.attrib.get("implicit") == "yes"
            is_first = measure_index == 0
            if not implicit and not is_first and abs(actual - expected) > tolerance_quarters:
                report.warnings.append(
                    ValidationWarning(
                        "measure_duration_mismatch",
                        f"Measure duration is {actual:g} quarter notes; expected {expected:g}",
                        part_id=part_id,
                        measure=number,
                    )
                )
    return report
