# WP-E01-K — Rigid Translation Controls and J2 Tangent Verification

Date: 2026-10-21  
Branch: `codex/qf-wp-e01-a-implementation-20261020`

## Outcome

The historical WP-E01-J result remains **12 collected, 8 passed, 4 failed**. All four failures occurred during setup, before the translation assertions, because the test paired a newly constructed `DofManager` with a `NonlinearAssemblyPlan` bound by object identity to the manager created with the plan. The test now passes the matching manager and plan together. The corrected, hash-bound module collected the same 12 intended cases and completed once under the reviewed Windows Job Object supervisor: **12 passed, 0 failed, 0 skipped, 0 xfailed, 0 xpassed**.

This verifies the exact-translation raw internal-force control within the test's proposed roundoff bounds. It does not validate an admissible reduced Newton direction, assembled J2 tangent consistency, production Newton convergence, or FEM qualification. The historical near-translation weak-direction mismatch remains unresolved.

## Identity and preservation

Starting clean identity: `b806f901e2d63fe30a2c971e6a84f7c28609ba97`.  
Repository: `C:/wpc01-frictionless-public-integration-wt/wp-e01`.  
Origin: `https://github.com/emptiesvoid-cloud/QF_solver.git`.

The old J2 report, execution logs, thresholds, scientific criteria, and all production files were preserved. The existing manifest's 29 production-source pins and 32 effective supervisor pins were rechecked and matched. No production source, FEM route, constitutive routine, public API, or Armijo certificate was changed. The original traceback and execution record remain under `qualification/0_2_12/wp_e01_j_execution_2026-10-21/`; the prior report is `qualification/0_2_12/wp_e01_j_j2_high_precision_diagnostics_2026-10-21.md`.

| Artifact | Historical identity | Corrected identity |
|---|---|---|
| `tests/unit/test_wp_e01i_j2_precision_diagnostics.py` | `59DBAF1F84E518C2F10FC573ED973EE22187399671B7045F22C3F73B349F4C95` | `C51AE1381AFC7376442DE57D62E4B1FC15C74034D03547193734C9F7C6AF8EC1` |
| `tests/conftest.py` | `A3220FD8716FC86E316EF0577E7E3E8DB789C850B0201E63EEF1ED2CD28F0618` | `E3140E747F403A6BB6B0DD323B341C7B9B88655AAC3FDCA8D6FAA8F17EA36882` |
| Collection guard | `722D30D59C710D93DAD82150C40DBF6EB6FF2CCCBCF6BB27179A3D3F24F718B4` | `90E54550596031B2CF19838604C558CE21C53E457A3EA122655BD12E8FF7478C` |
| Supervisor | `74A6043726702CEF1AEC888FC40D5BE57B1487DE2DFF4B7FAC15193C56EB450C` | `71922EBC2BA0FB9FCDF9AE257D4E0648AE72941F62F8A8D6AD5CFA601F074C0D` |

The preceding WP-E01-I execution manifest SHA-256 was `9884A3846B2D8929371DABC1E6A7D7E1BB489CCB094D62FDCADE3D193133141C`; the K manifest preserves its historical identity.

The supervisor and collection guard changes only bind the corrected executable hashes and manifest. The test remains registered `NUMERICAL_UNIT`; the 12-node allowlist and safety classification were not broadened. The initial corrected execution manifest was committed with the test correction; its final evidence fields were updated after the authorized run.

## Setup correction

`NonlinearAssemblyPlan.matches(...)` requires the plan's `model_token` and `dofs_token` to match the exact model and `DofManager` objects used for assembly. The helper had constructed `plan` with one manager, discarded that manager, and returned a newly constructed manager to the four translation tests. Assembly therefore correctly rejected the mismatched object identity before reaching any translation assertion.

The test-only correction returns the original `dofs` object from `_prepared_state(...)`, unpacks it in the four translation cases, and passes it with its bound plan. The fixture, element/node mapping, DOF ordering, prescribed DOFs, geometry, material parameters, accepted plastic history, translation vector, physical reference, and assertions are unchanged. No identity guard was bypassed.

The correction was committed as `46c0d624f643a9ef95946966164a11adfca873a6` (`test: fix WP-E01 translation plan identity setup`). Its scoped test diff is preserved in that commit.

The test-source change is limited to carrying the original manager through the fixture helper and using it with the cached plan:

```diff
- return model, center, plan, base, internal, tangent, accepted, base_trial, digest
+ return model, center, dofs, plan, base, internal, tangent, accepted, base_trial, digest
```

The four translation cases now unpack that returned manager instead of calling `model.dof_manager()` again. The other helper caller discards the additional returned field and keeps its separate DOF construction only for fixed-index inspection; it does not pair that new object with the cached assembly plan.

## Supervised collection and execution

The exact parent command was:

```text
C:/Python313/python.exe -m experiments.wp_e01i_j2_diagnostic_supervisor
```

The supervisor performed guarded collection and then launched exactly one fixed-target pytest child. No unsupervised fallback or retry occurred. The pytest module was not edited between collection and execution.

| Control | Observed configuration / evidence |
|---|---|
| Test inventory | 12 exact authorized nodes; unchanged intended inventory |
| Result | 12 passed; 0 failed, skipped, xfailed, xpassed |
| Pytest elapsed | 5.97 s |
| Supervisor elapsed | 7.6170424 s |
| Child exit | 0; PID 37044 |
| Per-process committed-memory cap | 268,435,456 bytes |
| Job committed-memory cap | 268,435,456 bytes |
| Peak process / job committed memory | 103,591,936 / 103,591,936 bytes |
| Active process limit | 1 |
| BLAS threads | 1 |
| Timeout | No |
| Kill-on-close / breakaway | Enabled / disallowed |
| Cleanup | `VERIFIED_WINDOWS_JOB_CLOSED` |
| Automatic retry | Disabled; none occurred |

The supervisor queried and reported Job Object limits at runtime; this was committed-memory accounting, not an RSS claim. Collection and execution remained guarded by the fixed module, conftest, fixture, and node allowlist. Source review found no Gmsh/native FEM, public solver, network, worker, or test-side child-process path reachable from the selected tests.

### Exact observed node inventory

1. `test_j2_high_precision_fixed_history_tangent_diagnostic[tet4-perfect-free-center-mixed]`
2. `test_j2_high_precision_fixed_history_tangent_diagnostic[tet4-hardening-free-center-mixed]`
3. `test_j2_high_precision_fixed_history_tangent_diagnostic[tet4-perfect-weak]`
4. `test_j2_high_precision_fixed_history_tangent_diagnostic[tet4-hardening-weak]`
5. `test_j2_high_precision_fixed_history_tangent_diagnostic[hex8-perfect-weak]`
6. `test_j2_high_precision_fixed_history_tangent_diagnostic[hex8-hardening-weak]`
7. `test_j2_exact_translation_control_on_raw_internal_operator[tet4-perfect]`
8. `test_j2_exact_translation_control_on_raw_internal_operator[tet4-hardening]`
9. `test_j2_exact_translation_control_on_raw_internal_operator[hex8-perfect]`
10. `test_j2_exact_translation_control_on_raw_internal_operator[hex8-hardening]`
11. `test_historical_weak_direction_is_approximate_and_not_constraint_admissible[TET4]`
12. `test_historical_weak_direction_is_approximate_and_not_constraint_admissible[HEX8]`

Each full pytest node name is recorded in `wp_e01_k_execution_2026-10-21/raw_supervisor_output/execution/collection_nodes.json`.

## Translation evidence and interpretation

The four exact-translation controls apply `[0.125, -0.0625, 0.03125] m` uniformly to all nodes in the raw element/internal operator. They deliberately include prescribed-DOF components and do not apply constraint reduction. External and contact terms are excluded. Thus they test full-space rigid-translation invariance of the internal constitutive force and null action of the base tangent, not a reduced-space Newton perturbation.

| Family / hardening | Binary64 internal-force shift (N) | `||K t||` (N) | Proposed bound (N) | Decimal force shift (N) | Decimal relative shift | Force shift / bound | `||K t||` / bound |
|---|---:|---:|---:|---:|---:|---:|---:|
| TET4 / 0 Pa | 3.6323380922354273e-6 | 6.410755948900581e-6 | 0.051283824970166224 | 0 | 0 | 7.0828e-5 | 1.2501e-4 |
| TET4 / 1.5e9 Pa | 3.6780437697741085e-6 | 8.698194669225073e-6 | 0.051283824970166224 | 0 | 0 | 7.1719e-5 | 1.6961e-4 |
| HEX8 / 0 Pa | 2.0397180595563474e-6 | 6.178184780902394e-6 | 0.08882619045479737 | 5.7337695384450185e-70 | 1.16007018315294e-78 | 2.2963e-5 | 6.9554e-5 |
| HEX8 / 1.5e9 Pa | 2.0474596744947455e-6 | 6.7336969088211305e-6 | 0.08882619045479737 | 5.6709917783400110e-70 | 1.14705004641258e-78 | 2.3050e-5 | 7.5808e-5 |

All four controls passed their stated assertions: internal force shift and tangent null action were below the test's proposed binary64 bounds; accepted-state digest equality held; element state counts and production/Decimal branch identities were preserved; and Decimal force invariance met the proposed `1e-65` relative limit. Those bounds remain test proposals, not Owner-approved tangent thresholds.

Adding a uniform translation leaves the continuum deformation gradient and strain unchanged. The tests observed force invariance and `K t`; they did **not** emit a direct strain-difference metric, a digest string per translation case, or the difference between tangent matrices evaluated at translated and base states. These quantities are NOT_RECORDED. The Decimal TET4 force shift was exactly zero in Decimal arithmetic for both tested histories; the HEX8 shifts were approximately `5.7e-70 N`.

### Full-space versus reduced-space direction

The other two characterization nodes confirm that the historical weak directions are only approximately uniform translations: their unit-normalized distance to exact translation was `9.998905183280703e-16 m` (TET4) and `1.0066655652116372e-15 m` (HEX8). Their norms on prescribed DOFs were `0.9428090415820634` and `0.9813067629253164`, respectively. They are not members of the supported free-DOF reduced space. A raw full-space translation control therefore cannot turn them into admissible Newton directions.

Prior reported weak-direction local relative differences were 6.74–11.03%. Their absolute differences were of the same micro-newton order as the measured `K t` actions. The current exact-translation tests do not decompose a weak vector into translation and admissible components, nor compare the shifted tangent matrix to the original. Consequently they do not identify whether the earlier weak-direction discrepancy is due to cancellation, finite-difference resolution, a tangent inconsistency, or a combination. No weak-direction discrepancy is reclassified as resolved.

The six fixed-history Decimal derivative diagnostics and two TET4 Richardson convergence diagnostics passed in this corrected run as well; they remain bounded derivative evidence for their tested cases. They do not validate the preceding plastic-history evolution or all assembled directions.

## Independent review

A separate read-only reviewer examined the correction, observed output, mathematical scope, and evidence limitations. The reviewer agreed that the manager/plan fix is valid and that the corrected run supports only the raw full-space translation controls. The reviewer also confirmed that the tests do not resolve prior weak-direction mismatches: the vectors differ, prescribed components are large, and the translation null-action scale is comparable to the prior absolute mismatch scale. This was an independent review of the evidence, not scientific gate approval.

## Evidence files and hashes

The raw supervisor output is preserved under `qualification/0_2_12/wp_e01_k_execution_2026-10-21/raw_supervisor_output/`:

| File | SHA-256 |
|---|---|
| `preflight.json` | `106B75CADDF8FE4E0CD5AE33C51F6AABC3AFD67AB5508FAD170546272C8CC037` |
| `summary.json` | `9FEEC209DD51295F94A0290943BBF9655A58CCB1A99E12D11517B5328EC9F0EE` |
| `execution/collection_nodes.json` | `D5ED0E79A92C64C436C219A55635E144448CE6EA29C3C47EEB41A5A470FA151B` |
| `execution/phase_result.json` | `40D3C41E0BE84602C6BF7EF915709DA0A4ABC03194C950E2FA24C50C14962CC9` |
| `execution/stderr.log` | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` |
| `execution/stdout.log` | `B67301E6C7DF0E61F59CD85F377B041907F02F8F0AF55D4E27434B1E5BFCCE22` |

Final execution manifest: `qualification/0_2_12/wp_e01_k_rigid_translation_execution_manifest_2026-10-21.json`  
SHA-256: `9E48A5D8F0DA55122B5CB4946BC0C4D8E3753212AB712AD97A6DE1A56ADCD4F5`.

The manifest records the original historical hashes, corrected executable hashes, exact node inventory, guarded runtime result, process limits and evidence hashes. It was updated after execution to replace stale pending fields with observed collection and result data; that documentation-only update did not alter the executed module, registry, guard, supervisor, or the preserved logs.

## Conclusion and next Owner decision

The setup defect is corrected and the exact-translation controls are `VERIFIED_BOUNDED` for the tested raw internal operators. The scientific status remains:

- `WEAK_DIRECTION_RESOLUTION`: **PARTIAL / UNRESOLVED**
- `J2_ASSEMBLED_TANGENT_CONSISTENCY`: **BLOCKED_PENDING_INDEPENDENT_EVIDENCE**
- `J2_TANGENT_SCIENTIFIC_GATE`: **NOT_APPROVED**
- `GLOBAL_ASSEMBLY_VNV`: **PARTIAL**

The next useful GO is a separately hash-bound test of a perturbation constructed only from free DOFs, on the same fixed accepted J2 history, with a branch-preserving step sweep and independent Decimal force-difference oracle. It should report the reduced direction's norm, tangent action, finite-difference plateau, branch margins, absolute/global/local errors, and accepted-state digest before and after. Keep the raw full-space translation control as a separate invariance test. Do not activate production Newton/Armijo or freeze a tangent gate under that test authorization.

## Required status

```text
RESOURCE_SUPERVISOR: VERIFIED_FOR_CAMPAIGN
TRANSLATION_TEST_SETUP: CORRECTED
RIGID_TRANSLATION_VNV: VERIFIED_BOUNDED
J2_HIGH_PRECISION_ORACLE: PREVIOUS_6_PASS_BOUNDED
TET4_RICHARDSON_CONVERGENCE: PREVIOUS_2_PASS_BOUNDED
WEAK_DIRECTION_RESOLUTION: PARTIAL / UNRESOLVED
J2_ASSEMBLED_TANGENT_CONSISTENCY: BLOCKED_PENDING_INDEPENDENT_EVIDENCE
J2_TANGENT_SCIENTIFIC_GATE: NOT_APPROVED
GLOBAL_ASSEMBLY_VNV: PARTIAL
INCREMENTAL_NEWTON_FEM: NOT_RUN
PRODUCTION_ARMIJO_CERTIFICATE: NOT_VERIFIED
NATIVE_FEM_VNV: NOT_RUN
SCIENTIFIC_QUALIFICATION: NOT_ACQUIRED
WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET
```
