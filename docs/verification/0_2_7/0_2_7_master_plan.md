---
doc_id: DOC-027-006
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 Master Plan and Level-Up Extension

## Objective and boundary

The foundation theme **Prismatic Solid Interoperability and Numerical
Robustness** is historical scope. The active official theme is
**Reproducible Large-Model Solving and Numerical Trust**. The Level-Up
extension targets reproducible large-model execution and numerical trust,
while preserving the controlled WEDGE6 vertical slice and stronger
cross-family contracts and better evidence. It does not authorize new physics
by itself. WEDGE15, PYRAMID5, TL HEX8, refined Arc-Length, finite-kinematic J2,
friction/finite sliding/mortar and HEX8R qualification are outside the
qualified 0.2.7 scope unless a future Owner decision explicitly changes it.

The plan starts from the tagged 0.2.6 baseline
`e839373b6aef291a93292186d7553ba5cd12af55`. WP01 release truth and
provenance is `PASS`; WP02 registry control is `PASS`; WP03 descriptor and
preflight control is `PASS`; WP04 harness control is `PASS`; WP05 external
oracle preflight is `PASS` for deck validation only; and WP06 mesh-quality
contract control is `PASS`. WP07 is now `PASS` for the experimental elemental
kernel; WP08 and WP09 are complete with their recorded bounded scope, WP10 has
completed its independent bounded modal qualification for the declared
consistent-mass route, WP11 records
`PASS_WITH_LIMITATIONS` with its Owner review closed by WP20, and WP12 retains
its bounded readiness status. The foundation WP01-WP12 history is preserved; the
Level-Up portfolio is `CLOSED / ACCEPT_WITH_CONSOLIDATION`; WP13 is now
`PASS` on its controlled golden-baseline evidence and WP14 is `PASS` on its
frozen execution contract; WP15 is `PASS_WITH_LIMITATIONS`, WP16 is `PASS`
after the official PETSc retry, WP17 is `PASS_WITH_LIMITATIONS`, WP18 is
`PASS_WITH_LIMITATIONS` after the Bronze/Silver ladder, WP19 is
`PASS_WITH_LIMITATIONS` on bounded adversarial and HEX8 diagnostic evidence,
WP20 is `PASS_WITH_LIMITATIONS` for the existing bounded small-strain J2
scope. WP21 is `PASS_WITH_LIMITATIONS` for surgical compatibility and
release-truth cleanup; WP22 remains `PLANNED` for final Owner release action.

## Work packages and STOP/GO criteria

### WP01 - Release truth and provenance

- **Objective:** establish one authoritative baseline, version, branch and
  evidence-SHA vocabulary for 0.2.7.
- **Dependencies:** none.
- **GO:** exact baseline, clean-state record, package/tag separation and
  reproducible manifest rules are reviewed.
- **STOP:** SHA/version/tag ambiguity, dirty baseline or historical evidence
  silently reused as current evidence.
- **Evidence required:** baseline manifest, release-state audit and provenance
  checklist.
- **Files:** `qualification/0_2_7/manifest.json`, release notes and provenance
  records.
- **Status:** `PASS` (release-truth foundation only).

### WP02 - Capability registry v2

- **Objective:** represent capability maturity at element x analysis x
  material x route granularity.
- **Dependencies:** WP01.
- **GO:** unique IDs, source sentinels, evidence links, exclusions and
  machine-readable status validation pass.
- **STOP:** maturity inferred from implementation, duplicate rows, orphan
  implementation or missing public combination.
- **Evidence required:** registry schema, migration mapping and audit output.
- **Files:** `qualification/0_2_7/requirements.json`, registry migration
  records and coverage matrix.
- **Status:** `PASS` for the registry control; no numerical capability was promoted.

### WP03 - Element descriptors and compatibility preflight

- **Objective:** describe element topology, DOFs, faces, quadrature, loads and
  supported analysis/material routes before execution.
- **Dependencies:** WP02.
- **GO:** deterministic preflight accepts supported combinations and rejects
  unsupported ones without changing default numerical behavior.
- **STOP:** implicit fallback, misleading support claim, public API break or
  compatibility decision hidden in runner code.
- **Evidence required:** descriptor schema, accept/reject table and negative
  tests.
- **Files:** descriptor contract, preflight evidence and targeted tests.
- **Status:** `PASS` for the technical descriptor and preflight control; no
  numerical capability was promoted.

### WP04 - Declarative V&V harness

- **Objective:** add a small declarative runner for new cases without a
  massive refactor of the existing verification modules.
- **Dependencies:** WP01 and WP02.
- **GO:** case schema, oracle adapters, manifest/digest output and deterministic
  replay pass on a small fixture corpus.
- **STOP:** arbitrary command execution, changed solver route, hidden defaults
  or loss of old evidence.
- **Evidence required:** schema tests, fixture replay and migration boundary.
- **Files:** additive harness modules, case definitions and tests.
- **Status:** `PASS` for the additive harness contract and representative
  migration samples; no numerical source was changed.

### WP05 - External oracle preflight

- **Objective:** establish whether C3D6/PENTA6 comparisons are actually
  available and comparable before WEDGE6 implementation.
- **Dependencies:** WP01 and WP02.
- **GO:** pinned tool/version, node order, quadrature, face convention,
  observable mapping and reproducible deck contract are recorded.
- **STOP:** unavailable tool represented as PASS, incompatible kinematics or
  untransformable observables.
- **Evidence required:** preflight report, deck templates and availability
  classification.
- **Files:** `0_2_7_external_oracle_plan.md`, the WEDGE6 external review pack,
  deck metadata and manifests.
- **Status:** `PASS` for local-only deck preflight; no WEDGE6 implementation or
  QF/external correlation is claimed.

### WP06 - Mesh quality and distortion contract

- **Objective:** define quality, Jacobian, orientation, distortion and
  conditioning diagnostics that apply across element families.
- **Dependencies:** WP02 and WP03.
- **GO:** metrics, invalid cases, reproducible sampling and Owner policy exist.
- **STOP:** universal aspect-ratio cutoff, mesh quality inferred from one scalar
  or failed cases hidden by a solver retry.
- **Evidence required:** quality schema, controlled mesh set and failure tests.
- **Files:** `0_2_7_mesh_quality_plan.md`, metric definitions and reports.
- **Status:** `PASS` for the additive diagnostic contract; no universal quality
  threshold or new numerical capability was introduced.

### WP07 - WEDGE6 kernel and elemental V&V

- **Objective:** implement and verify the reviewed WEDGE6 formulation within
  the elemental small-strain elastic scope.
- **Dependencies:** WP03, WP05 and WP06.
- **GO:** the reviewed shape functions, integration and geometry certificate
  are implemented; elemental invariants, stiffness/recovery and deterministic
  evidence pass while public maturity remains `EXPERIMENTAL`.
- **STOP:** certified inversion is not rejected, rank or rigid-body behavior is
  unexpected, or an existing formulation is modified.
- **Evidence required:** implementation, targeted V&V catalog/evidence and
  experimental maturity decision.
- **Files:** WEDGE6 kernel, formulation contract, quality/preflight integration,
  targeted tests and `wp07_state.json`.
- **Status:** `PASS` (`EXPERIMENTAL` elemental kernel only).

### WP08 - WEDGE6 static vertical slice

- **Objective:** add only the smallest static path needed to exercise WEDGE6
  import, faces, loads, BCs, reactions and stress/post-processing.
- **Dependencies:** WP07.
- **GO:** static patch/constant-strain, equilibrium, Gmsh, face loads, error
  handling and maintained example pass.
- **STOP:** incomplete face mapping, silent unsupported input, source-tree-only
  example or result without provenance.
- **Evidence required:** case manifest, analytical checks, mesh levels and
  reproducible smoke.
- **Files:** WEDGE6 implementation and its focused tests, only after WP07.
- **Status:** `PASS_WITH_LIMITATIONS` for independent experimental evidence.

### WP09 - WEDGE6 robustness and external V&V

- **Objective:** test distortion, orientation, quality, load paths, failure
  modes and comparable C3D6/PENTA6 results.
- **Dependencies:** WP08.
- **GO:** declared mesh/refinement/quality matrix and independent correlation
  support the proposed bounded static claim.
- **STOP:** unexplained divergence, threshold weakening or non-comparable
  external result presented as validation.
- **Evidence required:** internal and external manifests, negative cases and
  Owner classification.
- **Files:** WEDGE6 campaign records and external correlation pack.
- **Status:** `PASS_WITH_LIMITATIONS`; Owner review is required and the existing
  bounded small-strain J2 scope is retained.

### WP10 - WEDGE6 modal qualification closure

- **Objective:** qualify only the modal route that has its own mass, boundary,
  residual, mode-shape and mesh evidence.
- **Dependencies:** WP08 and WP09.
- **GO:** consistent-mass modal invariants, first-three-mode refinement,
  deterministic replay and compatible external frequency/MAC evidence are
  recorded under a bounded Owner policy.
- **STOP:** transferring static maturity to dynamics or hiding rigid modes and
  mass-convention assumptions.
- **Evidence required:** mass policy, eigenpair residuals, mode checks,
  first-three-mode refinement, frequency/MAC matching and replay.
- **Files:** modal contract, final cases, final evidence and Owner state.
- **Status:** `PASS_WITH_LIMITATIONS`; modal maturity is
  `QUALIFIED_BOUNDED` only for the declared consistent-mass WEDGE6 scope.

### WP11 - Existing capability maturity and J2 gaps

- **Objective:** close high-value V&V gaps in existing TET4/TET10/HEX8/HEX20
  small-strain J2 without changing the formulation.
- **Dependencies:** WP01, WP04 and WP06.
- **GO:** increment sensitivity, tangent checks, failure handling and
  cross-family evidence are complete or explicitly bounded.
- **STOP:** finite-kinematic promotion, weakened tolerance or formulation
  change disguised as V&V work.
- **Evidence required:** predeclared policies, all-family records and Owner
  decision.
- **Files:** J2 gap-closure contract and evidence manifests.
- **Status:** `PASS_WITH_LIMITATIONS`; Owner closure is recorded by WP20 and
  the existing bounded J2 qualification is retained.

### WP12 - Large-scale and 1M-DOF readiness

- **Objective:** characterize model creation, assembly, solve and memory
  boundaries without promising universal 1M-DOF support.
- **Dependencies:** WP02, WP04 and WP06.
- **GO:** 100k/300k/500k/1M measurements have hardware, topology and resource
  context; resource limitation is an explicit result.
- **STOP:** missing resource data, incomparable runs or an unqualified
  scalability claim.
- **Evidence required:** timing/RAM/nnz/residual manifests and verdict matrix.
- **Files:** `0_2_7_1m_dof_plan.md` and benchmark outputs.
- **Status:** `PASS_WITH_LIMITATIONS`; bounded evidence recorded, Owner review
  pending.

### Historical foundation WP13 - Research and stretch selection

- **Objective:** select only high-value research candidates after the core
  contracts are stable.
- **Dependencies:** applicable closed prerequisites from WP06-WP12.
- **GO:** explicit Owner selection with a small experiment and a bounded
  classification.
- **STOP:** WEDGE15/PYRAMID5/TL HEX8/finite J2/coupled physics or HEX8R being
  promoted by adjacency or test count.
- **Evidence required:** choice record, risk review and non-qualification
  statement where appropriate.
- **Files:** `0_2_7_owner_decision_log.md`, research evidence only.
- **Status:** `NOT_STARTED`.

### Historical foundation WP14 - Documentation and release closeout

- **Objective:** reconcile registry, docs, package, reproducibility, full
  regression and Owner release decision.
- **Dependencies:** WP01-WP13 as applicable to the final scope.
- **GO:** clean source, package/install checks, T3 results, safe claims and
  signed Owner closeout.
- **STOP:** stale claims, missing manifests, numerical regression, package
  drift or unresolved public capability.
- **Evidence required:** release criteria, final test matrix, archive audit and
  Owner decision.
- **Files:** release notes, final manifests and public documentation.
- **Status:** `NOT_STARTED`.

## Order rule

The architecture and evidence contracts preceded the WP07 numerical proof.
WP07 is complete only for the experimental elemental kernel; WP08 must add the
static/import/load/post workflow before any user-facing WEDGE6 claim. Stretch
work is optional and cannot delay a bounded core unless it changes a public
claim.

## Level-Up 1 historical extension

The active official theme is **Reproducible Large-Model Solving and Numerical
Trust**. The portfolio decision is `CLOSED / ACCEPT_WITH_CONSOLIDATION` for
the scope extension only. WP01-WP12 and their evidence remain preserved;
WP13 and WP14 are complete on their controlled records; WP15 is
`PASS_WITH_LIMITATIONS` on its controlled subscale evidence, WP16 is `PASS`
on the official PETSc retry, WP17 is `PASS_WITH_LIMITATIONS`, WP18 is
`PASS_WITH_LIMITATIONS` after its Bronze/Silver evidence, WP19 is
`PASS_WITH_LIMITATIONS` on bounded adversarial and HEX8 diagnostic evidence,
and WP20 is `PASS_WITH_LIMITATIONS` for the existing bounded J2 scope. WP21
is `PASS_WITH_LIMITATIONS` after its surgical cleanup evidence; WP22 remains
`PLANNED` until its own final release evidence is recorded.

| WP | Title | Weight | Priority | Status |
| --- | --- | ---: | --- | --- |
| WP13 | Release truth and golden numerical baseline | 4% | MUST | `PASS` |
| WP14 | Large-scale execution contract | 5% | MUST | `PASS` |
| WP15 | Matrix-Free TET4 V2 / SPD / preconditioning | 10% | MUST | `PASS_WITH_LIMITATIONS` |
| WP16 | True 1M DOF qualification | 10% | MUST / release blocker | `PASS` |
| WP17 | PETSc/MPI + large sparse path | 5% | SHOULD | `PASS_WITH_LIMITATIONS` |
| WP18 | 3M DOF ladder Bronze/Silver/Gold | 7% | MUST / mandatory | `PASS_WITH_LIMITATIONS` |
| WP19 | Adversarial robustness + HEX8 diagnostic | 5% | MUST | `PASS_WITH_LIMITATIONS` |
| WP20 | Residual J2 / external V&V closure | 3% | SHOULD | `PASS_WITH_LIMITATIONS` |
| WP21 | Architecture/API/registry surgical cleanup | 3% | SHOULD | `PASS_WITH_LIMITATIONS` |
| WP22 | Final Release Qualification | 3% | MUST | `PLANNED` |

Machine-readable criteria are in `qualification/0_2_7/level_up_plan.json`.
WP16 required a true 1M FEM iterative solve with reactions, residual,
equilibrium, energy, subscale comparison and two replays. WP18 separates
Bronze model/resource preflight, Silver full solve and Gold distributed/restart
evidence; Bronze alone authorizes no 3M solve claim. WP18 Silver completed two
3M true-DOF solves on the declared structured TET4 PETSc/MPI route. Gold
remains `NOT_ATTEMPTED` because no restart/checkpoint or distinct second
physical case was run; no Gold claim is made.

The following remain deferred to 0.2.8+: mixed TET/WEDGE/HEX, WEDGE15,
PYRAMID5, production HEX8R/SRI/B-bar, finite-kinematic J2, TL HEX8, refined
Arc-Length, new nonlinear couplings, matrix-free multi-family and general
Newmark/harmonic qualification.

## WP19 - Adversarial robustness and HEX8 diagnostic

WP19 is `PASS_WITH_LIMITATIONS` for the 24-case adversarial catalog and the
bounded HEX8 diagnostic. The execution source SHA is
`dc5975b78727d9dca6d0a48b716e60f355b8799f`; the lot started at
`7f7ffbaf0b3fdda7d3ad31ba95f20a54e4719a53`. Ten positive cases passed and 14
predeclared failure cases returned `EXPECTED_FAILURE_PASS`; replay was
deterministic, all failure paths were fail-closed, and no NaN/Inf result was
accepted.

The HEX8 study covers three axial-refinement, three slenderness and three
transverse-resolution rows. Six same-mesh CalculiX 2.20/C3D8 displacement
comparisons pass the existing one-percent diagnostic threshold, with maximum
full-displacement relative error `1.997130986610937e-06`. The inherited deck
does not request reaction or energy outputs, so those external observables are
`NOT_COMPARABLE`. Agreement between QF and C3D8 while both deviate from the
Euler diagnostic supports `LOW_ORDER_LIMITATION` with secondary
`MESH_DEPENDENCE`; locking is compatible with the observation but not proven.
No HEX8R/SRI/B-bar formulation is evaluated or promoted, and no QF-specific
bug was found.

The authoritative records are `qualification/0_2_7/wp19_state.json`,
`qualification/0_2_7/wp19_cases.json`,
`qualification/0_2_7/wp19_runtime/wp19_robustness_summary.json`,
`qualification/0_2_7/wp19_runtime/wp19_hex8_diagnostic.json` and
`qualification/0_2_7/wp19_runtime/wp19_golden_replay.json`. WP20 is closed with
its existing bounded J2 scope; previous maturity decisions remain unchanged.
WP21 is closed with `PASS_WITH_LIMITATIONS`, and WP22 is next.

## WP20 - Residual J2 / external V&V closure

WP20 is `PASS_WITH_LIMITATIONS` with Owner decision
`OWNER_APPROVED_BOUNDED_KEEP_EXISTING_SCOPE`. It closes the residual review of
the existing small-strain J2 route without changing the FEM formulation or
promoting a capability. TET4, TET10, HEX8 and HEX20 remain qualified only in
the existing bounded scope: isotropic small-strain J2, radial return and full
Newton for nonlinear static use.

The controlled evidence records passing return mapping, yield detection,
unload/reload, simple cycling, tangent finite differences, increment
characterization, rollback, energy, cross-family consistency, explicit
failure modes, no NaN/Inf and deterministic replay. The maximum tangent FD
error is `2.120472111937634E-10` against the existing `1E-6` limit. There is
no universal structural increment threshold; tangent symmetry and modified
Newton behavior remain diagnostics.

The external part is `PARTIAL_REUSED_CONTROLLED_EVIDENCE`: Code_Aster 18.1.0
constitutive evidence from G06 is reused for all four families. No new
structural external campaign or post-result tolerance retuning is claimed.
Finite-kinematic J2 remains experimental/not qualified. See
`qualification/0_2_7/wp20_state.json` and
`docs/verification/0_2_7/0_2_7_wp20_j2_closeout.md`.

## Level-Up 2: active large-model program

The previous Level-Up portfolio is now treated as **Level-Up 1**: its
qualification evidence is preserved and its program block is `50/50 CLOSED`.
The active namespace is **`027-LEVEL-UP-2`**, starting from the qualified
baseline `8f08bfb5a6d4dedcd24966f5474e8c12cbfa5bc3`. LU2 has acquired `46/50`
through the completed WP01 observatory, bounded WP02 configuration freeze,
WP03 Gold Compute, LU2-WP06 execution/recovery closeout, the LU2-WP07 route
maturity audit and the LU2-WP08 decision closeout, with LU2-WP04 Bronze and
LU2-WP05 Silver now closed, so the current global progress is `96/100`; these values replace the older
non-additive accounting view for active planning without rewriting any
historical result.

The machine-readable source of truth is
`qualification/0_2_7/level_up_2_plan.json`, with state and navigation records
in `level_up_2_state.json` and `level_up_2_index.json`.

| LU2 work package | Focus | Weight | Priority | Current status |
| --- | --- | ---: | --- | --- |
| LU2-WP01 | Evidence and Performance Observatory | 4% | MUST | `PASS` |
| LU2-WP02 | CPU/MPI/GAMG readiness and configuration freeze | 9% | MUST | `PASS_WITH_LIMITATIONS` |
| LU2-WP03 | 3M Gold Compute | 9% | MUST | `PASS_WITH_LIMITATIONS` |
| LU2-WP04 | 5M Bronze | 5% | MUST | `PASS` |
| LU2-WP05 | 5M Silver | 9% | MUST | `PASS` |
| LU2-WP06 | Execution Contract / Recovery / Diagnostics | 4% | MUST | `PASS_WITH_LIMITATIONS` |
| LU2-WP07 | Existing Routes Maturity and Targeted V&V | 4% | SHOULD | `PASS_WITH_LIMITATIONS` |
| LU2-WP08 | Mixed / WEDGE15 / PYRAMID5 / HEX8 Decisions | 2% | SHOULD | `PASS_WITH_LIMITATIONS` |
| LU2-WP09 | Release Truth / Registry / CI / Final Qualification | 4% | MUST | `NOT_STARTED` |

The 3M Gold contract retains the existing Silver case and requires a
materially distinct second 3M FEM workload with two replays. The claim is
limited to structured TET4 linear-static execution on the recorded machine
and MPI configuration; restart is not required for Gold Compute. The 5M
Bronze contract requires two deterministic constructions, matching DOF,
partition, ownership and digests, distributed operator construction and
preconditioner setup under declared resource budgets, but creates no solve
claim. The 5M Silver contract requires a complete two-replay solve with the
frozen MPI configuration, residual/equilibrium/energy/finiteness checks and
no post-result retuning. The MPI V2 contract targets 2, 4 and 8 ranks on one
host, requires 3M strong-scaling measurements, and treats unavailable 8-rank
execution as `PASS_WITH_LIMITATIONS`, never as `FULL`.

C1 (matrix-free TET4 capacity), C2 (GPU foundation) and C3 (10M capacity)
are installed as zero-weight conditional gates. C1 remains dormant because
the WP04 time-budget overrun was observed during an owner-interrupted run
without persisted progress/resource telemetry; C2 requires real GPU evidence;
C3 requires 5M Silver first and can never block LU2. New physics, production
HEX8R/SRI/B-bar, WEDGE15, PYRAMID5, finite-kinematic J2, TL HEX8, refined
Arc-Length, new nonlinear couplings, matrix-free multi-family and general
Newmark/harmonic qualification remain deferred to 0.2.8+.

### LU2-WP08 decision closeout

LU2-WP08 is closed as `PASS_WITH_LIMITATIONS` from the controlled decision
matrix `qualification/0_2_7/lu2_wp08_decision_matrix.json`. Mixed
TET/WEDGE/HEX is `PARTIAL` technically but has no qualified end-to-end
contract and is deferred. WEDGE15 and PYRAMID5 are not supported or active
capabilities and remain deferred. The existing HEX8 route remains bounded;
WP19 is a diagnostic, not proof of a universal locking correction. HEX8R,
SRI and B-bar are research-only decisions, and hourglass control is deferred
with reduced integration. No implementation, large benchmark or maturity
promotion occurred. The earlier owner-interrupted WP04 attempt is preserved as
historical forensic evidence; the corrected WP04 Bronze and WP05 Silver gates
are now closed under the unchanged freeze.

LU2-WP02 is recorded in the controlled execution index
`qualification/0_2_7/wp02_runtime/wp02_evidence_index.json` and freeze
`qualification/0_2_7/wp02_runtime/wp02_config_freeze.json`, under the
predeclared contract `qualification/0_2_7/wp02_execution_contract.json`.
The same 3M structured TET4 workload passed at 2, 4 and 8 MPI ranks on the
recorded Docker host. GAMG and contiguous partitioning were selected from
characterized subscale alternatives. Preflight, redistribution,
communication and I/O remain explicitly unmeasured because the legacy runner
does not expose separate boundaries; no phase is inferred from total time.
The claim is consequently bounded to the recorded host, image, input and
configuration. The machine-readable closeout is
`qualification/0_2_7/wp02_state.json`.

LU2-WP03 is closed as `PASS_WITH_LIMITATIONS`, with
`3M_GOLD_COMPUTE = PASS`. The existing WP18 Silver case is retained as
Workload A, and a materially distinct 3,000,000-DOF structured TET4 workload
completed two replays under the exact WP02 freeze. The contract, preflight,
Observatory records, replay comparison and descriptive A/B comparison are
listed in `qualification/0_2_7/wp03_runtime/wp03_evidence_index.json` and
summarized in
`docs/verification/0_2_7/0_2_7_wp03_3m_gold_compute.md`. The claim is limited
to the recorded single-host Docker/PETSc/MPI route; preflight, redistribution,
communication and I/O are explicitly not measured, and no universal,
multi-node, GPU, mixed-mesh, nonlinear or restart claim is made. LU2-WP04 was
then attempted on a real `5,012,640`-DOF TET4 workload. Two independent model
constructions and the resource preflight passed, but the owner-interrupted
container remained CPU-active in frozen AIJ operator assembly without a
completion record. The attempt is therefore
`PASS`, with the earlier owner-interrupted attempt retained as historical
forensic evidence. LU2-WP05 subsequently completed the two-replay 5M Silver
solve under the unchanged freeze. C1 is not confirmed; LU2 is at `96/100` and
LU2-WP09 is the next active gate.

LU2-WP01 is recorded in `qualification/0_2_7/observatory_contract.json` with
the controlled fixture `qualification/0_2_7/wp01_observatory_sample.json`.
The observatory is opt-in, rejects incomplete or non-finite PASS-like
evidence, and does not infer a performance regression or improvement from a
comparison.

`DECISION_GATE_1 = CONTINUE_TO_LEVEL_UP_2` is closed. After LU2-WP09,
`FINAL_DECISION_GATE` permits only an explicit `RELEASE` or `NEW_LEVEL_UP`
decision; there is no automatic release. The WP02 execution used the
controlled 3M evidence run; the setup commit itself ran no heavy benchmark,
changed no numerical source and performed no publication action.
