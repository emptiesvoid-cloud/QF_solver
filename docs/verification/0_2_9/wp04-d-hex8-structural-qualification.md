# WP04-D — HEX8 structural qualification contract

Status: `PHASE 1 — EXECUTED; G04-11 PASS PENDING OWNER REVIEW`

This record freezes and records the bounded HEX8 G04-11 campaign at source revision
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

## Executed campaign

The frozen campaign was executed from the qualification-only runner at
execution SHA `e01e292a36dc4f2e6bfe1cbe8a64a6b563707edf`. H1, H2, and H3 all
completed normally with the exact C2R6 route; H4 was not run because the
predeclared H2→H3 rescue condition was not triggered. No production mechanics
source was changed, no PETSc route was used, and no full repository suite was
run.

| Case | Status | Nodes | HEX8 | DOFs | Wall time (s) | Tip displacement | Energy | Representative sigma_xx |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H1 | PASS | 1,377 | 1,024 | 4,131 | 521.627944 | -0.18501826612672562 | 4.620499385338013 | 2716.128200197168 |
| H1 replay | PASS | 1,377 | 1,024 | 4,131 | 576.935198 | -0.18501826612672562 | 4.620499385338013 | 2716.128200197168 |
| H2 | PASS | 4,225 | 3,456 | 12,675 | 1999.949211 | -0.1953490499118973 | 4.877906362795091 | 3052.3835804268574 |
| H3 | PASS | 9,537 | 8,192 | 28,611 | 4936.010063 | -0.19933380039473436 | 4.977170539703795 | 2910.498904645881 |

The pre-solve consistent-face-load checks preserve the physical resultant
`[0,-50,0]` and reference moment `[12.5,0,-200]` at every required level;
equal-share loading was not used. The frozen H2→H3 comparison is:

| Observable | H2→H3 relative delta | Frozen limit | Result |
| --- | ---: | ---: | --- |
| End displacement | 0.01999034019793022 | 0.02 | PASS |
| Reaction | 9.224898992711293e-14 | 0.02 | PASS |
| Strain energy | 0.019943897062970836 | 0.02 | PASS |
| Representative sigma_xx | 0.046483239095767515 | 0.10 | PASS |

Global equilibrium passes across H1–H3. The maximum force-relative error is
`6.479137079435662e-14` and the maximum moment-relative error is
`4.033649056229668e-15`. The combined deformation envelope is also passing:
minimum `det(F)=0.9924435183210853`, principal stretches
`[0.9907111439153957,1.0092228247131967]`, and maximum
`||E||_F=0.0095824348944902`.

MINRES+Jacobi completed without direct fallback. The maximum recorded
linear backward error is `1.2871251130701805e-12` (H3); the H3 process peak
RSS/private values are `475258880`/`450584576` bytes. Per-case result JSON
contains the corresponding process and telemetry-sample memory fields.
All required accepted steps are classified `CONVERGED_RESIDUAL` and the
accepted load-factor path is the 12-step path from `1/12` through `1.0`.

H1 replay is deterministic at the frozen comparison: accepted-state digests
and load factors are identical, termination classifications are identical,
and the recorded relative deltas for tip displacement, reaction, energy, and
stress are all zero. Raw arrays are retained in compressed NPZ form and load
with `allow_pickle=False`; no object arrays are present. Immediate-flush
JSONL telemetry is retained for H1, H2, H3, H1 replay, and the H1 small-load
support runs.

The frozen small-load support sequence was also executed at multipliers
`0.1`, `0.01`, and `0.001`. The displacement error decreases to
`2.5607163831358572e-05` at `0.001`, while the reaction error at that level is
`2.7738177407149553e-04`, above the supporting `1e-4` threshold. This is an
explicit supporting limitation and is not used to hide or alter the frozen
G04-11 H2→H3 mesh decision; it should be revisited in the later combined
WP04 family review.

## G04-11 decision and G04-12 preparation

The controlled audit record is
`qualification/0_2_9/wp04d/g04_11_audit.json`; the campaign summary is
`qualification/0_2_9/wp04d/hex8_campaign_result.json`. The required H1/H2/H3
cases, fixed physical load, equilibrium, deformation envelope, replay, and
H2→H3 convergence all pass, so `G04-11 = PASS` pending Owner review. H4 is
`NOT_RUN_OPTIONAL_RESCUE_NOT_TRIGGERED`.

The H3 result and raw arrays are prepared as machine-readable G04-12 inputs,
but no cross-family comparison or G04-12 decision is made in WP04-D. HEX8
remains `RESEARCH_ONLY`, WP04 remains `0/12`, and the validated total remains
`29/100` until the combined WP04 closure audit.

## Phase boundary

The contract remains immutable after result execution. This record now includes
the executed H1/H2/H3 evidence and the G04-11 judgment. G04-12 is limited to
preparing machine-readable HEX8 inputs for the later cross-family decision; it
is not decided here. WP04 remains `0/12`, TET4 and HEX8 remain
`RESEARCH_ONLY`, and production mechanics source is unchanged.
