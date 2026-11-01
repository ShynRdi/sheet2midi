# Roadmap — Reliability First

> **No public release until stable gates pass.** See [RELIABILITY.md](RELIABILITY.md) for the formal acceptance contract. All phases below are **internal development phases**, not promised versions or release dates.

## Foundation (implemented, not certified reliable)

- [x] pluggable OMR backends
- [x] canonical MusicXML intermediate and basic validation
- [x] multi-track MIDI renderer and track-by-staff option
- [x] CLI and HTTP API
- [x] synthetic regression/robustness scaffolding
- [x] skip positively identified non-score PDF pages (PR #24)
- [ ] complete independent correctness evidence for the above

## P0 — Detect and contain catastrophic errors

- [ ] [#26](https://github.com/ShynRdi/sheet2midi/issues/26): structural collapse detection (backend evidence versus exported score)
- [ ] distinguish score page recognition failure from true non-score page; preserve provenance
- [ ] quality result contract `PASS / WARN / UNSAFE` for CLI, API and saved artifacts
- [ ] hard regression for known false-PASS cases; no silent acceptance of known corruption

## P1 — Validate page and rhythm consistency

- [ ] [#25](https://github.com/ShynRdi/sheet2midi/issues/25): page boundary and split-measure continuity
- [ ] independent golden MusicXML → MIDI oracle and exact event comparisons
- [ ] [#12](https://github.com/ShynRdi/sheet2midi/issues/12): cadenza, tuplets and cross-staff safety; no automatic speculative repair
- [ ] provenance and reversibility of all transformations
- [ ] baseline whole-system and per-class regression dashboard

## P2 — Verified OMR quality

- [ ] >=100 licensed development scores with independently verified MusicXML ground truth
- [ ] compare HOMR, Oemer and Audiveris on identical versioned inputs
- [ ] strict note, pitch, onset, duration, structure, measure, false-safe and coverage metrics
- [ ] clean-image plus scan/rotation/blur/perspective robustness matrix
- [ ] fix highest-severity evidence-backed recognition and synchronization failures
- [ ] independently adjudicated ground truth for challenging layouts

## P3 — Freeze, validate, then consider Stable

- [ ] >=300 unseen, licensed frozen holdout scores
- [ ] acceptance thresholds frozen before first holdout evaluation
- [ ] pass **all applicable gates in RELIABILITY.md** per claimed supported class
- [ ] Linux and macOS clean installation and deterministic core behavior
- [ ] DAW import interoperability checks and documented supported scope
- [ ] independent release-quality review of known limitations and false-safe failures

**Only after these pass:** decide whether a stable public release is justified. Feature requests such as performance dynamics, sustain controls, GUI correction workflows and additional export options remain secondary until core safety and correctness gates are met.
