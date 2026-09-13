---
doc_id: DOC-029-WP06F-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
review_date: ""
---

# WP06-F — closure, replay, reference and provenance contract

## Status

This is a Phase-0 preparation artifact. It awards no formal point: WP06-F is
`0/1`, WP06 remains `0/8` and the validated total remains `29/100`.

The contract defines how future WP06-D and WP06-E structural evidence can be
closed. It does not generate or infer any structural result. No structural,
postbuckling, reference or external solve was run, and no production
mechanics changed.

The machine-readable source is
`qualification/0_2_9/wp06f_closure_contract.json`; the preparation-only
checker is `scripts/check_wp06_closure.py`.

## Required evidence manifest

Final closure requires all thirteen explicitly identified artifacts:

| ID | Required artifact |
|---|---|
| WP06-A-CONTRACT | `qualification/0_2_9/wp06a_arc_length_formulation_contract.json` |
| WP06-B-CONTRACT | `qualification/0_2_9/wp06b_continuation_state_rollback.json` |
| WP06-C-EVIDENCE | `qualification/0_2_9/wp06c_arc_length_predictor_corrector_identities.json` |
| WP06-D-PHASE0 | `qualification/0_2_9/wp06d_structural_limit_point_contract.json` |
| WP06-D-RAW | `qualification/0_2_9/wp06d_phase1_structural_raw.json` |
| WP06-D-REFERENCE | `qualification/0_2_9/wp06d_reference_result.json` |
| WP06-D-REPLAY | `qualification/0_2_9/wp06d_replay_result.json` |
| WP06-E-PHASE0 | `qualification/0_2_9/wp06e_postbuckling_imperfection_contract.json` |
| WP06-E-RAW | `qualification/0_2_9/wp06e_phase1_structural_raw.json` |
| WP06-E-REFERENCE | `qualification/0_2_9/wp06e_reference_result.json` |
| WP06-E-REPLAY | `qualification/0_2_9/wp06e_replay_result.json` |
| WP06-F-REPORT | `docs/verification/0_2_9/wp06-final-closure-report.md` |
| WP06-F-CLOSURE | `qualification/0_2_9/wp06f_closure_report.json` |

Missing artifacts are `WP06_INCOMPLETE_EVIDENCE`; they are never an implicit
PASS. Phase-0 contracts do not substitute for the required Phase-1 raw,
reference or replay results.

## Provenance and authority

Every Phase-1 artifact must bind repository, branch, source SHA, contract
revision/digest, case-definition digest, solver-policy digest and
element/formulation identity. Reference artifacts additionally require their
independent implementation digest. D and E Phase-1 artifacts must share the
Owner-provided governing branch/policy binding. Historical A/B/C and Phase-0
D/E artifacts may retain their original source SHA, but their identity and
digests remain mandatory.

The authority order is strict:

1. raw numeric evidence;
2. machine-readable derived metrics;
3. human-readable report;
4. summary status.

A report or summary saying `PASS` cannot override a failed raw observation.
Wrong or stale digests, cross-branch Phase-1 evidence, cross-benchmark data or
missing provenance fail closed.

## WP06-D closure gates

The D track closes only when every gate passes independently:

- exact frozen WP06-D R1 benchmark, formulation, M1/M2/M3 mesh digests and
  mesh-independent point-load rule;
- derived M2→M3 refinement metrics;
- first structural limit point and accepted path continuation beyond it;
- independent reference comparison;
- vector force and moment equilibrium;
- `det(F)`, principal-stretch and Green-Lagrange envelope;
- accepted-path replay, including radius/orientation/history and required
  Newton counts;
- no altered-physics retry, undeclared M4 or result-dependent threshold.

The equilibrium derivation is vector based:

```text
force_error = ||R_support + F_external|| /
              max(||R_support||, ||F_external||, F_char, floor)
moment_error = ||M_reaction + M_external|| /
               max(||M_reaction||, ||M_external||, M_char, floor)
```

Both limits are `1e-8`. Refinement uses
`abs(M3-M2)/max(abs(M2),abs(M3),scale_floor)` with the frozen D thresholds in
the JSON contract. Missing or non-finite raw values are incomplete evidence.

## WP06-E closure gates

The E track closes only when every gate passes independently:

- exact `WP06E-TET4-IMPERFECT-COLUMN-001` TET4 total-Lagrangian StVK route;
- exact explicit coordinate imperfection
  `Z_imperfect = Z0 + alpha*(1-cos(0.5*pi*X/L))` with `alpha/L=0.005`;
- no mode-based substitution, bifurcation-detection claim or branch-switch
  claim;
- independent reference comparison, vector equilibrium and geometric
  envelope;
- complete required observations and replay;
- full Phase-1 provenance binding.

The reference must not call QF production arc-length, continuation,
residual/tangent or TET4 geometric-nonlinear routines. Missing or mismatched
reference evidence is `WP06_HOLD_REFERENCE`.

## Cross-WP consistency and replay

A through E must retain the same `SPHERICAL_ARC_LENGTH_CUSTOM` identity,
residual/sign convention, accepted/trial/rollback semantics, orientation
policy, claim vocabulary and governing execution-policy identity for D/E.
Inconsistency fails closure; tracks are not averaged.

D and E replay compare accepted displacement/path, lambda, radius, orientation,
accepted/rejected steps, Newton counts where required and terminal
classification with relative tolerance `1e-12` and absolute floor `1e-14`.
Qualitative path differences fail even when the final endpoint is close.

## Public claim boundary

If A–F all pass, the maximum bounded claim is:

> QF Solver 0.2.9 qualifies a bounded spherical arc-length continuation
> route for selected TET4 geometrically nonlinear StVK benchmarks, including
> limit-point traversal and imperfection-seeded continuation.

This does not qualify general postbuckling, bifurcation detection, branch
switching, contact/plastic/dynamic buckling, universal element families or
MPI/PETSc arc-length.

Formal points remain `8/8` only if A, B, C, D, E and F all pass. Preparation
artifacts alone award no point; a D/E failure leaves formal WP06 at `0/8`
unless Owner governance is explicitly revised.

## Preparation validation

`tests/unit/test_wp06f_closure_contract.py` exercises valid raw evidence and
anti-downgrade cases for missing artifacts, provenance, benchmark/amplitude/
mesh/load/policy mismatches, refinement, equilibrium, reference, replay,
envelope, unsupported claims, undeclared M4, non-finite data and unexpected
production changes. The checker is not a structural runner and defaults to
the Phase-0 no-execution guard.

