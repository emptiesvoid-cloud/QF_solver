# WP12-A autonomous controller recovery and execution

**Status:** `BLOCKED_BY_UNRESOLVED_CONTRACT`
**Current phase:** synthetic controller recovery complete; PR/CI, controller designation, fresh WP07 preflight/manifest and scientific execution pending.

## Scope and safety

Work is isolated on branch `fix/wp12a-dynamics-launcher-contract`, based on canonical launcher commit `6422e6188b1b9e17abcb2e51c0724fc69e45e6a7`, in the new worktree `C:\Users\fari\.codex\worktrees\wp12a-launcher-fix\qf_solver`. The pinned shared controller and scientific worktree were not modified. No policy, allowlist, mandate, budget, scientific test, solver, oracle, threshold, or historical result was changed.

No FEM, assembly, eigensolve, Newmark or harmonic body ran. The end-to-end test replaces the supervised child with a stub that captures the exact command and environment, writes synthetic output files, and returns a controlled process result; it does not call pytest.

## Root causes and corrections

1. The execution CLI exposed `--preflight-id`, but `run_pytest()` rejected it for `wp12_dynamics`. The WP12-A path now accepts the ID, verifies the receipt checksum and schema, exact nodeid, current source/controller identities before and after collection, solver origin, skip/body/return-code attestations, registered DDL and timeout, and unchanged ledger attestations. `prepare-manifest` now requires this receipt for dynamics and stores its ID, path and SHA-256. Execution revalidates the receipt, compares it with the manifest, and archives it in `run.json` before reserving.
2. The WP12 manifest validator returned no `decision_id`, while attempt reservation indexed that field unconditionally. The validator now returns an optional decision ID, and ledger reservation uses `.get()`; manifests that have no separate decision ID remain valid under the existing Owner-decision fields and retain their authorization ID in the ledger.
3. The synthetic full-path test found that WP12 manifests were passed to the HEX20-specific child-provenance contract without the associated attempt ID and `run.json` path. That optional environment contract is now passed only to the WP12-B HEX20 route that supplies the full triplet.

These changes are limited to controller behavior. The WP12-Dynamics allowlist remains at 13 exact nodes; no source or policy registration changed.

## Synthetic validation

- `python -m pytest tests/unit/test_development_autonomous_policy.py tests/unit/test_wp12b_diagnostic_provenance.py -q --tb=short` — **190 passed**.
- `python -m ruff check scripts/development_autonomous.py tests/unit/test_development_autonomous_policy.py tests/unit/test_wp12b_diagnostic_provenance.py` — **passed**.
- `python -m py_compile scripts/development_autonomous.py tests/unit/test_development_autonomous_policy.py tests/unit/test_wp12b_diagnostic_provenance.py` — **passed**.
- `git diff --check` — **passed**.
- Policy loads successfully with 12 registered worktrees and 13 unchanged WP12-A allowlisted nodeids.
- Synthetic coverage includes refusal of missing/tampered preflights, exact manifest/preflight binding, exact scope/mandate, source/controller/solver identity, nodeid, DDL and timeout checks, zero reservation on refusal, one synthetic reservation on approved path, and durable run/ledger output. WP12-B sidecar tests were included.

## CI and integration status

The repository's required GitHub quality workflow runs the broad `tests/unit` and `tests/integration` suites; the workflow also includes engineering FEM campaigns and controlled benchmarks. Those jobs can execute scientific models. Triggering them now would violate the task restriction against real scientific tests during correction. Therefore no push or PR was created, no CI run was started, and there is no PR/CI status to report. The local branch is ready for review.

No merge, shared-controller update, or `AGENTS.md` designation change was made. These actions are not authorized implicitly by a green local synthetic suite. The required release checkout, new official controller fingerprint, WP12-A collect-only receipt, and replacement manifest must be prepared only after integration/designation is authorized. The earlier WP07 manifest and decision are not transferable to a changed controller identity.

## Next authorized steps

1. Resolve whether GitHub CI may run its existing scientific test and FEM jobs for this controller-only PR, or provide an approved CI route that runs only non-scientific checks without changing repository gates.
2. Create and review the technical PR, run the authorized CI checks, then obtain the applicable integration approval. Do not merge or change the pinned controller before that approval.
3. After canonical designation, recalculate controller identity, verify the clean science checkout and solver origin, collect the exact WP07 node, and prepare a new source/controller/preflight-bound manifest. Keep it `PREPARED_NOT_AUTHORIZED` and request a new Owner decision on its SHA-256.
4. Only after that new decision, reserve and execute one WP07 attempt using the canonical launcher. Preserve complete output for pass, assertion failure, refusal or timeout. Do not retry a consumed attempt.

No scientific result exists for this recovery branch. WP07 remains unexecuted under the new controller.
