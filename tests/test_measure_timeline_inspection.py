from pathlib import Path

from sheet2midi.musicxml import inspect_measure_timelines

SCORE = """<?xml version="1.0" encoding="UTF-8"?>
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
        <duration>3</duration>
        <staff>1</staff>
      </note>
      <backup><duration>3</duration></backup>
      <note>
        <pitch><step>C</step><octave>3</octave></pitch>
        <duration>3</duration>
        <staff>2</staff>
      </note>
    </measure>
  </part>
</score-partwise>
"""


def test_inspect_measure_timelines_reports_backup_and_staff_positions(
    tmp_path: Path,
) -> None:
    score = tmp_path / "score.musicxml"
    score.write_text(SCORE, encoding="utf-8")

    report = inspect_measure_timelines(score, ["1"], part_id="P1")

    assert report["missing_measures"] == []
    measure = report["measures"][0]
    assert measure["maximum_quarters"] == 3
    assert measure["final_cursor_quarters"] == 3

    backups = [event for event in measure["events"] if event["kind"] == "backup"]
    assert backups == [
        {
            "index": 2,
            "kind": "backup",
            "duration_quarters": 3.0,
            "cursor_before_quarters": 3.0,
            "cursor_after_quarters": 0.0,
        }
    ]

    notes = [event for event in measure["events"] if event["kind"] == "note"]
    assert notes[0]["staff"] == 1
    assert notes[0]["start_quarters"] == 0
    assert notes[1]["staff"] == 2
    assert notes[1]["start_quarters"] == 0
