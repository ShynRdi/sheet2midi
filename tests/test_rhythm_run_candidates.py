from pathlib import Path

from sheet2midi.musicxml import inspect_rhythm_runs

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
      </attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>F</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
    </measure>
    <measure number="2">
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>1</duration><voice>1</voice><type>16th</type><staff>1</staff>
        <time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification>
        <notations><tuplet type="start"/></notations>
      </note>
      <note><pitch><step>D</step><octave>5</octave></pitch><duration>1</duration><voice>1</voice><type>16th</type><staff>1</staff></note>
      <note><pitch><step>E</step><octave>5</octave></pitch><duration>1</duration><voice>1</voice><type>16th</type><staff>1</staff></note>
      <note><pitch><step>F</step><octave>5</octave></pitch><duration>1</duration><voice>1</voice><type>16th</type><staff>1</staff></note>
      <note><pitch><step>G</step><octave>5</octave></pitch><duration>1</duration><voice>1</voice><type>16th</type><staff>1</staff></note>
    </measure>
    <measure number="3">
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>2</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>2</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>D</step><octave>5</octave></pitch><duration>2</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
    </measure>
  </part>
</score-partwise>
"""


def test_inspect_rhythm_runs_finds_short_runs_and_metadata(
    tmp_path: Path,
) -> None:
    score = tmp_path / "score.musicxml"
    score.write_text(SCORE, encoding="utf-8")

    result = inspect_rhythm_runs(score, ["1", "2", "3"], part_id="P1")

    by_measure = {item["measure"]: item for item in result["measures"]}

    m1 = by_measure["1"]
    assert m1["candidate_count"] == 1
    assert m1["candidates"][0]["candidate_kind"] == (
        "short_run_without_tuplet_metadata"
    )
    assert m1["candidates"][0]["note_count"] == 5
    assert m1["candidates"][0]["duration_quarters"] == 0.5

    m2 = by_measure["2"]
    assert m2["candidate_count"] == 1
    assert m2["candidates"][0]["candidate_kind"] == (
        "short_run_with_tuplet_metadata"
    )
    assert m2["candidates"][0]["has_tuplet_metadata"] is True
    assert m2["candidates"][0]["duration_quarters"] == 0.25

    assert by_measure["3"]["candidate_count"] == 0
