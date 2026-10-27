from pathlib import Path

from sheet2midi.validation import validate_musicxml


ALIGNMENT_SCORE = """<?xml version="1.0" encoding="UTF-8"?>
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

TUPLET_SCORE = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Piano</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>6</divisions>
        <time><beats>3</beats><beat-type>4</beat-type></time>
      </attributes>
      <note><rest/><duration>18</duration></note>
    </measure>
    <measure number="2">
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>6</duration>
        <time-modification>
          <actual-notes>3</actual-notes>
          <normal-notes>2</normal-notes>
        </time-modification>
        <notations><tuplet type="start"/></notations>
      </note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>6</duration></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>6</duration></note>
      <note><pitch><step>F</step><octave>4</octave></pitch><duration>6</duration></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>6</duration></note>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>6</duration></note>
    </measure>
  </part>
</score-partwise>
"""


def test_validator_classifies_staff_divergence(
    tmp_path: Path,
) -> None:
    score = tmp_path / "alignment.musicxml"
    score.write_text(ALIGNMENT_SCORE, encoding="utf-8")

    report = validate_musicxml(score)

    assert len(report.diagnostics) == 1
    diagnostic = report.diagnostics[0]
    assert diagnostic.measure == "2"
    assert diagnostic.classification == "possible_staff_alignment_error"
    assert diagnostic.staff_durations == {"1": 6.0, "2": 3.0}


def test_validator_classifies_tuplet_metadata_as_irregular_candidate(
    tmp_path: Path,
) -> None:
    score = tmp_path / "tuplet.musicxml"
    score.write_text(TUPLET_SCORE, encoding="utf-8")

    report = validate_musicxml(score)

    assert len(report.diagnostics) == 1
    diagnostic = report.diagnostics[0]
    assert diagnostic.measure == "2"
    assert diagnostic.classification == "possible_irregular_passage"
    assert diagnostic.time_modification_count == 1
    assert diagnostic.tuplet_notation_count == 1
