from __future__ import annotations

import copy
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from .models import KeySignatureEvent, NoteEvent, TempoEvent, TimeSignatureEvent


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local(child.tag) == name]


def _child(element: ET.Element, name: str) -> ET.Element | None:
    for child in element:
        if _local(child.tag) == name:
            return child
    return None


def _text(element: ET.Element, name: str, default: str | None = None) -> str | None:
    node = _child(element, name)
    return node.text.strip() if node is not None and node.text else default


def read_musicxml_bytes(path: Path) -> bytes:
    path = Path(path)
    if path.suffix.lower() != ".mxl":
        return path.read_bytes()

    with zipfile.ZipFile(path) as archive:
        rootfile: str | None = None
        try:
            container = ET.fromstring(archive.read("META-INF/container.xml"))
            for node in container.iter():
                if _local(node.tag) == "rootfile":
                    rootfile = node.attrib.get("full-path")
                    if rootfile:
                        break
        except KeyError:
            pass

        if rootfile is None:
            candidates = [
                name
                for name in archive.namelist()
                if name.lower().endswith((".xml", ".musicxml"))
                and not name.startswith("META-INF/")
            ]
            if not candidates:
                raise ValueError(f"No MusicXML document found inside {path}")
            rootfile = candidates[0]
        return archive.read(rootfile)


def parse_root(path: Path) -> ET.Element:
    return ET.fromstring(read_musicxml_bytes(path))


def normalize_musicxml(path: Path, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    root = parse_root(path)
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
    return output


def merge_scores(inputs: list[Path], output: Path) -> Path:
    if not inputs:
        raise ValueError("No MusicXML inputs to merge")
    if len(inputs) == 1:
        return normalize_musicxml(inputs[0], output)

    base = parse_root(inputs[0])
    if _local(base.tag) != "score-partwise":
        raise ValueError("Only score-partwise MusicXML is supported for page merging")

    base_parts = _children(base, "part")
    for source in inputs[1:]:
        root = parse_root(source)
        parts = _children(root, "part")
        if len(parts) != len(base_parts):
            raise ValueError("Cannot merge pages with different part counts")
        for base_part, extra_part in zip(base_parts, parts, strict=True):
            for measure in _children(extra_part, "measure"):
                base_part.append(copy.deepcopy(measure))

    for part in base_parts:
        for index, measure in enumerate(_children(part, "measure"), start=1):
            measure.set("number", str(index))

    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(base).write(output, encoding="utf-8", xml_declaration=True)
    return output


def pitch_to_midi(note: ET.Element, transpose: int = 0) -> int | None:
    if _child(note, "rest") is not None:
        return None
    pitch = _child(note, "pitch")
    if pitch is None:
        return None
    step = _text(pitch, "step")
    octave_text = _text(pitch, "octave")
    if step is None or octave_text is None:
        return None
    semitone = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[step]
    alter = int(float(_text(pitch, "alter", "0") or "0"))
    midi = 12 * (int(octave_text) + 1) + semitone + alter + transpose
    return max(0, min(127, midi))


def parse_events(
    path: Path,
    repair_serialized_measures: set[tuple[str, str]] | None = None,
) -> tuple[
    list[NoteEvent], list[TempoEvent], list[TimeSignatureEvent], list[KeySignatureEvent]
]:
    root = parse_root(path)
    if _local(root.tag) != "score-partwise":
        raise ValueError("Only score-partwise MusicXML is currently supported")

    repair_serialized_measures = repair_serialized_measures or set()

    part_names: dict[str, str] = {}
    part_list = _child(root, "part-list")
    if part_list is not None:
        for score_part in _children(part_list, "score-part"):
            part_id = score_part.attrib.get("id", "")
            part_names[part_id] = _text(score_part, "part-name", part_id) or part_id

    notes: list[NoteEvent] = []
    tempos: list[TempoEvent] = []
    signatures: list[TimeSignatureEvent] = []
    keys: list[KeySignatureEvent] = []
    seen_tempos: set[tuple[float, float]] = set()
    seen_signatures: set[tuple[float, int, int]] = set()
    seen_keys: set[tuple[float, int, str]] = set()

    for part in _children(root, "part"):
        part_id = part.attrib.get("id", "part")
        part_name = part_names.get(part_id, part_id)
        absolute_quarters = 0.0
        divisions = 1
        transpose = 0
        open_ties: dict[tuple[int, str, int], NoteEvent] = {}

        for measure in _children(part, "measure"):
            measure_number = measure.attrib.get("number", "")
            repair_serialized = (
                part_id,
                measure_number,
            ) in repair_serialized_measures
            cursor_div = 0
            max_div = 0
            last_note_start = 0
            stream_cursors: dict[tuple[int, str], int] = {}
            stream_last_note_start: dict[tuple[int, str], int] = {}

            for item in measure:
                kind = _local(item.tag)
                if kind == "attributes":
                    div_text = _text(item, "divisions")
                    if div_text:
                        divisions = max(1, int(div_text))
                    transposition = _child(item, "transpose")
                    if transposition is not None:
                        chromatic = _text(transposition, "chromatic", "0") or "0"
                        transpose = int(chromatic)
                    time = _child(item, "time")
                    if time is not None:
                        beats = int(_text(time, "beats", "4") or "4")
                        beat_type = int(_text(time, "beat-type", "4") or "4")
                        event_key = (absolute_quarters, beats, beat_type)
                        if event_key not in seen_signatures:
                            signatures.append(TimeSignatureEvent(*event_key))
                            seen_signatures.add(event_key)
                    key = _child(item, "key")
                    if key is not None:
                        fifths = int(_text(key, "fifths", "0") or "0")
                        mode = _text(key, "mode", "major") or "major"
                        event_key = (absolute_quarters, fifths, mode)
                        if event_key not in seen_keys:
                            keys.append(KeySignatureEvent(*event_key))
                            seen_keys.add(event_key)

                elif kind == "direction":
                    sound = _child(item, "sound")
                    if sound is not None and "tempo" in sound.attrib:
                        bpm = float(sound.attrib["tempo"])
                        offset = float(_text(item, "offset", "0") or "0") / divisions
                        event_key = (absolute_quarters + offset, bpm)
                        if event_key not in seen_tempos:
                            tempos.append(TempoEvent(*event_key))
                            seen_tempos.add(event_key)

                elif kind == "backup":
                    duration = int(_text(item, "duration", "0") or "0")
                    cursor_div -= duration

                elif kind == "forward":
                    duration = int(_text(item, "duration", "0") or "0")
                    cursor_div += duration
                    max_div = max(max_div, cursor_div)

                elif kind == "note":
                    duration_div = int(_text(item, "duration", "0") or "0")
                    is_chord = _child(item, "chord") is not None
                    staff = int(_text(item, "staff", "1") or "1")
                    voice = _text(item, "voice", "1") or "1"

                    if repair_serialized:
                        stream_key = (staff, voice)
                        stream_cursor = stream_cursors.get(stream_key, 0)
                        if is_chord:
                            start_div = stream_last_note_start.get(
                                stream_key,
                                stream_cursor,
                            )
                        else:
                            start_div = stream_cursor
                            stream_last_note_start[stream_key] = start_div
                            stream_cursors[stream_key] = start_div + duration_div
                        max_div = max(max_div, start_div + duration_div)
                    else:
                        start_div = last_note_start if is_chord else cursor_div
                        if not is_chord:
                            last_note_start = start_div

                    pitch = pitch_to_midi(item, transpose)
                    if pitch is not None and duration_div > 0:
                        start = absolute_quarters + (start_div / divisions)
                        duration = duration_div / divisions
                        tie_types = {
                            tie.attrib.get("type", "") for tie in _children(item, "tie")
                        }
                        tie_key = (staff, voice, pitch)
                        event = NoteEvent(
                            part_id=part_id,
                            part_name=part_name,
                            staff=staff,
                            voice=voice,
                            pitch=pitch,
                            start_quarters=start,
                            duration_quarters=duration,
                        )

                        if "stop" in tie_types and tie_key in open_ties:
                            original = open_ties[tie_key]
                            extended = NoteEvent(
                                **{
                                    **original.__dict__,
                                    "duration_quarters": (
                                        start + duration - original.start_quarters
                                    ),
                                }
                            )
                            if "start" in tie_types:
                                open_ties[tie_key] = extended
                            else:
                                notes.append(extended)
                                del open_ties[tie_key]
                        elif "start" in tie_types:
                            open_ties[tie_key] = event
                        else:
                            notes.append(event)

                    if not repair_serialized and not is_chord:
                        cursor_div += duration_div
                        max_div = max(max_div, cursor_div)

            absolute_quarters += max_div / divisions

        notes.extend(open_ties.values())

    if not tempos:
        tempos.append(TempoEvent(0.0, 120.0))
    return notes, sorted(tempos, key=lambda x: x.start_quarters), signatures, keys



def inspect_measure_timelines(
    path: Path,
    measures: list[str],
    part_id: str | None = None,
) -> dict:
    if not measures:
        raise ValueError("At least one measure number is required")

    root = parse_root(path)
    if _local(root.tag) != "score-partwise":
        raise ValueError("Only score-partwise MusicXML is currently supported")

    requested = set(measures)
    results: list[dict] = []

    for part in _children(root, "part"):
        current_part_id = part.attrib.get("id", "part")
        if part_id is not None and current_part_id != part_id:
            continue

        divisions = 1
        beats = 4
        beat_type = 4

        for measure_index, measure in enumerate(_children(part, "measure"), start=1):
            number = measure.attrib.get("number", str(measure_index))
            cursor = 0
            maximum = 0
            last_note_start = 0
            events: list[dict] = []

            for item_index, item in enumerate(measure):
                kind = _local(item.tag)

                if kind == "attributes":
                    div_text = _text(item, "divisions")
                    if div_text:
                        divisions = max(1, int(div_text))
                    time = _child(item, "time")
                    if time is not None:
                        beats = int(_text(time, "beats", "4") or "4")
                        beat_type = int(_text(time, "beat-type", "4") or "4")
                    if number in requested:
                        events.append(
                            {
                                "index": item_index,
                                "kind": "attributes",
                                "divisions": divisions,
                                "time": f"{beats}/{beat_type}",
                                "cursor_before_quarters": cursor / divisions,
                                "cursor_after_quarters": cursor / divisions,
                            }
                        )
                    continue

                if kind == "backup":
                    duration = int(_text(item, "duration", "0") or "0")
                    before = cursor
                    cursor -= duration
                    if number in requested:
                        events.append(
                            {
                                "index": item_index,
                                "kind": "backup",
                                "duration_quarters": duration / divisions,
                                "cursor_before_quarters": before / divisions,
                                "cursor_after_quarters": cursor / divisions,
                            }
                        )
                    continue

                if kind == "forward":
                    duration = int(_text(item, "duration", "0") or "0")
                    before = cursor
                    cursor += duration
                    maximum = max(maximum, cursor)
                    if number in requested:
                        events.append(
                            {
                                "index": item_index,
                                "kind": "forward",
                                "duration_quarters": duration / divisions,
                                "staff": _text(item, "staff"),
                                "voice": _text(item, "voice"),
                                "cursor_before_quarters": before / divisions,
                                "cursor_after_quarters": cursor / divisions,
                            }
                        )
                    continue

                if kind != "note":
                    continue

                duration = int(_text(item, "duration", "0") or "0")
                is_chord = _child(item, "chord") is not None
                start = last_note_start if is_chord else cursor
                if not is_chord:
                    last_note_start = start
                    cursor += duration
                end = start + duration
                maximum = max(maximum, end)

                if number in requested:
                    pitch = _child(item, "pitch")
                    pitch_name = None
                    if pitch is not None:
                        step = _text(pitch, "step")
                        octave = _text(pitch, "octave")
                        alter = _text(pitch, "alter")
                        if step and octave:
                            accidental = ""
                            if alter == "1":
                                accidental = "#"
                            elif alter == "-1":
                                accidental = "b"
                            pitch_name = f"{step}{accidental}{octave}"

                    events.append(
                        {
                            "index": item_index,
                            "kind": "note",
                            "staff": int(_text(item, "staff", "1") or "1"),
                            "voice": _text(item, "voice", "1") or "1",
                            "pitch": pitch_name,
                            "rest": _child(item, "rest") is not None,
                            "chord": is_chord,
                            "duration_quarters": duration / divisions,
                            "start_quarters": start / divisions,
                            "end_quarters": end / divisions,
                            "cursor_after_quarters": cursor / divisions,
                        }
                    )

            if number in requested:
                results.append(
                    {
                        "part_id": current_part_id,
                        "measure": number,
                        "divisions": divisions,
                        "time_signature": f"{beats}/{beat_type}",
                        "expected_quarters": beats * (4 / beat_type),
                        "maximum_quarters": maximum / divisions,
                        "final_cursor_quarters": cursor / divisions,
                        "events": events,
                    }
                )

    found = {(item["part_id"], item["measure"]) for item in results}
    missing = []
    for measure in measures:
        if part_id is None:
            if not any(found_measure == measure for _, found_measure in found):
                missing.append(measure)
        elif (part_id, measure) not in found:
            missing.append(measure)

    return {
        "source": str(path),
        "requested_measures": measures,
        "part_id": part_id,
        "missing_measures": missing,
        "measures": results,
    }



def inspect_irregular_measures(
    path: Path,
    measures: list[str],
    part_id: str | None = None,
) -> dict:
    if not measures:
        raise ValueError("At least one measure number is required")

    root = parse_root(path)
    if _local(root.tag) != "score-partwise":
        raise ValueError("Only score-partwise MusicXML is currently supported")

    requested = set(measures)
    results: list[dict] = []

    for part in _children(root, "part"):
        current_part_id = part.attrib.get("id", "part")
        if part_id is not None and current_part_id != part_id:
            continue

        divisions = 1
        beats = 4
        beat_type = 4

        for measure_index, measure in enumerate(_children(part, "measure"), start=1):
            number = measure.attrib.get("number", str(measure_index))

            for attributes in _children(measure, "attributes"):
                div_text = _text(attributes, "divisions")
                if div_text:
                    divisions = max(1, int(div_text))
                time = _child(attributes, "time")
                if time is not None:
                    beats = int(_text(time, "beats", "4") or "4")
                    beat_type = int(_text(time, "beat-type", "4") or "4")

            if number not in requested:
                continue

            cursor = 0
            maximum = 0
            last_note_start = 0
            note_count = 0
            rest_count = 0
            chord_note_count = 0
            grace_note_count = 0
            dotted_note_count = 0
            missing_type_count = 0
            type_counts: dict[str, int] = {}
            duration_counts: dict[str, int] = {}
            beam_counts: dict[str, int] = {}
            staff_spans: dict[int, list[int]] = {}
            voice_spans: dict[tuple[int, str], list[int]] = {}
            stream_totals: dict[tuple[int, str], int] = {}
            backup_count = 0
            backup_total = 0
            forward_count = 0
            forward_total = 0
            time_modification_count = 0
            tuplet_notation_count = 0
            barline_count = len(_children(measure, "barline"))

            print_markers = [
                {
                    "new_system": item.attrib.get("new-system"),
                    "new_page": item.attrib.get("new-page"),
                }
                for item in measure
                if _local(item.tag) == "print"
            ]

            for item in measure:
                kind = _local(item.tag)
                if kind == "backup":
                    duration = int(_text(item, "duration", "0") or "0")
                    backup_count += 1
                    backup_total += duration
                    cursor -= duration
                    continue
                if kind == "forward":
                    duration = int(_text(item, "duration", "0") or "0")
                    forward_count += 1
                    forward_total += duration
                    cursor += duration
                    maximum = max(maximum, cursor)
                    continue
                if kind != "note":
                    continue

                note_count += 1
                duration = int(_text(item, "duration", "0") or "0")
                is_chord = _child(item, "chord") is not None
                if is_chord:
                    chord_note_count += 1
                    start = last_note_start
                else:
                    start = cursor
                    last_note_start = start
                    cursor += duration

                end = start + duration
                maximum = max(maximum, end)

                if _child(item, "rest") is not None:
                    rest_count += 1
                if _child(item, "grace") is not None:
                    grace_note_count += 1
                if _child(item, "dot") is not None:
                    dotted_note_count += 1

                note_type = _text(item, "type")
                if note_type is None:
                    missing_type_count += 1
                    note_type = "<missing>"
                type_counts[note_type] = type_counts.get(note_type, 0) + 1

                duration_key = f"{duration / divisions:g}"
                duration_counts[duration_key] = duration_counts.get(duration_key, 0) + 1

                for beam in _children(item, "beam"):
                    value = (beam.text or "").strip() or "<empty>"
                    beam_counts[value] = beam_counts.get(value, 0) + 1

                if _child(item, "time-modification") is not None:
                    time_modification_count += 1
                notations = _child(item, "notations")
                if notations is not None:
                    tuplet_notation_count += len(_children(notations, "tuplet"))

                staff = int(_text(item, "staff", "1") or "1")
                voice = _text(item, "voice", "1") or "1"
                staff_span = staff_spans.setdefault(staff, [start, end])
                staff_span[0] = min(staff_span[0], start)
                staff_span[1] = max(staff_span[1], end)
                voice_span = voice_spans.setdefault((staff, voice), [start, end])
                voice_span[0] = min(voice_span[0], start)
                voice_span[1] = max(voice_span[1], end)
                if not is_chord:
                    stream_key = (staff, voice)
                    stream_totals[stream_key] = stream_totals.get(stream_key, 0) + duration

            expected = beats * (4 / beat_type)
            results.append(
                {
                    "part_id": current_part_id,
                    "measure": number,
                    "time_signature": f"{beats}/{beat_type}",
                    "divisions": divisions,
                    "expected_quarters": expected,
                    "serialized_max_quarters": maximum / divisions,
                    "final_cursor_quarters": cursor / divisions,
                    "implicit": measure.attrib.get("implicit"),
                    "non_controlling": measure.attrib.get("non-controlling"),
                    "attributes_count": len(_children(measure, "attributes")),
                    "barline_count": barline_count,
                    "print_markers": print_markers,
                    "note_count": note_count,
                    "rest_count": rest_count,
                    "chord_note_count": chord_note_count,
                    "grace_note_count": grace_note_count,
                    "dotted_note_count": dotted_note_count,
                    "missing_type_count": missing_type_count,
                    "note_type_counts": dict(sorted(type_counts.items())),
                    "duration_quarter_counts": dict(
                        sorted(duration_counts.items(), key=lambda item: float(item[0]))
                    ),
                    "beam_counts": dict(sorted(beam_counts.items())),
                    "backup_count": backup_count,
                    "backup_total_quarters": backup_total / divisions,
                    "forward_count": forward_count,
                    "forward_total_quarters": forward_total / divisions,
                    "time_modification_count": time_modification_count,
                    "tuplet_notation_count": tuplet_notation_count,
                    "staff_spans": {
                        str(staff): {
                            "start_quarters": span[0] / divisions,
                            "end_quarters": span[1] / divisions,
                            "span_quarters": (span[1] - span[0]) / divisions,
                        }
                        for staff, span in sorted(staff_spans.items())
                    },
                    "voice_spans": {
                        f"{staff}:{voice}": {
                            "start_quarters": span[0] / divisions,
                            "end_quarters": span[1] / divisions,
                            "span_quarters": (span[1] - span[0]) / divisions,
                        }
                        for (staff, voice), span in sorted(voice_spans.items())
                    },
                    "independent_stream_totals_quarters": {
                        f"{staff}:{voice}": total / divisions
                        for (staff, voice), total in sorted(stream_totals.items())
                    },
                }
            )

    found = {(item["part_id"], item["measure"]) for item in results}
    missing = []
    for measure in measures:
        if part_id is None:
            if not any(found_measure == measure for _, found_measure in found):
                missing.append(measure)
        elif (part_id, measure) not in found:
            missing.append(measure)

    return {
        "source": str(path),
        "requested_measures": measures,
        "part_id": part_id,
        "missing_measures": missing,
        "measures": results,
    }



def inspect_rhythm_runs(
    path: Path,
    measures: list[str],
    part_id: str | None = None,
    min_notes: int = 5,
    max_duration_quarters: float = 0.5,
) -> dict:
    if not measures:
        raise ValueError("At least one measure number is required")
    if min_notes < 2:
        raise ValueError("min_notes must be at least 2")
    if max_duration_quarters <= 0:
        raise ValueError("max_duration_quarters must be positive")

    root = parse_root(path)
    if _local(root.tag) != "score-partwise":
        raise ValueError("Only score-partwise MusicXML is currently supported")

    requested = set(measures)
    results: list[dict] = []

    for part in _children(root, "part"):
        current_part_id = part.attrib.get("id", "part")
        if part_id is not None and current_part_id != part_id:
            continue

        divisions = 1
        beats = 4
        beat_type = 4

        for measure_index, measure in enumerate(_children(part, "measure"), start=1):
            number = measure.attrib.get("number", str(measure_index))

            for attributes in _children(measure, "attributes"):
                div_text = _text(attributes, "divisions")
                if div_text:
                    divisions = max(1, int(div_text))
                time = _child(attributes, "time")
                if time is not None:
                    beats = int(_text(time, "beats", "4") or "4")
                    beat_type = int(_text(time, "beat-type", "4") or "4")

            if number not in requested:
                continue

            cursor = 0
            last_note_start = 0
            stream_notes: dict[tuple[int, str], list[dict]] = {}

            for item in measure:
                kind = _local(item.tag)
                if kind == "backup":
                    cursor -= int(_text(item, "duration", "0") or "0")
                    continue
                if kind == "forward":
                    cursor += int(_text(item, "duration", "0") or "0")
                    continue
                if kind != "note":
                    continue

                duration = int(_text(item, "duration", "0") or "0")
                is_chord = _child(item, "chord") is not None
                start = last_note_start if is_chord else cursor
                if not is_chord:
                    last_note_start = start
                    cursor += duration

                if (
                    is_chord
                    or duration <= 0
                    or _child(item, "rest") is not None
                    or _child(item, "grace") is not None
                ):
                    continue

                staff = int(_text(item, "staff", "1") or "1")
                voice = _text(item, "voice", "1") or "1"
                note_type = _text(item, "type") or "<missing>"
                duration_quarters = duration / divisions
                has_time_modification = _child(item, "time-modification") is not None
                notations = _child(item, "notations")
                tuplet_count = (
                    len(_children(notations, "tuplet"))
                    if notations is not None
                    else 0
                )

                stream_notes.setdefault((staff, voice), []).append(
                    {
                        "start_div": start,
                        "end_div": start + duration,
                        "duration_quarters": duration_quarters,
                        "note_type": note_type,
                        "has_time_modification": has_time_modification,
                        "tuplet_notation_count": tuplet_count,
                    }
                )

            candidates: list[dict] = []
            for (staff, voice), notes in sorted(stream_notes.items()):
                notes = sorted(notes, key=lambda note: (note["start_div"], note["end_div"]))
                run: list[dict] = []

                def flush_run(
                    *,
                    candidates: list[dict] = candidates,
                    staff: int = staff,
                    voice: str = voice,
                    divisions: int = divisions,
                ) -> None:
                    nonlocal run
                    if len(run) < min_notes:
                        run = []
                        return

                    duration_quarters = run[0]["duration_quarters"]
                    if duration_quarters > max_duration_quarters:
                        run = []
                        return

                    has_tuplet_metadata = any(
                        note["has_time_modification"]
                        or note["tuplet_notation_count"] > 0
                        for note in run
                    )
                    candidates.append(
                        {
                            "staff": staff,
                            "voice": voice,
                            "start_quarters": run[0]["start_div"] / divisions,
                            "end_quarters": run[-1]["end_div"] / divisions,
                            "span_quarters": (
                                run[-1]["end_div"] - run[0]["start_div"]
                            )
                            / divisions,
                            "note_count": len(run),
                            "note_type": run[0]["note_type"],
                            "duration_quarters": duration_quarters,
                            "has_tuplet_metadata": has_tuplet_metadata,
                            "candidate_kind": (
                                "short_run_with_tuplet_metadata"
                                if has_tuplet_metadata
                                else "short_run_without_tuplet_metadata"
                            ),
                        }
                    )
                    run = []

                for note in notes:
                    if not run:
                        run = [note]
                        continue

                    previous = run[-1]
                    same_duration = (
                        abs(
                            note["duration_quarters"]
                            - previous["duration_quarters"]
                        )
                        <= 1e-9
                    )
                    same_type = note["note_type"] == previous["note_type"]
                    contiguous = note["start_div"] == previous["end_div"]

                    if same_duration and same_type and contiguous:
                        run.append(note)
                    else:
                        flush_run()
                        run = [note]

                flush_run()

            print_markers = [
                {
                    "new_system": item.attrib.get("new-system"),
                    "new_page": item.attrib.get("new-page"),
                }
                for item in measure
                if _local(item.tag) == "print"
            ]
            expected = beats * (4 / beat_type)
            results.append(
                {
                    "part_id": current_part_id,
                    "measure": number,
                    "time_signature": f"{beats}/{beat_type}",
                    "expected_quarters": expected,
                    "print_markers": print_markers,
                    "candidate_count": len(candidates),
                    "candidates": candidates,
                }
            )

    found = {(item["part_id"], item["measure"]) for item in results}
    missing = []
    for measure in measures:
        if part_id is None:
            if not any(found_measure == measure for _, found_measure in found):
                missing.append(measure)
        elif (part_id, measure) not in found:
            missing.append(measure)

    return {
        "source": str(path),
        "requested_measures": measures,
        "part_id": part_id,
        "min_notes": min_notes,
        "max_duration_quarters": max_duration_quarters,
        "missing_measures": missing,
        "measures": results,
    }



def inspect_rhythm_group_hypotheses(
    path: Path,
    measures: list[str],
    part_id: str | None = None,
    group_size: int = 7,
    min_notes: int = 5,
    max_duration_quarters: float = 0.5,
) -> dict:
    if group_size < 2:
        raise ValueError("group_size must be at least 2")

    run_report = inspect_rhythm_runs(
        path,
        measures,
        part_id=part_id,
        min_notes=min_notes,
        max_duration_quarters=max_duration_quarters,
    )

    grouped_measures: list[dict] = []
    for measure in run_report["measures"]:
        hypotheses: list[dict] = []
        for candidate in measure["candidates"]:
            note_count = int(candidate["note_count"])
            full_groups, remainder = divmod(note_count, group_size)
            hypotheses.append(
                {
                    "staff": candidate["staff"],
                    "voice": candidate["voice"],
                    "start_quarters": candidate["start_quarters"],
                    "end_quarters": candidate["end_quarters"],
                    "note_count": note_count,
                    "note_type": candidate["note_type"],
                    "duration_quarters": candidate["duration_quarters"],
                    "group_size": group_size,
                    "full_group_count": full_groups,
                    "remainder_notes": remainder,
                    "exact_grouping": full_groups > 0 and remainder == 0,
                    "encoded_group_span_quarters": (
                        group_size * candidate["duration_quarters"]
                    ),
                    "has_tuplet_metadata": candidate["has_tuplet_metadata"],
                    "evidence": (
                        "exact_note_count_multiple_only"
                        if full_groups > 0 and remainder == 0
                        else "partial_note_count_match_only"
                    ),
                }
            )

        grouped_measures.append(
            {
                "part_id": measure["part_id"],
                "measure": measure["measure"],
                "time_signature": measure["time_signature"],
                "expected_quarters": measure["expected_quarters"],
                "print_markers": measure["print_markers"],
                "hypothesis_count": len(hypotheses),
                "exact_grouping_count": sum(
                    1 for hypothesis in hypotheses if hypothesis["exact_grouping"]
                ),
                "hypotheses": hypotheses,
            }
        )

    return {
        "source": run_report["source"],
        "requested_measures": run_report["requested_measures"],
        "part_id": part_id,
        "group_size": group_size,
        "min_notes": min_notes,
        "max_duration_quarters": max_duration_quarters,
        "missing_measures": run_report["missing_measures"],
        "measures": grouped_measures,
    }



def inspect_measure_offsets(
    path: Path,
    part_id: str,
) -> dict:
    root = parse_root(path)
    if _local(root.tag) != "score-partwise":
        raise ValueError("Only score-partwise MusicXML is currently supported")

    for part in _children(root, "part"):
        current_part_id = part.attrib.get("id", "part")
        if current_part_id != part_id:
            continue

        divisions = 1
        absolute_quarters = 0.0
        measures: list[dict] = []

        for measure_index, measure in enumerate(_children(part, "measure"), start=1):
            number = measure.attrib.get("number", str(measure_index))
            cursor = 0
            maximum = 0
            last_note_start = 0

            for item in measure:
                kind = _local(item.tag)
                if kind == "attributes":
                    div_text = _text(item, "divisions")
                    if div_text:
                        divisions = max(1, int(div_text))
                    continue
                if kind == "backup":
                    cursor -= int(_text(item, "duration", "0") or "0")
                    continue
                if kind == "forward":
                    cursor += int(_text(item, "duration", "0") or "0")
                    maximum = max(maximum, cursor)
                    continue
                if kind != "note":
                    continue

                duration = int(_text(item, "duration", "0") or "0")
                is_chord = _child(item, "chord") is not None
                start = last_note_start if is_chord else cursor
                if not is_chord:
                    last_note_start = start
                    cursor += duration
                maximum = max(maximum, start + duration)

            duration_quarters = maximum / divisions
            measures.append(
                {
                    "measure": number,
                    "start_quarters": absolute_quarters,
                    "duration_quarters": duration_quarters,
                    "end_quarters": absolute_quarters + duration_quarters,
                }
            )
            absolute_quarters += duration_quarters

        return {
            "source": str(path),
            "part_id": part_id,
            "measures": measures,
        }

    raise ValueError(f"Part not found: {part_id}")



def inspect_cross_staff_segments(
    path: Path,
    measures: list[str],
    part_id: str | None = None,
    group_size: int = 7,
) -> dict:
    if not measures:
        raise ValueError("At least one measure number is required")
    if group_size < 2:
        raise ValueError("group_size must be at least 2")

    root = parse_root(path)
    if _local(root.tag) != "score-partwise":
        raise ValueError("Only score-partwise MusicXML is currently supported")

    requested = set(measures)
    results: list[dict] = []

    for part in _children(root, "part"):
        current_part_id = part.attrib.get("id", "part")
        if part_id is not None and current_part_id != part_id:
            continue

        divisions = 1
        beats = 4
        beat_type = 4

        for measure_index, measure in enumerate(_children(part, "measure"), start=1):
            number = measure.attrib.get("number", str(measure_index))

            for attributes in _children(measure, "attributes"):
                div_text = _text(attributes, "divisions")
                if div_text:
                    divisions = max(1, int(div_text))
                time = _child(attributes, "time")
                if time is not None:
                    beats = int(_text(time, "beats", "4") or "4")
                    beat_type = int(_text(time, "beat-type", "4") or "4")

            if number not in requested:
                continue

            cursor = 0
            maximum = 0
            last_note_start = 0
            backup_count = 0
            backup_total = 0
            forward_count = 0
            forward_total = 0
            boundaries: list[dict] = []
            segments: list[dict] = []
            current_segment: dict | None = None

            def flush_segment(
                *,
                divisions: int = divisions,
                segments: list[dict] = segments,
            ) -> None:
                nonlocal current_segment
                if current_segment is None:
                    return

                advance_count = current_segment["advance_note_count"]
                current_segment["exact_grouping"] = (
                    advance_count >= group_size
                    and advance_count % group_size == 0
                )
                current_segment["full_group_count"] = advance_count // group_size
                current_segment["remainder_notes"] = advance_count % group_size
                current_segment["span_quarters"] = (
                    current_segment["end_div"] - current_segment["start_div"]
                ) / divisions
                current_segment["start_quarters"] = (
                    current_segment.pop("start_div") / divisions
                )
                current_segment["end_quarters"] = (
                    current_segment.pop("end_div") / divisions
                )
                current_segment["duration_quarter_counts"] = dict(
                    sorted(
                        current_segment["duration_quarter_counts"].items(),
                        key=lambda entry: float(entry[0]),
                    )
                )
                segments.append(current_segment)
                current_segment = None

            for item_index, item in enumerate(measure):
                kind = _local(item.tag)

                if kind == "attributes":
                    div_text = _text(item, "divisions")
                    if div_text:
                        divisions = max(1, int(div_text))
                    time = _child(item, "time")
                    if time is not None:
                        beats = int(_text(time, "beats", "4") or "4")
                        beat_type = int(_text(time, "beat-type", "4") or "4")
                    continue

                if kind == "backup":
                    flush_segment()
                    duration = int(_text(item, "duration", "0") or "0")
                    before = cursor
                    cursor -= duration
                    backup_count += 1
                    backup_total += duration
                    boundaries.append(
                        {
                            "index": item_index,
                            "kind": "backup",
                            "duration_quarters": duration / divisions,
                            "cursor_before_quarters": before / divisions,
                            "cursor_after_quarters": cursor / divisions,
                        }
                    )
                    continue

                if kind == "forward":
                    flush_segment()
                    duration = int(_text(item, "duration", "0") or "0")
                    before = cursor
                    cursor += duration
                    maximum = max(maximum, cursor)
                    forward_count += 1
                    forward_total += duration
                    boundaries.append(
                        {
                            "index": item_index,
                            "kind": "forward",
                            "duration_quarters": duration / divisions,
                            "cursor_before_quarters": before / divisions,
                            "cursor_after_quarters": cursor / divisions,
                        }
                    )
                    continue

                if kind != "note":
                    continue

                duration = int(_text(item, "duration", "0") or "0")
                is_chord = _child(item, "chord") is not None
                start = last_note_start if is_chord else cursor
                if not is_chord:
                    last_note_start = start
                    cursor += duration
                end = start + duration
                maximum = max(maximum, end)

                staff = int(_text(item, "staff", "1") or "1")
                voice = _text(item, "voice", "1") or "1"
                stream = (staff, voice)

                if current_segment is not None:
                    current_stream = (
                        current_segment["staff"],
                        current_segment["voice"],
                    )
                    if stream != current_stream:
                        flush_segment()

                if current_segment is None:
                    current_segment = {
                        "segment_index": len(segments),
                        "staff": staff,
                        "voice": voice,
                        "start_div": start,
                        "end_div": end,
                        "note_count": 0,
                        "advance_note_count": 0,
                        "chord_note_count": 0,
                        "rest_count": 0,
                        "duration_quarter_counts": {},
                    }

                current_segment["note_count"] += 1
                current_segment["end_div"] = max(current_segment["end_div"], end)
                if is_chord:
                    current_segment["chord_note_count"] += 1
                else:
                    current_segment["advance_note_count"] += 1
                if _child(item, "rest") is not None:
                    current_segment["rest_count"] += 1

                duration_key = f"{duration / divisions:g}"
                counts = current_segment["duration_quarter_counts"]
                counts[duration_key] = counts.get(duration_key, 0) + 1

            flush_segment()

            stream_transitions = 0
            for previous, current in zip(segments, segments[1:], strict=False):
                if (
                    previous["staff"] != current["staff"]
                    or previous["voice"] != current["voice"]
                ):
                    stream_transitions += 1

            expected = beats * (4 / beat_type)
            results.append(
                {
                    "part_id": current_part_id,
                    "measure": number,
                    "time_signature": f"{beats}/{beat_type}",
                    "divisions": divisions,
                    "expected_quarters": expected,
                    "serialized_max_quarters": maximum / divisions,
                    "final_cursor_quarters": cursor / divisions,
                    "group_size": group_size,
                    "backup_count": backup_count,
                    "backup_total_quarters": backup_total / divisions,
                    "forward_count": forward_count,
                    "forward_total_quarters": forward_total / divisions,
                    "segment_count": len(segments),
                    "stream_transition_count": stream_transitions,
                    "exact_group_segment_count": sum(
                        1 for segment in segments if segment["exact_grouping"]
                    ),
                    "boundaries": boundaries,
                    "segments": segments,
                }
            )

    found = {(item["part_id"], item["measure"]) for item in results}
    missing = []
    for measure in measures:
        if part_id is None:
            if not any(found_measure == measure for _, found_measure in found):
                missing.append(measure)
        elif (part_id, measure) not in found:
            missing.append(measure)

    return {
        "source": str(path),
        "requested_measures": measures,
        "part_id": part_id,
        "group_size": group_size,
        "missing_measures": missing,
        "measures": results,
    }
