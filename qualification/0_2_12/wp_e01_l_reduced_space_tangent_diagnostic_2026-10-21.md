# WP-E01-L — Reduced-Space J2 Tangent Diagnostic Preparation

Date: 2026-10-21
Branch: `codex/qf-wp-e01-a-implementation-20261020`
Baseline: `affa6346b57224accceb35bd27d6a98b4fc46e95`

## Outcome

Prepared a hash-bound, source-only diagnostic for the Newton-relevant reduced J2 operator. The module compares the production reduced tangent action with a separately implemented, fixed-history Decimal derivative of the reduced internal-force residual for TET4 and HEX8 and for perfect plasticity and linear isotropic hardening. It includes two admissible projected directions per family/material combination and fail-closed projection controls.

No pytest collection, tests, finite-difference sweeps, FEM solve, public solver, Gmsh, worker, or native backend was run in WP-E01-L. The earlier WP-E01-K result (12/12 under its own executable identity) is historical and was not repeated. The historical 6.74–11.03% weak full-space discrepancies remain unresolved. Projection in this package constructs valid reduced directions; it does not reclassify the original full-space vectors as admissible Newton directions.

## Repository and preservation

The starting worktree was the required clean WP-E01 branch and HEAD. The origin was `https://github.com/emptiesvoid-cloud/QF_solver.git`. Production source was not edited. The frozen E01-A/Newton criteria, J2 constitutive equations, global assembly, line-search certificate registry, public routes, and previous scientific gates are unchanged. The canonical roadmap and other work-package worktrees were not modified.

The WP-E01-K report and its 12/12 evidence remain intact. Its report SHA-256 is `C9628D955436395136B327E79E163D765881034D119B92EB17AEBAB7A4E0D1C8`.

## Reduced-space operator and admissibility

Let `Q_f` be the full-by-free injection matrix that maps reduced coordinates into the full displacement vector. The tested residual and tangent are

\[
R_f(u)=Q_f^T(F_{\mathrm{int}}(u)-F_{\mathrm{ext}}),\qquad
K_{ff}(u)=Q_f^T K_t(u)Q_f.
\]

For a dimensionless, unit-norm admissible direction `v_f`, the diagnostic compares

\[
K_{ff}v_f
\quad\text{with}\quad
\frac{R_f(u+hQ_fv_f)-R_f(u-hQ_fv_f)}{2h}.
\]

Every plus/minus oracle evaluation uses the same synthetic incoming material-history snapshot. The fixture has `F_ext = 0`, so `R_f = Q_f^T F_int`. With this residual sign, the Newton correction equation is `K_ff * delta_u_f = -R_f`. The test does not solve this equation or assess convergence.

`DofManager` orders solid translations as UX, UY, UZ. `GlobalAssembler.fixed_indices` supplies the prescribed index set; the fixture checks the exact free list against the center node’s three translational DOFs. For the TET4 fan mesh, 8 of 9 nodes are prescribed (24 of 27 DOFs) and center node 8 is free. For HEX8, 26 of 27 nodes are prescribed (78 of 81 DOFs) and center node 13 is free. `BoundaryCondition` represents fixed DOFs with zero prescribed values in this model API. The preload and base displacements therefore move only the free center node and leave all constrained components exactly zero. The plan and its original `DofManager` are retained together and checked with `plan.matches(model, dofs)`.

The seed is projected by zeroing prescribed components, then normalized. Projection is rejected for malformed/nonfinite input, invalid or duplicate fixed indices, a zero vector, no free DOFs, or a free projection no larger than `128 * binary64 epsilon` times the original norm. This is a direction eligibility guard, not a tangent acceptance threshold.

One seed reproduces the earlier near-translation pattern before projection. Its projection retains the center node’s free x component and is therefore an admissible reduced direction after projection; the projected vector is essentially a center-node direction, not a rigid translation. The original full-space near-translation, which contains prescribed components, is not passed to the reduced derivative check. The second seed is a mixed vector projected onto the same free subspace.

## Fixture and independent oracle

| Fixture dimension | Prepared values |
|---|---|
| Element family | TET4 fan mesh (12 elements, 1 integration point each); HEX8 mesh (8 elements, 8 integration points each) |
| Elastic parameters | `E=210 GPa`, `nu=0.30` |
| J2 parameters | `sigma_y0=250 MPa`; `H=0` or `H=1.5 GPa` |
| Frozen-history preload | Center-node-only displacement of `0.0016 m * [1, -0.5, 0.75]`; all prescribed boundary DOFs remain zero. Every history entry is finite and shape-valid, and at least one integration point must have nonzero accumulated and tensor plastic strain |
| Base displacement | Center-node-only displacement of `0.003 m * [1, -0.5, 0.75]`, plus a small center-node offset; every prescribed component remains zero |
| Oracle precision | 80-digit standard-library `Decimal`; every stored binary64 input is reconstructed with `Decimal.from_float` |
| Direction count | Two projected directions for each family × hardening combination |
| Main derivative cases | 8 (2 families × 2 hardening values × 2 directions) |

The Decimal oracle independently constructs TET4 constant gradients and HEX8 trilinear gradients with 2×2×2 quadrature, forms the small-strain tensor, performs the J2 radial return in tensor notation, integrates internal nodal forces, and scatter-adds them. A synthetic prior material evaluation supplies the incoming plastic history; the history and accumulated equivalent plastic strain are the exact represented input values and remain fixed. This state table is a diagnostic input snapshot, not evidence of a solver-committed or equilibrated increment. The oracle records each integration point's elastic/plastic branch identity and distance to the yield switch. Mixed elastic/plastic base branches are allowed, but every plus/minus evaluation must preserve the corresponding base branch. The production tangent is computed by the actual in-memory nonlinear assembly and restricted with (Q_f); it is not used to generate the Decimal force derivative.

This is independent in constitutive/geometry/quadrature/force calculation, but uses the same model coordinates, connectivity, material inputs, and accepted history as input data. It does not independently validate how that history was created, the production history evolution, or the full Newton transaction. Production tangent binary64 entries are exactly reconstructed into Decimal for the matrix-vector product; this adds no precision to the tangent itself.

The centered sweep contains six ordinary-scale steps from `1e-4` through `3e-7 m` and six finer Decimal steps from `1e-8` through `1e-18 m`. Five adjacent-pair Richardson estimates are prepared from the ordinary-scale sweep. Each direction is unit normalized, so actions and derivative errors have units N/m. The diagnostic records absolute error, global stiffness-relative error, direction-local error when defined, reference action norm, branch margin, accepted-state digest, production/Decimal base-force difference, full step sweep, and Richardson estimates. These values are printed by the test for later execution evidence.

The reporting scale `K_REFERENCE_N_PER_M = 5.25e11 N/m` is not an acceptance threshold. Its stated provenance is `max(3K, 2mu) * V_ref / L_ref^2`, with `K=175 GPa`, `V_ref=1 m^3`, and `L_ref=1 m` for the declared elastic parameters. No tangent tolerance, plateau pass rule, or scientific gate is asserted.

## Static test inventory and safety

The static inventory is 15 parameter-expanded cases across two test functions:

1. Eight reduced tangent diagnostics: TET4/HEX8 × (H=0/1.5\) GPa × projected historical-seed/mixed directions.
2. Seven projection refusals: all prescribed, numerically degenerate free projection, nonfinite seed, wrong shape, duplicate fixed index, out-of-range fixed index, and zero seed.

The executable is hash-bound as `NUMERICAL_UNIT`. The test body imports NumPy, pytest, Decimal, and in-memory model/assembly/state helpers. Source inspection found no public `solve`, `solve_model`, Newton driver, load-control, Armijo activation, Gmsh/native backend, network, worker, subprocess, or test-body filesystem write. The nonlinear assembly module imports conditional contact helpers, but the fixture has no contact pairs. The collection guard is intentionally allowed to write its exact node/fixture record in the isolated temporary directory, then rechecks it before the test loop. The fixed-target supervisor uses one shell-free child, but was not run in this mandate.

Import/collection closure was reviewed statically only. A broad AST closure walk over production package initializers can over-approximate imports (including conditional contact utilities and an unused subprocess helper in the manifest/signing area); no test body calls that helper. No runtime import, pytest collection, child launch, or native library load was attempted. A future execution GO must repeat a fresh exact-path import/collection/process-path review.

The manifest records the prepared limits (256 MiB process and job committed memory, one active process, 120-second parent deadline, kill-on-close, no breakaway/retry, and single BLAS thread), but explicitly marks runtime enforcement `false` for WP-E01-L. Do not treat these limits as runtime evidence until the parent supervisor has been run after a separate Owner GO and its Job Object settings/counters are verified.

## Review findings

A separate read-only reviewer examined the reduced-space mapping, J2 state convention, Decimal methodology, branch checks, dimensions, and threshold status. The reviewer confirmed the projection defines admissible center-node DOFs, the sign and units are coherent, and no tangent threshold is asserted. The first review identified two preparation issues: the original affine displacement did not satisfy this model API's zero fixed values, and the diagnostic stiffness scale needed provenance. The test was corrected to use center-node-only preload/base displacements compatible with the fixed DOFs; it now explicitly requires nonzero plastic history but permits mixed base branches. Scale provenance was added to source and manifest. In the final rereview, the reviewer confirmed these corrections and caught an overstatement in the manifest branch rule: production tangents are evaluated only at the base state, not at each finite-difference perturbation. The manifest now states that production and Decimal branch arrays are compared at the base; only the Decimal plus/minus branches are required to preserve the Decimal base branch. No tests or numerical calculations were run and no scientific gate was approved.

Remaining scientific limitations:

* The historical weak full-space mismatches remain unresolved; the projected seed tests a different reduced-space direction.
* The derivative oracle differentiates force at a fixed synthetic prior-material history snapshot. The displacement satisfies zero prescribed values, but is not claimed to be an equilibrium solution. The snapshot was generated by a prior constitutive evaluation, not a solver commit. It does not validate a converged accepted increment, state evolution, or Newton increment convergence.
* The fixture has zero external force and does not test displacement-dependent/follower loads, reactions, line search, cutback, checkpoint durability, or native FEM.
* No measured derivative errors or branch margins exist yet because the module has not been collected or executed.
* All candidate tangent acceptance criteria remain proposed and require separate Owner review.

## Prepared artifacts and identities

| Artifact | SHA-256 |
|---|---|
| `tests/unit/test_wp_e01l_j2_reduced_space_diagnostic.py` | `DE87ED55EFC5DB341A4F90FC0AD34DE4758ACBFD76241C91F7A37C7B80A61D2A` |
| `tests/conftest.py` | `34B6D57A76BE6C84D7B803C6D1E9C1899E800B81E6BC1CAD8746139858371F71` |
| `experiments/wp_e01l_collection_guard.py` | `5105BB6EA5AD68D481E5BAC4AB14671DA1044045ACA6FD019580DD99F62919C8` |
| `experiments/wp_e01l_reduced_space_supervisor.py` | `F6000E9DF5391681B831EC5D16514D315D36CB2377CE9A94428A8C744DF0B831` |
| `qualification/0_2_12/wp_e01_l_reduced_space_execution_manifest_2026-10-21.json` | `6F6C1E497317500D8BEF710A4E4C65E051B2B285058B0871FECEEFB3148F7F2E` |

The manifest freezes all 29 production-source hashes inherited from the WP-E01-K campaign and the exact static node allowlist. All production pins were checked against the K manifest; no production file was changed. The manifest is preparation metadata only and does not authorize execution. Its supervisor limits have not been verified at runtime for WP-E01-L.

## Required next Owner decision

The next Owner GO should authorize one guarded collection and, conditionally, one supervised run of the exact diagnostic module below. It must bind every artifact by these hashes, preserve the 15-node allowlist, require fresh Windows Job Object limit/process-cleanup verification, prohibit automatic retry, and leave all tangent thresholds proposed. The exact parent command is:

```text
C:/Python313/python.exe -m experiments.wp_e01l_reduced_space_supervisor
```

The child target is only `tests/unit/test_wp_e01l_j2_reduced_space_diagnostic.py`. If collection differs or any identity/safety gate fails, stop without test execution.

## Status

```text
REDUCED_SPACE_TANGENT_DIAGNOSTICS: PREPARED_NOT_RUN
RIGID_TRANSLATION_VNV: PREVIOUS_VERIFIED_BOUNDED
WEAK_DIRECTION_RESOLUTION: UNRESOLVED
J2_ASSEMBLED_TANGENT_CONSISTENCY: BLOCKED_PENDING_INDEPENDENT_EVIDENCE
J2_TANGENT_SCIENTIFIC_GATE: NOT_APPROVED
INCREMENTAL_NEWTON_FEM: NOT_RUN
SCIENTIFIC_QUALIFICATION: NOT_ACQUIRED
WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET
```
