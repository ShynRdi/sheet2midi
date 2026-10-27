from pathlib import Path

from sheet2midi.validation import validate_musicxml_pages


PAGE_1 = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Piano</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <time><beats>3</beats><beat-type>4</beat-type></time>
      </attributes>
      <note><duration>3</duration></note>
    </measure>
    <measure number="2">
      <note><duration>3</duration></note>
    </measure>
  </part>
</score-partwise>
"""

PAGE_2 = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Piano</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <note><duration>3</duration></note>
    </measure>
    <measure number="2">
      <note><duration>6</duration></note>
    </measure>
  </part>
</score-partwise>
"""


def test_validate_pages_inherits_meter_and_maps_page_measure(
    tmp_path: Path,
) -> None:
    page_1 = tmp_path / "page-0001.musicxml"
    page_2 = tmp_path / "page-0002.musicxml"
    page_1.write_text(PAGE_1, encoding="utf-8")
    page_2.write_text(PAGE_2, encoding="utf-8")

    report = validate_musicxml_pages([page_1, page_2])

    assert report["warning_count"] == 1
    warning = report["warnings"][0]
    assert warning["code"] == "measure_duration_mismatch"
    assert warning["measure"] == "4"
    assert warning["page"] == 2
    assert warning["page_measure"] == "2"
    assert warning["message"] == "Measure duration is 6 quarter notes; expected 3"
