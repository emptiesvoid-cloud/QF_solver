# HEX8-SRI source identity and Owner decisions

## Registered source bytes

The `hex8sri-convergence24` scope is pinned to branch `research/hex8-sri-equilibrium`,
HEAD `f6402edc84af71d4d4be5b091b0ed323c1631529`, tree
`81ea54ff0ab3f0f7430b30b5aa562f995b06e7e5`, and source fingerprint
`eb58f1ad1314debdc08f34f312eae17961fc4ebfaae8510632258b5eb51305a9`.

The fingerprint algorithm hashes the sorted relative path, a NUL byte, and each
file's SHA-256 computed from its raw checkout bytes. It does not normalize line
endings. The 517 per-file digests used by the registered E-drive checkout are
preserved in [the source byte inventory](hex8sri-source-byte-inventory-f6402ed.json).
That checkout had `core.autocrlf=true`. A separate checkout at the same HEAD and
tree differed only in line endings for five files: `__init__.py`,
`archive_audit.py`, `campaign.py`, `campaign_planning.py`, and `mesh_quality.py`
under `experiments/hex8_sri_equilibrium/`. Their raw SHA-256 values are recorded
in the inventory. Neither checkout was normalized or rewritten. The controller
verifies the registered HEAD, tree, complete raw-byte inventory, and aggregate
fingerprint before accepting this scope.

The prior controller fingerprint `c93d539d6b67417f067a190066629d41f84c1a04f61a86b50034c3cfda917d04`
was recorded for science HEAD `8b61f5d37b9557e6d04cbcf8d787b4208af49486`. PR #31 advanced
the science branch to the registered `f6402edc84af71d4d4be5b091b0ed323c1631529` and
added the approved criteria contract, finiteness and negative-displacement verdicts,
and test-side provenance/sidecar checks. The reviewed diff did not change element
operators, material values, mesh geometry, load, supports, or the numerical solver
formulation. The EOL-only checkout difference is a separate raw-byte identity issue,
not the sole cause of the old `c93d…` registration becoming stale.

## Separate decisions

The controller uses two independently archived decisions. The record command
validates and stores a submitted JSON file atomically without replacement; it
does not create an execution manifest or reserve an attempt:

```powershell
python scripts/development_autonomous.py archive-hex8sri-owner-decision --decision-json <path>
```

### `CRITERIA_FREEZE_ONLY`

This decision has schema `qfsolver-hex8sri-criteria-freeze-decision-v1` and must
set status `CRITERIA_FROZEN_EXECUTION_NOT_AUTHORIZED`,
`execution_authorized=false`, and `do_not_execute=true`. It binds the exhaustive
criteria definitions, formulas, units, classifications, thresholds, all six
first-mesh nodeids, their registered case digests, the source identity, and the
controller identity. Its approved criteria are:

| Classification | Frozen criteria |
|---|---|
| `CASE_GATE` | Finite required observables; `det(J)>0` at sampled points; free residual relative `<=1e-7`; energy identity defect relative `<=1e-8`; force closure relative `<=1e-6`; moment closure relative `<=1e-6`; signed mean loaded-face `UZ<0`. |
| `CASE_DIAGNOSTIC` | Stiffness symmetry, affine Jacobian reproduction, internal-energy positivity (not asserted), formulation comparison, condition estimate, time, sampled RSS, and descriptive Timoshenko difference. |
| `CAMPAIGN_GATE_DEFERRED` | Last-two-level displacement and energy changes `<=2%`, and errors to a qualified independent 3D reference `<=5%`. These remain `NOT_ASSESSED` until the required evidence exists. |

A freeze-only decision contains no execution limits or authorized-node list. It
cannot satisfy the execution approval schema and cannot transition a prepared
manifest to `OWNER_AUTHORIZED`.

### `EXECUTION_APPROVED`

Execution requires a separate decision with schema
`qfsolver-hex8sri-execution-approval-v1`, status `APPROVED`,
`execution_authorized=true`, and `do_not_execute=false`. It must reference the
archived freeze decision ID, path, and SHA-256; carry the same frozen criteria;
bind the exact six manifest paths and raw SHA-256 values; identify the six exact
nodeids, scope, mandate, source and controller identities; and state the
registered limits and an unexpired validity interval. The per-case execution
manifest must independently bind the selected case, its validated collect-only
receipt, and its budget. The runner checks these records before reserving an
attempt.

JSON schema validation, the `approved_by` field, and a local SHA-256 establish
record consistency only. They do not cryptographically authenticate the Owner
or provide tamper-proof storage. Preserve Owner provenance through the
project's separately controlled review and archival process.

## Current preparation status

The scope remains `execution_authorized=false`, with one maximum attempt per
registered nodeid and its dedicated ledger unchanged. Existing case manifests
and preflight receipts are historical records bound to the former source and
controller identities; they are not current authorization inputs. After this
Configuration PR is reviewed and merged, regenerate the six first-mesh
non-authorized manifests and collect-only receipts against the final identities,
validate them, then submit a freeze-only decision. No execution approval or
scientific attempt is created by this change.
