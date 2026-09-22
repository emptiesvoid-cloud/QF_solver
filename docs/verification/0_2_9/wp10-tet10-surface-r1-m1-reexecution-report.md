# WP10 TET10 surface-traction R1 — final M1 reexecution

## Decision scope

This report is the authoritative M1 evidence for a new bounded TET10
benchmark. It uses the existing quadratic distributed-load integrator on the
two unique TET10 faces at `x=1`; it does not use the historical equal nodal
split. The historical TET10 `FAIL_CLOSED` result remains preserved and is not
rewritten.

The new contract freezes a reference resultant of `0.25` and the path
`[0.2, 0.4, 0.6, 0.8, 1.0]`. This reduces the benchmark load to remain inside
the corotational small-deformation scope; it is not a threshold change.

## Exact provenance

```text
BRANCH = codex/wp10-tet10-surface-r1
AUTHORIZED_BASE_SHA = cfec576ed44e8c68469ba45613ecbd46792ce7ff
EXECUTION_SHA = a114a707332487a637569661b9548f2928d885b7
RUNNER_SHA = 21eec18611b1eec3c6e2c4c2250f781827b98401
CONTRACT_SHA256 = e1203f6203281b3bf5e8a503b52ed1fe8f2a548128819e685764477c60c34359
POLICY_DIGEST = 93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac
PRODUCTION_MECHANICS_CHANGED = NO
THRESHOLDS_CHANGED = NO
```

## M1 result

| Level | Nodes | Elements | DOFs | Accepted | Fallbacks | Max residual | Max PEEQ | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| H1 (`cells_x=1`) | 26 | 5 TET10 | 78 | 5/5 | 0 | `2.9311688994e-08` | `0.0280873` | PASS_CANDIDATE |
| H2 (`cells_x=2`) | 43 | 10 TET10 | 129 | 5/5 | 0 | `1.9546937605e-09` | `0.0243754` | PASS_CANDIDATE |
| H3 (`cells_x=4`) | 77 | 20 TET10 | 231 | 5/5 | 0 | `9.4735445307e-10` | `0.0235426` | PASS_CANDIDATE |

Every level completed without fallback and within the local corotational
strain bound `0.05`. The integrated load balance is, for every level,

```text
resultant = [0.24999999999999994, 0, 0]
error norm = 5.551115123125783e-17
moment about origin = [0, 0.125, -0.125]
```

The displacement norms are `0.0675712`, `0.0870239`, and `0.114956` for
H1/H2/H3. H1→H2 changes by `22.35%` and H2→H3 by `24.30%`; therefore this
three-level x-only hierarchy is diagnostic evidence only and does not support
a mesh-convergence claim.

## Independent observable and gates

Each reference file verifies finite displacements and recomputes the surface
load resultant. It is explicitly **not** an independent global FEM/Newton
solve. All three reference checks pass and their hashes are recorded in the
reexecution manifest.

M2 and M3 were not executed. They remain fail-closed until M1 is reviewed and
a separate contact/replay contract is frozen and authorized.

## Final status

```text
WP10_TET10_SURFACE_M1 = PASS_CANDIDATE_H1_H2_H3
WP10_TET10_MESH_CONVERGENCE = NOT_CLAIMED
WP10_TET10_M2 = NOT_RUN_BLOCKED
WP10_TET10_M3 = NOT_RUN_BLOCKED
WP10_TET10_EXTENSION_POINTS = 0_PENDING_OWNER_REVIEW
FINAL_STATUS = READY_FOR_OWNER_REVIEW_BEFORE_M2_M3
```
