# Architecture

Sheet2MIDI separates recognition from symbolic music processing.

```text
Input
  ↓
Page preparation
  ↓
OMRBackend.recognize()
  ↓
MusicXML / MXL
  ↓
normalize + merge
  ↓
validate
  ↓
render MIDI
```

## Why MusicXML is canonical

Direct image-to-MIDI output hides recognition mistakes. MusicXML preserves score structure such as parts, staves, voices, measures, key/time signatures, lyrics, and notation that MIDI cannot fully represent.

## Score hierarchy

The system is designed around:

```text
Score
└── Part
    └── Staff
        └── Voice
            └── Event
```

MIDI rendering consumes temporal events reconstructed from MusicXML `note`, `chord`, `backup`, and `forward` elements. `backup` is essential for independent voices sharing a measure/staff.

## Track modes

`staff` (default) creates one MIDI track per staff. This is useful for piano editing in a DAW.

`part` creates one MIDI track per MusicXML part, merging all staves of the part.

## OMR adapters

Backends run as subprocesses and return a MusicXML/MXL path. Their dependencies and licenses are intentionally outside the core package.

## Validation

Validation is non-destructive. It reports suspicious structure but never silently rewrites recognized music in v0.1.
