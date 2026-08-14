from __future__ import annotations

from .base import OMRBackend
from .subprocess_backends import AudiverisBackend, HomrBackend, OemerBackend

_BACKENDS: dict[str, type[OMRBackend]] = {
    "homr": HomrBackend,
    "oemer": OemerBackend,
    "audiveris": AudiverisBackend,
}


def backend_status() -> dict[str, bool]:
    return {name: backend().available() for name, backend in _BACKENDS.items()}


def get_backend(name: str) -> OMRBackend:
    if name == "auto":
        for candidate in ("homr", "oemer", "audiveris"):
            backend = _BACKENDS[candidate]()
            if backend.available():
                return backend
        raise RuntimeError("No OMR backend found. Install homr, oemer, or Audiveris.")
    try:
        backend = _BACKENDS[name]()
    except KeyError as exc:
        raise ValueError(f"Unknown OMR backend: {name}") from exc
    if not backend.available():
        raise RuntimeError(f"OMR backend '{name}' is not installed or not on PATH")
    return backend


__all__ = ["OMRBackend", "backend_status", "get_backend"]
