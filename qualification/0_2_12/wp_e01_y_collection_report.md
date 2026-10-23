# WP-E01-Y â€” Supervised Newton Test Collection

## Result

The one-use `GO-COLLECT` was accepted for the exact WP-E01-X Newton target. The fixed-target supervisor collected **16/16 authorized node IDs** and did not run test bodies. The supervisor summary records `test_execution=NOT_RUN`, `run_launched=false`, and `automatic_retry=false`.

| Gate | Result |
|---|---|
| Repository / source identity | PASS â€” authorized source HEAD and all frozen pins matched |
| Collection guard | PASS â€” target remained `NUMERICAL_UNIT` |
| Observed inventory | PASS â€” 16 exact nodes matched the static allowlist |
| Job Object containment | PASS â€” one process, limits read back, no breakaway |
| Natural completion / cleanup | PASS â€” child exit 0, no timeout, Job closed |
| Collection evidence receipt v2 | PASS â€” accepted and hashes reconciled |
| Newton RUN / test bodies | NOT RUN |

## Baseline and scope

- Worktree: `C:\wpc01-frictionless-public-integration-wt\wp-e01-x`
- Branch: `codex/wp-e01-x-newton-test-remediation-20261021`
- Source commit at collection: `ec96b6b7be084dc114077a88f4c2d0e9327b71ca`
- Origin: `https://github.com/emptiesvoid-cloud/QF_solver.git`
- Static manifest SHA-256: `1f8f423e7347f1b1ce4a58b73b3907b73e35199060185982b3dd0fec79ce56bc`
- Runtime COLLECT manifest SHA-256: `21b3ffc433b833f020d3da53b124a59d9b7668ff861838ab939794fb9601def9`
- Static source map: 34 exact pins. Runtime map: 36 entries, consisting of the static map plus the guard and supervisor pins; the existing Job Object helper pin was confirmed identical.
- Before collection, all 34 static pins matched file bytes, the worktree had no tracked changes, the fixed evidence directory did not exist, and the C: volume had 37,002,731,520 bytes free.

The generated runtime manifest is fixed to `execution_phase=COLLECT`, `accepted_collection=null`, and `automatic_retry=false`. It binds the fixed repository, target, `NUMERICAL_UNIT` registry classification, static manifest, source map, Python environment, resource limits and evidence directory.

## Preflight and command

The only parent command launched was:

```text
C:/Python313/python.exe -m experiments.wp_e01uvw_newton_supervisor --phase collect
```

The supervisor source fixes the child to Python 3.13.1 with pytest 8.4.1, NumPy 2.2.6, SciPy 1.15.2, psutil 7.2.2, plugin autoload disabled, one BLAS thread and no parallel pytest. Its `_preflight` verified repository identity, all runtime pins, test registry AST binding, and the static safety review. The child invocation was constructed internally with `-S`, the frozen collection guard, `--collect-only`, and only `tests/unit/test_wp_e01uvw_newton.py`.

The import/collection review had no reachable public solve, `solve_model`, native FEM, Gmsh, network or numerical worker path. The target and registry hashes remained those in the frozen source manifest. The 22-case reporting-simulation module remained pinned `PURE_UNIT` at its previously reviewed hash; its historical **22/22** result was not rerun in this collection campaign.

## Observed nodes

The guarded collection output reports `16 tests collected in 1.02s` and exactly the frozen nodes:

1. `tests/unit/test_wp_e01uvw_newton.py::test_incremental_equilibrium_matches_independent_affine_hencky_reference[tet4]`
2. `tests/unit/test_wp_e01uvw_newton.py::test_incremental_equilibrium_matches_independent_affine_hencky_reference[hex8]`
3. `tests/unit/test_wp_e01uvw_newton.py::test_final_equilibrium_is_independent_of_admissible_load_partition[tet4]`
4. `tests/unit/test_wp_e01uvw_newton.py::test_final_equilibrium_is_independent_of_admissible_load_partition[hex8]`
5. `tests/unit/test_wp_e01uvw_newton.py::test_small_strain_solution_approaches_linear_hencky_limit`
6. `tests/unit/test_wp_e01uvw_newton.py::test_unattainable_excessive_load_fails_without_fabricating_equilibrium`
7. `tests/unit/test_wp_e01uvw_newton.py::test_failed_second_increment_preserves_last_accepted_equilibrium`
8. `tests/unit/test_wp_e01uvw_newton.py::test_iteration_limit_refuses_increment_without_changing_accepted_state`
9. `tests/unit/test_wp_e01uvw_newton.py::test_singular_reduced_tangent_refuses_and_preserves_initial_state`
10. `tests/unit/test_wp_e01uvw_newton.py::test_residual_merit_backtracking_records_rejected_full_step`
11. `tests/unit/test_wp_e01uvw_newton.py::test_invalid_trial_is_rejected_then_smaller_admissible_step_is_selected`
12. `tests/unit/test_wp_e01uvw_newton.py::test_wrong_mesh_accepted_state_fails_closed`
13. `tests/unit/test_wp_e01uvw_newton.py::test_same_mesh_non_equilibrium_state_is_not_accepted_as_restart`
14. `tests/unit/test_wp_e01uvw_newton.py::test_load_step_count_and_order_are_bounded`
15. `tests/unit/test_wp_e01uvw_newton.py::test_reduced_increment_embedding_has_zero_prescribed_components`
16. `tests/unit/test_wp_e01uvw_newton.py::test_initial_state_must_be_in_free_space_equilibrium`

No test pass/fail counts are reported because collection does not execute test bodies.

## Runtime containment

The Job Object was configured and read back before child resume:

- Process committed-memory cap: 268,435,456 bytes.
- Job committed-memory cap: 268,435,456 bytes.
- Active-process limit: 1.
- Parent wall deadline: 120 seconds; observed phase duration: 1.7701 seconds.
- Peak process and job committed memory: 52,047,872 bytes each.
- PID after resume: `28452`; PIDs after exit: none.
- Child exit code: 0; timeout: false; failure: none.
- Kill-on-close: enabled; breakaway: disabled.
- Cleanup: `VERIFIED_WINDOWS_JOB_CLOSED`.

## Evidence and hashes

All raw collection artifacts are preserved under `qualification/0_2_12/wp_e01_x_newton_execution_2026-10-21/20261021T195229Z/`. The evidence index was independently recomputed; its complete file map matched the indexed map exactly. The receiptâ€™s evidence-index digest, summary digest and receipt digest all match.

| Artifact | SHA-256 |
|---|---|
| `collection_receipt.json` | `ab4d7f0fac08b2fdb877747eb7dc681af35d232507a55208e326a35616a1edd8` |
| `collection_nodes.json` | `3a3efcabc6634f7bebbf4bc68ed2979ec5c65ef4cbae6a25aa5e4a1d0d5e61a0` |
| `collect_evidence_hashes.json` | `2b4af90c20e692fe8aec21fbdb29a628db5482c7ee04299c4e8114609a7d05bf` |
| `collect/phase_result.json` | `bb3463d2c0a514b05a06dff66bdbe60585675378d5a7960b2bd28dc9ad245c6e` |
| `collect_summary.json` | `941549a8da1e50690d6402e026fbf5fc71b85efcaf549ccc9d3a5f0bed5ac85b` |
| `collection_runtime_manifest.json` | `21b3ffc433b833f020d3da53b124a59d9b7668ff861838ab939794fb9601def9` |
| `preflight.json` | `4ef3b9a5b87e01b10ee82bcd9d339cb8c2fa449dcb40676314e72714acd5668c` |
| `collect/stdout.log` | `2253cfc3d60135ef9b9a104796b4c3c7d880ac67e6d3435e982f312313a2406e` |
| `collect/stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

Frozen source identities verified at launch:

| File | SHA-256 |
|---|---|
| `tests/unit/test_wp_e01uvw_newton.py` | `5ad19f7e563efc4ae2f40805c7d8b15c4cb59b32136b185b6147349b4d3ff0a2` |
| `tests/conftest.py` | `113f5c6267689e31df3b73fa3f333421488967b1358085809a8da8dfd20de9e3` |
| `experiments/wp_e01uvw_newton_collection_guard.py` | `e5ea3bbe695c4380a5445694f62e0c2cc415ab361faf6f85d1171ed463d41ccb` |
| `experiments/wp_e01uvw_newton_supervisor.py` | `d3986e408a9e9739165cc1f01e52cbddddb6fcf012f26601e30511373c957892` |
| `experiments/wpc01_exploratory_supervisor.py` | `76e71e833280b92c2478ec8aed187a473bf5f4002e5983c2386f37b58e9bbe62` |

The historical U/V/W report hash is `dc254d1228796023a04e98c690b45434c29c18bff35297550a0de7ab59fac9ff`. Its prior results remain unchanged: U 31/31 PASS; V 13 PASS / 3 FAIL; W read-only review complete. These were not rerun. The 22/22 reporting simulation result is also historical, not rerun.

## Independent review

A distinct read-only reviewer, `/root/wp_e01x_review`, independently checked the receipt v2, exact node inventory, evidence-index digest and recomputed map, phase result, process/limit/cleanup accounting, and explicit `test_execution=NOT_RUN` / `run_launched=false` state. The reviewer found no P0/P1/P2 issue. The review did not execute tests or modify files.

## Final status and next decision

- `WP_E01_COLLECTION`: **ACCEPTED**
- `NEWTON_RUN`: **NOT_RUN**
- `NEWTON_V&V`: **PARTIAL** â€” exact nodes are collected and frozen; numerical behavior remains unexecuted under this authorization.
- `SCIENTIFIC_QUALIFICATION`: **NOT_ACQUIRED**
- Historical Stage V: **13 PASS / 3 FAIL**, preserved; no failure was hidden or rerun.

The next Owner decision is a separate exact-path `GO-RUN` bound to this accepted receipt, runtime-manifest digest, source HEAD, and evidence directory. This collection authorization does not permit a Newton RUN.
