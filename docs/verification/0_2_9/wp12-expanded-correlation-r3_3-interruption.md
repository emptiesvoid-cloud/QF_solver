# WP12 R3.3 expanded correlation — interrupted fail-closed attempt

## Outcome

`R3.3 = FAIL_CLOSED_EXECUTION`; it produced no Code_Aster correlation results. The run was stopped after repeated mesh-reader failures, before continuing through all 144 cases. This diagnostic attempt does not alter WP12 points, Owner decisions, R2 evidence, or the governing ledger.

| Execution state | Count |
|---|---:|
| Frozen cases | 144 |
| Completed with Code_Aster exit code 6 | 20 |
| Completed correlation candidates | 0 |
| Case interrupted while running | 1 |
| Cases not started | 123 |
| `aster_raw.json` results | 0 |

All 20 completed cases failed in `LIRE_MAILLAGE`, before `MECA_STATIQUE`, with `MODELISA7_81`: Code_Aster expected an identifier but rejected the numeric node name at mesh line 5. The interrupted case, `tet4_rectangular_beam_h3_axial_x`, has the same mesh-reader diagnostic in its preserved `.mess` log, but no completed process record; it is therefore classified as interrupted, not as a completed failure.

The R3.3 runner generated 21 case directories. Its sibling manifest contains 337 file entries; an independent integrity pass found no missing, extra, size-mismatched, or hash-mismatched files. The raw directory remains local and ignored by Git; its sibling manifest and this audit are versioned.

## Provenance

```text
BRANCH = codex/wp12-expanded-correlation
R3_3_CONTRACT_SHA256 = b7d732a74ff064a44d8bc83558986d6650d96d7c2b5bc4de97594f17f128a0ae
R3_3_FREEZE_COMMIT = c344879781136e32964dae9f6bfd97950a41efa2
R3_3_EXECUTION_SHA = f14d1eee623bfc991ed38e0aa3bd8164e0a1746e
R3_3_RUNNER_SHA = c344879781136e32964dae9f6bfd97950a41efa2
R3_3_MANIFEST_SHA256 = e6e0e4cceb901170806c44ac0dfe7eaf091044f8a76db5b584fbe175c5ee6552
R3_3_MANIFEST_ENTRIES = 337
R3_3_MANIFEST_INTEGRITY = PASS
PRODUCTION_MECHANICS_CHANGED = NO
THRESHOLDS_CHANGED = NO
WP12_POINTS_CHANGED = NO
```

The interruption audit is machine-readable at [wp12_external_vv_r3_3_execution_audit.json](../../../qualification/0_2_9/wp12_external_vv_r3_3_execution_audit.json). No result from this attempt may be counted as external correlation evidence.

## Next prospective revision

R3.3 exposed a second mesh-format constraint: node labels must be valid Code_Aster identifiers, not bare numeric tokens. A short-prefix candidate (`N1`, `N2`, …) was rejected by the regression test because HEX20 H3 still produced an 81-column record; it was not frozen or executed. The next exporter uses compact bijective alphabetic names (`A`…`Z`, `AA`…), validated against both the native-format reader requirements and the 80-column limit. The R3.3 contract, manifest, failed logs, and this audit remain preserved. The next campaign must use a new frozen contract and a completely new output root; no R3.3 raw result is reusable.
