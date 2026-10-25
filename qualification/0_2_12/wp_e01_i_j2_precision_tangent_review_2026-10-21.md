# WP-E01-I — J2 high-precision oracle and tangent-gate review

**Date:** 2026-10-21
**Scope:** WP-E01-I source review and diagnostic preparation only.
**Status:** Prepared; the new module was not collected or executed.

## Repository and evidence identity

The dedicated worktree was `C:\wpc01-frictionless-public-integration-wt\wp-e01`, on branch `codex/qf-wp-e01-a-implementation-20261020`, with origin `https://github.com/emptiesvoid-cloud/QF_solver.git`. At entry, HEAD was `5eb0d381dc34e8037faf12b1a4ea784168decb90` and the worktree was clean. The 17 production-source hashes recorded by WP-E01-H matched the H execution manifest. The I execution package additionally pins 12 source dependencies used to construct and evaluate the prepared fixtures; all 29 declared source identities match. No production source was edited.

The frozen H report and evidence remain unchanged. H collected 20 cases and recorded **16 PASS / 4 FAIL**, with no skips, xfails, or xpasses. The four failed pytest nodes were the TET4 and HEX8 fixed-history tangent cases at `H=0` and `H=1.5e9 Pa`. At direction level, the report records two TET4 free-center global-window failures, two TET4 weak-direction local-window failures, and two HEX8 weak-direction local-window failures. The elastic TET4 and HEX8 tests passed their corrected analytical stress references and bounded assembly assertions. These are historical H results, not rerun here.

The H report SHA-256 is `741947C130DF21042DA8E0465732634465E25371CDB79BAA400CDF123DBE8E5B`. Original H test, safety registry, supervisor, collection guard and manifest identities are preserved in the H report and the new I manifest. The immutable H test identity remains `8FA46D1D2FF402C72E0D85851EB57307173FBA3D37A39567E3678608FE818296`.

Exact failed H nodes:

```text
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_residual_tangent_fixed_state_fd[TET4-0.0]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_residual_tangent_fixed_state_fd[TET4-1500000000.0]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_residual_tangent_fixed_state_fd[HEX8-0.0]
tests/unit/test_wp_e01e_global_assembly_vnv.py::test_j2_global_residual_tangent_fixed_state_fd[HEX8-1500000000.0]
```

These four node failures contain six failed directional conditions: both TET4 nodes fail the free-center global-window and weak local-window conditions; both HEX8 nodes fail the weak local-window condition.

## A — TET4 centered-difference window

For a sufficiently smooth vector force map `F(u)` and fixed direction `p`, Taylor expansion gives

\[
D_h = \frac{F(u+hp)-F(u-hp)}{2h}
    = J(u)p + \frac{h^2}{6}D^3F(u)[p,p,p]
      + \frac{h^4}{120}D^5F(u)[p,p,p,p,p] + O(h^6).
\]

Thus the leading centered-difference truncation error is proportional to `h²` while the branch and smoothness assumptions hold. H measured global errors for the TET4 free-center mixed direction:

| `h` | H=0 error | H=1.5e9 Pa error |
|---:|---:|---:|
| `3e-6` | `2.04e-7` | `2.02e-7` |
| `1e-6` | `2.26e-8` | `2.25e-8` |
| `3e-7` | `2.04e-9` | `2.02e-9` |

The error ratios are approximately 9 for a step ratio of 3, then approximately 11.1 for a step ratio of 10/3, matching the corresponding squared step ratios. This supports an O(h²) truncation-dominated trend on these points. Three measurements do not prove an asymptotic regime, and the ratio test alone does not establish the tangent.

The proposed H rule required every point in the final three-step window to satisfy the `1e-7` global error threshold. The coarsest point exceeds that threshold, while the two finer points are below it and errors continue decreasing by approximately h². The all-three rule therefore rejects a window containing a visibly truncation-dominated point. That is a limitation of the proposed window-selection rule; it is not evidence that the scientific threshold itself should be relaxed.

The H `K_ref=5.25e11 N/m`; each tested direction had norm approximately `1 m`. The full-window global errors and weak-action values were recorded as follows:

| Element / H (Pa) | Direction | `||Kp||` (N) | Global error at `h=(3e-6,1e-6,3e-7)` | Weak FD action norms at same `h` (N) |
|---|---|---:|---|---|
| TET4 / 0 | free-center mixed | `3.9573e11` | `(2.0357e-7, 2.2619e-8, 2.0358e-9)` | — |
| TET4 / `1.5e9` | free-center mixed | `3.9695e11` | `(2.0230e-7, 2.2477e-8, 2.0231e-9)` | — |
| TET4 / 0 | weak near-translation | `1.9900e-4` | `(6.0869e-14, 1.8236e-13, 6.0732e-13)` | `(0.031891, 0.095673, 0.318909)` |
| TET4 / `1.5e9` | weak near-translation | `1.7948e-4` | `(6.7223e-14, 2.0154e-13, 6.7154e-13)` | `(0.035259, 0.105778, 0.352593)` |
| HEX8 / 0 | weak near-translation | `6.7201e-5` | `(4.2155e-14, 8.3959e-14, 2.0451e-13)` | `(0.022100, 0.044078, 0.107360)` |
| HEX8 / `1.5e9` | weak near-translation | `6.9357e-5` | `(4.6078e-14, 9.2811e-14, 2.7664e-13)` | `(0.024159, 0.048714, 0.145212)` |

All six weak-direction local errors were about one under the candidate local comparison, despite global normalized errors near `1e-13`. The H report estimated `eps ||F_base||/h` at approximately `0.04–0.52 N`, comparable to or larger than those measured weak finite differences. The weak local metric is therefore unresolved by the binary64 subtraction in that step range; global normalization hides this fact. All base and perturbation branches were reported smooth plastic; the minimum recorded positive yield margin was approximately `200.154 MPa`, and the accepted-state digest was unchanged.

**Candidate alternative, not approved:** retain all branch-preserving measurements, form a Richardson estimate for each adjacent pair,

\[
D_R(h;r)=\frac{r^2D_{h/r}-D_h}{r^2-1},
\]

and report the estimated truncation term separately from the derivative error. Require agreement of successive Richardson estimates only over a range where the branch is unchanged and the signal is numerically resolved. Do not select a step solely because it gives a favorable error. Keep the H `1e-7` tangent threshold and all other existing candidate limits unchanged until Owner review; no revised gate is activated here.

## B — Historical weak direction and rigid translation

H defines its weak vector as a uniform x-translation plus `1e-15` times a mixed vector, followed by normalization. It is therefore **approximately translational, not an exact rigid translation**. The H mesh constrains every node except the center node. The weak vector contains nonzero components on prescribed DOFs, so it is also **not an admissible reduced Newton direction**. H evaluated this vector as a full-space diagnostic. Its local near-null finite-difference values must not be interpreted as a constrained Newton tangent result.

For an unconstrained internal elastic/small-strain constitutive operator, a rigid translation `t` applied equally to all nodes leaves every displacement gradient and strain unchanged. With the same accepted J2 history, this implies `F_int(u+t)=F_int(u)` and, for the smooth fixed-history tangent, `K_int t=0` up to floating-point evaluation error. To test this invariant under the current fixture's prescribed-displacement boundary data, translate the prescribed nodes as well as free nodes for this **raw internal-operator control**. Do not include external loads, contact, constraints, or reactions in that raw invariant comparison. A separate constrained check must instead set constrained direction components to zero and must not call that vector a rigid translation.

The prepared control uses an exact binary-fraction uniform translation on all nodes. It fixes the accepted plastic state, checks the trial branch identities, compares raw internal forces and the tangent action, and independently checks the tensor/quadrature force in Decimal arithmetic. The binary64 comparison uses a proposed scale tied to force magnitude and `K_ref ||t||`; it does not demand bitwise zero. The Decimal comparison uses a proposed relative arithmetic bound. Both bounds remain diagnostic proposals and require Owner review before becoming acceptance criteria.

The exact tests deliberately report separately that prescribed DOFs were translated and that no external/contact terms were included. They do not claim a reduced equilibrium mode or integrated FEM objectivity.

## C — Prepared fixed-history Decimal oracle

`tests/unit/test_wp_e01i_j2_precision_diagnostics.py` contains a separate, standard-library Decimal implementation of the fixed-history force derivative for the H TET4/HEX8 mesh. Its arithmetic is set to 80 decimal digits. It reconstructs each stored binary64 model input, direction, material parameter, and accepted-state component with `Decimal.from_float`, then forms `u ± h p` and computes strain, stress, force integration, and nodal scatter in Decimal. It does not convert already-rounded production force vectors to Decimal and call those high precision.

The oracle independently derives TET4 reference gradients and the HEX8 2×2×2 Gauss gradients, computes small-strain tensor elasticity and associated J2 radial return, converts the accepted engineering-shear plastic strain state into a symmetric tensor, integrates stress against reference gradients, and scatter-adds nodal forces. It compares those force derivatives to both the production binary64 tangent action and a high-precision dot product of the exact binary64 tangent entries and direction. The latter distinguishes tangent-matrix multiplication roundoff from force-difference behavior.

The incoming accepted state is fixed for every plus/minus evaluation. The prepared diagnostic checks each Decimal base/plus/minus branch against the base branch, records minimum yield margin, and confirms the production accepted-state digest is unchanged. `H=0` and `H=1.5e9 Pa` remain separate cases. The new test reports both global and selected-row actions; the TET4 free-center case uses free rows, while weak full-space directions report all rows.

This is an independent **fixed-history derivative** oracle, not an independent history-evolution oracle. The accepted history is obtained by the existing production preload call and then held fixed; material constants and the mesh are inputs to both paths. The independent force evaluator does not call the production J2 stress routine, element force routine, quadrature routine, or global scatter routine. It does consume the model's already parsed node and connectivity data. The prepared suite does not compare every isolated element's local tangent in a separate Decimal test, so a future discrepancy still needs localization between local production tangent and global scatter. Historical D4R element evidence remains separate evidence for its own exact source identity.

The Decimal input reconstruction preserves the exact binary64 inputs rather than reconstructing intended decimal literals. It cannot restore precision already lost before those binary64 model inputs or accepted history were created. The oracle has not been executed; no high-precision numerical result is claimed.

## D — Candidate direction gate

The following is a proposed diagnostic contract only. All new limits remain **PROPOSED** and are not Owner-approved.

1. **Direction identity and domain:** record element/global direction identity, norm, constrained DOFs, row projection, fixed accepted history, material branch at base and both perturbation sides, and minimum yield margin. A constrained tangent test must use a direction with zero prescribed-DOF components. A raw rigid-translation control is a separate full-space invariant.
2. **Absolute/global error:** report `e_abs(h)=||Kp-D_h||₂` in N and a dimensionless global error using a predeclared `K_ref ||p||₂` force scale. Also report the raw reference and action norms; the global normalization alone cannot establish accuracy of a weak local response.
3. **Direction-local error:** evaluate a local relative error only when `||D_h||` is above a declared, step-dependent numerical-resolution bound. Otherwise mark the local metric `NOT_EVALUABLE`; do not treat noise exceeding a fixed stiffness-only null floor as evidence of eligibility.
4. **Step convergence:** retain the complete step sweep. Estimate centered-difference truncation by Richardson pairs, and assess plateau only among branch-preserving, resolved estimates. For binary64 force differences, include a cancellation estimate proportional to machine precision times the force scale divided by `h`. For the Decimal oracle, separately report the precision-controlled sweep. No threshold is selected by this report.
5. **Branch handling:** smooth-branch central differences require unchanged per-point branch identity and a recorded margin. Near a yield switch, do not use a centered derivative across the switch; report one-sided branch derivatives separately or classify the case as `NOT_EVALUABLE` for a smooth-branch gate.
6. **Independent agreement:** compare production matrix action, independently integrated fixed-history force derivative, and any production-force finite difference as three separately named quantities. They must represent the same fixed state, row projection, displacement direction, and load convention.
7. **Failure meaning:** distinguish `TANGENT_MISMATCH`, `TRUNCATION_DOMINATED`, `ROUND_OFF_LIMITED`, `BRANCH_CROSSING`, and `NOT_EVALUABLE`. A not-evaluable local direction is neither a tangent PASS nor a production FAIL.

The test records diagnostic quantities and does not contain a new tangent acceptance assertion. In particular, neither `1e-7`, `1e-5`, `1e-6`, the proposed `1024 ε` translation factor, nor the proposed Decimal translation bound is frozen by WP-E01-I.

## E — Prepared executable diagnostics and safety

| Artifact | Purpose / static inventory | Classification / execution state |
|---|---|---|
| `tests/unit/test_wp_e01i_j2_precision_diagnostics.py` | 3 test functions; 12 statically enumerated parameter cases: 6 fixed-history derivative cases, 4 exact-translation controls, 2 historical-vector controls | `NUMERICAL_UNIT`, hash-bound; **not collected or run** |
| `experiments/wp_e01i_collection_guard.py` | Binds exact test and registry hashes, exact 12 node IDs, functions, fixtures and marker; writes a guarded collection record under isolated `TMP` and revalidates it before test bodies | Static review only; **not run** |
| `experiments/wp_e01i_j2_diagnostic_supervisor.py` | Fixed target/no CLI args; reviewed Windows Job Object helper; one suspended shell-free pytest child; one process; 256 MiB per-process and job committed-memory limits; 120-second parent deadline; kill-on-close; one BLAS thread; no retry | Static configuration only; **not runtime verified or launched** |
| `qualification/0_2_12/wp_e01_i_execution_manifest_2026-10-21.json` | Frozen exact-path identities, node inventory, source identities, resource settings, historical evidence, and non-authorization status | Prepared; **grants no execution permission** |

The module imports `decimal`, `itertools`, NumPy, pytest, `GlobalAssembler`, nonlinear assembly helpers, `FiniteElementModel`, and material-state initialization/digest helpers. Source review found no public solve, `solve_model`, native FEM, Gmsh initialization, worker, subprocess, network, or checkpoint write reachable from the test bodies. The fixed supervisor disables pytest plugin autoload, clears pytest `addopts`, supplies only the fixed collection guard, constrains inherited environment, and uses a one-child Job Object. The reviewed Job Object source can set/query committed-memory limits, active-process limit, kill-on-close, and disallow breakaway. This is source evidence only: limits and cleanup have **not** been verified at runtime.

The collection guard's 12 entries are a static inventory, not an observed collection. No `pytest --collect-only`, pytest invocation, numerical probe, native import probe, or model solve was performed. The only checks in this mandate are source inspection, hash computation, JSON/source review, and static Python AST parsing / diff checks.

## Independent read-only review

`<reviewer-workspace>` separately reviewed the H evidence and the prepared I test, guard, supervisor, and manifest. It agreed the exact-translation test is correctly scoped as a raw internal-operator control, the Decimal oracle is independently formulated for fixed accepted history, and no production defect is demonstrated by H. The reviewer identified and blocked the initial stale supervisor test hash; that pin was reconciled. The reviewer also identified derivative and `Kp` unit labels that incorrectly said N/m; all action/error labels now say N, while `K_reference` remains N/m and is multiplied by the displacement-direction norm. A final read-only confirmation found the registry, guard, supervisor, manifest and test hashes consistent. No reviewer executed or collected tests.

## Exact prepared identities

| File | SHA-256 |
|---|---|
| `tests/unit/test_wp_e01i_j2_precision_diagnostics.py` | `59DBAF1F84E518C2F10FC573ED973EE22187399671B7045F22C3F73B349F4C95` |
| `tests/conftest.py` | `A3220FD8716FC86E316EF0577E7E3E8DB789C850B0201E63EEF1ED2CD28F0618` |
| `experiments/wp_e01i_collection_guard.py` | `722D30D59C710D93DAD82150C40DBF6EB6FF2CCCBCF6BB27179A3D3F24F718B4` |
| `experiments/wp_e01i_j2_diagnostic_supervisor.py` | `74A6043726702CEF1AEC888FC40D5BE57B1487DE2DFF4B7FAC15193C56EB450C` |
| `qualification/0_2_12/wp_e01_i_execution_manifest_2026-10-21.json` | `9884A3846B2D8929371DABC1E6A7D7E1BB489CCB094D62FDCADE3D193133141C` |
| Frozen H report | `741947C130DF21042DA8E0465732634465E25371CDB79BAA400CDF123DBE8E5B` |
| H execution manifest | `0F609B4B51AE81A8FD2F2BD4233510D9002AD0A46404279D6532D19AE8E31E91` |
| Reviewed shared Job Object supervisor | `9BD8C75B19B49C758F9558CF9299EEEDC18762B1E40DBD69968377A94D6C9090` |

The I manifest additionally binds these source dependencies (all values were checked against the worktree after the I preparation changes):

| Source | SHA-256 |
|---|---|
| `src/solveur/materials/solid.py` | `7D8223C81999D037900C26BF1A6A2ABC9F4B47C0CFF597F4BE0CF0163E8092AA` |
| `src/solveur/materials/factory.py` | `63F06024111085FB87F68A4B5CFD5EADD10C4D6253D7E02761CCE19D88FBC275` |
| `src/solveur/core/model.py` | `15DD9C88BFA68E33863DA3027C10E73369E8AB892D584E40D1601C7E0A5448FF` |
| `src/solveur/core/dofs.py` | `62B1A414B2FE9E816C8373B8A0193A5F5ABFF1BFF54BFABE3289FDA52FABA114` |
| `src/solveur/core/assembly/plan.py` | `DD7B468645AB713A172D0DD067182D17625C4B24F3D7856842336E9B97B7677F` |
| `src/solveur/core/assembly/sparse.py` | `5999F94A132DC762D8F92DFC3A5DD27815426D4FEC0CEB04DF2BBF4199CD4B96` |
| `src/solveur/core/nonlinear/material_state.py` | `6439F50398A8A914123ABD804752C018D879FAD909F437F075267373916B7DFA` |
| `src/solveur/core/nonlinear/contracts.py` | `FAEA669E31A85988071E64D930246769212F5745ED5E09E8ECC07B7200363809` |
| `src/solveur/elements/registry.py` | `AD055AD1FE624B5B780D81A161323378A4E26C1FE07F46E99A7281494D55EEF8` |
| `src/solveur/elements/solid/common.py` | `ED5EF8CDEF23B001F1D0FE1DF7ECB603180512D70DBA46D502B860B3A3D30379` |
| `src/solveur/core/analyses/settings.py` | `8E654EC276669829911A79DD477F595C830396E522010DDF67C1F7A5636FBB76` |
| `src/solveur/core/constraints.py` | `63F89595AE0DD035B31CE5CDB7A621D52F8DBBA9D0AC934A0090BBB955936E14` |

All new tangent and translation thresholds remain proposed. No E01 production implementation, test result, J2 tangent freeze, Newton/Armijo certificate, FEM qualification, merge, or release is claimed.

## Required statuses

| Status | Result |
|---|---|
| `ELASTIC_PATCH_VNV` | `PREVIOUS_PASS_BOUNDED` |
| `STVK_GLOBAL_TANGENT` | `PREVIOUS_PASS_BOUNDED` |
| `J2_TANGENT_VNV` | `FOUR_PREVIOUS_FAIL` |
| `J2_HIGH_PRECISION_ORACLE` | `PREPARED_NOT_RUN` |
| `RIGID_TRANSLATION_VNV` | `PREPARED_NOT_RUN` |
| `REVISED_TANGENT_GATE` | `PROPOSED_NOT_APPROVED` |
| `GLOBAL_ASSEMBLY_VNV` | `PARTIAL` |
| `INCREMENTAL_NEWTON_FEM` | `NOT_RUN` |
| `PRODUCTION_ARMIJO_CERTIFICATE` | `NOT_VERIFIED` |
| `NATIVE_FEM_VNV` | `NOT_RUN` |
| `SCIENTIFIC_QUALIFICATION` | `NOT_ACQUIRED` |
| `WP_E01_STATUS` | `OPEN / EXPERIMENTAL_TARGET` |

## Exact next Owner decision

Authorize one supervised, exact-path execution of the prepared I diagnostic package, bound to the final WP-E01-I commit and the manifest SHA-256. The fixed parent command is:

```text
C:/Python313/python.exe -m experiments.wp_e01i_j2_diagnostic_supervisor
```

That parent launches one guarded pytest process for the one registered 12-case module. Its collection guard validates the exact node set before the test loop. The execution limits remain the configured 256 MiB process and Job Object committed-memory caps, 120-second parent deadline, one child process, one BLAS thread, kill-on-close cleanup, and no retry. This recommendation is a request for a separate Owner GO; this report and manifest do not authorize collection or execution. The next run should report the full Decimal step sweep, branch margins, raw translation residual/action, state digests, runtime resource enforcement, and all `NOT_EVALUABLE` conditions without changing any threshold.
