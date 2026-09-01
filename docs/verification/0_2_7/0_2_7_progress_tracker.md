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
universal increment-independence claim is added.
WP14 records the frozen large-scale execution contract for the Level-Up
namespace. It is a governance/contract PASS only; it does not claim a 1M or
3M solve.

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
| WP11 | `PASS_WITH_LIMITATIONS` | T2 targeted | `4d0ee14f4aa61b9337874a991263a93b4f9a8c73` | `94461602dfd1782be57c20e1801a0d5d8e262ef1` | keep qualified bounded J2 scope; Owner review required | no universal increment threshold; tangent symmetry diagnostic only; finite-kinematic J2 remains experimental |
| WP12 | `PASS_WITH_LIMITATIONS` | T1 targeted + bounded scaling | `4971ac4f6c1e5cff2ca48e40ca6db5e8147d0d0a` | `4971ac4f6c1e5cff2ca48e40ca6db5e8147d0d0a` | proposed Owner review | 300k assembly-only; 1M time-limited; SciPy/PETSc backend limits |
| WP13 | `PASS` | T1 targeted | `fcdde28a146a3a502972fdad30821f8e8a857da7` | `qualification/0_2_7/golden/evidence.json` | golden numerical baseline and release truth | 8 PASS + 1 EXPECTED_FAILURE_PASS; no maturity promotion |
| WP14 | `NOT_STARTED` | T0 not run | - | - | - | - |

## Official Level-Up extension

The active theme is **Reproducible Large-Model Solving and Numerical Trust**.
`027-LEVEL-UP` is `CLOSED / ACCEPT_WITH_CONSOLIDATION` as a scope decision;
WP15 is `PASS_WITH_LIMITATIONS` on controlled subscale evidence; WP16-WP22
remain individually `PLANNED` and do not constitute execution evidence. WP13 has its own controlled proof record; the remaining criteria and weights are authoritative in
`qualification/0_2_7/level_up_plan.json`.

| WP | Weight | Priority | Status | Rule |
| --- | ---: | --- | --- | --- |
| WP13 | 4% | MUST | `PASS` | release truth and golden baseline |
| WP14 | 5% | MUST | `PASS` | frozen large-scale execution contract; no solve claim |
| WP15 | 10% | MUST | `PASS_WITH_LIMITATIONS` | matrix-free TET4, SPD and preconditioning; subscale evidence complete, WP16 remains the 1M gate |
| WP16 | 10% | MUST | `PLANNED` | release blocker; true 1M FEM solve |
| WP17 | 5% | SHOULD | `PLANNED` | PETSc/MPI path and provenance |
| WP18 | 7% | MUST | `PLANNED` | mandatory 3M Bronze/Silver/Gold ladder |
| WP19 | 5% | MUST | `PLANNED` | adversarial robustness and HEX8 diagnostic |
| WP20 | 3% | SHOULD | `PLANNED` | residual J2 and external V&V closure |
| WP21 | 3% | SHOULD | `PLANNED` | surgical architecture/API/registry cleanup |
| WP22 | 3% | MUST | `PLANNED` | final release qualification |

The 45% historical block, 60% current acquired/progress view and 100% total
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
gaps remain outside this work package.
