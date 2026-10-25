# QF Solver v0.2.12 — Integration roadmap overlay

**Normative state updated:** 2026-10-25
**Reviewed branch:** `emptiesvoids-cloud/0.2.12`
**HEAD at review start:** `8aa83f632643c389aed3b8c4e9223f8c422eee1a`

This file records the current integration decision that supplements the preserved Owner roadmap. The Owner-approved roadmap remains byte-preserved at [`owner_provided/QF_Solver_v0.2.12_roadmap_WPE01.md`](owner_provided/QF_Solver_v0.2.12_roadmap_WPE01.md). The earlier integration snapshot is preserved verbatim at [`wp_e01_source_snapshot_ROADMAP.md`](wp_e01_source_snapshot_ROADMAP.md); its WP-E01 row reflects the status before Owner decision BC and is historical.

## Normative portfolio state — 2026-10-25

This is the latest operational state after the recorded WP11 closure decision. It supersedes earlier portfolio-count snapshots below without changing their historical contents.

| Work package | Current disposition |
|---|---|
| WP00 | `CLOSED` — positive historical closure |
| WP01 | `CLOSED` — positive historical closure |
| WP02 | `CLOSED` — positive historical closure |
| WP03 | `CLOSED` — positive historical closure |
| WP04 | `CLOSED` — positive historical closure |
| WP05 | `CLOSED` — positive historical closure; v0.2.12 reduced harmonic |
| WP06 | `CLOSED` — positive historical closure; v0.2.12 modal Newmark |
| WP07 | `CLOSED` — positive historical closure |
| WP08 | `CLOSED_BOUNDED` — positive historical closure within its recorded scope |
| WP09 | `CLOSED_BOUNDED` — positive historical closure within its recorded scope |
| WP10 | `CLOSED_BOUNDED` — positive historical closure within its recorded scope |
| WP-C01 | `CLOSED_NEGATIVE`; remediation remains `OPEN` — [R19 status register](wp_c01_r19_status_register.json) |
| WP-C02 | `CLOSED_BOUNDED` — WP-C02-AR/N03 only — [Owner N13 decision](wp_c02_n13_owner_bounded_closure_decision.md) |
| WP-D01 | `INCONCLUSIVE` — open — [integration report](wp_d01_stable_projection_integration_report.md) |
| WP-D02 | `CLOSED_BOUNDED` — within its recorded scope — [closure report](wp_d02_bounded_closure_report.md) |
| WP-E01 | `OPEN_WITH_BOUNDED_CERTIFICATES` — [integration report](wp_e01_bc_integration_report.md) |
| WP11 | `CLOSED` — operational API/integration gate only — [closure assessment](wp11_final/closure_gate_assessment.md) |
| WP12 | `OPEN` |
| WP13 | `OPEN` |

Portfolio total: **19 work packages; 14 positive closures, 1 historical negative closure, and 4 open**. This is an administrative count, not a measure of scientific qualification, coverage, or release readiness. WP00–WP10's historical scopes and statuses are preserved in the [Owner-approved roadmap](owner_provided/QF_Solver_v0.2.12_roadmap_WPE01.md); WP08–WP10 are positive but bounded closures. WP-C01's open remediation is tracked against its negative historical closure and is not a twentieth work package. WP-D01 is included among the four open packages because its disposition is `INCONCLUSIVE`.

WP11 closed only for its approved API, integration, traceability, result-contract, serialization, documented-compatibility, and refusal scope. The [closure assessment](wp11_final/closure_gate_assessment.md) and [capability traceability matrix](wp11_final/capability_traceability_matrix.tsv) preserve the accepted boundary. Its closure does not require or imply rotor numerical non-regression. Rotor numerical V&V belongs to WP12; WP12 remains open. No WP12 solver checks or WP13 activities are executed by this roadmap update.

## Capacités héritées de v0.2.11 — Rotordynamique

These are already implemented v0.2.11 capabilities carried in the current source tree. They are inherited experimental routes, not newly created v0.2.12 work packages and not part of the v0.2.12 WP05/WP06 feature names.

### Rotating modal — `rotating_modal`

- Experimental small-perturbation model for a straight, connected, unbranched and collinear BEAM2 shaft, circular isotropic beam sections, and centered rigid axisymmetric disks attached at shaft nodes.
- Assembles structural `M` and `K` plus the disk unit-speed gyroscopic matrix `G`. Uses the signed-speed convention `M q̈ + ΩG q̇ + Kq = 0` with the frozen global axis and right-hand rule; speed is applied once.
- Solves the quadratic eigenvalue problem with a serial dense SciPy QEP and returns complex eigenvalues, frequencies, and complex modes.
- Historical WP05 verification GYRO-01 through GYRO-04 is recorded as PASS for the frozen contract and source identity. The route remains `EXPERIMENTAL` and has no general rotating-machinery qualification.

### Campbell — `campbell`

- Runs only over a finite, explicitly supplied, strictly increasing list of signed spin speeds; it does not generate or adaptively refine a speed grid.
- Tracks complex modes using the frozen complex MAC/global assignment policy, records branch lineage, handles degenerate subspaces, and preserves missing samples and unresolved associations as gaps or ambiguities.
- Historical WP06 verification GYRO-05 and GYRO-06 is recorded as PASS within their contracts. The high-frequency pair's ambiguity at 100 rad/s remains explicit; no branch is forced through it. GYRO-06 is internal mesh-convergence evidence, not independent physical validation.
- Maturity remains `EXPERIMENTAL`. A Campbell crossing is not a forced-response amplitude, unbalance-response prediction, operating-danger assessment, or instability verdict.

### Shared exclusions and maturity boundary

The source contracts reject distributed shaft gyroscopic terms, forced unbalance response, speed-dependent bearings or other speed-varying `M/K/G` inputs, general rotor damping (the accepted WP05 model is undamped), centrifugal prestress/stress-stiffening, contact/rubbing and nonlinear rotor response, and sparse/PETSc/SLEPc/MPI QEP backends. These routes do not qualify general rotating machinery. The exact model validators and refusal rules remain those in the frozen v0.2.11 contracts; this summary does not extend them.

The [v0.2.12 WP00 baseline](wp00_baseline_scope.md) and [frozen baseline contract](wp00_baseline_scope_contract.json) assign reduced harmonic response to WP05 and modal Newmark transient response to WP06. They mark prepared Campbell as optional and not selected, and place rotors outside the newly selected dynamic scope. Those statements define the new v0.2.12 work scope; they do not remove the separately released v0.2.11 rotating_modal and campbell capabilities from the inherited codebase.

| Release/work-package identity | Capability | Relationship |
|---|---|---|
| v0.2.11 WP05 | Gyroscopic model / rotating_modal | Inherited capability; GYRO-01–04 |
| v0.2.11 WP06 | Campbell / complex modal tracking | Inherited capability; GYRO-05–06 |
| v0.2.12 WP05 | Reduced harmonic response | Current-release feature; distinct numbering |
| v0.2.12 WP06 | Modal Newmark transient response | Current-release feature; distinct numbering |

WP numbering is release-specific; identical WP numbers across releases do not denote the same capability. See the [v0.2.11 WP05 contract](../0_2_11/wp05_gyroscopic_contract.json), [WP05 report](../0_2_11/wp05_gyroscopic_report.md), [v0.2.11 WP06 contract](../0_2_11/wp06_campbell_contract.json), [WP06 report](../0_2_11/wp06_campbell_report.md), [capability index](../../docs/capabilities/index.md), [rotating-modal guide](../../docs/mechanics/rotating-modal.md), and [Campbell guide](../../docs/mechanics/campbell.md).

The prospective WP12 checks are documented in [wp12_rotating_inherited_regression_plan.md](wp12_rotating_inherited_regression_plan.md). They are all NOT_RUN on the reviewed HEAD; the historical v0.2.11 records are not current-HEAD test results.

## Historical integration decisions and dated snapshots

### Snapshot — WP-E01 Owner BC, 2026-10-23
`WP_E01=OPEN_WITH_BOUNDED_CERTIFICATES`.

WP-E01 is included in v0.2.12 as an experimental capability set with strictly scoped evidence. It remains open and is not a standalone publication gate. WP11, WP12, and WP13 retain their own open validation criteria and are not closed by this decision.

- `PRODUCTION_ARMIJO_GF4_SLAVE_BOUNDED=VERIFIED_BOUNDED` applies only to the archived GF4 TET4 deformable slave subsystem and its exact historical source, manifest, and image identity.
- `MASTER_ASSEMBLY_EQUILIBRIUM=NOT_VERIFIED`.
- The raw global BA verdict remains `FAIL`.
- The global J2 tangent remains unresolved.
- Hencky material-point and directional-tangent evidence is bounded to its recorded tests; the tangent convergence plateau is not established.
- `GENERAL_SCIENTIFIC_QUALIFICATION=NOT_ACQUIRED`.

See [`wp_e01_bc_integration_report.md`](wp_e01_bc_integration_report.md) for the integrated file inventory, maturity matrix, tests, exact hashes, exclusions, and risks. The original Owner roadmap and historical reports remain unchanged.

### Snapshot — WP11 preliminary open position, 2026-10-23, before final closure

This section preserves the earlier open assessment. It is superseded by the
dated post-verification decision at the end of this overlay.

`WP11=OPEN`. The WP11-A audit and WP11-B traceability package cover the
capabilities present on this integration branch. The API surface and selected
serialization/refusal contracts have targeted non-qualifying regression
coverage; this does not close the complete WP11 integration gate by itself.
The ordinary result DTOs do not all have a shared versioned schema or generic
deserializer. WP11-B records this contract boundary for an Owner decision.

WP-D02 remains `CLOSED_BOUNDED` at its documented recovery scope. WP-E01
remains `OPEN_WITH_BOUNDED_CERTIFICATES`: the GF4 certificate is historical to
its exact TET4 slave-subsystem identity, master assembly equilibrium remains
`NOT_VERIFIED`, and the global J2 tangent remains unresolved. WP-C02 is now
`CLOSED_BOUNDED` only for the WP-C02-AR manufactured TET4 fixed planar-face
benchmark and prospective criteria N03. `GENERAL_CONTACT_QUALIFICATION` and
`DOCKER_EQUIVALENCE` remain `NOT_ACQUIRED`; no asymptotic convergence claim is
made. The N06/N08 and Docker `FAIL`/`FAIL_CLOSED` verdicts remain unchanged.
This does not close the broader contact route or alter the WP11, WP12, or WP13
criteria. D01 remains separate from the bounded C02 decision.

### Snapshot — WP11 review state during verification, 2026-10-25

The official state remained `WP11=OPEN` throughout verification. The Owner
decision accepts the operational API/integration scope and the heterogeneous
documented result contracts; no universal result schema or generic
`load_result()` is required. The exact
acceptance matrix, compatibility reserve, test results and exclusions are in
[`wp11_final/closure_gate_assessment.md`](wp11_final/closure_gate_assessment.md)
and [`wp11_final/owner_decision_followup_manifest.json`](wp11_final/owner_decision_followup_manifest.json).

This operational closure does not promote D01 (`INCONCLUSIVE`), expand C02
`CLOSED_BOUNDED` beyond AR/N03, or close E01 (`OPEN_WITH_BOUNDED_CERTIFICATES`).
Numerical V&V and performance remain WP12 work. No WP12 or WP13 execution,
merge to `main`, tag, package publication, or site publication is included.

See [`wp11_b_closure_gate_assessment.md`](wp11_b_closure_gate_assessment.md)
for the current gate assessment and recommended decision.

### Snapshot — WP11 Owner policy review before the final gate result, 2026-10-25

The Owner decision recorded for the operational API/integration WP11 resolves
the earlier questions above. The official status remains `WP11=OPEN` while the
current contract verification is completed. The acceptance scope is API
integration, traceability, result contracts, serialization, documented
compatibility, and refusals. Numerical V&V campaigns and performance
measurements belong to WP12. Any additional FEM execution requires its own
frozen manifest and separate authorization.

The heterogeneous documented result DTOs are accepted for v0.2.12; no
universal result schema or `load_result()` is required. Existing versioned
schemas, refusal rules, and stated limits remain in force. D01 remains
`INCONCLUSIVE`; C02 remains `CLOSED_BOUNDED` only for AR/N03; E01 remains
`OPEN_WITH_BOUNDED_CERTIFICATES`. None is promoted by WP11 API evidence. The
dated acceptance matrix and exact proof references are in
[`wp11_final/wp11_acceptance_matrix.tsv`](wp11_final/wp11_acceptance_matrix.tsv)
and [`wp11_final/owner_decision_record.md`](wp11_final/owner_decision_record.md).
This policy review did not alter historical ledgers or approve WP12, WP13,
merge, tag, or publication.

### Snapshot — WP-C02 integration and portfolio count before WP11 closure, Owner N13 / M-ERGE, 2026-10-23

`WP_C02_STATUS=CLOSED_BOUNDED` applies solely to WP-C02-AR/N03. The selected
integration is recorded in
[`wp_c02_integration_merge_report.md`](wp_c02_integration_merge_report.md);
it does not change the scientific scope or claim Docker equivalence. N10
execution results and their archive remain external and are linked by their
own manifest and integrity hashes.

The integration portfolio count recorded at that earlier point was
**19 work packages: 13 positive closures, 1 negative closure, and 5 open**. It is a
historical count from before the WP11 closure and is superseded by the
2026-10-25 normative count above. Neither count measures scientific maturity
or release readiness. The Owner roadmap remains preserved verbatim, and
`main`/public release are unchanged.

### WP11 CLOSE evidence — 2026-10-25

`WP11=CLOSED` for the operational API/integration gate (interfaces,
traceability, result contracts, serialization, documented compatibility and
refusals), following the acceptance criteria approved by the Owner. The
closure dossier records `CLOSE`, the `save_result` migration reserve, the
verification limits and exact proof references in
[`wp11_final/closure_gate_assessment.md`](wp11_final/closure_gate_assessment.md)
and [`wp11_final/owner_decision_followup_manifest.json`](wp11_final/owner_decision_followup_manifest.json).

This operational closure does not promote D01 (`INCONCLUSIVE`), expand C02
`CLOSED_BOUNDED` beyond AR/N03, or close E01 (`OPEN_WITH_BOUNDED_CERTIFICATES`).
Numerical V&V and performance remain WP12 work. No WP12 or WP13 execution,
merge to `main`, tag, package publication, or site publication is included.
