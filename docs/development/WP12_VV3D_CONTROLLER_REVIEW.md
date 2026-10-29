# WP12 VV3D controller candidate review

## Scope

This change adds the prospective `wp12_vv3d_adaptive` scope for campaign
`WP12-VV3D-ADAPTIVE-20261029-R1`. It registers 12 initial FEM cases, eight
closed-catalog adaptive FEM cases, and four archive-only QPOST jobs. The campaign
policy remains `execution_authorized: false`; a run still requires the exact
campaign contract and Owner decision, one source-bound collect-only preflight,
and a matching per-case execution manifest.

The candidate is not the officially designated controller. The release
`AGENTS.md` continues to pin the existing shared controller until a reviewed
designation change is made. No real preflight, reservation, ledger write, FEM
assembly, solve, or eigensolve was performed while preparing this candidate.

## Enforced limits

- At most 24 scientific FEM attempts and 28,800 cumulative seconds.
- At most 1,200 seconds, 4,096 MiB sampled RSS, and 30,000 selected DDL per FEM
  case; one attempt per case and no implicit retry.
- One VV3D FEM/QPOST job at a time through the campaign-exclusive lock.
- Up to 12 additional adaptive catalog entries are selectable only through the
  frozen campaign transition table and their exact eligibility receipts.
- QPOST reads an archived source result and has a separate one-job budget; it
  does not reserve a FEM attempt.

The timeout, RSS, process, temporary-size, and archive-size monitors remain
procedural/sample-based controls, not hard OS quotas. A process crash leaves its
reservation open and blocks continuation. A documented resolution requires
confirmed process absence and reliable measured elapsed time; the runner does
not retry or silently clear the reservation.

## Provenance and evidence

The runner checks the exact registered nodeid, clean registered science
worktree, source and controller identities, campaign contract and decision,
bound artifact SHA-256 values, the collect-only receipt and its raw-byte hash,
and the exact authorized manifest before reservation. It records the
reservation receipt before launching the single-node child process. Afterward,
it separates the scientific verdict from the provenance verdict and requires
the sidecar and state archive for a scientific PASS. QPOST binds its source run,
eligibility record, transition decision, archive, and criteria before processing.

The contract validator explicitly does not cryptographically authenticate the
Owner. Local JSON decisions and file hashes establish consistency and
traceability, not signer identity or tamper-proof storage. The designated
controller and Owner-controlled archive remain part of the trust boundary.

## Checks run on this candidate

The following checks use synthetic fixtures or static analysis only; they do
not collect or execute any registered VV3D scientific nodeid:

- Controller policy, contract, ledger, and runner-gate tests: **307 passed**.
- Science preparation synthetic tests: **49 passed, 24 registered science cases
  deselected**.
- Ruff, Python compilation, policy JSON parsing, and `git diff --check`: passed.

These checks are local candidate evidence. GitHub reported no status checks or
workflow runs for the then-current PR heads; no CI result is claimed here.

## Readiness boundary

The implementation and local synthetic checks are ready for Owner review. The
campaign itself remains `PREPARATION_AUTHORIZED_EXECUTION_NOT_AUTHORIZED`. Before
any scientific attempt, the Owner must approve the frozen campaign contract;
the release policy must designate a clean controller checkout by exact HEAD,
tree, and provenance fingerprint; and official collect-only receipts and
authorized manifests must be generated and validated against those final
identities. This PR does not perform those steps or grant that authorization.
