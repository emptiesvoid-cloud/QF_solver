# TET4 reference and implementation audit — WP12-T TET4

## Identity and scope

Static inspection of `FEM-TET4-H-001` only. Checkout `checkout-0.2.12`, branch `emptiesvoids-cloud/0.2.12`, HEAD `8e3afe8ba89208c986e559712179fc992aa66c9d`, tree `a3b99ba6fa638b94bd91b0cd431f769cb2b4ff3c`. Frozen science identity from the execution record: commit `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b`; the integrator verified inspected `src/` files match the frozen source. Runner/tests are separate identities. This is not a new execution or qualification result.

The inspected external attempt is `20261026T095627Z-aedceeb89280`, case receipt SHA-256 `e8d93fae9cc07021e89444727551e39313a59c292305f7d0643dd27e2b23f8be`. Per parent’s archive audit, the receipt and 38 output hashes were independently verified; the three raw HDF5 hashes are reproduced below from this worker’s read-only hash calculation. Receipt was `PYTEST_PASS_ONLY`; utility diagnostic `WARNING`; physical validation `NOT_ESTABLISHED`; no independent 3D reference. It is bounded characterization, not a qualification verdict.

Run values: L=4 m, W=H=0.4 m, E=70 GPa, nu=0.3, Fz=-1 N; levels 12/96/768 TET4 and 36/135/675 DOF. Reported mean tip UZ is `-5.14927314061041e-9`, `-1.6781818466340907e-8`, `-4.795612893178559e-8` m.

## Independent reference arithmetic

Rectangular section: `A=WH=0.16 m²`, `I_y=WH³/12=0.0021333333333333334 m⁴`, `G=E/[2(1+nu)]=26.9230769231 GPa`, `kappa=5/6`.

- Bending: `F L³/(3 E I_y) = -1.4285714285714285e-7 m`.
- Shear: `F L/(kappa G A) = -1.1142857142857143e-9 m`.
- Sum: `-1.4397142857142855e-7 m`, matching the recorded diagnostic.

Both terms have units of metres. The computed level magnitudes are 3.58%, 11.66%, and 33.31% of this beam value (deficits 96.42%, 88.34%, 66.69%). Consecutive displacement changes are `1.1632545325730497e-8` and `3.117431046544468e-8` m; the response grows in magnitude, but the increment grows too. Orders 0.1263 and 0.4056 are based on error relative to this diagnostic. The arithmetic is verified; the 1D beam formula is not an exact or independently validated oracle for the clamped 3D solid.

The shear term is about 0.774% of the stated total beam compliance. Thus the recorded arithmetic does not contain a missing shear contribution capable of explaining the observed beam-relative gap; this does not bound other 1D-to-3D modeling differences. For nu=0.3, bulk-to-shear modulus is `2(1+nu)/[3(1-2nu)]=13/6`; the material is not approaching the incompressible limit nu=0.5. No volumetric-locking diagnosis follows merely from using a low-order solid.

## Source chain and algebra

- [Structured convergence utility](../../../../src/solveur/verification/tet4_structured_convergence.py#L106): beam formula 106–124; run defaults, generator/solver routing and reported arithmetic tip-node mean 156–265; diagnostic status checks 261–299. This study wrapper selects `matrix_free` or `petsc`; it does not select local SciPy assembled mode.
- [Block generator](../../../../src/solveur/large/generator.py#L107): cantilever configuration; six-tet split 168–186; clamp arrays 237–240; tip loads 243–278.
- [TET4 element](../../../../src/solveur/elements/solid/tet4.py#L25): signed volume/gradients 25–42; `Ke=V Bᵀ D B` and positive-volume check 44–51.
- [Voigt B](../../../../src/solveur/elements/solid/common.py#L16): components are normal strains then engineering shears `gamma_xy, gamma_yz, gamma_xz`; shear rows use the unsymmetrized gradient sums. [Isotropic D](../../../../src/solveur/materials/solid.py#L42) uses Lamé lambda in normal off-diagonals, lambda+2mu on normal diagonals, and mu=G on engineering-shear diagonals. Thus this B/D pair is energy-conjugate. With B in m⁻¹, D in Pa, volume in m³, Ke has N/m.
- [Batched kernel](../../../../src/solveur/large/tet4_batch.py#L8): volume*BᵀDB and symmetric averaging 8–28; oriented determinant/volume and gradients at [line 134](../../../../src/solveur/large/tet4_batch.py#L134); batched B at [line 165](../../../../src/solveur/large/tet4_batch.py#L165). Its B rows match the common helper by inspection.
- [Matrix-free CG](../../../../src/solveur/large/matrix_free.py#L31): same model loads and fixed arrays, free-DOF restriction, CG, recomputed residual 31–77. Element templates call `Tet4Element.stiffness` 230–242; `_apply_full_into` computes local `Ke u` and scatters using `np.bincount` in `_accumulate_node_values` 135–149, 211–227.
- The CG call explicitly supplies `M=operator.preconditioner()` and records `nodal_block_jacobi` ([matrix_free.py](../../../../src/solveur/large/matrix_free.py#L55)). The preconditioner builds per-node 3x3 block inverses ([construction](../../../../src/solveur/large/matrix_free.py#L150)); it is not a full stiffness inverse. This source fact does not establish its effectiveness, condition number, or a comparison with the assembled solution for this case.
- [Chunked assembly](../../../../src/solveur/large/assembler.py#L48): batch Ke, DOF maps and duplicate-summing CSR 48–125; load/fixed extraction 330–345. Actual assembled solve entry is `solve_large_model(model, ..., solver_backend="scipy")`, dispatching to `_solve_scipy` at [solver.py#L52](../../../../src/solveur/large/solver.py#L52) and [solver.py#L108](../../../../src/solveur/large/solver.py#L108); `_solve_scipy` assembles, restricts to free DOFs, solves, and restores zero constrained displacement 115–139.

The SciPy backend is not automatically a direct solve. These generated models request CG; `_solve_scipy` honors that method unless `parameters["method"]` overrides it. A prospective direct comparison must explicitly set `parameters={"method": "direct"}`; its supported [sparse direct branch](../../../../src/solveur/core/solvers/linear.py#L142) is separate from the matrix-free CG algorithm.

Algebraic affine reproduction: each linear tetra’s barycentric shape functions exactly reproduce `u(x)=A x+c`; its constant strain is the exact symmetric part of A and constant stress is D times that strain. This proves per-element affine interpolation consistency, not a complete assembled affine patch for arbitrary boundary loading. Existing WP04-B affine tests target the geometric/finite-strain route and are distinct from this linear small-strain case. A complete linear patch additionally needs compatible boundary tractions and assembled force balance.

Pure-bending kinematics show why linear TET4 bending deserves a controlled discrimination test, without proving locking: for an illustrative x-z beam field with curvature `kappa_b`, `u_x=-kappa_b x z`, `u_z=kappa_b x²/2` yields `epsilon_xx=-kappa_b z` and `gamma_xz=∂u_x/∂z+∂u_z/∂x=0` (sign follows the chosen curvature convention). A P1 tetra cannot exactly interpolate the quadratic `x²` or bilinear `xz` displacement; its piecewise affine interpolation may leave parasitic shear and excess stiffness. This is a kinematic approximation mechanism, not a demonstrated cause or effect size for the observed gap. Axial cell/thickness ratios are `h_x/t=5, 2.5, 1.25` over factors 1/2/4. Poisson response and actual bending/shear energy contributions were not recorded.

## Archived HDF5 inspection (read-only)

The external run directory contains three `model.h5` files. A one-off Python calculation read only HDF5 datasets with `h5py`, using NumPy for geometry/load arithmetic; it imported no QF modules, generated no mesh, assembled no matrix, and solved nothing. Schema for every file: `nodes`, `tet4`, `material_ids`, `fixed_nodes`, `fixed_dofs`, `load_nodes`, `load_dofs`, `load_values`. There is no displacement dataset and the saved `summary.json`, `report.md`, `results.csv` contain scalar tip means/residuals only. Therefore nodal displacement fields and the refined-level work-conjugate/center values are **NOT_RECORDED** in the preserved artifacts inspected here. Computing their differences requires an explicitly authorized future run that retains fields, not offline reprocessing of these model files.

| Level | H5 SHA-256 | bounds (m) | det / signed V per tet | Unique faces: boundary / interior | edge min–max (m) | max edge/min edge |
|---|---|---|---|---:|---|---:|
| 1 (2x1x1) | `4807FEA4CDE876F57EF1E376F9B0791F5367526D182E236655B39E73E57BAA7D` | [0,0,0]–[4,.4,.4] | .32 / .0533333333333 | 20 / 14 | .4–2.0784609691 | 5.1961524227 |
| 2 (4x2x2) | `4C1A085240D0A595B811CD546C2BC6B0067FCE26966DBFB345643940C93FAFC3` | [0,0,0]–[4,.4,.4] | .04 / .00666666666667 | 80 / 152 | .2–1.0392304845 | 5.1961524227 |
| 4 (8x4x4) | `51B415B4B431BCE594420D83312F0BC17A24AF17E4A996A914E0FCA3513FAFB7` | [0,0,0]–[4,.4,.4] | .005 / .000833333333333 | 320 / 1376 | .1–.5196152423 | 5.1961524227 |

All signed determinants are positive and identical within each level; each of the six local tets belongs to one of two repeated shape families (two sorted-edge signatures); minimum interior dihedral is 11.30993247 degrees and maximum 90 degrees at all levels. Volumes equal `L H W/(6 nx ny nz)`; summed volume is 0.64 m³. No duplicate or non-manifold triangular faces were found: every unique face had incidence one (boundary) or two (interior). Boundary-face counts by coordinate plane equal expected rectangular box triangulations: x planes 2/8/32 each; y and z planes 4/16/64 each. Every element belongs to one of two repeated scaled shape families; all share max-edge/min-edge ratio 5.196 and min/max interior dihedral 11.31/90 degrees, with no worsening quality distribution across levels. These are partial quality measures; no radius-ratio or scaled-Jacobian metrics were computed.

Nestedness was checked directly from archived connectivity and coordinates. For every fine tetra at level 2, its four vertices have nonnegative barycentric coordinates (tolerance 1e-10) in at least one level-1 tetra; likewise all 768 level-4 tetrahedra are contained in a level-2 tetra. Fine mesh is conforming by the face-incidence check, fills the same bounding box, and total volumes agree. This supports these particular archived simplicial meshes forming nested P1 spaces (each coarse tetra is partitioned by contained fine tetrahedra), not merely nested Cartesian nodes. It corrects the earlier assumption that nested FE spaces were unknown.

Load arrays all act on dof 2 (global Z). Resultant is `(0,0,-1) N` at every level. Moment about coordinate origin is `(-0.2,4,0) N m`; the x component is the y=.2 offset times Fz. About the loaded-face centroid `(4,.2,.2)`, the load has zero torsional moment, and about the clamp-face centroid `(0,.2,.2)` the bending moment is `(0,4,0) N m`. Thus the tributary load has correct force, face centroid, zero centroidal torsion, and expected 4 N m cantilever moment. Load-vector Euclidean norms from stored nodal arrays are `.5`, `.375`, `.21875 N` for factors 1,2,4. Accordingly `max(||rhs||₂,1)=1` in the utility, but `||rhs||₂` is not 1; reported same-operator residual numerators are numerically equal to relative residuals only because of that denominator.

Stored clamp node/component pairs match all three translations on every x=0 face node: 4 nodes/12 pairs, 9/27, 25/75. These are translational solid constraints, no rotational DOFs.

Tributary nodal loads are a defined benchmark input, and they preserve total force and first moment. Do not call them defective. They are not the same as consistent uniform traction integrated against the six-tet boundary’s P1 triangular face functions in general: on one square split into two triangles, P1 corner fractions are 1/3, 1/6, 1/3, 1/6, versus 1/4 each for tensor-product tributary weights. Both distributions conserve force and centroid on the square. Source also provides a separate `surface_consistent` Q4-like face rule, which gives quarter weights per rectangular face cell; that too differs in nodal pattern from triangular P1 surface integration. Compare them only as distinct load discretizations with the same resultant/moment.

## Observable and residual semantics

The utility computes equal-node arithmetic mean UZ at x=L (utility line 239). It is not the work-conjugate displacement for the archived force vector, which is `fᵀu/Fz`. H1 has 4 equally weighted loaded nodes, so those functionals coincide there; H2 and H3 have 9 and 25 tip nodes and nonuniform load weights, so equality is not guaranteed. Since HDF5 lacks `u`, weighted/center observables cannot be recalculated: **NOT_RECORDED**, not merely pending arithmetic.

Matrix-free residual is recomputed as `||rhs-A_free x||₂ / max(||rhs||₂,1)` with its own operator. Reported values are 4.009e-9, 2.668e-9, 2.140e-9 and denominator is 1 N by the norms above. This indicates iteration convergence against that operator; it does not bound displacement error without conditioning information, prove route equivalence, or validate the continuum reference.

Using `||rhs||` instead of the reported denominator gives approximately `8.018e-9`, `7.115e-9`, and `9.785e-9`, consistent with the code's CG `rtol=1e-8` criterion. The decreasing reported residual is partly influenced by the decreasing norm of the distributed nodal load; it is not evidence that displacement accuracy improves by the same factor. The `max(...,1)` convention also depends on the input force unit scale, which is why both the numerator and load norm should be retained.

Even though the archived P1 spaces are nested, a variational monotonic-compliance argument additionally requires the same continuous load functional on those spaces and the matching work observable. Here tributary nodal quadrature changes with the grid and the reported quantity is an unweighted nodal mean. Nestedness alone therefore cannot establish a monotone bound or a formal convergence rate for this reported scalar.

## Existing tests and evidence boundaries

The following source nodeids exist; their presence does not establish they ran in this case or passed on current HEAD:

- Element checks: `tests/unit/test_tet4_element.py::test_tet4_stiffness_is_symmetric`, `::test_tet4_has_six_rigid_body_modes`, and `::test_tet4_rejects_inverted_or_degenerate_element`.
- Batch-vs-element stiffness: `tests/unit/test_large_tet4_batch.py::test_batched_tet4_stiffness_matches_element_reference`.
- Matrix-free operator-vs-assembled matvec: `tests/unit/test_wp15_matrix_free.py::test_matrix_free_workspace_matches_assembled_and_keeps_results_independent`.
- Full solve-vs-solve exists for an orthotropic one-cell scope, not this isotropic archived cantilever: `tests/unit/test_orthotropic_dynamic_large.py::test_orthotropic_large_matrix_free_matches_assembled`.
- A separate WP04-B geometric affine patch has nodeids `tests/verification/test_wp04_b_geometric_identities.py::test_b09_b12_tet4_affine_patch[0]` through `[3]`; it is not the current small-strain cantilever case.
- Study contracts: `tests/unit/test_tet4_structured_convergence.py::test_nested_plan_has_deterministic_levels`, `::test_cantilever_generator_uses_transverse_tributary_loads`, and `::test_timoshenko_reference_and_convergence_metrics`.

No exact current-case assembled-vs-matrix-free solution comparison is present in the archived outputs. The study wrapper itself uses `solve_structured_matrix_free`, not local SciPy assembled. For a future same-model local comparison the actual assembled entry is `solve_large_model(..., solver_backend="scipy", parameters={"method": "direct"})`; comparing against matrix-free must use an explicit separately approved case entry, not treat existing unrelated tests as its result.

## Verdict

**ROOT_CAUSE_IDENTIFIED: NO — INCONCLUSIVE.** Archived models verify expected force/moments, clamp, positive elements in two repeated scaled shape families, conforming topology, and nested mesh spaces. Static algebra verifies the linear element’s affine reproduction and the routes’ common intended `V BᵀD B` form. These findings reduce the likelihood of gross load, constraint, orientation, or mesh-topology errors. They do not quantify spatial error or establish matrix-free/assembled solution agreement for this case. The beam-vs-solid oracle mismatch, very coarse h/t samples, non-equivalent mean/work observables, and plausible P1 bending shear contamination remain explanations to discriminate. No cause’s share of the 66.69% finest-level beam-relative deficit is measured; automatic locking or solver-defect attribution is unsupported.
