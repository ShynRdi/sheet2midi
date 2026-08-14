# Roadmap

## v0.1 — foundation

- [x] pluggable OMR backends
- [x] MusicXML as canonical representation
- [x] standard multi-track MIDI renderer
- [x] piano staff separation
- [x] structural validation
- [x] CLI and HTTP API

## v0.2 — benchmark and correctness

- [ ] curated public-domain benchmark set
- [ ] pitch accuracy metric
- [ ] onset/duration metrics
- [ ] measure exact-match metric
- [ ] OMR backend comparison harness
- [ ] confidence score per page / measure
- [ ] regression corpus for piano, duet, vocal+piano, SATB, choir+piano

## v0.3 — richer MIDI performance

- [ ] sustain pedal / CC64
- [ ] dynamics to velocity curves
- [ ] repeat and ending realization
- [ ] articulation-aware note lengths
- [ ] lyrics meta events
- [ ] configurable General MIDI programs

## v0.4 — correction loop

- [ ] visual score preview
- [ ] suspicious-measure highlighting
- [ ] measure-level re-recognition
- [ ] automatic repair candidates
- [ ] export corrected MusicXML + MIDI

## v1.0 target

Reliable conversion of common printed Western multi-part sheet music into editable MusicXML and DAW-ready multi-track MIDI, with measurable confidence and an explicit correction workflow.
