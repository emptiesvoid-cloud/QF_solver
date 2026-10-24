# QF Solver v0.2.12 Integration Progress Ledger

Updated: 2026-10-21
Authority: Owner GO — QF Solver v0.2.12 Integration Baseline
Integration branch: `codex/v0.2.12-integration`
Repository: `https://github.com/emptiesvoid-cloud/QF_solver.git`

## Baseline and integration

- Designated base: WP10 commit `1d7fef04094d2f4b920795b4b3c25f052fcf21c0`.
- WP10 is the verified parent of the reviewed RBE integration.
- WP13 implementation commit: `d07fdf72e487ac35e2ef9afaccc8d9c46f25d4bd`.
- WP13 integration documentation and bounded maturity record: `dec81ab031f98ea24a8860b7ff0376c69d9e9feb`.
- Integration snapshot tree before this ledger entry: `14039d1499284744437bee16f226ab9a492d9c7c`.
- The integration branch was created from the designated base and fast-forwarded to the reviewed WP13 integration. No merge conflicts occurred.
- No C02, D01, E01, D02 or other experimental work-package changes were imported.
- No public capability registry, public solver route, main branch, release or deployment was changed.

## Targeted regression on the designated branch

Run commit: `dec81ab031f98ea24a8860b7ff0376c69d9e9feb`.

Environment: Python 3.13.1; pytest 8.4.1; `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `QF_SOLVER_RUN_EXTERNAL=0`.

Command:

```powershell
python -m pytest -q tests/unit/test_rbe_links.py tests/unit/test_mpc_reduction.py tests/unit/test_backend_edge_matrix_contracts.py tests/unit/test_mesh_validation.py tests/unit/test_mesh_validation_edge_contracts.py tests/unit/test_code_aster_rbe.py tests/unit/test_wp13_02_mixed_dynamic_validation.py
```

Observed: **100 passed, 0 failed, 0 skipped**; pytest-reported duration 7.25 s, shell-measured duration 9.418 s, exit code 0. External Code_Aster execution was disabled. This is the fresh run on the newly designated branch.

Test SHA-256 values:

| Test module | SHA-256 |
| --- | --- |
| `tests/unit/test_rbe_links.py` | `d730601b7d7c284273537cb987d5518d76334b81324adf58451833344428d815` |
| `tests/unit/test_mpc_reduction.py` | `c6d2c0c5685ed9d614c4ae696db4fffe322409904e7fa19e9abff859880ea009` |
| `tests/unit/test_backend_edge_matrix_contracts.py` | `6ff2e7294e18df075cbf8a13e8ae2c635ad3336b2bc4c255fdf97daf2640af12` |
| `tests/unit/test_mesh_validation.py` | `0c6cd80e6625102ac036d0c822ff1fad6c6be6b90487abe6de9a3ee465a34e65` |
| `tests/unit/test_mesh_validation_edge_contracts.py` | `aef73bb9dbc1c1996bd81caedafbf070028c5c895b589f9f3b5f5a4807126557` |
| `tests/unit/test_code_aster_rbe.py` | `3070a33978e72111c496a9899f6d504f72bd865246e22a71c635e54fba4b290f` |
| `tests/unit/test_wp13_02_mixed_dynamic_validation.py` | `0324f5e96122f4556f2368fed74798d62e6a74fa152e55452e62f635e4884721` |

## Integrated implementation identities

| Source | SHA-256 |
| --- | --- |
| `src/solveur/core/rbe.py` | `3031c1c106c220e96c8b2e16dd0fe57a5efe028792891962867b8351ec95793c` |
| `src/solveur/core/constraints.py` | `428f9d2bd907859e37a2dc8ea7e86102d804c1ec61c3473051cf85ab4fca9b41` |
| `src/solveur/io/constraint_schema.py` | `08735d9c518097053597967dabc9f2aa2630a5b836d9daa1931502332ea50a6a` |
| `src/solveur/mesh/validation.py` | `2f80e5f2f17f5138ac875bc32d9e46ad416a9941b11ba13688188ec23b4642b6` |
| `src/solveur/mesh/validation_rank.py` | `b286c05fa98dd0d1eb6c14e6b6e51fa567c25b01c61838c870874d6bdb71ee7b` |

Frozen WP13 source qualification: source commit `dc3fed78a33e7557e0214916dbdcf659ed5944ab`, Git tree `81516bf096a4d66443d88479325f8e32a23ff698`, report SHA-256 `8a2805b9be7010e11c0f097e5445f74d1a57290a89137879fb18f119c707c7a4`.

## Owner-approved bounded maturity scopes

| Capability | Status | Scope |
| --- | --- | --- |
| RBE2 linear statics | `QUALIFIED_BOUNDED` | Small-displacement linear statics; verified rigid-arm/acyclic configurations. Rotations and `tie_rotations` only where mechanically meaningful and supported by the DOFs. |
| RBE3 rigid-body projection linear statics | `QUALIFIED_BOUNDED` | Six reference DOFs; translational independent-node DOFs; strictly positive weights; full-rank geometry with `sigma_min/sigma_max > 1e-12`. |
| Acyclic MPC reduction linear statics | `QUALIFIED_BOUNDED` | Verified affine, compatible, acyclic linear-static MPC systems; cycles and incompatible constraints refused. |
| RBE3 weighted | `VERIFIED_BOUNDED` | Per-component weighted interpolation/extrapolation; general spatial moment preservation is not guaranteed. |
| MPC rank diagnostic | `VERIFIED_BOUNDED` | Dense reduced-system diagnostic for at most 180 active DOFs; conservative threshold, not a universal rank oracle. |

These labels apply only to the approved tested configurations. The runtime capability registry remains unchanged; no broader public capability is inferred.

## Remaining integration queue and boundary

- WP-C02: separate experimental branch; not integrated here.
- WP-D01: separate work package; not integrated here.
- WP-E01: separate work package; not integrated here.
- Other work-package changes remain outside this branch pending their own review and authorization.
- This branch is an internal development integration target only. Main-branch merge, release, website deployment and broader qualification remain unauthorized.

## WP-E01 bounded experimental inclusion — Owner decision BC (2026-10-23)

The initial snapshot above recorded WP-E01 as separate and not integrated. This section records the later Owner decision BC and is the current operational status; the earlier section remains historical context.

- **Current status:** `WP_E01=OPEN_WITH_BOUNDED_CERTIFICATES`.
- **Owner scope:** E01 is included in v0.2.12 as an experimental capability set. It is not a standalone release gate and does not close WP11, WP12, or WP13.
- **Integrated experimental material-point code:** the isolated, opt-in Hencky kinematics/material-point kernel and its directional material tangent are available by direct module import only. They are not registered in a material factory, public API, element dispatch, global assembly, or Newton route.
- **Tests:** the original hash-bound 41-case Hencky material-point suite and 35-case directional-tangent suite are retained and pass on this integration branch. The tangent evidence establishes bounded directional agreement only; `TANGENT_CONVERGENCE_PLATEAU=NOT_ESTABLISHED`.
- **StVK:** existing WP08–WP10 implementations and their bounded scopes remain authoritative; E01 does not replace or broaden them.
- **Additional E01-C1 material-point availability (2026-10-24):** `solveur.materials.finite_strain_elastic` now provides direct-import StVK and isochoric/volumetric compressible Neo-Hookean kernels. The module is not exported, connected to `MaterialFactory`, element dispatch, global assembly, a solver route, or result serialization. The two targeted integration commits are `413e6d45` and `4af64673`. Seven material-point test functions and two public-facade inventory regressions pass; no FEM was run. `FINITE_STRAIN_ELASTIC_FORMULATION=PROPOSED/INCOMPLETE`; `FINITE_STRAIN_MATERIAL_POINT_VNV=VERIFIED_BOUNDED` only for its documented point-level scope; `FINITE_STRAIN_FEM_VNV=NOT_RUN`; `SCIENTIFIC_QUALIFICATION=NOT_ACQUIRED`.
- **Historical E01 certificate:** `PRODUCTION_ARMIJO_GF4_SLAVE_BOUNDED=VERIFIED_BOUNDED` only for the archived GF4 TET4 slave subsystem, its exact source commit/tree, manifest, and image. It is preserved as historical evidence and is not a certificate for this integration HEAD.
- **Required exclusions:** `MASTER_ASSEMBLY_EQUILIBRIUM=NOT_VERIFIED`; `GLOBAL_J2_TANGENT=UNRESOLVED`; `GENERAL_SCIENTIFIC_QUALIFICATION=NOT_ACQUIRED`. The raw global BA verdict remains `FAIL`.
- **Not integrated:** E01 contact, nonlinear assembly/solver, public-route, worker/supervisor, Docker, global-assembly, Newton, and Hencky element-tangent adapter changes. They overlap shared C02/D02/WP08–WP10 paths or lack target-specific qualification.
- **Historical evidence archive:** E01 reports/manifests are preserved as source-snapshot records under `qualification/0_2_12/`; see [the integration report](wp_e01_bc_integration_report.md) for exact identities and test results.

No public capability registry, release policy, `main` branch, tag, or publication was changed.

## WP11 consolidation — Owner mandate WP11-B (2026-10-23)

- **Current status:** `WP11=OPEN`; WP11-A/B consolidate the actual API, results, schema, serialization and maturity scope without claiming closure automatically.
- **Scope assessed:** only capabilities present in `codex/v0.2.12-integration`, including bounded D02 stress recovery and isolated experimental E01-BC Hencky point-material kernels. C02, D01 and broader E01 solver/contact changes remain outside this branch.
- **D01/C02 sequencing:** neither is treated as a technical WP11 prerequisite absent a demonstrated direct dependency or an explicit historical contract. No source from those branches was imported.
- **Result-schema boundary:** ordinary static/modal/transient/harmonic result DTOs expose `to_dict()` serialization but do not share one versioned schema or a generic result deserializer. Experimental modal-Newmark and reduced-harmonic DTOs have separate versioned contracts. WP11-B documents this distinction; it does not alter solver behavior or create a new serialization contract.
- **Scientific exclusions retained:** `WP_D02=CLOSED_BOUNDED`; `WP_E01=OPEN_WITH_BOUNDED_CERTIFICATES`; `PRODUCTION_ARMIJO_GF4_SLAVE_BOUNDED=VERIFIED_BOUNDED` only for its historical TET4 slave scope; `MASTER_ASSEMBLY_EQUILIBRIUM=NOT_VERIFIED`; raw E01-BA aggregate verdict `FAIL`; global J2 tangent unresolved; `GENERAL_SCIENTIFIC_QUALIFICATION=NOT_ACQUIRED`.
- **Decision:** WP11 closure is proposed only after review of the traceability matrix and the Owner decision on whether the unversioned ordinary-result payloads meet the existing integration contract. WP12/WP13 remain open.
- **Evidence:** see `wp11_b_api_results_maturity_consolidation.md`, `wp11_b_capability_traceability_matrix.tsv`, and `wp11_b_closure_gate_assessment.md`. No FEM solve, Docker operation, release action, or public capability promotion was performed for WP11-B.

## WP-C01 R18 consolidation — administrative pending state (2026-10-24)

- **Historical status preserved:** `WP_C01_HISTORICAL=CLOSED_NEGATIVE`; `CANONICAL_M2_NOT_RECOVERED`; `WP_C02=CLOSED_BOUNDED`.
- **Remediation status:** the existing WP status contract has no `PENDING_FURTHER_QUALIFICATION` value. Keep `WP_C01_REMEDIATION=OPEN` and record `C01_FOLLOWUP_STATE=PENDING_FURTHER_QUALIFICATION` in [the R18 status register](wp_c01_r18_status_register.json).
- **R17 integration:** the archive JSON reader, offline replay tool, unit tests, replay evidence and independent review are included. The FEM smoke node itself was not added to this branch, and no FEM was launched in R17/R18.
- **R16 archive replay:** `B_STAR_R16_ARCHIVE_REPLAY=PASS`; the original `B_STAR_INTEGRATED_FEM_SMOKE=FAIL` and consumed attempt ledger remain preserved. `R16_RAW_MOMENT=ACQUIRED` from the independent archived-data reconstruction.
- **B* scope:** `B_STAR_INTEGRATION=MERGED_EXPERIMENTAL`, `B_STAR_STICK_SLIP=VALIDATED_EXPLORATORY`; legacy remains the default. The opt-in mode is limited to small rotations and one initially frozen pair. No numeric angle threshold is implemented. `B_STAR_GLOBAL_SLIP_TANGENT`, `FINITE_SLIDING_CONTACT`, and `C01_SPATIAL_CONVERGENCE` remain `NOT_ACQUIRED`.
- **Other work packages:** `WP11=PAUSED_BY_OWNER`; no WP11, WP12 or WP13 work was performed in this consolidation. The previous WP11-B section is a historical record and is not updated here.
- **Review and validation:** see [the independent review](wp_c01_r18_independent_review.md) and [traceability matrix](wp_c01_r18_traceability_matrix.tsv). No scientific solver equations, thresholds, or archives were changed. No merge to `main`, release, Docker operation, or certificate promotion occurred.
