---
doc_id: DOC-029-WP03-011
revision: 0.1
status: implementation_migration
applicable_version: 0.2.9-development
---

# WP03-D — arc-length robustness and radius policy boundary

> **Targeted implementation evidence, not a release claim.** This step keeps
> WP03 at 0/7 points, does not change arc-length mathematics or maturity, and
> leaves independent closure to WP03-E.

## Scope and baseline

WP03-D was implemented from
`862e6dd5e5b976fbb2ca57c1966640691fcb2700` on branch
`0.2.9-unified-nonlinear`. The structured pre-edit D-B01–D-B15 observations
are retained in `qualification/0_2_9/wp03_d_baseline.json`.

The specialized `solve_arc_length_correction` kernel, augmented constraint,
predictor sign and branch-selection mechanics were not changed. The change
is limited to the robustness boundary around that kernel.

## One policy authority

`UnifiedArcLengthRadiusPolicy` is the single radius-policy authority. It
consumes `RetryClassification` and owns accepted-step keep/grow/shrink,
retry shrink, minimum-radius termination and deterministic diagnostics. The
`UnifiedContinuationController` remains responsible for rollback and
accepted-state publication.

The policy records two distinct radii:

| Term | Meaning |
| --- | --- |
| policy radius | value carried between accepted/rejected decisions |
| effective attempt radius | value passed to the correction kernel after target clipping |

On retry, rollback is completed and verified before policy evaluation. A
target-clipped attempt advances to the first policy-shrink value strictly
below the failed effective radius. This preserves the normal cutback
trajectory while preventing a “cutback” that repeats the identical effective
attempt indefinitely. Equality with the minimum radius is permitted; a
candidate below it is terminal.

Unknown `RuntimeError` behavior is preserved as the existing
`OWNER_POLICY_DEPENDENT` path when owner policy is enabled. Explicit terminal
arc stages (minimum radius, max steps and load-factor policy boundaries) are
not recursively retried. Checkpoint save remains after physical commit and
outside the radius retry path.

## Target-clipped audit

The start-SHA audit reproduced the defect: policy radius `0.1` was reduced to
`0.05`, while target clipping kept the effective failed and retry radii at
`0.0035355339059327385`. The policy now advances the retry radius to
`0.003125`, so the next effective attempt is strictly smaller. This is a
bounded policy-progress correction; no difficult physical convergence claim
is made, so G03-10 remains `NOT_YET_DEMONSTRATED`.

## Preservation and validation

The D-B01–D-B15 cases remain PASS or bounded PASS under the frozen comparison
policy (relative `1e-9`, absolute floor `1e-12`). Existing WP01-D,
WP02-D and WP02-D1 arc/restart tests remain green. The focused WP03-D file
contains T03D-01 through T03D-40, including policy boundaries, source audit,
target clipping, restart preservation and checkpoint-failure isolation.

| Targeted group | Result |
| --- | --- |
| WP03-D focused tests | `40 passed` |
| WP03-C / WP03-B | `35 passed` / `30 passed` |
| WP02-D / WP02-D1 | `28 passed` / `10 passed` |
| WP01-D continuation | `22 passed` |
| arc analysis | `3 passed, 27 deselected` |
| failure modes / campaign | `20 passed` / `1 passed` |
| state/checkpoint/contact groups | `25 passed`; `38 passed`; `13 passed` |
| J2/load-path and geometric groups | `25 passed`; `12 passed` |
| geometric public / penalty-contact focused | `7 passed`; `7 passed, 12 deselected` |

The source audit finds one radius-policy authority and one radius-shrink
policy loop. The full repository suite was not run. No numerical or element
formulation, historical evidence, maturity claim or checkpoint schema was
changed. WP03 remains at `ARC_LENGTH_ROBUSTNESS_BOUNDARY`, 0/7 points, and
the next action is Owner review before the independent WP03-E closure audit.
