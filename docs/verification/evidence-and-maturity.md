---
doc_id: DOC-VV-MATURITY-028-001
revision: 1.0
status: controlled
applicable_version: 0.2.8
reviewer: ""
approver: ""
---

# V&V, evidence and maturity

**Current release:** QF Solver `0.2.8` / `v0.2.8`
**Publication:** `PUBLISHED`

This page explains how a public capability status is supported. The current
orientation is maintained by the [0.2.8 capability index](../capabilities/index.md)
and the [consolidated element-analysis registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/consolidated_registry.json).

## Evidence chain

A bounded V&V campaign is expected to preserve the following chain:

1. **Prospective contract** — scope, inputs, tolerances, gates and failure
   policy are declared before the campaign.
2. **Frozen execution** — the declared formulation, model, solver route and
   gates are not changed after observing results.
3. **Evidence pack** — raw or machine-readable results, environment, source
   provenance and integrity digests are retained at the linked record.
4. **Independent checks** — analytical, dense, external or otherwise
   independent oracle evidence is identified with its limitations.
5. **Replay** — deterministic or semantic replay compares the declared arrays,
   states, residuals and status fields.
6. **Failure contract** — invalid inputs and unsupported scopes fail closed with
   explicit, traceable errors.
7. **Decision record** — an Owner Gate or delivery record states the final
   bounded scope and limitations.

Large raw arrays and campaign artifacts remain repository evidence. Public
pages link to the relevant manifests and records without presenting raw data
as a general performance or physics claim.

## Maturity vocabulary

| Label | Meaning in the 0.2.8 public surface |
| --- | --- |
| `QUALIFIED_BOUNDED` | The declared combination passed its frozen qualification gates within the recorded scope. It is not a universal claim. |
| `EXPERIMENTAL_BOUNDED` | A usable route with bounded evidence and explicit limitations, not a general qualified capability. |
| `EXPERIMENTAL` | An exploratory or partially verified route whose evidence is insufficient for bounded qualification. |
| `RESEARCH_ONLY` | Discovery or feasibility work; no production support claim. |
| `NOT_VALIDATED` | Implementation or architecture may exist, but the required validation gates did not pass or were not executed. |
| `INTERNAL` | Retained for development and traceability; not a public supported route. |

The 46 element-analysis records currently remain `32 QUALIFIED_BOUNDED`,
`14 EXPERIMENTAL`, `0 NOT_QUALIFIED`. Separate mixed workflows and capability
records do not change those counts.

## Current boundaries

- Mixed static, modal, translational MPC and multi-material workflows are
  separate bounded serial records.
- Mixed Newmark and harmonic workflows are `EXPERIMENTAL_BOUNDED` serial
  workflows with frozen timestep, frequency and damping scopes.
- The mixed distributed PETSc/MPI runtime is `NOT_VALIDATED`; WP13-01C remains
  unresolved and is deferred beyond the 0.2.8 release gate.
- The `.inp`, HDF5, frictionless contact and HEX8-SRI capabilities remain
  separate bounded experimental records.
- PYRAMID5, geometric nonlinear discovery and high-order interface feasibility
  remain internal or research routes.

## Historical separation

The [0.2.7 verification summary](0_2_7/README.md) and historical benchmark
pages are immutable provenance. Chronological WP01 and earlier interim
dispositions in the [0.2.8 evidence summary](0_2_8/README.md) are retained for
auditability, but they are not the current maturity state. Use the capability
index and consolidated registry for current status.
