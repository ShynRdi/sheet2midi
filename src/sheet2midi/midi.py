from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import mido

from .models import KeySignatureEvent, NoteEvent, TempoEvent, TimeSignatureEvent
from .musicxml import parse_events

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


def render_midi(musicxml: Path, output: Path, track_mode: str = "staff") -> Path:
    if track_mode not in {"staff", "part"}:
        raise ValueError("track_mode must be 'staff' or 'part'")

    notes, tempos, signatures, keys = parse_events(musicxml)
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
