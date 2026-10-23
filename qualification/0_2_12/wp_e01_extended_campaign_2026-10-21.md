# WP-E01 Extended Campaign — D4 Execution and Integrated FEM Preparation

**Date:** 2026-10-21  
**Branch:** `codex/qf-wp-e01-a-implementation-20261020`  
**Verified starting HEAD:** `5334f9a9655fb03dc32465c9a301039908119bdf`  
**Scope:** Exact-path D4 offline element test, its test-fixture correction, and integrated nonlinear FEM verification preparation. No native backend, Gmsh, public solver, or additional FEM test was run.

## 1. D4 execution chronology

Preflight verified the expected D4 test SHA-256 `DC6A2EAF2B6DD7F67AAF1B20C3EC6381A0319BF6F04F1B716078F01E646B6BB6`, the registry SHA-256 `855511FCD82B30E12FC6F5E41A0C8D66C4C76E2FF92D29C89BDD2EF95BBA1C38`, and the `NUMERICAL_UNIT` registration. The reviewed module imports direct element kernels, NumPy/SciPy, material/state helpers and pytest. The conftest Gmsh probe is conditional on a separate optional-mesh module; it is not reached for this module. The test contains no `solve_model`, public solver, backend, Gmsh, worker, or process call.

The authorized first-stage command was run once, with BLAS/OpenMP thread counts limited to one:

```powershell
python -m pytest -q -s tests/unit/test_wp_e01d1_element_vnv.py -k 'j2_element_requires_exact_state_vector_cardinality or j2_none_state_vector_is_the_explicit_fresh_state_path or j2_state_cardinality_rule_does_not_generalize_to_stateless_materials or j2_invalid_state_slot_fails_before_any_constitutive_update or j2_non_list_state_layout_fails_closed or j2_state_vector_validation_is_shared_by_force_tangent_wrapper'
```

**Observed result:** 6 passed, 16 failed, 43 deselected (22 selected; pytest reported 1.76 s). The command exited nonzero. Failures were:

* Cardinality: `tet4-0`, `tet4-2`, `hex8-7`, `hex8-9`.
* Invalid slots: `none`, `list`, `string`, and `missing-history`, each for TET4 and HEX8.
* Non-list state layout: TET4 and HEX8.
* Shared force/tangent wrapper: TET4 and HEX8.

The two valid cardinalities, explicit `None` fresh initialization, and stateless-material compatibility cases passed. The tangent, StVK, and full-module stages were **not run** after the first-stage failure.

### Failure classification and prepared correction

All 16 failures used the test-only `_CountingStatefulMaterial`, which was a composition wrapper rather than a `VonMisesElastoplasticMaterial` subtype. The production boundary intentionally activates J2 cardinality validation with `isinstance(material, VonMisesElastoplasticMaterial)` before point evaluation. Consequently, this spy did not represent the selected J2 formulation and did not exercise that guard. This run does not demonstrate a defect for the direct concrete J2 route, nor does it verify the malformed-state behavior on that route. The broader custom-adapter state identity contract remains unspecified; it should not be expanded implicitly.

The spy is now a J2 subclass with an external-to-the-material behavior counter implemented as an instance attribute, so it retains the production material identity while still proving that rejected state input causes zero constitutive calls. The invalid-state tests still assert typed refusal and state immutability. This is a test-only correction; no production source, thresholds, mathematical contract, or safety tier changed. The registry digest was updated. **The changed identity has not been executed.**

## 2. Integrated FEM verification preparation

These are future test designs, not results. They separate small-strain J2 from total-Lagrangian StVK and distinguish element/global assembly checks from protected solver-entry checks.

### Common tiny cube

Use the unit cube nodes, in the existing HEX8 order:

```text
0 (0,0,0)   1 (1,0,0)   2 (1,1,0)   3 (0,1,0)
4 (0,0,1)   5 (1,0,1)   6 (1,1,1)   7 (0,1,1)
```

The HEX8 mesh is one element `[0,1,2,3,4,5,6,7]`. The TET4 counterpart uses six positive-orientation tetrahedra about diagonal `0–6`:

```text
[0,1,2,6], [0,2,3,6], [0,3,7,6],
[0,7,4,6], [0,4,5,6], [0,5,1,6]
```

For uniaxial traction in `+X`, fix `UX` on the `x=0` nodes `[0,3,4,7]`; additionally fix `UY,UZ` at node 0 and `UZ` at node 3 to remove rigid modes without constraining the homogeneous uniaxial solution. Apply equal consistent nodal forces `F/4` in `+X` to nodes `[1,2,5,6]`. The reference area and volume are both 1 m² and 1 m³. This gives 24 total DOFs, at most 17 free DOFs, one HEX8 or six TET4 elements, and at most eight integration points per element.

### Small-strain J2 references and routes

Use SI material values `E=210 GPa`, `nu=0.30`, `sigma_y0=250 MPa`, and `H=20 GPa` (positive isotropic hardening; do not use a load-controlled perfect-plastic plateau as the primary Newton fixture). For monotonic target stress `sigma=F/A`, independently reduce the homogeneous uniaxial material response to:

```text
elastic:  eps_x = sigma/E, eps_y = eps_z = -nu*sigma/E, alpha = 0
plastic:  alpha = (sigma - sigma_y0)/H
          eps_x = sigma/E + alpha
          eps_y = eps_z = -nu*sigma/E - alpha/2
```

The monotonic route uses `analysis.type=nonlinear_static`, `method=newton_raphson`, `kinematics=small_strain`, and the explicit E01-A opt-in. Predeclare `e01a_force_reference_n=F_max`, `e01a_absolute_force_tolerance_n=0`, `e01a_initial_load_increment=0.2`, `max_iterations=25`, `tolerance=1e-8`, `adaptive_load_steps=false`, and `load_steps=5`. Load targets are 0.2, 0.4, 0.6, 0.8, and 1.0 of the case-declared final traction; no Armijo certificate is required for `newton_raphson`.

For an elastic-to-plastic sequence, choose load targets that straddle 250 MPa, e.g. 200, 240, 260, and 300 MPa. Compare every accepted integration-point stress and alpha to the independent one-dimensional return-map history, check the free-DOF residual at each acceptance, and verify reaction balance. These remain proposed references and execution gates; only the E01-A residual criterion itself is already contract-approved experimental behavior.

Unloading/reloading uses the existing signed `analysis.load_path` capability with the E01-A opt-in **disabled**, because E01-A explicitly rejects caller-supplied load paths. A proposed cyclic factor path is `[0.4, 1.0, 0.4, 0.0, -1.0, 0.0, 1.0]` on the same load pattern. Compare state transitions to an independent scalar signed J2 return map. Results from this legacy path must not be presented as E01-A load-control verification.

For checkpoint/restart, save only an accepted step to an isolated temporary path, reconstruct the same model identity, verify accepted displacement/material state and continue the remaining path. This tests normal restart consistency only; it does not test abrupt-process or filesystem crash durability. No production J2 contributor currently supplies a deterministic retryable finite admissibility event for this cube. A rollback case must use a clearly labelled synthetic typed contributor and cannot claim production J2 retry coverage.

### Total-Lagrangian StVK references

Use the same meshes with a homogeneous isotropic elastic material. For a prescribed affine deformation gradient `F`, compute independently:

```text
E_GL = 0.5 (F^T F - I)
S = lambda_L tr(E_GL) I + 2 mu E_GL
P = F S
sigma_Cauchy = J^-1 P F^T
```

For a modest uniaxial stretch `lambda_x=1.02`, set `E11=(lambda_x²-1)/2`; the traction-free transverse Green strain follows from `S22=S33=0` as `E22=E33=-lambda_L E11/[2(lambda_L+mu)]`, with positive transverse stretch `sqrt(1+2 E22)`. Apply nominal force `P11*A_ref` as equal `X` nodal forces on the loaded face. Compare homogeneous nodal deformation, assembled forces, stress measures, reactions, and `det(F)>0` against this reference. This fixture is bounded to modest StVK strain and makes no claim that StVK is suitable for arbitrary distortions.

For global rigid-rotation objectivity use an assembly-only state `u=(Q-I)X`, with orthogonal `Q`. The reference has `E_GL=0`, zero StVK energy, and zero internal nodal force. This cannot be verified by a zero-displacement solve; it is a direct global-assembly test.

For global derivative checks, define `R=f_ext-f_int` for dead nodal loads, so `J_R=-K_int`. Hold incoming J2 states fixed and make detached trial states for every perturbation. Use central differences only within a smooth fixed branch; use one-sided differences at yield switches. Report absolute, global stiffness-scaled, and direction-local errors. Do not adopt one tangent threshold across all branches or promote the D4 candidate gate.

### Proposed future test inventory and safety classes

No integrated test module was created or executed under this campaign. Proposed exact paths and node IDs:

* `tests/unit/test_wp_e01_integrated_assembly_vnv.py` (six direct assembly cases): `test_j2_global_tangent_fd[HEX8/TET4]`, `test_tl_stvk_global_rotation[HEX8/TET4]`, `test_tl_stvk_global_tangent_fd[HEX8/TET4]`. Candidate classification: `NUMERICAL_UNIT` only after import-closure review and exact hash registration; no public solver, model router, backend, Gmsh, worker, or process.
* `tests/unit/test_wp_e01_integrated_solver_vnv.py` (nine protected solver cases): `test_j2_e01a_monotone_patch[HEX8/TET4]`, `test_j2_cyclic_state_history[HEX8/TET4]`, `test_j2_checkpoint_restart[HEX8/TET4]`, `test_j2_synthetic_retry_rollback`, `test_stvk_uniaxial_patch[HEX8/TET4]`. Because these call an integrated nonlinear solver entry, the existing registry policy classifies the unreviewed route `NATIVE_AUTH_REQUIRED`; a future exact-path Owner authorization must explicitly allow the in-process Python solver scope while continuing to exclude native backends and child processes. No safety-tier bypass is proposed.

Mandatory/diagnostic checks for a future execution: E01-A free residual `||R_f||2 <= 1e-8 max(||f_target,f||2,F_ref)` with case-declared `F_ref=F_max` and `F_abs=0 N`; constraint and finite-state refusal; exact lambda=1 acceptance; reaction force balance; state continuity at every accepted step; positive `det(F)`; global residual/Jacobian sign; full-step and tangent direction diagnostics. A relative solution/state error target of `1e-8` and reaction-balance target of `1e-8` are **PROPOSED**, scaled by the corresponding analytical field/resultant; use absolute scale floors for near-zero quantities. These are not frozen. The D4 J2 tangent thresholds remain unfrozen, and near-yield nonsmooth directions are ineligible for centered differentiation.

Bound future execution to one process and one numerical-library thread, 256 MiB memory, and a 20-minute wall limit. Cap each solve at 10 prescribed increments and 25 Newton corrections/increment; permit temporary checkpoint files only under `tmp_path`. These are proposed resource limits and do not authorize execution. Exact test-file hashes and collection/import reviews must be attached to the next GO.

## 3. Status and remaining decision

* D4 execution: **FAIL** (first stage); 16 failures are attributable to a test spy that did not preserve the selected J2 type. Corrected identity prepared, not run.
* Element V&V: **INCOMPLETE**; no tangent, StVK, or full-module stage ran on the original identity.
* J2 state validation: **NOT VERIFIED by this campaign** on malformed vectors for the direct J2 identity. The test-only correction addresses the fixture; a future execution is required.
* J2 direction gate: **INCOMPLETE**; not executed.
* Raw tangent skew: **NOT_EVALUABLE** at runtime; source provides opt-in raw capture.
* J2 tangent scientific freeze: **NOT_APPROVED**; consistency remains `BLOCKED_PENDING_INDEPENDENT_EVIDENCE`.
* Integrated FEM V&V: **PREPARED_NOT_RUN**; native FEM and production Armijo certification remain unverified.
* Scientific qualification: **NOT_ACQUIRED**. WP-E01 remains **OPEN / EXPERIMENTAL_TARGET**.

The next Owner GO should authorize the corrected D4 test identity below, staged in order (state vectors, J2 tangent/raw capture, StVK diagnostics, full element module), and a separate exact-path integrated solver campaign only after D4 passes. It should include independent review of the proposed J2 tangent gate. No test authorization is carried forward automatically.

## 4. Evidence identity

The historical D2 result remains 43 PASS / 4 XFAIL and was not rerun. D3 source hashes are recorded in `wp_e01_d3_j2_state_tangent_hardening_2026-10-21.md`. This campaign changed no production source.

* Original executed test identity: `DC6A2EAF2B6DD7F67AAF1B20C3EC6381A0319BF6F04F1B716078F01E646B6BB6`.
* Corrected, unexecuted test identity: `B2B7B4DED7D0C33391041B0036D5C1C1EA527C60823E0F16B1A9362F3221128F`.
* Updated registry identity: `BE69BCA847CBA5A301D8D3EDF28FD60FAFE5F24C106F389FF5AB536760CE7DB4`; classification remains `NUMERICAL_UNIT`.
* Test correction commit: `9d0863e3f440098b677716e211bdde6ec64bef11`.

Only static syntax, registry/hash, diff, and source-path checks were performed after the test edit. No tests were rerun.
