from pathlib import Path

from sheet2midi.musicxml import inspect_rhythm_group_hypotheses

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
      </attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>F</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>A</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>B</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>F</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>A</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>B</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
    </measure>
    <measure number="2">
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>D</step><octave>5</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>E</step><octave>5</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>F</step><octave>5</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>G</step><octave>5</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>A</step><octave>5</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>B</step><octave>5</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>D</step><octave>5</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note><note><pitch><step>E</step><octave>5</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
    </measure>
  </part>
</score-partwise>
"""


def test_inspect_rhythm_group_hypotheses_distinguishes_exact_and_partial(
    tmp_path: Path,
) -> None:
    score = tmp_path / "score.musicxml"
    score.write_text(SCORE, encoding="utf-8")

    result = inspect_rhythm_group_hypotheses(
        score,
        ["1", "2"],
        part_id="P1",
        group_size=7,
    )

    by_measure = {item["measure"]: item for item in result["measures"]}

    exact = by_measure["1"]["hypotheses"][0]
    assert exact["note_count"] == 14
    assert exact["full_group_count"] == 2
    assert exact["remainder_notes"] == 0
    assert exact["exact_grouping"] is True
    assert exact["evidence"] == "exact_note_count_multiple_only"

    partial = by_measure["2"]["hypotheses"][0]
    assert partial["note_count"] == 10
    assert partial["full_group_count"] == 1
    assert partial["remainder_notes"] == 3
    assert partial["exact_grouping"] is False
    assert partial["evidence"] == "partial_note_count_match_only"
