# WP09 — bounded corotational small-strain J2 candidate

Status: implementation candidate; not formally qualified and not awarded points.

This package implements Owner-selected option A for WP09: a corotational
geometric-nonlinear route with an additive small-strain von Mises/J2 material
state. It is deliberately additive. The existing Green–Lagrange / second
Piola route remains available under `kinematics=total_lagrangian_j2` and is not
replaced, rewritten, or reinterpreted by this work.

## Formulation

For each integration point, the deformation gradient is decomposed as

```text
F = R U
```

The constitutive update is evaluated on the local corotated strain

```text
e_local = U - I
```

using the existing additive small-strain J2 material update. The local stress
is rotated to the spatial force measure with

```text
P = R sigma_local
```

The element tangent is a central-difference tangent of the complete internal
force at fixed committed material state. This exposes the geometric and frame
transport terms to Newton without claiming an analytic finite-strain
consistent tangent.

Committed tensorial state is transported from the previous corotated frame to
the current frame. Trial state is returned separately and is therefore subject
to the existing nonlinear transaction, rollback, and acceptance rules.

## Explicit bounded scope

The route is bounded by the Frobenius norm of the local stretch strain:

```text
||U - I||_F <= corotational_max_local_strain
default = 0.05
```

An invalid determinant or a bound violation raises a controlled nonlinear
failure; it is never silently clipped. The route currently supports the
homogeneous solid families TET4, TET10, HEX8, and HEX20, with Full Newton
only. TET4 and HEX8 are the initial candidate verification families; TET10
and HEX20 are implemented but remain outside the first formal gate until
their dedicated evidence is produced.

The route is intended for large rigid rotations with small local strains. It
does not claim validity for large local plastic strains, finite-strain
multiplicative plasticity, or arbitrary large-deformation plasticity.

## Required gates before any formal WP09 attribution

1. Rigid-rotation objectivity with zero spurious force/stress.
2. Independent finite-difference verification of the numerical tangent.
3. State transport verification across a changing corotated frame.
4. Trial-state immutability and rollback verification.
5. Bounded TET4/HEX8 structural solves with equilibrium and envelope checks.
6. Load-step and mesh sensitivity inside the declared local-strain bound.
7. An independent compatible reference or observable recomputation, explicitly
   labelled so it is not mistaken for an independent FEM solve.
8. Replay and source/provenance verification.

Failure of any required gate remains visible and blocks formal attribution.

## Deliberate non-claims

This candidate does not qualify:

- the existing Green–Lagrange route as a finite-strain plasticity model;
- multiplicative `F = F_e F_p` plasticity;
- finite sliding or contact coupling;
- follower-load or pressure-coupled tangent consistency;
- dynamics, MPI/PETSc, or distributed restart;
- general bifurcation/postbuckling behavior;
- external-solver correlation;
- arbitrary local strains above the frozen bound.

The Green–Lagrange route remains the separate research path. Results from the
two formulations must not be mixed in one qualification record without an
explicit formulation label and provenance check.

## Current implementation evidence

The implementation adds `src/solveur/elements/solid/corotational_j2.py` and
opt-in dispatch through `kinematics=corotational_j2`. Targeted tests cover
TET4/HEX8 execution, rigid rotation, state transport, committed-state
immutability, the local-strain guard, and uncached assembly dispatch.

This document is a candidate contract only. It does not close OD-029-01,
does not update the official WP09 ledger, and does not award WP09 points.
