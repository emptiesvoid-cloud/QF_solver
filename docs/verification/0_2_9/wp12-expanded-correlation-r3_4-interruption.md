# WP12 R3.4 expanded correlation — fail-fast execution record

## Outcome

`R3.4 = FAIL_CLOSED`; the campaign stopped at its first execution exception as required by the frozen contract. Only the first of 144 cases was attempted; the other 143 were not started. No external correlation result was produced.

Code_Aster successfully read the mesh and constructed the model, material, and fixed boundary condition. It then aborted while processing `AFFE_CHAR_MECA(FORCE_NODALE=...)`: `NOEUD='E'` reached `char8_to_int`, which expected the solver's `N`-prefixed integer node convention and raised a Fortran “Bad integer for item 1 in list input” error. `MECA_STATIQUE` was not reached, the process exited with code 2, and no `aster_raw.json` exists.

| Execution state | Count |
|---|---:|
| Frozen cases | 144 |
| Attempted | 1 |
| Code_Aster execution failures | 1 |
| Independent-auditor candidate passes | 0 |
| Not started | 143 |
| External raw results | 0 |

The QF-side model files for the attempted case are preserved, but this is not a QF-versus-Code_Aster correlation result. The independent campaign auditor correctly returned `FAIL_CLOSED` (0/144); its 289 errors include the one failed case and the expected missing evidence for 143 unstarted cases.

## Integrity and provenance

The partial R3.4 output manifest contains 20 entries. A separate integrity check recomputed all sizes and SHA-256 values: 20/20 match, with no missing or extra files.

```text
BRANCH = codex/wp12-expanded-correlation
CONTRACT_SHA256 = 91ca0b310763209fa010955e723e21d8d09ca6bc0141f5317d167bab711896e3
FREEZE_COMMIT = 885d0bc24804b77dd339a396948c970d403add2b
EXECUTION_SHA = b6e969dea9889de6d58382e61e327ded3776337e
RUNNER_SHA = 885d0bc24804b77dd339a396948c970d403add2b
MANIFEST_SHA256 = b482c84debe6d4d75098f4ca149ad362f2d077bc528e0a54cb4ec3530e5e81ec
INDEPENDENT_AUDIT_SHA256 = 09863ee81c9339b781bf29d09d95795e4443e740d63c50b43d7588e0ea6b3fd6
PRODUCTION_MECHANICS_CHANGED = NO
THRESHOLDS_CHANGED = NO
WP12_POINTS_CHANGED = NO
```

The machine audit is [wp12_external_vv_r3_4_execution_audit.json](../../../qualification/0_2_9/wp12_external_vv_r3_4_execution_audit.json). The independent full-matrix audit is [wp12_external_vv_r3_4_expanded_audit.json](../../../qualification/0_2_9/wp12_external_vv_r3_4_expanded_audit.json); the partial raw tree remains local and ignored, with its sibling manifest versioned.

## Next exporter rule

The mesh reader accepts alphabetic labels, but `FORCE_NODALE/NOEUD` requires node labels of the form `N` followed by an integer. The next revision will therefore use `N1`, `N2`, … for nodes while using one-character alphabetic element identifiers (`A`…`Z`) to keep even HEX20 H3 connectivity records within 80 columns. Regression tests must verify both the native mesh text and force-card references before a new contract is frozen. R3.4's contract, logs, manifest, and fail-closed audit remain preserved; no R3.4 raw result is reusable.
