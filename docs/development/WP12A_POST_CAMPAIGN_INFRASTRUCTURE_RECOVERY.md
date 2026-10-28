# WP12-A post-campaign infrastructure recovery

**Status:** `WP12A_POST_CAMPAIGN_RECOVERY_CONTROLLER_DESIGNATION_REVIEW_PENDING`

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

## Changes integrated and prepared

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
- PR #57 was merged to `emptiesvoids-cloud/0.2.12` as
  `5d3d239aae90506efa2db40ff9af115e794f7bea`. The release contains the writer
  fix and the synthetic tests above.
- The exact three writer fixes were applied to the registered scientific
  worktree and committed as `5f96dd604fe40279ead0186f49be77e7a0bbeac1` on
  `codex/wp12-dynamic-harmonic-verification`. This changes only test-sidecar
  instrumentation; it does not change solver equations, numerical criteria,
  oracles, or thresholds.
- The controller candidate appended source registrations for the three exact
  nodeids against that science HEAD. The active allowlist remains 13 nodeids;
  registration history grew from 34 to 37 records. No earlier registration
  was replaced.
- Candidate registration fingerprints are Newmark
  `d4743785db99a79181281429827d0de688e5eae94e9ad285491040aaa75c7a8e`, reduced
  harmonic `3a8c1324d0563214911e8f9abca87c09ddf98907d5d8ab01c822640c82baa4fe`,
  and base motion
  `f16bbeea012b8c86924215156b1ffbac23d2248d0b0194067bcd9af36a3c3909`.
- A clean detached controller candidate is pinned at
  `C:\Users\fari\.codex\worktrees\wp12-shared-controller-dynreg-20261028\qf_solver`:
  HEAD `b206e6f520e9b03c3c925c3bef20883f01aa9800`, tree
  `6f16b0d1d5fe204707e6b784355d34c943f18db5`, official fingerprint
  `e48d4e61f04df2819431465130b12c3d36f24f6f92fbdf8221f44190442e1e08`.
  A prospective root `AGENTS.md` pin and its unambiguous-resolution test are in
  branch `fix/wp12a-source-registration-20261028`, awaiting PR review and CI.

No runner, policy, solver equation, scientific oracle, threshold, historical
manifest, decision, receipt, refusal, archive, or ledger was changed.

## Synthetic validation

The complete `scripts/run_wp12_controller_synthetic.py` suite finished with
**254 passed, 0 failed, 0 skipped, 0 errors** on the registration/designation
candidate after the full suite was rerun. This includes synthetic cases for
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

PR #57 is merged. The candidate registration/designation change is on branch
`fix/wp12a-source-registration-20261028`, based on that merge, and still needs
its own review and CI before the root designation can take effect. The
scientific worktree changes described above are limited to the three sidecar
writers and have refreshed append-only registrations. No preflights or
manifests have been created yet; they must be generated only after the
designation change is integrated, and each preflight must bind the then-current
Dynamics v2 ledger.

No scientific calculation, reservation, or preflight was performed. Once the
controller designation is integrated, prepare a fresh Newmark collect-only
preflight and manifest against the current ledger. Reduced harmonic and base
motion must be prepared just in time after each preceding attempt is archived;
their old preflights/manifests/decisions are not reusable. A Newmark pytest
failure remains historical and its mechanical verdict is still not
established. No result here upgrades development status to formal
qualification.
