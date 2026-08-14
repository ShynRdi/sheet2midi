from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class OMRBackend(ABC):
    name: str

    @abstractmethod
    def available(self) -> bool:
        """Return whether this backend can run in the current environment."""

    @abstractmethod
    def recognize(self, image: Path, output_dir: Path) -> Path:
        """Recognize one image and return a MusicXML or MXL file."""
