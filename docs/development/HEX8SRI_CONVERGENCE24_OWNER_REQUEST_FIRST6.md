# Draft Owner decision request — first six HEX8-SRI convergence cases

**State: NOT SUBMITTED FOR EXECUTION APPROVAL.** This document prepares a
separate decision request. It does not authorize or reserve any FEM attempt.

## Proposed bounded tranche

Branch scope: `hex8sri-convergence24` on
`research/hex8-sri-equilibrium`. The requested tranche is exactly the three
formulations at `ν = 0.3` and `ν = 0.4999` on the `4×2×2` mesh:

| Nodeid | Formulation | ν | Mesh | DDL (total / fixed / free) |
|---|---|---:|---:|---:|
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p3-4x2x2]` | HEX8 standard | 0.3 | 4×2×2 | 135 / 27 / 108 |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p3-4x2x2]` | SRI historical | 0.3 | 4×2×2 | 135 / 27 / 108 |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p3-4x2x2]` | SRI corrected | 0.3 | 4×2×2 | 135 / 27 / 108 |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p4999-4x2x2]` | HEX8 standard | 0.4999 | 4×2×2 | 135 / 27 / 108 |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_historical-nu_0p4999-4x2x2]` | SRI historical | 0.4999 | 4×2×2 | 135 / 27 / 108 |
| `tests/verification/test_hex8_sri_convergence.py::test_convergence_case[sri_corrected-nu_0p4999-4x2x2]` | SRI corrected | 0.4999 | 4×2×2 | 135 / 27 / 108 |

All cases share the same 20×1×1 m geometry, structured mesh, `E = 1.0e6 Pa`,
traction resultant `(0, 0, -1) N` on `x = 20 m`, and fully fixed `x = 0`
face. Each case is a separate process and would run sequentially, one attempt
maximum per exact nodeid, without automatic retry.

## Proposed resource ceilings

Each case has a 180 s wall-time ceiling and a 512 MiB sampled RSS ceiling.
RSS is a soft observation, not an OS-enforced quota. Each case also inherits
the registered limits: 8 processes, 8 MiB per captured stream / 16 MiB total,
512 MiB temporary files, 256 MiB per-attempt archive, and a 2,048 MiB free-
disk floor. Sequential wall-time ceilings sum to 1,080 s (18 minutes). The
six individual archive ceilings sum to 1,536 MiB; the free-disk floor remains
2,048 MiB throughout. These are limits, not runtime or peak-memory forecasts.

## Preconditions before this request can be approved

1. The execution-gate PR must be reviewed and merged or the exact reviewed
   controller branch HEAD must be selected for execution.
2. The science test currently uses the old `hex8sri` identity and old
   controller branch contract. It must be updated to validate the separate
   Owner manifest, decision record, case manifest, and preflight before any
   assembly; its source fingerprint and all 24 preflights must then be
   refreshed. No attempt may be reserved against the current test source.
3. The case manifests currently mark criteria
   `PROPOSED_REQUIRES_OWNER_FREEZE` with `frozen_criteria: null`. A separate
   Owner decision must freeze the registered proposed criteria verbatim.
   This changes each case registration digest and requires refreshed
   controller bindings, case identities, and collect-only receipts.
4. A final dossier must list the exact controller HEAD/tree and file hashes,
   source HEAD and fingerprint, six case-manifest SHA-256 values, six
   validated preflight IDs and SHA-256 values, and the final budgets. Those
   identities are intentionally not filled from stale receipts here.

## Decision requested after the preconditions are met

The later Owner decision should explicitly authorize only the six nodeids in
the table, one attempt per nodeid, with the ceilings above, against the exact
final controller, source, case-manifest, and preflight identities. It should
not authorize the remaining 18 cases, change thresholds, or imply a general
HEX8-SRI qualification.

Upon approval, preserve the decision as a separate JSON record under the
controller's `authorizations/hex8sri-convergence24/owner-decisions/` folder.
Each per-node execution manifest must bind that record's SHA-256 and remain
limited to the matching exact case and preflight. A prepared template is not
an approval, and this draft is not a signature or an execution instruction.
