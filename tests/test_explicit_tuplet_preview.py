from pathlib import Path

import mido
import pytest

from sheet2midi.midi import render_midi

SAFE_SCORE = """<?xml version="1.0" encoding="UTF-8"?>
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
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>F</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
    </measure>
    <measure number="2">
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>2</duration><voice>1</voice><type>quarter</type><staff>1</staff></note>
    </measure>
  </part>
</score-partwise>
"""


OVERLAP_SCORE = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Piano</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>2</divisions>
        <time><beats>3</beats><beat-type>4</beat-type></time>
        <staves>2</staves>
      </attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>F</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice><type>eighth</type><staff>1</staff></note>
      <backup><duration>7</duration></backup>
      <note><pitch><step>C</step><octave>3</octave></pitch><duration>7</duration><voice>5</voice><type>half</type><staff>2</staff></note>
    </measure>
  </part>
</score-partwise>
"""


def _note_on_ticks(path: Path) -> list[int]:
    midi = mido.MidiFile(path)
    ticks = []
    for track in midi.tracks:
        absolute = 0
        for msg in track:
            absolute += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                ticks.append(absolute)
    return sorted(ticks)


def test_explicit_tuplet_preview_compresses_exact_run_and_shifts_later_notes(
    tmp_path: Path,
) -> None:
    score = tmp_path / "safe.musicxml"
    output = tmp_path / "preview.mid"
    score.write_text(SAFE_SCORE, encoding="utf-8")

    render_midi(
        score,
        output,
        tuplet_previews=[("P1", "1")],
        tuplet_group_size=7,
        tuplet_in_space_of=6,
    )

    ticks = _note_on_ticks(output)
    assert ticks[:7] == [0, 206, 411, 617, 823, 1029, 1234]
    assert ticks[7] == 1440


def test_explicit_tuplet_preview_rejects_overlapping_other_stream(
    tmp_path: Path,
) -> None:
    score = tmp_path / "overlap.musicxml"
    output = tmp_path / "preview.mid"
    score.write_text(OVERLAP_SCORE, encoding="utf-8")

    with pytest.raises(ValueError, match="overlaps the candidate run"):
        render_midi(
            score,
            output,
            tuplet_previews=[("P1", "1")],
            tuplet_group_size=7,
            tuplet_in_space_of=6,
        )
