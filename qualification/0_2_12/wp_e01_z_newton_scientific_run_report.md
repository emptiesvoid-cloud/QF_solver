# WP-E01-Z â€” Incremental Newton Scientific Run: Precheck Blocked

## Decision

`PRECHECK_BLOCKED`. No WP-E01-Z supervisor invocation, pytest collection, test body, or Newton calculation was launched. The accepted WP-E01-Y receipt is valid for its frozen collection identity, but that identity no longer equals the current checkout HEAD. The Owner instruction explicitly prohibits bypassing an exact-HEAD requirement.

The one-use GO-RUN was therefore not exercised. No test results or pass/fail counts are claimed for WP-E01-Z.

## Repository and identity evidence

- Worktree: `C:\wpc01-frictionless-public-integration-wt\wp-e01-x`
- Branch: `codex/wp-e01-x-newton-test-remediation-20261021`
- Current HEAD at precheck: `c3c16278ce7b862137299c6a7d3bafd5c70f836e`
- Source HEAD recorded by the accepted Y collection: `ec96b6b7be084dc114077a88f4c2d0e9327b71ca`
- Origin: `https://github.com/emptiesvoid-cloud/QF_solver.git`
- Worktree was clean before this report was created.

The only commit after the collection source HEAD was the documentary/evidence commit `c3c16278ce7b862137299c6a7d3bafd5c70f836e`. Its added paths are the Y report, collection artifacts, and a COLLECT-phase runtime manifest; it changed no Newton source, test, safety registry, collection guard, supervisor, or scientific implementation. This verifies source continuity, but does not waive the supervisorâ€™s exact Git HEAD binding.

The static manifest remains SHA-256 `1f8f423e7347f1b1ce4a58b73b3907b73e35199060185982b3dd0fec79ce56bc`. All **34/34** frozen source pins matched current file bytes at precheck. The static allowlist contains the same 16 unique node IDs.

Key unchanged executable identities:

| File | SHA-256 |
|---|---|
| Newton test module | `5ad19f7e563efc4ae2f40805c7d8b15c4cb59b32136b185b6147349b4d3ff0a2` |
| `tests/conftest.py` | `113f5c6267689e31df3b73fa3f333421488967b1358085809a8da8dfd20de9e3` |
| Collection guard | `e5ea3bbe695c4380a5445694f62e0c2cc415ab361faf6f85d1171ed463d41ccb` |
| Supervisor | `d3986e408a9e9739165cc1f01e52cbddddb6fcf012f26601e30511373c957892` |
| Job Object helper | `76e71e833280b92c2478ec8aed187a473bf5f4002e5983c2386f37b58e9bbe62` |

## Accepted WP-E01-Y receipt

The existing Y collection remains accepted, without alteration:

- Receipt: `qualification/0_2_12/wp_e01_x_newton_execution_2026-10-21/20261021T195229Z/collection_receipt.json`
- Receipt SHA-256: `ab4d7f0fac08b2fdb877747eb7dc681af35d232507a55208e326a35616a1edd8`
- Collection runtime-manifest SHA-256: `21b3ffc433b833f020d3da53b124a59d9b7668ff861838ab939794fb9601def9`
- Evidence-index SHA-256: `2b4af90c20e692fe8aec21fbdb29a628db5482c7ee04299c4e8114609a7d05bf`
- Receipt records `accepted=true`, `execution_phase=COLLECT`, `node_count=16`, containment and cleanup verified, and automatic retry disabled.
- The indexed evidence map was recomputed and matched exactly at precheck.

The Y report is [wp_e01_y_collection_report.md](wp_e01_y_collection_report.md). Its collection result remains 16 authorized nodes observed, with no test bodies run.

## Exact supervisor incompatibility

The current runtime manifest is still `execution_phase=COLLECT`, with `source_commit=ec96b6b7be084dc114077a88f4c2d0e9327b71ca` and `accepted_collection=null`. It is not a RUN authorization profile.

The supervisor source at `experiments/wp_e01uvw_newton_supervisor.py` enforces both of these constraints:

1. `_load_inputs()` rejects unless `runtime["source_commit"] == current_git_head` (source lines 284â€“288). Using the unchanged Y manifest at current HEAD `c3c16278...` would fail this check.
2. `_load_accepted_collection()` compares the collection snapshot and RUN manifest after removing only `execution_phase` and `accepted_collection` (lines 855â€“860 and 908â€“910). A RUN manifest rebound to current HEAD `c3c16278...` would differ from the accepted collection snapshotâ€™s `source_commit=ec96b6b7...` and be rejected.

No supervisor command was invoked to test this failure. The incompatibility is established by static source inspection and the frozen runtime/receipt identities. No manifest or receipt was rewritten, no checkout was moved, and no guard was bypassed.

## Independent review

A distinct reviewer, `<reviewer-workspace>`, performed a read-only check. The reviewer confirmed that commit `c3c16278...` changed no scientific or safety source, but includes the COLLECT runtime manifest as well as the report and evidence. The reviewer independently confirmed the two exact-HEAD/snapshot checks above and classified them as a hard precheck block. No P0/P1 issue was reported; the review did not run tests or invoke the supervisor.

A contract-preserving future route is possible, but requires a new Owner GO: run from a clean worktree exactly matching the collection source commit with a newly frozen RUN manifest matching the accepted Y collection snapshot. An alternative is a fresh collection and conditional RUN under a single new authorization at the then-current frozen HEAD, with no commit between collection and RUN. This report does not authorize either route.

## Historical results and limits

- WP-E01-Y collection: **16 nodes accepted**, test bodies not run.
- WP-E01-Z corrected Newton RUN: **NOT RUN â€” PRECHECK_BLOCKED**.
- Historical Stage V result remains **13 PASS / 3 FAIL**; it was not rerun or rewritten.
- Reporting simulation result remains the historical **22/22 PASS**; it was not rerun here.
- Bounded global assembly evidence remains historical; no new global or incremental Newton numerical evidence was produced.

## Status

- `WP_E01_COLLECTION`: **ACCEPTED** (WP-E01-Y receipt)
- `WP_E01_Z_PRECHECK`: **BLOCKED â€” source HEAD mismatch with accepted collection**
- `WP_E01_CORRECTED_RUN`: **NOT_RUN**
- `WP_E01_NEWTON_SYNTHETIC_VNV`: **NOT_ESTABLISHED BY THIS CAMPAIGN**
- `INCREMENTAL_NEWTON`: **PARTIAL; no WP-E01-Z run evidence**
- `GLOBAL_ASSEMBLY`: **VERIFIED_BOUNDED** (prior bounded evidence only)
- `AUTHORITATIVE_INTEGRATION`: **PENDING**
- `PUBLIC_RELEASE`: **NOT_AUTHORIZED**
- `GENERAL_NEWTON_QUALIFICATION`: **NOT_ACQUIRED**

No numerical execution, retry, threshold change, source change, integration, or release occurred under this GO.
