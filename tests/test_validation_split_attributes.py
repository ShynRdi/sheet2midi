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
        <divisions>2</divisions>
        <staves>2</staves>
      </attributes>

      <attributes>
        <time>
          <beats>3</beats>
          <beat-type>4</beat-type>
        </time>
      </attributes>

      <note><duration>2</duration></note>
      <note><duration>2</duration></note>
      <note><duration>2</duration></note>
    </measure>

    <measure number="2">
      <note><duration>2</duration></note>
      <note><duration>2</duration></note>
      <note><duration>2</duration></note>
    </measure>

    <measure number="3">
      <note><duration>2</duration></note>
      <note><duration>2</duration></note>
      <note><duration>2</duration></note>
      <note><duration>2</duration></note>
    </measure>
  </part>
</score-partwise>
"""


def test_validator_reads_time_signature_from_later_attributes_block(
    tmp_path: Path,
) -> None:
    score = tmp_path / "split-attributes.musicxml"
    score.write_text(SCORE, encoding="utf-8")

    report = validate_musicxml(score)

    assert report.valid_xml

    mismatches = [
        warning
        for warning in report.warnings
        if warning.code == "measure_duration_mismatch"
    ]

    assert len(mismatches) == 1
    assert mismatches[0].part_id == "P1"
    assert mismatches[0].measure == "3"
    assert mismatches[0].message == (
        "Measure duration is 4 quarter notes; expected 3"
    )
