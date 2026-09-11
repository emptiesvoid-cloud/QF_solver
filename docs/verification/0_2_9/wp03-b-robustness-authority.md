---
doc_id: DOC-029-WP03-008
revision: 0.1
status: implementation_migration
applicable_version: 0.2.9-development
---

# WP03-B — unified stagnation and line-search authority

> **Targeted implementation evidence, not a release claim.** This step does
> not change FEM formulations, element kernels, accepted-state ownership or
> maturity. WP03 remains worth 0/7 points pending its independent closure.

## Scope and baseline

WP03-B was implemented from
`9a97025670f7fbb28cbe4c6e2e76eacbf9fc5714` on branch
`0.2.9-unified-nonlinear`. The executed baseline is recorded in
`qualification/0_2_9/wp03_b_baseline.json`.
The full WP03-A campaign record is intentionally not rewritten.

The baseline groups passed as follows: B01/B06 `11 passed`, B03/B04
`27 passed`, B05 `30 passed`, and B07/B12/B13/B14 `28 passed`. The B02 group
had `35 passed, 1 failed` because the pre-existing adversarial adaptive
rollback override does not accept the already-present `commit_to_inputs`
keyword. The relevant J2 control, excluding that one pre-existing failure,
was `35 passed, 1 deselected`. No value from that failure is treated as a
WP03-B pass.

After the production change, the complete B02 control was rerun and produced
the identical `35 passed, 1 failed` result with the same adaptive override
`TypeError`; the exclusion control remained `31 passed, 1 deselected`. The
step-up/WP03 guards and the WP03-B tests pass together (`35 passed`). This
confirms that the known adaptive signature debt is unchanged rather than
introduced by the robustness migration.

## Single robustness authority

`UnifiedNonlinearRobustnessController` in
`src/solveur/core/nonlinear/robustness.py` is the sole policy authority for:

- the four-sample free-DOF residual stagnation decision;
- NaN/Inf and convergence precedence;
- the alpha=1 then halving line-search policy;
- strict merit decrease and explicit Armijo acceptance;
- bounded floor/reduction handling; and
- deterministic policy/decision diagnostics.

`UnifiedNewtonEngine` consumes this controller. `solve_full_newton`, the
stateful load-control adapter and legacy line-search helpers delegate to the
same policy loop. A source scan finds one reduction loop in the controller,
no reduction loop in the compatibility helpers and no inline driver
stagnation loop. The controller never mutates accepted or trial nonlinear
state.

The public default is a four-sample, `1e-10` plateau decision and a strict
line search with `min_alpha=1e-4` and at most 12 reductions. Explicit
`NonlinearRobustnessOptions` are recorded as `EXPERIMENTAL_OVERRIDE`.
Historical direct helper defaults (`min_alpha=0`, `max_reductions=14`) remain
observable as `COMPATIBILITY_ADAPTER` configuration; they were not observed
to alter the easy baseline outcomes.

Adaptive increment/cutback consolidation and arc-length robustness remain
deferred to WP03-C/WP03-D. The state/transaction authority is unchanged.

## Gate status

| Gate | Status | Boundary |
| --- | --- | --- |
| G03-01 | **PARTIAL** | Fixed/load-control policy authority covered; continuation consolidation remains. |
| G03-02 | **PASS_BOUNDED** | Common formulation-neutral controller and existing composition seam. |
| G03-03 | **PASS** | Stagnation boundary, precedence and deterministic diagnostics tested. |
| G03-04 | **PASS** | One common line-search policy loop. |
| G03-05 | **PENDING_WP03_C** | Adaptive policy consolidation deferred. |
| G03-06 | **PENDING_WP03_C** | Adaptive policy consolidation deferred. |
| G03-07 | **PENDING_WP03_C** | Adaptive policy consolidation deferred. |
| G03-08 | **PARTIAL** | Fixed-path diagnostics covered; continuation-wide closure deferred. |
| G03-09 | **PASS_BOUNDED** | Easy targeted regressions pass; no maturity expansion. |
| G03-10 | **NOT_YET_DEMONSTRATED** | No difficult-case improvement claim. |

## Validation

The new WP03-B suite reports `30 passed`. WP01/02 foundation, continuation,
checkpoint, fixed Newton, geometric, penalty/contact, failure and robustness
option targeted regressions are recorded in the JSON evidence. Ruff and
compileall pass. Mypy reports no diagnostics in the new robustness/driver/
iteration implementation; the changed-module command still reports the
inherited load-control mixin debt (14 diagnostics), with no WP03-B-added
diagnostic identified.

The complete repository suite was not run. WP03 validated points remain `0/7`
and the roadmap total remains `22/100`.
