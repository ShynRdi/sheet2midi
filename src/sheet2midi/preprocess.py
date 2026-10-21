from __future__ import annotations

import math
import shutil
from pathlib import Path
from typing import Any


def _load_cv() -> tuple[Any, Any]:
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "Deskew preprocessing requires: pip install 'sheet2midi[preprocess]'"
        ) from exc
    return cv2, np


def _read_image(path: Path) -> Any:
    cv2, np = _load_cv()
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not decode image: {path}")
    return image


def _estimate_skew_from_image(image: Any, max_angle: float = 7.5) -> float:
    cv2, np = _load_cv()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape[:2]

    max_dimension = max(height, width)
    if max_dimension > 1800:
        scale = 1800.0 / max_dimension
        gray = cv2.resize(
            gray,
            (max(1, round(width * scale)), max(1, round(height * scale))),
            interpolation=cv2.INTER_AREA,
        )
        height, width = gray.shape[:2]

    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(
        blurred,
        50,
        150,
        apertureSize=3,
        L2gradient=True,
    )

    angles: list[float] = []
    threshold = max(80, round(width * 0.08))
    lines = cv2.HoughLines(
        edges,
        1,
        np.pi / 1800,
        threshold=threshold,
    )
    if lines is not None:
        for line in lines[:200]:
            _rho, theta = line[0]
            angle = math.degrees(float(theta)) - 90.0
            if -max_angle <= angle <= max_angle:
                angles.append(angle)

    if len(angles) < 3:
        segments = cv2.HoughLinesP(
            edges,
            1,
            np.pi / 720,
            threshold=max(40, round(width * 0.04)),
            minLineLength=max(40, round(width * 0.12)),
            maxLineGap=max(10, round(width * 0.03)),
        )
        if segments is not None:
            for segment in segments[:500]:
                x1, y1, x2, y2 = segment[0]
                angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
                if -max_angle <= angle <= max_angle:
                    angles.append(angle)

    if len(angles) < 3:
        return 0.0
    return float(np.median(np.asarray(angles, dtype=np.float32)))


def estimate_skew_angle(source: Path, max_angle: float = 7.5) -> float:
    """Estimate small page rotation from near-horizontal staff lines."""
    source = Path(source)
    return _estimate_skew_from_image(_read_image(source), max_angle=max_angle)


def deskew_image(
    source: Path,
    destination: Path,
    *,
    max_angle: float = 7.5,
    min_angle: float = 0.25,
) -> tuple[Path, float]:
    """Deskew one score image and return the output path plus detected angle."""
    cv2, _np = _load_cv()
    source = Path(source)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    image = _read_image(source)
    angle = _estimate_skew_from_image(image, max_angle=max_angle)

    if abs(angle) < min_angle:
        corrected = image
        angle = 0.0
    else:
        height, width = image.shape[:2]
        center = (width / 2.0, height / 2.0)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        cosine = abs(float(matrix[0, 0]))
        sine = abs(float(matrix[0, 1]))
        new_width = int(math.ceil((height * sine) + (width * cosine)))
        new_height = int(math.ceil((height * cosine) + (width * sine)))
        matrix[0, 2] += (new_width / 2.0) - center[0]
        matrix[1, 2] += (new_height / 2.0) - center[1]
        corrected = cv2.warpAffine(
            image,
            matrix,
            (new_width, new_height),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )

    success, encoded = cv2.imencode(".png", corrected)
    if not success:
        raise RuntimeError(f"Could not encode deskewed image: {destination}")
    encoded.tofile(str(destination))
    return destination, angle


def preprocess_page(source: Path, destination: Path, mode: str = "none") -> Path:
    """Prepare one rendered page for OMR."""
    if mode == "none":
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination
    if mode == "deskew":
        return deskew_image(source, destination)[0]
    raise ValueError("preprocess mode must be 'none' or 'deskew'")


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
