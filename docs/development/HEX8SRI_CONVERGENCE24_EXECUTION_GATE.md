# HEX8-SRI convergence24 execution gate

## Status

Controller support is prospective. The registered scope remains
`execution_authorized: false`; all 24 scientific case manifests remain
`execution_authorized: false`, `do_not_execute: true`, and
`PREPARED_NOT_AUTHORIZED`. No attempt has been reserved by this extension.

The code path accepts only one exact registered nodeid, its current case
manifest, a validated collect-only receipt, a separate `OWNER_AUTHORIZED`
execution manifest, and a separately archived Owner decision record whose
SHA-256 matches the manifest reference. It checks the campaign mandate,
source fingerprint, controller provenance, solver origin, case registration
digest, exact preflight identity, fixed per-node budget, decision scope and
authorized node list before any attempt-ledger write.

The preparation command writes only a create-once draft under the dedicated
controller run store:

```text
python scripts/development_autonomous.py prepare-hex8sri-manifest \
  --target '<one registered convergence24 nodeid>' \
  --preflight-id '<validated pf-… receipt>' \
  --authorization-id '<unique draft id>'
```

The resulting file is `PREPARED_NOT_AUTHORIZED`, has both execution flags
closed, and contains no Owner decision. It is placed in a `prepared/`
subdirectory, which the execution validator rejects. An approved manifest
must be a new file directly in the campaign authorization directory, and must
reference a separately archived decision JSON beneath `owner-decisions/`.
Existing drafts, case manifests, preflight receipts, and campaign evidence are
never overwritten.

The Owner decision record must carry exactly these fields:

`decision_id`, `status`, `approved_by`, `approved_at_utc`, `reason`,
`scope_id`, `mandate_id`, `campaign_id`, `authorized_nodeids`,
`source_fingerprint`, `controller_fingerprint`, `controller_head`, and
`limits_by_nodeid`.

The decision must name `Owner`, use `APPROVED`, identify one or more exact
allowlisted nodeids, bind the current source and controller identities, and
repeat the immutable per-node limits. The execution manifest duplicates that
decision and binds its record path and SHA-256. The runner can verify the
record's contents and all bindings; this local JSON workflow is auditable but
is not a cryptographic signature of the human approver. A signed Owner
identity would require a separately approved signature-verification service
and key policy, neither of which is introduced here.

## Pre-execution blockers

The current science test is still the earlier `hex8sri` contract. It expects
the old worktree/controller identity, reads authorization state from the case
manifest, and requires `OWNER_FROZEN` criteria. The new runner checks a
dedicated execution-manifest contract marker and required environment fields
before reserving an attempt, so this source version is refused before ledger
reservation.

The 24 case manifests also currently have
`criteria_status: PROPOSED_REQUIRES_OWNER_FREEZE` and
`frozen_criteria: null`. The runner additionally refuses any case whose
frozen criteria do not equal the registered proposed criteria verbatim. A
separate Owner decision must freeze those criteria; the case registration
digest, controller policy binding, manifests, fingerprints, and collect-only
receipts must then be refreshed. Thresholds must not be edited to obtain a
PASS.

Changing the science test contract or freezing criteria changes the current
science identity. The present preparation fingerprint is
`1fce68d6b2f2702c794e37d73c16414e0d0e4c0f2837331e5792b6fbfb414555`; it must
not be reused after source or registered case-content changes. The old
preflights remain historical evidence and are not silently rebound.

## Static solver-resource audit

The registered convergence driver assembles each 24-by-24 element stiffness
into three NumPy triplet arrays (`int32` row, `int32` column, `float64`
value), converts COO to CSR, extracts `Kff` as CSR, converts it to CSC, and
uses SciPy SuperLU (`splu`, `MMD_AT_PLUS_A`). The condition number is estimated
from the same sparse factorization using `onenormest`; it is not an
eigensolve. The driver does not create a dense `Kff`.

The table gives static storage arithmetic, not observed peak memory. COO
triplets use 16 bytes per element matrix entry. CSR figures use a conservative
structural ceiling of 81 scalar entries per free DDL and 12 bytes per CSR
entry plus 4-byte row pointers; actual sparsity is lower. Dense `Kff` is shown
only as a comparison. SuperLU fill, conversion temporaries, NumPy/SciPy
allocator behavior, and archive compression are not bounded by those input
matrix estimates.

| Mesh | Elements | Nodes | Total DDL | Fixed DDL | Free DDL | COO triplets | CSR `Kff` structural ceiling | Dense `Kff` equivalent |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 4×2×2 | 16 | 45 | 135 | 27 | 108 | 0.14 MiB | 0.10 MiB | 0.09 MiB |
| 8×4×4 | 128 | 225 | 675 | 75 | 600 | 1.13 MiB | 0.56 MiB | 2.75 MiB |
| 16×8×8 | 1,024 | 1,377 | 4,131 | 243 | 3,888 | 9.00 MiB | 3.62 MiB | 115.33 MiB |
| 32×16×16 | 8,192 | 9,537 | 28,611 | 867 | 27,744 | 72.00 MiB | 25.82 MiB | 5,872.57 MiB |

At 32×16×16, the state also stores 3.00 MiB of sampled Gauss strains and
0.56 MiB of sampled Jacobians, before the global sparse matrix, conversion
copies, factorization fill, and compressed evidence. This is a static lower
inventory, not a peak-RSS prediction. SuperLU fill has not been measured, so
the 16,384 MiB RSS setting is a monitored ceiling, not a demonstrated
adequate memory requirement.

| Mesh | Wall timeout ceiling | RSS monitored ceiling |
|---|---:|---:|
| 4×2×2 | 180 s | 512 MiB |
| 8×4×4 | 300 s | 1,024 MiB |
| 16×8×8 | 900 s | 4,096 MiB |
| 32×16×16 | 3,600 s | 16,384 MiB |

The ceilings sum to 8 h 18 min across all 24 nodes when run sequentially.
They are not execution-time forecasts. No new assembly, solve, eigensolve,
or runtime/memory measurement was performed for this audit.

## Validation performed

The controller-only test module contains synthetic policy, manifest,
preflight-writer, ledger, resource-monitor, refusal, and compatibility tests.
It does not call `run_convergence_case`. The runner refuses this scope unless
the exact preflight and Owner manifest validate; it also refuses a prepared
manifest, a mismatched decision record, a changed source/controller/case
binding, an unregistered nodeid, a changed budget, an incompatible ledger,
or a previously consumed node attempt.

The first-six-case Owner request is in
[`HEX8SRI_CONVERGENCE24_OWNER_REQUEST_FIRST6.md`](HEX8SRI_CONVERGENCE24_OWNER_REQUEST_FIRST6.md).
It is a draft decision request, not an authorization.
