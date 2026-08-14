from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .midi import render_midi
from .models import ConversionResult
from .musicxml import merge_scores
from .omr import get_backend
from .preprocess import prepare_pages
from .validation import validate_musicxml


def convert(
    source: Path,
    output_dir: Path,
    engine: str = "auto",
    track_mode: str = "staff",
) -> ConversionResult:
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(source)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    backend = get_backend(engine)

    with tempfile.TemporaryDirectory(prefix="sheet2midi-") as tmp:
        work = Path(tmp)
        pages = prepare_pages(source, work / "pages")
        recognized: list[Path] = []
        for index, page in enumerate(pages, start=1):
            page_output = work / "omr" / f"page-{index:04d}"
            recognized.append(backend.recognize(page, page_output))

        musicxml = merge_scores(recognized, output_dir / "score.musicxml")

    report = validate_musicxml(musicxml)
    validation_json = output_dir / "validation.json"
    validation_json.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    midi = render_midi(musicxml, output_dir / "score.mid", track_mode=track_mode)
    return ConversionResult(output_dir, musicxml, midi, validation_json)
