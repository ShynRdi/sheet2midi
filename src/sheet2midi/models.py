from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class NoteEvent:
    part_id: str
    part_name: str
    staff: int
    voice: str
    pitch: int
    start_quarters: float
    duration_quarters: float
    velocity: int = 80


@dataclass(frozen=True)
class TempoEvent:
    start_quarters: float
    bpm: float


@dataclass(frozen=True)
class TimeSignatureEvent:
    start_quarters: float
    numerator: int
    denominator: int


@dataclass(frozen=True)
class KeySignatureEvent:
    start_quarters: float
    fifths: int
    mode: str = "major"


@dataclass
class ValidationWarning:
    code: str
    message: str
    part_id: str | None = None
    measure: str | None = None


@dataclass
class ValidationReport:
    valid_xml: bool = True
    score_type: str | None = None
    warnings: list[ValidationWarning] = field(default_factory=list)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["warning_count"] = len(self.warnings)
        return payload


@dataclass(frozen=True)
class ConversionResult:
    output_dir: Path
    musicxml: Path
    midi: Path
    validation_json: Path
