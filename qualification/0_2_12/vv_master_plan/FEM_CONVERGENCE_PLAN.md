# FEM and time-discretization convergence plan

**Status:** PREPARATION_ONLY
**Numerical execution:** NUMERICAL_EXECUTION_NOT_PERFORMED
**WP12:** OPEN

## 1. Purpose

Use refinement studies to test discretization behavior for a declared observable and bounded formulation. A converged number is not automatically correct: retain the analytic/external reference error, model idealization, algebraic error, and discretization error separately.

## 2. Common preregistration

For every study, freeze before execution:

1. Scientific commit/tree and exact source/test/fixture/model-generator hashes.
2. Geometry, units, material axes, element order/formulation, element integration, constraints, loads and resultants.
3. Nested mesh or time-step sequence and the reason the sequence is admissible.
4. Observable definition, frame, sign, sampling location/region, recovery procedure and reference value/source.
5. Linear/nonlinear solver, tolerances, backend, frequency/time grid and stopping criteria.
6. Acceptance rule, uncertainty decomposition and treatment of failed/nonconverged levels.
7. Output path and storage budget. Retain all levels, including failures.

Do not choose a threshold after seeing the finest-level result. If the contract does not give a threshold for that observable, use CRITERION_TO_REVIEW. Do not use element counts as a surrogate for spatial resolution when element order or geometry mapping changes.

## 3. Spatial studies by family

| Family | Candidate study | Observables | Main risks / decision needed |
|---|---|---|---|
| TET4 | Structured nested cantilever or block with a smooth displacement/energy target; one separate boundary traction case | Tip displacement; resultant reaction; strain energy; fixed-region stress | Select exact study entry point. `tests/unit/test_tet4_structured_convergence.py` tests planning/reference logic; it must not be cited as an executed multi-mesh FEM run. Actual generator is `src/solveur/verification/tet4_structured_convergence.py`. |
| TET10 | Tension patch plus bending/torsion structural refinement | Displacement, frequency, energy, fixed-region stress | `src/solveur/verification/tet10_structural_convergence.py`; `tests/verification/test_tet10_structural_convergence_vnv.py::test_tet10_structural_convergence_campaign_passes` is a campaign test, but its model/output identities and current authorization still need review. |
| HEX8 / HEX8-SRI | Separate standard and SRI routes on the same controlled model | Displacement, energy, modal frequency, hourglass/quality indicators | Never pool formulations; preserve prior PASS/FAIL by formulation. |
| HEX20 / WEDGE6 / PYRAMID5 | Bounded high-order or feasibility cases | Displacement, strain, integration error, geometry diagnostics | PYRAMID5 has a kernel but no compatibility descriptor; WEDGE6 route maturity is limited. Do not call a feasibility case general convergence evidence. |
| BEAM2 | Multi-element Timoshenko cantilever; vary element length while retaining section and shear regime | Tip displacement, rotations, reactions, beam resultants, frequency | A one-element analytic test does not establish mesh convergence; exact parameters and beam theory assumptions must be frozen. |
| MITC3 / MITC4 | Flat/curved shell, laminate and modal/harmonic studies kept separate | Displacement, frequency, strain energy, ply stress/resultant at fixed locations | Shell integration, drilling condensation, local axes, ply recovery and the independent shell formulation can differ. Use finite observables, not singular edge maxima. |
| Composite | Fixed stack and geometry with structured mesh refinement | Displacement, selected ply stress, failure index | Maximum failure index at cutouts/free edges may be singular/nonconvergent; define a fixed path/distance before run. |
| Nonlinear solids | Load-step sensitivity and mesh sequence on a bounded, smooth J2 case | Equilibrium residual, force/reaction balance, plastic strain at fixed region, energy | Newton convergence and constitutive integration error are separate from mesh convergence. Keep line-search failures and rejected steps. |
| Contact | Bounded normal-contact and friction cases, one mesh parameter varied at a time | Gap, pressure resultant, penetration, equilibrium, slip/dissipation | Search/projection changes, edge transitions, stick-slip, and mesh-dependent active sets; C01 negative and C02 AR/N03-only statuses remain binding. |
| Rotordynamics | Historical mesh sizes/speeds only under dedicated rotor approval | Frequencies, QEP residual, branch frequency, subspace/MAC | GYRO-06 is historical internal convergence only. Preserve ambiguity at 100 rad/s. Do not infer broad rotor convergence. |

## 4. Time and frequency refinement

- **Direct and modal Newmark:** For a smooth linear oscillator, compare a fixed time interval and excitation with a decreasing step. Use the route’s frozen order/acceptance only where contract conditions apply. Record numerical damping and the error at identical sample times. WP06 currently has a second-order observed-order assertion in its unit test, but the test’s existence is not an execution on the candidate.
- **Base acceleration:** Keep input interpolation and end-hold behavior fixed. Compare relative/absolute outputs separately, and verify the full-mass coupling and frame/sign convention.
- **Harmonic sweeps:** Freeze frequencies and resolve resonance/near-resonance cases separately. A dense sweep does not establish convergence unless an observable and frequency-resolution criterion are defined.
- **Campbell speed sweeps:** Speeds must be explicit and frozen. Refinement in speed does not resolve a true/near modal crossing by itself. Report branch ambiguity instead of forcing continuity.

## 5. Stress and singularities

For stress convergence:

- Name the stress measure, coordinate frame, tensor/Voigt order, sign convention, and evaluation point.
- Keep the physical point or sampling region fixed as the mesh changes.
- Distinguish Gauss-point values, extrapolated nodal values, and smoothed values.
- Identify mathematical singularities from point supports, sharp corners, contact edges and cutouts. Do not require their peak stress to converge.
- If the quantity is a local peak, define a finite-radius/path observable and demonstrate it is away from changing mesh singular zones.

See `src/solveur/verification/singularity_stress.py` and the applicable post-processing contracts before selecting a stress oracle.

## 6. Existing studies and selection warning

The repository contains actual verification campaign sources and tests for TET10, shells, composites, contact, nonlinear and dynamic cases. The existence of those suites does not authorize a broad directory run. Select exact case/nodeids and inspect their marker, output effects, model size, external dependencies and evidence identity.

The unit node `tests/unit/test_tet4_structured_convergence.py::test_timoshenko_reference_and_convergence_metrics` verifies the reference/metrics logic and a synthetic trend; it does not invoke the multi-level FEM study. The production study helper exists separately. Do not list that unit node as mesh-convergence proof.

Potential actual campaign entry `tests/verification/test_tet10_structural_convergence_vnv.py::test_tet10_structural_convergence_campaign_passes` must be inspected and explicitly selected before any run. It may create files and execute multiple mesh levels; classify cost and output effects from source, not from its filename.

## 7. Acceptance

Prefer:

- A monotone/consistent trend where theory predicts it, with the error metric and reference uncertainty fixed beforehand.
- A contract-defined final increment or error bound only where its assumptions match.
- Explicit reporting of nonmonotonic behavior and model/geometry changes.
- Separate mesh convergence from external correlation and from solver residual.

If a defensible asymptotic order is not expected for mixed/distorted meshes, do not impose one. Report observed sequence and leave acceptance CRITERION_TO_REVIEW.

## 8. Proposed first mesh case

FEM-TET4-H-001 in the [catalog](BENCHMARK_CATALOG.md) is intentionally marked NEW_TEST_REQUIRED because no exact bounded, local TET4 multi-mesh node was approved by this static review. The owner should either:

1. Approve an existing verification campaign after its exact node, manifest, outputs and budgets are inspected; or
2. Authorize a small test/harness that calls the existing structured-study function using frozen nested levels and outputs.

No test, mesh, or solver was run to prepare this plan.
