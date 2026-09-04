---
doc_id: DOC-027-014
revision: 0.1
status: controlled_release
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# 0.2.7 Release Criteria

These criteria describe the controlled release boundary for QF Solver 0.2.7.
The Owner has completed the qualification decision at 100 percent; the stable
tag and publication sequence are recorded separately by Step 1. This document
does not authorize PyPI publication.

## Scope and provenance

- [ ] target version, package metadata and future tag agree;
- [ ] final source SHA, evidence heads and generated artifact digests are
  separated and reproducible;
- [ ] current branch is clean and the archive contains no internal paths,
  secrets or accidental generated bulk;
- [ ] every public capability has one registry row, maturity, evidence and
  limitation;
- [ ] WEDGE6 is either bounded with its own evidence or explicitly not
  qualified; no neighboring element is promoted transitively.

## Numerical and V&V checks

- [ ] T0/T1/T2/T3 results match the declared test policy;
- [ ] modified functional code has targeted and required full-regression
  evidence;
- [ ] mesh quality, orientation, failure modes and deterministic replay are
  recorded for each newly claimed route;
- [ ] external comparisons are formulation-compatible or explicitly skipped;
- [ ] numerical thresholds were declared before the corresponding run and no
  criterion was weakened after observation;
- [ ] resource limits and performance claims are bounded by hardware and
  topology.

## Public release checks

- [ ] README, changelog, API stability and installation instructions match the
  final status;
- [ ] experimental, research and not-qualified routes remain visible;
- [ ] package wheel/sdist build and clean installation pass;
- [ ] the final full regression and documentation checks are green, with
  expected skips documented;
- [ ] Owner signs the final decision before tag, release or PyPI publication.

No tag, GitHub release or PyPI publication is authorized by this planning
document.
