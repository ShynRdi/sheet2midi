# Sheet2MIDI

**Sheet2MIDI** is an open-source pipeline for turning printed sheet music into editable **MusicXML** and standard **MIDI** files that can be imported into DAWs such as GarageBand, Logic Pro, Ableton Live, FL Studio, Reaper, and notation editors.

> Image/PDF → OMR → MusicXML → validation → multi-track MIDI

The project intentionally uses **MusicXML as the canonical intermediate format**. OMR is imperfect; keeping a structured score between recognition and MIDI makes errors inspectable, correctable, and measurable.

## Goals

Sheet2MIDI is designed around real multi-part scores rather than a single melody line:

- solo melody / instrument sheets
- piano grand staff (right hand + left hand)
- polyphonic piano
- instrumental duets and ensembles
- vocal + piano
- SATB / choral scores
- choir + piano
- larger printed Western scores as recognition engines improve

Handwritten notation is **not** a v0.1 target.

## v0.1 architecture

```text
PDF / PNG / JPG
      │
      ▼
page preparation
      │
      ▼
OMR backend
  ├─ homr
  ├─ oemer
  └─ Audiveris
      │
      ▼
MusicXML / MXL
      │
      ├─ structural validation
      └─ normalization / page merge
      │
      ▼
MIDI renderer
      │
      ▼
Standard Type-1 .mid
```

The OMR layer is pluggable. Sheet2MIDI itself does not vendor an OMR model.

## Supported OMR backends

### homr

Install `homr` so the `homr` executable is available. Its upstream CLI accepts an image and writes MusicXML beside it.

### oemer

Install from PyPI:

```bash
pip install oemer
```

Sheet2MIDI invokes the upstream `oemer <image> -o <output-dir>` interface.

### Audiveris

Install Audiveris and make the `audiveris` executable available. Sheet2MIDI uses batch transcription/export to MusicXML/MXL.

The three engines have different licenses and recognition strengths. Review the upstream license before redistributing or embedding an engine in another product.

## Installation

Core package:

```bash
pip install -e .
```

PDF support:

```bash
pip install -e '.[pdf]'
```

API server:

```bash
pip install -e '.[api]'
```

Development:

```bash
pip install -e '.[dev,pdf,api]'
```

## CLI

See available backends:

```bash
sheet2midi backends
```

Convert a sheet:

```bash
sheet2midi convert score.png --engine auto --output out
```

PDF:

```bash
sheet2midi convert score.pdf --engine audiveris --output out
```

Render an existing MusicXML file to MIDI without running OMR:

```bash
sheet2midi midi score.musicxml --output score.mid
```

Validate MusicXML:

```bash
sheet2midi validate score.musicxml
```

### Piano track layout

By default `--track-mode staff` keeps staves separate. A two-staff Piano part becomes approximately:

```text
Conductor
Piano - Right Hand
Piano - Left Hand
```

Use:

```bash
sheet2midi convert piano.png --track-mode part
```

to merge both staves into one MIDI instrument track.

## API

```bash
uvicorn sheet2midi.api:app --host 0.0.0.0 --port 8000
```

Then upload a sheet to `POST /v1/convert`. The endpoint returns a ZIP containing the recognized MusicXML, generated MIDI, and validation report.

## What v0.1 MIDI currently preserves

- multiple score parts
- multiple staves per part
- independent MusicXML voices via `backup` / `forward` timing
- chords
- rests and rhythmic spacing
- ties
- tempo changes represented by `<sound tempo="...">`
- time signatures
- key signatures
- separate piano hands when requested
- basic General MIDI instrument inference from part names

MusicXML remains richer than MIDI. Lyrics, engraving, slurs, most articulation, detailed dynamics, pedal semantics, repeat realization, ornaments, and advanced score directions are not all rendered to playback yet.

## Reliability philosophy

OMR recognition and MIDI rendering are different problems. A symbol can be correctly retained in MusicXML even if v0.1 does not yet translate it into a MIDI performance instruction. Do not throw away the MusicXML output.

The validator currently flags structural issues such as malformed score types and measure-duration mismatches. Future releases will add confidence scoring and automatic repair suggestions.

## Development

```bash
pytest
ruff check .
```

## Roadmap

See [ROADMAP.md](ROADMAP.md).

## Contributing

Contributions, score fixtures, OMR error reports, and backend adapters are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Sheet2MIDI's own source code is released under the [MIT License](LICENSE). OMR backends are separate projects and retain their own licenses.
