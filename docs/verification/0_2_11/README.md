---
doc_id: DOC-VV-PUBLIC-0211-001
title: QF Solver 0.2.11 verification summary
revision: 1.0
status: controlled_candidate
applicable_version: 0.2.11
reviewer: ""
approver: ""
---

# QF Solver 0.2.11 verification summary

This summary reports the recorded WP01–WP06 evidence for QF Solver 0.2.11.
It does not turn a numerical result into an automatic maturity decision. The
release was published on 2026-10-07 with version DOI
[`10.5281/zenodo.23214487`](https://doi.org/10.5281/zenodo.23214487); the
separate publication record verifies channel availability and exact selected
artifact hashes. Original source identities, measurements and decisions remain
in their structured records.

## Scope and provenance

New WP03 records use schema v2 execution identities, content hashes,
structured expected-failure contracts, explicit evidence availability, and
an explicit separation between internal provenance and public records.
Historical records are read as historical evidence; they were not migrated or
rewritten. The design and historical compatibility limits are documented in
the [WP03 V&V/data design](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/qualification/0_2_11/wp03_vnv_data_design.md)
and [contract](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/qualification/0_2_11/wp03_vnv_data_contract.json).

## Gyroscopic and Campbell evidence

| Case | Evidence | Result and boundary |
| --- | --- | --- |
| GYRO-01 | Zero-speed rotating-modal recovery against the classic modal route | PASS within the recorded frequency, multiplicity, subspace, normalization and residual comparisons. |
| GYRO-02 | Disk mass/G identities, skew symmetry, frame covariance, signed speed, energy property, ownership and fail-closed checks | PASS for the bounded rigid axisymmetric disk model. |
| GYRO-03 | Independent disk-oscillator analytical oracle over signed speeds | PASS; oracle does not use the production gyroscopic assembly. |
| GYRO-04 | Zero-speed degeneracy and signed-speed spectral splitting | PASS within the frozen WP05 scope and tolerances. |
| GYRO-05 | Analytical Campbell branches, phase/order invariance, degeneracy lineage and a controlled ambiguous case | PASS; ambiguity is reported rather than connected by force. |
| GYRO-06 | 4/8/16/32-element BEAM2 shaft-and-disk mesh sequence at 0, 100 and 250 rad/s | PASS internal mesh-convergence evidence only; the high-frequency pair remains ambiguous at 100 rad/s. |

The detailed machine-readable records are [GYRO-05](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/qualification/0_2_11/gyro_05_campbell_analytical.json)
and [GYRO-06](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/qualification/0_2_11/gyro_06_beam2_convergence.json).
The [WP05 contract](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/qualification/0_2_11/wp05_gyroscopic_contract.json)
and [WP06 contract](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/qualification/0_2_11/wp06_campbell_contract.json)
carry the frozen equations, input scope, thresholds and result requirements.

For GYRO-06, the maximum relative frequency delta between the two finest
meshes (16 and 32 elements) was `0.00011432899`, against the predeclared
`0.005` limit. The largest recorded QEP relative residual was
`1.61735001e-9`, against `1e-8`. These comparisons establish internal
mesh-convergence evidence for the documented model, not independent physical
validation or a general rotordynamics qualification.

## Maturity and visible limitations

Both `rotating_modal` and `campbell` remain `EXPERIMENTAL`. Campbell is an
orchestration and tracking layer over the WP05 solve, not a new physical
formulation. At 100 rad/s the high-frequency pair remains ambiguous, and the
tracker preserves the gap instead of forcing continuity. The 1× line is only
a frequency-coincidence reference; the analysis does not predict forced
response, unbalance amplitude, operational danger, instability, or validated
critical speeds.

The scope is serial, dense SciPy QEP for straight BEAM2 shafts and centered
rigid axisymmetric disks under constant signed speed, fixed global axis,
small perturbations, and undamped/unprestressed conditions. Variable-speed or
speed-dependent properties, distributed shaft gyros, general damping,
centrifugal stiffening, contact, nonlinear rotors and PETSc/SLEPc/MPI remain
outside scope.

## Gates and publication boundary

WP01–WP06 provide their recorded baseline, architecture, V&V, historical
retest, gyro and Campbell evidence. The final QF0211-G07/G08 gates and exact-
source release audit are recorded separately under WP07. The published 0.2.10
tag and artifacts are not modified by this version or by later edits to the
current public documentation. Each release audit applies only to its recorded
source and artifact bytes.

Historical 0.2.10 G03 remains `FAIL_PRESERVED`; the complete repository
archive is not cleared. Historical WP14 remains `HOLD_NOT_PROMOTED`. These
statuses are distinct from the QF0211 work-package gates and are not changed
by the newer passing results.
