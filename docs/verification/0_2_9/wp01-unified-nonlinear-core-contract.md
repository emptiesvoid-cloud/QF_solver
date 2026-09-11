---
doc_id: DOC-029-WP01-001
revision: 0.1
status: prospective_contract
applicable_version: 0.2.9-development
---

# WP01 prospective Unified Nonlinear Core contract

> **Contract phase only.** WP01-A freezes architecture and acceptance gates; it
> authorizes no core implementation, formulation change, maturity promotion or
> WP02 state-persistence work.

## Canonical diagnostic convention

\[
R(u,\lambda,state)=\lambda F_{ext}-F_{internal}-F_{contact}
\]

\[
K_T=K_{material}+K_{geometric}+K_{contact}.
\]

The convention is diagnostic and architectural. Existing routes that compute
the algebraically equivalent `internal - external` residual may be adapted
inside compatibility layers; physical force definitions must not be changed to
make a sign look uniform.

Newton corrections and convergence norms apply on declared free DOFs. Fixed
DOFs remain prescribed inputs and are used for physical reaction/equilibrium
recovery. The authoritative driver owns the load factor; a contribution sees
it as immutable evaluation input and cannot advance it.

## One driver, composable contributions

The future authoritative driver owns the complete increment lifecycle:
increments, residual normalization, linear corrections, line search,
cutback/retry, acceptance/rejection, failure propagation and diagnostics.

`NonlinearAssemblyProtocol` and `CompositeNonlinearAssembly` remain the
primary composition seam. A material, geometric or contact contribution owns
only its force, tangent, trial-state update, diagnostics and admissibility
result. It never owns an independent global Newton loop.

```text
accepted state n
  -> driver.begin_trial()
  -> predictor / lambda owned by driver
  -> composite residual + tangent assembly
  -> Newton correction / line search
  -> global convergence + contribution admissibility
  -> atomic commit  OR  complete rollback + policy-controlled cutback
```

The full machine-readable contract is
`qualification/0_2_9/wp01_unified_nonlinear_core_contract.json`.

## Compatibility and non-goals

Existing public entry points may remain as adapters. No public API removal is
authorized in WP01-A. Frictional active-set/Coulomb paths remain research
compatibility until separately adapted; no frictional common-driver integration
is authorized here.

Finite-strain plasticity, geometric formulation changes, new contact or
element formulations, nonlinear MPI/PETSc, nonlinear dynamics and maturity
claims are explicit non-goals. OD-029-01 remains open and no J2-plus-geometry
physics choice is made in WP01.

See also the [ownership model](wp01-ownership-model.md),
[state transaction contract](wp01-state-transaction-contract.md),
[migration matrix](wp01-migration-matrix.md),
[failure/retry matrix](wp01-failure-retry-matrix.md) and
[prospective gate matrix](wp01-gate-matrix.md).
