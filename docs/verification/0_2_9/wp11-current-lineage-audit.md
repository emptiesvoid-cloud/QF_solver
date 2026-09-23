---
doc_id: DOC-029-WP11-CURRENT-LINEAGE-AUDIT
revision: 1.0
status: ready-for-owner-review
---

# WP11 — current lineage audit

## Result

```text
AUDIT_STATUS = PASS_WITH_LIMITATIONS
WP11_STATUS = READY_FOR_OWNER_REVIEW
WP11_CANDIDATE_POINTS = 6/6
WP11_OFFICIAL_POINTS = 0/6
STRUCTURAL_RERUN = NO
FULL_TEST_SUITE = NOT_RUN
```

The existing WP11 M1/M2/M3 evidence was retained and checked after bringing
the current local governing lineage into the WP11 qualification branch. No
raw result was regenerated or overwritten.

## Provenance

```text
BRANCH = codex/wp11-qualification
HEAD = 476726bdbf545de6a5511bde85a1fb6731097181
LOCAL_GOVERNING_HEAD = 3e4f79161c0484563387a55d3de9c19c5389f9b3
REMOTE_GOVERNING_HEAD = 04d1f1a60dcb4435c925cf5f788302da698aaf0e
BASE_SHA = 04d1f1a60dcb4435c925cf5f788302da698aaf0e
RUNNER_SHA = b3bec329b4ae6a4c3f3f3e8ef9d221fd12fea13c
EXECUTION_SHA = f9bb50f8f1fe8d6920a81ebe61f1730214a469e0
EVIDENCE_COMMIT_SHA = 6ec88ca384120ae1ec495344809e03ba66c24b7b
CONTRACT_SHA256 = 37876e3da02b1ca9a97ee535d8e2026131cc61900f3d478a578d9398ff0eb0d6
MANIFEST_SHA256 = 7bebaa7d7f0f1d5da875a2a46841519f4e99e734cc8d5d6ae160be62774c06bc
EXECUTION_SHA_IS_ANCESTOR_OF_HEAD = YES
EVIDENCE_COMMIT_IS_ANCESTOR_OF_HEAD = YES
PRODUCTION_SOURCE_DIFF_BASE_TO_HEAD = NONE
WORKING_TREE = CLEAN
ACTIVE_WP11_PROCESS = NONE
PUSH = NOT_PERFORMED
```

The execution and evidence commits remain in the Git ancestry. The local
governing branch contains the WP09/WP10 administrative closure, while the
remote governing ref remains unchanged. This package therefore does not
claim that the remote has been updated.

## Results retained

| Gate | Result | Scope |
| --- | --- | --- |
| M1 | `PASS_CANDIDATE` | serial SciPy TET4 static baseline, 24 DOFs |
| M2 | `PASS_CANDIDATE` | PETSc/GAMG, 2 MPI ranks, 24 DOFs |
| M3 | `PASS_REPLAY` | fresh-process replay, deterministic fields equal |

The recorded M1/M2 maximum absolute displacement difference is
`3.308722450212111e-24`, with maximum relative difference
`6.422498112526624e-16`. The M2 residual is
`1.9690961052303745e-26`; M2/M3 observable deltas are zero.

The reference is a file-backed independent observable comparison. It is not
an independent global FEM/Newton solve and no Code_Aster or other external
solver correlation is claimed.

## Verification performed on this branch

```text
TARGETED_TESTS = 49 passed, 1 skipped
GIT_DIFF_CHECK = PASS
JSON_VALIDATION = PASS
PRODUCTION_MECHANICS_CHANGED = NO
THRESHOLDS_CHANGED = NO
STRONG_SCALING_CLAIM = NO
WEAK_SCALING_CLAIM = NO
```

The contract remains marked `PREPARATION_ONLY`; this audit does not promote
it retroactively. Official WP11 points remain `0/6` until an explicit Owner
decision records acceptance of the bounded 24-DOF TET4 PETSc/MPI scope.

## Limitations retained

- TET4 static path only;
- bounded 24-DOF smoke qualification;
- input arrays replicated per rank;
- no partitioned HDF5 input;
- no strong- or weak-scaling claim;
- no dynamics, contact or friction qualification;
- no external FEM solver correlation.

## Next step

Owner review of the bounded WP11 candidate. If accepted, record the decision
in the official ledger before any governing-branch push. No WP11 points are
awarded by this audit.
