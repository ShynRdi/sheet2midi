from pathlib import Path

import mido

from sheet2midi.midi import render_midi
from sheet2midi.musicxml import parse_events

PIANO = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <staves>2</staves>
      </attributes>
      <direction><sound tempo="96"/></direction>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>8</duration><voice>1</voice><staff>1</staff></note>
      <note><pitch><step>E</step><octave>5</octave></pitch><duration>8</duration><voice>1</voice><staff>1</staff></note>
      <backup><duration>16</duration></backup>
      <note><pitch><step>C</step><octave>3</octave></pitch><duration>16</duration><voice>1</voice><staff>2</staff></note>
    </measure>
  </part>
</score-partwise>
"""


def test_musicxml_reconstructs_piano_staves(tmp_path: Path) -> None:
    source = tmp_path / "piano.musicxml"
    source.write_text(PIANO)
    notes, tempos, signatures, keys = parse_events(source)
    assert [note.pitch for note in notes] == [72, 76, 48]
    assert {note.staff for note in notes} == {1, 2}
    assert tempos[0].bpm == 96
    assert signatures[0].numerator == 4
    assert keys[0].fifths == 0


def test_staff_mode_writes_separate_piano_tracks(tmp_path: Path) -> None:
    source = tmp_path / "piano.musicxml"
    source.write_text(PIANO)
    output = render_midi(source, tmp_path / "piano.mid", track_mode="staff")
    midi = mido.MidiFile(output)
    names = [
        message.name
        for track in midi.tracks
        for message in track
        if message.type == "track_name"
    ]
    assert names == ["Conductor", "Piano - Right Hand", "Piano - Left Hand"]


def test_part_mode_merges_piano_staves(tmp_path: Path) -> None:
    source = tmp_path / "piano.musicxml"
    source.write_text(PIANO)
    output = render_midi(source, tmp_path / "piano.mid", track_mode="part")
    midi = mido.MidiFile(output)
    names = [
        message.name
        for track in midi.tracks
        for message in track
        if message.type == "track_name"
    ]
    assert names == ["Conductor", "Piano"]
