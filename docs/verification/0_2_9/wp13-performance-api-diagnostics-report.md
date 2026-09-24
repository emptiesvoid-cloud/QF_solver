---
doc_id: DOC-029-WP13-RESULT-001
revision: 0.1
status: candidate_for_owner_review
applicable_version: 0.2.9-development
---

# WP13 — performance, API et diagnostics

## Verdict

`WP13_STATUS = PASS_CANDIDATE_WITH_LIMITATIONS` for the bounded scope below.
No official points have been awarded. No score or ledger was changed.

The execution used the prospective contract `QF-029-WP13-EXEC-001`, frozen
before tests and measurements. The governing baseline is
`9c4048dc1909520e3933f86b2b62a9bfd6562c2c`; the exact execution commit is
`f08800b5d80f3640cef5e15dd9df1be1e90962f7` on
`codex/wp13-wp14-overnight`.

## API and diagnostic verification

The exact frozen command completed with exit code 0:

```text
python -m pytest tests/unit/test_public_api_contract.py tests/unit/test_audit_detail_levels.py tests/unit/test_nonlinear_performance.py
11 passed in 2.61s
```

This covers the current public facade inventory and stability labels, selected
API signatures, compatibility imports, a documented load/check/solve/save
workflow, invalid-input/serialization rejection, additive audit detail
levels, retention of WARNING/FAIL rows, and the bounded nonlinear campaign
harness. The negative behaviors are assertions in the existing tests; none
were removed or weakened.

## Bounded nonlinear performance observations

The existing `VNV-J2-NONLINEAR-PERFORMANCE-006` campaign returned
`PASS_INTERNAL` for both declared families. Measurements are local and
descriptive only.

| Element | DOFs | Elements | Increments | Newton iterations | Solve time [s] | Peak Python allocation [bytes] | Max relative residual |
|---|---:|---:|---:|---:|---:|---:|---:|
| TET4 | 204 | 140 | 24 | 33 | 8.837795 | 5,945,507 | 4.06118e-9 |
| TET10 | 1,023 | 140 | 24 | 33 | 35.614007 | 12,967,703 | 7.49374e-9 |

Time covers the solve after mesh import. Memory is `tracemalloc` Python
allocation peak, not process RSS. The cases are small cyclic J2 bars; these
numbers do not support performance ranking, speedup, mesh-scaling, HPC,
cross-machine, or general solver-performance claims.

The existing campaign preserves meshes, setup files and aggregate metrics,
but does not persist full displacement fields or a complete solver-result
object. This package therefore cannot independently recompute the campaign
metrics from the full solution state; its scope is the existing internal
characterization and checked-in campaign gates.

## Provenance and integrity

- Contract SHA-256: `5d9faa73032c8d2441003e31ad13b1d49292b9a4a2a2aead86ab3b8168c43305`
- Governing policy digest: `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`
- Runtime: Windows 10 build 19045; Python 3.13.1; 6 physical / 12 logical CPUs; 102,963,109,888 bytes RAM; NumPy 2.2.6; SciPy 1.15.2; Gmsh 4.15.2; pytest 8.4.1.
- Production `src/` has no diff from the governing baseline. No solver mechanics, threshold, or policy changes were made.
- The JSON execution record and evidence manifest contain exact commands, source/test hashes, raw campaign file hashes and sizes.

## Status and boundaries

```text
API_TESTS = PASS
DIAGNOSTIC_TESTS = PASS
PERFORMANCE_HARNESS = PASS
BOUNDED_TET4_TET10_CAMPAIGN = PASS_INTERNAL
FULL_TEST_SUITE = NOT_RUN
PRODUCTION_MECHANICS_CHANGED = NO
THRESHOLDS_OR_POLICY_CHANGED = NO
WP14 = NOT_RUN
WP13_OFFICIAL_POINTS = 0
MERGE_OR_PUSH = NOT_PERFORMED
```

The current machine ledger assigns WP13 one point, while the frozen roadmap
assigns it two. This report does not resolve that allocation discrepancy.
The package is evidence for Owner review only; it does not qualify every API,
diagnostic, element family, analysis method, or performance regime.
