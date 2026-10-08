# WP10 — Nonlinear convergence and status contract

## Existing criterion retained

The existing Newton driver computes the free-DOF residual and reports a relative residual with a finite denominator based on the target-force norm, the configured force scale, and the existing unit floor. This prevents division by zero at zero load. When force magnitudes are below that floor, the comparison behaves as an absolute residual test in the solver's force units. WP10 does not alter that public tolerance, its normalization, increment tolerances, maximum-iteration limit, or line-search/cutback acceptance rules.

The residual, displacement update, and accepted-state commit must correspond to the same candidate. A convergence test reached on an accepted candidate is finalized, step metadata is attached, and the composite state is committed. A maximum-iteration stop, constitutive/tangent error, or linear solver failure is not relabeled as convergence. A rejected increment remains present in the rejection history if a smaller cutback later succeeds.

## Status distinctions

The solver's existing typed failure reasons are retained. Relevant observable outcomes include:

| Outcome | Meaning | Accepted-state effect |
|---|---|---|
| `CONVERGED` / successful result | Existing convergence conditions satisfied and finalization completed | Candidate composite committed |
| `MAX_ITERATIONS` | Iteration budget exhausted | No commit for failed increment |
| `LINEAR_SOLVER_FAILURE` | Linear correction could not be produced | No commit for failed increment |
| `CONSTITUTIVE_FAILURE` / invalid trial | Local material or state update failed | No commit for failed increment |
| `CUTBACK_REQUIRED` / rejected attempt | Current increment rejected by existing policy | Accepted state unchanged; rejection reason retained |
| checkpoint incompatibility/corruption | Resume preconditions or integrity checks failed | No restart state installed |

Exact API names are those already present in `NonlinearFailureReason` and result diagnostics; WP10 does not add a parallel public status enum.

## Zero load and near-zero references

For zero load and zero residual, the residual criterion is finite and may accept the unchanged equilibrium state. For nonzero residual near zero target load, the absolute force scale/floor prevents unstable relative normalization. This remains unit-dependent; changing it would require a separate, explicitly validated scaling decision.

## Proof boundary

The WP10 tests check zero-load finiteness and a forced max-iteration failure whose serialized error reports `converged=false`. Existing Newton, cutback, line-search, and arc-length suites check their route-level outcomes. These software checks do not establish general nonlinear convergence, mesh-independent tolerances, or a semi-smooth Newton theorem.
