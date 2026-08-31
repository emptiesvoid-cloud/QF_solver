---
doc_id: DOC-027-006
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 Master Plan

## Objective and boundary

The proposed theme is **Prismatic Solid Interoperability and Numerical
Robustness**. The plan targets a controlled WEDGE6 vertical slice, stronger
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
kernel; WP08-WP14 remain `NOT_STARTED`.

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
- **Status:** `NOT_STARTED`.

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
- **Status:** `NOT_STARTED`.

### WP10 - WEDGE6 modal qualification

- **Objective:** qualify only the modal route that has its own mass, boundary,
  residual, mode-shape and mesh evidence.
- **Dependencies:** WP08 and WP09.
- **GO:** first-mode and, if explicitly contracted, additional mode evidence
  has compatible analytical/external references.
- **STOP:** transferring static maturity to dynamics or hiding rigid modes and
  mass-convention assumptions.
- **Evidence required:** mass policy, eigenpair residuals, mode checks,
  refinement and replay.
- **Files:** modal contract, cases and evidence manifests.
- **Status:** `NOT_STARTED`.

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
- **Status:** `NOT_STARTED`.

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
- **Status:** `NOT_STARTED`.

### WP13 - Research and stretch selection

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

### WP14 - Documentation and release closeout

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
