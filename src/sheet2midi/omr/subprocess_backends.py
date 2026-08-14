from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .base import OMRBackend


def _find_output(directory: Path, before: set[Path] | None = None) -> Path:
    before = before or set()
    candidates = [
        path
        for pattern in ("*.musicxml", "*.mxl", "*.xml")
        for path in directory.rglob(pattern)
        if path not in before and "META-INF" not in path.parts
    ]
    if not candidates:
        raise RuntimeError(f"OMR backend produced no MusicXML/MXL in {directory}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


class HomrBackend(OMRBackend):
    name = "homr"

    def available(self) -> bool:
        return shutil.which("homr") is not None

    def recognize(self, image: Path, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        local_image = output_dir / image.name
        if image.resolve() != local_image.resolve():
            shutil.copy2(image, local_image)
        before = set(output_dir.rglob("*.musicxml")) | set(output_dir.rglob("*.mxl"))
        subprocess.run(["homr", str(local_image)], cwd=output_dir, check=True)
        return _find_output(output_dir, before)


class OemerBackend(OMRBackend):
    name = "oemer"

    def available(self) -> bool:
        return shutil.which("oemer") is not None

    def recognize(self, image: Path, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        before = set(output_dir.rglob("*.musicxml")) | set(output_dir.rglob("*.mxl"))
        subprocess.run(["oemer", str(image), "-o", str(output_dir)], check=True)
        return _find_output(output_dir, before)


class AudiverisBackend(OMRBackend):
    name = "audiveris"

    def available(self) -> bool:
        return shutil.which("audiveris") is not None

    def recognize(self, image: Path, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        before = set(output_dir.rglob("*.musicxml")) | set(output_dir.rglob("*.mxl"))
        subprocess.run(
            [
                "audiveris",
                "-batch",
                "-transcribe",
                "-export",
                "-output",
                str(output_dir),
                "--",
                str(image),
            ],
            check=True,
        )
        return _find_output(output_dir, before)
