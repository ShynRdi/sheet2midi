from __future__ import annotations

import shutil
from pathlib import Path


def prepare_pages(source: Path, workdir: Path, scale: float = 2.0) -> list[Path]:
    source = Path(source)
    workdir.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() != ".pdf":
        destination = workdir / source.name
        shutil.copy2(source, destination)
        return [destination]

    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise RuntimeError(
            "PDF input requires the optional dependency: pip install 'sheet2midi[pdf]'"
        ) from exc

    pdf = pdfium.PdfDocument(str(source))
    pages: list[Path] = []
    for index in range(len(pdf)):
        page = pdf[index]
        bitmap = page.render(scale=scale)
        image = bitmap.to_pil()
        output = workdir / f"page-{index + 1:04d}.png"
        image.save(output)
        pages.append(output)
        page.close()
    pdf.close()
    return pages
