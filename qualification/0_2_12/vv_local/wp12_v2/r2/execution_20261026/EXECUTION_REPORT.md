# WP12-V2-R2 — single authorized attempt, 2026-10-26

**SCIENTIFIC_ATTEMPT_PERFORMED · PYTEST_EXECUTION_STATUS=FAIL · OVERALL_SCIENTIFIC_STATUS=INCOMPLETE · WP12_STATUS=OPEN · WP13_STATUS=OPEN**

The one Owner-authorized attempt was executed and preserved. It stopped on a TypeError in the prospective test's diagnostic code, before producing the scientific JSON payload. This is not a demonstrated failure of a mechanical oracle or of the production TET4 implementation. No retry, source change, threshold change, new solve or refinement followed the failure. The attempt budget is exhausted: **1/1 used, 0 remaining**.

## Identity and preserved evidence

- Campaign: `WP12-V2-R2-H1-OPERATOR-AUDIT-002`; case `TET4-H1-OPERATOR-AUDIT-002`.
- Exact nodeid: `tests/unit/test_wp12_v2_tet4_operator_audit.py::test_tet4_h1_operator_audit_002`.
- Manifest SHA-256: `a0eb16a37ab1c4e23e6624b77d829d091a7a1ac4635617a0038034d50611a503`.
- Run ID: `20261026T150049Z-ac1279749bfb`; started `2026-10-26T15:00:49.376317Z`.
- Receipt SHA-256: `1e275f9e92f8fa0a5d7e5b21b7c15fd055579be0d5c24ca66aeccc151358d13a`.
- Separate Owner decision SHA-256: `de487adb117fea0dc256a943cd9ae6f0f9ffe53c5145dc3d3e6296d74712d0a9`; operational registration `2026-10-26T15:00:28Z`, expiry `2026-10-27T15:00:28Z`. This is the explicitly accepted local, non-cryptographic decision route.
- Local evidence: `E:\QFSolverWP12B\wp12-local-vv-evidence\WP12-V2-R2-H1-OPERATOR-AUDIT-002\TET4-H1-OPERATOR-AUDIT-002\20261026T150049Z-ac1279749bfb\`.

The [sanitized provenance record](RUN_PROVENANCE.json) includes the six evidence-file hashes, receipt/decision/preflight identities, terminal ledger record, exact selection and frozen identities. Raw stdout/stderr, JUnit, selection, receipt and local Owner/preflight records remain preserved locally. Hostname and unrelated local/account data from raw JUnit are not published in the summary. The receipt and its existing hash inventory were verified without editing or adding files to the run directory. Both the one-attempt reservation and terminal record remain intact.

## Preflight and provenance outcomes

All 35 SHA-256/Git-OID inventory entries matched before launch and after execution. The science checkout `00428adf38e9397340ac136f6f503a268eb671da` / `df4ec667bf746b042c900fad1f86bf542e1a437b`, tests `67813b4a36a057bbaa9e5fba32bcdea66ddf4df3` / `ffee889f0cd70b089ec8e1719b84a667babfa1be`, and runner `731fd9d6b05efe227de60e8cb19ba095cc8b29d9` / `19b775be2d49890b890c41b6d56f5b1be082279b` were clean and unchanged before and after.

The dedicated Python 3.13.17, Pytest 8.4.1, NumPy 2.2.6, SciPy 1.15.2, h5py 3.14.0 and threadpoolctl 3.6.0 matched. The non-numerical diagnostic child observed all six thread variables at `1`, OpenBLAS 0.3.29 at one thread, and DLL SHA-256 `6547e9fb966e9773caee2755e91a8bf4d6f3a2f0eebf9646b0158f8675ea4ab5`. The full argv matched the approved command including `-s`; no existing campaign destination or reservation was reused.

The actual scientific child collected exactly the one approved nodeid. Its selection record has `exact_match=true`, `source_import_ok=true`, `sys_path_unchanged=true` and `import_error=null`; solveur resolved to `E:\QFSolverWP12B\science\src\solveur\__init__.py`. This run therefore demonstrates that the R2 collection/import correction passed its actual provenance gate.

## Exact execution result

| Recorded quantity | Value |
|---|---:|
| Process exit code | 1 |
| Runner-supervised wall time | 1.738046 s |
| JUnit suite time | 1.270 s |
| JUnit testcase time | 0.935 s |
| Selected / executed testcases | 1 / 1 |
| JUnit failures / errors / skips | 1 / 0 / 0 |
| stdout / stderr bytes | 10,514 / 0 |
| Timeout / output cap / interruption | false / false / false |
| Raw runner status / pytest status | FAIL / FAIL |
| Numeric marker | NOT_EXPOSED |
| Overall scientific status | INCOMPLETE |

These timings characterize this aborted test invocation, not FEM solver performance. No CPU/RAM peak was measured by this runner. Its accepted local limitations still apply; no sandbox, hard resource quota, process attestation or independent archive is claimed.

## Cause and stage coverage

The JUnit failure is exactly:

```text
TypeError: list indices must be integers or slices, not tuple
tests/unit/test_wp12_v2_tet4_operator_audit.py:482
```

In the [frozen prospective test](../../../../../../tests/unit/test_wp12_v2_tet4_operator_audit.py), `scalar_local` is a Python list of matrices (line 425). The first invalid access is `scalar_local[element, row, column]` (line 482); the same error also exists at line 492 as `scalar_local[element, column, row]`. Indexing must select the list element first, then index its matrix, for example `scalar_local[element][row, column]`. The nearby batch accesses are valid because `batch_local` is an ndarray. A separate read-only worker checked both occurrences and the definitions; no code was changed. Confidence in this diagnosis is high.

The exception location shows that the test advanced through fixture/archive identity checks, scalar/batch preparation, one-chunk assembly and CSR capture checks, DDL/scatter checks and the exact free-matrix comparison. It invoked roundoff/symmetry diagnostic routines and then failed while constructing the `(14,22)` scalar contribution record. The relevant values remained in the failed process's memory and were not exported. This stage coverage is inferred from the executed source/traceback; it is not a substitute for the absent scientific output.

The final contributor assertion, 24-column matrix-free checks, archived-field residual/reaction/energy evaluations, negative controls, final mandatory acceptance list and JSON emission were not reached. No assertion-record payload exists, so individual final criteria cannot be labeled PASS from this run.

## Requested quantitative H1 assessment

| Requested evidence | Acquired current-run result |
|---|---|
| All 24 matrix-free columns; absolute/relative Frobenius, infinity and maximum errors | NOT_ACQUIRED; stage not reached. |
| Scalar/batch/reference numerical discrepancies | NOT_ACQUIRED in preserved observables; no metric values emitted. |
| Global K-Kᵀ and elements 0/8/9 contribution values | NOT_ACQUIRED; contribution serialization failed. |
| Independent residuals, reactions, force/moment balance | NOT_ACQUIRED; stage not reached. |
| Energy, external work and exact identity checks | NOT_ACQUIRED; stage not reached. |
| Archived displacement difference and terminal/conjugate displacement | NOT_ACQUIRED; stage not reached. |
| Arithmetic assumptions / bound satisfied | null / null in the missing-payload classification. |
| Gamma scientific status | INCONCLUSIVE, because required scientific data are missing; no evaluated bound is evidenced. |

The recorded gamma INCONCLUSIVE is a missing-evidence classification, not an observed satisfied gamma bound with unresolved arithmetic assumptions. Overall INCOMPLETE must be preserved. No earlier WP12-S/U numerical value is relabeled as a current-run measurement. U3's historical FAIL is unchanged. This run neither establishes nor disproves full matrix-free/direct equivalence on H1; it supplies valid execution provenance and a test-instrumentation defect diagnosis.

## Next decision and WP12-W

The minimal prospective correction is limited to the two list/matrix indexing expressions in the test. It requires a new test commit/tree and manifest SHA-256 while preserving the scientific source, numerical values, gamma protocol, fixtures and the now-working R2 runner. A focused synthetic check of the diagnostic data structure should precede a new freeze. No repair was applied to the approved frozen test and no extra attempt is authorized by the remaining validity time of the current decision.

Do not launch W1/W2 on the basis of this incomplete result. Retain the existing WP12-W preparation, obtain the intended H1 exported operator/archived-field evidence under a separately authorized prospective test, then review its non-gamma criteria and explicit gamma reserves before deciding on bending refinement. No further rotor, contact, benchmark or production-physics investigation is required by this instrumentation failure.

WP12 and WP13 remain OPEN. WP12-W remains PREPARED_NOT_AUTHORIZED. All historical sources, manifests, tests and WP12-S/U records are preserved.
