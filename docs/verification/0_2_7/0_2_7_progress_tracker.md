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
robustness campaign; its external outcomes remain explicitly partial or
bounded and do not promote WEDGE6. WP10 records an independent consistent-
mass modal evidence lot with bounded Code_Aster frequency correlation; public
modal maturity remains `EXPERIMENTAL` and qualification is deferred.
WP12 records bounded large-scale readiness evidence for the existing structured
TET4 route; its Owner decision remains pending.

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
| WP09 | `PASS_WITH_LIMITATIONS` | T1 targeted + external preflight | `2a27291bcc72e5819014fa172e3d056e80a87d43` | `d3cb2cc43886c56471778a91bef965dee869a8d4` | WEDGE6 robustness bounded PASS; one bounded Code_Aster affine correlation; public maturity `EXPERIMENTAL` | no public external qualification; CalculiX formulation mismatch; pressure/refinement/distorted external cases unclaimed |
| WP10 | `PASS_WITH_LIMITATIONS` | T1/T2 targeted + Code_Aster | `ea356c484ebb2a3c4282f6eb9cbae6b1992eee6e` | `7d494eaa638ffa88a04ed3e5c51f6036ad1804a1` | independent consistent-mass modal evidence; public maturity `EXPERIMENTAL` | four-level frequency refinement is diagnostic; external frequency tolerance remains `OWNER_REVIEW_REQUIRED`; no MAC or modal qualification claim |
| WP11 | `NOT_STARTED` | T0 not run | - | - | - | - |
| WP12 | `PASS_WITH_LIMITATIONS` | T1 targeted + bounded scaling | `4971ac4f6c1e5cff2ca48e40ca6db5e8147d0d0a` | `4971ac4f6c1e5cff2ca48e40ca6db5e8147d0d0a` | proposed Owner review | 300k assembly-only; 1M time-limited; SciPy/PETSc backend limits |
| WP13 | `NOT_STARTED` | T0 not run | - | - | - | - |
| WP14 | `NOT_STARTED` | T0 not run | - | - | - | - |

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

WP09 records 22 controlled cases: 18 internal passes and four expected
fail-closed outcomes covering inverted geometry, wrong node order, malformed
Gmsh and singular boundary conditions. CalculiX C3D6 completed a local affine
run but is explicitly `NOT_FORMULATION_COMPATIBLE` with the QF six-point
production quadrature. Code_Aster PENTA6 completed one affine same-mesh run
through the derived headless image, with displacement, total reaction and
strain-energy evidence recorded as bounded external evidence. The affine
tolerance remains `OWNER_REVIEW_REQUIRED`; pressure, refinement and distorted
external cases remain unclaimed, and no WEDGE6 public promotion is claimed.

WP12 has completed a bounded readiness campaign at declared 100k, 300k, 500k,
750k and 1M target levels. Matrix-free TET4 solves completed through 750141
DOF, a separate 311469-DOF assembly-only probe recorded sparse storage and
resource use, and the 1M attempt was classified `RESOURCE_LIMITED_TIME`.
SciPy CG and direct routes retain their explicit configured/resource limits;
PETSc/SLEPc were unavailable. The evidence is ready for Owner review and does
not claim universal 1M or multi-million-DOF support.

WP10 records 16 controlled modal cases: 15 `PASS` results and one
`EXPECTED_FAILURE_PASS` for zero density. The consistent mass is positive,
conservative and production/reference-quadrature consistent. The common modal
route passes finite-positive spectrum, residual, mass-orthogonality and replay
checks on single, multi-element and distorted prisms. Code_Aster 18.1.0/PENTA6
matches six frequencies on the declared affine same-mesh case within the
predeclared `1e-2` bounded candidate. The result is frequency-only external
evidence; WEDGE6 modal maturity remains `EXPERIMENTAL` and public qualification
is deferred.
