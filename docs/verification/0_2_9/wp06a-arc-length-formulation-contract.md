---
doc_id: DOC-029-WP06A-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
review_date: ""
---

# WP06-A — Arc-Length Formulation Contract

## Status and evidence boundary

This contract records the equations and policies actually implemented at
source revision 03166e98a9a0b8cc7978c7ad2a370e441aefdc1e on branch
0.2.9-wp06-prep. It is a technical candidate for WP06-A, not formal Owner
qualification. WP06-A formal points remain 0/1 and the WP06 total remains
0/8.

No structural snap-through or postbuckling solve, external solver run, heavy
solve, or full test suite is part of this artifact. No mechanics, formulation,
convergence, or maturity behavior is changed.

The exact formulation label is:

    SPHERICAL_ARC_LENGTH_CUSTOM

The label is chosen because the implementation uses a spherical constraint
and a custom predictor/orientation/correction path. The source does not
establish equivalence to a named Crisfield or Riks implementation, so neither
named method is claimed.

## Source trace

| Contract item | Source evidence | Classification |
|---|---|---|
| Route dispatch | src/solveur/core/nonlinear/solver.py, NonlinearStaticSolver.solve | IMPLEMENTED |
| Continuation loop | src/solveur/core/nonlinear/arc_length.py, NonlinearArcLengthMixin._solve_arc_length | IMPLEMENTED_BOUNDED |
| Step predictor/corrector | src/solveur/core/nonlinear/arc_length.py, _solve_arc_length_step | SPECIALIZED |
| Sparse augmented solve | src/solveur/core/nonlinear/iteration.py, solve_arc_length_correction | IMPLEMENTED_BOUNDED |
| Controls and validation | src/solveur/core/nonlinear/controls.py, ArcLengthControls | IMPLEMENTED_BOUNDED |
| Radius authority | src/solveur/core/nonlinear/robustness.py, UnifiedArcLengthRadiusPolicy | IMPLEMENTED_BOUNDED |
| Compatibility seam | src/solveur/core/nonlinear/driver.py, common contribution/residual helpers | REUSABLE |

The public arc-length route is nonlinear_static. The separate
geometric_nonlinear_static route currently exposes a full-Newton path rather
than an arc-length method. This contract therefore does not generalize the
arc-length claim to that route.

## Residual contract

The implemented continuation residual is:

    R(u, lambda) = lambda * F_ext - F_internal(u)

The assembled internal vector is supplied by the common nonlinear assembly
seam. It includes the applicable internal contribution and any contribution
owned by that assembly route. The arc-length loop evaluates the residual on
free degrees of freedom as:

    residual = load_factor * loads - internal

The residual reference used by the current route is:

    reference = max(norm(loads[free]), 1.0)

This is a convergence normalization, not a physical equilibrium claim.
Future structural qualification must separately record vector equilibrium and
its scale.

## Spherical constraint contract

For one trial step relative to the last accepted state:

    delta_u = u_trial,free - u_accepted,free
    delta_lambda = lambda_trial - lambda_accepted

The source carries the accepted base factor as base_factor and evaluates:

    g =
        delta_u^T * delta_u
        + (load_scale * delta_lambda)^2
        - radius^2

The convergence value used by the arc step is:

    relative =
        max(
            norm(residual[free]) / reference,
            abs(g) / max(radius^2, 1.0e-30)
        )

An arc step is accepted only when relative is less than or equal to the
caller-supplied nonlinear tolerance. Thus both the physical residual term and
the spherical-constraint term participate in the current acceptance test.

The current arc loop does not impose a separate correction-magnitude
acceptance gate. A future WP06-C or WP06-F contract may require that
observable, but its absence is recorded as a gap rather than silently
invented here.

## Predictor contract

At the accepted base state, the free predictor is obtained from:

    K_ff * predictor = F_ext,ff

where K_ff is the current free tangent and F_ext,ff is the reduced external
load direction. The configured nonlinear linear-solver adapter is used for
this predictor.

Let alpha denote load_scale and s denote the attempted radius. The scalar
load-factor predictor is:

    delta_lambda_pred =
        direction * s / sqrt(predictor^T * predictor + alpha^2)

and the displacement predictor is:

    delta_u_pred = delta_lambda_pred * predictor

The initial direction is the sign of the target load direction. Once a prior
direction exists, the implementation first uses displacement orientation:

    displacement_orientation = previous_du^T * predictor

The scaled augmented-space value is retained as a tie-breaker:

    tangent_orientation =
        displacement_orientation + alpha^2 * previous_dlambda

If the displacement projection is materially nonzero, its sign selects the
direction. The source uses a relative projection threshold based on
1.0e-12 times the product of the two norms, with a 1.0e-30 floor. Only when
that projection is effectively zero can the scaled load-factor term select a
negative direction. This preserves displacement-branch orientation while
allowing a legitimate load-factor reversal at a turning point.

If load-factor turning is disabled and the predictor would pass the target,
delta_lambda is clipped to target_factor - base_factor. The clip is a target
policy boundary, not a new predictor equation.

The reported predictor sign is the sign of delta_lambda_pred. The reported
branch direction is computed from the accepted-step augmented alignment when
there is a previous direction. No quadratic roots are enumerated.

## Radius and load-scale contract

If no explicit radius is supplied, the initial helper computes:

    load_scale_0 = max(norm(predictor), 1.0e-12)
    radius_0 =
        sqrt(predictor^T * predictor + load_scale_0^2)
        / max(load_steps, 1)

The route then applies optional parameters:

- arc_length_radius: explicit current radius override;
- max_arc_length_radius: maximum carried radius;
- arc_length_load_scale: explicit load-factor scaling override.

The route rejects a non-finite or non-positive current radius, a maximum below
the current radius, or a non-positive load scale. The radius is measured in
the mixed displacement/load-factor space defined by the chosen load_scale;
there is no claim that it is dimensionless without that declared scaling.

## Corrector contract

For n_free free displacement unknowns, each correction uses the sparse
augmented system:

    [ K_ff                  -F_ext,ff                         ] [du]
    [ 2 * delta_u^T          2 * alpha^2 * delta_lambda       ] [dl]

with right-hand side:

    [ residual[free] ]
    [ -g            ]

The top-right block is the load column and the bottom row is the linearized
spherical constraint row. The result is applied as:

    u_trial,free += du
    lambda_trial += dl

The matrix has dimension n_free + 1. It is generally non-symmetric because
the two coupling blocks have different scaling and orientation. It is not
expected to be SPD.

The source retains sparse CSC structure and calls SciPy sparse direct
spsolve. CG and MINRES are not valid by default for this augmented system;
the regular nonlinear adapter's SPD or WP04 iterative policy must not be
inherited. Any iterative/PETSc arc correction requires an independent
conditioning, symmetry, convergence and replay contract.

Matrix-rank warnings, value/shape/runtime failures and a non-finite correction
are reported as the typed ARC_LENGTH_FAILURE route reason. The current
umbrella is an implementation boundary, not a claim that all predictor,
constraint and correction failure causes are independently classified.

## Adaptive-radius contract

ArcLengthControls currently validates and stores:

| Control | Current default or rule |
|---|---|
| adaptive_radius | false unless adaptive_arc_length is enabled |
| minimum_radius | 1.0e-10 |
| growth_factor | 1.5 |
| shrink_factor | 0.5 |
| grow_below_iterations | max(2, max_iterations // 4) |
| shrink_above_iterations | max(3, max_iterations // 2) |

The controls reject non-finite values, non-positive minimum radius, growth
below one, shrink outside (0,1), and invalid iteration-threshold ordering.

After a globally accepted step:

- grow when adaptive mode is enabled and iterations are at or below the grow
  threshold, capped at maximum_radius;
- shrink when adaptive mode is enabled and iterations are at or above the
  shrink threshold, floored at minimum_radius;
- otherwise keep the policy radius.

After a failed step, the continuation controller rolls back first. Only then
does UnifiedArcLengthRadiusPolicy classify the failure and calculate a
retry-level radius. A retryable failure reduces the policy radius by the
shrink factor. If target clipping made the effective attempted radius smaller
than the policy radius, the policy reduces further until the next effective
attempt is strictly below the failed clipped attempt. A non-retryable failure,
an unverified rollback, or a radius below the minimum produces a terminal
decision.

The rejected count is recorded by UnifiedContinuationController. There is no
separate fixed maximum-retry integer in ArcLengthControls; termination is
bounded by failure classification, minimum radius, load-factor limits and
max_arc_steps.

This separates solver-step rollback from a retry-policy update. The accepted
continuation state is not changed by rejection; the next attempted radius is a
policy variable.

## Non-finite and predictor controls

The ordinary nonlinear linear-solver adapter rejects non-finite reduced
matrices and right-hand sides before dispatch and rejects non-finite returned
corrections. The arc correction kernel rejects a non-finite augmented
correction. Continuation validation rejects non-finite load factor, radius,
maximum radius, load scale, previous load increment and previous displacement
direction.

The current implementation does not add a second independent finite check
inside the initial-radius helper after an arbitrary custom linear adapter
returns. Therefore a future alternate adapter must preserve the adapter
finite-result contract; an explicit post-predictor guard remains a bounded
hardening gap.

## Technical-candidate decision

WP06-A candidate evidence is sufficient for:

- exact identification of the implemented method as
  SPHERICAL_ARC_LENGTH_CUSTOM;
- a reproducible residual/constraint/predictor/corrector contract;
- explicit augmented-system backend and symmetry boundaries;
- deterministic radius-policy semantics and failure handling.

It is not sufficient for:

- structural limit-point qualification;
- postbuckling or snap-back claims;
- iterative/PETSc augmented-backend qualification;
- bifurcation/branch-switching claims;
- external validation or high-order continuation.

Candidate status: WP06-A technical candidate 1/1, formal points 0/1 pending
integration and Owner closure.
