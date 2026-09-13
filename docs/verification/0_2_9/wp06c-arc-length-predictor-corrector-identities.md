---
doc_id: DOC-029-WP06C-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
review_date: ""
---

# WP06-C — Arc-Length Predictor, Corrector and Constraint Identities

## Status and scope

This document records lightweight local qualification of the implemented
arc-length predictor, spherical constraint, augmented correction and radius
policy at source revision 03166e98a9a0b8cc7978c7ad2a370e441aefdc1e. The
branch is 0.2.9-wp06-prep.

The result is a technical candidate for WP06-C, weight 2. Formal WP06-C
points remain 0/2 and total WP06 formal points remain 0/8. No structural
postbuckling, large FE, external solver, MPI/PETSc or full-suite execution was
performed. The tests are mathematical/local evidence only and do not qualify
structural snap-through or postbuckling.

The frozen formulation label remains:

    SPHERICAL_ARC_LENGTH_CUSTOM

No Crisfield or Riks equivalence is claimed.

## Predictor identity

For the accepted state and free tangent, the production predictor equation is:

    K_ff * p = F_ext,ff

A deterministic two-by-two direct sparse case produced:

    relative residual = norm(K_ff*p - F_ext,ff)
                       / max(norm(F_ext,ff), 1)
                     = 0

This is below the frozen candidate limit of 1e-11.

The production arc route uses LinearSystemSolver for this predictor and
requires its convergence flag. The adapter validates finite matrix/RHS and
finite returned correction. A custom alternate adapter remains responsible
for preserving that finite-result contract; the arc initial-radius helper
does not add a second post-return finite check.

## Spherical constraint identity

For each tested radius and load scale:

    g = Delta-u^T*Delta-u
        + (load_scale*Delta-lambda)^2
        - radius^2

The frozen candidate check is:

    abs(g) / max(radius^2, 1) <= 1e-12

Measured normalized errors for small, nominal and larger scales were:

| radius | load_scale | normalized constraint error |
|---:|---:|---:|
| 1e-3 | 0.5 | 2.12e-22 |
| 5e-2 | 1.0 | 0 |
| 4e-1 | 2.0 | 0 |

ARC_CONSTRAINT_STATUS is PASS for these local cases. These are algebraic
identity checks, not evidence of a physical FE path.

## Constraint Jacobian

For the constraint:

    partial g / partial Delta-u = 2*Delta-u^T
    partial g / partial Delta-lambda = 2*load_scale^2*Delta-lambda

The production correction kernel was captured without changing its solve
behavior. Its final row matched this analytical row exactly in the tested
two-dimensional case:

    Frobenius relative error = 0
    maximum-column relative error = 0

The equality is algebraic; no result-dependent threshold was introduced.

## Augmented Newton Jacobian

For the combined residual:

    H(u, lambda) = [ R(u, lambda), g(u, lambda) ]
    R = lambda*F_ext - F_internal(u)

For the scalar test F_internal(u) = u - u^3, the direct Jacobian of H is:

    J_H =
        [ -K_tangent       F_ext                         ]
        [ 2*Delta-u        2*load_scale^2*Delta-lambda   ]

The production correction system is:

    A =
        [ K_tangent       -F_ext                       ]
        [ 2*Delta-u        2*load_scale^2*Delta-lambda ]

with right-hand side [R, -g]. Thus the production top row is the explicitly
row-scaled Newton form needed to solve A*correction = [R, -g]; it is not an
unexplained sign discrepancy. The bottom constraint row is unchanged.

Central finite differences of H were compared to the corresponding
row-normalized production matrix at three predeclared steps:

| FD step | Frobenius relative error | maximum-column relative error |
|---:|---:|---:|
| 1e-4 | 7.36e-9 | 1.00e-8 |
| 1e-5 | 7.23e-11 | 9.82e-11 |
| 1e-6 | 6.45e-12 | 8.67e-12 |

The candidate limits are 1e-6 and 5e-6. The classification is
LOCAL_CONSISTENT_ROW_SCALED for this fixed-load-direction algebraic test.
It is not a global structural tangent-consistency claim.

## Predictor orientation and root policy

The production algorithm does not enumerate quadratic roots. Its deterministic
orientation policy is:

1. begin with the sign of the target load direction;
2. when a previous accepted direction exists, use
   previous_du dot predictor first;
3. use the scaled previous_dlambda term only as a tie-breaker when the
   displacement projection is effectively zero;
4. preserve displacement-branch orientation while allowing load-factor
   reversal at a legitimate turning point;
5. report predictor sign and branch alignment as diagnostics.

The source uses a 1e-14 test for whether a previous direction exists and a
1e-12 relative projection criterion with a 1e-30 floor for the orientation
tie-break. Existing WP01/WP03 tests cover same-direction preservation,
reversal/turning behavior, deterministic initial direction and near-zero
policy boundaries.

PREDICTOR_ORIENTATION_POLICY is deterministic and continuity is PASS on the
existing focused route tests. This does not constitute bifurcation detection
or branch switching.

## Local corrector and limit-point toy

The existing reduced scalar helper uses:

    F_internal(u) = u - u^3
    F_ref = 1
    lambda = u - u^3

The analytical positive limit point is:

    u = 1/sqrt(3) = 0.5773502691896257
    lambda = 0.3849001794597505

With 80 steps, radius 0.05 and maximum 40 local iterations, the helper:

- returned PASS_INTERNAL_RESEARCH;
- observed a turning point at step 14;
- continued through the turning point for the full 80-step path;
- had maximum equilibrium error 3.25e-13;
- had one detected branch turn;
- remained finite and deterministic on exact replay.

The load-factor range was approximately [-2.608806171660758,
0.38473022923171823]. This is a reduced scalar algorithmic result. It is not
a production FE snap-through or postbuckling qualification.

## Adaptive radius local semantics

The existing UnifiedArcLengthRadiusPolicy tests provide the local policy
evidence:

- accepted low-iteration step: declared growth;
- accepted high-iteration step: declared shrink;
- accepted intermediate step: keep;
- growth is capped by maximum radius;
- shrink is floored at minimum radius;
- retryable failure: rollback then retry shrink;
- non-retryable failure or unverified rollback: terminal;
- minimum-radius exhaustion: terminal;
- target-clipped failure: next effective retry is strictly smaller.

The route source ordering confirms controller.rollback occurs before
radius_policy.on_failure. The accepted-state digest is retained while retry
radius is changed as a next-trial policy variable. No failed trial radius is
published as accepted state.

## Failure and non-finite controls

The lightweight controls exercised:

- non-finite reduced linear input: typed NAN_DETECTED;
- invalid non-finite radius control: input validation failure;
- singular augmented correction: ARC_LENGTH_FAILURE;
- non-finite augmented correction: ARC_LENGTH_FAILURE;
- radius policy terminal conditions;
- typed failure followed by composite rollback and digest verification.

The current implementation intentionally retains ARC_LENGTH_FAILURE as an
aggregate arc predictor/corrector reason. WP06-C does not redesign the
failure taxonomy. The custom-adapter post-predictor finite guard remains a
bounded implementation hardening gap, not a qualification failure of the
current LinearSystemSolver path.

## Deterministic replay

The reduced toy path was executed twice with identical settings. Results:

- accepted displacement path: exact match;
- load-factor path: exact match;
- fixed radius history: exact match;
- orientation/branch behavior: exact match;
- Newton iteration counts: exact match;
- terminal classification: exact match;
- maximum equilibrium error: finite and below 1e-8.

The frozen replay tolerances are relative 1e-12 and absolute floor 1e-14.
The observed differences for the stored path and fixed radius were zero.

## Claim boundary and governance

The maximum claim supported by this artifact is local mathematical evidence
for the current spherical custom predictor/corrector, constraint row,
deterministic orientation and bounded radius-policy semantics, plus a reduced
algebraic limit-point research demonstration.

This artifact does not claim:

- structural snap-through or postbuckling qualification;
- snap-back robustness;
- bifurcation detection or branch switching;
- high-order FE continuation;
- external validation;
- distributed or MPI continuation;
- universal convergence or conditioning behavior.

Production mechanics, convergence policy, element formulation and maturity
are unchanged. WP06-C remains a technical candidate pending Owner review and
later integration with the governing 0.2.9 policy.
