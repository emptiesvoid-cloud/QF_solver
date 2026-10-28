# WP12-A post-campaign infrastructure recovery

**Status:** `WP12A_POST_CAMPAIGN_RECOVERED_PENDING_INTEGRATION`

**Scope:** synthetic/controller and evidence-writer recovery only. No FEM test
body, assembly, eigensolve, harmonic solve, Newmark step, preflight, reservation,
or scientific retry was run in this task.

## Findings

The consumed Newmark attempt `dev-301ba3b31a43` failed in the observables writer
before pytest assertions. Its authorized manifest was in
`authorizations/wp12_dynamics/owner-authorized/`; all three WP12-A sidecar
writers accepted only the parent `authorizations/wp12_dynamics/`. The refusal
was therefore a path-contract mismatch. The attempt remains `PYTEST_FAILED`,
its numerical sidecar was not produced, and its mechanical verdict is not
established. No retry is authorized by this change.

The reduced-harmonic and base-motion preflights were bound to Dynamics v2 ledger
SHA-256
`1b16630787734661fb542cc95d0654f61fade7abeb31819dd0fc7c7824046685`. The
Newmark attempt advanced that ledger, so those receipts correctly fail the
current-ledger identity check. The controller’s strict preflight validation is
unchanged; stale receipts are not made valid by this patch.

## Changes prepared

- The Newmark, reduced-harmonic, and base-motion writers now read the captured
  controller policy, validate its hash, derive the evidence root, and accept
  only the exact scope authorization directory or its direct
  `owner-authorized` child. The configured authorization path must remain under
  the evidence root. A symlinked `owner-authorized` directory, nested manifest
  directories, and paths outside the configured root are rejected. Manifest
  SHA-256, Owner state, nodeid, source identity, attempt layout, and atomic
  write checks remain enforced.
- The controller synthetic suite now includes the observables archive tests.
  CI path filters, Ruff, and compilation cover the changed writer modules and
  their synthetic tests.
- Added the just-in-time procedure in
  `WP12A_DYNAMIC_JUST_IN_TIME_PREPARATION.md` and linked it from `AGENTS.md`.
  Each sequential case must be prepared only after the preceding attempt is
  archived, using a new collect-only preflight and manifest against the current
  ledger. A previous Owner decision does not transfer to a replacement
  manifest.

No runner, policy, solver equation, scientific oracle, threshold, historical
manifest, decision, receipt, refusal, archive, or ledger was changed.

## Synthetic validation

The complete `scripts/run_wp12_controller_synthetic.py` suite finished with
**254 passed, 0 failed, 0 skipped, 0 errors**. This includes synthetic cases for
all three writers accepting the exact `owner-authorized` location, rejecting a
nested manifest path, preserving sidecars after a controlled assertion failure,
and refusing to overwrite existing output. The campaign test advances only a
temporary synthetic ledger, proves the old preflight is refused, then creates a
collect-only receipt and a `PREPARED_NOT_AUTHORIZED` manifest bound to the new
ledger state.

Additional checks passed:

- Ruff on the runner entry point, controller synthetic runner, policy tests,
  three writer modules, and archive synthetic tests.
- Python compilation of the same changed Python files.
- `development_autonomous_policy.json` parses as JSON.
- `git diff --check`.

The first focused archive run exposed Windows path-length overflow in newly
added synthetic fixture names. The fixture names were shortened; the rerun
passed all 24 archive tests. This did not involve production evidence paths.

## Historical campaign state preserved

- Generic ledger SHA-256 remains
  `20670ceedfe1cc969ce614df13b8bd94b108f43e2e2892cf1601a8607a3dad37`.
- Dynamics v2 ledger SHA-256 at report time is
  `3000ea966c1803a845c2a3b9694a663eebe65d8a62b61f07d4876232ac2b19a2`;
  its predecessor link remains bound to the generic ledger above. It contains
  two WP12-A records, for 7/130 total inherited-plus-current attempts.
- Historical Newmark outcomes remain `PASS / PYTEST_FAILED / PASS` in the
  generic ledger, followed by the separate consumed `PYTEST_FAILED` attempt in
  Dynamics v2. The harmonic-reduced and base-motion historical entries remain
  unchanged. WP07 remains the recorded `PASS`.
- The Newmark failure report, sidecars (including their absence), preflight
  receipts, and the two stale-preflight refusals remain untouched.

## Next preparation gate

The code change is on a dedicated branch based on release HEAD
`40d88187b3e640f2d5eef0d054c71877c5fb08d5`, pending PR integration. The active
scientific worktree `E:\QFSolverAgents\wp12-dynamics` was not modified. After
the code is integrated, its three writer changes must be propagated to that
scientific source and the exact WP12-A node registrations refreshed, because
their source fingerprints will change. Only then can the official controller
run fresh collect-only preflights and prepare new manifests.

No preflights or manifests were generated here. Newmark, reduced harmonic, and
base motion each require separate Owner decisions tied to their new manifests.
The reduced-harmonic and base-motion cases must be prepared just in time after
the preceding reservation updates the ledger. Old manifests and decisions are
not reusable. No classification here upgrades a development result to formal
qualification.
