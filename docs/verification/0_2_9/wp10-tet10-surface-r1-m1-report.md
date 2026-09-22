# WP10 TET10 surface-traction R1 — M1 report

## Scope

This is a new bounded requalification attempt for TET10. It does not rewrite
or supersede the historical equal-share TET10 failure. The only change in the
benchmark definition is the load representation: a constant traction is
integrated with the existing quadratic TET10 surface-load path over the two
unique boundary faces at `x=1`, producing consistent nodal contributions.

The reference resultant is intentionally bounded at `0.25` and the load path
is `[0.2, 0.4, 0.6, 0.8, 1.0]`. This is a new contract choice, not a change
to an old threshold.

## Provenance

```text
BRANCH = codex/wp10-tet10-surface-r1
AUTHORIZED_BASE_SHA = cfec576ed44e8c68469ba45613ecbd46792ce7ff
EXECUTION_SHA = acd6a5f4c8541ffcfdcde7e5be26cb0fdafcc52f
RUNNER_SHA = 7bd222fa7b4327148969c580602389f4235664b3
CONTRACT_SHA256 = c6d6cd9d1a0a869443eb9ae5d7b8e03283f7fa46c37dc72287206fc0d16b11a8
POLICY_DIGEST = 93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac
PRODUCTION_MECHANICS_CHANGED = NO
THRESHOLDS_CHANGED = NO
M2_M3_EXECUTED = NO
```

## Load audit

The x=1 boundary contains two unique quadratic triangular TET10 faces at
each level. Their total area is `1.0`; the applied traction is therefore
`[0.25, 0, 0]`. The integrated values are:

```text
resultant = [0.24999999999999994, 0, 0]
resultant error norm = 5.551115123125783e-17
moment about origin = [0, 0.125, -0.125]
```

This verifies the consistent load assembly and replaces the historical
`0.5 / number_of_loaded_nodes` nodal split only in this new R1 benchmark.

## M1 results

| Level | Nodes | TET10 | DOFs | Accepted | Fallbacks | Max relative residual | Max PEEQ | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| H1 (`1 x 1 x 1` blocks in x scope) | 26 | 5 | 78 | 5/5 | 0 | `2.9311688994e-08` | `0.0280873` | PASS_CANDIDATE |
| H2 (`2 x 1 x 1`) | 43 | 10 | 129 | 5/5 | 0 | `1.9546937605e-09` | `0.0243754` | PASS_CANDIDATE |
| H3 (`4 x 1 x 1`) | 77 | 20 | 231 | 5/5 | 0 | `9.4735445307e-10` | `0.0235426` | PASS_CANDIDATE |

All three levels remain below the frozen local corotational strain bound of
`0.05`; all increments were accepted and no fallback was reported.

The displacement-norm changes are approximately `22.35%` from H1 to H2 and
`24.30%` from H2 to H3. Consequently this run demonstrates a stable M1
execution path, but it does **not** establish mesh convergence. The hierarchy
refines only the x direction and is retained as bounded diagnostic evidence.

## Reference and gates

The per-level reference files independently recompute finite displacement and
surface-load resultant observables. They do not constitute an independent
global FEM/Newton solve. All three reference files pass and have the same
contract/provenance binding as their primary result.

M2 and M3 were not run. They remain blocked until the owner reviews this new
M1 evidence and explicitly freezes/authorizes the subsequent contact and
replay scope.

The first invocation accidentally used the globally installed package rather
than this clone's `src` tree and produced an `InputValidationError` before a
solve. That pair of files is quarantined under
`H1_preflight_environment_mismatch/`; it is not part of the authoritative
M1 evidence and had no numerical result.

## Status

```text
WP10_TET10_SURFACE_M1 = PASS_CANDIDATE_H1_H2_H3
MESH_CONVERGENCE = NOT_CLAIMED
M2 = NOT_RUN_BLOCKED
M3 = NOT_RUN_BLOCKED
WP10_TET10_EXTENSION_POINTS = 0_PENDING_OWNER_REVIEW
FINAL_STATUS = READY_FOR_OWNER_REVIEW_BEFORE_M2_M3
```
