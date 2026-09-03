---
doc_id: DOC-027-003
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 Progress Tracker

This tracker records actual progress, not intent. WP01 through WP06 and T1-R
record completed foundation controls; WP07 records the Terra-authorized
elemental WEDGE6 kernel and WP08 records its bounded static vertical slice.
Its public maturity remains `EXPERIMENTAL`; the slice does not imply modal,
robustness or external-correlation qualification. WP09 records a bounded
robustness campaign; its external outcomes are bounded and do not promote
WEDGE6. WP10 records an independent consistent-
mass modal evidence lot with bounded Code_Aster frequency and mode-shape
correlation. WP10-FINAL qualifies the first three modes within its declared
bounded scope; modes four to six remain diagnostic for refinement.
WP12 records bounded large-scale readiness evidence for the existing structured
TET4 route; its Owner decision remains pending.
WP11 records a bounded maturity extension for existing small-strain J2 across
TET4, TET10, HEX8 and HEX20; the existing qualification is kept and no
universal increment-independence claim is added. WP20 closes the corresponding
Owner review with the same bounded scope and no promotion.
WP14 records the frozen large-scale execution contract for the Level-Up
namespace. It is a governance/contract PASS only; it does not claim a 1M or
3M solve. WP17 closes the pinned PETSc/MPI route with limitations after
consuming the controlled WP16 retry and WP18 Silver evidence. WP18 records a
PASS_WITH_LIMITATIONS 3M ladder: Bronze preflight
and Silver full solve passed on the declared PETSc route; Gold remains
unattempted.

F4 is the current release audit and is recorded as `PASS_WITH_LIMITATIONS`
after its targeted and full-test validation: no P0/P1 test-quality finding
remains, critical invalid-input assertions are typed, and the remaining
optional-environment/test-harness limitations are explicit. The full suite
retains three visible failures in experimental or stale nonlinear paths; none
was hidden or reclassified as PASS. F5 has not started.

| WP | Status | Current test level | Start SHA | Evidence head | Owner decision | Blocker |
| --- | --- | --- | --- | --- | --- | --- |
| WP01 | `PASS` | T1 targeted | `e99289aca40011ca0424944099e2d2093cf21a65` | `bb822839248b5ffb9faef5d79a6c83f288faefb3` | release-truth foundation | - |
| WP02 | `PASS` | T1 targeted | `3058dbcf53967dc50f70814a71b4094d61023dda` | pending commit | registry v2 contract | - |
| WP03 | `PASS` | T1 targeted | `ba6111a257ae567e496adcbcdc74de392dd66b6e` | pending commit | descriptor and fail-closed preflight | - |
| WP04 | `PASS` | T1 targeted | `684c39c72191d43c53e1f21043dc746d213a561d` | pending commit | declarative V&V harness v2 | - |
| WP05 | `PASS` | T1 targeted | `fb102e649235a276096b3a37e19eb61e19a5b43f` | `PENDING_WP05_COMMIT` | external oracle preflight bounded PASS; no WEDGE6 correlation | external tools local-only; QF WEDGE6 not implemented |
| WP06 | `PASS` | T1 targeted | `884637a60bc752c1d02644fe4d14ae056a2876b8` | `c3989df875bcb385bb8e3b144380526db8151d55` | common diagnostic contract; no universal threshold | - |
| T1-R | `PASS` | T1 targeted | `32e4e40bf18f0fdcd0a4ae9959d4f0df2b76892e` | `32e4e40bf18f0fdcd0a4ae9959d4f0df2b76892e` | pre-WP07 formulation, mapping, face, quality and V&V contracts | Terra/Owner re-review required; kernel not authorized |
| T1-R3 | `PASS` | T1 targeted | `d4abc2f15b0e5167cd2faa4734e6a836bdb12514` | pending commit | exact Jacobian certificate and strict external contract | Terra re-review required; kernel not authorized |
| WP07 | `PASS` | T2 targeted | `69b7d01beb81263fc2b87cfacb83985db10e3a82` | `e2e0de5a8df465d5f2254a954d1b2f5c97181cf0` | technical kernel and elemental V&V PASS; public maturity `EXPERIMENTAL` | WP08 workflow, imports, face loads, reactions and external correlation deferred |
| WP08 | `PASS` | T2 targeted | `d4d2942a5fc31ffb97ef373a4466c46be34de991` | `8040909d6d65f740e1daf858ce572d250a87b39a` | static workflow PASS; public maturity `EXPERIMENTAL` | WP09 robustness/external and WP10 modal evidence deferred |
| WP09 | `PASS_WITH_LIMITATIONS` | T1 targeted + T2 external | `2a27291bcc72e5819014fa172e3d056e80a87d43` | `4b2fcdc9ed51821b05b52851912be3ebbe764b14` | WP09-FINAL: 12-case Code_Aster PENTA6 bounded external PASS; public maturity `EXPERIMENTAL` | CalculiX formulation mismatch; tolerance approval remains Owner review; no public WEDGE6 promotion |
| WP10 | `PASS_WITH_LIMITATIONS` | T1/T2 targeted + Code_Aster | `4e005423ba4fd87c6ab6ea2fe5c7a345c21d8e43` | `9d79dc8b306e6cc65f2f4ae2e77e00f676182b84` | `OWNER_APPROVED_BOUNDED_FIRST_THREE_MODES`; modal maturity `QUALIFIED_BOUNDED` within declared scope | modes four to six remain diagnostic for refinement; no lumped mass or transfer to other dynamics |
| WP11 | `PASS_WITH_LIMITATIONS` | T2 targeted | `4d0ee14f4aa61b9337874a991263a93b4f9a8c73` | `94461602dfd1782be57c20e1801a0d5d8e262ef1` | keep qualified bounded J2 scope; Owner-approved by WP20 | no universal increment threshold; tangent symmetry diagnostic only; finite-kinematic J2 remains experimental |
| WP12 | `PASS_WITH_LIMITATIONS` | T1 targeted + bounded scaling | `4971ac4f6c1e5cff2ca48e40ca6db5e8147d0d0a` | `4971ac4f6c1e5cff2ca48e40ca6db5e8147d0d0a` | proposed Owner review | 300k assembly-only; 1M time-limited; SciPy/PETSc backend limits |
| WP13 | `PASS` | T1 targeted | `fcdde28a146a3a502972fdad30821f8e8a857da7` | `qualification/0_2_7/golden/evidence.json` | golden numerical baseline and release truth | 8 PASS + 1 EXPECTED_FAILURE_PASS; no maturity promotion |
| WP14 | `NOT_STARTED` | T0 not run | - | - | - | - |

## Level-Up 1 historical extension

The active theme is **Reproducible Large-Model Solving and Numerical Trust**.
`027-LEVEL-UP` is `CLOSED / ACCEPT_WITH_CONSOLIDATION` as a scope decision;
WP15 is `PASS_WITH_LIMITATIONS` on controlled subscale evidence, WP16 is
`PASS` after the official PETSc retry, and WP17 is `PASS_WITH_LIMITATIONS`
after the PETSc/MPI closure, and WP18 is `PASS_WITH_LIMITATIONS` after the
Bronze/Silver ladder. WP19 is now `PASS_WITH_LIMITATIONS` on bounded
adversarial and HEX8 diagnostic evidence; WP20 is now
`PASS_WITH_LIMITATIONS` for the existing bounded J2 scope. WP21 is
`PASS_WITH_LIMITATIONS` on surgical cleanup and does not promote a capability;
WP22 remains `PLANNED` and neither package constitutes a final release approval.
WP13 has its own
controlled proof record; the remaining criteria and weights are authoritative in
`qualification/0_2_7/level_up_plan.json`.

| WP | Weight | Priority | Status | Rule |
| --- | ---: | --- | --- | --- |
| WP13 | 4% | MUST | `PASS` | release truth and golden baseline |
| WP14 | 5% | MUST | `PASS` | frozen large-scale execution contract; no solve claim |
| WP15 | 10% | MUST | `PASS_WITH_LIMITATIONS` | matrix-free TET4, SPD and preconditioning; subscale evidence complete, WP16 remains the 1M gate |
| WP16 | 10% | MUST | `PASS` | two reproducible PETSc CG/GAMG replays at 1,029,000 DOF satisfy the frozen WP14 contract |
| WP17 | 5% | SHOULD | `PASS_WITH_LIMITATIONS` | pinned PETSc/MPI route closed from two-replay 1M and 3M Silver evidence; host availability and AIJ memory remain limitations |
| WP18 | 7% | MUST | `PASS_WITH_LIMITATIONS` | Bronze preflight and two-replay Silver 3M solve; Gold unattempted |
| WP19 | 5% | MUST | `PASS_WITH_LIMITATIONS` | 24-case fail-closed robustness corpus and bounded HEX8/C3D8 diagnostic |
| WP20 | 3% | SHOULD | `PASS_WITH_LIMITATIONS` | bounded existing four-family J2 closure; reused constitutive external evidence; no universal structural increment claim |
| WP21 | 3% | SHOULD | `PASS_WITH_LIMITATIONS` | surgical architecture/API/registry cleanup; broader redesign deferred |
| WP22 | 3% | MUST | `PLANNED` | final release qualification |

The 45% historical block, 82% current acquired/progress view and 100% total
plan weights are separate governance measures and must not be added together.

## Update rules

- Record the exact source SHA before a lot starts and the evidence SHA after a
  lot is committed.
- Keep `SUPPORTED`, `TESTED`, `VERIFIED` and `QUALIFIED_BOUNDED` separate.
- Record `SKIPPED`, `RESOURCE_LIMITED`, `NOT_COMPARABLE` and
  `EXPECTED_FAILURE` explicitly; never convert them to `PASS`.
- Update the machine-readable progress record in the same commit as a status
  change.
- A work package can move to `READY_FOR_OWNER_REVIEW` only with the evidence
  listed in the gate matrix and a clean, reproducible replay.

## Current baseline note

The only baseline evidence inherited at foundation start is the controlled
0.2.6 release at `e839373b6aef291a93292186d7553ba5cd12af55`. It is a reference
point, not a 0.2.7 result. WP01 is the first completed foundation control;
WP02 is complete for the registry control; WP03 is complete for the descriptor
and preflight control; WP04 is complete for the additive V&V harness control;
WP05 has completed the controlled external-oracle preflight. WP06 has
completed the common mesh-quality diagnostic contract. T1-R has prepared the
remaining pre-WP07 contracts and asymmetric fixtures. Terra/Owner review
authorized WP07, whose elemental kernel and targeted V&V are complete. WP08
has completed the bounded static vertical slice: Gmsh Prism 6 import,
declared TRI3/QUAD4 face loads, common static assembly, equilibrium and
post-processing are evidenced through the V&V v2 path. WEDGE6 remains
`EXPERIMENTAL`; WP09 has completed its internal robustness evidence with
external limitations recorded, and WP10 has completed its separate modal
evidence gate.

WP09 preserves its 22-case internal robustness corpus: 18 passes and four
expected fail-closed outcomes covering inverted geometry, wrong node order,
malformed Gmsh and singular boundary conditions. Its WP09-FINAL external
campaign adds 12 Code_Aster PENTA6 cases covering affine tension/compression,
shear, bending, TRI3/QUAD4 pressure, prescribed displacement, multi-element,
declared distortion and three refinement levels. All 12 primary displacement,
total-reaction and strain-energy comparisons pass with tolerances fixed before
execution; final external replay is deterministic. CalculiX C3D6 remains
explicitly `NOT_FORMULATION_COMPATIBLE` with the QF six-point production
quadrature, and WEDGE6 remains `EXPERIMENTAL` with public qualification
deferred.

WP12 has completed a bounded readiness campaign at declared 100k, 300k, 500k,
750k and 1M target levels. Matrix-free TET4 solves completed through 750141
DOF, a separate 311469-DOF assembly-only probe recorded sparse storage and
resource use, and the 1M attempt was classified `RESOURCE_LIMITED_TIME`.
SciPy CG and direct routes retain their explicit configured/resource limits;
PETSc/SLEPc were unavailable. The evidence is ready for Owner review and does
not claim universal 1M or multi-million-DOF support.

WP10 preserves the original 16 controlled modal cases as historical evidence.
WP10-FINAL adds the declared refinement/MAC catalog and records a four-level
4/8/16/32 prism sequence. The first three frequencies meet the predeclared
final-change rule; all requested modes are finite and positive, deterministic,
and have normalized residual at most `2.40e-11`. Code_Aster 18.1.0/PENTA6
matches `24/24` modes over four same-mesh cases, with maximum frequency error
`1.927e-13` and minimum MAC `0.9999999999999991`. The active modal maturity is
`QUALIFIED_BOUNDED` for the declared consistent-mass WEDGE6 scope; modes four
to six remain diagnostic for refinement and other dynamic routes stay outside
the claim.

WP11 has completed its all-family small-strain J2 characterization without
changing the formulation: material paths, tangent FD, multi-element, cycles,
energy, rollback, increment sensitivity, Newton and failure-mode records are
in the controlled evidence artifact. The existing qualified J2 scope is
retained with explicit limitations; finite-kinematic J2 and unrelated dynamics
gaps remain outside this work package. WP16 has a completed 1,029,000-DOF
PETSc qualification, and WP17-R has recorded the pinned PETSc/MPI route and
its AIJ memory limitation. WP18 has completed its Bronze/Silver ladder: the
3M Silver solve passed twice under the frozen contract; Gold remains
`NOT_ATTEMPTED` because no restart/checkpoint or distinct second physical
case was run. WP19 has completed its bounded adversarial and HEX8 diagnostic
campaign. WP20 closes the Owner review with the existing bounded scope; WP21
has completed its surgical compatibility and release-truth scope with
`PASS_WITH_LIMITATIONS`; WP22 remains `PLANNED` for final Owner release.

## WP19 - Adversarial robustness and HEX8 diagnostic

WP19 is recorded as `PASS_WITH_LIMITATIONS` from execution source SHA
`dc5975b78727d9dca6d0a48b716e60f355b8799f`, with the lot starting at
`7f7ffbaf0b3fdda7d3ad31ba95f20a54e4719a53`. The 24-case T1 corpus produced
10 positive `PASS` results and 14 `EXPECTED_FAILURE_PASS` results. There were
no unexpected failures or invalid evidence records. Replay was deterministic,
failure paths were fail-closed, and no NaN/Inf result was accepted.

The HEX8 study contains three axial-refinement, three slenderness and three
transverse-resolution rows. Six same-mesh CalculiX 2.20/C3D8 displacement
comparisons pass the existing one-percent diagnostic threshold, with maximum
full-displacement relative error `1.997130986610937e-06`. External reactions
and strain energy are `NOT_COMPARABLE` because the inherited deck requests
displacement only. QF and C3D8 agree while both deviate from the slender-beam
Euler diagnostic; the result is classified as `LOW_ORDER_LIMITATION` with
secondary `MESH_DEPENDENCE`. Locking is compatible with the observation but
not proven, and no HEX8R/SRI/B-bar formulation is evaluated or promoted.

The controlled records are `qualification/0_2_7/wp19_state.json`,
`qualification/0_2_7/wp19_runtime/wp19_robustness_summary.json`,
`qualification/0_2_7/wp19_runtime/wp19_hex8_diagnostic.json` and
`qualification/0_2_7/wp19_runtime/wp19_golden_replay.json`. WEDGE6 and all
previous gate decisions remain unchanged. WP20 is closed with bounded
limitations and WP21 is closed with `PASS_WITH_LIMITATIONS`; WP22 is next.

## WP20 - Residual J2 and external V&V closure

WP20 is `PASS_WITH_LIMITATIONS` from review start SHA
`26a734d1656c1c824c27f4708a8783abfddde17c` against evidence source SHA
`94461602dfd1782be57c20e1801a0d5d8e262ef1`. The Owner decision is
`OWNER_APPROVED_BOUNDED_KEEP_EXISTING_SCOPE`: TET4, TET10, HEX8 and HEX20
remain `KEEP` within the existing `QUALIFIED_BOUNDED` small-strain J2 scope.

Return mapping, yield detection, unload/reload, simple cycling, tangent FD,
increment characterization, rollback, energy, cross-family checks, explicit
failure modes, no NaN/Inf and deterministic replay are recorded as passing or
bounded evidence. The tangent FD maximum is `2.120472111937634E-10` against
the existing `1E-6` limit. No universal structural increment threshold is
claimed; tangent symmetry and modified Newton behavior remain diagnostics.

External V&V is `PARTIAL_REUSED_CONTROLLED_EVIDENCE`: Code_Aster 18.1.0 G06
constitutive evidence is reused for the four families, with no new structural
campaign and no post-result tolerance retuning. Finite-kinematic J2 remains
experimental/not qualified. The authoritative records are
`qualification/0_2_7/wp20_state.json`,
`qualification/0_2_7/wp11_j2_evidence.json` and
`docs/verification/0_2_7/0_2_7_wp20_j2_closeout.md`. WP21 is closed with
`PASS_WITH_LIMITATIONS`; WP22 is next.

## Active global accounting

The historical Level-Up portfolio is closed as Level-Up 1 at `50/50`. The
active program is Level-Up 2 at `46/50`, giving `CURRENT_GLOBAL_PROGRESS =
96/100`. The earlier 45/55, 82/85 and 32/50 views remain historical accounting
records only; they are not added to the current program and do not replace
any evidence. The active machine-readable records are
`qualification/0_2_7/level_up_2_plan.json`,
`qualification/0_2_7/level_up_2_state.json` and
`qualification/0_2_7/level_up_2_index.json`.

## Level-Up 2 active plan

| Work package | Weight | Priority | Status | Rule |
| --- | ---: | --- | --- | --- |
| LU2-WP01 | 4% | MUST | `PASS` | evidence and performance observatory |
| LU2-WP02 | 9% | MUST | `PASS_WITH_LIMITATIONS` | CPU/MPI/GAMG freeze before large runs |
| LU2-WP03 | 9% | MUST | `PASS_WITH_LIMITATIONS` | distinct second 3M workload and two replays |
| LU2-WP04 | 5% | MUST | `PASS` | real 5M Bronze completed with global readiness, finalization and evidence |
| LU2-WP05 | 9% | MUST | `PASS` | complete two-replay 5M Silver solve under the frozen route |
| LU2-WP06 | 4% | MUST | `PASS_WITH_LIMITATIONS` | recovery, diagnostics and fail-closed execution; bounded to existing checkpoint routes |
| LU2-WP07 | 4% | SHOULD | `PASS_WITH_LIMITATIONS` | existing route maturity retained at bounded combination scope; no promotion or demotion |
| LU2-WP08 | 2% | SHOULD | `PASS_WITH_LIMITATIONS` | explicit decisions; deferred/research routes remain unqualified |
| LU2-WP09 | 4% | MUST | `NOT_STARTED` | final registry, CI, package and Owner qualification |

LU2-WP02 evidence is defined by the predeclared contract
`qualification/0_2_7/wp02_execution_contract.json`, the controlled run index
`qualification/0_2_7/wp02_runtime/wp02_evidence_index.json`, the frozen
configuration `qualification/0_2_7/wp02_runtime/wp02_config_freeze.json` and
the closeout `qualification/0_2_7/wp02_state.json`. The 3M structured TET4
route passed at 2, 4 and 8 ranks with replay coverage at 2 and 8 ranks. GAMG
and contiguous partitioning were selected from characterized subscale
alternatives. Preflight, redistribution, communication and I/O are explicitly
unmeasured because the legacy runner does not expose separate boundaries; no
phase is inferred. The evidence is therefore bounded to the recorded host,
Docker image, input and solver configuration.

LU2-WP03 is closed as `PASS_WITH_LIMITATIONS` with
`3M_GOLD_COMPUTE = PASS`. Workload A is the preserved WP18 Silver control;
Workload B is a materially distinct 3,000,000-DOF structured TET4 case with
two PASS replays under the unchanged freeze. The controlled evidence is
indexed by `qualification/0_2_7/wp03_runtime/wp03_evidence_index.json` and
the bounded metrics are recorded in
`docs/verification/0_2_7/0_2_7_wp03_3m_gold_compute.md`. Preflight,
redistribution, communication and I/O remain `NOT_MEASURED`; no performance
speedup is inferred between the distinct workloads. LU2-WP04 was completed as
`PASS` on a real 5,012,640-DOF TET4 model, with global readiness, all-rank
finalization and preserved evidence. LU2-WP05 then completed the two-replay 5M
Silver solve under the unchanged freeze. The earlier owner-interrupted
attempt remains historical forensic evidence and is not the active gate status;
C1 was not confirmed.

LU2-WP08 is closed as `PASS_WITH_LIMITATIONS` by the controlled decision
matrix `qualification/0_2_7/lu2_wp08_decision_matrix.json`. Mixed
TET/WEDGE/HEX remains a partial technical path without an end-to-end
qualification and is deferred. WEDGE15 and PYRAMID5 are not supported or
active capabilities and are deferred. Existing HEX8 remains bounded under
WP19; HEX8R, SRI and B-bar are research-only, and hourglass control is
deferred with reduced integration. No numerical source, capability maturity
or WP04 forensic status changed. The supervised WP04 retry remains the next
operational action.

LU2-WP01 evidence is defined by
`qualification/0_2_7/observatory_contract.json` and the controlled sample
`qualification/0_2_7/wp01_observatory_sample.json`. LU2 weights sum to 50 %.
C1, C2 and C3 are installed zero-weight conditional gates. C1 remains
`DORMANT` because the WP04 time-budget overrun was observed during an
owner-interrupted run without persisted progress/resource telemetry; C2 and C3
remain dormant. LU2-WP03 is complete, LU2-WP04 remains incomplete, and a
supervised WP04 retry is the next active action; its
pre-LU2 baseline is `8f08bfb5a6d4dedcd24966f5474e8c12cbfa5bc3`.

The following paragraph preserves the earlier WP06 closeout snapshot; it is
historical accounting, not the current LU2 state.

LU2-WP06 is closed as `PASS_WITH_LIMITATIONS` at 4%. The additive lifecycle
and diagnostic taxonomy are covered by
`qualification/0_2_7/wp06_execution_contract.json` and
`tests/unit/test_execution_contract.py`; existing nonlinear and Newmark
checkpoint tests remain the recovery evidence. Recovery is deliberately
bounded to those routes, with no universal distributed or fault-tolerance
claim. This closeout raised LU2 accounting from 24/50 to 28/50 and global
progress from 74/100 to 78/100. WP04 remains `USER_INTERRUPTED_INCONCLUSIVE`
and its supervised retry remains the next operational action.

LU2-WP07 closes as `PASS_WITH_LIMITATIONS` through the machine-readable
matrix `qualification/0_2_7/lu2_wp07_maturity_matrix.json` and state
`qualification/0_2_7/lu2_wp07_state.json`. Existing route maturity was audited
against the registry and reused WP06, WP19 and WP20 evidence; no new external
campaign, numerical source change or maturity promotion was performed. The
active accounting is now `46/50` and `96/100` globally. WP04 and WP05 are
closed; LU2-WP09 is the next active gate.

S1 installs the optional rank-zero JSONL assembly telemetry contract for that
retry. It records flushed chunk progress, rates, ETA when available, phases,
resource fields and one-million-element milestones; it does not change the
WP04 status or global progress.
