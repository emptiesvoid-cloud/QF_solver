# WP12 R3.5 pre-freeze smoke — harness attempt 2 preserved

The second diagnostic smoke attempt is `FAIL_CLOSED_DIAGNOSTIC_HARNESS`, not a Code_Aster result. It attempted only `tet4_slender_beam_h3_combined_xyz` and failed because the wrapper supplied `execution_sha` but omitted `contract_sha256`. As in attempt 1, the shared runner completed one QF linear solve and wrote the three QF model/result files, then raised `KeyError` while creating case provenance. No Code_Aster container or external solver process was started; three families remain unattempted.

The separate 5-file raw tree is hash-manifested and fully intact. It is not a correlation result and is not reused by the next smoke attempt.

```text
SMOKE_STATUS = FAIL_CLOSED_DIAGNOSTIC_HARNESS
SOURCE_SHA = 5608233bf17a2c1d15c18bf845983543e1e0a060
ATTEMPTED = 1/4
QF_DIAGNOSTIC_CASES = 1
CODE_ASTER_PROCESSES = 0
CODE_ASTER_RAW_RESULTS = 0
RAW_FILE_COUNT = 5
MANIFEST_SHA256 = 2fc085cd77d6b4357e046100a1860972327438b65fa7df488d33c24c26297200
SMOKE_REPORT_SHA256 = f8d533041fcf677eb1f73149c9682ab3021ccdc78f51a9f5631b1f2429495dca
PRODUCTION_MECHANICS_CHANGED = NO
WP12_POINTS_CHANGED = NO
```

Machine audit: [wp12_external_vv_r3_5_mesh_smoke_attempt_2_audit.json](../../../qualification/0_2_9/wp12_external_vv_r3_5_mesh_smoke_attempt_2_audit.json). The following attempt uses another output/report/manifest path and supplies the complete runner readiness object.
