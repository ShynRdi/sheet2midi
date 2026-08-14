# Benchmarking

Sheet2MIDI should improve through measured recognition accuracy, not by visually inspecting a few MIDI files.

## Corpus

`benchmarks/corpus/manifest.json` defines five initial score layouts:

1. piano right hand + left hand
2. instrumental duet
3. vocal + piano
4. SATB choir
5. choir + piano

The ground-truth MusicXML files are synthetic and intentionally small so they can be redistributed and reviewed easily.

## Render the input sheets

Install MuseScore and Sheet2MIDI PDF support, then run:

```bash
python scripts/render_benchmark_corpus.py
```

This renders each ground-truth score into a PNG under `benchmarks/corpus/images/`. The PNGs are generated artifacts and are not required to be committed.

## Evaluate one prediction

```bash
sheet2midi evaluate \
  benchmarks/corpus/ground_truth/piano-grand.musicxml \
  predicted.musicxml
```

Default tolerances are 1/8 quarter-note (0.125 quarters) for onset and duration.

Metrics include:

- onset precision / recall / F1: same pitch and onset within tolerance
- note precision / recall / F1: pitch + onset + duration within tolerance
- duration accuracy among onset-matched notes
- mean onset and duration error
- part, staff, and voice accuracy among matched notes

Part/staff/voice scores are diagnostic. OMR engines may rename parts while still recognizing the musical notes correctly.

## Run a real OMR benchmark

After rendering images and installing an OMR engine:

```bash
sheet2midi benchmark benchmarks/corpus/manifest.json --engine homr
```

or use `oemer` / `audiveris`.

The command writes `benchmark.json` plus one conversion output directory per case.

## Why synthetic first?

Synthetic fixtures give us exact ground truth and remove copyright ambiguity. They are only the baseline. The next corpus layer should add carefully licensed public-domain scans and photographed pages with rotation, perspective distortion, blur, shadows, and JPEG compression.
