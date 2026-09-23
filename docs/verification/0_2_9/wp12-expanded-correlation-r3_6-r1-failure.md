# WP12 R3.6-R1 — fail-closed execution record

## Outcome

`R3.6-R1 = FAIL_CLOSED_EXECUTION`. The frozen campaign stopped at its first external execution failure. One of 144 cases was attempted; the other 143 were not started. No QF-versus-Code_Aster numerical correlation was produced.

Code_Aster read the generated mesh (24 nodes, 30 TETRA4 elements), created the mechanical model, material, and fixed-root boundary condition, then aborted while parsing the first `FORCE_NODALE` card. The compact alphabetic node label was emitted as `NOEUD="AE"`; the Code_Aster 18.1 runtime raised a Fortran `Bad integer for item 1 in list input` in `char8_to_int.F90`. `MECA_STATIQUE` was not reached. The fresh container process exited with code 2 after approximately five seconds.

This is an export/interface failure, not a numerical failure. It does not invalidate or replace the earlier frozen R3.6 contract, and no retry was made into the R1 output directory.

| Execution state | Count |
|---|---:|
| Frozen cases | 144 |
| Attempted | 1 |
| Code_Aster execution failures | 1 |
| Candidate correlations passed | 0 |
| Not started | 143 |
| Numerical Code_Aster results | 0 |

## Integrity and provenance

The local raw directory is ignored by Git and remains intact. Its versioned manifest lists 20 files; all 20 sizes and SHA-256 values were independently recomputed, with no missing or extra files.

```text
BRANCH = codex/wp12-expanded-correlation
EXECUTION_SHA = d453b0c34238650f2453df08531618883fec6243
CONTRACT_SHA256 = 37849c0e763d4ceb4550bd099370bfa2810f8b17b4ebef6d969c79a626262852
RUNNER_SHA = f32d864e7674ac80dfb6e7e42e9432eb1edd0958
R1_MANIFEST_SHA256 = 2c77e55317008d4b638dc39897287db8c5bb990bc54231e80aa1cee4d8501436
R1_INDEPENDENT_AUDIT_SHA256 = 988a9976234665a5526845291cf0d240a19ec7c08afe1e622305e4a70a7c5dec
R1_SUMMARY_SHA256 = 6344699b5c4e756f613ad0b4a19ef0ceb108f70936af5d483f6332c73950a704
FIRST_CASE_PROCESS_SHA256 = 6213af1b373a3601f01da06949f94d4f537baa0e68bfd79403a679ff7015e992
FIRST_CASE_MESS_SHA256 = 7cbbcd041971786f5af6d23bc59e4e9b8c5dd9dfa92187a731be04931caab346
FIRST_CASE_STDOUT_SHA256 = d592faf1d0acc7110a9d27820cd22d84804c83364aafc55f313c5793ba7d5628
PROCESS_EXIT_CODE = 2
ASTER_RAW_RESULT = ABSENT
PRODUCTION_MECHANICS_CHANGED = NO
THRESHOLDS_CHANGED = NO
WP12_POINTS_CHANGED = NO
```

The independent audit is fail-closed at 0/144: the attempted case has no `aster_raw.json`, and the remaining 143 cases correctly lack execution artifacts. The complete per-case audit and the 20-file raw manifest are versioned as `qualification/0_2_9/wp12_external_vv_r3_6_diverse_r1_audit.json` and `qualification/0_2_9/wp12_external_vv_r3_6_diverse_r1_manifest.json`. The raw directory is `qualification/0_2_9/wp12_external_vv_r3_6_diverse_r1_raw/` and is not committed.

## Corrective action for a new revision

R1 is immutable. A new contract revision may change only how the unchanged nodal force vector is addressed in the Code_Aster command file: use the already-generated singleton node groups `QFxxxxx` through `FORCE_NODALE(GROUP_NO=...)`, rather than passing compact alphabetic labels through `NOEUD`. The independent auditor must decode and compare every group/component/value against the frozen raw load vector. Geometry, meshes, materials, boundary conditions, loads, numerical thresholds, image, and sequential fail-fast policy remain unchanged. The corrected exporter must pass targeted serialization/auditor tests before a distinct R2 contract and output directory are frozen.

```text
R3.6_R1_STATUS = FAIL_CLOSED_EXECUTION
R3.6_R1_RAW_INTEGRITY = PASS (20/20)
R3.6_R1_NUMERICAL_CORRELATION = NOT_RUN
R3.6_R2_AUTHORIZATION = WITHIN_EXISTING_OWNER-APPROVED_CORRELATION_SCOPE
```
