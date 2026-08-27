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
lower any requirement. G02 now has a controlled evidence pack, but remains
`OPEN` pending the Owner's explicit decision on the bounded pre-limit
mesh/refinement treatment and the exact release scope. G03 and G06 retain
provisional observations and remain `OPEN` until their own controlled
campaigns close. G08 is closed by the controlled replay recorded below. G09 has a
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
| 025-G08 | Performance characterized | reproducible cost/memory profiles for all mandatory paths; HEX20 explained; numerical non-regression after optimization | relevant functional gates | PASS |
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

## Controlled closure: 025-G08

`025-G08` is `PASS` for bounded performance characterization. The final
controlled replay is archived under `results/vnv_0_2_5/g08_latest/`. Its
manifest records the exact clean source SHA, `dirty=false`, commands, runtime
versions, environment data and SHA-256 digests for the raw samples, aggregate
summary and report.

The mandatory load-control profile contains 12 `PASS` samples: three repeats
for each of TET4, TET10, HEX8 and HEX20. The same clean-SHA campaign also
contains one-repeat characterization smokes for the geometric-static,
arc-length, contact and coupled paths. These smokes document shared-driver
costs; they are not claims that those functional gates are closed.

The aggregate report quantifies total, element-kernel, assembly and sparse
solve costs, Python allocation peaks, RSS observations, Newton iterations and
residuals. It explicitly identifies the HEX20 kernel as the dominant measured
cost and records the corresponding kernel/assembly and kernel/total ratios.
The repeated numerical fields and convergence status are stable across the
three load-control repeats. No speedup, multi-million-DOF scalability or
memory-efficiency claim is inferred from this local bounded campaign. The
closure therefore satisfies the existing G08 contract without changing any
functional gate or acceptance threshold.

## Controlled evidence: 025-G02 (gate remains OPEN)

The dedicated pack at `results/vnv_0_2_5/g02_latest/` records the exact clean
source SHA, `dirty=false`, reproducible command, environment and SHA-256
digests. It contains:

- rigid translation, 0.7 rad rigid rotation and combined translation/rotation
  objectivity checks for TET4, TET10, HEX8 and HEX20;
- sparse internal-force tangent finite-difference checks for all four families;
- bounded TET4/HEX8 large-rotation paths above 0.5 rad with positive `det(F)`;
- four-level coarse/medium/fine/refined pre-limit mesh observations for TET4
  and HEX8;
- four-family small-strain-limit recovery;
- twelve-step pinned Code_Aster 18.1 TET4/HEX8 histories for displacement,
  reactions, `SIEF_ELGA` stress and `EPSI_ELGA` strain.

The pack status is intentionally `OPEN` because the mesh/refinement trend is
reported as `PASS_INTERNAL_RESEARCH` with no invented universal threshold, and
the Owner must decide whether that bounded treatment satisfies the existing
G02 contract. The load-control line-search failure at the physical stability
boundary is retained as a limitation and is not recast as a defect or a PASS.
The evidence qualifies neither `total_lagrangian_j2` nor TET10/HEX20 plastic
finite-kinematic behaviour, and does not close G03-G06.

## STOP/GO policy

An `OPEN` or `BLOCKED` prerequisite forbids dependent implementation. Optional
independent branches may continue only when their full dependency chain is
closed. `NOT_IN_RELEASE_SCOPE` is acceptable only for predeclared optional work
and must not appear in README/package capability claims.
