# WP-E01-D4R Consolidated Numerical Regression Campaign

**Date:** 2026-10-21
**Branch:** `codex/qf-wp-e01-a-implementation-20261020`
**Scope:** staged direct TET4/HEX8 element-algebra tests only. No native FEM, public solver, Gmsh, subprocess, integrated nonlinear solve, or production Armijo certificate is authorized.

## Baseline and historical evidence

The campaign began at clean HEAD `fc648aff413e2dd047d96bb3b5525a9435c31496`. The original D4 attempt remains historical evidence: **6 passed, 16 failed, 43 deselected**. Its test spy used composition and failed the element's production J2 type check; that diagnosis was not treated as a successful regression.

The currently authorized test module initially matched SHA-256 `B2B7B4DED7D0C33391041B0036D5C1C1EA527C60823E0F16B1A9362F3221128F`; `tests/conftest.py` matched `BE69BCA847CBA5A301D8D3EDF28FD60FAFE5F24C106F389FF5AB536760CE7DB4`. The module was registered `NUMERICAL_UNIT`. Collection-only inspection found exactly 65 cases. Its imports reach NumPy/SciPy element algebra, direct element kernels, and in-memory state helpers. The collection hook's Gmsh capability probe is restricted to a separate optional mesh-test list; this module is not in that list. No public solve, native FEM, worker, or child-process path was found.

The five production-source files match the digests in the D3 report; no production source was changed during this campaign.

| Production source (D3 identity) | SHA-256 |
| --- | --- |
| `src/solveur/elements/solid/j2_state.py` | `1DD85418DF2026D3A9E3DE4F8DA5FCA30021E85882F0606290F083C0D23C26A4` |
| `src/solveur/elements/solid/common.py` | `ED5EF8CDEF23B001F1D0FE1DF7ECB603180512D70DBA46D502B860B3A3D30379` |
| `src/solveur/elements/solid/tet4.py` | `5DAA0CDECE28F0C352649607872EED2A49900ACF7BE76BCC11EB98A8C9181B59` |
| `src/solveur/elements/solid/hex8.py` | `E4D37B19268BD7FCE81F270E17BA314CE8390667B19685CC982F514802E13A3F` |
| `src/solveur/elements/solid/hex8_total_lagrangian_batch.py` | `95DF9E1895BB631D598FA52FD22986E153C865F77C91557E904FF0AF766451A6` |

## Stage 1 initial execution

The authorized 22-case state-vector selector ran with single-thread numerical-library limits. Result: **14 passed, 8 failed, 43 deselected in 1.45 s**. All eight failures were the two element families crossed with four malformed state slots. The exception type and source path were correct: `InputValidationError` originated in `validate_j2_state_vector` after the direct element API call. The assertion expected `material state at integration-point slot`, while the helper emits `J2 state at integration-point slot`. No spy-generated exception occurred.

## Test-only repair before the authorized rerun

The malformed-state test now asserts the actual typed-validator message and exercises both an unwrapped `VonMisesElastoplasticMaterial` and the counting subclass. The unwrapped call checks direct boundary refusal and input immutability; the subclass call checks that refusal happens before any constitutive `evaluate` call. `None` at the vector level remains a distinct fresh-initialization request; `None` inside a supplied state list remains invalid. The test inventory and scientific thresholds are unchanged. Production source and test safety classification are unchanged.

Updated executable identity before rerun: test SHA-256 `FFA43CB053934C6DFF319955CB0857634C761662869D4B49B6BE4973F5FD6B6D`; safety registry SHA-256 `1E605BE8AA656B1B0FCD81D3AAA87FDAEF75AF5E3BAA4EBDF8FD5272A3BF47A3`. The module remains `NUMERICAL_UNIT`; only its digest changed. `git diff --check` and AST parsing of the changed Python files passed. No imports were added.

## Staged execution results

All executions used the same reviewed module and single-thread numerical-library settings (`OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`). No other pytest module was selected.

| Stage | Exact selector | Result | Pytest runtime |
| --- | --- | ---: | ---: |
| Collection, baseline identity | `--collect-only -q tests/unit/test_wp_e01d1_element_vnv.py` | 65 collected | 1.04 s |
| Stage 1 initial, before test-only correction | six D3-approved state-vector selectors | 14 passed, 8 failed, 43 deselected | 1.45 s |
| Collection, corrected identity | same collection-only command | 65 collected | 1.08 s |
| Stage 1 corrected | six D3-approved state-vector selectors | 22 passed, 43 deselected | 1.05 s |
| Stage 2 | `-k 'j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps'` | 8 passed, 57 deselected | 9.39 s |
| Stage 3 | `-k 'stvk_assembled_tangent_matches_independent_split_and_force_derivative'` | 2 passed, 63 deselected | 1.04 s |
| Stage 4 full regression | `python -m pytest -q -s tests/unit/test_wp_e01d1_element_vnv.py` | **65 passed, 0 failed, 0 skipped, 0 xfailed, 0 xpassed** | 9.25 s |

Exact test invocations, run sequentially:

```powershell
python -m pytest --collect-only -q tests/unit/test_wp_e01d1_element_vnv.py
python -m pytest -q -s tests/unit/test_wp_e01d1_element_vnv.py -k 'j2_element_requires_exact_state_vector_cardinality or j2_none_state_vector_is_the_explicit_fresh_state_path or j2_state_cardinality_rule_does_not_generalize_to_stateless_materials or j2_invalid_state_slot_fails_before_any_constitutive_update or j2_non_list_state_layout_fails_closed or j2_state_vector_validation_is_shared_by_force_tangent_wrapper'
python -m pytest -q -s tests/unit/test_wp_e01d1_element_vnv.py -k 'j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps'
python -m pytest -q -s tests/unit/test_wp_e01d1_element_vnv.py -k 'stvk_assembled_tangent_matches_independent_split_and_force_derivative'
python -m pytest -q -s tests/unit/test_wp_e01d1_element_vnv.py
```

The collection-only and Stage 1 commands were each repeated once after the test-only digest update. No other pytest command was run.

The initial Stage 1 failures were assertion-message mismatches only. Every exception was the intended `InputValidationError` raised by `validate_j2_state_vector`; the actual message begins `J2 state at integration-point slot`. After the documented test-only repair, both the unwrapped material and spy path passed. No test assertion or scientific tolerance was relaxed.

The D4R baseline module was `B2B7B4DED7D0C33391041B0036D5C1C1EA527C60823E0F16B1A9362F3221128F`; after the in-scope test-only repair its SHA-256 is `FFA43CB053934C6DFF319955CB0857634C761662869D4B49B6BE4973F5FD6B6D`. The registry was updated without changing the tier; its final SHA-256 is `1E605BE8AA656B1B0FCD81D3AAA87FDAEF75AF5E3BAA4EBDF8FD5272A3BF47A3`. The full-run log is `<local-temp>\qf_wp_e01_d4r_full_20261021.log`, SHA-256 `C20F86E76AA32F6E581ADEE0722538B6DF84B6092FB7C452EC626A8A67807C9A`.

## Numerical evidence

### J2 assembled tangent

Eight cases cover TET4/HEX8, perfect plasticity / `H=1.5 GPa`, and virgin / nonzero accepted plastic history. Each finite-difference evaluation starts from a deep copy of the same accepted integration-point state. The independent force reference separately builds shape gradients and engineering-Voigt B matrices, then applies its tensor-form radial return; the element tangent is compared both with the full force derivative and four explicit directions. The sweep is `h/L = 1e-4, 3e-5, 1e-5, 3e-6, 1e-6, 3e-7`.

| Element | H (Pa) | History | Raw production skew (N/m) | `rho_skew` | Full-matrix relative error at `h/L=3e-7` | Max eligible direction global error | Max eligible direction local error |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| TET4 | 0 | virgin | 0 | 0 | 2.101e-10 | 1.626e-10 | 9.421e-10 |
| HEX8 | 0 | virgin | 9.865e-6 | 3.836e-18 | 1.051e-11 | 4.510e-12 | 2.273e-10 |
| TET4 | 1.5e9 | virgin | 0 | 0 | 2.092e-10 | 1.614e-10 | 9.169e-10 |
| HEX8 | 1.5e9 | virgin | 1.829e-5 | 7.113e-18 | 1.056e-11 | 4.437e-12 | 2.198e-10 |
| TET4 | 0 | preloaded | 0 | 0 | 4.835e-10 | 3.727e-10 | 1.634e-9 |
| HEX8 | 0 | preloaded | 1.425e-5 | 5.539e-18 | 2.428e-11 | 1.062e-11 | 4.055e-10 |
| TET4 | 1.5e9 | preloaded | 0 | 0 | 4.805e-10 | 3.696e-10 | 1.600e-9 |
| HEX8 | 1.5e9 | preloaded | 1.435e-5 | 5.580e-18 | 2.407e-11 | 1.058e-11 | 3.978e-10 |

The full-matrix fine-step absolute errors ranged from `27.04` to `146.56 N/m`. Every matrix sweep met the test's proposed plateau rule. Across all cases, the minimum branch margin over the base and perturbations was `4.743475e8 Pa`; all tested perturbations stayed on the plastic branch. Mixed, deviatoric-shear and weak-mixed directions were individually `PASS`. The rigid-translation null direction was `NOT_EVALUABLE` for local relative error, as specified by the test's `64 eps K_ref ||p||` floor; its largest selected absolute error was `9.54e-6 N/m`, and its largest global-normalized error was `1.091e-16`.

The measured J2 raw skew is from the production pre-symmetrization diagnostic, not an independent reconstruction. The maximum was `1.8295e-5 N/m`, with `rho_skew=7.113e-18`; returned-vs-symmetrized-raw difference was zero at recorded precision. These are bounded element results. The `1e-7` global, `1e-5` local, and plateau settings remain **PROPOSED**; passing them does not freeze D5 or qualify the tangent.

### TL/StVK assembled tangent

The independent reference explicitly constructs `F`, Green–Lagrange strain, PK2 stress, PK1 force, and separate material and geometric stiffness contractions. Central differences use `h/L = 3e-5, 1e-5, 3e-6`.

| Element | Raw production skew (N/m) | `rho_skew` | Full-matrix absolute error at `h/L=3e-6` (N/m) | Full-matrix normalized error |
| --- | ---: | ---: | ---: | ---: |
| TET4 | 0 | 0 | 3.924 | 1.488e-11 |
| HEX8 | 4.046e-5 | 3.933e-17 | 18.223 | 1.771e-11 |

TET4 returns the raw unsymmetrized sparse tangent; HEX8 supplies the actual per-element pre-symmetrization diagnostic. HEX8's returned matrix agreed with the independently symmetrized reference. Rigid rotation, force covariance under rotation plus stretch, homogeneous finite-deformation energy/force, invalid-geometry refusal, material/geometric split, and the dead-load residual sign `D R = -K_int` all passed in the 65-case run. The StVK `1e-7` comparison tolerance is a test proposal, not a qualification threshold.

### State and element-family findings

Stage 1 and the full suite verify TET4's one-point and HEX8's eight-point J2 state-vector cardinalities, explicit `states=None` fresh initialization, stateless-material compatibility, typed refusal of wrong counts / non-list layouts / non-mapping or incomplete slots, immutability on rejection, and rejection before constitutive evaluation. The corrected negative cases also call the unwrapped production material. This evidence is limited to the tested mapping structure and required fields; it does not establish validation of every field's numeric shape/type at checkpoint ingress.

The four unloading/reverse-reyield element cases pass for fixed accepted histories. This is direct element history evidence, not a multi-segment global load-path result. TET4 J2 remains one integration point per element; HEX8 J2 remains eight. The TL/StVK path remains separate from small-strain J2.

## Read-only review and findings

This is a second read-only pass by the primary agent, **not an independent reviewer**. The test spy inherits from `VonMisesElastoplasticMaterial`, preserves its initialization, and delegates valid evaluation to `super()`. For malformed states the exception is thrown before `evaluate`; the unwrapped checks now directly confirm the same boundary behavior. No artificial exception is introduced.

* **P0:** none found in the bounded module execution or contract trace.
* **P1:** `J2_TANGENT_CONSISTENCY` remains `BLOCKED_PENDING_INDEPENDENT_EVIDENCE`; proposed tangent thresholds have not received Owner freeze or a separate reviewer. No production Armijo route certificate was registered.
* **P1:** integrated production Newton/J2 behavior, true contributor retry evidence, global reactions, and WP10 restart across an assembled mesh remain unexecuted. The selected campaign intentionally does not reach those paths.
* **P2:** tested element geometry is canonical unit TET4 / HEX8; distorted-mesh sensitivity, mesh convergence, native FEM, public solver behavior, checkpoint crash durability, and material-field value validation at checkpoint ingress were not established.

No production code changed. The original D4 and current pre-repair test failures remain documented rather than erased.

## Integrated FEM V&V plan — prepared, not executed

The next bounded in-memory assembly study should build coordinates directly, without Gmsh. Use a unit cube with either (a) twelve TET4 elements formed by joining the twelve face triangles to an interior center node (9 nodes, 27 DOF, 12 J2 integration points), or (b) a structured `2x2x2` HEX8 mesh (27 nodes, 81 DOF, 64 J2 integration points). Prescribe the affine displacement on the outer cube nodes; leave the center node free. All test data and states are deterministic and fit in dense `81x81` matrices or small sparse matrices. Suggested cap: 30 seconds per exact module, under 256 MiB, one numerical-library thread.

Use `E=210 GPa`, `nu=0.30`, `sigma_y0=250 MPa`, and separately `H=0` and `H=1.5 GPa`. For the elastic constrained-axial-strain patch `epsilon=diag(1e-4,0,0)`, `mu=80.769230769 GPa`, `lambda=121.153846154 GPa`, and the exact stress is `diag(28.269230769,12.115384615,12.115384615) MPa`; unit-face resultants are the corresponding stress components times `1 m^2`. A predeclared physical force reference for the path can be the elastic reaction envelope `(lambda+2mu)*epsilon_max*A`, computed from the declared material, displacement endpoint and face area before solving; `F_abs=0 N`, `tau_R=1e-8` remain the frozen experimental E01-A policy, not qualification evidence.

For `epsilon=diag(epsilon_x,0,0)`, the independent J2 reference has `q_trial=2mu*epsilon_x`; virgin yield begins at `epsilon_y=sigma_y0/(2mu)=1.547619e-3`. A monotone endpoint `epsilon_x=0.002` gives `q_trial=323.076923 MPa`. From virgin state, the closed-form single-direction radial-return values are `Delta_gamma=0.0003015873` for perfect plasticity and `Delta_gamma approximately 0.0002997318` for `H=1.5 GPa`; final `q` is respectively `250 MPa` and approximately `250.449598 MPa`. Use the independent tensor recurrence at each accepted increment, not the production return map, as the state and stress oracle. Reactions use exact uniform `sigma*n` face traction and global force/moment closure.

| Proposed exact test ID | Expanded cases | Candidate classification | Reference and measured quantities | Boundary / blocker |
| --- | ---: | --- | --- | --- |
| `test_j2_global_affine_elastic_patch_and_reaction_reference[family]` | 2 | `NUMERICAL_UNIT` candidate | Closed-form stress, center-node equilibrium, face resultants and total force/moment closure | Direct in-memory assembly only; case-declared `F_ref` required. |
| `test_j2_global_monotone_path_matches_tensor_return[family-hardening]` | 4 | `NUMERICAL_UNIT` candidate | Independent tensor radial-return recurrence at `lambda=(0.25,0.5,0.75,0.80,1)`; accepted IP state continuity | Monotone path only; keeps TET4 / HEX8 separate. |
| `test_j2_global_residual_tangent_fixed_state_fd[family-hardening]` | 4 | `NUMERICAL_UNIT` candidate | `J_R=-K_int` for dead loads; perturb each free DOF from an identical accepted snapshot; report absolute, global and local errors | Use proposed D4 candidate limits only after Owner review; do not cross yield switches centrally. |
| `test_j2_global_accepted_state_wp10_v2_restart[family]` | 2 | `NUMERICAL_UNIT` candidate | Accepted-state identity, per-element integration-point identities and rejection ledger before/after a `tmp_path` round trip | Normal restart only; no crash durability claim. |
| `test_j2_global_trial_rollback_after_synthetic_retry[family]` | 2 | `NUMERICAL_UNIT` candidate | Poison a disposable trial, inject an explicitly synthetic typed retry, then compare the accepted state and digest | Synthetic orchestration only; no production material/contact retry evidence. |
| `test_stvk_global_rigid_rotation_and_affine_patch[family]` | 2 | `NUMERICAL_UNIT` candidate | `F=Q` gives `E=0`, `S=P=0`, zero energy and internal force; combined affine stretch uses independent `F/E/S/P` reference | In-memory assembly only; no public solver. |
| `test_stvk_global_residual_tangent_and_reaction_balance[family]` | 2 | `NUMERICAL_UNIT` candidate | Independent material/geometric stiffness sum, `J_R=-K_int`, reaction force/moment balance | Keep StVK separate from J2; proposed numerical gates remain unfrozen. |
| `test_e01a_j2_global_newton_trace[family-hardening]` | 4 | `NUMERICAL_UNIT` candidate, **blocked** | Compare center-node displacement against the affine solution at each `lambda`; record correction count (maximum 25), final residual evaluation, commit count and residual history | Do not run against the production route while its derivative-certificate registry is empty. Requires independently verified route derivative and separate exact-path GO; no production certificate activation is authorized here. |
| `test_j2_global_unload_reverse_reload[family-hardening]` | 4 | `NUMERICAL_UNIT` candidate, **blocked** | Accepted-state path `epsilon_x: +0.002 -> +0.001 -> -0.002 -> +0.002`; compare every IP stress, plastic strain and `alpha` with the independent tensor return recurrence | Requires multi-segment load-path / accepted-state continuation semantics; the current single monotone `lambda` contract does not express this path. |

The first seven rows are 18 candidate offline assembly/restart cases for a new hash-bound `tests/unit/test_wp_e01d4_global_assembly_vnv.py` module. The final two rows are eight additional Newton-trace and multi-segment cases proposed separately for `tests/unit/test_wp_e01d4_global_newton_vnv.py`; they remain blocked. Neither module was created or authorized for execution here. `NUMERICAL_UNIT` remains conditional on review of the final imports and execution closure; no Gmsh, `solve_model`, public solver, worker, subprocess, or native library may be reachable. The frozen production derivative-certificate registry is empty. Therefore production Newton iteration traces with J2 or StVK remain **blocked** until the route-specific residual derivative and verified-descent condition are independently established and separately authorized; do not insert a certificate as part of test preparation. The present contract uses one monotone `lambda` path, so integrated unload / reverse-reyield / reload needs separate multi-segment path support or a separate accepted-state continuation contract. D4's direct element unload/reverse-reyield tests do not fill that global-path gap.

The exact next Owner decision should be an execution GO bound to the newly prepared module's final SHA-256 for the in-memory global-assembly cases above, plus separate scientific review of the still-proposed J2 tangent gate. Public solver, native FEM and production Armijo authorization remain separate decisions.

## Final disposition

```text
D4R_EXECUTION: PASS
J2_STATE_VALIDATION: VERIFIED_BOUNDED
J2_DIRECTIONAL_GATE: VERIFIED_BOUNDED (candidate limits only)
RAW_TANGENT_SKEW: MEASURED
TET4_J2_ELEMENT_VNV: VERIFIED_BOUNDED
HEX8_J2_ELEMENT_VNV: VERIFIED_BOUNDED
TET4_TL_STVK_ELEMENT_VNV: VERIFIED_BOUNDED
HEX8_TL_STVK_ELEMENT_VNV: VERIFIED_BOUNDED
INTEGRATED_FEM_VNV: PREPARED_NOT_RUN
J2_TANGENT_SCIENTIFIC_FREEZE: NOT_APPROVED
PRODUCTION_ARMIJO_CERTIFICATE: NOT_VERIFIED
NATIVE_FEM_VNV: NOT_RUN
SCIENTIFIC_QUALIFICATION: NOT_ACQUIRED
WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET
```
