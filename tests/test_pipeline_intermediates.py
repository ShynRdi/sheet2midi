from pathlib import Path

from sheet2midi.pipeline import convert


class FakeBackend:
    def recognize(self, source: Path, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        result = output_dir / "page.musicxml"
        result.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="4.0">
  <part-list>
    <score-part id="P1"><part-name>Piano</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
      </attributes>
      <note><rest/><duration>4</duration></note>
    </measure>
  </part>
</score-partwise>
""",
            encoding="utf-8",
        )
        return result


def test_convert_keeps_per_page_musicxml_when_requested(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "score.png"
    source.write_bytes(b"image")

    monkeypatch.setattr(
        "sheet2midi.pipeline.prepare_pages",
        lambda source, output_dir: [source],
    )
    monkeypatch.setattr(
        "sheet2midi.pipeline.get_backend",
        lambda engine: FakeBackend(),
    )

    output = tmp_path / "out"
    convert(source, output, keep_intermediates=True)

    intermediate = output / "intermediates" / "page-0001.musicxml"
    assert intermediate.exists()
    assert "score-partwise" in intermediate.read_text(encoding="utf-8")
