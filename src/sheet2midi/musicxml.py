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


def parse_events(path: Path) -> tuple[
    list[NoteEvent], list[TempoEvent], list[TimeSignatureEvent], list[KeySignatureEvent]
]:
    root = parse_root(path)
    if _local(root.tag) != "score-partwise":
        raise ValueError("Only score-partwise MusicXML is currently supported")

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
            cursor_div = 0
            max_div = 0
            last_note_start = 0

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
                    start_div = last_note_start if is_chord else cursor_div
                    if not is_chord:
                        last_note_start = start_div

                    pitch = pitch_to_midi(item, transpose)
                    if pitch is not None and duration_div > 0:
                        staff = int(_text(item, "staff", "1") or "1")
                        voice = _text(item, "voice", "1") or "1"
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

                    if not is_chord:
                        cursor_div += duration_div
                        max_div = max(max_div, cursor_div)

            absolute_quarters += max_div / divisions

        notes.extend(open_ties.values())

    if not tempos:
        tempos.append(TempoEvent(0.0, 120.0))
    return notes, sorted(tempos, key=lambda x: x.start_quarters), signatures, keys
