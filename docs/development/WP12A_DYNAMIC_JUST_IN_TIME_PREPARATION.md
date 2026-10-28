# WP12-A sequential case preparation

WP12-A cases share the append-only Dynamics v2 attempt ledger. A successful
reservation changes that ledger's SHA-256. The controller binds each collect-only
preflight and each prepared manifest to the exact ledger state observed during
preflight, and refuses execution if the ledger has changed since then.

Prepare and review one case at a time:

1. Complete and archive the preceding case, including its final ledger receipt.
2. Read the current Dynamics v2 ledger and verify its predecessor link to the
   immutable generic ledger. Do not reset either ledger.
3. Run the official exact-node collect-only preflight with a new, unused ID:

   ```powershell
   python <official-launcher> preflight --worktree wp12_dynamics --target <exact-nodeid> --preflight-id <new-pf-id>
   ```

4. Require `PREFLIGHT_PASS`, exactly one collected nodeid, no skip, no test body,
   no reservation, and no ledger mutation. Preserve the receipt and its SHA-256.
5. Prepare a new, unique manifest bound to that preflight:

   ```powershell
   python <official-launcher> prepare-manifest --worktree wp12_dynamics --target <exact-nodeid> --authorization-id <new-manifest-id> --preflight-id <new-pf-id>
   ```

6. Verify the manifest remains `PREPARED_NOT_AUTHORIZED` and submit its exact
   SHA-256, nodeid, identities, budget, preflight receipt, and current ledger
   identity for a separate Owner decision. Preparation is not authorization.
7. Only after that exact decision has been recorded may the single approved case
   be invoked through the official `test --scope fem_exploratory` route. Preserve
   the resulting attempt and ledger records even if pytest fails.
8. Before preparing the next case, return to step 1 and obtain a fresh preflight
   and manifest against the newly advanced ledger.

Do not prepare a batch of manifests against one ledger snapshot for sequential
execution. A reservation by case A invalidates the preflights and manifests for
cases B and C that were prepared against the earlier ledger, even if their
scientific source and controller identities have not changed. Preserve stale
receipts and manifests as historical records; create new IDs rather than
overwriting them. An Owner decision for a stale manifest is not transferable to
its replacement.

This procedure does not authorize a case, add a retry, or change a scientific
criterion. Collect-only preflights do not run test bodies or reserve attempts.
