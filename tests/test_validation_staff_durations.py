from pathlib import Path

from sheet2midi.validation import validate_musicxml

SCORE = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1">
      <part-name>Piano</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <time>
          <beats>3</beats>
          <beat-type>4</beat-type>
        </time>
        <staves>2</staves>
      </attributes>
      <note><duration>3</duration><staff>1</staff></note>
      <backup><duration>3</duration></backup>
      <note><duration>3</duration><staff>2</staff></note>
    </measure>
    <measure number="2">
      <note><duration>6</duration><staff>1</staff></note>
      <backup><duration>6</duration></backup>
      <note><duration>3</duration><staff>2</staff></note>
    </measure>
  </part>
</score-partwise>
"""


def test_validator_reports_staff_specific_duration_mismatch(
    tmp_path: Path,
) -> None:
    score = tmp_path / "staff-mismatch.musicxml"
    score.write_text(SCORE, encoding="utf-8")

    report = validate_musicxml(score)

    assert report.valid_xml
    staff_warnings = [
        warning
        for warning in report.warnings
        if warning.code == "staff_duration_mismatch"
    ]

    assert len(staff_warnings) == 1
    assert staff_warnings[0].part_id == "P1"
    assert staff_warnings[0].measure == "2"
    assert staff_warnings[0].message == (
        "Staff 1 duration is 6 quarter notes; expected 3"
    )
