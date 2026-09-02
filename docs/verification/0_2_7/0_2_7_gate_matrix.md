---
doc_id: DOC-027-002
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 Gate Matrix

This matrix is a controlled status record. WP01 is `PASS` for release truth, WP02 is
`PASS` for the combination-level registry control, and WP03 is `PASS` for the
technical descriptor and fail-closed preflight control, and WP04 is `PASS` for
the additive V&V harness control. WP05 is `PASS` for the external deck
preflight only; it issues no WEDGE6 QF result or capability. WP06 is `PASS`
for the additive mesh-quality diagnostic contract; it introduces no new
numerical capability or universal quality cutoff. The WP07 row is technical
kernel evidence only: WEDGE6 remains `EXPERIMENTAL` and is not publicly
qualified. WP08 adds the bounded static vertical slice without changing that
maturity. WP10 separately records consistent-mass modal evidence and bounded
Code_Aster frequency/MAC correlation; its modal combination is
`QUALIFIED_BOUNDED` only within the declared scope.
WP12 records bounded large-scale readiness evidence for the existing structured
TET4 route; its Owner decision remains pending and its resource limits are not
success claims. WP11 records a bounded maturity extension for existing
small-strain J2 evidence across TET4, TET10, HEX8 and HEX20; it keeps the
qualified scope and does not create a universal increment-independence claim.
WP18 records a PASS_WITH_LIMITATIONS 3M Bronze/Silver ladder under the frozen
WP14 contract; Gold remains unattempted and no Gold claim is made. WP20 closes
the Owner review of the existing bounded small-strain J2 scope with
PASS_WITH_LIMITATIONS; WP21 is now PASS_WITH_LIMITATIONS for surgical cleanup
and WP22 remains planned for the final Owner release action.

| Gate | Work package | Purpose | Dependencies | GO evidence | STOP conditions | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `027-G01` | WP01 | Release truth and provenance | None | exact baseline, clean-state and version records | SHA, tag or version mismatch | `PASS` |
| `027-G02` | WP02 | Element x analysis x material x route registry | G01 | schema, uniqueness and implementation cross-check | inferred maturity or orphan capability | `PASS` |
| `027-G03` | WP03 | Compatibility descriptors and preflight | G02 | deterministic accept/reject matrix | default-path or API behavior change | `PASS` |
| `027-G04` | WP04 | Declarative V&V harness | G01-G02 | additive runner contract and replay proof | numerical route refactor or hidden command execution | `PASS` |
| `027-G05` | WP05 | C3D6/PENTA6 oracle preflight | G01-G02 | comparable deck contract and availability record | non-comparable oracle presented as PASS | `PASS` |
| `027-G06` | WP06 | Mesh quality/distortion contract | G02-G03 | metrics, invalid cases, deterministic classification and preflight diagnostic | universal aspect-ratio cutoff | `PASS` |
| `027-G07` | WP07 | WEDGE6 kernel and elemental V&V | G03, G05, G06, T1-R | reviewed contracts, six-node kernel, stiffness/recovery checks, exact quality certificate and deterministic evidence | certified inversion not rejected; rank or rigid modes unexpected; affine patch or quadrature check fails; existing element formulation changed | `PASS` |
| `027-G08` | WP08 | WEDGE6 static vertical slice | G07 | 15-case Gmsh/import/load/assembly/equilibrium/post evidence with deterministic replay | missing face/load, silent unsupported path or unexpected failure | `PASS` |
| `027-G09` | WP09 | WEDGE6 robustness and external V&V | G08 | mesh/distortion/adversarial evidence with explicit external availability and comparability outcomes | unexplained divergence, weakened threshold or false external PASS | `PASS_WITH_LIMITATIONS` |
| `027-G10` | WP10 | WEDGE6 modal evidence | G08-G09 | mass, modes, residual, mesh, replay and bounded external frequency evidence | static evidence transferred without modal proof; hidden mass convention; unexplained non-finite modes | `PASS_WITH_LIMITATIONS` |
| `027-G11` | WP11 | Existing maturity and J2 gaps | G01, G04, G06 | all-family J2/increment/tangent evidence | formulation change or relaxed acceptance | `PASS_WITH_LIMITATIONS` |
| `027-G12` | WP12 | Large-scale readiness | G02, G04, G06 | declared size/resource measurements, bounded backend/resource verdicts and deterministic replay | universal 1M claim or uncharacterized failure | `PASS_WITH_LIMITATIONS` |
| `027-G13` | WP13 | Research/stretch selection | relevant closed prerequisites | explicit Owner scope selection | scope creep or transitive promotion | `NOT_STARTED` |
| `027-G14` | WP14 | Release closeout | G01-G13 as applicable | docs, full regression, package and Owner review | stale claim, provenance gap or regression | `NOT_STARTED` |

`027-G07` required a design review before implementation. The external oracle
preflight and formulation review preceded the kernel, and the current PASS is
limited to the elemental technical route. The descriptor reports
`EXPERIMENTAL_ROUTE`; WP08 provides a bounded static user workflow, and WP09
adds controlled robustness evidence without creating a public qualification.
CalculiX C3D6 is explicitly non-formulation-compatible with the QF production
quadrature. WP09-R repairs the headless Code_Aster path and records one
bounded affine PENTA6 correlation through a derived image pinned to the base
image digest. WP10 modal evidence is recorded separately for its own claims.
The consistent mass, finite-positive modes, residual, orthogonality, replay and
zero-density fail-closed checks pass. The four-level 4/8/16/32 refinement
passes for the first three modes under the predeclared `1e-2` final-change
rule; modes four to six remain diagnostic. Code_Aster 18.1.0/PENTA6 provides
bounded same-mesh frequency and MAC evidence over four cases, with `24/24`
matched modes. `COMB-WEDGE6-modal` is `QUALIFIED_BOUNDED` only for the
declared consistent-mass scope; no general dynamics claim is made. G13 may remain open
or deferred without blocking a bounded core release when research routes are
explicitly excluded.

`027-G12` is `PASS_WITH_LIMITATIONS` for the declared structured TET4
linear-static readiness scope. Matrix-free CG completed 100k through 750k
target levels (actual maximum 750141 DOF); 300k assembly-only evidence reached
311469 DOF; SciPy direct was resource-limited at 107811 DOF; higher SciPy
levels were rejected by the configured 200000-DOF guard; and the 1M
matrix-free attempt was time-limited after 600 seconds. These results are
hardware- and topology-specific and do not qualify a universal 1M solve.
The evidence is recorded in
`qualification/0_2_7/wp12_scaling_evidence.json`,
`qualification/0_2_7/wp12_assembly_probe_300k.json` and
`0_2_7_large_scale_readiness.md`; `027-OD-005` remains
`PROPOSED_OWNER_REVIEW`.

## Official Level-Up portfolio

`027-LEVEL-UP` is `CLOSED / ACCEPT_WITH_CONSOLIDATION`: the scope was
accepted, and the executed WP16 and WP18 results are recorded separately
below.
WP13 is `PASS` on its controlled golden-baseline evidence. WP14 is `PASS` on
its frozen execution contract; WP15 is `PASS_WITH_LIMITATIONS` on controlled
subscale evidence; WP16 is `PASS` after the official PETSc retry; WP17 is
`PASS_WITH_LIMITATIONS` after its pinned PETSc/MPI closure; WP18 is
`PASS_WITH_LIMITATIONS` after the Bronze/Silver ladder; and WP19 is
`PASS_WITH_LIMITATIONS` on bounded adversarial and HEX8 diagnostic evidence.
WP20 is `PASS_WITH_LIMITATIONS` for the existing bounded small-strain J2
scope. WP21 is `PASS_WITH_LIMITATIONS` for surgical compatibility, public
audit and release-truth cleanup; WP22 remains `PLANNED` for the final Owner
release action. The active theme is **Reproducible Large-Model Solving and
Numerical Trust**.

| Level-Up gate | Work package | Status | Weight | Required interpretation |
| --- | --- | --- | ---: | --- |
| `LUP-027-G13` | WP13 release truth and golden baseline | `PASS` | 4% | distinct SHA roles and golden baseline |
| `LUP-027-G14` | WP14 large-scale execution contract | `PASS` | 5% | frozen topology, resource and execution contract; no solve claim |
| `LUP-027-G15` | WP15 matrix-free TET4 V2 | `PASS_WITH_LIMITATIONS` | 10% | SPD, preconditioning and assembled subscale; no WP16/1M claim |
| `LUP-027-G16` | WP16 true 1M DOF qualification | `PASS` | 10% | two PETSc CG/GAMG replays satisfy frozen residual, equilibrium, energy and SPD criteria |
| `LUP-027-G17` | WP17 PETSc/MPI and large sparse path | `PASS_WITH_LIMITATIONS` | 5% | two-replay 1M and 3M Silver evidence on the pinned route; host availability and AIJ memory remain limitations |
| `LUP-027-G18` | WP18 3M Bronze/Silver/Gold ladder | `PASS_WITH_LIMITATIONS` | 7% | Bronze preflight and two-replay Silver solve; Gold unattempted |
| `LUP-027-G19` | WP19 adversarial robustness and HEX8 diagnostic | `PASS_WITH_LIMITATIONS` | 5% | 24-case fail-closed corpus and bounded HEX8/C3D8 diagnostic; no formulation promotion |
| `LUP-027-G20` | WP20 residual J2 and external V&V closure | `PASS_WITH_LIMITATIONS` | 3% | existing four-family small-strain J2 scope retained; no universal structural increment claim |
| `LUP-027-G21` | WP21 surgical architecture/API/registry cleanup | `PASS_WITH_LIMITATIONS` | 3% | legacy compatibility preserved; broader redesign deferred |
| `LUP-027-G22` | WP22 final release qualification | `PLANNED` | 3% | final regression/package/Owner checkpoint |

Machine-readable criteria are in `qualification/0_2_7/level_up_plan.json` and
`qualification/0_2_7/requirements.json`. WP16 is satisfied and WP18 records
the mandatory Silver result. Bronze creates no solve claim, Gold remains
unattempted, and no Level-Up record promotes a capability.

WP18 evidence is recorded in
`qualification/0_2_7/wp18_runtime/wp18_summary.json` and
`qualification/0_2_7/wp18_state.json`. The 3M Silver route completed twice
at 3,000,000 true DOF with residual, equilibrium, energy, finite-output and
SPD checks passing. The claim is limited to the structured TET4 linear-static
model and the pinned two-rank PETSc/MPI environment; AIJ setup and peak RSS
remain material limitations.

## `027-G19` adversarial robustness and HEX8 diagnostic

WP19 evidence is recorded in `qualification/0_2_7/wp19_state.json` and the
linked runtime artifacts. The 24 predeclared cases produced 10 positive
`PASS` results and 14 `EXPECTED_FAILURE_PASS` results, with deterministic
replay, fail-closed failure paths and no accepted NaN/Inf result. The failure
classes include invalid geometry and ordering, duplicate nodes, singular or
inconsistent constraints, invalid material/load data, malformed Gmsh and
missing physical groups.

The HEX8 diagnostic covers three axial-refinement, three slenderness and
three transverse-resolution rows. Six same-mesh CalculiX 2.20/C3D8
displacement comparisons pass the existing one-percent diagnostic threshold;
the maximum full-displacement relative error is `1.997130986610937e-06`.
External reactions and energy are `NOT_COMPARABLE` because the inherited deck
requests displacement only. QF and C3D8 agree while both deviate from the
Euler diagnostic, supporting a `LOW_ORDER_LIMITATION` classification with
secondary `MESH_DEPENDENCE`; locking remains compatible but unproven. No
HEX8R/SRI/B-bar formulation is evaluated or promoted.

## `027-G11` bounded J2 maturity extension

WP11 records `PASS_WITH_LIMITATIONS` for the existing small-strain J2 route,
with its Owner review closed by WP20 as
`OWNER_APPROVED_BOUNDED_KEEP_EXISTING_SCOPE`. The
controlled catalog and evidence cover elastic prediction, first yield, radial
return, internal variables, unloading/reloading, simple cycling, tangent finite
differences, connected multi-element paths, energy, rollback and explicit
failure modes on TET4, TET10, HEX8 and HEX20. Full Newton is the accepted
route; modified Newton non-convergence is recorded as diagnostic.

The increment study uses a declared load path and 1/2/4 subdivisions per
branch. It records family-specific sensitivity without introducing a new
universal acceptance threshold. Algorithmic tangent symmetry is diagnostic
only, finite-kinematic J2 remains experimental/not qualified, and no new
external structural campaign is claimed. Evidence is in
`qualification/0_2_7/wp11_j2_evidence.json` and its source SHA is
`94461602dfd1782be57c20e1801a0d5d8e262ef1`.

## `LUP-027-G20` residual J2 and external V&V closure

WP20 is `PASS_WITH_LIMITATIONS` with Owner decision
`OWNER_APPROVED_BOUNDED_KEEP_EXISTING_SCOPE`. It retains the existing
`QUALIFIED_BOUNDED` `MAT-J2-SMALL` scope for small-strain isotropic J2 with
radial return and full Newton on TET4, TET10, HEX8 and HEX20. No family is
promoted or demoted, and finite-kinematic J2 remains experimental/not
qualified.

The evidence closes the residual review items: return mapping, yield
detection, unload/reload, simple cycling, tangent finite differences,
increment characterization, rollback, energy, cross-family consistency,
failure modes, no NaN/Inf and deterministic replay. The tangent FD maximum is
`2.120472111937634E-10` against the existing `1E-6` limit. Increment results
remain characterization only; no universal structural increment threshold or
tangent-symmetry qualification is claimed. Modified Newton non-convergence
remains diagnostic.

External V&V is `PARTIAL_REUSED_CONTROLLED_EVIDENCE`: the controlled
Code_Aster 18.1.0 constitutive evidence from G06 is reused for all four
families. No new structural J2 campaign is claimed, and no post-result
tolerance retuning occurred. The authoritative records are
`qualification/0_2_7/wp20_state.json` and
`docs/verification/0_2_7/0_2_7_wp20_j2_closeout.md`. WP21 then closed its
surgical compatibility and release-truth scope; WP22 remains the next Owner
release action.

## Level-Up 2 gate namespace

The prior Level-Up is closed as Level-Up 1 at `50/50`. The active namespace is
`027-LEVEL-UP-2`, based on the qualified snapshot
`8f08bfb5a6d4dedcd24966f5474e8c12cbfa5bc3`. LU2 is at `24/50` after the WP01
observatory, bounded WP02 configuration freeze, completed WP03 Gold Compute
and LU2-WP08 scope closeout, and the global program is therefore `74/100`.
The active
contracts and state are
authoritative in `qualification/0_2_7/level_up_2_plan.json` and
`qualification/0_2_7/level_up_2_state.json`.

| Gate | Work package | Weight | Priority | Current status | PASS boundary |
| --- | --- | ---: | --- | --- | --- |
| `LU2-027-G01` | LU2-WP01 observatory | 4% | MUST | `PASS` | phase-separated, digest-backed performance evidence |
| `LU2-027-G02` | LU2-WP02 configuration freeze | 9% | MUST | `PASS_WITH_LIMITATIONS` | explicit CPU/MPI/PETSc/KSP/PC and fail-closed backend |
| `LU2-027-G03` | LU2-WP03 3M Gold Compute | 9% | MUST | `PASS_WITH_LIMITATIONS` | distinct 3M FEM workload, two replays, bounded claim |
| `LU2-027-G04` | LU2-WP04 5M Bronze | 5% | MUST | `USER_INTERRUPTED_INCONCLUSIVE` | two matching constructions and operator/PC preflight, no solve claim |
| `LU2-027-G05` | LU2-WP05 5M Silver | 9% | MUST | `NOT_STARTED` | complete two-replay solve under frozen MPI and resource criteria |
| `LU2-027-G06` | LU2-WP06 execution/recovery | 4% | MUST | `NOT_STARTED` | explicit, fail-closed outcomes and state integrity |
| `LU2-027-G07` | LU2-WP07 existing routes | 4% | SHOULD | `NOT_STARTED` | only decision-changing targeted V&V, no transitive promotion |
| `LU2-027-G08` | LU2-WP08 route decisions | 2% | SHOULD | `PASS_WITH_LIMITATIONS` | deferred/experimental routes remain unqualified; existing HEX8 remains bounded |
| `LU2-027-G09` | LU2-WP09 final qualification | 4% | MUST | `NOT_STARTED` | explicit Owner RELEASE or NEW_LEVEL_UP decision |

LU2-WP02 is closed with limitations by the controlled 3M MPI evidence index
and configuration freeze. The route covers 2, 4 and 8 ranks on one recorded
Docker host, with GAMG selected over the characterized HYPRE and graph
partition alternatives. The legacy runner does not expose separate preflight,
redistribution, communication or I/O timings; these fields remain explicitly
unmeasured and are never inferred. See
`docs/verification/0_2_7/0_2_7_wp02_configuration_freeze.md` and
`qualification/0_2_7/wp02_state.json`.

LU2-WP03 is closed as `PASS_WITH_LIMITATIONS` with `3M_GOLD_COMPUTE = PASS`.
The existing WP18 Silver case remains the controlled Workload A, while a
materially distinct 3,000,000-DOF structured TET4 workload completed two
replays under the unchanged freeze. The records are
`qualification/0_2_7/wp03_runtime/wp03_evidence_index.json`,
`qualification/0_2_7/wp03_runtime/wp03_summary.json` and
`qualification/0_2_7/wp03_runtime/wp03_replay_comparison.json`; exact metrics
and the bounded claim are documented in
`docs/verification/0_2_7/0_2_7_wp03_3m_gold_compute.md`. Preflight,
redistribution, communication and I/O remain explicitly `NOT_MEASURED`, and
the evidence makes no universal, multi-node, GPU, mixed-mesh, nonlinear or
restart claim. LU2-WP04 was attempted with a real `5,012,640`-DOF TET4
workload. The two independent constructions and preflight passed, but the
owner-interrupted container remained CPU-active in frozen AIJ assembly without
a completion record. The gate is therefore
`USER_INTERRUPTED_INCONCLUSIVE`, not PASS or proven `RESOURCE_LIMITED`; the
evidence makes no 5M Bronze, readiness or solve claim. C1 is not confirmed and
WP05 remains blocked pending a supervised retry.

Conditional gates `C1` (matrix-free TET4 capacity), `C2` (GPU foundation) and
`C3` (10M capacity exploration) are installed with zero weight. C1 remains
`DORMANT` because the 2x time budget overrun was observed during an
owner-interrupted run without persisted progress/resource telemetry; C2
requires real hardware evidence, and C3 requires 5M Silver first; none can
block LU2.
Bronze never
creates a 3M solve claim, Gold does not require restart, and no post-result
retuning or silent fallback is permitted.

## `LU2-027-G08` route-decision closeout

LU2-WP08 is `PASS_WITH_LIMITATIONS`. The controlled decision matrix is
[`qualification/0_2_7/lu2_wp08_decision_matrix.json`](../../../qualification/0_2_7/lu2_wp08_decision_matrix.json)
and its state record is
[`qualification/0_2_7/lu2_wp08_state.json`](../../../qualification/0_2_7/lu2_wp08_state.json).
No new element, formulation or mixed-mesh framework was implemented.

Mixed TET/WEDGE/HEX is `PARTIAL` at technical infrastructure level but has no
qualified end-to-end route and is deferred. WEDGE15 and PYRAMID5 are
`NOT_SUPPORTED` and deferred; negative fixtures do not constitute
implementation. Existing HEX8 remains `SUPPORTED_WITH_LIMITATIONS` within
the bounded WP19 diagnostic scope. HEX8R, SRI and B-bar are
`RESEARCH_ONLY`, while hourglass control is deferred with any future reduced
integration route. These decisions do not change the active capability
registry or any earlier Owner decision.
