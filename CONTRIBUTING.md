# Contributing

Thanks for helping improve Sheet2MIDI.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,pdf,api]'
pytest
ruff check .
```

## Pull requests

Keep recognition backends isolated behind the `OMRBackend` interface. The core package must remain usable without installing a heavyweight OMR model.

When changing MusicXML or MIDI behavior, add a minimal synthetic MusicXML fixture that reproduces the case. Prefer assertions on pitches, onset ticks, durations, track layout, and validation warnings over binary snapshot files.

## Score samples

Only submit sheet music you have the right to redistribute. Public-domain synthetic or self-authored fixtures are preferred.

## Scope

Good contributions include:

- OMR backend adapters
- MusicXML parsing improvements
- MIDI semantics
- score validation rules
- benchmark/evaluation tooling
- tests for polyphony, piano, duets, vocal, and choral layouts
