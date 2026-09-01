---
doc_id: DOC-027-023
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# WP09 WEDGE6 robustness and external V&V

WP09 exercises the WP08 six-node prism static slice without changing the
WEDGE6 kernel or any existing element formulation. The controlled catalog has
22 internal T1 cases: affine tension, compression, shear, bending, TRI3 and
QUAD4 pressure, prescribed displacement, a conforming multi-element mesh,
distortion, a three-level refinement ladder, aspect-ratio and skew probes,
fail-closed invalid inputs, rigid transforms, scale and deterministic replay.

The committed run contains 18 `PASS` and four `EXPECTED_FAILURE_PASS` results,
with no unexpected failure, NaN/Inf or silent success. Inverted connectivity,
wrong node order, malformed Gmsh and singular boundary conditions are retained
as explicit failure-path evidence. The near-degenerate prism is a quality
warning case; it is not silently promoted to a normal-quality mesh.

## External comparison boundary

The primary observables are displacement, total reaction and strain energy.
Stress is secondary and requires the same measure, evaluation point and
coordinate convention. The inherited WP05 affine same-mesh relative candidate
is `1e-6` and remains `OWNER_REVIEW_REQUIRED`; non-affine, distorted and
refinement cases require case-specific Owner approval before execution. No
threshold was retuned after observing QF output.

CalculiX 2.20 / C3D6 was executed from the pinned image
`qf-solver/calculix-nafems13h:2.20` (digest recorded in the evidence). The
minimal affine deck completed, but the comparison is recorded as
`NOT_FORMULATION_COMPATIBLE`: the C3D6 route reports two integration points,
whereas QF WEDGE6 production uses `TRI3_X_GAUSS2` with six points. The observed
displacement and energy differences are preserved as diagnostic data and are
not a QF qualification PASS.

Code_Aster 18.1 / PENTA6 was first reproduced in the pinned image. The root
cause was not a missing package: `mpi4py` is present in the image's Spack view,
but the stock `run_aster` profile does not expose that view. A derived local
image now exposes the pinned Python and dynamic-library paths, links the
`.mail` through a controlled `.export`, and executes `run_aster --no-mpi` with
one launcher process. The run recognizes `MECA_PENTA6` and completes without a
GUI. Its internal communicator is still `mpi4py` with size one; `--no-mpi`
means that no `mpiexec` relaunch occurs.

The affine same-mesh comparison is recorded as
`PASS_EXTERNAL_CORRELATION_BOUNDED`: relative displacement, total reaction and
strain-energy errors are respectively `1.73e-15`, `1.03e-15` and `3.46e-16`
against the predeclared `1e-6` WP05 candidate. The candidate remains
`OWNER_REVIEW_REQUIRED`; this is not a public WEDGE6 promotion. Pressure,
refinement and distorted external cases remain unclaimed.

## Status and boundary

WP09 is `PASS_WITH_LIMITATIONS` as a controlled robustness campaign. WEDGE6
remains `EXPERIMENTAL` with public qualification `DEFERRED`. This evidence is
not a general external validation, does not qualify pressure/refinement or
distortion against either external solver, and does not cover modal, dynamic,
nonlinear, J2, TL or contact routes. WP10 may proceed as a separate technical
work package, subject to its own mass and modal contracts.

Machine-readable records:

- `qualification/0_2_7/vnv_v2/wp09_cases.json`
- `qualification/0_2_7/vnv_v2/wp09_evidence.json`
- `qualification/0_2_7/vnv_v2/wp09r_code_aster_evidence.json`
- `qualification/0_2_7/wp09_state.json`
- `qualification/0_2_7/wp09r_state.json`
- `scripts/run_wp09_wedge6.py`
- `tests/unit/test_wp09_wedge6_robustness.py`
- `qualification/0_2_7/external_oracles/wedge6/docker/headless_contract.json`
