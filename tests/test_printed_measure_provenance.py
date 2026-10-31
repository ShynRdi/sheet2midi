from pathlib import Path

from sheet2midi.musicxml import inspect_printed_measure_provenance

SCORE = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Piano</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="36">
      <attributes>
        <divisions>2</divisions>
        <time><beats>3</beats><beat-type>4</beat-type></time>
      </attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>12</duration><voice>1</voice><type>whole</type><staff>1</staff></note>
    </measure>
    <measure number="37">
      <print new-system="yes"/>
      <attributes><divisions>2</divisions></attributes>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>12</duration><voice>1</voice><type>whole</type><staff>1</staff></note>
    </measure>
    <measure number="38">
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>6</duration><voice>1</voice><type>half</type><staff>1</staff></note>
    </measure>
  </part>
</score-partwise>
"""


def test_inspect_printed_measure_provenance_links_overfull_system_fragments(
    tmp_path: Path,
) -> None:
    score = tmp_path / "score.musicxml"
    score.write_text(SCORE, encoding="utf-8")

    result = inspect_printed_measure_provenance(
        score,
        ["36", "37", "38"],
        part_id="P1",
    )

    fragments = {item["measure"]: item for item in result["fragments"]}
    assert fragments["36"]["overfull"] is True
    assert fragments["37"]["overfull"] is True
    assert fragments["37"]["starts_new_system"] is True
    assert fragments["37"]["divisions_declared"] is True
    assert fragments["37"]["time_declared"] is False
    assert fragments["38"]["overfull"] is False

    links = {
        (item["from_measure"], item["to_measure"]): item
        for item in result["adjacency_links"]
    }
    assert links[("36", "37")]["classification"] == "strong_continuation_candidate"
    assert "both_adjacent_fragments_are_overfull" in links[("36", "37")]["reasons"]
    assert "current_fragment_starts_new_system" in links[("36", "37")]["reasons"]
    assert (
        "current_fragment_redeclares_context_without_new_meter"
        in links[("36", "37")]["reasons"]
    )
    assert links[("37", "38")]["classification"] == "weak_or_no_continuation_evidence"
    assert result["warning"].startswith("Continuation classifications")
