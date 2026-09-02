---
doc_id: DOC-027-013
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 Owner Decision Log

This log preserves the foundation decisions and records the Terra-authorized
WP07 technical implementation separately from public qualification.

| Decision ID | Topic | Proposed state | Decision | Evidence/SHA | Date |
| --- | --- | --- | --- | --- | --- |
| 027-OD-001 | WEDGE6 formulation and scope | `PROPOSED_OWNER_REVIEW` | pending | WP05/WP06/WP07 | - |
| 027-OD-002 | mesh-quality policies | `PROPOSED_OWNER_REVIEW` | pending | WP06 | - |
| 027-OD-003 | external C3D6/PENTA6 comparability | `PROPOSED_OWNER_REVIEW` | pending | WP05 | - |
| 027-OD-004 | J2 gap-closure policies | `OWNER_APPROVED_BOUNDED_KEEP_EXISTING_SCOPE` | `KEEP_QUALIFIED_BOUNDED_WITH_LIMITATIONS` | WP20, `94461602dfd1782be57c20e1801a0d5d8e262ef1` | 2026-09-01 |
| 027-OD-005 | 1M-DOF verdict and public boundary | `PROPOSED_OWNER_REVIEW` | pending | WP12 | - |
| 027-OD-006 | stretch/research selection | `PROPOSED_OWNER_REVIEW` | pending | WP13 | - |
| 027-OD-007 | final release scope | `PROPOSED_OWNER_REVIEW` | pending | WP14 | - |
| 027-OD-008 | WEDGE6 elemental kernel | `TERRA_GO` | `PASS_TECHNICAL_EXPERIMENTAL_ONLY` | T1-R4, WP07 evidence | 2026-08-31 |
| 027-OD-009 | WEDGE6 static vertical slice | `WP08_REVIEWED` | `PASS_TECHNICAL_EXPERIMENTAL_ONLY` | WP08 state/evidence, 8040909d6d65f740e1daf858ce572d250a87b39a | 2026-08-31 |
| 027-OD-010 | residual J2 and external V&V closure | `OWNER_APPROVED_BOUNDED_KEEP_EXISTING_SCOPE` | `PASS_WITH_LIMITATIONS` | `qualification/0_2_7/wp20_state.json`, `94461602dfd1782be57c20e1801a0d5d8e262ef1` | 2026-09-01 |
| 027-OD-011 | WP21 architecture/API/registry and release-truth cleanup | `OWNER_REVIEWED_BOUNDED` | `PASS_WITH_LIMITATIONS` | `qualification/0_2_7/wp21_state.json`, `qualification/0_2_7/wp21_final_release_truth.json`, `0f565dc9669763751a75f13b02004bde18af571c` | 2026-09-01 |

WP01 is a release-engineering foundation control rather than a numerical Owner
qualification decision. Its status is `PASS` because the SHA roles, actual
0.2.6 publication state, artifact classes and tag/version guard are recorded in
the WP01 machine-readable records. This does not approve any 0.2.7 capability.

WP02 is a registry-engineering foundation control rather than a new capability
qualification decision. Its status is `PASS` because the v2 source of truth
preserves all 33 public legacy identifiers, exposes 44 combination records,
keeps historical statuses out of the active vocabulary, and passes deterministic
schema, migration and generated-view checks. Inherited `QUALIFIED_BOUNDED`
states remain bounded 0.2.6 scope; this work package introduces no new evidence
or promotion.

WP03 is a compatibility-engineering foundation control rather than a new
capability qualification decision. Its descriptors describe technical routing
for existing element families, while the v2 registry remains the source of
maturity. The preflight is fail-closed and reports supported, experimental,
non-qualified and unsupported routes distinctly. Targeted descriptor, workflow
and analysis tests pass; no numerical source or Owner maturity decision was
changed.

WP05 is an external-oracle engineering control rather than a WEDGE6
qualification decision. The pinned Docker runs validated one minimal CalculiX
C3D6 deck and one Code_Aster PENTA6 deck locally. Both oracle routes are
`AVAILABLE_LOCAL_ONLY`; no QF WEDGE6 implementation, comparison verdict or
public capability was created. The eight future benchmarks remain `PLANNED`,
and the comparability tolerance remains `OWNER_REVIEW_REQUIRED`.

The WP05 preflight is `PASS` with the local-only limitation recorded in the
machine-readable contract and review pack. This does not authorize WP07 or
change any existing 0.2.6 decision.

WP04 is an additive V&V-engineering control rather than a capability
qualification decision. Its declarative case/oracle schema, runner verdicts,
canonical evidence serialization and replay mismatch checks pass on three
representative fixtures. Historical V&V runners remain supported; no numerical
source or maturity decision was changed.

WP06 is an additive mesh-quality control rather than a numerical capability
qualification. The common contract covers TET4, TET10, HEX8 and HEX20 with
deterministic `VALID`, `VALID_WITH_WARNING` and `INVALID` classifications,
and invalid geometry is surfaced by preflight as `MESH_GEOMETRY_INVALID`. No
universal aspect-ratio or conditioning threshold was approved; inherited
family diagnostics retain their legacy provenance. Rigid-transform,
dimensionless-scale, inversion, duplicate-node and serialization checks pass.
The WEDGE6 quality contract is prepared only as an inactive future schema and
`WEDGE6_IMPLEMENTED` remains `NO`. This status records engineering evidence
and does not promote any capability.

An entry may be changed to an approved state only with a decision owner, exact
evidence SHA, scope, limitations and date. No decision here reopens G07 or
changes any 0.2.6 maturity classification.

T1-R is a remediation checkpoint, not an Owner qualification decision. It
records the inactive WEDGE6 formulation, quadrature candidate and richer
verification reference, asymmetric node/face fixture, prism Jacobian validity
controls, stiffness/mass V&V obligations and external primary observables.
Its targeted tests pass and no WEDGE6 capability or kernel is exposed. The
checkpoint is ready for Terra/Owner re-review; WP07 remains `NOT_STARTED` and
kernel authorization remains `OWNER_REVIEW_REQUIRED`.

T1-R3 closes the two review findings that remained open. The inactive quality
contract now specifies a scale-aware certified minimum: at fixed triangular
coordinates `det(J)` is quadratic in `t`, so endpoints and every interior
stationary point are checked at each triangular vertex. Quadrature, face and
interior samples are diagnostics only. The Terra adversarial prism is rejected
by this certificate, with no automatic repair and no WEDGE6 kernel exposure.

The WEDGE6 external contract has one unique primary-observable declaration,
strict duplicate-key JSON loading, an affine same-mesh `1e-6` candidate marked
`OWNER_REVIEW_REQUIRED`, and mandatory case-specific Owner approval for
non-affine, distorted or refinement cases. Post-observation tolerance retuning
is forbidden. T1-R3 is ready for Terra re-review; WP07 remains `NOT_STARTED`
and kernel authorization remains `OWNER_REVIEW_REQUIRED`.

## WP07 technical implementation decision

Terra High's T1-R4 review authorized implementation after all six original
pre-WP07 blockers were closed. WP07 is `PASS` for the six-node, 18-DOF
small-strain homogeneous-isotropic elastic elemental kernel and its targeted
V&V. Evidence covers shape identities, affine constant strain, exact Jacobian
certificate, stiffness symmetry, rank 12 with six rigid-body modes, prescribed
load-state tests, distorted geometry, energy and production/reference
quadrature replay.

This is not a public qualification. The registry maturity for
`COMB-WEDGE6-linear_static` is `EXPERIMENTAL`, and preflight returns
`EXPERIMENTAL_ROUTE`. Gmsh import, face loads, user-level assembly and
reactions, modal/dynamic routes, nonlinear materials, contact and external
correlation were deferred to WP08 and later gates. Existing TET/HEX
formulations and their evidence are unchanged.

## WP08 static vertical-slice decision

WP08 is `PASS` for the bounded six-node Gmsh Prism 6 static workflow. The
15-case controlled evidence contains 14 `PASS` results and one
`EXPECTED_FAILURE_PASS` for fail-closed rejection of inverted geometry, with
no unexpected failures. It covers canonical TRI3/QUAD4 face mapping, nodal
and distributed loads, sparse static assembly, reactions, force and moment
equilibrium, constraints and displacement/strain/stress/energy recovery.

This decision does not promote WEDGE6: `COMB-WEDGE6-linear_static` remains
`EXPERIMENTAL` and public qualification is `DEFERRED`. Modal/Newmark/harmonic,
nonlinear, J2, TL, contact, robustness and external-correlation claims remain
outside this gate and require their own evidence.

## WP09 robustness and external V&V decision

WP09 is `PASS_WITH_LIMITATIONS` for the declared WEDGE6 static robustness
campaign. The controlled evidence contains 22 cases: 18 internal `PASS`
results and four `EXPECTED_FAILURE_PASS` results for inverted geometry, wrong
node ordering, malformed Gmsh input and singular boundary conditions. Aspect,
skew, near-degenerate, rigid-transform, scale-invariance, multi-element,
refinement and deterministic replay checks are recorded without changing the
kernel or existing element numerics.

The external results remain explicitly non-qualifying. CalculiX C3D6 completed
the affine deck locally, but its two-point integration route is not
formulation-compatible with QF WEDGE6 production `TRI3_X_GAUSS2` integration;
the displacement and energy differences are retained as diagnostics, not as a
failure or a pass. Code_Aster PENTA6 is now executed through the WP09-R
derived headless image: `mpi4py` was present in the pinned image's Spack view
but was not exposed by the stock profile, and `--no-mpi` does not bypass that
import. One affine same-mesh correlation passes for displacement, total
reaction and strain energy under the predeclared `1e-6` candidate, which remains
`OWNER_REVIEW_REQUIRED`. No pressure, refinement or distorted external
correlation is claimed. WEDGE6 remains
`EXPERIMENTAL` and public qualification remains `DEFERRED`; WP10 may proceed
under its separate modal contract.

## WP09-FINAL external qualification closure

WP09-FINAL is recorded as `PASS_WITH_LIMITATIONS` for a bounded external
Code_Aster PENTA6 campaign. The run is sourced from
`4b2fcdc9ed51821b05b52851912be3ebbe764b14` and contains 12 deterministic cases:
affine tension/compression, shear, bending, TRI3 pressure, QUAD4 pressure,
prescribed displacement, a conforming multi-element mesh, a declared
affine-skew prism and refinement levels 1, 2 and 4. The headless derived image
is Code_Aster 18.1.0 with one launcher process and no GUI.

Displacement, total reaction and strain energy are the primary observables.
All 12 cases pass the predeclared comparisons; maximum relative errors are
`2.93e-15`, `3.60e-15` and `2.48e-15`. The `1e-6` affine candidate and the
`1e-5` refinement/distortion candidates were fixed before execution and remain
`OWNER_REVIEW_REQUIRED`; no post-result retuning occurred. CalculiX C3D6 is
`NOT_COMPARABLE` under the controlled integration convention and supplies no
qualification verdict.

This closes the WP09 external evidence gap without promoting WEDGE6. The
public maturity remains `EXPERIMENTAL` and public qualification remains
`DEFERRED`. The evidence is bounded to the declared homogeneous-isotropic,
small-strain, linear-static WEDGE6/PENTA6 slice and does not qualify modal,
dynamic, nonlinear, J2, TL, contact, stress-extrapolation or general physical
validation routes. The prior 22-case internal WP09 corpus remains preserved.

## WP10-FINAL modal qualification decision

WP10-FINAL is `PASS` within a bounded scope, while gate `027-G10` remains
`PASS_WITH_LIMITATIONS`. The active Owner decision is
`OWNER_APPROVED_BOUNDED_FIRST_THREE_MODES` for homogeneous isotropic
small-strain WEDGE6 with consistent translational mass. The final policy was
fixed before replay: normalized eigenpair residual `<= 1e-7`, same-mesh
frequency error `<= 1e-2`, MAC `>= 0.99`, near-degenerate subspace matching for
relative gaps `<= 1e-5`, and final adjacent refinement change `<= 1e-2` for
the first three frequencies. Post-result retuning is forbidden.

The four-level sequence 4/8/16/32 passes the refinement rule for the first
three modes; modes four to six remain diagnostic because the fourth final
change is `1.075439%`. Code_Aster 18.1.0/PENTA6 headless comparisons pass on
four same-mesh cases (axial single, bending multi-prism, distorted valid prism
and multi-WEDGE): all `24/24` modes match, the maximum frequency error is
`1.927e-13`, and the minimum MAC is `0.9999999999999991`. The evidence is
tied to source SHA `9d79dc8b306e6cc65f2f4ae2e77e00f676182b84`, the final case
catalog and the pinned Code_Aster image.

`COMB-WEDGE6-modal` is now `QUALIFIED_BOUNDED` only for this declared route
and scope. Static evidence is not transferred automatically. Lumped mass,
Newmark, harmonic, nonlinear, J2, TL, contact and general dynamics remain
outside WP10. The previous 16-case WP10 records remain preserved as historical
evidence; the active final records are the `wp10_final_*` artifacts.

## WP12 large-scale readiness checkpoint

WP12 is recorded as `PASS_WITH_LIMITATIONS` for a bounded readiness study of
the existing generated structured TET4 linear-static route. The campaign
completed matrix-free CG through 750141 DOF, recorded a separate 311469-DOF
assembly-only probe, and classified the 1M attempt as `RESOURCE_LIMITED_TIME`.
SciPy CG/direct limits and PETSc/SLEPc unavailability are explicit. The
optimization caches existing grouped connectivity and flattened DOF indices in
the matrix-free operator; targeted numerical equivalence passes and no FEM
formulation changed. This is evidence for `027-OD-005`, not an Owner closeout:
the decision remains `PROPOSED_OWNER_REVIEW`, and no universal 1M claim is
made.

## WP11 - Existing small-strain J2 maturity

WP11 is recorded as `PASS_WITH_LIMITATIONS`; WP20 closes Owner review of the
bounded maturity record. The existing `MAT-J2-SMALL` qualification is kept for
TET4, TET10, HEX8 and HEX20; no capability is promoted or demoted. The
controlled evidence covers material state transitions, radial return, finite
difference tangent checks, unload/reload and cycling, multi-element response,
energy, rollback, increment sensitivity, full-Newton behavior and explicit
failure modes.

The source under test is `94461602dfd1782be57c20e1801a0d5d8e262ef1`, from a
WP11 start at `4d0ee14f4aa61b9337874a991263a93b4f9a8c73`. The maximum tangent
FD error is `2.1204721119376345e-10` against the existing `1e-6` limit.
Increment partition results are characterization only: no universal
structural independence threshold is introduced. Tangent symmetry remains a
diagnostic, modified Newton remains diagnostic, finite-kinematic J2 remains
experimental/not qualified, and no new external structural run is claimed.

## WP15 - Matrix-free TET4 V2 / SPD / preconditioning

Date: 2026-09-01. Execution source snapshot:
`6e20bc53d175e5b4eac37a1e76f13266998ce074`; baseline snapshot:
`2a12f04479eb085137c1d586c99bcf191e702ccc`.

Owner decision: `PASS_WITH_LIMITATIONS`. The structured homogeneous TET4
matrix-free route matches the assembled subscale action, displacement and
energy within the frozen WP14 limits on 81, 375, 2,187 and 14,739 DOF. The
deterministic SPD checks, residual, equilibrium and energy evidence pass.

Private operator workspaces are retained because they reduce the measured
Python allocation peak by 15.4% at 14,739 DOF. No general solve speed-up is
claimed: timing remains hardware/run dependent and was neutral-to-slower in
the recorded before/after sweep. Nodal block-Jacobi remains the selected
WP14-compatible preconditioner; diagonal-Jacobi is characterized but not
promoted from this subscale evidence. The scatter `bincount` remains a future
optimization target. WP15 does not qualify 1M DOF; WP16 remains the official
release-blocking qualification gate.

## 027-LEVEL-UP - official extended scope decision

Date: 2026-09-01. Source snapshot:
`72888ea63241a4445f6600aa6c2b882401f85ef1`.

Owner decision: `CLOSED / ACCEPT_WITH_CONSOLIDATION` for the portfolio named
**Reproducible Large-Model Solving and Numerical Trust**. The decision accepts
WP13-WP22 as the official next scope. WP13 is complete on its controlled
golden-baseline evidence and WP14 is complete on its frozen execution
contract; WP15 is now `PASS_WITH_LIMITATIONS` and WP16-WP22 remain open. The decision does not
promote a capability or rewrite WP01-WP12 evidence. The WP13 record is in
`qualification/0_2_7/wp13_state.json`.

## WP14 - Large-scale execution contract

WP14 is `PASS` for contract evidence only. The authoritative record is
`qualification/0_2_7/wp14_execution_contract.json`, with state in
`qualification/0_2_7/wp14_state.json`. It freezes the structured TET4 model at
1,029,000 true DOF, four assembled/matrix-free subscale cases, the captured
Windows/Python/NumPy/SciPy/OpenBLAS profile, explicit CG and SPD conditions,
predeclared residual/equilibrium/energy tolerances, replay requirements,
resource safety rules and the 3M Bronze/Silver/Gold ladder.

No 1M or 3M solve was run in WP14, no solve claim is created, no numerical
formulation changed, and WP15 is the next execution package.

WP16 is a release blocker and requires a true reproducible 1M-DOF iterative
FEM solve with loads, BC, reactions, residual, equilibrium, energy, two
replays and full resource/provenance capture. WP18 is mandatory and separates
3M Bronze model/preflight, Silver full solve and Gold PETSc/MPI distributed
restart/second-case evidence. Bronze alone authorizes no 3M solve claim.

Deferred to 0.2.8+: mixed TET/WEDGE/HEX, WEDGE15, PYRAMID5, production
HEX8R/SRI/B-bar, finite-kinematic J2, TL HEX8, refined Arc-Length, new
nonlinear couplings, matrix-free multi-family and general Newmark/harmonic
qualification. Machine-readable criteria are in
`qualification/0_2_7/level_up_plan.json`.

## WP19 - Adversarial robustness and HEX8 diagnostic

Date: 2026-09-01. Lot start SHA:
`7f7ffbaf0b3fdda7d3ad31ba95f20a54e4719a53`. Execution source SHA:
`dc5975b78727d9dca6d0a48b716e60f355b8799f`.

Owner decision: `PASS_WITH_LIMITATIONS`. The 24 predeclared adversarial cases
produce 10 positive `PASS` and 14 `EXPECTED_FAILURE_PASS` outcomes. Replay is
deterministic, failure handling is fail-closed, no NaN/Inf result is accepted,
and no QF-specific bug is found.

The HEX8 diagnostic covers axial refinement, slenderness and transverse
resolution. Six same-mesh CalculiX 2.20/C3D8 displacement comparisons pass the
existing diagnostic threshold with maximum full-displacement relative error
`1.997130986610937e-06`. The result is classified as
`LOW_ORDER_LIMITATION` with secondary `MESH_DEPENDENCE`; locking is compatible
with the observation but not proven. Reactions and energy are
`NOT_COMPARABLE` in the inherited displacement-only deck. No HEX8R/SRI/B-bar
formulation is promoted, no numerical formulation changes, and WP20 closes the
J2 review with bounded limitations; WP21 is next.

## WP17-FINAL - PETSc/MPI large solver path closure

Date: 2026-09-01. Review start SHA:
`cd4da89797ff37e0b142d0705aa4fae0972a7065`.

Owner decision: `PASS_WITH_LIMITATIONS`. The pinned PETSc 3.25.1 / MPICH
5.0.1 CG+GAMG route is explicit and reproducible. The controlled evidence
contains two passing 1,029,000-DOF replays, a passing same-configuration
subscale comparison and two passing 3,000,000-DOF WP18 Silver replays. The
WP14 acceptance tolerance remains `1e-8`; the supplemental internal PETSc
target `1e-10` was predeclared and is not an acceptance-policy change.

PETSc remains optional at runtime and unavailable host selection remains
fail-closed. AIJ memory is approximately 3.52 GiB at 1M DOF and 10.08 GB at
3M DOF on the pinned two-rank route. The observed 1M speedup of about 7.4x
against the old matrix-free run is case- and environment-specific. No public
default backend, general HPC/GPU claim, formulation or existing numerical
route is changed. The machine-readable closeout is
`qualification/0_2_7/wp17_final_state.json`.

## WP20 - Residual J2 and external V&V closure

Date: 2026-09-01. Review start SHA:
`26a734d1656c1c824c27f4708a8783abfddde17c`. Evidence source SHA:
`94461602dfd1782be57c20e1801a0d5d8e262ef1`.

Owner decision: `PASS_WITH_LIMITATIONS` with
`OWNER_APPROVED_BOUNDED_KEEP_EXISTING_SCOPE`. TET4, TET10, HEX8 and HEX20
remain `KEEP` within the existing `QUALIFIED_BOUNDED` small-strain J2 scope.
The scope is isotropic small-strain J2 with radial return and full Newton for
nonlinear static use. No family is promoted or demoted, and finite-kinematic
J2 remains experimental/not qualified.

The evidence closes return mapping, yield detection, unload/reload, simple
cycling, tangent finite differences, increment characterization, rollback,
energy, cross-family consistency, explicit failure modes, no NaN/Inf and
deterministic replay. The maximum tangent FD error is
`2.120472111937634E-10` against the existing `1E-6` limit. No universal
structural increment threshold is claimed; tangent symmetry and modified
Newton behavior remain diagnostics.

External V&V is `PARTIAL_REUSED_CONTROLLED_EVIDENCE`: Code_Aster 18.1.0
constitutive evidence from G06 is reused for all four families. No new
structural external campaign or post-result tolerance retuning is claimed.
The authoritative records are
`qualification/0_2_7/wp20_state.json` and
`docs/verification/0_2_7/0_2_7_wp20_j2_closeout.md`.

## WP21 - Architecture, API and registry surgical cleanup

Date: 2026-09-01. Review start SHA:
`a24c02e2c95edf374d2e2357c6445afc772bc000`. Cleanup source SHA:
`0f565dc9669763751a75f13b02004bde18af571c`.

Owner decision: `PASS_WITH_LIMITATIONS`. The active package and runtime
identity are aligned on `0.2.7a0`; the public audit is clean; legacy
`solveur` and `qf_solver` imports and the documented launchers remain covered;
the registry retains all 33 public capability anchors and 46 combination
records. The WP13 golden replay records eight positive passes and one
expected-failure pass with no mismatch.

This decision is surgical and does not approve a broad architecture redesign,
change any FEM formulation, promote WEDGE6 static, promote finite-kinematic
J2, or alter any earlier Owner maturity decision. WP22 remains the separate
final release action. The controlled records are
`qualification/0_2_7/wp21_state.json`,
`qualification/0_2_7/wp21_final_release_truth.json`,
`qualification/0_2_7/wp21_public_document_audit.json` and
`qualification/0_2_7/golden/wp21_replay_evidence.json`.

## Level-Up 2 setup decision

| Decision ID | Topic | Decision | Evidence/SHA | Date |
| --- | --- | --- | --- | --- |
| 027-OD-012 | Level-Up 2 governance installation | `CONTINUE_TO_LEVEL_UP_2`; LU2 `OPEN` at `0/50`, LU1 `CLOSED` at `50/50` | `qualification/0_2_7/level_up_2_plan.json`, `level_up_2_state.json`, `8f08bfb5a6d4dedcd24966f5474e8c12cbfa5bc3` | 2026-09-02 |

The decision installs the theme **Reproducible Large-Model Performance and
Solver Maturity** and the nine LU2 work packages with a total weight of 50 %.
It does not execute a benchmark, alter a numerical formulation, promote a
capability or change the immutable LU1 evidence. C1, C2 and C3 are dormant
zero-weight conditional gates. The final gate after LU2-WP09 is installed with
the explicit alternatives `RELEASE` and `NEW_LEVEL_UP`; publication is never
automatic.

## LU2-WP01 observatory closeout

Date: 2026-09-02. Execution source SHA:
`e1703b5bc00e9cf2eb92e7e346783c9764201808`.

Owner decision: `PASS` for the evidence and performance observatory contract.
The additive API records phase-separated timings, iterations, matvecs,
residual/equilibrium/energy, rank-aware resource metrics, environment and
artifact digests. PASS-like evidence requires a committed clean source, input
and result SHA-256 digests, a non-empty command and declared environment.
Comparisons are descriptive only and never infer a regression or improvement.
The legacy benchmark path remains unchanged; missing input provenance becomes
`NOT_COMPARABLE`. The controlled record is
`qualification/0_2_7/wp01_observatory_sample.json`, with contract
`qualification/0_2_7/observatory_contract.json` and implementation
`src/solveur/verification/observatory.py`. No heavy benchmark, full regression,
numerical formulation change or maturity promotion occurred. LU2-WP02 was the
next work package.

## LU2-WP02 configuration freeze closeout

Date: 2026-09-02. Execution source SHA:
`3cb817c9391ef7998c5950d3071c8d9ce1be5dd8`.

Owner decision: `PASS_WITH_LIMITATIONS` for the recorded CPU/MPI/PETSc route.
The existing 3M structured TET4 FEM workload completed at 2, 4 and 8 MPI ranks
with PASS invariants and unchanged WP14 tolerances. Two replays were recorded
at 2 and 8 ranks. The selected frozen configuration is contiguous partitioning,
AIJ, CG and GAMG in Docker image
`qf-solver-large@sha256:d6a1718001fc36772906d1a9505637bbd0a4b7e1d8ccc9afdbcb6f67b7ff6d0e`,
with freeze ID `LU2-WP02-FREEZE-bfd1975b012453a3`.

HYPRE/BoomerAMG and graph partitioning were characterized on the recorded
subscale but were not selected. Preflight, redistribution, communication and
I/O are explicitly unmeasured because the legacy runner does not expose
separate boundaries; they are not inferred from total time. The evidence is
therefore bounded to the recorded structured TET4 input, host, container,
rank counts and frozen configuration. No solver/formulation, tolerance or
public maturity decision changed. The controlled records are
`qualification/0_2_7/wp02_execution_contract.json`,
`qualification/0_2_7/wp02_runtime/wp02_evidence_index.json`,
`qualification/0_2_7/wp02_runtime/wp02_config_freeze.json` and
`qualification/0_2_7/wp02_state.json`. LU2-WP03 is ready.

## LU2-WP03 3M Gold Compute closeout

Date: 2026-09-02. Execution source SHA:
`0a6b573485cb39d07b5e179aecd654af41bbc8e7`.

Owner decision: `PASS_WITH_LIMITATIONS`, with `3M_GOLD_COMPUTE = PASS`.
The existing WP18 Silver result remains the controlled Workload A. A
materially distinct real 3,000,000-DOF structured TET4 linear-static workload
with a 2.0 m x 0.75 m x 1.25 m block geometry completed two PASS replays under
the unchanged WP02 freeze: PETSc 3.25.1, MPICH 5.0.1, 8 ranks, contiguous
partitioning, AIJ, CG and GAMG. Both runs passed the frozen residual,
equilibrium, energy, finite-output, no-NaN/Inf and SPD checks; each used 1,046
iterations. The replay maximum numerical relative delta was `6.06e-13`.

The claim is bounded to structured TET4 homogeneous isotropic linear-static
FEM on the pinned single-host Docker/PETSc/MPI configuration. Preflight,
redistribution, communication and I/O remain explicitly `NOT_MEASURED` because
the runner does not expose those phase boundaries. Workload A/B timings are
descriptive only because their geometries differ; no speedup or universal
3M, multi-node, GPU, mixed-mesh, nonlinear or restart claim is made. The
controlled records are `qualification/0_2_7/wp03_execution_contract.json`,
`qualification/0_2_7/lu2_wp03_state.json`,
`qualification/0_2_7/wp03_runtime/wp03_evidence_index.json`,
`qualification/0_2_7/wp03_runtime/wp03_summary.json` and
`qualification/0_2_7/wp03_runtime/wp03_replay_comparison.json`. LU2-WP04 is
the next work package.

## LU2-WP08 scope decision closeout

Date: 2026-09-02. Decision source SHA:
`8ef34e345f970879548a4dfdce4ac5ba32c11bda`.

Owner decision: `PASS_WITH_LIMITATIONS`. The controlled matrix is
`qualification/0_2_7/lu2_wp08_decision_matrix.json`. Mixed TET/WEDGE/HEX is
partial at infrastructure level but has no qualified end-to-end route and is
deferred. WEDGE15 and PYRAMID5 are not supported or active capabilities and
are deferred. The existing HEX8 route remains bounded by WP19; HEX8R, SRI and
B-bar are research-only, and hourglass control is deferred with any future
reduced-integration route. No element, formulation, public maturity or
large-model benchmark changed. The WP04 supervised retry remains the next
operational action.

## LU2-WP06 execution and recovery closeout

Date: 2026-09-02. Decision source SHA:
`4771a23af8cee4549460b9e84edb9228c3a9f60d`.

Owner decision: `PASS_WITH_LIMITATIONS`. The additive execution lifecycle,
stable diagnostic taxonomy and fail-closed checkpoint boundary are installed
and covered by focused tests. Existing nonlinear static, arc-length and
Newmark checkpoint routes retain the recovery claim; linear, buckling,
harmonic, geometric nonlinear and large distributed routes remain explicitly
non-recoverable under this contract. No universal execution graph, timeout
recovery, distributed recovery or fault-tolerance claim is made. The
controlled records are `qualification/0_2_7/wp06_execution_contract.json`,
`qualification/0_2_7/lu2_wp06_state.json`,
`docs/verification/0_2_7/0_2_7_wp06_execution_contract.md` and
`tests/unit/test_execution_contract.py`. LU2-WP07 is ready as an independent
targeted-V&V work package; the separately pending WP04 supervised retry is
unchanged.

## LU2-WP07 existing route maturity closeout

Date: 2026-09-02. Review source SHA:
`65b9d2b168ac7be1df1c0c1cd2d58e8286d4af00`.

Owner decision: `PASS_WITH_LIMITATIONS`. The machine-readable maturity matrix
is `qualification/0_2_7/lu2_wp07_maturity_matrix.json`, with state in
`qualification/0_2_7/lu2_wp07_state.json`. Linear static, modal, buckling,
harmonic, Newmark, small-strain J2 and frictionless contact retain their
existing bounded scopes. Nonlinear static, Arc-Length and static WEDGE6
remain experimental; HEX8 buckling, finite-kinematic J2, friction, coupled
routes and deferred candidates remain outside qualified claims. WP06, WP19
and WP20 evidence was reused, no new external case was run, and no maturity
promotion or demotion was made. LU2 progress is now `32/50` and `82/100`
globally. The LU2-WP04 supervised retry remains unchanged.
