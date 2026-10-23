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

## Current WP11 consolidation — WP11-A/B

`WP11=OPEN`. The WP11-A audit and WP11-B traceability package cover the
capabilities present on this integration branch. The API surface and selected
serialization/refusal contracts have targeted non-qualifying regression
coverage; this does not close the complete WP11 integration gate by itself.
The ordinary result DTOs do not all have a shared versioned schema or generic
deserializer. WP11-B records this contract boundary for an Owner decision.

WP-D02 remains `CLOSED_BOUNDED` at its documented recovery scope. WP-E01
remains `OPEN_WITH_BOUNDED_CERTIFICATES`: the GF4 certificate is historical to
its exact TET4 slave-subsystem identity, master assembly equilibrium remains
`NOT_VERIFIED`, and the global J2 tangent remains unresolved. D01 and C02 are
not treated as WP11 prerequisites absent a demonstrated dependency or an
explicit historical contract requiring them. WP12 and WP13 remain open and
retain their separate criteria.

See [`wp11_b_closure_gate_assessment.md`](wp11_b_closure_gate_assessment.md)
for the current gate assessment and recommended decision.
