# WP07-D contact-event line-search remediation R2.3

## Purpose and preserved evidence

R2.2 remains the authoritative historical failure record. Its three PENALTY
primary cases remain `FAIL_CLOSED_PROCESS_EXIT`; no R2.2 result, log, hash,
authorization, or decision is rewritten. R2.3 is a prospective requalification
of the same bounded WP07-D benchmark and M1/M2/M3 hierarchy.

## Diagnosis

The penalty residual and tangent are consistent on a fixed contact branch,
including the frozen `surface_lumped` integration. The failure observed in the
prior campaign is consistent with a nonsmooth open-to-contact transition: a
Newton correction can cross a gap-zero event, while canonical powers-of-two
backtracking may sample only points on either side of the narrow useful region.
The previous run’s telemetry showed canonical line-search failure near such a
transition. This diagnosis does not change the historical classification.

## R2.3 correction

The production contact force, residual, tangent, penalty values, search
geometry, physical inputs, convergence thresholds, iteration limits, linear
solver, and fallback policy are unchanged. The nonlinear globalization now:

1. runs the existing canonical backtracking candidates first;
2. predicts fixed-initial-search gap-zero factors along the current Newton
   correction;
3. only if canonical backtracking finds no acceptable trial, evaluates a
   bounded set of additional factors around representative predicted events;
4. applies the exact same merit acceptance rule to every candidate; and
5. retains the original fail-closed line-search error if no candidate passes.

The added diagnostics are observational only. Exceptions in diagnostic
collection or event-candidate generation do not alter the solve and do not
enable fallback. The maximum number of supplemental factors in one iteration
is 24; the existing canonical reduction count and minimum alpha are unchanged.

## Diagnostic evidence before formal requalification

The corrected checkout completed direct diagnostic PENALTY solves at M1 and
M2 using the frozen meshes. These were not executions through the source-bound
formal runner, and are not qualification evidence:

| Level | Nodes | Elements | DOFs | Accepted increments | Newton iterations | Final relative residual | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| M1 | 408 | 1,536 | 1,224 | 8/8 | 68 | 1.8185e-11 | `PASS_DIAGNOSTIC` |
| M2 | 2,604 | 12,288 | 7,812 | 8/8 | 76 | 2.8881e-11 | `PASS_DIAGNOSTIC` |

No M3, independent reference, or replay is claimed by these observations.
Formal status remains fail-closed until the prospective R2.3 campaign completes
under its exact committed execution SHA.

## R2.3 gates and limitations

R2.3 preserves the contract’s force, moment, displacement, contact-resultant,
active-region, penetration, energy, stress, deformation-envelope, reference,
and replay gates byte-for-byte. It changes only the declared trial-generation
strategy for the bounded fixed-initial-search penalty route. ACTIVE_SET remains
in the campaign as the independently frozen companion route. All structural
cases run sequentially; references follow only passing primary cases; replay
is allowed only after the raw-evidence gate passes.

No WP07-E/WP08-E closure, points, ledger update, merge, push, tag, or release is
authorized by this record. A failure in R2.3 must be retained as evidence.
