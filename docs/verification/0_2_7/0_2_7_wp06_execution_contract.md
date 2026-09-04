---
doc_id: DOC-027-LU2-WP06-001
revision: 0.1
status: controlled_evidence
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# LU2-WP06 - Execution contract, recovery and diagnostics

WP06 installs a small additive contract around existing routes. It does not
replace the router and does not alter FEM assembly, solver tolerances or
formulations.

## Lifecycle

`ExecutionSession` enforces the following fail-closed lifecycle:

`CREATED -> VALIDATED -> RUNNING -> CONVERGED -> CHECKPOINTED -> RECOVERED -> RUNNING`

Any terminal failure is represented by `FAILED` and requires a structured
diagnostic. Invalid transitions are rejected. Each session records the source
SHA, route, backend, solver status, provenance, evidence link and state history.

## Diagnostics

The stable taxonomy is defined in
`src/solveur/execution/diagnostics.py`. Codes use the `QF-EXEC-` namespace and
carry a category, deterministic message, minimal context and a recoverability
flag. It covers model/input errors, unsupported capabilities, unavailable
backends, non-convergence, resource limitation, numerical invalidity,
checkpoint corruption, recovery failure and unclassified execution failure.

Existing solver exceptions can be mapped with `diagnostic_from_exception`.
Unknown exceptions remain `EXECUTION_FAILURE`; they cannot become a PASS.

## Recovery boundary

Existing versioned NPZ checkpoint stores remain the persistence authority.
Targeted tests demonstrate valid round trips and reject corrupted or
incompatible checkpoints. The recoverable boundary is limited to fixed-load
nonlinear static, arc-length nonlinear static and Newmark transient routes.
Linear static, buckling, harmonic, geometric nonlinear and large distributed
routes have no restart claim under this WP06 contract.

This scope is intentionally bounded: a valid checkpoint does not imply a
universal fault-tolerance guarantee, and an unavailable or invalid recovery
never becomes a successful result.

## Evidence and tests

The machine-readable contract is
`qualification/0_2_7/wp06_execution_contract.json`, with closeout state in
`qualification/0_2_7/lu2_wp06_state.json`. The new focused tests are
`tests/unit/test_execution_contract.py`; legacy nonlinear and dynamic
checkpoint tests remain unchanged and continue to cover their existing paths.

WP06 is `PASS_WITH_LIMITATIONS`. No heavy benchmark, full regression, new
physics or numerical formulation change was performed.
