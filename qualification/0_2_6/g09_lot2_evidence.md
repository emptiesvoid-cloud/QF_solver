# 026-G09 Contact Lot 2 Evidence

Status: **PASS_WITH_LIMITATIONS**; official gate remains **NOT_STARTED**.
Source SHA: `341e82d61a2074bd744c84c9c7a9140bd1ac0bb0`; dirty: `False`.

## Scope and policy

This lot exercises the existing TET4 frictionless node-to-triangle penalty path. No friction, finite-sliding, surface-to-surface formulation or production penalty range is qualified.

| Declared item | Value |
|---|---|
| Mesh levels | `(1, 2, 4)` |
| Penalties | `(10000.0, 100000.0, 1000000.0)` |
| Solver tolerance | `1.0e-08` |
| Reference comparison tolerance | `1.0e-08` |

## Mesh and penalty sensitivity

| Mesh | Nodes | Elements | DOF | Penalty | Gap | Penetration | Reaction norm | Residual | Iterations |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 8 | 5 | 24 | 1e+04 | -1.62380333e-03 | 1.62380333e-03 | 1.93495444e+01 | 2.20090744e-13 | 2 |
| 1 | 8 | 5 | 24 | 1e+05 | -1.62435220e-04 | 1.62435220e-04 | 1.93500493e+01 | 8.28848150e-13 | 2 |
| 1 | 8 | 5 | 24 | 1e+06 | -1.62440711e-05 | 1.62440711e-05 | 1.93500999e+01 | 2.17269758e-11 | 2 |
| 2 | 12 | 10 | 36 | 1e+04 | -1.70422856e-03 | 1.70422856e-03 | 1.91853109e+01 | 3.71258871e-13 | 2 |
| 2 | 12 | 10 | 36 | 1e+05 | -1.70468143e-04 | 1.70468143e-04 | 1.91863730e+01 | 1.39550599e-12 | 2 |
| 2 | 12 | 10 | 36 | 1e+06 | -1.70472673e-05 | 1.70472673e-05 | 1.91864793e+01 | 1.89075422e-11 | 2 |
| 4 | 20 | 20 | 60 | 1e+04 | -1.71796771e-03 | 1.71796771e-03 | 1.90947909e+01 | 1.45954887e-14 | 2 |
| 4 | 20 | 20 | 60 | 1e+05 | -1.71840302e-04 | 1.71840302e-04 | 1.90960341e+01 | 5.49250936e-13 | 2 |
| 4 | 20 | 20 | 60 | 1e+06 | -1.71844656e-05 | 1.71844656e-05 | 1.90961584e+01 | 6.61865229e-11 | 2 |

Mesh-level replay exact: `True`.
Penetration monotone within each tested mesh: `True`.
Mesh trend is observational; no universal convergence or penalty band is inferred.

## Contact cycles

| Case | Load path | Active sequence | Gap sequence | Final replay | Status |
|---|---|---|---|---:|---|
| `open_to_close` | `[0.0, 1.0]` | `[False, True]` | `[1.0, -0.00016244]` | 0.000e+00 | `PASS_INTERNAL_RESEARCH` |
| `close_to_open` | `[1.0, 0.0]` | `[True, False]` | `[-0.00016244, 1.0]` | 1.402e-15 | `PASS_INTERNAL_RESEARCH` |
| `open_close_open` | `[0.0, 1.0, 0.0]` | `[False, True, False]` | `[1.0, -0.00016244, 1.0]` | 1.402e-15 | `PASS_INTERNAL_RESEARCH` |
| `open_close_open_reclose` | `[0.0, 1.0, 0.0, 1.0]` | `[False, True, False, True]` | `[1.0, -0.00016244, 1.0, -0.00016244]` | 5.757e-16 | `PASS_INTERNAL_RESEARCH` |
| `load_up_down` | `[0.0, 0.25, 0.5, 0.75, 1.0, 0.75, 0.5, 0.25, 0.0]` | `[False, True, True, True, True, True, True, True, False]` | `[1.0, -1.244e-05, -6.244e-05, -0.00011244, -0.00016244, -0.00011244, -6.244e-05, -1.244e-05, 1.0]` | 1.469e-15 | `PASS_INTERNAL_RESEARCH` |

Recontact replay exact: `True`.
The contact active set is recomputed from the current trial displacement; no ghost contact state is stored.

## Cutback, retry and rollback

| Case | Rejected attempt | Rejected increments | Adaptive path | Digest preserved | Reference error | Status |
|---|---:|---:|---|---:|---:|---|
| `failure_before_first_commit` | 1 | 1 | `[0.5, 1.0]` | True | 4.514e-09 | `PASS_INTERNAL_ROLLBACK` |
| `failure_after_one_committed_increment` | 2 | 1 | `[0.5, 0.75, 1.0]` | True | 9.118e-09 | `PASS_INTERNAL_ROLLBACK` |

Contact transaction: `N/A` for persistent contact state because this frictionless active set is stateless; common material/displacement transaction is checked.

## Failure and adversarial contract

| Case | Status | Exception/reason | Deterministic | Fail closed |
|---|---|---|---:|---:|
| `invalid_penalty` | `EXPECTED_FAILURE` | `InputValidationError x3` / `None` | True | True |
| `invalid_target` | `EXPECTED_FAILURE` | `MeshValidationError` / `None` | True | True |
| `invalid_master_geometry` | `EXPECTED_FAILURE` | `InputValidationError` / `None` | True | True |
| `unsupported_contact_route` | `EXPECTED_FAILURE` | `MeshValidationError` / `None` | True | True |
| `excessive_penetration` | `EXPECTED_FAILURE` | `NumericalConvergenceError` / `CONTACT_PENETRATION_EXCESSIVE` | True | True |
| `newton_max_iterations` | `EXPECTED_FAILURE` | `NumericalConvergenceError` / `MAX_ITERATIONS` | True | True |

## Penalty governance

Experimental candidate for Owner review only: `1e4..1e6`.
Status: `OWNER_REVIEW_REQUIRED`.
The interval is an experimental candidate for the tested TET4 benchmark because all three values converged at all three mesh levels and penetration was non-increasing. It is not a production policy.
No universal production range or conditioning cutoff is approved by this report.

## Limitations

- Official 026-G09 remains NOT_STARTED; Lot 2 evidence does not close the gate.
- Scope remains TET4 frictionless node-to-triangle penalty contact in the initial configuration.
- General surface-to-surface, finite sliding, friction, self-contact and external correlation remain out of scope.
- No Owner-approved penalty range or conditioning threshold is claimed.
