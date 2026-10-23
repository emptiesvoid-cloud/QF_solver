# WP-E01-D2 — TET4/HEX8 element-level V&V results

**Date:** 2026-10-21<br>
**Repository:** `C:\wpc01-frictionless-public-integration-wt\wp-e01`<br>
**Branch:** `codex/qf-wp-e01-a-implementation-20261020`<br>
**Baseline:** `395e35d5c86621f101cb3eebb7ed60318947253a`<br>
**Scope:** exact-path element algebra only. No native FEM, public solve, Gmsh, worker, or subprocess execution.

## 1. Executive result

The final exact-path run collected 47 cases and reported **43 passed, 4 xfailed, 0 skipped**. The four xfails are intentional fail-closed probes for the known TET4/HEX8 J2 state-vector length defect. All element force, StVK, and correctly sized J2 state/tangent checks passed on the bounded one-element fixtures.

The initial, unmodified run collected 43 cases and reported **35 passed, 8 failed**. All eight failures came from a J2 full-matrix finite-difference plateau assertion using only three coarse steps. The measured error decreased approximately quadratically with step size; the third error was already below the proposed global threshold, but the assertion required a three-point passing plateau. The test sweep omitted the three finer steps already declared for the directional oracle. The test was corrected to use that existing six-step range; no scientific threshold or production implementation was changed.

These are bounded direct-element results. They do not close `J2_TANGENT_CONSISTENCY`, qualify a production nonlinear route, or verify global boundary-condition, checkpoint, or native FEM behavior.

## 2. Baseline and execution chronology

Preflight confirmed repository origin `https://github.com/emptiesvoid-cloud/QF_solver.git`, the requested worktree and branch, clean baseline HEAD, and the original test and registry hashes. The exact reviewed test was registered as `NUMERICAL_UNIT`. Its import closure comprises NumPy, pytest, SciPy sparse support, direct element/material classes, and in-memory state helpers. The selected module is not in `OPTIONAL_MESH_TEST_MODULES`; collection therefore does not call the Gmsh probe. Static inspection found no public solver call, `solve_model`, FEM backend, Gmsh initialization, worker, child process, or test-body file write.

The only element dimensions are 12 DOFs/one material point for TET4 and 24 DOFs/eight Gauss points for HEX8. Numerical-library thread counts were limited to one. Collection and final execution disabled pytest cache and Python bytecode writes. No tracked file other than the test module and its safety-registry digest changed during verification.

| Cycle | Command and scope | Result |
|---|---|---|
| Preflight | `python -m pytest --collect-only -q -p no:cacheprovider tests/unit/test_wp_e01d1_element_vnv.py` | 43 cases collected in 1.03 s; matched the original static inventory. |
| 1 — initial execution | `python -m pytest -q -s tests/unit/test_wp_e01d1_element_vnv.py` | 35 passed, 8 failed in 6.21 s (8.21 s shell wall time). Failures were the eight J2 full-matrix plateau assertions listed below. |
| 2 — focused remediation | Same exact module command, after extending the matrix sweep to the already declared six steps and adding raw-skew/state-length diagnostics | 43 passed, 4 xfailed in 9.69 s (11.57 s shell wall time). |
| 3 — final authorized run | Same exact module command after correcting the StVK diagnostic step label | 43 passed, 4 xfailed in 9.79 s (11.66 s shell wall time). |

The initial eight failing node IDs were:

* `test_j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps[virgin-perfect-tet4]`
* `test_j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps[virgin-perfect-hex8]`
* `test_j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps[virgin-isotropic_hardening-tet4]`
* `test_j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps[virgin-isotropic_hardening-hex8]`
* `test_j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps[preloaded-perfect-tet4]`
* `test_j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps[preloaded-perfect-hex8]`
* `test_j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps[preloaded-isotropic_hardening-tet4]`
* `test_j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps[preloaded-isotropic_hardening-hex8]`

The final 47 collected node IDs share the prefix `tests/unit/test_wp_e01d1_element_vnv.py::`; the suffixes were:

```text
test_zero_displacement_has_zero_internal_force_and_valid_tangent[j2-tet4]
test_zero_displacement_has_zero_internal_force_and_valid_tangent[j2-hex8]
test_zero_displacement_has_zero_internal_force_and_valid_tangent[tl_stvk-tet4]
test_zero_displacement_has_zero_internal_force_and_valid_tangent[tl_stvk-hex8]
test_small_strain_limit_matches_independent_linear_element_force[j2-tet4]
test_small_strain_limit_matches_independent_linear_element_force[j2-hex8]
test_small_strain_limit_matches_independent_linear_element_force[tl_stvk-tet4]
test_small_strain_limit_matches_independent_linear_element_force[tl_stvk-hex8]
test_stvk_homogeneous_finite_deformation_matches_independent_force_and_energy[tet4]
test_stvk_homogeneous_finite_deformation_matches_independent_force_and_energy[hex8]
test_stvk_rigid_rotation_is_energy_free[tet4]
test_stvk_rigid_rotation_is_energy_free[hex8]
test_stvk_force_covaries_under_superposed_rotation_and_stretch[tet4]
test_stvk_force_covaries_under_superposed_rotation_and_stretch[hex8]
test_stvk_assembled_tangent_matches_independent_split_and_force_derivative[tet4]
test_stvk_assembled_tangent_matches_independent_split_and_force_derivative[hex8]
test_invalid_reference_and_inverted_current_geometries_are_refused[tet4]
test_invalid_reference_and_inverted_current_geometries_are_refused[hex8]
test_j2_assembled_internal_force_matches_independent_tensor_gauss_reference[perfect-tet4]
test_j2_assembled_internal_force_matches_independent_tensor_gauss_reference[perfect-hex8]
test_j2_assembled_internal_force_matches_independent_tensor_gauss_reference[isotropic_hardening-tet4]
test_j2_assembled_internal_force_matches_independent_tensor_gauss_reference[isotropic_hardening-hex8]
test_each_integration_point_uses_its_own_accepted_j2_history[tet4]
test_each_integration_point_uses_its_own_accepted_j2_history[hex8]
test_j2_element_rejects_incomplete_or_surplus_state_vectors[tet4-missing]
test_j2_element_rejects_incomplete_or_surplus_state_vectors[tet4-surplus]
test_j2_element_rejects_incomplete_or_surplus_state_vectors[hex8-missing]
test_j2_element_rejects_incomplete_or_surplus_state_vectors[hex8-surplus]
test_j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps[virgin-perfect-tet4]
test_j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps[virgin-perfect-hex8]
test_j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps[virgin-isotropic_hardening-tet4]
test_j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps[virgin-isotropic_hardening-hex8]
test_j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps[preloaded-perfect-tet4]
test_j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps[preloaded-perfect-hex8]
test_j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps[preloaded-isotropic_hardening-tet4]
test_j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps[preloaded-isotropic_hardening-hex8]
test_j2_unloading_and_reverse_reyield_follow_fixed_accepted_history[perfect-tet4]
test_j2_unloading_and_reverse_reyield_follow_fixed_accepted_history[perfect-hex8]
test_j2_unloading_and_reverse_reyield_follow_fixed_accepted_history[isotropic_hardening-tet4]
test_j2_unloading_and_reverse_reyield_follow_fixed_accepted_history[isotropic_hardening-hex8]
test_dead_load_residual_derivative_is_negative_internal_force_tangent[tet4]
test_dead_load_residual_derivative_is_negative_internal_force_tangent[hex8]
test_accepted_element_history_advances_only_when_trial_states_are_accepted[tet4]
test_accepted_element_history_advances_only_when_trial_states_are_accepted[hex8]
test_discarded_j2_trial_cannot_contaminate_next_accepted_element_update[tet4]
test_discarded_j2_trial_cannot_contaminate_next_accepted_element_update[hex8]
test_composite_state_rollback_commit_and_accepted_identity_are_deterministic
```

At the initial sweep's final `h/L=3e-6`, for example, the TET4 virgin/perfect-plastic matrix error was `6.379e3 N/m`, normalized `2.104e-8`; the preceding normalized values were `2.104e-6` and `2.338e-7`. The first two coarse points exceeded the proposed `1e-7` gate, so three passing adjacent points could not exist. This was a finite-difference sweep defect, not evidence of a production tangent defect. Original thresholds were preserved.

## 3. Formulations exercised

### Small-strain J2

For each point the force is assembled as `f_int = sum_g w_g det(J_0,g) B_g^T sigma_g`, with engineering strain order `[xx, yy, zz, gamma_xy, gamma_yz, gamma_xz]` and tensorial stress shear. The returned matrix is the internal-force tangent candidate `K_int = sum_g w_g det(J_0,g) B_g^T C_alg,g B_g`; under a fixed dead nodal load, the free residual `R=f_ext-f_int` therefore has derivative `dR/du=-K_int`.

Finite-difference evaluations received detached copies of the same accepted material state. Virgin and preloaded states, `H=0`, `H=1.5 GPa`, elastic/plastic updates, unloading, reverse re-yield, mixed directions, a weak translation-plus-1%-mixed direction, and an exact translation null direction were exercised. The force oracle independently reconstructed shape gradients, engineering-Voigt B matrices, tensorial stress, and radial return; it does not call the production J2 material update. The derivative oracle differentiates the assembled element force with centered differences while holding accepted state fixed and checking branch identity. It is not an FEM solve.

### Total-Lagrangian StVK

The TET4 one-point and HEX8 eight-point routes use reference gradients, `F=I+Grad_X(u)`, `E=(F^T F-I)/2`, second-Piola stress `S`, and `P=F S`. Internal force is `f_int,a = integral(P_iJ N_a,J dV_0)`. The independent reference forms the raw material and geometric contractions separately, then compares their sum to the returned stiffness and to finite differences of internal force. Rigid rotation, force covariance, homogeneous finite deformation, and invalid current `det(F)` were included.

## 4. J2 assembled tangent diagnostics

The table reports full-matrix Frobenius errors at the last three central-difference steps. `e_abs` is in N/m; `rho_G` uses the test's `max(||D_h f_int||_F, K_ref sqrt(n_dof))` scale. `rho_local,max` is the largest normalized direction-local error among mixed, deviatoric-shear, and weak-mixed directions at `h/L=3e-7`. The exact translation null is excluded from local relative acceptance because its derivative is zero; its absolute error remains about `4e-6` to `1e-5 N/m` on TET4 and `7e-6 N/m` on HEX8, while its global normalized value is below `1e-13`.

| Element | History | H (Pa) | `e_abs` at `3e-6` | `rho_G` at `3e-6` | `e_abs` at `3e-7` | `rho_G` at `3e-7` | `rho_local,max` at `3e-7` |
|---|---|---:|---:|---:|---:|---:|---:|
| TET4 | virgin | 0 | 6.379e3 | 2.104e-8 | 6.368e1 | 2.101e-10 | 9.421e-10 |
| HEX8 | virgin | 0 | 2.708e3 | 1.053e-9 | 2.704e1 | 1.051e-11 | 1.579e-9 |
| TET4 | virgin | 1.5e9 | 6.340e3 | 2.092e-8 | 6.341e1 | 2.092e-10 | 9.170e-10 |
| HEX8 | virgin | 1.5e9 | 2.692e3 | 1.047e-9 | 2.715e1 | 1.056e-11 | 1.757e-9 |
| TET4 | preloaded | 0 | 1.465e4 | 4.833e-8 | 1.466e2 | 4.835e-10 | 1.634e-9 |
| HEX8 | preloaded | 0 | 6.220e3 | 2.418e-9 | 6.245e1 | 2.428e-11 | 1.519e-9 |
| TET4 | preloaded | 1.5e9 | 1.456e4 | 4.803e-8 | 1.456e2 | 4.805e-10 | 1.601e-9 |
| HEX8 | preloaded | 1.5e9 | 6.181e3 | 2.403e-9 | 6.190e1 | 2.407e-11 | 1.149e-9 |

All eight full-matrix error sequences decrease approximately as `h^2` over the tested range. Each has a three-point fine-step window meeting the module's **proposed** global plateau conditions (`rho_G <= 1e-7`, spread `<=5e-8`). The worst reported `rho_G` at `h/L=3e-6` is `4.834e-8`; the worst at `3e-7` is `4.836e-10`. The maximum non-null local error at `3e-7` is `1.757e-9`. These support a bounded candidate review only; neither `1e-7` nor `1e-5` is Owner-frozen.

**Local-gate limitation:** the prepared test currently asserts `min(local_errors) <= PROPOSED_J2_DIRECTIONAL_TANGENT_TOL`, not that every direction's fine-step local error or local plateau satisfies the candidate limit. The printed evidence shows every non-null direction's errors at `3e-6` and `3e-7` below `1e-5`, but that stronger statement is diagnostic, not enforced by the current assertion. Tighten this assertion before using it as a frozen mandatory gate. This was documented rather than changed after the third and final authorized test cycle.

## 5. J2 state-vector P1

The expected direct element history length is **one** mapping for TET4 and **eight** mappings for HEX8. The four negative probes intentionally xfailed because the current code does not reject malformed vectors:

| Call | Supplied count | Expected | Observed direct result | Consequence |
|---|---:|---:|---|---|
| TET4 missing | 0 | 1 | Accepted; returned one trial state | Empty list is treated like no state/virgin history. |
| TET4 surplus | 2 | 1 | Accepted; returned one trial state | Entries after index 0 are ignored. |
| HEX8 missing | 7 | 8 | Accepted; returned eight trial states | Missing point is evaluated with `None`, which initializes virgin history. |
| HEX8 surplus | 9 | 8 | Accepted; returned eight trial states | Entries after integration point 7 are ignored. |

Source: `Tet4Element.internal_force_tangent_state` selects `states[0] if states else None` (`tet4.py:74`); `Hex8Element.internal_force_tangent_state` selects `states[g] if states and g < len(states) else None` (`hex8.py:130`). `initial_material_states()` normally creates the correct count (`core/nonlinear/material_state.py:166-214`), but `core/assembly/nonlinear.py:318-335` forwards an existing row to the element and validates the returned collection's type, not its expected length. No distinct public-route length guard was found in that inspected path. Therefore standard fresh initialization is dimensioned correctly, while malformed persisted or caller-supplied rows may silently lose history; checkpoint restore validation was not separately exercised here.

**P1 correction proposal (not implemented):** for a stateful material, treat `states is None` as explicit virgin initialization; when a list is supplied, require exactly the element's integration-point count and a valid mapping at every slot before any constitutive update. Reject empty, truncated, surplus, and malformed rows with a typed invalid-state error. Validate at the direct element boundary so both direct callers and the public assembly path receive the same protection. Do not rely on returned list length to detect a missing input state.

## 6. Tangent symmetrization P1

The production methods symmetrize returned matrices at `tet4.py:81`, `hex8.py:137`, `tet4_total_lagrangian_batch.py:85`, and `hex8_total_lagrangian_batch.py:73`. The reconstructed raw skew metric is

```text
rho_skew = ||K_raw - K_raw^T||_F / max(||K_raw||_F, K_ref sqrt(n_dof))
```

For StVK, the independent unsymmetrized `K_material+K_geometric` reference gave TET4 skew `1.771e-5 N/m`, `rho_skew=6.713e-17`, and symmetrization change `1.129e-5 N/m`; HEX8 gave `4.169e-5 N/m`, `rho_skew=4.052e-17`, and change `2.551e-5 N/m`.

For J2, the pre-symmetrized `sum B^T C_alg B` matrix was reconstructed from independently enumerated B/weights and the material response at the fixed accepted history. Across the eight tangent cases, maximum raw skew was `1.830e-5 N/m`, maximum `rho_skew=7.114e-18`, maximum symmetrization change `1.145e-5 N/m`, and returned-versus-reconstructed-symmetric difference was zero at reported precision. This reconstruction uses the production constitutive tangent; the separate force finite differences provide the derivative comparison.

The raw production matrix is not directly exposed, so these measurements are reconstructed from the source formulas rather than captured before the in-method symmetrization. The errors are at floating-point roundoff scale and the returned tangent agrees with finite-difference internal-force derivatives on the tested states. There is no evidence here that symmetrization conceals a material differentiation error. A minimal observability proposal, if direct inspection is later required, is an opt-in private diagnostic returning `(K_raw, 0.5*(K_raw+K_raw.T))` while preserving default return values; this requires separate Owner approval and is not necessary to alter the production route based on these results.

## 7. Independent review and limitations

The mathematical oracles are independent of the corresponding element assembly routines: shape gradients, J2 stress updates, and StVK stress/energy/tangent contractions are reconstructed separately. The derivative itself intentionally finite-differences the production element force. The read-only review after execution was conducted by the primary agent; **no independent second reviewer was available**, so it is a self-review rather than an independent review.

* **P0:** none found in the reviewed exact-path execution.
* **P1:** malformed TET4/HEX8 state-vector lengths are accepted as detailed above.
* **P1/observability:** production tangent methods return only symmetrized matrices. Reconstructed raw skew is negligible in these cases, but the source does not expose the unmodified matrix.
* **P2:** the tests use one canonical unit TET4 and HEX8 each, not distorted meshes; the geometry determinant thresholds remain implementation guards, not approved physical limits.
* **P2:** no global constrained-DOF residual/reaction assembly, follower-force tangent, mesh convergence, serialized checkpoint/restart, crash durability, native FEM, public solver, production Armijo certificate, or real contact/material retry path was exercised.

## 8. Recommendations and disposition

1. Retain the six-step J2 matrix sweep. It fixes the initial false failure without relaxing the candidate tolerances.
2. Keep the J2 tangent limits as `PROPOSED`; seek Owner review and a genuinely independent scientific review before freezing the gate. Keep `J2_TANGENT_CONSISTENCY = BLOCKED_PENDING_INDEPENDENT_EVIDENCE`.
3. Obtain separate Owner authorization before adding the state-count production guard. The xfailed tests should become ordinary passing negative tests only after that implementation is authorized and reviewed.
4. No tangent symmetrization change is recommended from these measurements. If direct raw observability is required, approve a non-default diagnostic seam separately.
5. Preserve the scope boundary: these runs are direct element-kernel evidence, not native FEM V&V or qualification.

```text
D2_TEST_EXECUTION: PARTIAL
TET4_J2_ELEMENT_VNV: VERIFIED_BOUNDED (correctly sized histories only)
HEX8_J2_ELEMENT_VNV: VERIFIED_BOUNDED (correctly sized histories only)
TET4_TL_STVK_ELEMENT_VNV: VERIFIED_BOUNDED
HEX8_TL_STVK_ELEMENT_VNV: VERIFIED_BOUNDED
J2_STATE_VECTOR_P1: CHARACTERIZED / CORRECTION_PROPOSED
RAW_TANGENT_SKEW_P1: MEASURED_BY_RECONSTRUCTION
ELEMENT_RESIDUAL_JACOBIAN: VERIFIED_BOUNDED
J2_TANGENT_GATE: REVISED_CANDIDATE_FOR_OWNER_REVIEW
J2_TANGENT_CONSISTENCY: BLOCKED_PENDING_INDEPENDENT_EVIDENCE
NEO_HOOKEAN_INTEGRATION: NOT_AUTHORIZED
PRODUCTION_ARMIJO_CERTIFICATE: NOT_VERIFIED
NATIVE_FEM_VNV: NOT_RUN
SCIENTIFIC_QUALIFICATION: NOT_ACQUIRED
WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET
```

## 9. Artifact hashes

The production-source hashes below identify the exact inspected implementations; no production source was changed.

| File | SHA-256 |
|---|---|
| `tests/unit/test_wp_e01d1_element_vnv.py` | `07413EBF533B9314243EC8123A4A517DEC705FA16F6BC5D9355B082DC5A4E2BB` |
| `tests/conftest.py` | `D6D1D74688F1A2D24D379E687861373EA42EE7F83553EFDE72F6B02E1FCD8BF6` |
| `src/solveur/elements/solid/tet4.py` | `0517683946A0292E2224D77BA197229EBDBC91DCF935B57D9B75E728D9BE3D0B` |
| `src/solveur/elements/solid/hex8.py` | `4DD8BA606B7E8CAB9697FD26CE0BAF37FBAF046F9E95894AFB0AC8EAA0C85D7A` |
| `src/solveur/elements/solid/tet4_total_lagrangian_batch.py` | `CC7FA09C23778312B2EC8AED54208041A5E0E9EEBA0AD7F983672D6522BBEBCA` |
| `src/solveur/elements/solid/hex8_total_lagrangian_batch.py` | `D6E524B2233A84702974518A1F2136C0BEF00BC744F120041150EAE78BBF1BF5` |
| `src/solveur/elements/solid/common.py` | `EFB267439FBEA27DB606B69BEB71B7A22DB521332231E8F2E4CF03B52CB77DA5` |
| `src/solveur/materials/solid.py` | `7D8223C81999D037900C26BF1A6A2ABC9F4B47C0CFF597F4BE0CF0163E8092AA` |
| `src/solveur/core/assembly/nonlinear.py` | `C5C6E1953C3B08C30397F18F8DF07FB8D355216BF372C45CEE5695FCE7BC65E1` |
| `src/solveur/core/nonlinear/material_state.py` | `6439F50398A8A914123ABD804752C018D879FAD909F437F075267373916B7DFA` |
| Initial D1 preparation report | `E96B45899AF3498A2F0D658A65EF53E0248A465510FCB715B5D7AB9A58F26AAA` |
| Final exact-run log (temporary, not in repository) | `43BD29C2095D35DE013F3E1B20902F7EF66AD0081542564C42A7CCF6F35A7420` |

No production source was modified. The D1 report remains the historical preparation record; this D2 dossier records the subsequent execution and test-only remediation.
