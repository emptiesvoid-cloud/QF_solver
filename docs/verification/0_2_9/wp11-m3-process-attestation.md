---
doc_id: DOC-029-WP11-M3-PROCESS-ATTESTATION
revision: 1.0
status: controlled_evidence
---

# WP11 R2 M3 process-event attestation

## Purpose and status

This addendum supplements the already-recorded WP11 R2 M3 replay evidence. It performs no solve and changes no historical result. It correlates the four M3 result records with retained events from the local Docker daemon.

```text
ATTESTATION_TYPE = POSTHOC_EXTERNAL_PROCESS_ATTESTATION
AUDIT_TIME_UTC = 2026-09-23T10:37:55Z
BRANCH_AT_AUDIT = codex/wp11-qualification
HEAD_BEFORE_ADDENDUM = a6e70ca0f772b8a1ea6c4f450ef324107b104e74
CONTRACT_SHA256 = 308e531be35c680d35e4532720e1b6185cf4eff4891acad14308c39225a330c2
AUTHORIZED_SOURCE_SHA = f122032cbac77b98137b61f27907ba28755a250a
AUTHORIZED_RUNNER_SHA = f122032cbac77b98137b61f27907ba28755a250a
M3_SOLVES_RERUN = NO
HISTORICAL_RESULT_FILES_MODIFIED = NO
LEDGER_OR_OWNER_DECISION_CHANGED = NO
PUSH = NO
MERGE = NO
```

The frozen contract requires a fresh-process replay manifest, but it does **not** list a solver `policy_digest` among its provenance requirements. The R2 result files do not contain such a field. Its absence is therefore a future provenance-hardening opportunity, not a violation of this frozen contract; no digest has been invented or retroactively inserted.

## Evidence source and correlation method

The local Docker daemon's retained `container` events were queried read-only for `2026-09-22T19:59:00Z` through `2026-09-22T20:00:00Z`, filtered to the exact pinned image in the R2 contract. The events show four distinct containers, each bound to the WP11 qualification checkout at `/workspace`, each started and then terminated with `exitCode=0`. Their recorded image digest matches the frozen contract.

The M3 JSON records are themselves hash-checked and contain `fresh_process=true`, the family-specific runner command, process ID, start time, source SHA, runner SHA, contract SHA, image digest, and runtime versions. Their start times fall inside the corresponding short-lived container intervals.

The family-to-container association below is **chronological/serial correlation**, not an explicit identity link: the M3 JSON has no Docker container ID, and the Docker events have no family label or family-specific output-directory attribute. The four event sequences do not overlap and align in order with the TET4, HEX8, TET10, HEX20 M3 timestamps and the recorded serial campaign order. This supports the fresh-container interpretation, but is weaker than a prospective manifest that writes the container ID into each result.

| M3 family (correlated by order) | M3 result SHA-256 | Result start UTC / in-container PID | Docker container ID | Container start → die UTC | Exit |
|---|---|---|---|---|---:|
| TET4 | `2f7517e4d733ffa5c8d529595895f46f758f12e19ac7ac2723369b1190994e93` | `2026-09-22T19:59:18.757125Z` / 9 | `5788bce52e169ebc3143ddf248d207e029faa4a6f1ca491c68719001e4105ae1` | `19:59:17.775623128Z` → `19:59:18.991845153Z` | 0 |
| HEX8 | `b863fab0f8333ec3fee11afa7d00d83ced7ee6a8802637208c3e0362d80a5ad2` | `2026-09-22T19:59:20.406057Z` / 8 | `b036ae0fc5480730f6238e132e2090d8f5168e07320dd643b5967202f0f6dd73` | `19:59:19.416291131Z` → `19:59:20.642927623Z` | 0 |
| TET10 | `78958000b2595f8c0bfab38956581089cb0e38c6673a206ae8a254ebce8842b1` | `2026-09-22T19:59:22.048453Z` / 9 | `52cf9a0e40465ef185d7bca118297faec940c80588b96696c696fbcfa6c8a6fa` | `19:59:21.067980045Z` → `19:59:22.307683000Z` | 0 |
| HEX20 | `ede8d28e23e8112eb6ba3b1a6f5d2d35d99ba40876ded8c44cea1169eae811e6` | `2026-09-22T19:59:23.708475Z` / 8 | `3745570d3d0865f11d99430b87d990b2a4ffc0f5fd17a16e51b436141615d3ea` | `19:59:22.698419694Z` → `19:59:23.957251633Z` | 0 |

All four results report the same contract SHA, authorized source/runner SHA, pinned image digest `ghcr.io/fenics/dolfinx/dolfinx@sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8`, two MPI ranks, and `status=PASS`. The JSON result hashes and normalized Docker event fields are recorded in the companion machine-readable attestation.

## Scope and interpretation of the source change

The source diff from comparison base `04d1f1a60dcb4435c925cf5f788302da698aaf0e` to the authorized execution source `f122032cbac77b98137b61f27907ba28755a250a` contains one source path:

```text
A src/solveur/large/multifamily.py
```

Thus, no pre-existing solver kernel was modified in that diff, but a new bounded production assembly/model/linear-solve route was added. The unqualified statement “production mechanics unchanged from the governing baseline” would be inaccurate. The narrow statement “pre-existing mechanics kernels were not modified; the new bounded multi-family route was added” is supported.

## Conclusion and remaining limitation

The Docker event history adds independent, post-hoc evidence that four separate containers using the frozen image and a bind mount of the WP11 checkout started and exited successfully in the same serial sequence as the four M3 records. Family mapping is inferred from timestamps and campaign order because no shared container identifier was written into the result records. No evidence here upgrades the NumPy observable recomputation into an independent global FEM solve or supports an MPI scaling claim.

This is an audit addendum only. It does not change the existing Owner decision, WP11 points, global ledger, qualification scope, or limitations. For future runs, the runner should persist the Docker container ID, host process invocation, explicit process exit code, and policy/configuration digest prospectively in each result and replay manifest.
