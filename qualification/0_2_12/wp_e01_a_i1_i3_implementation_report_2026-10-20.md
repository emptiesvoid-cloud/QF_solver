# QF Solver v0.2.12 — WP-E01-A I1–I3 Implementation Report

- **Date:** 2026-10-20
- **Worktree:** `C:\wpc01-frictionless-public-integration-wt\wp-e01`
- **Branch:** `codex/qf-wp-e01-a-implementation-20261020`
- **Verified implementation baseline:** `b5726699160f5e094d477b60b276fa7a080aada0`
- **Scientific authority:** [Owner-approved WP-E01-A scientific freeze](wp_e01_a_owner_scientific_freeze_2026-10-20.md)
- **Scope:** I1 Newton residual/correction, I2 Armijo and load control, I3 transactions/checkpoints.

| Implementation slice | Commit |
| --- | --- |
| I1 residual and correction contract | `0f430fe16f1438e53d5f988db5a23bd47037a1ef` |
| I2 Armijo, cutback, normalized load control, opt-in integration | `457eae2c5cafb478cd5e543b8ef2fbcdd4a92c38` |
| I2 preserve result-schema compatibility when opt-in is false | `6f872f24d93de798552ef256ce2de37bcf8b90e3` |
| I3 WP10 v2 metadata persistence seam | `b4a90d2b38880ff4b601399eef9a746a3b366e83` |
| I3 checkpoint identity and continuation-state validation | `c46e56b82f6532a8cf2aedecb281fdeabf77b2ac` |

This report records implementation on an isolated branch. The frozen experimental contract was not changed. Implementation correctness has not been established by execution, and this work does not qualify a route.

## Contract-to-code traceability

| Requirement | Implementation | Source status / limitation |
| --- | --- | --- |
| I1 free-DOF residual `R_f = f_target,f - f_internal,f`; `||R_f||₂ ≤ 1e-8 max(||f_target,f||₂,F_ref)+F_abs` | `e01a.py`, `driver.py` | Implemented behind `experimental_wp_e01_a: true`. `F_ref` is mandatory, `F_abs` defaults to `0 N`, and scales plus target force are checked for finiteness and a positive `S_F`. The caller must declare a physically meaningful load-pattern envelope; source code records the value as a case declaration but cannot independently prove its physical provenance. |
| Prescribed displacement boundary and reaction exclusion | `solver.py`, `e01a.py`, `driver.py` | Free DOFs are reduced before the norm. The existing model represents homogeneous fixed DOFs; nonzero constrained displacement states and unsupported MPC/RBE/contact constraints fail closed. No-free-DOF models fail closed. |
| 25 Newton correction updates and post-update residual verification | `driver.py` | Implemented for the opt-in route. The initial residual is not counted. The route evaluates the residual after update 25 before converging or reporting the finite iteration-limit failure. The existing non-E01-A path retains its prior iteration logic. |
| Explicit invalid/nonfinite state and nonconvergence handling | `e01a.py`, `driver.py`, `load_control.py` | Trial and converged states are validated; invalid state is terminal. Nonfinite residuals/corrections and finite iteration-limit failures carry explicit failure reasons/diagnostics. |
| Normalized Armijo merit, verified descent, `c1=1e-4`, 13 trials | `e01a.py`, `load_control.py`, `driver.py`, `solver.py` | The helper uses `T_R=1e-8 S_F+F_abs`, `φ=½||R_f/T_R||₂²`, `Dφ[p]=R_fᵀJ_Rp/T_R²`, requires finite `Dφ[p]<0`, and tests `α=2^-k`, `k=0…12`. Candidate residuals use the same accepted increment-base material state. The derivative-certificate registry is empty, so `newton_line_search` fails closed for every route pending independent route-specific evidence. No J2 tangent is used as a certificate. |
| Cutback, minimum, endpoint, rejection limit | `e01a.py`, `load_control.py`, and the targeted remediation below | Uses the frozen `β=0.5`, `Δλ_min=1e-4 Δλ₀`, exact `λ=1` clipping and maximum 25 global rejections. No 26th attempt is started. A failed clipped final increment terminates incomplete. Typed admissibility evidence now passes through contribution composition only when every inadmissible response supplies a positive finite normalized increment bound below the actual attempted increment and the driver has validated the trial state. Unknown or untyped failures remain terminal. |
| Trial/accepted isolation, rollback, exactly-once outer commit | Existing `NonlinearStateTransaction` / `UnifiedContinuationController`, plus `load_control.py` | Reuses detached composite-state transactions. Rejected attempts compare the accepted-state digest before and after rollback. The accepted displacement/material/contact/continuation state is published only after converged state and result checks; accepted material state is copied once at the outer increment commit. |
| Additive WP10 v2 checkpoint subrecord and restart ledger | `e01a.py`, `load_control.py`, `checkpoint.py` | Stores versioned `qf_wp_e01a` identity, formulation/profile, load path, accepted state digest and coordinate, step, initial/minimum/next increments, attempt intent, rejection ledger, and restart provenance in WP10 v2 migration metadata and accepted state. Attempt intent is durably saved before trial work. A resumed in-progress attempt is restored to its accepted snapshot, counted once, persisted as terminal, and fails closed. Missing/mismatched/corrupt E01-A metadata fails closed. `force=False` preserves the existing WP10 save-frequency behavior; forced saves are used only by E01-A for write-ahead intent and accepted checkpoints. No historical checkpoint is rewritten. |
| Reproducible result marking | `solver.py` | Opt-in output labels the route `EXPERIMENTAL`, `NOT_INDEPENDENTLY_VERIFIED`, `NOT_ASSESSED`, records residual/load-path settings, and states that a numerical pass does not imply qualification. |

## Status distinctions

- `OWNER_APPROVED_EXPERIMENTAL`: the unchanged scientific contract in the Owner freeze record.
- `IMPLEMENTED`: source paths for the listed requirements are present on this branch.
- `NOT_IMPLEMENTED`: no built-in E01-A contribution currently emits typed increment-dependent admissibility evidence. The targeted remediation adds the typed propagation and fail-closed classifier path; until a supported contribution supplies such evidence, its inadmissibility remains terminal.
- `NOT_VERIFIED`: no numerical test, solver execution, checkpoint restart, or route-specific independent V&V was performed.
- `BLOCKED`: Armijo activation remains blocked for all routes until a route-specific residual derivative and descent certificate has independent evidence. `J2_TANGENT_CONSISTENCY` remains `BLOCKED_PENDING_INDEPENDENT_EVIDENCE`.

### I1 — Newton residual and convergence

**Source implementation: IMPLEMENTED.** The experimental API is opt-in and requires SI units, `e01a_force_reference_n`, and `e01a_initial_load_increment`. `e01a_absolute_force_tolerance_n` is optional and defaults to zero. A zero or invalid effective force scale fails closed. Correction-size diagnostics do not replace the residual gate.

### I2 — Armijo, cutback, and load path

**Source implementation: IMPLEMENTED; derivative-certified line-search activation: BLOCKED.** The experimental `newton_raphson` route can use the new residual/load-control behavior without Armijo. The `newton_line_search` route cannot proceed until its route key has an independently reviewed certificate. The certificate registry is intentionally empty. No retry occurs for an unverified or non-descending direction.

### I3 — Transactions and checkpoints

**Source implementation: IMPLEMENTED; restart behavior: NOT_VERIFIED.** WP10 v2 remains the container and its legacy save-frequency behavior is unchanged unless the E01-A caller requests a forced write-ahead save. E01-A restart without its own complete metadata subrecord or with inconsistent mirror/state identity is refused. Interrupted attempts are terminal after one persistent rejection entry; they are not silently replayed.

## Focused test preparation

Added [`tests/unit/test_wp_e01a_policy.py`](../../tests/unit/test_wp_e01a_policy.py) and a hash-bound `NUMERICAL_UNIT` safety-registry entry in [`tests/conftest.py`](../../tests/conftest.py). The initial implementation snapshot recorded an incorrect digest; the current test source SHA-256, also bound by the safety registry, is `FBEBAA51ABA43CAC7900C4490B06BF9CE275A930E44AB19497B877CFB2F0739B`.

The prepared checks cover the free-DOF residual convention and force scaling, zero/missing scales, the 25-update/post-update source path, refusal of arbitrary Armijo certificate labels and the exact 13-trial profile without activating any route certificate, typed contribution inadmissibility propagation, narrow retry classification, minimum/cutback/endpoint helpers, supported constraints, detached transaction rollback and commit count, checkpoint schema/path/state identity refusal, write-ahead intent/restart guard source paths, global rejection budget ordering, result-check-before-commit ordering, and opt-in/default control metadata.

These tests were **not run**. They do not execute model assembly, the solver entry point, a checkpoint store/restart, FEM, or a subprocess. Therefore actual nonlinear trajectories, rollback under a real material update, checkpoint atomicity/restart equivalence, and route-specific Armijo derivative accuracy remain unverified. The repository's native execution guards were not changed.

## Static checks and compatibility review

- `python -m py_compile` succeeded for the changed Python source and prepared test file. This was syntax compilation only.
- `git diff --check` succeeded.
- No `pytest`, numerical test, solver, `solve_model`, FEM assembly, backend, worker, or subprocess execution was performed.
- Source review confirms `experimental_wp_e01_a` defaults to `false`; new `UnifiedNewtonEngine` arguments default to `None`; the legacy residual floor/convergence branch and legacy load-control defaults remain on the existing path. This is source-level compatibility evidence only, not runtime verification.

## Remaining verification risks

1. Independently verify `J_Rp`, its sign, and finite negative descent for each route before adding any derivative certificate. No Armijo route is enabled now.
2. Independently verify free-DOF equilibrium accuracy, force-unit scaling, the final correction check, and exact endpoint behavior against analytical or independent references.
3. Exercise every retry/terminal failure class under future explicit V&V authorization, including the 25-rejection boundary and clipped-final-step failure.
4. Verify real transaction rollback, state digest invariance, write-ahead durability, interruption handling, checkpoint corruption refusal, and same-path restart equivalence. Prepared source checks do not establish these behaviors.
5. A case-provided `F_ref` value can be validated as finite and positive in the effective scale; its physical representativeness remains a case declaration requiring review.
6. No J2 tangent, Full Newton J2, or general nonlinear FEM qualification claim is made. No J2 energy field or historical `plastic_dissipation` interpretation was changed.

## Final status

- `WP_E01_A_I1: IMPLEMENTED`
- `WP_E01_A_I2: IMPLEMENTED` (`newton_line_search` remains fail-closed pending route-specific derivative evidence)
- `WP_E01_A_I3: IMPLEMENTED` (not independently verified)
- `FROZEN_EXPERIMENTAL_CONTRACT: PRESERVED`
- `OFFLINE_TESTS: PREPARED_NOT_RUN`
- `DEFAULT_API_COMPATIBILITY: VERIFIED_BY_SOURCE`
- `NUMERICAL_VNV: NOT_RUN`
- `NATIVE_FEM_AUTHORIZED: NO`
- `J2_TANGENT_CONSISTENCY: BLOCKED`
- `WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET`

The implementation branch is not merged. No qualification or release status has changed. Wait for separate Owner authorization before test execution or additional numerical work.

## Targeted implementation remediation — 2026-10-20

Owner-authorized follow-up addressed the independent implementation-review findings without changing the frozen scientific contract:

* `ContributionResponse` now carries an optional typed `E01AIncrementDependentAdmissibility`; composition preserves evidence and records any untyped inadmissible component. The Newton driver emits retry evidence only after its E01-A trial-state validation and only when every failing component's finite positive maximum normalized increment is strictly below the actual attempted increment. The retry classifier accepts only the resulting versioned diagnostic under material/contact admissibility failure reasons. Untyped, malformed, nonfinite, stale-bound, mixed typed/untyped, unknown, unsupported, singular, and invalid-state failures stay terminal. The existing load controller still rolls back and verifies the accepted-state digest before classification, and the global rejection budget is unchanged. No current built-in E01-A contribution produces the new evidence yet; therefore no present material/contact case gains an unverified retry path.
* The Armijo helper now requires both the route identity and the exact certificate value registered for that route. The registry is immutable and remains empty. No route certificate was added; `J2_TANGENT_CONSISTENCY` remains blocked.
* Opted-in E01-A now rejects `adaptive_load_steps=true`. Results distinguish requested legacy line-search controls from the effective E01-A profile and state that those legacy values are not applied. The opt-in default remains false, and legacy behavior outside E01-A is unchanged by source inspection.
* Focused test preparation adds typed-response composition and failure-bound checks, rollback-before-classification ordering, and checkpoint schema/path/state-identity refusal. Checkpoint I/O, interruption recovery, and restart equivalence remain `NOT_VERIFIED` because no test or solver execution was authorized here.

The test source was rehashed and its `NUMERICAL_UNIT` registry binding updated together. Current test SHA-256: `FBEBAA51ABA43CAC7900C4490B06BF9CE275A930E44AB19497B877CFB2F0739B`. Tests remain `PREPARED_NOT_RUN`; only AST parsing and `git diff --check` are permitted and recorded for this follow-up.

**Remediation disposition:** `E01_A_RETRY_CLASSIFICATION=FIXED_BY_SOURCE`; `E01_A_ARMIJO_FAIL_CLOSED=PRESERVED`; `E01_A_LEGACY_OPTIONS=RESOLVED`; `E01_A_CHECKPOINT_RUNTIME=NOT_VERIFIED`; `OFFLINE_TESTS=PREPARED_NOT_RUN`; `E01_A_IMPLEMENTATION_ACCEPTANCE=PENDING_VERIFICATION`. WP-E01 remains `OPEN / EXPERIMENTAL_TARGET`.
