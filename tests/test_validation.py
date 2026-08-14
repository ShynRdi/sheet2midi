from pathlib import Path

from sheet2midi.validation import validate_musicxml


def test_validator_flags_short_non_first_measure(tmp_path: Path) -> None:
    xml = """<score-partwise version="4.0">
    <part-list><score-part id="P1"><part-name>Voice</part-name></score-part></part-list>
    <part id="P1">
      <measure number="1"><attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><note><rest/><duration>4</duration></note></measure>
      <measure number="2"><note><rest/><duration>3</duration></note></measure>
    </part></score-partwise>"""
    source = tmp_path / "bad.musicxml"
    source.write_text(xml)
    report = validate_musicxml(source)
    assert report.valid_xml is True
    assert [warning.code for warning in report.warnings] == ["measure_duration_mismatch"]
