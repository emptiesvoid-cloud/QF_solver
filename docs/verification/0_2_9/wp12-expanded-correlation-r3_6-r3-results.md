# WP12 R3.6-R3 — diverse-topology Code_Aster correlation

## Verdict

`PASS_WITH_LIMITATIONS`. All 144 frozen cases completed, and the independent raw-evidence auditor returned `PASS_WITH_LIMITATIONS` with 144/144 cases and no audit errors. This is supplemental same-mesh solver correlation evidence; it does not change WP12 points or the project ledger.

## Coverage

R3.6 adds three geometries to the prior R3.5 campaign: an L-section beam, a centered through-hole prism, and a stepped cantilever. Each was tested with TET4, HEX8, TET10, and HEX20; three frozen mesh levels; and four load cases. That is 12 cases for each family/geometry pair, 36 per element family, and 48 per geometry.

| Element family | L-section beam | Perforated prism | Stepped cantilever | Total |
|---|---:|---:|---:|---:|
| TET4 | 12/12 | 12/12 | 12/12 | 36/36 |
| HEX8 | 12/12 | 12/12 | 12/12 | 36/36 |
| TET10 | 12/12 | 12/12 | 12/12 | 36/36 |
| HEX20 | 12/12 | 12/12 | 12/12 | 36/36 |
| **Total** | **48/48** | **48/48** | **48/48** | **144/144** |

The four load cases are axial X, transverse Y, transverse Z, and combined XYZ. H1/H2/H3 refine only the longitudinal direction for each geometry; the campaign makes no isotropic or asymptotic mesh-convergence claim.

## Recomputed correlation and equilibrium gates

The independent auditor reloaded the raw QF/Code_Aster arrays and recomputed the observables. The largest values across all cases were:

| Metric | Maximum | Frozen limit |
|---|---:|---:|
| Displacement relative L2 | `9.776104e-13` | `1e-8` |
| Displacement relative L∞ | `1.041071e-12` | `1e-8` |
| Reaction relative L2 | `1.048708e-12` | `1e-8` |
| Reaction relative L∞ | `9.845147e-13` | `1e-8` |
| Strain energy / external work relative | `1.250508e-12` | `1e-8` |
| QF free residual relative L2 | `2.410894e-13` | `1e-8` |
| QF force equilibrium relative | `7.085696e-13` | `1e-8` |
| Code_Aster force equilibrium relative | `2.688119e-15` | `1e-8` |
| QF moment equilibrium relative | `5.666505e-13` | `1e-8` |
| Code_Aster moment equilibrium relative | `1.325090e-15` | `1e-8` |
| Fixed displacement absolute maximum | `3.769675e-23` | `1e-12` |

All 144 records have a fresh container process, exit code zero, the pinned Code_Aster 18.1.0 image, one CPU, and MPI disabled. The campaign ran sequentially. No numerical case failed and the fail-fast stop was not triggered.

## Provenance and integrity

```text
BRANCH = codex/wp12-expanded-correlation
CONTRACT_REVISION = R3_6_DIVERSE_TOPOLOGY_144_CASE_LINEAR_STATIC_CORRELATION_R3
CONTRACT_COMMIT_SHA = 3c82280a829acb4252b72a832b7b69618fe79dcb
CONTRACT_SHA256 = 45c73fdb2ad6e47138a535f9bbb5c38ccfac98b57d91a32eb3617d4595cc58a3
EXECUTION_SHA = 3c82280a829acb4252b72a832b7b69618fe79dcb
RUNNER_SHA = 3dee54a3b525c3c5f6c67d49b7c4ad12f0127fc6
MODEL_BUILDER_SHA = 69dbcb8c887456e0e1686bed605a6e80189a3273
INDEPENDENT_AUDITOR_SHA = 69dbcb8c887456e0e1686bed605a6e80189a3273
CONTRACT_BUILDER_SHA = 3dee54a3b525c3c5f6c67d49b7c4ad12f0127fc6
MANIFEST_SHA256 = 274cf786495729b5664c2f77b0f130420d11b611014af110cff228e3243e4d92
INDEPENDENT_AUDIT_SHA256 = 550e83f6eaad7b9d1a6adf1e4a57529a85e3850f88ea61ab2280d769997211ae
RAW_SUMMARY_SHA256 = 44a2f413ee47df572a5c90ba8572ea2ccafd6e46d4217a7870c64984f3ac3884
MANIFESTED_RAW_FILES = 2452
INDEPENDENT_AUDIT = PASS_WITH_LIMITATIONS, 144/144, zero errors
EXECUTION_WINDOW_UTC = 2026-09-23 16:32:21–16:47:04
PRODUCTION_SOURCE_CHANGED_BY_R3_6 = NO
OFFICIAL_POINTS_CHANGED = NO
FULL_REPOSITORY_TEST_SUITE = NOT_RUN
```

The raw files remain local and Git-ignored. Their complete file set, sizes, and SHA-256 digests are recorded in the versioned manifest; the independent audit verified the manifest and every case. R3.6-R1's Code_Aster label-parsing failure and R3.6-R2's preflight-only provenance failure are preserved in the R3 contract lineage and were not overwritten or counted as numerical results.

## Validation and interpretation

- Targeted WP12 tests: `29 passed`.
- `compileall`: PASS; `git diff --check`: PASS.
- Ruff and mypy executables were unavailable in this environment; neither is reported as passed.
- Full repository test suite: not run.
- No Code_Aster process remains active.
- R3.6 is homogeneous-isotropic, 3D, small-strain, linear-static correlation on the same discrete mesh and loads in both solvers. It is not experimental validation, an independent physical benchmark, a stress-field comparison, or proof of nonlinear/contact behavior.
- The three geometry families are structured voxel-like non-prismatic solids. The refinement is axial only. No wedge, pyramid, shell, or beam element is included.
- The evidence is supplemental and does not supersede R3.5, prior failure history, Owner decisions, WP12 score, or the global ledger.

```text
R3_6_STATUS = PASS_WITH_LIMITATIONS
CASES = 144/144 PASS_CANDIDATE
FAMILIES = TET4, HEX8, TET10, HEX20
GEOMETRIES = L_SECTION_BEAM, PERFORATED_PRISM, STEPPED_CANTILEVER
OFFICIAL_POINTS_CHANGED = NO
PUSH = NOT_PERFORMED
MERGE = NOT_PERFORMED
```
