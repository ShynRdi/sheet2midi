#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / "benchmarks/corpus-v2"
DIVISIONS = 4


def add_text(parent: ET.Element, tag: str, text: str, **attrs: str) -> ET.Element:
    node = ET.SubElement(parent, tag, attrs)
    node.text = text
    return node


def add_attributes(
    measure: ET.Element,
    *,
    staves: int = 1,
    clefs: tuple[str, ...] = ("G",),
) -> None:
    attrs = ET.SubElement(measure, "attributes")
    add_text(attrs, "divisions", str(DIVISIONS))
    key = ET.SubElement(attrs, "key")
    add_text(key, "fifths", "0")
    time = ET.SubElement(attrs, "time")
    add_text(time, "beats", "4")
    add_text(time, "beat-type", "4")
    if staves > 1:
        add_text(attrs, "staves", str(staves))
    for index, sign in enumerate(clefs, start=1):
        kwargs = {"number": str(index)} if staves > 1 else {}
        clef = ET.SubElement(attrs, "clef", kwargs)
        add_text(clef, "sign", sign)
        add_text(clef, "line", "2" if sign == "G" else "4")


def add_note(
    measure: ET.Element,
    step: str | None,
    octave: int | None,
    duration: int,
    note_type: str,
    *,
    staff: int = 1,
    voice: str = "1",
    chord: bool = False,
    lyric: str | None = None,
) -> None:
    note = ET.SubElement(measure, "note")
    if chord:
        ET.SubElement(note, "chord")
    if step is None:
        ET.SubElement(note, "rest")
    else:
        pitch = ET.SubElement(note, "pitch")
        add_text(pitch, "step", step)
        add_text(pitch, "octave", str(octave))
    add_text(note, "duration", str(duration))
    add_text(note, "voice", voice)
    add_text(note, "type", note_type)
    if staff != 1:
        add_text(note, "staff", str(staff))
    if lyric:
        lyric_node = ET.SubElement(note, "lyric")
        add_text(lyric_node, "text", lyric)


def backup(measure: ET.Element, duration: int = 16) -> None:
    node = ET.SubElement(measure, "backup")
    add_text(node, "duration", str(duration))


def new_score(parts: list[tuple[str, str]]) -> tuple[ET.Element, dict[str, ET.Element]]:
    root = ET.Element("score-partwise", {"version": "4.0"})
    part_list = ET.SubElement(root, "part-list")
    output: dict[str, ET.Element] = {}
    for part_id, name in parts:
        score_part = ET.SubElement(part_list, "score-part", {"id": part_id})
        add_text(score_part, "part-name", name)
        output[part_id] = ET.SubElement(root, "part", {"id": part_id})
    return root, output


def measure(part: ET.Element, number: int, **attrs) -> ET.Element:
    node = ET.SubElement(part, "measure", {"number": str(number)})
    if number == 1:
        add_attributes(node, **attrs)
    return node


def build_piano() -> ET.Element:
    root, parts = new_score([("P1", "Piano")])
    p = parts["P1"]
    patterns = [
        (("C", 5), ("E", 5), ("C", 3)),
        (("D", 5), ("F", 5), ("G", 2)),
        (("E", 5), ("G", 5), ("A", 2)),
        (("F", 5), ("A", 5), ("F", 2)),
    ]
    for i, (melody, harmony, bass) in enumerate(patterns, start=1):
        m = measure(p, i, staves=2, clefs=("G", "F"))
        add_note(m, *melody, 4, "quarter", staff=1)
        add_note(m, *harmony, 4, "quarter", staff=1, chord=True)
        add_note(m, "G", 5, 4, "quarter", staff=1)
        add_note(m, "E", 5, 8, "half", staff=1)
        backup(m)
        add_note(m, *bass, 8, "half", staff=2)
        add_note(m, "G", 2, 8, "half", staff=2)
    return root


def build_duet() -> ET.Element:
    root, parts = new_score([("V", "Violin"), ("C", "Cello")])
    violin = [("G", 4), ("A", 4), ("B", 4), ("C", 5)]
    cello = [("C", 3), ("D", 3), ("E", 3), ("F", 3)]
    for i in range(1, 5):
        vm = measure(parts["V"], i, clefs=("G",))
        cm = measure(parts["C"], i, clefs=("F",))
        for step, octv in (violin[i - 1], ("D", 5), ("E", 5), ("F", 5)):
            add_note(vm, step, octv, 4, "quarter")
        add_note(cm, *cello[i - 1], 8, "half")
        add_note(cm, "G", 2, 8, "half")
    return root


def build_vocal_piano() -> ET.Element:
    root, parts = new_score([("V", "Voice"), ("P", "Piano")])
    syllables = ["Sing", "the", "line", "now"]
    for i in range(1, 5):
        vm = measure(parts["V"], i, clefs=("G",))
        for j, step in enumerate(("C", "D", "E", "G")):
            add_note(vm, step, 4, 4, "quarter", lyric=syllables[j])
        pm = measure(parts["P"], i, staves=2, clefs=("G", "F"))
        add_note(pm, "C", 5, 8, "half", staff=1)
        add_note(pm, "E", 5, 8, "half", staff=1)
        backup(pm)
        add_note(pm, "C", 3, 16, "whole", staff=2)
    return root


def build_satb(with_piano: bool = False) -> ET.Element:
    defs = [("S", "Soprano"), ("A", "Alto"), ("T", "Tenor"), ("B", "Bass")]
    if with_piano:
        defs.append(("P", "Piano"))
    root, parts = new_score(defs)
    pitches = {"S": ("G", 4), "A": ("E", 4), "T": ("C", 4), "B": ("C", 3)}
    for i in range(1, 5):
        for pid in ("S", "A", "T", "B"):
            sign = "F" if pid == "B" else "G"
            m = measure(parts[pid], i, clefs=(sign,))
            step, octv = pitches[pid]
            add_note(m, step, octv, 8, "half")
            add_note(m, "D" if pid != "B" else "G", octv, 8, "half")
        if with_piano:
            pm = measure(parts["P"], i, staves=2, clefs=("G", "F"))
            add_note(pm, "C", 5, 4, "quarter", staff=1)
            add_note(pm, "E", 5, 4, "quarter", staff=1, chord=True)
            add_note(pm, "G", 5, 8, "half", staff=1)
            add_note(pm, "C", 5, 4, "quarter", staff=1)
            backup(pm)
            add_note(pm, "C", 3, 8, "half", staff=2)
            add_note(pm, "G", 2, 8, "half", staff=2)
    return root


def write_score(path: Path, root: ET.Element) -> None:
    ET.indent(root, space="  ")
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def main() -> None:
    outputs = {
        "piano-polyphonic.musicxml": build_piano(),
        "instrument-duet-v2.musicxml": build_duet(),
        "vocal-piano-v2.musicxml": build_vocal_piano(),
        "satb-v2.musicxml": build_satb(False),
        "choir-piano-v2.musicxml": build_satb(True),
    }
    target = ROOT / "ground_truth"
    for filename, score in outputs.items():
        path = target / filename
        write_score(path, score)
        print(path)

    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["cases"]) == len(outputs)


if __name__ == "__main__":
    main()
