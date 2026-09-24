---
doc_id: DOC-029-WP13-EXEC-001
revision: 0.1
status: frozen_execution_protocol
applicable_version: 0.2.9-development
---

# WP13 execution contract — bounded performance, API and diagnostics

This prospective protocol is limited to WP13. It was frozen before running
the tests or performance campaign. It binds to the governing baseline
`9c4048dc1909520e3933f86b2b62a9bfd6562c2c`; execution must occur from the
commit containing the contract, whose exact SHA is recorded separately as
`EXECUTION_SHA`.

## Scope

- **API:** existing `qf_solver` facade, documented stable/provisional export
  inventory, critical signatures, compatibility imports, minimal documented
  workflow, and existing invalid-input/serialization rejection checks.
- **Diagnostics:** existing `summary`, `diagnostic`, and `values` audit modes;
  WARNING/FAIL retention; Markdown pass-row limiting; configurable warning
  for exhaustive values export.
- **Performance record:** one execution of the existing bounded nonlinear J2
  characterization for its declared TET4 and TET10 cases. Record solver and
  resource observations; do not infer speedup or scalability.

## Frozen commands and gates

Run the exact targeted tests and performance command in
`qualification/0_2_9/wp13_wp14_overnight/wp13_execution_contract.json`.
The API and diagnostic gates are the existing checked-in assertions; changing
them is outside this execution. The campaign gate is its existing
`PASS_INTERNAL` status with both declared families, PASS case statuses, and
finite required measurements. No new elapsed-time or memory threshold is
introduced.

If a required dependency is unavailable, a test fails, a campaign case fails,
an observable is non-finite, or provenance is inconsistent, preserve the
failure and stop WP13 fail-closed. Do not substitute a case or tune solver
parameters.

## Evidence and boundaries

Record execution/contract/policy provenance, exact commands, machine/runtime
metadata, campaign outputs and SHA-256 hashes. The campaign's time and memory
are descriptive only. No performance ranking, speedup, scalability, or
cross-machine comparison is authorized. No production mechanics, thresholds,
policy, historical evidence, WP14, or official score/ledger may be changed.

The machine ledger currently allocates WP13 one point, while the frozen
roadmap allocates two. This protocol does not reconcile that discrepancy and
does not award points; any score decision remains for Owner review.
