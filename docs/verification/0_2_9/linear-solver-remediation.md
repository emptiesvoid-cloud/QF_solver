---
doc_id: DOC-029-LINEAR-SOLVER-REMEDIATION-001
revision: 1.0
status: hold
applicable_version: 0.2.9-development
---

# Linear-solver remediation — initial local validation

The nonlinear Newton path now reaches a single sparse linear-solver adapter
and has opt-in, failure-isolated JSONL telemetry. The adapter records the
reduced matrix's symmetry defect and supports direct, CG, MINRES, and GMRES
with none or Jacobi preconditioning. Direct fallback is explicit and recorded.

The frozen C2-M1 zero-state reduced TET4 system has 27,744 free DOFs and
1,151,694 nonzeros; its symmetry defect is zero at the recorded scale. Direct
SuperLU completed in 4.7984 s with measured relative residual
`7.512615895580403e-10`. This is recorded for compatibility, not used to relax
the strict Krylov acceptance contract.

With `rtol=1e-10`, `atol=1e-14`, maximum 10,000 iterations, and an independent
relative residual gate of `1e-10`, MINRES+Jacobi returned `1.340678e-05` and
CG+Jacobi (with explicit SPD declaration) returned `2.552145e-09`. Both were
rejected and fell back to direct. Therefore the medium-linear stage is not
passed; nonlinear C2-M1 and C2-M2/M3 were not started.

WP04 remains HOLD, G04-10 remains unresolved, and the roadmap remains 29/100.
This record neither changes the historical WP04-C failure nor reclassifies the
owner-aborted M3 run. Raw scalar evidence is in
`qualification/0_2_9/wp04_linear_solver_remediation.json`.
