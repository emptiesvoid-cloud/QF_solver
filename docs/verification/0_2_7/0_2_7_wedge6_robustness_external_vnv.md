---
doc_id: DOC-027-WP09-EXTERNAL-001
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

## Original external comparison boundary

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

The first Code_Aster 18.1 / PENTA6 reproduction was recorded in the WP09-R
lot. The root cause was not a missing package: `mpi4py` is present in the image's Spack view,
but the stock `run_aster` profile does not expose that view. A derived local
image now exposes the pinned Python and dynamic-library paths, links the
`.mail` through a controlled `.export`, and executes `run_aster --no-mpi` with
one launcher process. The run recognizes `MECA_PENTA6` and completes without a
GUI. Its internal communicator is still `mpi4py` with size one; `--no-mpi`
means that no `mpiexec` relaunch occurs.

That prior affine same-mesh comparison was recorded as
`PASS_EXTERNAL_CORRELATION_BOUNDED`: relative displacement, total reaction and
strain-energy errors are respectively `1.73e-15`, `1.03e-15` and `3.46e-16`
against the predeclared `1e-6` WP05 candidate. The candidate remains
`OWNER_REVIEW_REQUIRED`; it was not a public WEDGE6 promotion. Its external
coverage was intentionally limited to that single affine case.

## WP09-FINAL external closure

WP09-FINAL replays the declared Code_Aster PENTA6 route through the same
headless derived image and extends the external evidence without changing the
kernel or any existing element formulation. All 12 declared cases completed:
affine tension and compression, shear, bending, TRI3 pressure, QUAD4 pressure,
prescribed displacement, a conforming multi-element mesh, one declared
affine-skew prism and refinement levels 1, 2 and 4.

The primary observables are displacement, total reaction and strain energy.
The maximum relative errors over the 12 cases are `2.93e-15`, `3.60e-15` and
`2.48e-15`, respectively, against tolerances fixed before execution: `1e-6`
for `AFFINE_SAME_MESH`, `1e-5` for the declared refinement series and `1e-5`
for the declared distorted case. The tolerance values remain
`OWNER_REVIEW_REQUIRED`; they are bounded evidence policies, not universal
accuracy claims. The prescribed-displacement reaction is explicitly derived
at the imposed degrees of freedom so that it has the same physical meaning as
the Code_Aster support reaction.

The external campaign verdict is `PASS_EXTERNAL_CORRELATION_BOUNDED`: Code_Aster
ran all 12 cases, all 12 primary comparisons passed, and final external replay
was deterministic. CalculiX C3D6 remains `NOT_COMPARABLE` because its inherited
integration route is not equivalent to QF WEDGE6 production
`TRI3_X_GAUSS2`. No stress claim is made without equivalent sampling and
coordinate conventions.

## Status and boundary

WP09 is `PASS_WITH_LIMITATIONS` as a controlled robustness campaign. WEDGE6
remains `EXPERIMENTAL` with public qualification `DEFERRED`. The combined
evidence is not a general external validation and does not cover modal, dynamic,
nonlinear, J2, TL or contact routes. WP10 may proceed as a separate technical
work package, subject to its own mass and modal contracts.

Machine-readable records:

- `qualification/0_2_7/vnv_v2/wp09_cases.json`
- `qualification/0_2_7/vnv_v2/wp09_evidence.json`
- `qualification/0_2_7/vnv_v2/wp09r_code_aster_evidence.json`
- `qualification/0_2_7/external_oracles/wedge6/wp09_final_contract.json`
- `qualification/0_2_7/vnv_v2/wp09_final_external_cases.json`
- `qualification/0_2_7/vnv_v2/wp09_final_external_evidence.json`
- `qualification/0_2_7/wp09_final_state.json`
- `qualification/0_2_7/wp09_state.json`
- `qualification/0_2_7/wp09r_state.json`
- `scripts/run_wp09_final_external.py`
- `scripts/run_wp09_wedge6.py`
- `tests/unit/test_wp09_wedge6_robustness.py`
- `tests/unit/test_wp09_final_external.py`
- `qualification/0_2_7/external_oracles/wedge6/docker/headless_contract.json`
