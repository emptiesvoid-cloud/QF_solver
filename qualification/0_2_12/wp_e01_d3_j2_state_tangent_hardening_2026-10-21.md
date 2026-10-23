# WP-E01-D3 — J2 state contract and element tangent V&V hardening

**Date:** 2026-10-21
**Repository:** `C:\wpc01-frictionless-public-integration-wt\wp-e01`
**Branch:** `codex/qf-wp-e01-a-implementation-20261020`
**Baseline:** `5915a3ec35d72e89f740f6ffe090cb8bfed48357`
**Scope:** Direct TET4/HEX8 element boundaries, test preparation, and optional pre-symmetrization diagnostics. No pytest, FEM solve, public solver, Gmsh, worker, or subprocess execution.

## 1. Executive result

The direct small-strain J2 element boundary now fails closed on an explicit incomplete or malformed integration-point state vector. The existing `None` path remains the virgin-state initialization request. The TET4 and HEX8 counts are taken from their own `integration_point_count` values (1 and 8); the rule is limited to `VonMisesElastoplasticMaterial` and does not alter stateless solid materials or other element families.

The J2 tangent candidate test now checks every eligible direction on its own fine-step window. It reports the analytical and finite-difference actions, dimensional and normalized errors, step size, plateau, branch margin, and a direction status. A rigid-translation null direction is `NOT_EVALUABLE` for local relative error when its analytical action is no larger than the proposed `64 eps K_ref ||p||` floor; its global normalized and absolute errors remain reported and its global plateau remains checked. All candidate tolerances remain proposed.

Raw pre-symmetrization tangents are observable through opt-in internal diagnostics on direct J2 TET4/HEX8 and per-element HEX8-TL paths. Defaults and returned tangent values are unchanged by source inspection. The TET4-TL batch path already returns its raw sparse tangent directly; the D2 dossier's statement that this path symmetrizes the returned matrix conflicts with the baseline source and is corrected here as a source observation, without rewriting the historical D2 dossier.

No tests were run. Historical D2 results remain historical: 43 PASS and 4 XFAIL in the final D2 run. The new regression inventory is 21 test functions and 65 parameter-expanded cases, with the four old expected-failure probes replaced by ordinary contract assertions.

## 2. J2 integration-point state contract

The validation helper is called before element geometry or constitutive evaluation for J2. It enforces:

| Element route | Current integration scheme | Explicit state vector |
|---|---:|---|
| Small-strain J2 TET4 | One constant-strain point | Exactly 1 mapping |
| Small-strain J2 HEX8 | 2×2×2 Gauss integration | Exactly 8 mappings, in `integration_points` order |

`states=None` remains the existing fresh-state path. An explicitly supplied `[]`, tuple, short vector, surplus vector, non-mapping slot, or mapping missing any of `equivalent_plastic_strain`, `plastic_strain`, `plastic_dissipation`, `stress`, or `strain` raises `InputValidationError`. This required field set accepts both `VonMisesElastoplasticMaterial.initial_state()` and the accepted states produced by the existing return map; the optional `model` field is not required because the existing initial-state schema omits it. The material continues to validate model identity and field values.

Integration-point identity is positional. These direct APIs have no separate integration-point ID field, so duplicate-ID validation is not applicable. The HEX8 history regression uses distinct nonzero accepted histories and verifies that reordering the list changes the independently referenced force. Invalid vectors are rejected before any constitutive point is evaluated; the tests also snapshot the supplied states to detect mutation. The state-returning element method does not commit accepted state.

The new `validate_j2_state_vector` helper is called only for `VonMisesElastoplasticMaterial`. Stateless `SolidMaterial` callers retain the existing behavior, including an explicit empty `states` list being ignored. This avoids applying J2 cardinalities to unrelated formulations. The public nonlinear assembly still initializes stateful materials through `initial_material_states`; its existing typed wrapper catches `InputValidationError` as `ValueError` and emits `NumericalConvergenceError` with the existing `MATERIAL_UPDATE_FAILURE` classification. The global assembly algorithm, checkpoint schema, and WP10 behavior were not changed; malformed direct J2 inputs now follow that existing typed failure path.

The five required history keys prevent an empty or partial mapping from silently receiving the material's default zero plastic history. Numeric and material-identity validation remains in the existing constitutive implementation. The code does not add a separate element-point identity or alter the state serialization schema.

## 3. Directional tangent acceptance candidate

The D2 numerical thresholds are unchanged and remain **PROPOSED**:

* Global stiffness-normalized error: `1e-7`.
* Eligible direction-local error: `1e-5`.
* Existing centered step sweep: `h/L = (1e-4, 3e-5, 1e-5, 3e-6, 1e-6, 3e-7)`.
* Existing three-point plateau rule: all three errors are at or below the applicable tolerance and their spread is at most half that tolerance.

For each J2 direction `p`, the candidate test computes `K_int p` and centered differences of the element internal force while reusing an unchanged copy of the same accepted state. It verifies elastic/plastic branch identity and checks the independent reference's positive yield margin at the base and both perturbations. Each direction must satisfy the global plateau over the final three steps. Each eligible direction must also satisfy its own local directional plateau over those steps. No `min(local_errors)` aggregation remains.

The local denominator uses `max(||D_h f_int||_2, 64 eps K_ref ||p||_2)`. If `||K_int p||_2 <= 64 eps K_ref ||p||_2`, the local relative metric is declared `NOT_EVALUABLE`, not PASS. The global error, dimensional absolute error, perturbation size, and branch margin are still emitted. For other directions, the candidate reports the selected fine-window step and its analytical action, finite-difference derivative, absolute error, global error, local error, plateau status, and branch margin. The full candidate does not test through a yield switch; nonsmooth transitions remain excluded from centered branch-preserving derivatives.

The force and tangent oracles remain the existing independent tensor/shape-gradient constructions from D2. The force derivative necessarily differentiates the production element force; it is not an independent constitutive implementation. The D2 gate is therefore a bounded element derivative check, not material qualification or a frozen J2 tangent acceptance rule.

## 4. Raw tangent observability

The opt-in `diagnostics` keyword captures a copy before symmetrization. It does not alter the default return tuple or the default matrices. The diagnostic identifies each matrix as `d_internal_force_d_displacement` and records its Frobenius norm, raw skew, physical denominator floor, and normalized skew:

```text
rho_skew = ||K_raw - K_raw^T||_F / max(||K_raw||_F, K_ref sqrt(n_dof))
```

`K_ref` has stiffness units `N/m`: for J2 it is the elastic stiffness scale times `V/L²`; for StVK it is `max(3K, 2mu) V/L²`. The diagnostic matrix copy is explicitly the pre-symmetrization production matrix, not the independent reconstruction.

| Route | Direct raw-matrix visibility |
|---|---|
| J2 TET4 / HEX8 | New opt-in element diagnostic; normal return remains symmetrized |
| TL/StVK TET4 batch | Existing return is the raw sparse assembled tangent; no source change needed |
| TL/StVK HEX8 batch | New opt-in per-element raw tangent capture; normal return remains symmetrized |

For a multi-element HEX8-TL assembly, diagnostics retain each element's raw local matrix and metric; they do not allocate a second global sparse matrix. The D2 report incorrectly identified TET4-TL's returned tangent as symmetrized. At the verified baseline, `tet4_total_lagrangian_batch.py` returns `internal, tangent`; the returned sparse matrix is already the raw assembled tangent. The D2 reported numerical results are preserved, but its source description is not reused as evidence for this distinction.

## 5. Prepared tests and execution safety

**Exact module:** `tests/unit/test_wp_e01d1_element_vnv.py`
**Classification:** `NUMERICAL_UNIT` (unchanged)
**Prepared inventory:** 21 test functions, 65 parameter-expanded cases; no xfails remain in the module.
**SHA-256:** `DC6A2EAF2B6DD7F67AAF1B20C3EC6381A0319BF6F04F1B716078F01E646B6BB6`

New or strengthened coverage includes:

| Test group | Expanded cases |
|---|---:|
| Exact J2 cardinality: TET4 0/1/2; HEX8 7/8/9 | 6 |
| Explicit fresh `None` path | 2 |
| Stateless-material compatibility | 2 |
| Invalid slot type, `None`, and missing-history mapping | 8 |
| Non-list/ambiguous layout | 2 |
| `internal_force_and_tangent` wrapper validation | 2 |
| Existing J2 tangent gate, now per-direction | 8 |
| Existing remaining TET4/HEX8 J2 and TL/StVK cases | 35 |
| **Total** | **65** |

The test imports only NumPy, pytest, SciPy sparse support, direct TET4/HEX8 kernels, material/state helpers, and `InputValidationError`. The conftest only probes Gmsh for its two `OPTIONAL_MESH_TEST_MODULES`; this module is not in that set. Static import review found no Gmsh/native initialization, model builder, public solve, `solve_model`, worker, or child-process path. Test calculations remain bounded to 12-DOF TET4 and 24-DOF HEX8 direct element fixtures and in-memory state. The exact registered classification is retained; no safety guard was relaxed.

The prepared SHA registry entry in `tests/conftest.py` was updated without changing its tier. **Registry SHA-256:** `855511FCD82B30E12FC6F5E41A0C8D66C4C76E2FF92D29C89BDD2EF95BBA1C38`.

No collection or tests were run. Historical D2 duration was 9.79 seconds for its then-current 47 cases; this is context only, not a runtime measurement for the changed module. A future full-module run is expected to remain a small, single-threaded direct-element job; this estimate is not execution evidence.

### Exact-path Owner GO proposal

Run sequentially, stopping at any failure:

1. **State boundary only — 22 cases:**

   ```powershell
   python -m pytest -q -s tests/unit/test_wp_e01d1_element_vnv.py -k 'j2_element_requires_exact_state_vector_cardinality or j2_none_state_vector_is_the_explicit_fresh_state_path or j2_state_cardinality_rule_does_not_generalize_to_stateless_materials or j2_invalid_state_slot_fails_before_any_constitutive_update or j2_non_list_state_layout_fails_closed or j2_state_vector_validation_is_shared_by_force_tangent_wrapper'
   ```

2. **J2 directional tangent and raw capture — 8 cases:**

   ```powershell
   python -m pytest -q -s tests/unit/test_wp_e01d1_element_vnv.py -k 'j2_assembled_tangent_candidate_gate_uses_fixed_state_and_branch_preserving_steps'
   ```

3. **TL/StVK raw-tangent observation and element derivative — 2 cases:**

   ```powershell
   python -m pytest -q -s tests/unit/test_wp_e01d1_element_vnv.py -k 'stvk_assembled_tangent_matches_independent_split_and_force_derivative'
   ```

4. The full 65-case direct-element module may be authorized separately after the focused groups pass:

   ```powershell
   python -m pytest -q -s tests/unit/test_wp_e01d1_element_vnv.py
   ```

These are proposals only. Each command requires a separate exact-path Owner GO. They do not authorize native FEM, public solves, Gmsh, or qualification.

## 6. Source changes and compatibility

| File | Change |
|---|---|
| `src/solveur/elements/solid/j2_state.py` | New J2-only cardinality, mapping, and required-history validation using `InputValidationError` |
| `src/solveur/elements/solid/tet4.py` | Validate explicit J2 state vector before evaluation; optional raw tangent capture |
| `src/solveur/elements/solid/hex8.py` | Validate all eight J2 slots before the Gauss loop; optional raw tangent capture |
| `src/solveur/elements/solid/common.py` | Pure optional dense/sparse tangent-copy and Frobenius-skew helper; no state/error import added to other solid elements |
| `src/solveur/elements/solid/hex8_total_lagrangian_batch.py` | Optional per-element raw tangent diagnostics before its existing symmetrization |
| `tests/unit/test_wp_e01d1_element_vnv.py` | Fail-closed state regressions, independent state-ordering checks, direct raw capture, and per-direction tangent gates |
| `tests/conftest.py` | Updated exact module digest; `NUMERICAL_UNIT` classification retained |

No constitutive equation, material update, committed-state semantics, result serialization, checkpoint format, public solver entrypoint, public default, production Armijo certificate, or qualification state changed. The normal J2 and HEX8-TL return matrices still use their previous symmetrized values. The existing TET4-TL raw return is unchanged. Correctly sized J2 and stateless routes are intended to preserve their prior calculations, but the changed source has not been rerun; this report does not inherit D2 PASS evidence as fresh verification.

## 7. Review and remaining limits

The final review was a second read-only pass by the primary agent, **not an independent reviewer**.

* **P0:** none found in the reviewed diff.
* **P1:** malformed direct J2 state vectors are now rejected in source, but the regression suite is not run. `None` remains a caller-declared fresh-state path; a caller that incorrectly passes `None` after an accepted history cannot be distinguished at this direct API. The nonlinear solver's normal initialization path supplies a complete material-state table; checkpoint/topology corruption handling remains governed by the existing WP10 contract.
* **P1:** J2 tangent tolerances and the null-direction criterion are test proposals only. The tangent gate remains unapproved, and no J2 tangent consistency claim is made.
* **P2:** no explicit integration-point IDs exist; sequence position is the only identity. No native FEM, global assembly, contact coupling, checkpoint restart, full Newton qualification, or crash durability was exercised here.
* **P2:** TET4-TL's raw return differs from the D2 prose; its historical numeric results are not reclassified, but the source description must be read as corrected by this D3 record.

The raw diagnostic and tests do not validate a production Armijo derivative certificate. The J2 tangent gate remains `BLOCKED_PENDING_INDEPENDENT_EVIDENCE`; WP-E01 remains `OPEN / EXPERIMENTAL_TARGET`.

## 8. Static verification and status

Static AST parse and compile succeeded for all changed Python files. The test inventory was computed from the module's parametrization syntax (21 functions, 65 expanded cases). `git diff --check` reported no whitespace errors; Git emitted only its line-ending normalization warning for the existing test file. Hash registry and source digest must be rechecked at commit time.

```text
J2_STATE_VECTOR_P1: CORRECTED_BY_SOURCE
STATE_VECTOR_NEGATIVE_TESTS: PREPARED_NOT_RUN
J2_DIRECTION_LOCAL_GATE: CORRECTED_BY_TEST
RAW_TANGENT_SKEW_P1: DIRECTLY_OBSERVABLE_BY_SOURCE
TET4_J2_VNV: PREVIOUS_BOUNDED_EVIDENCE / REGRESSION_NOT_RUN
HEX8_J2_VNV: PREVIOUS_BOUNDED_EVIDENCE / REGRESSION_NOT_RUN
TET4_TL_STVK_VNV: PREVIOUS_BOUNDED_EVIDENCE
HEX8_TL_STVK_VNV: PREVIOUS_BOUNDED_EVIDENCE
J2_TANGENT_GATE: REVISED_CANDIDATE_FOR_OWNER_REVIEW
J2_TANGENT_CONSISTENCY: BLOCKED_PENDING_INDEPENDENT_EVIDENCE
NATIVE_FEM_VNV: NOT_RUN
ARMIJO_PRODUCTION_CERTIFICATE: NOT_VERIFIED
SCIENTIFIC_QUALIFICATION: NOT_ACQUIRED
WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET
```

## 9. Integrity

| Artifact | SHA-256 |
|---|---|
| `src/solveur/elements/solid/j2_state.py` | `1DD85418DF2026D3A9E3DE4F8DA5FCA30021E85882F0606290F083C0D23C26A4` |
| `src/solveur/elements/solid/common.py` | `ED5EF8CDEF23B001F1D0FE1DF7ECB603180512D70DBA46D502B860B3A3D30379` |
| `src/solveur/elements/solid/tet4.py` | `5DAA0CDECE28F0C352649607872EED2A49900ACF7BE76BCC11EB98A8C9181B59` |
| `src/solveur/elements/solid/hex8.py` | `E4D37B19268BD7FCE81F270E17BA314CE8390667B19685CC982F514802E13A3F` |
| `src/solveur/elements/solid/hex8_total_lagrangian_batch.py` | `95DF9E1895BB631D598FA52FD22986E153C865F77C91557E904FF0AF766451A6` |
| `tests/unit/test_wp_e01d1_element_vnv.py` | `DC6A2EAF2B6DD7F67AAF1B20C3EC6381A0319BF6F04F1B716078F01E646B6BB6` |
| `tests/conftest.py` | `855511FCD82B30E12FC6F5E41A0C8D66C4C76E2FF92D29C89BDD2EF95BBA1C38` |

Documentation commit: reported in the delivery message after commit. The source and test commits are `f5775ab3` and `87c6d91f`. The TET4-TL source inspected for the D2 report discrepancy remains unchanged at SHA-256 `CC7FA09C23778312B2EC8AED54208041A5E0E9EEBA0AD7F983672D6522BBEBCA`. The canonical roadmap and historical D2 dossier were not modified.
