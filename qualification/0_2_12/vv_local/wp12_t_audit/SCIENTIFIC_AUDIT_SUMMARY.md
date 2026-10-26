# WP12-T — scientific audit synthesis

**Date:** 2026-10-26.<br>
**Overall verdict:** `WP12_T_SCIENTIFIC_AUDIT_COMPLETED`.<br>
**Modal:** `MODAL_ROOT_CAUSE_IDENTIFIED` — `TEST_CRITERION_DEFECT`.<br>
**TET4:** `TET4_ROOT_CAUSE_INCONCLUSIVE` — causal classification `INCONCLUSIVE`.<br>
**New QF Solver tests, FEM solves, benchmarks and mesh generation:** `NOT_PERFORMED`.<br>
**WP11:** `CLOSED`; **WP12:** `OPEN`; **WP13:** `OPEN`.

Completion means the requested evidence/code audit and prospective protocol are delivered. It does not mean the historical failures were corrected, that the TET4 deficit has a unique explanation, or that WP12 is ready for closure.

## A. Modal: cause identified for this failure

For the exact rational matrices, Sylvester's criterion establishes SPD: first principal minors are 2 and 20, determinants are 47/16 and 156. The exact polynomial is `(47/16) lambda² -47 lambda +156`; its discriminant is 376 and roots are `8 ±16 sqrt(94)/47`. The raw 2-norm condition numbers are modest, approximately 1.506 for M and 2.648 for K, with a well-separated spectrum. The roots therefore do not present a near-degeneracy or strongly ill-conditioned challenge.

The archived values differ from these scalar roots by at most 1.89e-16 relatively. Recorded original-equation modal residuals are about 1.01e-16 and 5.94e-17; the mass-Gram Frobenius error is 3.54e-16. These observables were emitted before the failing assertion. The root and mass assertions ran; later independent residual assertions were not reached after failure. Internal basis diagnostics and these emitted measurements are distinct evidence from a complete prospective assertion set.

The JUnit failure is localized to `assert_allclose(K_r, diag(lambda_ref), rtol=1e-10, atol=0)`. For a zero reference entry, the allowed difference is exactly `0 + 1e-10*abs(0)=0`. The two observed off-diagonal values of about -4.44e-16 therefore fail regardless of their scale. The routine returns an actual bilinear projection, not a matrix whose off-diagonal values are explicitly set to zero. Exact mathematical eigenvectors diagonalize K in the M metric, but floating vectors/products need not have exact floating zeros.

The WP04 structured projection computes and mirrors one upper-triangle bilinear scalar for exactly symmetric stored K; it does not force modal diagonality, alter K or average away asymmetry. The tolerated near-symmetric branch preserves the historical bilinear product. Inspection reveals no equation change that would explain an incorrect spectrum. The archived actual mode vectors are not exposed, so the audit cannot reconstruct which operation produced the last bit of the off-diagonal or independently recompute their residuals from raw vectors. This limitation does not obscure why the recorded assertion failed.

**Recommended correction:** specify a new prospective test with separate scalar-root, projection-arithmetic, diagonalization, residual and Gram checks. Retain existing root assertion and WP04 residual/Gram criteria where applicable; derive the projection allowance from machine arithmetic and operator/vector scales. Prefer an exact rational projection of the returned binary vectors in this 2x2 case. Do not amend or replay the historical test. The [criterion proposal](MODAL_NUMERICAL_CRITERION_PROPOSAL.md) details the bounds, units, conditioning and non-equivalence of the checks.

**Regression implication:** no solver correction is supported by this failure. A corrected test would verify only its declared small-matrix scope. Downstream harmonic/Newmark consumers and general WP04 non-regression remain separate WP12 questions.

## B. TET4: input integrity established, deficit not uniquely explained

The beam diagnostic arithmetic checks independently: area 0.16 m², bending inertia 0.0021333333333333334 m⁴, G≈26.923 GPa, kappa=5/6; bending gives -1.4285714285714285e-7 m and shear -1.1142857142857143e-9 m, totaling -1.4397142857142855e-7 m. The shear term is only 0.774% of this diagnostic compliance. This verifies the formula, sign and dimensions; it does not make a 1D beam solution exact for the clamped 3D solid or determine the size of continuum/clamp/load effects.

The preserved HDF5 arrays were inspected without importing or executing QF Solver. The data confirm:

- 12/96/768 tetrahedra, 12/45/225 nodes, 36/135/675 total DOFs; geometry [0,4] × [0,.4] × [0,.4] m and total volume 0.64 m³.
- Positive signed element volumes, two repeated scaled shape families, max-edge/min-edge ratio ≈5.196 and dihedral range ≈11.31–90 degrees. No worsening of those shape measures across levels, no nonmanifold or interior unmatched faces, and fine-tetra containment in coarse tetrahedra at both refinement steps within the stated barycentric inspection tolerance.
- Resultant force (0,0,-1) N on every mesh. Moment about the global corner origin is (-.2,4,0) N m; about the root-section centroid it is (0,4,0) N m. There is no unintended centroidal torsional resultant.
- Fixed pairs exactly match all three translations on the x=0 face: 12/27/75 constrained DOFs, leaving 24/108/600 free DOFs. No additional fixed direction was found.

These checks weaken gross orientation, coverage, topology, force-resultant and accidental-clamp explanations for the actual archived model. They do not demonstrate its flexural accuracy or a same-case comparison of solver routes.

| Remaining issue | What is established | What remains uncertain |
|---|---|---|
| P1 bending approximation | Constant-strain tetrahedra cannot exactly represent quadratic transverse displacement and bilinear axial displacement of a simple pure-bending field, whose shear terms cancel analytically. h_x/thickness is 5, 2.5, 1.25 across these meshes. | Actual parasitic shear/energy and its share of the deficit are unrecorded. This is not a demonstrated locking diagnosis. |
| Element/material algebra | B uses engineering shear; D uses G on matching shear entries; Ke is V B^T D B. Barycentric interpolation reproduces affine fields algebraically; batch and scalar gradient forms are consistent by inspection. | No new independent affine/kernel execution or complete assembled patch was performed. Existing test sources are navigation/evidence candidates, not current results. |
| Loading and observable | Tributary nodal forces conserve force and moments. They differ from consistent P1 triangular traction integration. The reported tip value is an equal-node average, not generally f^T u/F. | No displacement field is present in the preserved model/summary outputs. Work-conjugate or centroid values and their numerical difference are NOT_RECORDED and cannot be reconstructed offline. |
| Matrix-free route | Template local stiffness/scatter, homogeneous restriction and nodal-block-Jacobi-preconditioned CG are explicit. Normalization by max(norm(f),1) explains the reported residual scale. | No independent assembled residual, condition estimate or same-model direct solution is archived. A small residual against the same operator cannot establish discretization accuracy. |
| Refinement/reference | Displacement magnitude increases strongly; the three meshes are nested, but increments still grow. Beam-gap orders are descriptive. | Neither a stable 3D limit nor asymptotic order is established. Nested spaces alone do not give a bound for a changing nodal load functional and an unweighted tip output. |

Thus the likely investigation branch is coarse P1 flexural approximation together with reference/load/observable limitations, but no contribution has been quantified. A constitutive, assembly or matrix-free defect is not demonstrated; absence of such proof does not establish absence of a defect. Classification remains `INCONCLUSIVE`, rather than relabeling the 66.69% finest-level beam gap as a physical error or declaring an expected discretization limitation proven.

## C. Smallest informative next steps

1. Review and implement the new modal criterion as a separately identified prospective test; freeze it before an authorized attempt. It answers whether projection/eigenpair checks agree under mathematically suitable criteria.
2. For TET4, retain the completed input audit. Prepare a small independent affine/kernel oracle (T6) and a same-archived-model assembled-versus-matrix-free comparison (T2), starting with H1. Preserve complete displacement, reaction and energy data in the new case so the two tip functionals become observable. These cases distinguish kernel errors from route/solution errors.
3. If those checks agree, select one directional resolution/load experiment (T4) to investigate the P1 bending mechanism. Use further isotropic refinement (T3), element comparison (T5) or independent 3D reference (T7) only to answer the uncertainty that remains. Do not automatically run all of them.

The [prospective plan](PROSPECTIVE_TEST_PLAN.md) gives parameters, model-size ceilings, proposed time/attempt budgets, acceptance prerequisites and stop rules. Those budgets and new criteria require Owner review; there is no authorized new scientific case or frozen executable manifest in this audit.

## D. Review provenance, disagreements and limitations

The primary integrator's active runtime is GPT-6.1 Sol. Two fresh-context Luna-executor tasks investigated modal algebra and TET4 respectively; a third fresh-context Luna-executor task, `wp12_t_critical`, reviewed claims and source in read-only mode. Their configured role fixes the model to GPT-6 Luna; reasoning effort `high` was requested. Separate runtime launch-event metadata was not exposed, so no additional model/effort verification is claimed. All three tasks completed; no worker remained active at consolidation. The tool exposes interruption but no separate close operation.

The critical reviewer corroborated the modal algebra and conditional rounding bound and found no concrete TET4 implementation defect or demonstrated locking cause. It identified a terminology error in the draft: WP04's eigensolver tolerance 1e-10 was incorrectly described as an independent-root error criterion. The final proposal attributes root agreement to the existing test assertion and treats the algorithm setting separately. The reviewer also requested documenting the nodal block-Jacobi preconditioner; this source fact was added. A final challenge found that selecting the SciPy backend alone retains the generated model's CG method; the prospective direct comparison now explicitly requires `parameters={"method": "direct"}`, supported by the inspected solver. The integrator additionally removed unsupported arbitrary rounding multipliers/condition caps and corrected draft claims about raw RHS normalization, unavailable displacement arrays, shape congruence and the required scope of a 3D reference. No substantive causal disagreement remains; the unresolved TET4 alternatives are explicitly retained.

This is an internal scientific audit using separately tasked investigators and challenger, not external laboratory certification or physical validation. The audit has no scientific run/tentative budget because none is authorized; resources were limited to three specialist tasks and small existing-data/analytical calculations. Token or wall-time consumption was not instrumented as a campaign metric. The [integrity record](README.md#existing-evidence-inspected) identifies accessible evidence, verified hashes and current/frozen Git snapshots. All reported geometry arithmetic concerns previously generated models. Historical `FAIL`, `WARNING`, source files, contracts, tests, tolerances and WP dispositions remain preserved.
