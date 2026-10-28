from pathlib import Path

from sheet2midi.musicxml import inspect_irregular_measures


SCORE = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Piano</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <time><beats>3</beats><beat-type>4</beat-type></time>
        <staves>2</staves>
      </attributes>
      <print new-system="yes"/>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>eighth</type>
        <beam number="1">begin</beam>
        <staff>1</staff>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>2</duration>
        <voice>1</voice>
        <type>eighth</type>
        <beam number="1">end</beam>
        <staff>1</staff>
      </note>
      <backup><duration>4</duration></backup>
      <note>
        <rest/>
        <duration>4</duration>
        <voice>5</voice>
        <type>quarter</type>
        <staff>2</staff>
      </note>
      <forward><duration>8</duration></forward>
    </measure>
  </part>
</score-partwise>
"""


def test_inspect_irregular_measures_summarizes_rhythmic_evidence(
    tmp_path: Path,
) -> None:
    score = tmp_path / "score.musicxml"
    score.write_text(SCORE, encoding="utf-8")

    result = inspect_irregular_measures(score, ["1"], part_id="P1")

    assert result["missing_measures"] == []
    measure = result["measures"][0]
    assert measure["time_signature"] == "3/4"
    assert measure["note_count"] == 3
    assert measure["rest_count"] == 1
    assert measure["note_type_counts"] == {"eighth": 2, "quarter": 1}
    assert measure["duration_quarter_counts"] == {"0.5": 2, "1": 1}
    assert measure["beam_counts"] == {"begin": 1, "end": 1}
    assert measure["backup_count"] == 1
    assert measure["backup_total_quarters"] == 1.0
    assert measure["forward_count"] == 1
    assert measure["forward_total_quarters"] == 2.0
    assert measure["staff_spans"]["1"]["span_quarters"] == 1.0
    assert measure["voice_spans"]["2:5"]["span_quarters"] == 1.0
    assert measure["independent_stream_totals_quarters"] == {
        "1:1": 1.0,
        "2:5": 1.0,
    }
    assert measure["print_markers"] == [
        {"new_system": "yes", "new_page": None}
    ]
