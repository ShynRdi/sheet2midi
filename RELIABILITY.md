# Sheet2MIDI Reliability Contract

> **Development policy:** No public releases (including alpha/beta), stable-product claims, or release-focused promotion until the stable acceptance gates in this document pass. The current version in source metadata is a development identifier, not an assertion of product stability.
>
> **Current status:** **NOT STABLE — GATES NOT MET**. Passing CI and producing valid MusicXML or MIDI does **not** prove musical correctness.

## 1. Reliability objective

For a **measured, explicitly supported input scope**, a conversion must either:

1. produce a structurally and musically correct result under the defined tolerance, or
2. identify uncertainty, explain the reason, and classify the result as **WARN** or **UNSAFE**.

An invalid or structurally corrupted result must never be silently classified as trustworthy. The project must not claim general correctness over arbitrary printed music.

"Stable" requires independent validation of **detection**, **accuracy**, **abstention**, **reproducibility**, and **output usability**; it cannot be inferred from the number of merged PRs or successful CLI runs.

## 2. Scope and explicit non-goals

Candidate input classes, each evaluated independently before being supported:

- clean, digitally engraved single-instrument sheet music;
- piano grand staff, independent voices, chords, rests, ties, and common meters;
- multi-page scores, including covers and lyric-only pages;
- multi-part instrumental scores and SATB / choir + piano;
- challenging rhythms (tuplets, cadenza, cross-staff notation, repeats).

Support is **earned per class through benchmark evidence**. A class that misses its gates stays **experimental/unsupported** even when other classes pass. Handwritten scores are out of scope unless separately validated.

The following are **not** reliability evidence: valid XML alone, non-empty MIDI files, a successful subprocess exit, visually plausible notes, subjective A/B listening alone, or one demo song.

## 3. Failure semantics

Every conversion needs a machine-readable quality report that distinguishes:

- **PASS:** all applicable hard gates pass and input lies in the measured supported domain;
- **WARN:** output is usable for inspection but has identified unresolved ambiguity;
- **UNSAFE:** evidence of structural collapse, corrupt/missing pages or parts, untrusted synchronization, or other failure that can mislead downstream users.

**UNSAFE** must be obvious to both CLI and API clients. The default workflow must not present an UNSAFE MIDI as verified. Users can explicitly export/debug unsafe artifacts, but their status must remain attached.

Never manufacture a numeric "confidence" from hand-tuned scores. Introduce probability-like confidence only after calibration on held-out, human-verified data with reliability curves and measured false-safe rates.

Unknown error conditions must not be caught and silently skipped. Skipping a page is valid only when positively identified as non-score content; log its source page number and reason. A page with music that the backend fails to recognize is a **failure**, not a harmless empty page, until differentiated.

## 4. Quality layers and required oracles

| Layer | Test oracle | Non-negotiable acceptance |
| --- | --- | --- |
| Ingestion/page classification | source page labels + expected score/non-score mask | no silent loss of score pages; traceable skips |
| OMR recognition | legal score image + independently verified MusicXML | measured pitch, onset, duration, clef/key/meter, rests, chords, part/staff and voice accuracy |
| MusicXML normalization and merging | golden per-page XML + expected combined XML | no unaccounted lost/reordered parts, pages, notes or measure fragments |
| MIDI rendering | known-correct MusicXML + exact expected MIDI event timeline | deterministic note-on/off, pitch, time, tracks/channels and metadata |
| Structural risk detection | labeled corrupt/healthy cases | known structural collapses and synchronization failures must be flagged |
| User-facing quality report | seeded PASS/WARN/UNSAFE fixtures | reason codes, page/measure references, no contradictory healthy status |
| Operations | clean-environment installation, CLI/API, reproducible CI | no environment-dependent silent changes |

A change affecting one layer must run its layer-specific regression suite plus relevant end-to-end tests. Do not use an OMR engine to validate renderer correctness.

## 5. Benchmark design

Create a **licensed, versioned, independently verified** corpus with separate populations:

- **Development:** at least 100 diverse scores for failure analysis, fixes, and adversarial case creation.
- **Frozen release holdout:** target at least 300 previously unseen scores from independently sourced scores/layouts; no model/rule tuning after evaluating this set. If a problem is fixed using a holdout example, that example becomes development data and a new untouched holdout is required.
- **Robustness and adversarial:** controlled image transforms, phones/scans, page-order perturbations, mixed text/score PDFs, accidental crop, key/clef changes, density, complex synchronization, and unsupported layout cases. Track these separately from clean-score metrics.
- **Synthetic unit-oracle fixtures:** isolated exact-reference MusicXML, MIDI event goldens and page-merge boundary fixtures.

Split at source composition/engraving-family level, not at individual page or transformed-image level, to prevent leakage. Store source provenance, use permissions, ground-truth construction, adjudication record, backend and software versions, dataset hash, and reproducible benchmark commands. Never commit copyrighted score images or score-derived reconstructions without permission.

Every score must have expected part/staff count and hierarchy, key/meter changes, page membership, bar/measure identities, pitches and onsets/durations. Hard cases require explicit adjudication by a reviewer familiar with notation.

### Metrics: report by class, not only the mean

- conversion completion and failure classifications;
- **strict note-level F1** (pitch + onset + duration matching with declared tolerance), plus separate pitch/onset/duration metrics;
- part/staff/voice attribution, structural exact match and catastrophic structural failure;
- exact measure and page-continuity accuracy;
- multi-track MIDI event exact-match against golden MusicXML;
- **false-safe rate:** share of incorrect/corrupted outputs incorrectly classified PASS;
- **coverage:** share of in-scope examples classified PASS, plus WARN/UNSAFE abstention rate;
- worst-class metrics, per-backend metrics, robustness curves, and confidence intervals.

A detector that labels everything UNSAFE has perfect apparent caution but **zero utility**; coverage and false-safe risk must be considered together.

## 6. Proposed stable acceptance gates

These targets are **working thresholds to validate**, not achieved results or product claims. Tighten or adjust only based on a documented risk analysis **before** opening the frozen holdout.

1. **Core correctness:** 100% deterministic unit/oracle, regression, lint and build suites pass on supported Python versions. No known reproducible renderer/merger corruption in declared supported cases.
2. **Undetected catastrophic corruption:** **zero observed** false-PASS catastrophic structure/page/synchronization failures on the frozen holdout and dedicated adversarial cases. Report sample size and upper confidence bounds; zero observed is not proof of zero real-world risk.
3. **Supported clean-class accuracy (target):** strict note F1 ≥ 0.98, onset F1 ≥ 0.98, duration match ≥ 0.98, part/staff assignment ≥ 0.995, measure integrity ≥ 0.995. All measured separately per claimed supported class.
4. **Safe coverage (target):** ≥ 0.95 of supported-domain clean holdout scores reach PASS without manual repair; lower coverage must be explicitly disclosed, not hidden by restricting the denominator after seeing results.
5. **Renderer:** exact expected note events, timing, track attribution and supported metadata across a golden MusicXML suite, including multi-part, chords, rests, ties, tempo/key/meter changes, page joins, and tricky voice offsets.
6. **Reproducibility:** clean installs and end-to-end smoke tests pass on macOS and Linux; fixed versions/inputs produce matching normalized outputs where deterministic behavior is expected.
7. **Provenance and operations:** every page/part/measure transformation remains auditable and reversible; no loss of score pages without detection.
8. **Evidence review:** benchmark, scope, known limitations and all release-blocking issue dispositions are reviewed before any stable release decision.

Do not extrapolate a claim to SATB, cross-staff tuplets, scanned images or other classes solely from piano/solo performance. When a class fails, exclude it from supported scope and return WARN/UNSAFE appropriately.

## 7. Current blockers (as of 2026-11-01)

- [#26](https://github.com/ShynRdi/sheet2midi/issues/26): **silent structural collapse** in a choral + piano layout; source staff/system count cannot be equated naively with simultaneous part count.
- [#25](https://github.com/ShynRdi/sheet2midi/issues/25): **multi-page measure continuity**; complementary partial measures and source-page provenance are not yet resolved.
- [#12](https://github.com/ShynRdi/sheet2midi/issues/12): **cadenzas, tuplets and cross-staff synchronization** with incomplete OMR semantics.
- Quality classification is not yet calibrated; valid XML can conceal a bad transcription.
- Independent, licensed, frozen, human-verified holdout does not yet meet this contract.

The mixed score/text page handling fix in PR #24 was a valuable end-to-end robustness regression, **not** proof that recognized musical pages are accurate.

## 8. Execution order (correctness first)

### A. Stop silent failures
- Add backend structural evidence and source-vs-output sanity checks; a suspiciously collapsed score must not PASS.
- Distinguish absent musical content from recognition failure and keep page-level provenance.
- Add explicit machine-readable PASS/WARN/UNSAFE contracts to CLI and API.
- Add regression tests from every observed failure (licensed/synthetic surrogates where necessary).

### B. Establish exact downstream correctness
- Build golden MusicXML → MIDI event oracle tests with zero ambiguity.
- Validate page merge and boundary continuity on synthetic and real examples.
- Prevent heuristic automatic timing repairs; keep any experimental preview opt-in.

### C. Measure and improve OMR, not just the wrapper
- Verify true source score structure against exported MusicXML.
- Compare HOMR, Oemer and Audiveris on identical, legal, version-locked fixtures.
- Investigate changed preprocessing and structural output, with ablations.
- Use benchmark errors to justify each repair; require no regressions on unrelated classes.

### D. Run a frozen holdout and stability review
- Freeze implementation, data and acceptance thresholds.
- Run the untouched holdout once for release evaluation, publish all per-class metrics and failures.
- Reopen development if a gate fails; use a new holdout for the next evaluation.
- **No public release until every gate for the declared supported scope is satisfied.**

## 9. PR definition of done

A reliability PR is incomplete unless it contains: a precise failure hypothesis, a minimal reproducer, a baseline test that fails before the fix, the fix or safe rejection, proof that unrelated valid input still works, measured comparison where appropriate, and documented remaining limitations.

**Prohibition:** do not silently change the canonical MusicXML just to satisfy an inherited meter or make one demo sound better.
