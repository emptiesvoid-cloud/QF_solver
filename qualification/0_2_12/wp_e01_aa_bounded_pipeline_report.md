# WP-E01-AA — Supervised Newton COLLECT → RUN report

Date: 2026-10-21  
Worktree: `C:\wpc01-frictionless-public-integration-wt\wp-e01-x`  
Branch: `codex/wp-e01-x-newton-test-remediation-20261021`  
Frozen execution HEAD: `580f39c157bcce4e8716c0ff0c2c45ff856aa588`  
Origin: `https://github.com/emptiesvoid-cloud/QF_solver.git`

## Result

The authorized two-phase pipeline completed at the frozen source HEAD. COLLECT accepted the exact 16-node allowlist. The conditional RUN then executed those same 16 nodes once under the fixed-target Windows Job Object supervisor: **16 passed, 0 failed, 0 skipped, 0 xfailed, 0 xpassed, 0 interrupted**. There was no retry and no source or test change between phases.

This is bounded evidence for the experimental single-element TET4/HEX8 affine Hencky Newton fixtures. It is not general FEM or production Newton qualification.

## Frozen identities and execution profile

| Item | SHA-256 |
|---|---|
| Static execution manifest | `1f8f423e7347f1b1ce4a58b73b3907b73e35199060185982b3dd0fec79ce56bc` |
| Newton test module | `5ad19f7e563efc4ae2f40805c7d8b15c4cb59b32136b185b6147349b4d3ff0a2` |
| Safety registry (`tests/conftest.py`) | `113f5c6267689e31df3b73fa3f333421488967b1358085809a8da8dfd20de9e3` |
| Collection guard | `e5ea3bbe695c4380a5445694f62e0c2cc415ab361faf6f85d1171ed463d41ccb` |
| Fixed-target supervisor | `d3986e408a9e9739165cc1f01e52cbddddb6fcf012f26601e30511373c957892` |
| Windows Job Object helper | `76e71e833280b92c2478ec8aed187a473bf5f4002e5983c2386f37b58e9bbe62` |
| RUN runtime manifest (archived) | `dde8abe998ad3a4842d19bad1040cf1134b38c57cb6163745b1c05896e5da70d` |

The runtime profile pinned source commit `580f39c…a588`, the static manifest and 36 runtime source hashes. All source pins matched at the RUN preflight. Its only differences from the accepted COLLECT snapshot were the authorized phase transition and accepted-collection binding. The profile fixed Python 3.13.1, pytest 8.4.1, NumPy 2.2.6, SciPy 1.15.2, psutil 7.2.2, plugin autoload disabled, one BLAS thread and no parallel pytest.

The two parent invocations, each used once, were:

```text
C:/Python313/python.exe -m experiments.wp_e01uvw_newton_supervisor --phase collect
C:/Python313/python.exe -m experiments.wp_e01uvw_newton_supervisor --phase run
```

The RUN child was the frozen pytest command for only `tests/unit/test_wp_e01uvw_newton.py`, with the registered collection guard. No direct/unsupervised pytest, unrelated module, public solver, native backend, Gmsh, network operation or worker was used.

## Collection and node inventory

COLLECT completed naturally with exit code 0 and an accepted v2 receipt. It observed exactly the authorized 16 nodes:

1. `test_incremental_equilibrium_matches_independent_affine_hencky_reference[tet4]`
2. `test_incremental_equilibrium_matches_independent_affine_hencky_reference[hex8]`
3. `test_final_equilibrium_is_independent_of_admissible_load_partition[tet4]`
4. `test_final_equilibrium_is_independent_of_admissible_load_partition[hex8]`
5. `test_small_strain_solution_approaches_linear_hencky_limit`
6. `test_unattainable_excessive_load_fails_without_fabricating_equilibrium`
7. `test_failed_second_increment_preserves_last_accepted_equilibrium`
8. `test_iteration_limit_refuses_increment_without_changing_accepted_state`
9. `test_singular_reduced_tangent_refuses_and_preserves_initial_state`
10. `test_residual_merit_backtracking_records_rejected_full_step`
11. `test_invalid_trial_is_rejected_then_smaller_admissible_step_is_selected`
12. `test_wrong_mesh_accepted_state_fails_closed`
13. `test_same_mesh_non-equilibrium_state_is_not_accepted_as_restart`
14. `test_load_step_count_and_order_are_bounded`
15. `test_reduced_increment_embedding_has_zero_prescribed_components`
16. `test_initial_state_must_be_in_free_space_equilibrium`

Full pytest node IDs, including module path, are preserved in `collection_nodes.json` and `run_results.json`. The RUN structured report has 48 lifecycle records (setup, call, teardown for each node); every record passed. The supervisor reconciled those records with pytest exit 0 and console output `16 passed in 6.62s`.

The previous WP-E01-Z attempt remains a precheck-blocked event, not a numerical run: it used a collection bound to an older HEAD. WP-E01-AA performed this fresh accepted collection at `580f39c…a588`, resolving that identity mismatch without changing scientific source. The historical Stage V result of 13 PASS / 3 FAIL remains preserved and was not rerun or rewritten.

## Bounded numerical measurements

Both physical equilibrium fixtures are single-element, dead-load affine uniaxial Hencky examples with exactly one free UX degree of freedom. At load factors 0.25, 0.5, 0.75 and 1.0, both converged in three Newton corrections per increment; every converged physical step used the full correction (`alpha=1`). The independent target uses the diagonal Hencky PK1 formula and hand-integrated tributary area; the iterative residual and tangent use the experimental global assembler.

| Fixture | Final free residual (N) | Residual limit (N) | Analytic displacement error (m) | Force closure (N) | Moment closure (N·m) |
|---|---:|---:|---:|---:|---:|
| TET4 | `7.254129741e-9` | `1.118492362e-6` | `5.893896482e-14` | `7.254129741e-9` | `0` |
| HEX8 | `7.162270776e-11` | `1.672738543e-6` | `5.342948306e-16` | `7.185125068e-11` | `1.063442990e-13` |

The small-strain relative linear-limit errors were `1.498168748e-3` and `7.495419263e-4` for the two tested strain amplitudes; the test's decreasing-error assertion passed.

Fail-closed and rollback scenarios also passed. The excessive-load TET4 case ended with `LINE_SEARCH_FAILED`, residual `1.107570942e6 N` against a `1.108502362e-3 N` limit, after nine rejected trial steps; the accepted-state identity remained recorded. The invalid-trial rollback case preserved the exact accepted-state digest (`b8d3d0…d3d6`) before and after rejection, with previous residual `1.828449586e-12 N`. Iteration-limit and singular-reduced-tangent cases returned their intended refusal statuses. Other malformed-state/restart and load-sequence guards passed.

The run therefore demonstrates a physical terminal rejected-trial sequence, but **not** successful physical backtracking to a smaller accepted step: convergent physical paths all used `alpha=1`. The separate backtracking and invalid-trial helper tests use synthetic scalar behavior.

## Newton sign and scope

For the tested displacement-independent dead loads, the canonical residual is

`R(u, λ) = F_int(u) − λ F_dead`, with `K_t = dR/du`.

The reduced Newton equation is `K_ff Δu_f = −R_f`, where `K_ff = P_fᵀ K_t P_f`. This agrees with the experimental driver and its free-DOF embedding. Follower/displacement-dependent loads are unsupported and would contribute an external-load derivative to the residual Jacobian.

Accepted state is immutable in-memory displacement/load data only. No material-history state, persistent checkpoint/restart, crash durability, contact, native FEM, public solver integration or general multi-DOF nonlinear model was verified. HEX8 positive determinant is sampled at its eight 2×2×2 Gauss points, not certified everywhere in the element. Residual-merit backtracking is not total-potential energy globalization and is not a production Armijo certificate. All numerical tolerances remain proposed; scientific qualification is not acquired.

## Evidence and containment

Collection receipt SHA-256: `ef4f60942cd8510ba2bd249643c7e044f93da68cffc4475a3831731b43359fa9`.  
Collection node inventory SHA-256: `3a3efcabc6634f7bebbf4bc68ed2979ec5c65ef4cbae6a25aa5e4a1d0d5e61a0`.  
Collection evidence index SHA-256: `f1ffbf518b0687b5eede7c3360dccce1df8e1121bc1e662628e57959aec950ef`.  
Collection runtime snapshot SHA-256: `0727521211942e3ccff3265afaa28403ce844a0a7fa3336321a8984f21369403`.

RUN summary SHA-256: `0343480f2b38d2de3a723b15e4d34f21723a8f46200827467c26ee106c159f43`.  
Structured node results SHA-256: `a6835f26f7292a303cc51402e9164585ea2fef7eddd6ea092cf48df3f5fde177`.  
RUN phase result SHA-256: `2fbceaa7d98fdea77d8045ebb0520968dd90e67b6ec26146da75fea0d583d785`.  
RUN evidence index SHA-256: `aa68445a013fcc7023f6b71b316da13bbe22f5dfb24d73febdb2d9107f214933`.  
RUN stdout SHA-256: `b993e2edd7a3a2936ded8d1dc70b6f39128707e83697bf32d2a2a5e51d33f54b`.  
RUN stderr SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty).

The RUN Job Object readback showed one active process, 268,435,456-byte per-process and job committed-memory caps, 120-second parent deadline, kill-on-close enabled, breakaway disabled. Child PID `37352` exited 0 after 7.4002 seconds; peak process and job committed memory were each 85,741,568 bytes. No timeout or failure was reported; no PID remained after exit; cleanup was `VERIFIED_WINDOWS_JOB_CLOSED`. The collection phase likewise had natural exit 0, 16 accepted nodes, 1.6506-second parent duration, 52,563,968-byte peak commitment, empty post-exit PID set and verified cleanup. No automatic retry occurred.

The full raw logs, preflights, receipts, runtime snapshot, structured results, phase records and evidence indexes are preserved in `qualification/0_2_12/wp_e01_x_newton_execution_2026-10-21/20261021T200339Z/`. The RUN profile used is preserved separately at `qualification/0_2_12/wp_e01_aa_run_runtime_manifest_2026-10-21.json`; the tracked reusable runtime profile was restored after the one-use run so its committed source identity is not left pointing at a transient execution state.

## Independent review

A distinct reviewer (`/root/wp_e01x_review`) performed read-only post-run review; no tests were run and no files were changed. The reviewer independently confirmed the exact node set, 48 passing lifecycle reports, consistency between structured counts and console output, accepted receipt and runtime bindings, evidence-index contents/digests, Job Object limits, timing, process accounting and cleanup. No P0/P1 scientific or safety issue was found.

One P2 reporting correction is recorded here: a prior static limitation phrase that physical Newton line-search rejection was not demonstrated would be overbroad for this run. The excessive-load TET4 path did reject nine physical trials before terminal failure. However, no physical rejected-then-smaller-accepted globalization step occurred. This narrows the wording; it does not alter the test or scientific gate.

## Status

- `WP_E01_AA_COLLECTION`: **ACCEPTED — 16/16 exact nodes**
- `WP_E01_AA_EXECUTION`: **PASS — 16/16**
- `INCREMENTAL_NEWTON`: **VERIFIED_BOUNDED for the tested one-free-DOF TET4/HEX8 affine dead-load paths; otherwise PARTIAL**
- `PHYSICAL_TERMINAL_TRIAL_REJECTION`: **OBSERVED — 9 rejected TET4 trials before failure**
- `PHYSICAL_REJECTED_THEN_ACCEPTED_BACKTRACKING`: **NOT_OBSERVED**
- `PRODUCTION_ARMIJO_CERTIFICATE`: **NOT_VERIFIED**
- `NATIVE_FEM_VNV`: **NOT_RUN**
- `SCIENTIFIC_QUALIFICATION`: **NOT_ACQUIRED**
- `WP_E01_STATUS`: **OPEN / EXPERIMENTAL_TARGET**

Next milestone: expand bounded synthetic Newton V&V beyond one free degree of freedom and add an independently measured physical case that rejects a full step and accepts a smaller one, while retaining route isolation. Checkpoint/restart, crash durability, production integration and any Armijo certificate require separate authorization.
