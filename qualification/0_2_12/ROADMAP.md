# QF Solver v0.2.12 — Integration roadmap overlay

**Updated:** 2026-10-23
**Branch:** `codex/v0.2.12-integration`

This file records the current integration decision that supplements the preserved Owner roadmap. The Owner-approved roadmap remains byte-preserved at [`owner_provided/QF_Solver_v0.2.12_roadmap_WPE01.md`](owner_provided/QF_Solver_v0.2.12_roadmap_WPE01.md). The earlier integration snapshot is preserved verbatim at [`wp_e01_source_snapshot_ROADMAP.md`](wp_e01_source_snapshot_ROADMAP.md); its WP-E01 row reflects the status before Owner decision BC and is historical.

## Current WP-E01 decision — Owner BC

`WP_E01=OPEN_WITH_BOUNDED_CERTIFICATES`.

WP-E01 is included in v0.2.12 as an experimental capability set with strictly scoped evidence. It remains open and is not a standalone publication gate. WP11, WP12, and WP13 retain their own open validation criteria and are not closed by this decision.

- `PRODUCTION_ARMIJO_GF4_SLAVE_BOUNDED=VERIFIED_BOUNDED` applies only to the archived GF4 TET4 deformable slave subsystem and its exact historical source, manifest, and image identity.
- `MASTER_ASSEMBLY_EQUILIBRIUM=NOT_VERIFIED`.
- The raw global BA verdict remains `FAIL`.
- The global J2 tangent remains unresolved.
- Hencky material-point and directional-tangent evidence is bounded to its recorded tests; the tangent convergence plateau is not established.
- `GENERAL_SCIENTIFIC_QUALIFICATION=NOT_ACQUIRED`.

See [`wp_e01_bc_integration_report.md`](wp_e01_bc_integration_report.md) for the integrated file inventory, maturity matrix, tests, exact hashes, exclusions, and risks. The original Owner roadmap and historical reports remain unchanged.

## WP11 consolidation snapshot — prior open position

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

## WP11 v0.2.12 Owner decision review — 2026-10-25

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

## WP11 v0.2.12 Owner decision review — 2026-10-25

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

## Current WP-C02 decision and integration — Owner N13 / M-ERGE

`WP_C02_STATUS=CLOSED_BOUNDED` applies solely to WP-C02-AR/N03. The selected
integration is recorded in
[`wp_c02_integration_merge_report.md`](wp_c02_integration_merge_report.md);
it does not change the scientific scope or claim Docker equivalence. N10
execution results and their archive remain external and are linked by their
own manifest and integrity hashes.

The integration portfolio count is **19 work packages: 13 positive closures,
1 negative closure, and 5 open**, for **68.4% positive closure**. This is an
operational roadmap count only; it does not measure overall scientific
maturity or release readiness. The Owner roadmap remains preserved verbatim,
and `main`/public release are unchanged.

## WP11 v0.2.12 outcome after verification — 2026-10-25

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
