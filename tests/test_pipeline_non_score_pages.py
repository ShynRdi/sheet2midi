import json
from pathlib import Path

import pytest

from sheet2midi.models import ValidationReport
from sheet2midi.omr.base import NoMusicDetectedError
from sheet2midi.pipeline import convert


class FakeBackend:
    def __init__(self, non_score_pages: set[str]) -> None:
        self.non_score_pages = non_score_pages

    def recognize(self, image: Path, output_dir: Path) -> Path:
        if image.name in self.non_score_pages:
            raise NoMusicDetectedError(f"No musical staff detected in {image}")

        output_dir.mkdir(parents=True, exist_ok=True)
        result = output_dir / f"{image.stem}.musicxml"
        result.write_text("<score-partwise version=\"4.0\"/>", encoding="utf-8")
        return result


def _install_pipeline_stubs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    backend: FakeBackend,
    page_names: list[str],
) -> None:
    pages = []
    for name in page_names:
        page = tmp_path / name
        page.write_bytes(b"image")
        pages.append(page)

    monkeypatch.setattr(
        "sheet2midi.pipeline.prepare_pages",
        lambda source, output_dir: pages,
    )
    monkeypatch.setattr("sheet2midi.pipeline.get_backend", lambda engine: backend)

    def fake_merge_scores(sources: list[Path], destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            "<score-partwise version=\"4.0\"/>",
            encoding="utf-8",
        )
        return destination

    monkeypatch.setattr("sheet2midi.pipeline.merge_scores", fake_merge_scores)
    monkeypatch.setattr(
        "sheet2midi.pipeline.normalize_musicxml",
        lambda source, destination: destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        or destination.write_text(
            source.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        or destination,
    )
    monkeypatch.setattr(
        "sheet2midi.pipeline.validate_musicxml",
        lambda source: ValidationReport(valid_xml=True, score_type="score-partwise"),
    )

    def fake_render_midi(
        source: Path,
        destination: Path,
        track_mode: str,
    ) -> Path:
        destination.write_bytes(b"MThd")
        return destination

    monkeypatch.setattr("sheet2midi.pipeline.render_midi", fake_render_midi)


def test_convert_skips_non_score_pages_and_keeps_music_pages(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "mixed.pdf"
    source.write_bytes(b"pdf")
    output = tmp_path / "out"
    backend = FakeBackend({"page-0002.png"})

    _install_pipeline_stubs(
        monkeypatch,
        tmp_path,
        backend,
        ["page-0001.png", "page-0002.png", "page-0003.png"],
    )

    result = convert(source, output, keep_intermediates=True)

    assert result.musicxml.exists()
    assert result.midi.exists()
    assert (output / "intermediates" / "page-0001.musicxml").exists()
    assert not (output / "intermediates" / "page-0002.musicxml").exists()
    assert (output / "intermediates" / "page-0003.musicxml").exists()

    skipped = json.loads(
        (output / "intermediates" / "skipped-pages.json").read_text(
            encoding="utf-8"
        )
    )
    assert skipped[0]["page"] == 2
    assert skipped[0]["reason"] == "no_musical_staff_detected"


def test_convert_fails_when_every_page_has_no_music(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "text-only.pdf"
    source.write_bytes(b"pdf")
    output = tmp_path / "out"
    backend = FakeBackend({"page-0001.png", "page-0002.png"})

    _install_pipeline_stubs(
        monkeypatch,
        tmp_path,
        backend,
        ["page-0001.png", "page-0002.png"],
    )

    with pytest.raises(NoMusicDetectedError, match="any page"):
        convert(source, output, keep_intermediates=True)

    skipped = json.loads(
        (output / "intermediates" / "skipped-pages.json").read_text(
            encoding="utf-8"
        )
    )
    assert [item["page"] for item in skipped] == [1, 2]
