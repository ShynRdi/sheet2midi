from pathlib import Path

from sheet2midi.musicxml import parse_events
from sheet2midi.validation import validate_musicxml

SERIALIZED = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Piano</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <time><beats>3</beats><beat-type>4</beat-type></time>
        <staves>2</staves>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>3</duration><voice>1</voice><staff>1</staff>
      </note>
      <backup><duration>3</duration></backup>
      <note>
        <pitch><step>C</step><octave>3</octave></pitch>
        <duration>3</duration><voice>5</voice><staff>2</staff>
      </note>
    </measure>
    <measure number="2">
      <note>
        <pitch><step>D</step><octave>3</octave></pitch>
        <duration>2</duration><voice>5</voice><staff>2</staff>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>2</duration><voice>1</voice><staff>1</staff>
      </note>
      <note>
        <pitch><step>E</step><octave>3</octave></pitch>
        <duration>2</duration><voice>5</voice><staff>2</staff>
      </note>
    </measure>
  </part>
</score-partwise>
"""


def test_serialization_repair_uses_independent_staff_voice_timelines(
    tmp_path: Path,
) -> None:
    source = tmp_path / "serialized.musicxml"
    source.write_text(SERIALIZED, encoding="utf-8")

    report = validate_musicxml(source)
    repair_measures = {
        (diagnostic.part_id, diagnostic.measure)
        for diagnostic in report.diagnostics
        if diagnostic.classification == "possible_staff_serialization_error"
    }
    assert repair_measures == {("P1", "2")}

    normal_notes, *_ = parse_events(source)
    repaired_notes, *_ = parse_events(
        source,
        repair_serialized_measures=repair_measures,
    )

    normal_measure_two = [note for note in normal_notes if note.start_quarters >= 3]
    repaired_measure_two = [note for note in repaired_notes if note.start_quarters >= 3]

    normal_by_pitch = {note.pitch: note.start_quarters for note in normal_measure_two}
    repaired_by_pitch = {note.pitch: note.start_quarters for note in repaired_measure_two}

    assert normal_by_pitch[62] == 3.0
    assert normal_by_pitch[62 + 12] == 5.0
    assert normal_by_pitch[64] == 7.0

    assert repaired_by_pitch[62] == 3.0
    assert repaired_by_pitch[62 + 12] == 3.0
    assert repaired_by_pitch[64] == 5.0
