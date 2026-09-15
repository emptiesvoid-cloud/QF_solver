# WP08-D M2 fail-closed forensic review

## Scope and authority

This is a read-only review of the already archived WP08-D Phase-1 M2 run. No
solve was rerun, no production code was changed, and no threshold or solver
parameter was changed.

The authoritative archive commit is `d2b07ec4c3ddcf45a96b9ceec278fb181ab70a0a`
on branch `0.2.9-wp08d-m1-phase1`. The M2 computation itself records runner
commit `d47287944906610eaac751871796de34df4b7d44` and governed baseline
`28cf9dd1886b72c6c7c9fc720dc778eddfce4441`. Both are ancestors of the
authoritative archive commit. This is an execution-versus-archive provenance
distinction, not an altered M2 result.

## Evidence integrity

The M2 manifest lists four preserved files. All four exist and match the
manifest size and SHA-256 values:

| file | bytes | SHA-256 verification |
|---|---:|---|
| `console.err.log` | 139 | PASS — `8c89e61cf9ec6d576cab7d2876d5fb7fdd076f91250629cb4259743b62e47eba` |
| `console.log` | 60 | PASS — `8a9a51aeb6e0dd45c06e8db16ff3388ed7005745ce1291de906b9de2c23a9fb2` |
| `progress.json` | 272 | PASS — `d541798de9a28c2b0f683d38560ac9bf270610d76fc96a1ce30422498b867da2` |
| `telemetry.jsonl` | 6,757 | PASS — `e16848f315c631688b21387d5e048991977fca8274379a59b7792e3d542524c2` |

The telemetry contains 10 valid JSON lines with contiguous sequence numbers
0 through 9. The canonical contract digest recomputes to
`d2d9533c873000996ab3fad992c653dfed37f533ed12d85af97b3696740f179a`, matching
the manifest and the M2 fail-closed record. The recorded governing policy
digest is consistently present in the manifest, contract, runner, telemetry,
and failure record as
`93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`.

Absence of `result.json` and `raw.npz` is expected and explicitly documented:
the production solve produced no converged terminal state. It is not evidence
loss or a partial overwrite.

## Exact observed failure point

The run reached:

- mesh construction: 49 nodes, 96 TET4 elements, 147 DOFs;
- assembly completion: 147 x 147 matrix with 3,033 nonzeros;
- contact linear-solve entry: backend `contact_active_set`;
- failure before any completed increment.

The last meaningful sequence is:

1. `ASSEMBLY_END` at elapsed 0.102345 s;
2. `LINEAR_SOLVE_START` at elapsed 0.102491 s;
3. `ANALYSIS_FAILED` at elapsed 0.162126 s with
   `NumericalConvergenceError`;
4. wrapper `RUN_FAILED` at elapsed 0.166293 s.

There is no `LINEAR_SOLVE_END`, `KRYLOV_PROGRESS`, `NEWTON_START`,
`STEP_END`, or accepted increment. The evidence therefore localizes the
failure to the first production contact solve after assembly, before the first
load-path increment was committed. The inner active-set iteration number and
the exact load-path increment are not serialized and cannot be recovered from
these artifacts without rerunning or modifying instrumentation.

The terminal message is:

> Frictional contact active set did not converge with direct or active-slip root iterations.

The direct route and the bounded active-slip root route are both represented in
the production call path. No alternate linear backend or unauthorized fallback
was enabled; the manifest records `serial_direct` and `fallback = disabled`.

## Contact-state evidence

The friction-enabled contact route was entered. The frozen runner constructs
contact operators with `friction_coefficient = 0.3`, and
`FrictionlessActiveSetSolver.solve` dispatches to `_solve_with_friction` when
any operator has friction. `_solve_with_friction` then tries the direct
fixed-point iteration and, after its `NumericalConvergenceError`, invokes
`solve_active_slip_root`.

The raw M2 evidence does **not** record an active-contact count, per-contact
gap, pressure, stick/slip state, or active-set history at failure. Therefore:

- frictional contact route invoked: **YES**;
- physical closed-contact state at the failure: **NOT RECORDED**;
- accepted contact state: **NONE**;
- accepted increments: **0 of 7**.

The telemetry label `method = frictionless_active_set` is a generic/legacy
method label on the contact-solver entry event. It does not override the
friction-enabled dispatch proven by the runner configuration and the failure
message. This is an observability limitation, not a basis for changing the
numerical result.

## Code-path audit

The read-only code trace is:

`build_production_model`
→ frictional `FrictionlessActiveSetSolver.solve`
→ `_solve_with_friction`
→ `_solve_friction_increment`
→ `_iterate_friction_increment(strategy="direct")`
→ `solve_active_slip_root` after direct failure
→ canonical `NumericalConvergenceError` after both paths fail.

The frozen M2 settings observed in the runner and manifest are:

- seven load-history increments;
- `contact_max_iterations = 25`;
- `contact_friction_tolerance = 1e-9`;
- `mu = 0.3`;
- tangential stiffness `kt = 1e6`;
- initial fixed-face normal search;
- serial direct contact KKT solves;
- fallback disabled.

`_friction_update` contains finite-state guards and an explicit zero trial-norm
branch. The archived exception is not a non-finite-state exception and the
preserved logs contain no NaN/Inf diagnostic. No evidence in this run proves a
defect in that guard or in the contact constitutive update.

The solver also owns a rollback transaction around each load increment. The
failure record confirms rollback-oriented failure handling and no committed
increment; there is no evidence of state leakage or a changed production
mechanics path.

## Reproducibility and limitations

The scenario is theoretically reproducible under the same repository lineage,
contract/policy digests, mesh generation, numerical libraries, and serial
execution: the mesh/load construction is deterministic and the observed
failure occurs on the fixed first-solve path. Empirical reproduction is outside
this review and was not performed.

The evidence has two bounded limitations:

1. the wrapper collapses the direct and active-slip-root exceptions into one
   terminal message, so it does not identify which inner iteration or root
   subcondition was last active;
2. telemetry stops at contact-solver entry and does not expose active-set
   iteration diagnostics.

These limitations prevent a more specific inner-cause claim. They do not turn
the preserved, contract-consistent failure into a successful qualification.

## Governance disposition

- M2: `FAIL_CLOSED` with `NumericalConvergenceError`.
- Independent reference: `NOT_RUN_DEPENDENCY_PRODUCTION_FAILURE`.
- Replay: `NOT_RUN_DEPENDENCY_PRODUCTION_FAILURE`.
- M3: `NOT_RUN_DEPENDENCY_M2_FAILURE`.
- Production mechanics changed: **NO**.
- Thresholds, solver parameters, and fallbacks changed: **NO**.
- `WP08D_FORMAL_POINTS = 0/2`.
- `WP08_FORMAL_POINTS = 0/8`.
- No corrective action or qualification rerun is authorized by this review.

## Final classification

`ACTIVE_SET_ROBUSTNESS_LIMITATION`

