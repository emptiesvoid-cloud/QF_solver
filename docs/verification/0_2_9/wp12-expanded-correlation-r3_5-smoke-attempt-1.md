# WP12 R3.5 pre-freeze smoke — harness failure preserved

The first diagnostic smoke attempt is `FAIL_CLOSED_DIAGNOSTIC_HARNESS`, not a Code_Aster result. It attempted only `tet4_slender_beam_h3_combined_xyz` and failed because the smoke wrapper omitted `readiness.execution_sha`. The shared runner completed the QF linear solve and wrote its model inputs, displacement, and stiffness, then raised `KeyError` while creating the case provenance record. No Code_Aster container or external solver process was started; the remaining three families were not attempted.

The 5-file partial output tree is intact and its sibling manifest passes size/SHA-256 verification. This attempt cannot establish mesh-import, force-card, or correlation validity and is not reused by the next smoke attempt.

```text
SMOKE_STATUS = FAIL_CLOSED_DIAGNOSTIC_HARNESS
SOURCE_SHA = 397d3bd4187716ffc7fd0a03aaabd4bcdce61569
ATTEMPTED = 1/4
QF_DIAGNOSTIC_CASES = 1
CODE_ASTER_PROCESSES = 0
CODE_ASTER_RAW_RESULTS = 0
RAW_FILE_COUNT = 5
MANIFEST_SHA256 = a807bbc2ba6959a470e9827b49e5011a3ba0e0fcb39129aec3c5499803cae5f5
SMOKE_REPORT_SHA256 = 3b9440491b1715cd057aba18040de0238491e0643988114aa813e2c097669269
PRODUCTION_MECHANICS_CHANGED = NO
WP12_POINTS_CHANGED = NO
```

Machine audit: [wp12_external_vv_r3_5_mesh_smoke_attempt_audit.json](../../../qualification/0_2_9/wp12_external_vv_r3_5_mesh_smoke_attempt_audit.json). The next attempt uses a distinct output/report/manifest path and includes the required execution SHA; these partial artifacts remain preserved.
