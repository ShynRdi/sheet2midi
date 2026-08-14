# Benchmarking

Sheet2MIDI should improve through measured recognition accuracy, not by visually inspecting a few MIDI files.

## Corpus v1

`benchmarks/corpus/manifest.json` contains the original five tiny deterministic regression layouts. They remain useful for fast sanity checks, but they are intentionally simple.

## Corpus v2

`benchmarks/corpus-v2/manifest.json` defines five generated four-measure layouts:

1. polyphonic piano grand staff
2. violin + cello duet
3. vocal + piano with lyrics
4. SATB
5. choir + piano

Generate the exact ground truth with:

```bash
python scripts/generate_benchmark_v2.py
```

Every note has an explicit MusicXML duration type and the piano/low-instrument parts use explicit clefs. The generator is the source of truth so fixtures are reproducible rather than hand-edited.

Render clean sheets with:

```bash
python scripts/render_benchmark_corpus.py benchmarks/corpus-v2/manifest.json
```

## Metrics

```bash
sheet2midi evaluate reference.musicxml predicted.musicxml
```

Metrics include pitch+onset F1, strict pitch+onset+duration F1, duration accuracy, mean timing errors, and diagnostic part/staff/voice accuracy.

## Robustness matrix

The manual `OMR robustness matrix` GitHub Action runs homr against the clean v2 corpus and deterministic degraded variants:

- rotation: 2.5°
- Gaussian blur
- directional shadow
- mild perspective warp
- low-quality JPEG recompression

The degradation files are generated artifacts, not committed benchmark truth. Run locally with:

```bash
python scripts/generate_benchmark_v2.py
python scripts/render_benchmark_corpus.py benchmarks/corpus-v2/manifest.json
python scripts/degrade_benchmark_images.py
```

Then benchmark any generated manifest under `benchmarks/corpus-v2/manifests/`.

## Why synthetic first?

Synthetic data gives exact symbolic ground truth and avoids copyright ambiguity. It does **not** replace real scanned scores. The next corpus layer should add redistributable public-domain scans and actual phone photographs, while preserving the same evaluation contract.
