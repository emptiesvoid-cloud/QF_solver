# 0.2.6 G07 B3 — Remaining gap resolution

Evidence ID: `026-G07-B3-GAP-RESOLUTION-001`

`G07_B3 = PARTIAL`. This step analyzed the two remaining blockers without
changing the solver, formulation, reference data, convergence thresholds, or
G07 status.

## TL HEX8 diagnosis

The unchanged production case is
`HEX8_m4_a10_compression_l0.2_d0.12` with four cells, aspect 10, distortion
0.12, compression load scale 0.2, and tolerance `1e-8`. Fixed-step probes
were run with the same physical history and 128, 256, and 512 increments.

| increments | failure increment | load factor | reason | residual initial → final | line-search reductions | runtime fields |
|---:|---:|---:|---|---:|---:|---|
| 128 | 48 | 0.375 | `MAX_ITERATIONS` | `7.812500e-4 → 4.392803e-4` | 608 | finite |
| 256 | 96 | 0.375 | `MAX_ITERATIONS` | `3.906250e-4 → 2.819640e-4` | 667 | finite |
| 512 | 192 | 0.375 | `MAX_ITERATIONS` | `1.953128e-4 → 1.683841e-4` | 766 | finite |

The failure index scales exactly with the partition, so the physical failure
factor remains `0.375`; subdivision does not pass the limiting state. The
residual drops sharply on the first Newton update and then decreases only
slowly. The last recorded reduced-tangent diagonal ranges were finite and
positive (`2.5355..10.1477`, `2.5504..10.1519`, and `2.5449..10.1503` for the
three partitions). The initial determinant minimum was `1.0`; the last
recorded determinant minima remained approximately `0.991`. Mesh validation
passed. No singular tangent, non-finite force/tangent, or invalid element was
observed on these probes.

The primary classification is therefore `SOLVER_ALGORITHM_LIMITATION`, with
step-size sensitivity as an observed contributing symptom. It is not
classified as `FORMULATION_BUG`, `MESH_PATHOLOGY`, or `REAL_BUG` by this
evidence.

The existing adaptive driver was also probed with a bounded minimum increment
of `0.01`, cutback factor `0.25`, and maximum eight cutbacks:

| partition | accepted steps | rejected attempts | terminal result | terminal factor | terminal relative residual | rollback |
|---:|---:|---:|---|---:|---:|---|
| 8 | 5 | 2 | `MIN_INCREMENT_REACHED` | `0.34375` | `1.536582e-4` | `TRUE` |
| 16 | 8 | 2 | `MIN_INCREMENT_REACHED` | `0.359375` | `5.484982e-4` | `TRUE` |
| 32 | 11 | 1 | `MIN_INCREMENT_REACHED` | `0.34375` | `1.536582e-4` | `TRUE` |

Cutback/retry preserves the committed state, but does not complete the
history. Consequently `TL_HEX8_COMPLETE_HISTORY = NO` and no complete HEX8
external correlation is claimed. `TL_HEX8_FINAL_RESULT = FAIL` for the
requested matched-path proof, bounded by this explicit algorithmic
limitation. No functional fix was attempted.

## ARC-002 refined-mesh window

The B1 coarse reference observed a turning point near load factor
`-0.03732654` and controlled displacement `-0.89337693` for both radii. The
same refined mesh was evaluated beyond the original B1 windows:

| radius | maximum steps | runtime result | turning point | final load factor | final displacement | minimum `det(F)` |
|---:|---:|---|---|---:|---:|---:|
| 0.01 | 320 | finite continuous path | not observed | `-0.04006680` | `-1.11601411` | `0.53594888` |
| 0.02 | 160 | finite continuous path | not observed | `-0.04006683` | `-1.11601476` | `0.53594781` |

The refined path remains finite and continuous at both extended windows, but
there is no turning-point observable to compare with the coarse mesh. Further
extension does not justify inferring one: the refined path reaches an explicit
invalid deformation before any detected turn at both tested settings:

- radius `0.01`, 640 steps: element 3, `det(F) = -3.396911e-4`;
- radius `0.02`, 320 steps: element 3, `det(F) = -1.433152e-1`.

`ARC002_FINAL_RESULT = DEFERRED` and
`ARC002_REFINED_TURNING_POINT = NO`. This is a limitation of the declared
refined-mesh turning-point evidence, not a fabricated pass or a formulation
change. No turning point is extrapolated from the coarse mesh.

## Scope, provenance, and closeability

- B3 baseline: `921e026934fbdedce0d4b0537922d6d22ab10e0f`.
- Probe runner: `scripts/run_g07_b3_gap_resolution.py`.
- Machine-readable evidence:
  `qualification/0_2_6/g07_b3_gap_resolution/g07_b3_gap_resolution_evidence.json`.
- The JSON records the execution SHA, case definitions, policies, probe
  results, finite-field checks, mesh quality, residual histories, and Arc
  path digests.
- `REAL_BUG_FOUND = NO`.
- `FUNCTIONAL_SOURCE_CHANGED = NO`.
- `NUMERICAL_REGRESSION = NO` for this source-unchanged diagnostic step.
- Full regression is skipped by the declared B3 policy.

Remaining blocking gaps are
`G07-TL-008-HEX8-COMPLETE-HISTORY` and
`G07-ARC-002-REFINED-MESH-TURNING-POINT-COMPARABILITY`. G07 Owner closeout is
not ready; no promotion is made.
