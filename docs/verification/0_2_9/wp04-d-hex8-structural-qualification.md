# WP04-D — HEX8 structural qualification contract

Status: `PHASE 0 — FROZEN_BEFORE_RESULT_EXECUTION`

This record freezes the bounded HEX8 G04-11 campaign at source revision
`0c23b11477140fa64b5dd2a74def3a042bfe3d8e` before any HEX8 structural result
is executed. The machine-readable contract is
`qualification/0_2_9/wp04d/hex8_contract.json`.

## Scope

The target is the existing full-integration HEX8 Total-Lagrangian
Saint-Venant–Kirchhoff static route for a homogeneous isotropic 3-D material,
serial execution, fixed translational DOFs on the x=0 face, and a distributed
dead load on the x=L face. Contact, arc-length, reduced integration, hourglass
control, J2-plus-geometry, nonlinear dynamics, and maturity promotion are out
of scope.

The physical benchmark is the frozen TET4 cantilever: `L=4.0`, `H=0.5`,
`D=0.5`, `E=1.0e6`, `nu=0.30`, and total resultant `[0,-50,0]`. The HEX8
boundary load is not equal-shared over end nodes. A constant face traction
`[0,-200,0]` is integrated consistently over each Q4 face; each face corner
receives one quarter of the face integral and shared nodes are accumulated.
The reference resultant and moment are checked before solving.

## Frozen meshes and gates

Required meshes are H1 `16×8×8` (1,377 nodes, 1,024 HEX8, 4,131 DOFs), H2
`24×12×12` (4,225 nodes, 3,456 HEX8, 12,675 DOFs), and H3 `32×16×16`
(9,537 nodes, 8,192 HEX8, 28,611 DOFs). H4 `48×24×24` (30,625 nodes,
27,648 HEX8, 91,875 DOFs) is predeclared as a rescue pair only: it may be
used only after an H2→H3 failure, evidence of slow discretization convergence,
and acceptance of the explicit rescue rule. No post-result mesh invention is
permitted.

The primary H2→H3 limits are 2% for end displacement, reaction, and strain
energy, and 10% for the volume-weighted representative `sigma_xx`. Force and
moment equilibrium must each be at most `1e-8`. Every counted state must stay
inside `det(F)≥0.20`, principal stretches `[0.75,1.30]`, and
`||E||_F≤0.30`.

The representative stress region is fixed in reference coordinates:
`0.40≤X/L≤0.60`, `0.75≤Y/H≤0.90`, and `0.25≤Z/D≤0.75`; it is volume-weighted
and excludes clamp/load singular regions. Tip displacement, reaction, energy,
equilibrium, deformation envelope, accepted load factors, Newton history,
termination classification, and MINRES diagnostics are recorded.

## Frozen solver and replay route

The owner-approved C2R6 route is used exactly: 12 fixed increments, Newton
tolerance `1e-10`, canonical existing line search, MINRES+Jacobi with
`rtol=1e-11`, `atol=1e-14`, `maxiter=10000`, direct fallback disabled, and
floor-aware termination enabled. Accepted physical state remains owned by
`UnifiedContinuationController` plus `NonlinearStateTransaction`.

H1 is the declared replay case. Two independent runs compare final physical
observables, accepted load path, and termination classifications at relative
`1e-12` / absolute `1e-14`. H2 and H3 are not duplicated solely for replay
when execution cost is material.

The supporting small-load sequence is also frozen before execution on H1:
load multipliers `0.1`, `0.01`, and `0.001`, each compared with a linear HEX8
reference using the identical mesh, material, boundary conditions, and
consistent face-load construction. At the smallest multiplier the displacement
and reaction relative limits are `1e-4`.

## Phase boundary

This file records the contract only. Result execution and G04-11 judgment are
the next phase. G04-12 is limited to preparing machine-readable HEX8 inputs for
the later cross-family decision; it is not decided here. WP04 remains `0/12`,
TET4 and HEX8 remain `RESEARCH_ONLY`, and production mechanics source is
unchanged.
