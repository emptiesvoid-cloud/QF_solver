# WP-E01-R — Hencky Tangent Review and Guarded Verification

**Date:** 2026-10-21
**Worktree:** `C:\wpc01-frictionless-public-integration-wt\wp-e01-q`
**Branch:** `codex/qf-wp-e01-q-hencky-tangent-20261021`
**Owner baseline:** `cb75e731aa146d54f177d7080a8d698b0bdd4fcd`

## Outcome

The independent constitutive review completed without a P0/P1 scientific blocker. The fixed-target supervisor was prepared and committed. One parent preflight stopped before pytest, due to a registry-parser mismatch. After correcting that supervisor-only parser, the supervisor verified the Windows Job Object limits and launched one collection child. Pytest reported 35 nodes, matching the frozen authorized node set, but the collection guard then exited with code 5 because its separate registry parser has the same trailing-comma defect. No accepted collection receipt was written, so the supervisor correctly did not launch the test phase.

**No tangent test body ran.** This campaign produced no new numerical tangent result. The historical WP-E01-P3 result of 41/41 material-point tests remains preserved and is not evidence for the new tangent.

## Status

| Item | Result |
|---|---|
| `HENCKY_MATERIAL_POINT_VNV` | `PREVIOUS_41_PASS_BOUNDED` |
| `HENCKY_TANGENT_COLLECTION` | `35_OBSERVED / BLOCKED` |
| `HENCKY_TANGENT_NUMERICAL_VNV` | `NOT_RUN` |
| `HENCKY_TANGENT_INDEPENDENT_REVIEW` | `COMPLETED` |
| `HENCKY_GLOBAL_FEM_ASSEMBLY` | `NOT_RUN` |
| `HENCKY_INCREMENTAL_NEWTON` | `NOT_RUN` |
| `SCIENTIFIC_QUALIFICATION` | `NOT_ACQUIRED` |
| `WP_E01_STATUS` | `OPEN / EXPERIMENTAL_TARGET` |

## Independent scientific review

A distinct read-only reviewer inspected the frozen tangent source, test module, preparation report and manifest. The reviewer found no P0/P1 issue in the stated chain rule, the first and second Fréchet derivatives, tensor contraction order, PK2/PK1 transformations, confluent limits, admissibility delegation, or expected hyperelastic Hessian major symmetry. The tangent remains isolated from element and Newton routes.

The reviewer recorded a P2 evidence limitation: the multistep centered-difference assertions accept based on the minimum error in a sweep, so a passing assertion alone would not prove a convergence plateau or order. General non-diagonal cases compare the production tangent to finite differences of the production stress response; independent Decimal/closed-form references are limited to diagonal, identity and volumetric cases. No runtime behavior was assessed by that review.

## Registry parser diagnosis

The registered test entry in `tests/conftest.py` is a valid three-string tuple with a Python trailing comma:

```python
"tests/unit/test_wp_e01q_hencky_tangent.py": (
    "NUMERICAL_UNIT",
    "...",
    "a99bcc6ea32bff3e2a669d2923380033f23e587aab95f612ab4047f98b7d7b50",
),
```

The first supervisor implementation used a regex that required the digest to be followed directly by `)`. That parent preflight failed before starting any child. I changed only the Q-specific supervisor check to parse the registry as Python AST and require a unique three-string tuple with the frozen digest and `NUMERICAL_UNIT` classification. Static cases accepted valid tuples with and without a trailing comma, and rejected wrong classification, wrong digest, wrong path, missing classification, extra fields and duplicate registration. The actual frozen registry was accepted by that check.

The collection guard still uses a separate regex in `experiments/wp_e01q_hencky_tangent_collection_guard.py:101-109`; it also rejects the valid trailing comma. This is the direct cause of the blocked collection. The guard was not changed after the collection attempt.

## Execution chronology

1. Verified the corrected Owner branch, origin, starting HEAD, clean worktree, and frozen tangent, test, registry, preparation-manifest and preparation-report hashes.
2. Completed the separate scientific review. No P0/P1 blocker was found.
3. Committed the fixed-target guard/supervisor and runtime manifest.
4. Initial supervisor invocation created no pytest child and stopped at parent registry preflight. Preserved summary: `qualification/0_2_12/wp_e01_q_execution_2026-10-21/20261021T153449Z/summary.json`.
5. Corrected the supervisor's registry parser, updated its runtime-manifest pin, and committed the correction.
6. Invoked the fixed-target supervisor once at committed HEAD `36db240869a1025ef1c180a5781dc5b36d098c63`. Parent preflight passed. One collection child ran under the Job Object. Its stdout contained 35 unique node IDs; comparison to the runtime manifest showed an exact set match. Pytest printed `35 tests collected in 0.56s`, then the collection guard rejected the registry tuple and exited 5. No collection record or success receipt was created. No run phase or test body was started.

The exact node lines are preserved in `qualification/0_2_12/wp_e01_q_execution_2026-10-21/20261021T153838Z/collect/stdout.log`. They matched the 35 node IDs listed in the frozen runtime manifest. Since the guard did not write its own collection inventory and receipt, the collection was observed but not accepted.

## Runtime containment evidence

The collection child command was fixed to `C:\Python313\python.exe -S -m pytest` with the collection guard plugin, `--collect-only`, and only `tests/unit/test_wp_e01q_hencky_tangent.py`. The parent used `shell=False`, created the child suspended, assigned it to the Job Object, and only then resumed it.

| Measurement | Observed |
|---|---:|
| Child PID while in Job | `700` |
| Active PIDs after resume | `[700]` |
| Active PIDs after exit | `[]` |
| Child exit code | `5` (guard rejection after discovery) |
| Wall time | `1.155634 s` of `120 s` |
| Process committed-memory cap | `268,435,456 bytes` |
| Job committed-memory cap | `268,435,456 bytes` |
| Peak process committed memory | `77,582,336 bytes` |
| Peak job committed memory | `77,582,336 bytes` |
| Active process limit | `1` |
| Kill on Job close | `true` |
| Breakaway allowed | `false` |
| Cleanup | `VERIFIED_WINDOWS_JOB_CLOSED` |
| Collection stderr | empty |

These are committed-memory values, not RSS/working-set measurements. The supervisor's collection acceptance failed because the child exit code was nonzero; the measured containment itself matched the configured limits. No test execution followed.

## Frozen identities

Scientific and target identities remained unchanged:

| File | SHA-256 |
|---|---|
| `src/solveur/materials/finite_strain_hencky_tangent.py` | `31109bbbf2353f9bbd86b7a7b0e5fe776016fdd1638550848b58b8bd4afef135` |
| `tests/unit/test_wp_e01q_hencky_tangent.py` | `a99bcc6ea32bff3e2a669d2923380033f23e587aab95f612ab4047f98b7d7b50` |
| `tests/conftest.py` | `23db87ce25e78f54bb23e382014d69e322fdf2cbe68823914930c8d6d8969305` |
| `qualification/0_2_12/wp_e01_q_hencky_tangent_execution_manifest_2026-10-21.json` | `22dfce5f7daac1a1c96628a6d93c82381880a934f11639927f3bf6d6f8ee1e55` |
| `qualification/0_2_12/wp_e01_q_hencky_tangent_preparation_2026-10-21.md` | `8cc674365d50c8c03d19f8328a3f3236baa031eddd8db29023f2b21fb851eb23` |

Final execution profile identities before report-only commit:

| File | SHA-256 |
|---|---|
| `experiments/wp_e01q_hencky_tangent_supervisor.py` | `dd06c9c427ff915c3d9a6a23aebde5828c69ec9a645c47ca539e56e491998f89` |
| `experiments/wp_e01q_hencky_tangent_collection_guard.py` | `0e15f504c367ef022e20f4d326f73539d54e6a2b3e87c98d925a5bed36b317ae` |
| `experiments/wpc01_exploratory_supervisor.py` | `9bd8c75b19b49c758f9558cf9299eeedc18762b1e40dbd69968377a94d6c9090` |
| `qualification/0_2_12/wp_e01_q_hencky_tangent_runtime_execution_2026-10-21.json` | `6a45a28ceb135e48f1debfd4ae7c1a05f1b6b78b5fdc87131d37b48e5950ccc1` |

All 18 runtime `source_identity_sha256` entries matched the actual file bytes at preflight. The supervisor and collection guard bindings also matched their actual hashes. Production and test files were not modified.

## Evidence hashes

Second invocation output root: `qualification/0_2_12/wp_e01_q_execution_2026-10-21/20261021T153838Z/`.

| Evidence | SHA-256 |
|---|---|
| `collect/stdout.log` | `66d9be8c2634a2ceac5f03b86be9d6f249656a5c3b24138ef575aee92ecf4abd` |
| `collect/stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `collect/phase_result.json` | `8f0e730e60a28c75ab1e91c3d6e9a41b121c2f583337a98a63dc81702044371a` |
| `preflight.json` | `7c48cfe0f6a1a68f63af0f1a6229ba8244b6e60279cbdfc4ba0854559b913e5a` |
| `summary.json` | `5fdd591fbb55356a83272ddb3b8a8bf65b8c2b1d52dce9b2d15280f453cd206e` |
| `evidence_hashes.json` | `fdf7b258fbf090866fc8a46c73db002e66dd9f811eba9496c8127a051612e408` |

The first, pre-child parent-preflight summary SHA-256 is `5f5fd4ac1284c91f51d68df166ececa31f6e6e064b04885eb4c637602018d26f`; its `evidence_hashes.json` SHA-256 is `a4fbad6974860a977f0492a8df1c8f2011188233507f08495a0d5bf91801972f`.

## Next Owner decision

Authorize one targeted collection-guard correction: replace its regex-based registry check with AST validation of the exact unique three-string tuple, enforcing the fixed target path, `NUMERICAL_UNIT`, and frozen test digest. Then update the guard/runtime-manifest pins, commit and review the new executable identity, and authorize one fresh guarded collection followed by the same conditional 35-node RUN. The present GO was consumed by a blocked collection and does not authorize a rerun against a changed guard identity.

No numerical test bodies ran in this campaign. No source or threshold change to the Hencky material or tangent is recommended from this execution.
