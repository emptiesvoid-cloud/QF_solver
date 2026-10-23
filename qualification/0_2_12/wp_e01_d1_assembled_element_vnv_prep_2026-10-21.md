# WP-E01-D1 — Assembled TET4/HEX8 residual and tangent V&V preparation

**Date:** 2026-10-21<br>
**Repository:** `C:\wpc01-frictionless-public-integration-wt\wp-e01`<br>
**Branch/base:** `codex/qf-wp-e01-a-implementation-20261020` at `28c360ee075af2e2548add4e6a90681aaebac13f`<br>
**Scope:** source review, isolated test preparation and static safety review only. No solver/test/FEM execution occurred.

## 1. Disposition

The existing TET4 and HEX8 small-strain J2 and Total-Lagrangian StVK kernels were reviewed. One hash-bound direct-element test module was prepared. It covers an independent force reference, full assembled tangent finite differences, material/geometric stiffness decomposition, fixed-state J2 branch checks, local history continuity, rollback and the in-memory E01-A accepted-state identity helper.

The worktree's historical evidence is preserved as historical: B6 residual/Jacobian 10/10 and C1 finite-strain material-point 17/17. Neither was rerun. This turn ran no pytest, numerical test, FEM solve, Gmsh, public API route, worker or subprocess. No production source or public API was modified. The test module does not exercise the public nonlinear solver or a native FEM backend.

## 2. Formulation and assembled residual contract

### Small-strain J2

For node-major element displacement `u_e`, reference quadrature point `g`, and accepted material history `z_n,g`:

```text
epsilon_g = B_g u_e
(sigma_g, z_trial,g, C_alg,g) = J2(epsilon_g; z_n,g)
f_int,e = sum_g w_g det(J_0,g) B_g^T sigma_g
K_int,e = sum_g w_g det(J_0,g) B_g^T C_alg,g B_g
```

The six strain entries are engineering-Voigt `[xx, yy, zz, gamma_xy, gamma_yz, gamma_xz]`; stress shear entries are tensorial. The returned element tangent is the derivative candidate for **internal force**, `df_int/du = K_int`. For a proportional dead nodal load, `R_f = (lambda f_ext - f_int)_f` on free DOFs and `dR_f/du_f = -K_int,ff`; constrained reactions are excluded. Follower loads need an external-force tangent and are outside the prepared fixtures.

`Tet4Element` has 12 DOFs, affine reference gradients, one constant-strain point, and signed `V_0 = det(J_0)/6`. It evaluates one constitutive response and returns one trial state. Its valid-reference volume guard is `V_0 > 1e-14` in the current code.

`Hex8Element` has 24 DOFs, trilinear shape functions, eight full-integration Gauss points at each natural coordinate `+/-1/sqrt(3)` with unit weights, `J_0 = dN/dxi @ X`, and `grad_X N = dN/dxi @ inv(J_0).T`. Its current geometry guard requires each sampled `det(J_0)` to exceed `1e-14 * max(span, 1)^3`. Each point contributes its own `B_g^T sigma_g` and `B_g^T C_alg,g B_g` term.

Both element methods return a symmetrized tangent. This is the API result compared with the independent force derivative; the pre-symmetrized matrix is not exposed by these methods.

### Total-Lagrangian StVK

The two batch routes use reference nodes and reference gradients. At each point:

```text
F = I + Grad_X(u)
C = F^T F
E = 0.5 (C - I)                       # Green-Lagrange strain
J = det(F)
W = 0.5 lambda (tr(E))^2 + mu (E:E) # per reference volume
S = lambda tr(E) I + 2 mu E           # PK2, reference frame
P = F S                               # full PK1, current/reference indices
sigma = J^-1 P F^T                    # Cauchy, current frame
```

With reference quadrature measure `dV_0 = w_g det(J_0,g)`,

```text
f_int,ai = sum_g dV_0 P_iJ N_a,J
A_iJkL = dP_iJ/dF_kL
        = F_iA C_AJBL F_kB + delta_ik S_LJ
K_abik = sum_g dV_0 N_a,J A_iJkL N_b,L
        = K_material + K_geometric
```

The geometric term is `delta_ik * integral(N_a,J S_LJ N_b,L dV_0)`; the material term is the `F C F` contraction. `TotalLagrangianTet4Assembly` uses 12 DOFs and one constant-gradient point. `TotalLagrangianHex8Assembly` uses 24 DOFs and eight `2x2x2` points. Both assemble the internal force in the reference configuration and return a symmetrized stiffness. Current guards reject TET4 reference volume `<=1e-14`, HEX8 invalid sampled reference Jacobians, and current `det(F) <= 1e-10`. These are code guards, not Owner-approved physical admissibility limits.

The element tests impose no global boundary conditions. In a later solver study, prescribed displacement DOFs must be eliminated/reconstructed, reactions omitted from the free residual, and the load tangent included for any displacement-dependent external force. The prepared sign test uses a constant dead nodal force only.

## 3. Independent references and candidate J2 gate

The test module constructs TET4 shape gradients by solving the affine interpolation equations and differentiates HEX8 trilinear shape functions directly at the independent Gauss-point list. Its StVK oracle evaluates the closed-form energy, `S`, `P`, internal force, and separate material/geometric tangent contractions without calling either batch assembly. The direct TET4 TL kernel is also compared as a second implementation path; it is corroborating evidence, not the sole oracle.

The J2 force oracle converts engineering strain to a tensor, computes isotropic trial stress and `q = sqrt(3/2 s:s)`, performs the closed-form radial return, and integrates independently reconstructed `B` matrices. It does not call `VonMisesElastoplasticMaterial`. The derivative reference does call the element internal-force method at `u +/- h p`, but every call receives a fresh copy of the same accepted incoming Gauss-point state. This isolates the displacement derivative from state accumulation. The tests include virgin and preloaded history, perfect plasticity and linear isotropic hardening, mixed and deviatoric-shear directions, translation null directions, and a full nodal-DOF Jacobian reconstruction. Perturbed states must preserve the independently calculated plastic trial branch. Loading, unloading and reverse re-yield are separate from the smooth-branch derivative gate; no centered difference crosses yield.

Recommended assembled J2 gate for Owner review, **all values PROPOSED and unfrozen**:

| Quantity | Candidate definition | Units / status |
|---|---|---|
| Absolute matrix error | `e_abs = ||K_int - D_h f_int||_F` | N/m; report for every step size. Candidate scale bound: `e_abs <= 1e-7 K_ref sqrt(n_dof)`. |
| Global stiffness scale | `K_ref = max(3K, 2mu) V_0 / L^2` | N/m; `V_0` is reference element volume and `L` its characteristic length. |
| Global normalized error | `rho_G = e_abs / max(||D_h f_int||_F, K_ref sqrt(n_dof))` | Dimensionless; candidate `rho_G <= 1e-7`. |
| Direction-local error | `e_p = ||K_int p - D_h f_int[p]||_2`; `rho_p = e_p / max(||D_h f_int[p]||_2, 64 eps K_ref ||p||_2)` | `e_p`: N/m for unit-norm displacement-coordinate direction; candidate `rho_p <= 1e-5` for non-null mixed/weak directions. Exact rigid modes use absolute/global errors only. |
| Perturbation sweep | `h/L = 1e-4, 3e-5, 1e-5, 3e-6, 1e-6, 3e-7` | Dimensionless displacement step. Keep plus/minus states on the same smooth constitutive branch and inside admissibility. |
| Plateau | At least three adjacent geometric steps with `rho_G <= 1e-7` and spread `max(rho)-min(rho) <= 0.5e-7` | Proposed numerical gate; also report local errors and absolute errors. |

The `1e-7` global/absolute candidate differs from the prior material-point `1e-8` candidate; neither is Owner-frozen. The element module encodes these as `PROPOSED_*` constants for a future review run. It does not change or promote `J2_TANGENT_CONSISTENCY`, which remains `BLOCKED_PENDING_INDEPENDENT_EVIDENCE`. A passing exact-path unit run would still be bounded to these element kernels and would not validate a production Armijo certificate or qualify FEM.

## 4. Prepared test inventory — NOT RUN

Exact module: `tests/unit/test_wp_e01d1_element_vnv.py`<br>
Static inventory: 15 test functions, 43 parameter-expanded cases. TET4 and HEX8 are distinct parameter IDs. The following are source inventory counts, not a pytest collection result.

| Test ID / function | Cases | Fixture coverage |
|---|---:|---|
| `test_zero_displacement_has_zero_internal_force_and_valid_tangent` | 4 | TET4/HEX8 x J2/TL-StVK, zero load/displacement, finite tangent. |
| `test_small_strain_limit_matches_independent_linear_element_force` | 4 | TET4/HEX8 x J2/TL-StVK; small affine strain against independent linear-elastic force. |
| `test_stvk_homogeneous_finite_deformation_matches_independent_force_and_energy` | 2 | TET4/HEX8 affine finite deformation, force/energy, resultant and moment balance; TET4 direct-kernel cross-check. |
| `test_stvk_rigid_rotation_is_energy_free` | 2 | TET4/HEX8 proper rigid rotation and objectivity. |
| `test_stvk_force_covaries_under_superposed_rotation_and_stretch` | 2 | TET4/HEX8 force covariance under a superposed rotation. |
| `test_stvk_assembled_tangent_matches_independent_split_and_force_derivative` | 2 | TET4/HEX8 full matrix and directional FD; independent material/geometric split. |
| `test_invalid_reference_and_inverted_current_geometries_are_refused` | 2 | TET4/HEX8 invalid reference orientation and nonpositive current `J`. |
| `test_j2_assembled_internal_force_matches_independent_tensor_gauss_reference` | 4 | TET4/HEX8 x perfect plasticity/linear isotropic hardening. |
| `test_each_integration_point_uses_its_own_accepted_j2_history` | 2 | TET4/HEX8 with distinct accepted integration-point histories. |
| `test_j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps` | 8 | TET4/HEX8 x `H=0`/`H=1.5 GPa` x virgin/preloaded; mixed, deviatoric-shear, translation-null and all-DOF FD. |
| `test_j2_unloading_and_reverse_reyield_follow_fixed_accepted_history` | 4 | TET4/HEX8 x perfect/hardening unloading and reverse re-yield. |
| `test_dead_load_residual_derivative_is_negative_internal_force_tangent` | 2 | TET4/HEX8; verifies `D R = -K_int` for a constant dead load. |
| `test_accepted_element_history_advances_only_when_trial_states_are_accepted` | 2 | TET4/HEX8; synthetic local increments with explicit fixture commit. |
| `test_discarded_j2_trial_cannot_contaminate_next_accepted_element_update` | 2 | TET4/HEX8; discard trial, then update from unchanged accepted state. |
| `test_composite_state_rollback_commit_and_accepted_identity_are_deterministic` | 1 | In-memory transaction rollback/commit and E01-A accepted identity helper. No serialized checkpoint or restart is exercised. |
| **Total** | **43** | Direct element kernels and in-memory state only. |

The independent references share the approved kinematics, tensor equations, material parameters, and the specified nodal order with the implementation; they do not call the same assembly routines. Hex8 reference quadrature is independently enumerated and differentiated. The finite-difference residual uses the implementation's force evaluator by design, while its derivative is independent. The test report must preserve absolute errors in N, J, N/m, or N·m as applicable, normalized global errors, and local directional errors; this preparation has no numerical error results.

## 5. State, checkpoint and compatibility limits

The local J2 tests supply one accepted state to TET4 and eight to HEX8. They verify fixed-state trial evaluation, local explicit acceptance, and in-memory rollback/identity. They do **not** verify a load-control driver, serialized WP10 v2 checkpoint, abrupt interruption, filesystem durability, or actual restart. Prior E01-A checkpoint evidence remains historical and is not reused as new element-level evidence.

Static source review found that `Hex8Element.internal_force_tangent_state` uses `None` for any missing state entries instead of rejecting an undersized state list; `Tet4Element` similarly treats an empty list as no prior state and ignores extra entries. The standard state-table path is expected to construct the integration-point count, but the direct element methods do not enforce that invariant. A short/misordered state vector can therefore restart a point from virgin history. This is a P1 integration blocker for untrusted state inputs; it was not changed here. The exact-path tests use complete, ordered states and do not conceal this finding.

## 6. Safety and proposed execution GO

The new module is hash-bound in `tests/conftest.py` as `NUMERICAL_UNIT`. Its imports are limited to NumPy, pytest, SciPy sparse for the existing TL batch classes, the direct TET4/HEX8 kernels, material definitions, and in-memory nonlinear state/identity helpers. Static import-closure inspection found no `gmsh`, `ctypes`, native solver, `solve_model`, public analysis router, worker, process-launch API, or subprocess path. The module is not in `OPTIONAL_MESH_TEST_MODULES`, so collection does not invoke the Gmsh capability probe. The SciPy sparse import is a numerical-library dependency, not a FEM backend. No registry guard or classification logic was weakened.

Proposed future command, requiring a separate exact-path Owner GO:

```powershell
python -m pytest -q tests/unit/test_wp_e01d1_element_vnv.py
```

Prepared bound: one module/process, no children, no public solver, no Gmsh, no backend; <=256 MiB and <=120 seconds. Expected static case inventory: 43. Because no collection was run, the actual collected count and runtime remain unverified. A later GO must first verify the exact test and registry hashes and review collection imports; any inventory/hash mismatch stops execution.

## 7. Neo-Hookean boundary

Neo-Hookean remains material-point-only. A later minimal integration change proposal should add a distinct finite-strain `evaluate(F)` response carrying `W`, `S`, full `P`, Cauchy stress and consistent tangents; an opt-in geometric assembly adapter; explicit material/factory validation and case-declared `J` domain; and point-located result metadata. It must preserve StVK defaults and keep the Cauchy/PK2 symmetric fields distinct from nine-component PK1. This requires Owner approval before editing protected assembly/analysis/material/result/checkpoint paths. It is not finite-strain J2 plasticity and is not included in these tests.

## 8. Independent read-only review findings

This was a second read-only pass by the primary agent, not an independent reviewer.

* **P0:** none found in the inspected test/import paths.
* **P1:** direct TET4/HEX8 APIs do not fail closed on incomplete or extra J2 state vectors; require complete integration-point identity/count before broad stateful integration.
* **P1:** the element APIs return symmetrized tangents, hiding the raw pre-symmetrization derivative. The prepared comparison can test the returned matrix against FD, but cannot independently inspect raw skew before symmetrization.
* **P2:** TET4/HEX8 `det(J_0)` and `det(F)` thresholds are implementation guards, not approved material-domain limits; the scale floor in HEX8 reference geometry is unit-sensitive.
* **P2:** current element-local tests do not cover prescribed-DOF reduction, reactions, follower loads, WP10 v2 restart, crash durability, production Newton, or Armijo route certification.

## 9. Final status

```text
ELEMENT_RESIDUAL_TANGENT_CONTRACT: REVIEWED / INCOMPLETE
TET4_J2_VNV: PREPARED_NOT_RUN
HEX8_J2_VNV: PREPARED_NOT_RUN
TET4_TL_STVK_VNV: PREPARED_NOT_RUN
HEX8_TL_STVK_VNV: PREPARED_NOT_RUN
ELEMENT_DERIVATIVE_ORACLES: PREPARED / INCOMPLETE
J2_TANGENT_GATE: REVISED_CANDIDATE_FOR_OWNER_REVIEW / INCOMPLETE
J2_TANGENT_CONSISTENCY: BLOCKED_PENDING_INDEPENDENT_EVIDENCE
NEO_HOOKEAN_INTEGRATION: NOT_AUTHORIZED
NATIVE_FEM_VNV: NOT_RUN
ARMIJO_PRODUCTION_CERTIFICATE: NOT_VERIFIED
SCIENTIFIC_QUALIFICATION: NOT_ACQUIRED
WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET
```

## Appendix A — hashes

The test hash is the digest bound by the exact `NUMERICAL_UNIT` registry entry. Source hashes identify reviewed files; they do not represent test evidence.

| File | SHA-256 |
|---|---|
| `tests/unit/test_wp_e01d1_element_vnv.py` | `42E1D349C6DA4CA95BC60CA09E2839EF3989C172ED453FF2CA8DF41BF965164C` |
| `tests/conftest.py` | `F9A68BEB4F0D2D1802ACBF8630AAF46E1E7686D6173C8F9FA3938BA2F69D818C` |
| `src/solveur/elements/solid/tet4.py` | `0517683946A0292E2224D77BA197229EBDBC91DCF935B57D9B75E728D9BE3D0B` |
| `src/solveur/elements/solid/hex8.py` | `4DD8BA606B7E8CAB9697FD26CE0BAF37FBAF046F9E95894AFB0AC8EAA0C85D7A` |
| `src/solveur/elements/solid/tet4_total_lagrangian_batch.py` | `CC7FA09C23778312B2EC8AED54208041A5E0E9EEBA0AD7F983672D6522BBEBCA` |
| `src/solveur/elements/solid/hex8_total_lagrangian_batch.py` | `D6E524B2233A84702974518A1F2136C0BEF00BC744F120041150EAE78BBF1BF5` |
| `src/solveur/materials/solid.py` | `7D8223C81999D037900C26BF1A6A2ABC9F4B47C0CFF597F4BE0CF0163E8092AA` |
| `src/solveur/core/nonlinear/state.py` | `977330C88438174BA29E826825B120A1135A8A04D6046E2B134DCA08AB3E3BF2` |
| `src/solveur/core/nonlinear/e01a.py` | `C0DC0EBFB56FC2DA52AFCA89550ADC922E2A52ED04C0B53A2F4A9022CC7BC139` |
| `tests/unit/test_wp_e01b_b6_residual_jacobian.py` | `2BC4CB5EF8AC4FB08DC78868EEEB90641CDF6D7B2C9A75B3BCCB8490762C09FF` |
| `tests/unit/test_wp_e01c_finite_strain_material.py` | `F64A3F9B2E296A2366A977A782C27635AB2E6868F2C44D55A84560D9A59399F9` |
| `qualification/0_2_12/wp_e01_de_fem_integration_review_2026-10-20.md` | `FF38E474C3937C47BC4AA4D618C3E9B8C4F2A4279193259D58C19133BC419FE0` |
