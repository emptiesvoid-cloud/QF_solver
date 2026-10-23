# WP-E01-P3 registry binding repair

Date: 2026-10-21

Worktree: `C:/wpc01-frictionless-public-integration-wt/wp-e01-m`

Branch: `codex/qf-wp-e01-m-logarithmic-strain-20261021`

Starting HEAD: `babcc63486525fbc9efb5eb1aef7703b81f16997`

## Defect and correction

The runtime manifest's `safety_registry` object contains exactly `path`,
`sha256`, and `classification`. The supervisor compared it with a two-key
dictionary, so Python's exact dictionary equality rejected the valid manifest.

The supervisor now uses `_registry_binding_matches()` and requires the exact
three-field binding:

```json
{
  "path": "tests/conftest.py",
  "sha256": "33304c38c2ef53aca2b3abc647e490db91245e56b1eb8d04963db1c86e9d8605",
  "classification": "NUMERICAL_UNIT"
}
```

Exact dictionary equality rejects missing and unexpected fields as well as
wrong paths, hashes, classifications, and malformed values. The check remains
fail-closed. The runtime manifest itself retains the classification field.

## Static regression review

The exact path and registry predicates were extracted from the supervisor AST
and evaluated directly with standard-library inputs. No supervisor, pytest,
collection, FEM, or numerical code was run.

Registry cases all passed: valid three-field binding; incorrect classification;
missing classification; incorrect digest; incorrect path; extra field;
malformed non-dictionary input. Path cases all passed: slash and backslash
forms of the worktree; an equivalent absolute path containing `experiments/..`;
a different existing directory; nonexistent path; relative path; and invalid
input.

The remaining preflight comparisons were checked against the frozen runtime
manifest: target path, digest, `NUMERICAL_UNIT` tier, 23 function names and 41
expected nodes; kernel; guard; supervisor; Job Object helper; Python/pytest/
NumPy profile; parent invocation; resource limits; static manifest; baseline;
and source-map identity. All 26 source-map entries matched local bytes. The
existing 256 MiB process/job commit limits, 120-second per-phase parent
deadline, one active process, suspended child assignment before resume,
kill-on-close, no-breakaway, no parallel pytest, and no-retry settings remain
unchanged. The original P2 supervisor invocation failed during preflight before
child creation; no pytest node was collected or executed.

A separate read-only reviewer confirmed the exact three-key schema, the
updated supervisor pin, all 26 source-map pins, and the unchanged containment
contract. It found no correction required. This was source/manifest review
only; the reviewer did not run pytest, collection, the supervisor, or numerical
tests.

## Frozen execution identity

| File | SHA-256 |
|---|---|
| `experiments/wp_e01o_hencky_supervisor.py` | `53ab796de8015306c9d1bc81cc7433a7480865e7055bc7cdaa8382424e4abbbb` |
| `qualification/0_2_12/wp_e01_o_hencky_execution_manifest_2026-10-21.json` | `8d581b53742a0e9b6a419b103335e09f553e20bec17171f3fbcec0f63eb9dc16` |
| `src/solveur/materials/finite_strain_hencky.py` | `b318dad553073f848b96528c61589ab2015c1eb1dd8fa52cb0bd52d13b09eab2` |
| `tests/unit/test_wp_e01m_hencky_material_point.py` | `cdd2651e9427c0e64284a75671d83d4f14cdd916a979759be0422f44dde84bfc` |
| `tests/conftest.py` | `33304c38c2ef53aca2b3abc647e490db91245e56b1eb8d04963db1c86e9d8605` |
| `experiments/wp_e01o_hencky_collection_guard.py` | `a9ff067c68887d2d0a291acaf847ee4be1548f4120ce789ca39395760caaa945` |
| `experiments/wpc01_exploratory_supervisor.py` | `9bd8c75b19b49c758f9558cf9299eeedc18762b1e40dbd69968377a94d6c9090` |

Runtime manifest SHA-256: `8d581b53742a0e9b6a419b103335e09f553e20bec17171f3fbcec0f63eb9dc16`.

Static WP-E01-M manifest SHA-256 remains
`42ca471ba4ae6379efa819573ed1c19f743754f48b4d21213bbc2673fdde75ed`.

## Conditional invocation

After commit and fresh identity verification, the single authorized parent
invocation is:

```text
C:/Python313/python.exe -m experiments.wp_e01o_hencky_supervisor
```

No direct pytest fallback is permitted. The supervisor must accept the exact
41-node collection receipt and containment checks before launching RUN.

## Status at preparation

`REGISTRY_BINDING_DEFECT: CORRECTED_BY_SOURCE`

`SUPERVISOR_RUNTIME_VNV: NOT_RUN`

`WP_E01_P3_COLLECTION: NOT_RUN`

`WP_E01_P3_EXECUTION: NOT_RUN`

`HENCKY_HISTORICAL_VNV: 35_PASS_1_FAIL_PRESERVED`

`HENCKY_CONSISTENT_TANGENT: NOT_IMPLEMENTED`

`SCIENTIFIC_QUALIFICATION: NOT_ACQUIRED`

`WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET`
