from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from pathlib import Path

import mido

from .models import KeySignatureEvent, NoteEvent, TempoEvent, TimeSignatureEvent
from .musicxml import (
    inspect_measure_offsets,
    inspect_rhythm_group_hypotheses,
    parse_events,
)
from .validation import validate_musicxml

TICKS_PER_BEAT = 480


_PROGRAMS = {
    "piano": 0,
    "violin": 40,
    "viola": 41,
    "cello": 42,
    "contrabass": 43,
    "bass": 43,
    "flute": 73,
    "oboe": 68,
    "clarinet": 71,
    "bassoon": 70,
    "trumpet": 56,
    "trombone": 57,
    "horn": 60,
    "guitar": 24,
    "organ": 19,
    "soprano": 52,
    "alto": 52,
    "tenor": 52,
    "choir": 52,
    "voice": 52,
    "vocal": 52,
}

_MAJOR_KEYS = {
    -7: "Cb",
    -6: "Gb",
    -5: "Db",
    -4: "Ab",
    -3: "Eb",
    -2: "Bb",
    -1: "F",
    0: "C",
    1: "G",
    2: "D",
    3: "A",
    4: "E",
    5: "B",
    6: "F#",
    7: "C#",
}
_MINOR_KEYS = {
    -7: "Abm",
    -6: "Ebm",
    -5: "Bbm",
    -4: "Fm",
    -3: "Cm",
    -2: "Gm",
    -1: "Dm",
    0: "Am",
    1: "Em",
    2: "Bm",
    3: "F#m",
    4: "C#m",
    5: "G#m",
    6: "D#m",
    7: "A#m",
}


def _program_for(name: str) -> int:
    lowered = name.lower()
    for needle, program in _PROGRAMS.items():
        if needle in lowered:
            return program
    return 0


def _staff_name(part_name: str, staff: int, staff_count: int) -> str:
    if staff_count <= 1:
        return part_name
    if "piano" in part_name.lower() and staff == 1:
        return f"{part_name} - Right Hand"
    if "piano" in part_name.lower() and staff == 2:
        return f"{part_name} - Left Hand"
    return f"{part_name} - Staff {staff}"


def _add_absolute_events(
    track: mido.MidiTrack,
    events: list[tuple[int, int, mido.Message]],
) -> None:
    previous = 0
    for tick, _order, message in sorted(events, key=lambda item: (item[0], item[1])):
        message.time = max(0, tick - previous)
        track.append(message)
        previous = tick


def _write_conductor(
    midi: mido.MidiFile,
    tempos: list[TempoEvent],
    signatures: list[TimeSignatureEvent],
    keys: list[KeySignatureEvent],
) -> None:
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.append(mido.MetaMessage("track_name", name="Conductor", time=0))
    events: list[tuple[int, int, mido.Message]] = []
    for event in tempos:
        tick = round(event.start_quarters * TICKS_PER_BEAT)
        events.append(
            (tick, 0, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(event.bpm)))
        )
    for event in signatures:
        tick = round(event.start_quarters * TICKS_PER_BEAT)
        events.append(
            (
                tick,
                1,
                mido.MetaMessage(
                    "time_signature",
                    numerator=event.numerator,
                    denominator=event.denominator,
                ),
            )
        )
    for event in keys:
        key_map = _MINOR_KEYS if event.mode.lower().startswith("min") else _MAJOR_KEYS
        if event.fifths in key_map:
            tick = round(event.start_quarters * TICKS_PER_BEAT)
            events.append(
                (tick, 2, mido.MetaMessage("key_signature", key=key_map[event.fifths]))
            )
    _add_absolute_events(track, events)



def _apply_explicit_tuplet_previews(
    musicxml: Path,
    notes: list[NoteEvent],
    tempos: list[TempoEvent],
    signatures: list[TimeSignatureEvent],
    keys: list[KeySignatureEvent],
    previews: list[tuple[str, str]],
    group_size: int,
    in_space_of: int,
) -> tuple[
    list[NoteEvent],
    list[TempoEvent],
    list[TimeSignatureEvent],
    list[KeySignatureEvent],
]:
    if group_size < 2:
        raise ValueError("group_size must be at least 2")
    if in_space_of < 1 or in_space_of >= group_size:
        raise ValueError("in_space_of must be between 1 and group_size - 1")

    scale = in_space_of / group_size
    preview_specs: list[dict] = []

    for part_id, measure_number in previews:
        report = inspect_rhythm_group_hypotheses(
            musicxml,
            [measure_number],
            part_id=part_id,
            group_size=group_size,
        )
        if report["missing_measures"]:
            raise ValueError(
                f"Tuplet preview measure not found: {part_id}:{measure_number}"
            )

        measure_report = report["measures"][0]
        exact = [
            hypothesis
            for hypothesis in measure_report["hypotheses"]
            if hypothesis["exact_grouping"]
        ]
        if len(exact) != 1:
            raise ValueError(
                "Tuplet preview requires exactly one exact grouping candidate in "
                f"{part_id}:{measure_number}; found {len(exact)}"
            )

        hypothesis = exact[0]
        offsets = inspect_measure_offsets(musicxml, part_id)
        measure_offset = next(
            (
                item
                for item in offsets["measures"]
                if item["measure"] == measure_number
            ),
            None,
        )
        if measure_offset is None:
            raise ValueError(
                f"Tuplet preview measure offset not found: {part_id}:{measure_number}"
            )

        original_start = (
            measure_offset["start_quarters"] + hypothesis["start_quarters"]
        )
        original_end = measure_offset["start_quarters"] + hypothesis["end_quarters"]
        preview_specs.append(
            {
                "part_id": part_id,
                "measure": measure_number,
                "staff": int(hypothesis["staff"]),
                "voice": str(hypothesis["voice"]),
                "original_start": original_start,
                "original_end": original_end,
            }
        )

    preview_specs.sort(key=lambda item: item["original_start"])

    transformed_notes = list(notes)
    transformed_tempos = list(tempos)
    transformed_signatures = list(signatures)
    transformed_keys = list(keys)
    cumulative_shift = 0.0

    for spec in preview_specs:
        part_id = spec["part_id"]
        measure_number = spec["measure"]
        staff = spec["staff"]
        voice = spec["voice"]
        run_start = spec["original_start"] - cumulative_shift
        run_end = spec["original_end"] - cumulative_shift
        run_span = run_end - run_start
        new_span = run_span * scale
        shift = run_span - new_span

        overlaps = [
            note
            for note in transformed_notes
            if not (
                note.part_id == part_id
                and note.staff == staff
                and note.voice == voice
                and run_start <= note.start_quarters < run_end
            )
            and note.start_quarters < run_end
            and (note.start_quarters + note.duration_quarters) > run_start
        ]
        if overlaps:
            sample = overlaps[0]
            raise ValueError(
                "Tuplet preview rejected because another note overlaps the candidate "
                f"run in {part_id}:{measure_number}: "
                f"{sample.part_id}/staff{sample.staff}/voice{sample.voice}"
            )

        updated: list[NoteEvent] = []
        for note in transformed_notes:
            if (
                note.part_id == part_id
                and note.staff == staff
                and note.voice == voice
                and run_start <= note.start_quarters < run_end
            ):
                relative_start = note.start_quarters - run_start
                updated.append(
                    replace(
                        note,
                        start_quarters=run_start + relative_start * scale,
                        duration_quarters=note.duration_quarters * scale,
                    )
                )
            elif note.start_quarters >= run_end:
                updated.append(
                    replace(
                        note,
                        start_quarters=note.start_quarters - shift,
                    )
                )
            else:
                updated.append(note)

        transformed_notes = updated
        transformed_tempos = [
            replace(
                event,
                start_quarters=(
                    event.start_quarters - shift
                    if event.start_quarters >= run_end
                    else event.start_quarters
                ),
            )
            for event in transformed_tempos
        ]
        transformed_signatures = [
            replace(
                event,
                start_quarters=(
                    event.start_quarters - shift
                    if event.start_quarters >= run_end
                    else event.start_quarters
                ),
            )
            for event in transformed_signatures
        ]
        transformed_keys = [
            replace(
                event,
                start_quarters=(
                    event.start_quarters - shift
                    if event.start_quarters >= run_end
                    else event.start_quarters
                ),
            )
            for event in transformed_keys
        ]
        cumulative_shift += shift

    return (
        transformed_notes,
        transformed_tempos,
        transformed_signatures,
        transformed_keys,
    )

def render_midi(
    musicxml: Path,
    output: Path,
    track_mode: str = "staff",
    repair_staff_serialization: bool = False,
    tuplet_previews: list[tuple[str, str]] | None = None,
    tuplet_group_size: int = 7,
    tuplet_in_space_of: int = 6,
) -> Path:
    if track_mode not in {"staff", "part"}:
        raise ValueError("track_mode must be 'staff' or 'part'")

    repair_measures: set[tuple[str, str]] = set()
    if repair_staff_serialization:
        report = validate_musicxml(musicxml)
        repair_measures = {
            (diagnostic.part_id, diagnostic.measure)
            for diagnostic in report.diagnostics
            if diagnostic.classification == "possible_staff_serialization_error"
        }

    notes, tempos, signatures, keys = parse_events(
        musicxml,
        repair_serialized_measures=repair_measures,
    )
    if tuplet_previews:
        notes, tempos, signatures, keys = _apply_explicit_tuplet_previews(
            musicxml,
            notes,
            tempos,
            signatures,
            keys,
            tuplet_previews,
            tuplet_group_size,
            tuplet_in_space_of,
        )
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    _write_conductor(midi, tempos, signatures, keys)

    staves_by_part: dict[str, set[int]] = defaultdict(set)
    part_names: dict[str, str] = {}
    for note in notes:
        staves_by_part[note.part_id].add(note.staff)
        part_names[note.part_id] = note.part_name

    grouped: dict[tuple[str, int | None], list[NoteEvent]] = defaultdict(list)
    for note in notes:
        key = (note.part_id, note.staff if track_mode == "staff" else None)
        grouped[key].append(note)

    for (part_id, staff), group in sorted(grouped.items(), key=lambda item: str(item[0])):
        part_name = part_names[part_id]
        staff_count = len(staves_by_part[part_id])
        name = part_name if staff is None else _staff_name(part_name, staff, staff_count)
        track = mido.MidiTrack()
        midi.tracks.append(track)
        safe_name = name.encode("ascii", "replace").decode()
        track.append(mido.MetaMessage("track_name", name=safe_name, time=0))
        track.append(
            mido.Message("program_change", program=_program_for(part_name), time=0)
        )

        events: list[tuple[int, int, mido.Message]] = []
        for note in group:
            start = round(note.start_quarters * TICKS_PER_BEAT)
            end = round((note.start_quarters + note.duration_quarters) * TICKS_PER_BEAT)
            events.append(
                (
                    start,
                    1,
                    mido.Message("note_on", note=note.pitch, velocity=note.velocity),
                )
            )
            events.append(
                (end, 0, mido.Message("note_off", note=note.pitch, velocity=0))
            )
        _add_absolute_events(track, events)

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    midi.save(output)
    return output
