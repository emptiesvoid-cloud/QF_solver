# 026-G09 Contact Lot 2 Contract

Lot 2 extends the existing bounded frictionless-contact evidence without changing the contact formulation or closing the official `026-G09` gate.

## Scope

- TET4 assembled through the existing common nonlinear driver.
- Frictionless node-to-triangle penalty contact in the initial configuration.
- Three physical mesh levels (`1`, `2`, `4`) on the same unit-block problem.
- Penalties `1e4`, `1e5` and `1e6`, selected from the predeclared Lot 1 sweep.
- Open/close/reopen load paths.
- Controlled common-driver rejection before the first commit and after one committed increment.
- Fail-closed validation and convergence failures.

Finite sliding, friction, general surface-to-surface contact, external contact correlation and a production penalty interval remain out of scope.

## Requirements

| ID | Evidence | Policy |
|---|---|---|
| `G09-L2-001` | Mesh and penalty sensitivity | Fixed physical problem; report trends, do not create a universal range. |
| `G09-L2-002` | Open/close/recontact paths | Signed gap, active set, no inactive attraction, deterministic final replay. |
| `G09-L2-003` | Cutback/retry/rollback | Committed state and displacement remain intact; contact active set is stateless and recomputed. |
| `G09-L2-004` | Adversarial inputs/failures | Typed or reason-coded failure, finite diagnostics, no silent convergence. |
| `G09-L2-005` | Candidate penalty governance | Candidate is experimental and requires Owner review; no conditioning cutoff is approved. |

The exact machine-readable contract is `qualification/0_2_6/g09_lot2_requirements.json` and the case mapping is `qualification/0_2_6/g09_lot2_case_registry.json`.

## Evidence status

The runner writes source SHA, clean-source state, configuration, thresholds, case results and artifact digests. The generated report is evidence for Lot 2 only; `gates.json` remains `026-G09.status = NOT_STARTED`.
