# WP-E01-P1 Windows path identity correction

Date: 2026-10-21

Branch: `codex/qf-wp-e01-m-logarithmic-strain-20261021`

Starting HEAD: `55de89a18dfdc2414af73ca5be260eb5535cbcce`

## Defect and correction

The WP-E01-O runtime manifest records the repository as
`C:/wpc01-frictionless-public-integration-wt/wp-e01-m`. On Windows,
`str(ROOT)` from the supervisor is
`C:\wpc01-frictionless-public-integration-wt\wp-e01-m`. These strings name the
same directory, but the old raw string comparison rejected the manifest.

The supervisor now uses `_repository_path_matches()` at the same preflight
gate. It requires a nonempty absolute string, resolves the expected and
declared paths with `strict=True`, requires both to be directories, and checks
`Path.samefile()`. Invalid, relative, nonexistent, non-directory, or different
paths return false and retain fail-closed preflight behavior. This accepts
slash-style and equivalent `.`/`..` component variations without accepting a
different repository or relying on the current directory to interpret a
relative manifest path.

The runtime manifest's supervisor SHA-256 pin was updated. Its schema,
repository value, target, test count, source map, and resource contract were
otherwise preserved. The Hencky kernel and test module were not modified.

## Static regression cases

The exact helper function was extracted from the supervisor AST and evaluated
with only `pathlib.Path` supplied. This was a bounded path-identity check; no
pytest, collection, numerical code, supervisor, or solver was launched.

| Case | Expected | Observed |
|---|---:|---:|
| Existing worktree in backslash form | Accept | Pass |
| Same worktree in forward-slash form | Accept | Pass |
| Absolute path with existing `experiments/..` components | Accept | Pass |
| Existing parent directory | Reject | Pass |
| Nonexistent directory | Reject | Pass |
| Existing file instead of directory | Reject | Pass |
| Relative manifest path | Reject | Pass |
| Empty manifest path | Reject | Pass |
| Non-string manifest path | Reject | Pass |

Additional AST/source checks confirmed the supervisor still calls its manifest,
repository-identity, SHA-256, registry, and test-safety gates. The existing
source-map pins were recomputed from disk. Source checks confirmed the 256 MiB
process/job limits, one active process, suspended child creation, Job Object
containment, accounting, and collection-before-run sequence remain present.
`git diff --check` passed. No pytest, collection, WP-E01-P execution, FEM, or
numerical test ran.

## Independent read-only review

A separate reviewer inspected the supervisor and manifest diff. The reviewer
found the change narrow and the comparison fail-closed for invalid, unresolved,
non-directory, and different targets. It confirmed the target/kernel/registry,
guard/helper, baseline, source-map, Job Object, timeout, process-limit, and
no-retry bindings remain unchanged. The reviewer did not execute helper cases,
collection, pytest, or the supervisor; this review is source-level only.

## Frozen identities

| File | SHA-256 |
|---|---|
| `experiments/wp_e01o_hencky_supervisor.py` | `3f129c264504c9b84b39d910bf6de39f4a36e36c677d730cc7078d108f24ce2f` |
| `qualification/0_2_12/wp_e01_o_hencky_execution_manifest_2026-10-21.json` | `1709f56ebdb6767dd5484e500d917aac46ef42b4206f7a6e7c1ba39c882a9bf5` |
| `src/solveur/materials/finite_strain_hencky.py` | `b318dad553073f848b96528c61589ab2015c1eb1dd8fa52cb0bd52d13b09eab2` |
| `tests/unit/test_wp_e01m_hencky_material_point.py` | `cdd2651e9427c0e64284a75671d83d4f14cdd916a979759be0422f44dde84bfc` |
| `tests/conftest.py` | `33304c38c2ef53aca2b3abc647e490db91245e56b1eb8d04963db1c86e9d8605` |
| `experiments/wp_e01o_hencky_collection_guard.py` | `a9ff067c68887d2d0a291acaf847ee4be1548f4120ce789ca39395760caaa945` |
| `experiments/wpc01_exploratory_supervisor.py` | `9bd8c75b19b49c758f9558cf9299eeedc18762b1e40dbd69968377a94d6c9090` |

Runtime manifest SHA-256: `1709f56ebdb6767dd5484e500d917aac46ef42b4206f7a6e7c1ba39c882a9bf5`.

Static WP-E01-M manifest SHA-256 remains `42ca471ba4ae6379efa819573ed1c19f743754f48b4d21213bbc2673fdde75ed`.

## Next execution proposal

After a separate Owner GO binds the final commit and these identities, use only
the manifest's fixed parent invocation:

```text
C:/Python313/python.exe -m experiments.wp_e01o_hencky_supervisor
```

The supervisor performs guarded collection, requires the exact 41-node target
inventory, rechecks the frozen identities, and launches the run phase only if
the collection receipt and containment checks pass. Do not invoke pytest
directly. The existing 256 MiB per-process/job limits, 120-second parent
deadline per phase, one active child, suspended assignment-before-resume,
kill-on-close, no-retry, and no-parallel-pytest settings remain in force.

## Status

`PATH_IDENTITY_DEFECT: CORRECTED_BY_SOURCE`

`SUPERVISOR_RUNTIME_VNV: NOT_RUN`

`HENCKY_HISTORICAL_VNV: 35_PASS_1_FAIL`

`HENCKY_NEW_COLLECTION: NOT_RUN`

`HENCKY_NEW_EXECUTION: NOT_RUN`

`SCIENTIFIC_QUALIFICATION: NOT_ACQUIRED`

`WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET`
