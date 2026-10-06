---
title: Experimental rotating modal analysis
doc_id: DOC-MECH-ROTATING-MODAL-WP05
revision: 1.0
applicable_version: 0.2.11
status: controlled_candidate
reviewer: ""
approver: ""
---

# Experimental rotating modal analysis

This route belongs to the unreleased 0.2.11 candidate; the latest published
package remains 0.2.10. Its experimental maturity and bounded scope do not
change the published release contract.

This page documents the bounded `rotating_modal` capability introduced for
QF Solver 0.2.11. It describes the numerical route; it does not assign a
qualification level. The route remains **EXPERIMENTAL**.

## Scope

The initial implementation accepts an undamped, unprestressed, linear and
serial model consisting of a straight, connected, unbranched BEAM2 shaft and
one or more centered rigid axisymmetric disks attached to existing beam
nodes. Beam sections must be circular and isotropic, and the spin axis must be
common, fixed in the global spatial frame, and parallel to the shaft. The
solver uses a dense SciPy generalized eigenvalue solve.

The analysis is not a general rotating-machinery solver. It rejects shells,
solid rotor meshes, eccentric or non-axisymmetric disks, generic duplicate
disk masses, unsupported constraints, contact, damping, centrifugal
stress-stiffening, variable speed, distributed beam gyroscopic terms,
nonlinear rotor response, and sparse/PETSc/SLEPc/MPI backends.

## Model and sign convention

For small perturbations around the undeformed, unprestressed state, the
equation is

```text
M q_ddot + Ω G q_dot + K q = 0
q(t) = Re(φ exp(λ t))
(λ² M + λ Ω G + K) φ = 0
```

`Ω` is a signed scalar in rad/s and appears once in the quadratic eigenvalue
problem. The configured axis is an explicit, normalized global vector using
the right-hand rule; the frame convention is `global_fixed_right_hand_rule`.
RPM conversion is available only through an explicit API and is never
inferred from an input value.

For a disk with unit axis `a`, mass `m`, diametral inertia `Jd`, and polar
inertia `Jp`, its nodal mass block is

```text
M_disk = diag(m I, Jd (I - a aᵀ) + Jp a aᵀ)
G_disk = diag(0, -Jp [a]×)
```

`G_disk` is the unit-speed contribution; the assembler does not multiply it
by `Ω` or project it to skew symmetry after assembly. The rotating disk owns
both its translational/rotary mass and its gyroscopic term. A generic
concentrated mass cannot also represent that disk at the same node.

## Numerical route and results

The route reuses structural `K` and `M` assembly, adds disk mass and a
separate skew `G`, and applies the same homogeneous fixed-DOF reduction to all
three matrices. It checks symmetry, skew symmetry, positive definiteness of
reduced `M` and `K`, and finite values before solving. It then solves the
dense generalized companion pencil with `scipy.linalg.eig(A, B)`; it does not
use a symmetric eigensolver or explicitly invert `M`.

The solver retains every raw complex root and mode. The convenience view
selects positive-imaginary oscillatory roots deterministically, while raw
roots remain available for inspection. Modes are mass-normalized with
`φᴴ M φ = 1`, phase-normalized without changing the represented eigenspace,
and checked against the original quadratic polynomial. Serialized complex
values carry explicit real and imaginary components.

At `Ω = 0`, the route is checked against the classic modal solve for the same
physical `K/M`; degenerate eigenspaces are compared as subspaces, not by
column-wise vector equality. Passing numerical checks does not imply
qualification or maturity promotion.

## Verification status and limitations

The 0.2.11 WP05 verification records report the exact cases, source identity,
environment, tolerances, and evidence availability. The initial checks cover
local disk formulation, zero-speed modal recovery, an independent analytical
disk oscillator, signed-speed spectrum behavior, complex result
serialization, and a bounded dense-backend characterization. Read those
records for the measured size limit; no limit is extrapolated beyond tested
sizes.

This single-speed route does not implement speed sweeps or modal tracking.
The separate experimental [`campbell` route](campbell.md) orchestrates
multiple `rotating_modal` solves and reports modal association and ambiguity;
it does not change the WP05 physical formulation or imply general rotordynamics
support.
