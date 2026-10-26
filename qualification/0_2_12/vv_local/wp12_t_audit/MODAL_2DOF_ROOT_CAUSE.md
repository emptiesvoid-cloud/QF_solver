# WP12-T modal 2-DOF numerical root-cause audit

**Disposition: `TEST_CRITERION_DEFECT` for the archived MODAL-2DOF-POLY-001 failure.** The receipt’s pre-assertion observables show the scalar eigenvalue errors, eigenpair residuals, and mass-orthogonality error are below their recorded limits; only the root and mass assertions had executed before the failure, while the later residual assertions were not reached. The failure is the projected-stiffness assertion comparing a floating-point off-diagonal of `-4.4408921e-16` to exact zero with `atol=0`. This is not evidence of a modal solver defect. It is not a qualification decision or a current-HEAD run.

## Identity and scope

This static audit was prepared in `checkout-0.2.12`, branch `emptiesvoids-cloud/0.2.12`, HEAD `8e3afe8ba89208c986e559712179fc992aa66c9d` (initially clean), against frozen science commit `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b`. The archived test receipt separately binds its science source to the same frozen commit/tree and test source to `cb445462e3e59fa487c28a0914d8d23ad47205e6`, tree `92feabc4dc86f142e5c042a232c9c529ec6210bf`.

This is a read-only code/evidence audit plus independent stdlib analytic recalculation. No QF imports, test collection, pytest, solver, or FEM execution was performed. Repository line references below refer to the named frozen source content; links are repository-relative.

## Exact analytical case

For the contract/test matrices

\[
M=\begin{bmatrix}2&1/4\\1/4&3/2\end{bmatrix},\quad
K=\begin{bmatrix}20&-2\\-2&8\end{bmatrix},
\]

both are symmetric positive definite: `det(M)=47/16>0`, `M11=2>0`; `det(K)=156>0`, `K11=20>0`. Under the customary assumption that the two generalized coordinates use compatible displacement units and M has a consistent mass scaling, mass normalization makes `φᵀMφ=1`; then `K_r=ΦᵀKΦ` and λ both have inverse-time-squared units, not the original physical stiffness units. With differently scaled or heterogeneous coordinates, those units and numerical conditioning must be interpreted through the declared DOF scaling. Expanding the generalized characteristic determinant exactly gives

\[
\det(K-\lambda M)=\frac{47}{16}\lambda^2-47\lambda+156,
\quad \Delta=376,
\quad \lambda_{1,2}=8\mp\frac{16\sqrt{94}}{47}.
\]

Numerically these are `4.699452011971861` and `11.300547988028141` (rad² per consistent time unit squared). A vector proportional to `[1, -(20-2λ)/(-2-λ/4)]` satisfies the first row of `Kφ=λMφ`. One analytically constructed mass-normalized sign choice is approximately `[0.22143825253196775, 0.7393982561290311]` and `[0.6794140108857991, -0.3662530309268925]`; each has `φᵀMφ=1`, and their cross product in the M metric is approximately `-5.97e-16`. These vectors follow from the exact matrix equation and are not proof that the archived solver returned these particular vectors; the archive did not expose its modal vectors. Sign and scaling of eigenvectors are non-unique. The raw M and K 2-norm condition numbers are approximately `1.50636` and `2.64800`; under diagonal congruence the scaled condition numbers are about `1.337` and `1.376`; the eigenvalue relative gap is about `0.5841`. This is a well-conditioned, clearly separated small case, not a near-degeneracy challenge.

These values are analytical recalculation, not fresh execution evidence. The exact coefficients, discriminant, roots, normalized observables, and historical run output are independently consistent at the displayed precision.

## Source and archived evidence findings

- [`ModalBasis._from_operators`](../../../../src/solveur/core/analyses/modal_basis.py#L172) requests `requested_modes + 1` where available from the generalized eigen backend, sorts the eigenpairs, rejects nonpositive eigenvalues, and mass-normalizes selected vectors. The call uses `_EIGENSOLVER_TOL` and `_EIGENSOLVER_MAXITER` (lines 209–219); WP04 records `1e-10` and 5000 as the solver settings.
- [`modal_basis_numerics.mass_normalize_and_handle_degenerate_subspaces`](../../../../src/solveur/core/analyses/modal_basis_numerics.py#L86) normalizes each vector using `sqrt(φᵀMφ)` and only rotates an effectively degenerate cluster. The present roots are far outside the cluster threshold.
- For exactly symmetric stored K, `_from_operators` calls [`project_exact_symmetric_bilinear`](../../../../src/solveur/core/analyses/modal_basis.py#L300) and assigns each computed upper-triangle scalar to both mirrored reduced entries; for a tolerated, not-exactly-symmetric K it retains the historical direct product `ΦᵀKΦ` (lines 300–314). The structured path is mathematically the same bilinear projection under exact K symmetry; its summation order may differ in floating point. It neither averages the completed matrix nor changes K. WP04 static docs describe the same behavior in [MECHANICS.md](../../../../docs/ai/MECHANICS.md#dynamic-operators-and-modal-reduction).
- The production implementation computes `M_r=ΦᵀMΦ`, checks its Frobenius distance from identity, checks each scale-normalized modal residual, and checks projected K against `diag(λ)` with a relative Frobenius error, all at inherited `1e-8` limits ([modal_basis.py](../../../../src/solveur/core/analyses/modal_basis.py#L316), [modal_basis_numerics.py](../../../../src/solveur/core/analyses/modal_basis_numerics.py#L156)). The WP04 contract gives definitions and limits ([wp04 contract](../../../../qualification/0_2_12/wp04_modal_basis_damping_contract.json#L20)).
- The prepared-input spectral screen uses diagonal congruence `D^-1/2 A D^-1/2`, dense Cholesky/eigenvalue analysis up to 256 DOFs, or sparse smallest-algebraic Ritz screening with residual; it expressly does not call the sparse screen a proof ([modal_basis_numerics.py](../../../../src/solveur/core/analyses/modal_basis_numerics.py#L33)). This small matrix pair has scaled eigenvalues well above the contract minimum `1e-12`.
- The independent-oracle test source checks exact polynomial coefficients, relative eigenvalue agreement, projected M, projected K, residuals, mass Gram error, and experimental maturity ([test_modal_two_dof_independent_oracle.py](../../../../tests/unit/test_modal_two_dof_independent_oracle.py#L20)). Its projected-K assertion uses `rtol=1e-10, atol=0` at line 63, so a theoretically zero entry has no absolute roundoff allowance.
- The archived attempt at `evidence://WP12-S-QUANT-001/MODAL-2DOF-POLY-001/20261026T095500Z-0494258ea65e` (receipt SHA-256 `a46d0d62740f79128552982ffd9c1835d458307bf6f9b261ba40320b02d3fd31`) is `FAIL`, exit code 1, one selected node, source import points to the frozen science checkout, and receipt interpretation explicitly says `PYTEST_PASS_ONLY` is not an oracle verdict or qualification decision. Its JUnit failure is solely the projected-K allclose assertion: two off-diagonal entries differ from exact zero by `4.4408921e-16`. The JSON payload records roots `[4.699452011971862, 11.300547988028141]`, relative root errors `[1.88996e-16, 0]`, residuals `[1.01023e-16, 5.94130e-17]`, and mass-Gram Frobenius error `3.53908e-16`; the recorded values are below their stated limits, but the test’s later residual and orthogonality assertions were not reached after the projected-K assertion failed. The observable payload does not expose the actual modal vectors or reduced K, so no claim about those unrecorded values is inferred beyond the JUnit excerpt.
- The existing broad extraction test includes a same-backend comparison and nonzero `atol` for projected operators at [`test_wp12_s_quantitative_extraction.py`](../../../../tests/unit/test_wp12_s_quantitative_extraction.py#L115), but that is not an independent eigenvalue oracle. The targeted polynomial assertion was later stricter at lines 237–303, creating the zero-entry criterion issue. The symmetric-projection unit test checks structured-vs-dense bilinear agreement with `2e-16` absolute and relative tolerances on a synthetic projection ([test_modal_symmetric_projection.py](../../../../tests/unit/test_modal_symmetric_projection.py#L22)); it is not this eigenpair test and does not replace the independent case oracle.

## Root-cause classification

**Primary: `TEST_CRITERION_DEFECT`.** A relative-only comparison against a zero reference makes the acceptance condition impossible for any nonzero roundoff, however small. The recorded absolute miss is about `4.44e-16`, while the diagonal modal stiffness values are order `1–10`; it is consistent with floating-point evaluation of the symmetric bilinear projection and its eigensolver vectors. The archived receipt does not include enough modal-vector/reduced-matrix precision to prove which arithmetic path produced that last bit, but there is no basis to label it as a physical/model defect.

**Not established: solver defect.** Independent exact roots and reported residuals support correct eigenpair extraction for this case. The current test does not quantify a perturbation in K or M and does not show a wrong eigenvalue or eigenvector. No new solver execution was conducted.

**Not established: symmetric-projection defect.** The exact-symmetry code intentionally mirrors one bilinear scalar into the opposite entry, thereby guaranteeing exact stored reduced symmetry. `ΦᵀKΦ` remains the mathematical definition. A roundoff-level off-diagonal is expected because distinct numerical eigenvectors are not exact symbolic vectors. A reproducible discrepancy larger than a scale-aware rounding/backward-error bound would merit a separate projection or eigenvector investigation.

**Evidence status:** archived failed local V&V attempt and static source review only. No PASS, no qualification closure, and no current-HEAD non-regression result. The WP04 contract marks the modal basis experimental and states numerical pass does not imply qualification ([contract](../../../../qualification/0_2_12/wp04_modal_basis_damping_contract.json#L5)).
