# 0.2.6a0 Master Plan

## Objective

0.2.6a0 is a maturity, reproducibility and architecture cycle. It makes the
qualification system executable as controlled work packages before any claim is
expanded. This foundation run adds no FEM physics and does not certify a new
release.

## Ordered Execution

1. G00 baseline and provenance.
2. G01 architecture audit.
3. G02 registry, runner and manifest contracts.
4. G03 corpus design.
5. G04-G13 controlled capability batches, each followed by evidence and gate
   review.
6. G14 full regression and architecture freeze.
7. G15 Owner review.

Every batch follows: audit, implement only the approved narrow change, verify,
benchmark where applicable, correlate, gate, then move to the next package.
An OPEN gate is recorded as OPEN; it is never converted to PASS by a new label.
