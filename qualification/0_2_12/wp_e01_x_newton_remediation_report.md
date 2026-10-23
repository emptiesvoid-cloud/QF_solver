# WP-E01-X — Newton Test and Supervised Reporting Remediation

Date: 2026-10-21
Worktree: `C:\wpc01-frictionless-public-integration-wt\wp-e01-x`
Branch: `codex/wp-e01-x-newton-test-remediation-20261021`

## Result

The three Stage V test failures were corrected in the test module without changing the Newton implementation or numerical tolerances. Supervisor reporting now distinguishes an unlaunched run from a completed failed run and refuses to count incomplete pytest lifecycles as passes. The original reporting simulation suite passed 18/18 after its hash registration was current. A later independent-review follow-up identified and closed a collection evidence-index binding gap; the expanded reporting suite then passed 22/22.

The 16-node Newton suite was **not collected or executed**. This campaign did not authorize either action. The source freeze is prepared for a separate `GO-COLLECT`, followed by a separate `GO-RUN` after the collection receipt is accepted.

Historical U/V/W outcomes remain unchanged: U 31/31 PASS; V 13 PASS / 3 FAIL from 16 authorized nodes; W read-only review completed. Those outcomes are historical evidence and are not restated as new verification.

## Baseline and provenance

The required starting state was verified: HEAD `e4fc700a3a4dfba7482da1fbd0e6ae56030fff10`, branch `codex/wp-e01-uvw-hencky-global-newton-20261021`, origin `https://github.com/emptiesvoid-cloud/QF_solver.git`, clean worktree. The report supplied for U/V/W matched SHA-256 `dc254d1228796023a04e98c690b45434c29c18bff35297550a0de7ab59fac9ff`.

The historical V `preflight.json` and runtime manifest each pin 34 source entries. A raw Git-blob comparison initially showed 29 byte differences, caused by Windows CRLF checkout bytes versus normalized LF Git blob bytes. A separate reviewer checked the original WP-E01-UVW Windows worktree and confirmed that **all 34/34 raw source hashes match** the historical preflight/runtime pins; after line-ending normalization, all 34/34 also match the Git tree at V commit `4a3b5323e49dc0276174a4dc40cb31e425a20cae` and W/X baseline `e4fc700a3a4dfba7482da1fbd0e6ae56030fff10`. This is line-ending representation, not source-content drift or a historical manifest inconsistency. The historical U/V evidence remains valid for its exact tested checkout bytes. The X static freeze independently records the actual bytes in the X worktree, including the changed test/registry/supervisor identities.

No production file under `src/` was modified in this campaign. Current frozen source identities include:

| File | SHA-256 |
|---|---|
| `src/solveur/materials/finite_strain_hencky.py` | `b318dad553073f848b96528c61589ab2015c1eb1dd8fa52cb0bd52d13b09eab2` |
| `src/solveur/materials/finite_strain_hencky_tangent.py` | `31109bbbf2353f9bbd86b7a7b0e5fe776016fdd1638550848b58b8bd4afef135` |
| `src/solveur/verification/experimental_hencky_global.py` | `e02baaf346c3b8f853049990c8ac053b5e76ffab92f0a138f167f997cd2503b9` |
| `src/solveur/verification/experimental_hencky_newton.py` | `1a24046913a4544aadba8dbec715f796ef56069f3cdbe813fd871a630950ffb0` |

## X1 — accepted-state partition assertions

The two failing nodes were the TET4 and HEX8 parameterizations of `test_final_equilibrium_is_independent_of_admissible_load_partition`. Each compared the exact accepted-state identity after the existing displacement comparison had already passed.

The state identity includes the exact displacement bytes. Separate converged load partitions can differ by floating-point roundoff while satisfying the already frozen displacement bound. The replacement keeps that existing check unchanged (`rtol=0`, `atol=2e-10 m`), then requires exact mesh fingerprint and load-factor equality and confirms that both accepted displacement arrays remain immutable. Exact identity assertions in rollback tests were not changed. No tolerance was raised and no state field was dropped.

## X2 — non-equilibrium initial-state scenario

The old test changed a dead-load entry to 500 N but called `initial_state()` at its default `load_factor=0`, so the tested external load was zero. The no-rejection result was correct for that setup.

The corrected fixture retains a balanced witness using the original fixture load, target displacement, and `lambda=1`. The rejection case evaluates the target displacement at `lambda=1` with the deliberately changed 500 N free dead load, then checks the actual global assembler residual against an independent diagonal PK1/area reference before calling the refusal method.

For `mu=2.5e6 Pa`, `kappa=6e6 Pa`, `s=1.08`, and `L=0.1 m`:

```text
P11 = (kappa + 4 mu / 3) log(1.08) / 1.08
    = 665095.4172258 Pa
TET4 free-node area = L^2 / 6
f_int = P11 L^2 / 6 = 1108.492362043 N
R_f = f_int - lambda f_dead = 1108.492362043 - 500
    = 608.492362043 N
```

The existing acceptance limit is `1e-8 N + 1e-9 ||lambda f_dead||`; for this one-entry 500 N load it is `5.1e-7 N`. The analytical residual exceeds that limit by about `608.492361533 N`. This is an analytical fixture calculation and source-level reference; the corrected Newton test itself was not run. The balanced witness is a call to `initial_state` with the original matching load at `lambda=1`, so an incorrect rejection would fail before the unbalanced case.

## X3 — outcome reporting and staged supervisor

`experiments/wp_e01uvw_newton_reporting.py` derives counts from pytest hook reports, not console text. It checks target and hash identity, exact node allowlist, schema, stored-count consistency, pytest/parent exit agreement, and process completion/containment. The parent Job Object phase record is authoritative for completion and containment; `run_results.json` hook reports are authoritative for per-node outcomes; stdout/stderr corroborate but do not define counts.

The status distinctions are:

| Evidence | Status |
|---|---|
| RUN phase never launched | `NOT_RUN` |
| Complete, contained pytest run with a structured failed node and exit 1 | `RUN_FAILED` |
| Complete, contained exit-0 run with no failed nodes | `RUN_PASSED` |
| Missing/malformed/contradictory reports, incomplete node lifecycle, exit mismatch, or failed containment | `RUN_INCOMPLETE` |

The run summary preserves collected, passed, failed, skipped, xfailed, xpassed, and interrupted counts. A `RUN_PASSED` run with skips or xfails is not a full target pass: `full_pass_target_met` remains false and campaign acceptance is `TARGET_NOT_MET`.

The report interpreter validates the per-node lifecycle. A pass requires successful setup, call, and teardown reports. Missing setup/call/teardown is counted as interrupted, never passed. Duplicate phases, invalid phase ordering, contradictory setup/call combinations, skipped teardown, malformed types (including unhashable phase/outcome JSON values), unknown nodes, and conflicting count/exit evidence fail closed. Strict XPASS remains visible as both a failed node and an xpassed diagnostic.

The supervisor now checks the complete collection-receipt field set and each emitted value before accepting a later RUN: node inventory/count, exact integer exit code (not boolean), classification, phase, target, source commit/map, manifest and guard hashes, output path, containment, cleanup, and no-retry state. Collection and RUN remain separate invocations; RUN requires a receipt-pinned manifest and refuses existing RUN artifacts.

## Follow-up — Collection evidence-index binding

A second read-only reviewer identified a P2 evidence-chain gap: RUN validated the collection phase-result fields but did not verify the phase-result bytes against the collection evidence hash index. This was corrected without changing Newton behavior or test thresholds. The receipt schema is now v2 and records the SHA-256 of the collection evidence index. To avoid a hash cycle, the index excludes the receipt, summaries, and evidence-index files; it includes the phase result, collected-node inventory, collection runtime-manifest snapshot, preflight record, and stdout/stderr logs. Before RUN, the supervisor verifies the receipt-pinned index digest, recomputes the complete evidence map, requires those six evidence files, and rejects any missing, extra, altered, malformed, or duplicate-key index entry. The future RUN manifest must pin the final receipt digest. This is source-level integrity validation; no collection receipt or runtime acceptance was created in this campaign.

## Validation performed

Authorized simulated-only command:

```text
C:/Python313/python.exe -m pytest -q tests/unit/test_wp_e01uvw_newton_reporting.py
```

The original source-freeze run observed **18 passed, 0 failed, 0 skipped in 0.54 s**. An earlier attempt observed 18 skipped because the PURE_UNIT hash registration had not yet been updated after editing the simulation module; the registration was corrected and that run passed. After evidence-index hardening, the same command was rerun. The first updated run produced **21 passed / 1 failed** because the duplicate-key regression expected a specific diagnostic while the helper correctly failed closed with a generic wrapper message. The diagnostic was made specific, and the final run produced **22 passed, 0 failed, 0 skipped in 0.59 s**. All outcomes are retained; no Newton numerical node was selected.

Static checks passed on the final source freeze:

* `py_compile` for the supervisor, guard, reporting helper, Newton test module, and reporting simulation module.
* Ruff on those files plus `tests/conftest.py`.
* Python AST parsing and literal registry checks.
* All 34 static-manifest source SHA-256 pins matched current file bytes after the follow-up updates.
* The 16-node allowlist was unique and remained the same historical target inventory.
* The Newton module remained `NUMERICAL_UNIT`; the synthetic reporting module remained `PURE_UNIT`; their exact registry digests matched.
* Both guard and supervisor static-manifest pins matched the static manifest digest.
* `git diff --check` passed after normalizing the new JSON manifest to LF. The first check caught CRLF whitespace in that manifest; it was normalized, repinned, and committed.

The target collection/runtime graph was not launched. No claim is made here about runtime Job Object enforcement for this new supervisor identity; a new collection must establish the supervisor’s runtime containment receipt before any test body may run.

## Independent read-only review

A separate reviewer checked the assertion changes, lifecycle accounting, collection receipt checks, and historical source-pin comparison. The state-comparison and non-equilibrium test corrections preserve the intended physics and existing thresholds. The reporting helper no longer accepts call-only reports as passes. The full receipt is field- and value-validated, including rejecting boolean `false` as integer exit code zero. The reviewer confirmed all 34 historical Windows checkout bytes match their V pins; 29 raw Git-blob hash differences are CRLF/LF normalization only. On a separate follow-up, the reviewer found the evidence-index omission described above; after correction, the reviewer read the receipt-v2 generation and RUN validation path and reported no P0/P1/P2 findings. This remains source-only review; the runtime evidence index was not produced or accepted.

The reviewer identified no remaining P0/P1/P2 defect in the corrected X source package and no historical source-content discrepancy. Both reviews were read-only and did not run tests or numerical calculations.

## Frozen identities and commits

Static freeze manifest: `qualification/0_2_12/wp_e01_x_newton_execution_manifest_2026-10-21.json`
SHA-256: `1f8f423e7347f1b1ce4a58b73b3907b73e35199060185982b3dd0fec79ce56bc`
It pins 34 files and the exact 16-node allowlist. The guard and supervisor embed this static-manifest hash.

| File | SHA-256 |
|---|---|
| `tests/unit/test_wp_e01uvw_newton.py` | `5ad19f7e563efc4ae2f40805c7d8b15c4cb59b32136b185b6147349b4d3ff0a2` |
| `tests/unit/test_wp_e01uvw_newton_reporting.py` | `966bb3f9b95005dc4a5d8a94f4f60b6d24604da921ee88529ab6a5c11872d34b` |
| `experiments/wp_e01uvw_newton_reporting.py` | `eed8f852e24e7c89d41ecf844e209171bae8e5970e50bb493c9851a091822301` |
| `experiments/wp_e01uvw_newton_collection_guard.py` | `e5ea3bbe695c4380a5445694f62e0c2cc415ab361faf6f85d1171ed463d41ccb` |
| `experiments/wp_e01uvw_newton_supervisor.py` | `d3986e408a9e9739165cc1f01e52cbddddb6fcf012f26601e30511373c957892` |
| `tests/conftest.py` | `113f5c6267689e31df3b73fa3f333421488967b1358085809a8dadfd20de9e3` |

Commits:

* `4b8860f585b8fa6e839aa89944b8646f6ea53889` — test/reporting corrections and initial static freeze.
* `a9c1b6b82ee09b20e335340321646e8a58164521` — canonical LF manifest bytes and corresponding guard/supervisor pin update; this freeze was superseded by the evidence-index follow-up.
* `181cf315f50a6a963895cbdb43abc4be5beea7b0` — receipt-v2 collection evidence-index binding, strict validator, and synthetic regressions; current source freeze and static-manifest repin.
* This report is committed separately after the source freeze; its final evidence HEAD is recorded in the handoff response.

The current source-freeze commit contains no production `src/` changes. The static manifest is the committed new freeze. A phase-specific runtime manifest is intentionally not authorized or frozen for execution by this source-only campaign; `PREPARATION_ONLY` must be converted to a separately authorized `COLLECT` profile at the next Owner GO, then a `RUN` profile must bind the accepted receipt-v2 and evidence-index digest under a second GO.

## Current limits and next decision

Preserved status:

* `GLOBAL_ASSEMBLY=VERIFIED_BOUNDED` — historical bounded U result only.
* `INCREMENTAL_NEWTON=PARTIAL` — Stage V remains 13/16, with original failures preserved.
* `GENERAL_NEWTON_QUALIFICATION=NOT_ACQUIRED`.
* `AUTHORITATIVE_INTEGRATION=PENDING`.
* Public release and production route activation are not authorized.

The next Owner decision is an exact-path **GO-COLLECT** for `tests/unit/test_wp_e01uvw_newton.py`, bound to source-freeze commit `181cf315f50a6a963895cbdb43abc4be5beea7b0`, static manifest SHA-256 above, and the changed executable/support hashes above. It must authorize only guarded collection with the existing Job Object bounds (256 MiB process and job commitment caps, one child, 120 seconds, kill-on-close, no retries). If and only if collection produces an accepted exact 16-node receipt-v2 and evidence-index binding, request a distinct **GO-RUN** bound to that receipt. The exact parent phase commands are:

```text
C:/Python313/python.exe -m experiments.wp_e01uvw_newton_supervisor --phase collect
C:/Python313/python.exe -m experiments.wp_e01uvw_newton_supervisor --phase run
```

The supervisor’s manifest must authorize the corresponding phase. No collection, Newton execution, production solver, native FEM, Gmsh, Armijo activation, merge, release, or qualification promotion occurred in WP-E01-X.
