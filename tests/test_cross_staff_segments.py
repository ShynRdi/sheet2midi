from pathlib import Path

from sheet2midi.musicxml import inspect_cross_staff_segments

SCORE = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Piano</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>2</divisions>
        <time><beats>3</beats><beat-type>4</beat-type></time>
        <staves>2</staves>
      </attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>F</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <backup><duration>7</duration></backup>
      <note><pitch><step>C</step><octave>3</octave></pitch><duration>2</duration><voice>5</voice><type>quarter</type><staff>2</staff></note>
      <note><pitch><step>G</step><octave>3</octave></pitch><duration>2</duration><voice>5</voice><type>quarter</type><staff>2</staff></note>
      <forward><duration>1</duration></forward>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
    </measure>
  </part>
</score-partwise>
"""


def test_inspect_cross_staff_segments_tracks_boundaries_and_exact_groups(
    tmp_path: Path,
) -> None:
    score = tmp_path / "score.musicxml"
    score.write_text(SCORE, encoding="utf-8")

    result = inspect_cross_staff_segments(
        score,
        ["1"],
        part_id="P1",
        group_size=7,
    )

    measure = result["measures"][0]
    assert measure["backup_count"] == 1
    assert measure["forward_count"] == 1
    assert measure["segment_count"] == 3
    assert measure["stream_transition_count"] == 2
    assert measure["exact_group_segment_count"] == 1

    first = measure["segments"][0]
    assert first["staff"] == 1
    assert first["voice"] == "1"
    assert first["advance_note_count"] == 7
    assert first["exact_grouping"] is True
    assert first["full_group_count"] == 1
    assert first["remainder_notes"] == 0

    second = measure["segments"][1]
    assert second["staff"] == 2
    assert second["voice"] == "5"
    assert second["advance_note_count"] == 2
    assert second["exact_grouping"] is False

    assert [boundary["kind"] for boundary in measure["boundaries"]] == [
        "backup",
        "forward",
    ]
