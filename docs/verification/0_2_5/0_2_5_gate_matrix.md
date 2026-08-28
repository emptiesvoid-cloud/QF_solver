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
lower any requirement. G02 is closed for the Owner-approved bounded elastic
Total-Lagrangian scope defined below. The qualified numerical source remains
distinct from the documentary Owner decision. G06 retains provisional
observations and remains `OPEN` until its own controlled campaign closes. G03
is closed for the bounded TET4 linear-buckling scope defined below. G08
is closed by the controlled replay recorded below. G09 has a
separate controlled failure campaign and is closed below; this does not close
any dependent functional gate.

| Gate | Name | Mandatory closure criteria | Dependencies | Status |
|---|---|---|---|---|
| 025-G00 | Baseline and architecture frozen | exact 0.2.4 SHA; provenance reconciled; tests/coverage/V&V/performance/API baselines; Owner audit approval | none | OPEN |
| 025-G01 | 0.2.4 nonlinear V&V debt closed | multi-element four-family J2; mesh/load-step/cyclic/energy/rollback/tangent evidence; bounded external curves; Owner-approved acceptance treatment | G00 | PASS |
| 025-G02 | Geometric nonlinear core verified | approved measures; TET4/HEX8 objectivity, tangent, energy, mesh and external evidence; common Full Newton | G01 | PASS |
| 025-G03 | Linear buckling verified | sparse eigenpath; Euler + nontrivial benchmark; factor/mode convergence and external correlation | G02 | PASS |
| 025-G04 | Arc-length verified | one sparse method; branch, limit point, restart, cutback and external response evidence | G02 | OPEN |
| 025-G05 | Frictionless contact verified | common residual/tangent/state/Newton; finite sliding, recontact, penetration sensitivity, rollback, external correlation | G02 | PASS |
| 025-G06 | Coupled nonlinear core verified | approved J2 finite-kinematics model; J2+geometry and geometry+contact; limit recovery, tangent, energy, mesh and external evidence | G01, G02, G05 | OPEN |
| 025-G07 | Frictional contact verified | only after Owner promotion; objective stick/slip, state, dissipation and external evidence | G05, G06, Owner GO | NOT_IN_RELEASE_SCOPE |
| 025-G08 | Performance characterized | reproducible cost/memory profiles for all mandatory paths; HEX20 explained; numerical non-regression after optimization | relevant functional gates | PASS |
| 025-G09 | Failure modes verified | complete mandatory failure matrix; structured reasons; no false convergence; exact rollback | relevant functional gates | PASS |
| 025-G10 | External correlation bounded | all mandatory external matrix cells complete or associated claim removed; full histories and provenance | G01-G06 | BLOCKED |
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

## G10 sweep decision

`025-G10` is `BLOCKED` by the still-open mandatory external cells associated
with `025-G04` and `025-G06`. The external matrix is classified as follows:

| Capability row | Current classification | Release consequence |
|---|---|---|
| J2 multi-element | `PASS_BOUNDED` | Two-cell Code_Aster history is supporting bounded evidence; it is not a complete G10 closure for every claimed path |
| Large deformation | `PASS_BOUNDED` | Bounded TET4/HEX8 elastic evidence only |
| Linear buckling | `PASS_BOUNDED` | Euler and bounded Code_Aster TET4 evidence; CalculiX remains a non-blocking SHOULD with recorded deviations/limits |
| Arc-length | `OPEN` | G04 remains open: the required independent reproducible reference and four-level branch study are not closed |
| Frictionless contact | `PASS_BOUNDED` | Bounded G05 contact contract only; no general external surface-to-surface claim |
| J2 + geometry | `OPEN` | G06 MUST: finite-kinematic J2 is not an approved model and the Code_Aster comparison is incomplete/non-comparable for the required scope |
| Geometry + contact | `OPEN` | G06 MUST: the finite-kinematic comparison has a mapped reaction deviation and no equivalent finite-sliding external history |
| Triple coupling | `NOT_REQUIRED` | SHOULD not promoted to a 0.2.5 release requirement |
| Friction | `NOT_REQUIRED` | COULD and G07 remains `NOT_IN_RELEASE_SCOPE` |

CalculiX is not promoted from SHOULD to MUST. Its available positive or
negative results remain supporting evidence and do not replace the Code_Aster
MUST cells. No requirement or tolerance is lowered by this decision.

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

## Controlled closure: 025-G02

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

The source pack intentionally remains `OPEN`: it faithfully records the state
before the Owner decision and is not rewritten after the numerical campaign.
The Owner decision record `0_2_5_g02_owner_review.md` accepts the coherent
four-level pre-limit trend as `APPROVED_BOUNDED_REFINEMENT`, without inventing a
universal mesh-convergence band. The accompanying review manifest distinguishes
the qualified source SHA from the documentary Owner-evidence SHA.

`025-G02` is therefore `PASS` only for the following bounded scope:

- elastic Total-Lagrangian finite-deformation statics using the common Full
  Newton path;
- TET4 and HEX8;
- the recorded pre-limit, positive-`det(F)` load domain and the associated
  objectivity, tangent, energy, mesh-trend and Code_Aster evidence.

The load-control line-search failure at the physical stability boundary is
retained as a limitation and is not recast as a defect or a PASS. This closure
does not qualify `total_lagrangian_j2`, finite-kinematic plasticity,
TET10/HEX20 finite-kinematic behavior, post-limit response, buckling,
arc-length, contact or coupled paths; G03-G06 remain unchanged. The Code_Aster
result is bounded numerical code-to-code correlation, not physical validation.

## Controlled closure: 025-G03

`025-G03` is `PASS` for a bounded first tangent-instability scope. The final
internal Euler campaign is archived under
`results/vnv_0_2_5/g03_euler_final/`; it contains four structured TET4 levels
(`16x4x4`, `24x6x6`, `32x8x8`, `40x10x10`) with sparse initial-stress
geometric stiffness, positive precritical `det(F)`, relative brackets below
`5e-3`, and a finest-level Euler error of `5.89 %`. The successive critical
load changes are recorded as `15.63 %`, `6.57 %` and `3.31 %`; this is a
bounded refinement trend, not a universal mesh-convergence claim.

The nontrivial external probe is archived under
`results/vnv_0_2_5/g03_final/` and is linked to qualified source SHA
`85c75d06955976251dd54ad782f57f1eb5a7f8f4`. QF Solver computes a critical
factor of `221.54828247814925` against `221.774` from the pinned Code_Aster
18.1.0 execution, a relative difference of `1.018e-3`. The best modal MAC is
`0.9999999989229131` and the QF critical-mode residual is `1.72e-15`.

This closure follows a demonstrated numerical correction: the buckling path
now assembles only the sparse initial-stress geometric contribution instead
of treating a full tangent difference as `Kg`. The exact TET4 unit test and
the targeted buckling suite are green. The current Docker image could not
replay Code_Aster in this environment because its launcher lacks `mpi4py`;
the archived Code_Aster deck, image digest and mode output remain preserved
as the external execution evidence. CalculiX remains a SHOULD cell: its
bounded TET4 campaign is retained as supporting evidence and its blocked
high-order probe is retained as negative evidence, but neither is required
to close G03.

The qualified scope is limited to sparse linear buckling / first tangent
instability with the supported total-Lagrangian solid path and the recorded
TET4 external probe. TET10, HEX8 and HEX20 remain internal/research for this
gate; post-buckling, imperfection-sensitive collapse and general stability
prediction remain outside the claim. The Owner decision is `APPROVED` with
mesh decision `APPROVED_BOUNDED_REFINEMENT`; `CONTRACT LOWERED = NO`.

## Owner audit: 025-G04 remains open

The controlled audit is recorded in `0_2_5_g04_owner_review.md`, with the
strict model/path comparison in `0_2_5_g04_external_branch_diagnostic.md` and
the targeted pack under `results/vnv_0_2_5/g04_latest/`. The common-driver QF
Solver path records one signed load-factor turn, exact restart suffixes and a
controlled cutback/retry, but remains `PASS_INTERNAL_RESEARCH` on a two-element
TET4 model. No four-level arc-length mesh study is available.

The historical monotone Code_Aster result has been resolved as a deck
configuration mismatch: it had the opposite physical force direction and used
mean crown displacement rather than the QF apex control DOF. The corrected
pinned Code_Aster 18.1 Docker replay uses downward `FZ=-1/3`, `APEX/DZ`, and a
matched continuation window; it produces one turn and agrees with the QF
equilibrium branch by a peak-normalized load-factor difference of
`1.3052e-05`. This is bounded code-to-code diagnostic evidence, not physical
validation or a gate closure.

`025-G04` therefore remains `OPEN`, `CONTRACT LOWERED = NO`, and no arc-length
production claim is promoted. The remaining functional blockers are the missing
published FEM branch reference and the required four-level mesh study. G03 and
G05 are unchanged; the updated G06 evidence follows below.

## Controlled G06 targeted evidence

The final controlled G06 evidence is archived under
`results/vnv_0_2_5/g06_latest/`. Its `summary.json`, `report.md` and
`evidence_manifest.json` record qualified source SHA
`8df4b4ac32e9416e89fe342871aab6e75cdd245c`, `dirty=true` at the current
documentary capture, and artifact digests. The dirty flag reflects the
uncommitted documentation updates; no solver source changed. The replay
covers the existing pairwise/triple composition checks,
the four-family J2 plus Total-Lagrangian path, the four-family updated
penalty-contact composition, a three-level (`1/2/4`) J2 plus geometry mesh
study, an independent global coupled tangent finite-difference check, and a
three-level geometry/contact mesh replay. All targeted internal paths
converged and remain classified `PASS_INTERNAL_RESEARCH`; the independent
tangent checks are `PASS_INTERNAL`.

The original complete step-level history capture is archived as
`results/vnv_0_2_5/g06_latest/coupled_histories.json` with original capture
SHA `a56db0863835ee16485adf5c9d30954c2f425ecb`. The aggregate manifest
records that only documentation changed between that clean capture and the
current qualified SHA; no solver source changed.

This evidence does not close `025-G06`. The independent coupled tangent FD and
the bounded geometry/contact mesh replay are now closed as internal
sub-proofs, but they do not replace the external MUST. A separate pinned
Code_Aster `GREEN_LAGRANGE` replay reaches the end of the bounded history for
TET4, HEX8 and HEX20; TET10 stops at the first load point after the configured
Newton limit. The measured QF/Code_Aster deviations are archived for
convention review, not promoted to unconditional external PASS. The historical
`GDEF_LOG` replay remains archived separately, including its HEX20
non-convergence.

The Code_Aster `CONTINUE` frictionless surface oracle also executes and is
recorded as bounded supporting evidence. Its discrete support springs require
`DEFORMATION='PETIT'`; a direct `GREEN_LAGRANGE` probe is rejected by
Code_Aster for that reason. It is therefore not a comparable finite-kinematic
3D solid geometry/contact full-history correlation and does not close the G06
MUST. A separate deformable TET4 `GREEN_LAGRANGE` probe reaches ten load
points and agrees in displacement/gap after contact activation, but its mapped
contact reaction differs by up to 76.7% and is not an identical multiplier
observable; it remains open comparison evidence. The finite-kinematic J2 path
remains experimental/research; no qualified coupled or physical-validation
claim is made. In the compared QF static route, contact is solved by the
historical exact active-set multiplier solver; the penalty formulation belongs
to the separate bounded research composition. Neither route establishes an
equivalent finite-sliding external correlation. CalculiX remains supporting
SHOULD evidence and cannot replace the missing Code_Aster MUST cells.
`CONTRACT LOWERED = NO`.

## Controlled closure: 025-G05

`025-G05` is `PASS` for the bounded contract in `025-REQ-018` through
`025-REQ-021`. The controlled evidence pack is archived under
`results/vnv_0_2_5/g05_latest/` and records source SHA
`a3ab8de707ffc88fc5e39e4f999eb872c9223b73` with `dirty=false`.

The targeted contact suite reports `82 passed / 2 skipped`. The internal pack
covers sparse common-driver assembly, fixed-active tangent FD (approximately
`6e-9`), open/close/recontact, updated normals, two-face and three-facet
traversal, facet-transition rollback, and penalty values from `1e2` through
`1e6`. The Code_Aster 18.1.0 Docker campaign compares ten-point histories for
the bounded corner, faceted-ramp and deformable TET4 cases; the 768-element
and 9,984-element replays both return `PASS_EXTERNAL_CORRELATION`. The 768-
element case retains an explicit transition observation: the second contact
activates at a different first load sample and the displacement-curve
difference is `4.33998 %`; the active-branch gap check remains below
`4.1e-16 m`. The 9,984-element confirmation removes that activation mismatch
for the recorded ten-point history.

The qualified claim is deliberately limited to frictionless penalty contact
from a slave node/patch to an explicitly supplied triangulated master surface,
with opt-in updated search and bounded finite-sliding projection. This is not
a mortar or segment-to-segment formulation and does not qualify unrestricted
surface-to-surface contact, self-contact, impact, friction or general large
sliding. The finite-sliding and updated-normal paths are internally qualified;
the external correlation is a bounded compatible normal-contact correlation.
CalculiX remains supporting evidence only and is not a G05 closure condition.

`CONTRACT_LOWERED = NO`. G05 closure does not close G06, G10, G11 or G12.

## STOP/GO policy

An `OPEN` or `BLOCKED` prerequisite forbids dependent implementation. Optional
independent branches may continue only when their full dependency chain is
closed. `NOT_IN_RELEASE_SCOPE` is acceptable only for predeclared optional work
and must not appear in README/package capability claims.
