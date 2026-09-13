---
doc_id: DOC-029-021
revision: 0.1
status: controlled-evidence
applicable_version: 0.2.9-development
---

# WP04-C2R6 recovered M2/M3 frozen-threshold audit

## Scope and provenance

This record recovers the completed C2R6 campaign from existing files on disk.
M2 and M3 were not rerun for this audit. No solver process was started and no
production source was changed.

- Branch: `0.2.9-unified-nonlinear`
- Campaign source SHA: `2c52bf8196a7d47d14ce1784290580160de26590`
- Campaign start: `2026-09-13T05:58:04.972809+00:00`
- M2: `2026-09-13T05:58:05.845108+00:00` to `2026-09-13T07:47:27.456796+02:00`
- M3: `2026-09-13T07:47:31.665307+02:00` to `2026-09-13T16:37:14.090684+02:00`
- M4: not run
- PETSc/PyAMG: not used
- Full repository suite: not run

The raw runner record at
`qualification/0_2_9/c2r6/campaign_result.json` contains a top-level
`G04-10: UNRESOLVED` placeholder because the runner did not calculate the
pairwise mesh thresholds. That raw value is preserved. The derived result in
`qualification/0_2_9/c2r6/frozen_threshold_audit.json` performs that frozen
calculation from the completed M2/M3 result files and records
`PASS_CANDIDATE_PENDING_OWNER_REVIEW`.

## Frozen route

Both cases used the same recorded route:

- MINRES with Jacobi preconditioning
- `rtol=1e-11`, `atol=1e-14`, `maxiter=10000`
- direct fallback disabled
- existing/enabled line search
- Newton tolerance `1e-10`
- 12 fixed load increments
- floor-aware termination enabled

## Output completeness

| Case | Mesh | Result/process status | Accepted steps | Telemetry | Failure/capture |
| --- | --- | --- | ---: | ---: | --- |
| M2 | 48 × 24 × 24; 165,888 TET4; 91,875 full DOFs | `COMPLETED` / `COMPLETED` | 12 | 313 declared, 313 lines | none |
| M3 | 64 × 32 × 32; 393,216 TET4; 212,355 full DOFs | `COMPLETED` / `COMPLETED` | 12 | 288 declared, 288 lines | none |

Each result contains accepted records for steps 1 through 12, accepted load
factors from 1/12 through 1.0, and accepted-state digests. The recorded M2
and M3 PIDs (57564 and 30220) are no longer running. No failure-forensics
capture is required by either result.

The result-level/per-step Newton totals are M2 `300` and M3 `275`; linear
solves are M2 `297` and M3 `272`, with zero direct fallbacks. The telemetry
`SOLVE_COMPLETED.newton_iterations` field reports 288 and 263 respectively,
under-counting by the 12 `FLOOR_CONVERGED` events in each case. This is a
non-blocking aggregate bookkeeping discrepancy in the existing telemetry, not
an incomplete campaign: the per-iteration event lines and
`STEP_ACCEPTED.iterations` sums agree with the result-level totals. No rerun
was used to resolve it.

## Floor-aware acceptance audit

Each case records three primary convergences and nine
`CONVERGED_NUMERICAL_FLOOR` events. Re-reading the existing telemetry and
result data confirms every floor event satisfies the frozen conjunction:
finite residual and correction, primary residual not yet met, residual within
the recorded state-resolution estimate, plateau spread within its frozen
window, correction within the machine-resolution threshold, linear backward
error at or below `1e-10`, no available line-search improvement, valid state,
and force/moment diagnostics within `1e-8`.

The maximum recorded linear backward errors are:

- M2: `4.777962584217645e-12`
- M3: `8.106166618904346e-12`

There are no non-finite values and no fallback events.

## Recovered physical results

| Observable | M2 | M3 |
| --- | ---: | ---: |
| Tip displacement | -0.19685864781061374 | -0.2002482511318092 |
| Reaction resultant norm | 49.9999999999999 | 49.99999999999998 |
| Strain energy | 4.915487767084533 | 4.999939075668591 |
| Representative `sigma_xx` | 3002.540859194057 | 3068.972048649666 |
| Minimum `det(F)` | 0.9917813121785688 | 0.9909797199809931 |
| Principal-stretch range | [0.99020740580251, 1.0097489329706606] | [0.9893216428558, 1.0104538037144282] |
| Maximum `||E||` | 0.010351119868140262 | 0.01111056564916684 |
| Force equilibrium relative error | 2.271677919850833e-14 | 2.5505039661180956e-14 |
| Moment equilibrium relative error | 1.2986843893587648e-15 | 7.63053276664867e-16 |

Both cases remain inside the frozen deformation envelope. Their accepted load
factor paths are identical, and each contains 12 accepted-state digests.

## Frozen M2-to-M3 thresholds

The original C2 frozen comparison is evaluated as
`abs(fine-medium)/max(abs(fine),abs(medium),1e-12)`, without changing any
threshold:

| Quantity | Delta | Frozen limit | Result |
| --- | ---: | ---: | --- |
| Tip displacement proxy | 0.01692700586415766 | 0.02 | PASS |
| Reaction resultant norm | 1.563194018672221e-15 | 0.02 | PASS |
| Strain energy | 0.016890467524899724 | 0.02 | PASS |
| Representative `sigma_xx` | 0.02164607184507869 | 0.10 | PASS |

All four frozen pair thresholds pass. Therefore the recovered campaign result
is `G04-10 = PASS_CANDIDATE_PENDING_OWNER_REVIEW`, not final WP04 closure.
The WP04 hold, zero points, and validated total remain unchanged pending Owner
review.

## Controlled artifacts

- Raw campaign: `qualification/0_2_9/c2r6/campaign_result.json`
- M2 result/status/telemetry: `qualification/0_2_9/c2r6/m2_result.json`,
  `m2_status.json`, `m2_telemetry.jsonl`
- M3 result/status/telemetry: `qualification/0_2_9/c2r6/m3_result.json`,
  `m3_status.json`, `m3_telemetry.jsonl`
- Frozen controls: `qualification/0_2_9/c2r6/floor_aware_policy.json`
- Derived audit: `qualification/0_2_9/c2r6/frozen_threshold_audit.json`
- Chronological remediation record:
  `docs/verification/0_2_9/linear-solver-remediation-master.md`

WP04 remains `HOLD` at `0/12`; validated total remains `29/100`; maturity is
unchanged. The next action is Owner review of this recovered
`PASS_CANDIDATE_PENDING_OWNER_REVIEW` result before any further WP04 work.
