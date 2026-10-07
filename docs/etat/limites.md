---
doc_id: DOC-STATE-003
revision: 2.0
status: controlled_candidate
applicable_version: 0.2.11
reviewer: ""
approver: ""
---

# Known limitations

These limitations apply to the cumulative QF Solver 0.2.11 surface.
Every result is bounded by its element family,
formulation, mesh, loads, boundary conditions, constitutive model, solver, and
evidence decision. The limitations below are technical boundaries, not a
complete list of input checks.

## Nonlinear mechanics

- A shared nonlinear driver, residual/tangent interface, and state transaction
  do not make every material/geometry/contact/backend combination available
  or qualified. Some contact active-set/recovery loops and arc-length
  correction remain specialized.
- General finite-strain multiplicative plasticity is not claimed. The accepted
  corotational J2 route supports large rotations with a small-local-strain
  assumption and is bounded to HEX8; it is not a general finite-strain model.
- The Total-Lagrangian St. Venant–Kirchhoff audit covers selected static serial
  TET4/HEX8 cases and records `GO_WITH_LIMITATIONS`, not a maturity promotion.
  It excludes contact, coupled J2/geometry, dynamics, MPI/PETSc, high-order
  families, follower loads, and reduced/hourglass HEX8 routes.
- Owner-accepted coupled evidence covers bounded static cases for TET4, HEX8,
  HEX20 and TET10. It does not cover friction, finite sliding, dynamics,
  MPI/PETSc, Code_Aster correlation, or an independent global FEM/Newton solve.
- Adaptive stepping, cutback/retry, line search and arc-length are convergence
  policies, not guarantees for arbitrary models. Current arc-length evidence
  does not establish general limit-point tracking, bifurcation, or
  postbuckling. General nonlinear transient dynamics is not covered.
- Checkpoint/restart and deterministic state digests apply only to the routes
  named in their records. Do not infer frictional-contact, distributed, or
  nonlinear-dynamics restart support from shared transaction code.

## Rotating modal and Campbell

- The rotating capability is experimental and restricted to serial dense gyroscopic
  modal analysis of straight, collinear, circular-isotropic BEAM2 shafts with
  centered rigid axisymmetric disks, constant signed spin, a fixed global
  axis, and an undamped, unprestressed small-perturbation model.
- Campbell diagrams only orchestrate single-speed modal solves and track their
  complex modes. They do not calculate forced response, unbalance amplitude,
  operational risk, instability, or validated critical speeds.
- At 100 rad/s, the high-frequency pair remains ambiguous. The tracker keeps
  the gap; it must not force continuity or interpolate across the ambiguity.
- GYRO-06 is internal mesh-convergence evidence, not independent physical
  validation. Both analysis maturities remain `EXPERIMENTAL`;
  numerical PASS does not itself qualify the capability.
- Distributed shaft gyros, variable speed, speed-dependent stiffness/mass,
  general damping, bearings, centrifugal stiffening, contact/rubbing,
  nonlinear rotors, forced unbalance response, PETSc/SLEPc and MPI are outside
  this scope.

## Contact

- Frictionless penalty node-to-triangle contact is experimental and bounded;
  it is not a general contact formulation.
- Frictional stick/slip has prior Owner-accepted bounded serial evidence for a
  narrow route, but formal requalification of the current source is not
  established. The accepted studies report mesh sensitivity; they do not
  establish mesh convergence.
- General updated search, finite sliding, self-contact, and impact/contact
  dynamics are not established by the available evidence.

## Elements, dynamics, and backends

- Nonlinear evidence is narrower than linear registry availability, especially
  for TET10/HEX20 and other higher-order routes. A linear element record does
  not imply a nonlinear capability.
- Modal, Newmark, harmonic, and linear-buckling boundaries are route-dependent.
  Mixed Newmark/harmonic records are experimental and do not establish general
  nonlinear dynamics.
- PETSc/MPI Owner-accepted evidence is limited to two-rank linear-static
  one-element cases with replicated input and root-side assembly. No strong-
  or weak-scaling, distributed assembly, nonlinear MPI, contact, or dynamics
  claim follows. Structured-TET4 large-model observations are workload- and
  environment-specific, not general performance guarantees.
- PETSc, MPI and SLEPc are optional external runtimes. Their absence must be
  reported for a backend-dependent run and does not invalidate core import.
- The `.inp` importer is a provisional bounded subset, not full Abaqus or
  CalculiX compatibility. Mixed HDF5 support is opt-in and does not establish
  restart, parallel-HDF5, or general scalability.
- WEDGE15 is unsupported; PYRAMID5 remains internal/research-only. HEX8-SRI
  is separate experimental evidence; no blanket HEX8R, B-bar, or
  hourglass-control production claim is made.

## Verification, validation, and release

- Code_Aster results are same-mesh numerical correlations for recorded
  linear-static observables and selected families. They are not experimental
  physical validation, general mesh convergence, general stress-field
  equivalence, or nonlinear solver correlation.
- Internal observable recomputation is not an independent global FEM/Newton
  solve. A test pass is not itself a maturity decision.
- No certification, Abaqus equivalence, industrial-grade guarantee, or
  universal physical validation is claimed.
- Selected wheel/sdist audits are bound to their exact source and release
  contract. A package-scoped result does not clear the full-repository G03
  archive gate or the automatic GitHub source archives. G03 remains FAIL and
  WP14 remains on HOLD.

For exact published element-analysis boundaries, see the
[0.2.8 consolidated registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/consolidated_registry.json).
For evidence see the [0.2.11 V&V summary](../verification/0_2_11/README.md),
the separate [0.2.10 records](../verification/0_2_10/README.md)
and the [capability index](../capabilities/index.md).
