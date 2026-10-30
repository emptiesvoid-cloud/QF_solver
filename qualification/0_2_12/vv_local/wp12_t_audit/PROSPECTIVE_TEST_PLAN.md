# WP12-T — minimal prospective verification plan

**Revision:** 2026-10-26; `PROPOSAL_ONLY / NOT_AUTHORIZED`.<br>
**New QF tests and FEM calculations in WP12-T:** `NOT_PERFORMED`.<br>
**WP12:** `OPEN`. The historical modal `FAIL` and TET4 `WARNING` remain unchanged.

The plan separates diagnosis from a possible correction and from its subsequent verification. Identifiers below are proposed study IDs, not registered executable nodeids. No new test file, campaign manifest or Owner execution decision is created by this audit. A prospective implementation must have its own identity and must not overwrite the WP12-S wrappers, assertions, receipts or evidence directory.

## 1. First decisions and dependencies

1. Review the [modal criterion proposal](MODAL_NUMERICAL_CRITERION_PROPOSAL.md). If accepted for implementation, create a new test without changing the historical test. Freeze its acceptance rules before executing it.
2. Use the archived-model findings in [the TET4 investigation](TET4_ROOT_CAUSE_INVESTIGATION.md) to rule on model persistence/topology questions already answerable without a solve. Do not schedule a replay merely to rediscover saved input data.
3. Approve only two small new TET4 discrimination cases initially: an independent affine/kernel oracle (T6) and a same-model operator/solver comparison (T2). They answer different questions and cannot substitute for one another.
4. Consider directional refinement (T4) only after model and implementation checks are satisfactory. Extend isotropic refinement (T3), compare element families (T5), or obtain an independent 3D reference (T7) only to resolve the remaining named uncertainty. None is an automatic universal WP12 closure condition.

The controlling governance remains [AGENTS.md](../../../../AGENTS.md), [QUALIFICATION_LOCAL_VV](../LOCAL_VV_POLICY.md), the [master-plan acceptance method](../../vv_master_plan/VV_MASTER_PLAN.md), and a future case-specific Owner decision. The old WP12-S decision cannot authorize any proposed ID below.

## 2. Modal prospective case

**Proposed ID:** `MODAL-2DOF-CRITERION-002`; `NEW_TEST_SPECIFICATION / NOT_IMPLEMENTED / NOT_RUN`.

Keep exactly the original rational K and M, two modes, dense backend, units/coordinate scaling and experimental maturity. Expose actual returned modes, eigenvalues, projected K/M, per-mode original-equation residuals, full mass Gram matrix, input hashes and all criteria before final assertions. Preserve all values if an assertion fails.

- Retain the original independent-oracle test's per-eigenvalue relative-error limit `1e-10`; this is an assertion criterion, distinct from the eigensolver's setting of the same numerical value.
- Retain WP04 modal residual and mass-orthogonality limits `1e-8` and the production diagonalization diagnostic, with their exact definitions.
- Check the projection computation separately from diagonalization. For this 2x2 fixture, exact rational evaluation of the bilinear forms using the returned binary64 vectors is feasible: `Fraction.from_float` treats each returned component as its exact stored value. Compare the production projection with that reference using a bound derived from its arithmetic, not a fixed arbitrary absolute tolerance. The [criterion proposal](MODAL_NUMERICAL_CRITERION_PROPOSAL.md) states the one-path/two-path gamma bounds and their assumptions.
- Check exact stored reduced symmetry only on the branch that deliberately mirrors one scalar. Do not require a numerically projected off-diagonal to be exactly zero.
- Freeze negative-control perturbations and demonstrate that each check detects its intended error: altered projection with unchanged vectors; wrong eigenvalue; non-eigenvector direction; nonorthogonal or incorrectly normalized vectors. These controls are test-design validation, not new evidence of physical solver accuracy.

**Output:** complete observables, assertion-level outcomes, original/future source identities and a separate receipt. A successful new test would demonstrate the new criterion and this small matrix case; it cannot erase the original `FAIL`, qualify WP04 generally, or establish downstream dynamic non-regression.

**Exit condition:** criteria reviewed and preregistered, arithmetic assumptions checked, all required observables present, and each applicable assertion satisfied in a separately authorized attempt. Otherwise preserve `FAIL`, `INCONCLUSIVE` or infrastructure status as appropriate. No solver correction is proposed on current evidence.

## 3. TET4 experiments and scientific questions

Keep the user's T1–T7 labels. Each row changes only the specified variables; all other physics, source identities and observable definitions must be frozen.

| ID | Question / proposed study | Variables and observables | What supports / challenges the hypothesis | Priority and qualitative cost |
|---|---|---|---|---|
| T1 | Is the intended input model actually represented, and what output can the archive support? | Read existing models only: coordinate/connectivity/fixed-set inventories, signed volumes, boundary faces, total load/moments. Distinguish stored input from missing displacement, energy and reactions. | A mismatch supports a setup/persistence defect; exact input agreement weakens that hypothesis but says nothing about solution accuracy. Energy or weighted-tip reconstruction is impossible if full displacements were not retained. | First; input inspection within this audit. Any new solution/postprocessing requiring missing data needs authorization. |
| T2 | Does matrix-free represent and solve the same discrete problem as independent assembled code? `TET4-ROUTE-CROSSCHECK-001` | Initially the unchanged H1 archived model: 12 TET4, 36 total DOFs. Compare element/scatter products on fixed deterministic probe vectors, free displacement vector, matrix-free and independently assembled residuals, reactions, strain energy, both tip means and load work. Escalate to unchanged H3 only if H1 leaves a specific scatter/template question unresolved. | Product disagreement isolates a route defect; product agreement but solution disagreement directs investigation to reduction/CG/preconditioning; agreement of both routes leaves shared formulation and discretization questions open. | MUST for attributing a route cause; low on H1, bounded on H3. |
| T3 | Does the same discretization approach a stable value? | One additional factor 8 is a possible first extension: cells 16x8x8, 6,144 TET4, 1,377 nodes, 4,131 total DOFs. Same material, clamp, load and both observables. No extrapolated continuum value is assumed. | A stable sequence can reduce uncertainty; continued large increments show the old sequence was inadequate. Neither proves equivalence to the beam or independently correct 3D elasticity. | SHOULD only after T2/T6; moderate and size-bounded. A factor 16 study is deferred to a separate decision. |
| T4 | Is longitudinal interpolation or section resolution controlling the stiffness? | From H3 (8x4x4), independently double nx only (16x4x4: 1,536 TET4, 1,275 total DOFs) or ny,nz only (8x8x8: 3,072 TET4, 2,187 total DOFs). Same force/moment and both tip functionals. Record bending/shear-related strain contributions if a mechanically consistent decomposition is defined. | Sensitivity to nx versus section refinement discriminates error mechanisms; it alone does not prove locking. A locking diagnosis also needs a defined slenderness/formulation comparison. | SHOULD after low-cost checks; moderate. These are candidate alternatives, not a combined authorized campaign. |
| T5 | Does a different approximation family remove a persistent error? | TET10, HEX8 or HEX20 only after verifying compatible geometry, material, quadrature, load/BC and output functional. Compare DOF/resolution as well as element count; avoid changing solver and element simultaneously. | Agreement of independently converged formulations weakens a route-specific explanation; divergence may reflect interpolation, quadrature, mesh or unmatched boundary data. | Conditional; moderate to high. No automatic requirement to run all families. |
| T6 | Are shape gradients, shear conventions, constitutive response and rigid/affine fields correct? `TET4-AFFINE-ORACLE-001` | New standalone exact tetrahedral affine/rigid-field oracle, including a non-axis-aligned positive-volume tetrahedron, known engineering strain, isotropic D and analytical energy. Test the single-element and batch kernels separately. Add a complete assembled affine patch only if needed, with independently integrated boundary traction. | Affine/rigid/energy inconsistency points to element/material/DOF code; agreement verifies these identities but does not verify bending accuracy. | MUST before assigning a formulation cause; low, distinct from a flexural solve. |
| T7 | How much of the beam gap is a genuine continuum-reference difference? | Independently reviewed 3D solution with matched clamp, traction/nodal load and observable, plus a documented reference error estimate. Same-mesh cross-code correlation and a converged 3D reference answer different questions. | Agreement with 3D but not beam supports reference mismatch; failure against a controlled 3D reference directs attention to discretization/implementation. | Conditional on the intended scientific claim; high. Code_Aster/Docker execution remains outside this audit. |

## 4. Criteria to freeze before an executable manifest

For T1, exact inventories, coordinate definitions, fixed components, resultant and moment are algebraic input identities. Use exact grid/rational arithmetic where possible; any floating comparison must state a scale and rounding allowance. They are not physical displacement acceptance thresholds.

For T2, first compare the operators on identical vectors; compare solutions only after constraining the identical DOFs and load vector. Preregister the vector norms, residual definition and conditioning/error budget. A displacement difference cannot be called a solver failure merely because it exceeds a freely chosen constant: relate the allowed difference to the two algebraic residuals and an applicable stability/conditioning estimate. If that estimate or a validated comparison tolerance is unavailable, mark the displacement comparison `CRITERION_TO_REVIEW` before execution. Preserve route-specific residuals, including the original `max(||f||,1)` convention; also report `||r||/||f||` for nonzero f so normalization is visible.

The prospective assembled direct route must explicitly call `solve_large_model(model, output_dir, solver_backend="scipy", parameters={"method": "direct"})`. Selecting only `solver_backend="scipy"` is insufficient: the generated model requests CG, and [_solve_scipy](../../../../src/solveur/large/solver.py#L125) takes that model method unless parameters override it. The [linear solver's direct branch](../../../../src/solveur/core/solvers/linear.py#L142) supports the proposed explicit choice. Separate the matvec comparison from direct-versus-CG solution comparison so an algorithm difference is not attributed prematurely to element assembly.

For T6, derive the exact affine strain/stress/energy and rigid-mode expectations independently of the tested B/Ke implementation. Freeze scale-aware floating arithmetic allowances from the selected operations. Positive volume, six rigid modes, affine reproduction and symmetry are distinct checks; satisfying one does not establish all the others. Do not silently reuse a test implementation as its own oracle.

For T3–T5, preregister both displacement functionals, force/moment equality and data completeness. No universal 1% beam-error limit, monotonicity rule, asymptotic order or locking threshold is approved here. A numerical convergence criterion or a reference-error threshold must be justified for the intended quantity and accepted before the run. For T7, match continuum loading and the observable before interpreting a correlation as verification. Physical validation still needs evidence of adequacy for an intended real-world use.

## 5. Candidate resource envelope — not approved

| Proposed unit | Maximum model size initially proposed | Attempts proposed | Proposed timeout | Resource caveat |
|---|---|---:|---:|---|
| Modal new criterion | Exact 2x2 matrices / 2 modes | 1 | 120 s | Reuses the small-case WP12-S timeout as a planning ceiling only. |
| T6 affine/kernel | A fixed small set of explicit tetrahedra, no mesh sweep | 1 | 120 s | Exact count/coordinates and calculations must be frozen in the new test. |
| T2 cross-route H1 | 12 TET4 / 36 total DOFs | 1 | 180 s | A SciPy direct assembled route is proposed; no PETSc/MPI/external dependency is needed. |
| Optional T2 H3 | 768 TET4 / 675 total DOFs | 1 | 180 s | Separate ID/decision only if justified by H1 outcome. |
| One T3 or T4 directional unit | At most 6,144 TET4 / 4,131 total DOFs | 1 | 1,800 s | Size ceiling derived from explicit candidate grids, not a measured runtime/memory forecast. |

All values above are `PROPOSED_OWNER_APPROVAL_REQUIRED`, including a possible 16 MiB per-stream soft log cap and single-thread numerical-library configuration. Existing WP12-S approvals do not transfer. CPU/RAM/storage requirements must be estimated from the actual new implementation before freezing the manifest; no unmeasured hard bound or filesystem sandbox is claimed. The previous local non-attested limitations must be explicitly accepted again or a suitable isolated environment selected.

Stop on identity/import mismatch, malformed selection or output, nonfinite values, solver failure, timeout, output budget, unexpected model size, or an unexplained scientific discrepancy. Preserve failed/partial outputs. No retry, tolerance edit or automatic progression to a larger case follows a failure.

## 6. Correction and disposition

- **Modal:** propose a new test criterion; no solver or physical formulation correction is supported by the present evidence. Review, implement separately, freeze and authorize the new case. Keep `MODAL-2DOF-POLY-001=FAIL`.
- **TET4 input or route defect, if later demonstrated:** identify the smallest offending layer, propose a separate source change and affected regressions, then qualify a new scientific identity. A fixture correction is not equivalent to preserving the old benchmark.
- **TET4 discretization/reference limitation, if later demonstrated:** document the usable resolution/model/observable scope and design an appropriate benchmark; do not modify the constitutive or element formulation merely to match a beam formula.
- **TET4 still inconclusive:** retain the hypothesis matrix and approve the next cheapest discriminating experiment. Keep `FEM-TET4-H-001` as characterization with helper `WARNING`.

No result in this plan closes WP12, changes maturity or authorizes publication. Its exit is an Owner-reviewable minimal protocol, not a completed correction or scientific campaign.
