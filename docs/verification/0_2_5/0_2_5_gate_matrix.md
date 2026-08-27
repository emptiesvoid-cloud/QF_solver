---
doc_id: DOC-NL-025-014
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 gate matrix

The matrix records the current controlled status after the G01 evidence
replay. Optional friction gate G07 is `NOT_IN_RELEASE_SCOPE` until an explicit
Owner promotion. Gate status values are restricted to `PASS`, `OPEN`, `BLOCKED` and
`NOT_IN_RELEASE_SCOPE`. Evidence labels such as
`PASS_INTERNAL` or `PASS_EXTERNAL_CORRELATION_BOUNDED` describe the supporting
proof, but do not replace the gate status. Only evidence generated on the
recorded SHA can close a gate.

G01 is closed by controlled internal and Code_Aster evidence under the stable
`g01_latest` and `g01_code_aster_latest` output paths. Both final manifests
record the same clean candidate source revision and artifact digests. The
Owner-approved treatment of mesh/load-step trends and rollback reference
differences is bounded and does not create a universal convergence claim or
lower any requirement. G02, G03, G06 and G08 retain provisional observations
and remain `OPEN` until their own controlled campaigns close. G09 has a
separate controlled failure campaign and is closed below; this does not close
any dependent functional gate.

| Gate | Name | Mandatory closure criteria | Dependencies | Status |
|---|---|---|---|---|
| 025-G00 | Baseline and architecture frozen | exact 0.2.4 SHA; provenance reconciled; tests/coverage/V&V/performance/API baselines; Owner audit approval | none | OPEN |
| 025-G01 | 0.2.4 nonlinear V&V debt closed | multi-element four-family J2; mesh/load-step/cyclic/energy/rollback/tangent evidence; bounded external curves; Owner-approved acceptance treatment | G00 | PASS |
| 025-G02 | Geometric nonlinear core verified | approved measures; TET4/HEX8 objectivity, tangent, energy, mesh and external evidence; common Full Newton | G01 | OPEN |
| 025-G03 | Linear buckling verified | sparse eigenpath; Euler + nontrivial benchmark; factor/mode convergence and external correlation | G02 | OPEN |
| 025-G04 | Arc-length verified | one sparse method; branch, limit point, restart, cutback and external response evidence | G02 | OPEN |
| 025-G05 | Frictionless contact verified | common residual/tangent/state/Newton; finite sliding, recontact, penetration sensitivity, rollback, external correlation | G02 | OPEN |
| 025-G06 | Coupled nonlinear core verified | approved J2 finite-kinematics model; J2+geometry and geometry+contact; limit recovery, tangent, energy, mesh and external evidence | G01, G02, G05 | OPEN |
| 025-G07 | Frictional contact verified | only after Owner promotion; objective stick/slip, state, dissipation and external evidence | G05, G06, Owner GO | NOT_IN_RELEASE_SCOPE |
| 025-G08 | Performance characterized | reproducible cost/memory profiles for all mandatory paths; HEX20 explained; numerical non-regression after optimization | relevant functional gates | OPEN |
| 025-G09 | Failure modes verified | complete mandatory failure matrix; structured reasons; no false convergence; exact rollback | relevant functional gates | PASS |
| 025-G10 | External correlation bounded | all mandatory external matrix cells complete or associated claim removed; full histories and provenance | G01-G06 | OPEN |
| 025-G11 | Full regression | complete 0.2.4 + accepted 0.2.5 tests, coverage policy, docs, V&V, build and smoke pass on candidate SHA | G08-G10 and mandatory functional gates | OPEN |
| 025-G12 | Documentation, traceability and Owner closure | final-SHA evidence, qualification/README/changelog/metadata consistency, limitations, artifacts and explicit Owner release decision | G11 | OPEN |

## Gate closure record

Every gate record includes:

- gate ID/status and exact SHA;
- requirements and V&V rows covered;
- command/environment and artifact links/digests;
- measured values and frozen thresholds;
- skips/exclusions and justification;
- known limits and residual risks;
- reviewer, date and Owner decision where required.

## Controlled closure: 025-G09

`025-G09` is closed by the controlled campaign at
`results/vnv_0_2_5/g09_latest/summary.json` and its
`evidence_manifest.json`. The manifest records the exact source SHA,
`dirty=false`, command, tool versions and SHA-256 digest of the report. The
campaign contains 22 intentional failure cases and reports `22 passed / 0
failed`, with `converged=false` and a structured diagnostic for every case.
The campaign is an internal failure-contract qualification; it does not
promote contact, arc-length, buckling or coupled capabilities to qualified
status and does not close their functional gates.

## Controlled closure: 025-G01

`025-G01` is `PASS`. The internal manifest at
`results/vnv_0_2_5/g01_latest/evidence_manifest.json` records
`PASS_INTERNAL_J2`, `dirty=false`, the exact candidate source revision and
digests for the constitutive, tangent, transaction, four-family,
mesh/load-step, cyclic, energy and rollback evidence. The Code_Aster manifest
at `results/vnv_0_2_5/g01_code_aster_latest/evidence_manifest.json` records
`PASS_EXTERNAL_CORRELATION`, `dirty=false` and `64/64` comparable checks for
TET4, TET10, HEX8 and HEX20.

The closure uses the Owner-approved bounded classifications in the J2 report:
mesh/PEEQ, load-step sensitivity and rollback numerical comparison are
`ACCEPTED_BOUNDED_OBSERVATION`; the rollback transaction invariant is
`THRESHOLD_JUSTIFIED`. `CONTRACT LOWERED = NO`. This closure changes no other
gate.

## STOP/GO policy

An `OPEN` or `BLOCKED` prerequisite forbids dependent implementation. Optional
independent branches may continue only when their full dependency chain is
closed. `NOT_IN_RELEASE_SCOPE` is acceptable only for predeclared optional work
and must not appear in README/package capability claims.
