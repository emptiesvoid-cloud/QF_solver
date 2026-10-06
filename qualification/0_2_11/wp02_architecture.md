# QF Solver 0.2.11 — WP02 targeted architecture freeze

**State:** design frozen for the approved initial 0.2.11 scope; no gyroscopic
route, physics, public API, or runtime behavior is implemented by this record.

**Baseline:** `c37179dae53604126aa6aa0d834770dfa4d2db37`

**WP01 checkpoint:** `11b235dc8fd8b8c384ab9653133f6e006e9464e0`

**Published baseline:** `v0.2.10` → `e535ff63464ddd7d76c2898df25470350b5154f1`

This is an additive architecture record for WP02 only. It does not amend the
WP01 capability/evidence inventory, any historical decision, or the immutable
0.2.10 release. `rotating_modal`, a gyroscopic matrix, a QEP solver, mode
tracking, and Campbell execution remain future WP05/WP06 work.

## 1. Audit of current responsibilities

| Component and current source | `CURRENT_RESPONSIBILITY` | `FUTURE_ROLE` | `CHANGE_REQUIRED` | `CHANGE_NOT_REQUIRED` | `RISK` |
|---|---|---|---|---|---|
| `solveur.core.router.AnalysisRouter` (`src/solveur/core/router.py`) | Normalizes settings, performs the common compatibility/mesh preflight, and dispatches explicit analysis types. | Add one explicit `rotating_modal` dispatch after common preflight, only in WP05; run its route-local validation before any K/M/G assembly. | Add the single route branch and route telemetry only if its contract is approved. | No plugin/registry framework; no change to existing route order or semantics in WP02. | A route added in only one entry point could be unreachable or bypass validation. |
| `AnalysisSettings` and JSON analysis schema (`core/analyses/settings.py`, `io/schema_analysis.py`) | `SUPPORTED_METHODS` drives settings and JSON acceptance; method parameters remain analysis-specific. | Define `rotating_modal` and its `dense_qep` method/config schema in WP05. | Route-specific validation for rotation and disks, before assembly. | No `rotating_modal` registration during WP02; do not silently accept unknown rotor data. | Duplicate or permissive schemas can accept incomplete physical inputs. |
| Compatibility descriptors and preflight (`src/solveur/compatibility/descriptors.py`, `preflight.py`) | Descriptors declare technical element/analysis compatibility; preflight checks each finite element, and checks `DISCRETE` only when the model has no finite elements. Registry maturity is evaluated separately. | In WP05, declare the bounded technical BEAM2 + `rotating_modal` route in the descriptor while retaining its explicit experimental status; add route-local disk checks because mixed beam/discrete models do not currently get a separate `DISCRETE` preflight. | Add the descriptor entry, tests for descriptor/preflight behavior, and a fail-closed `RotatingModalInputValidator` for discrete entities before assembly. | Do not create a qualification registry combination or promote maturity solely to make dispatch pass; do not broaden other element families or analyses. | Descriptor-only support could admit an unvalidated route; missing discrete validation could ignore or double-count disk inertia. |
| CLI (`solveur/cli/main.py`) and public API (`solveur/api/public.py`) | `solve_model` delegates through `AnalysisRouter`; CLI analysis choices are a separate explicit list. | Expose the future route through JSON/API and the existing `solve --analysis` surface, with the model carrying physical configuration. | Add the route name to the CLI at the same time as the WP05 route; keep configuration in the validated model input. | No new CLI flags for individual disk properties; no new public namespace export in WP02. | Two entry points can diverge; experimental behavior could be presented as stable. |
| Global sparse assembler (`core/assembly/assembler.py`) | Produces real sparse element K/M, paired assembly, load vectors, and discrete spring/mass blocks. Discrete inertial entries are consumed through `active_dofs()` and `matrix()`. | Continue to own K/M assembly. A future `RotatingDisk` mass entity in the existing discrete-mass collection participates in M exactly once via that interface. | Add no G responsibility to `GlobalAssembler`; add only the minimal disk entity/parser typing needed in WP05. | No generic contribution-provider framework and no changes to ordinary K/M routes. | Double-adding disk mass or leaking G into ordinary modal/dynamic analyses. |
| `ConcentratedMass` / `FiniteElementModel.dof_manager()` (`elements/discrete.py`, `core/model.py`) | A discrete mass owns node, mass, optional COM offset/inertia and supplies active DOFs and a mass matrix. The model asks each mass entry for active DOFs. | A future axisymmetric `RotatingDisk` is one discrete inertial entity: it owns its mass and inertias for M and its rotor identity/axis for the separate G contribution. | Add a typed disk entity and route-aware parsing in WP05; validate every discrete entry on the rotating route even when BEAM2 elements are present; represent a disk once, not as both a disk and a second concentrated mass. | Do not retrofit historical generic masses or change their matrix semantics. | Duplicate ownership corrupts M while ordinary solver tests may still appear plausible. |
| BEAM2 (`elements/beam/beam2.py`) | Six-DOF 3-D Timoshenko beam with existing linear stiffness and consistent mass, including sectional rotary inertia. | Supplies the flexible shaft K/M for the first bounded rotating route. | No element formulation changes. | No shaft/rotor coupling or centrifugal prestress in WP02/WP05 initial scope. | Requalification is required if beam stiffness, mass, frame, or DOF ordering changes. |
| DOF map, fixed constraints and dynamic reducer (`core/dofs.py`, `core/assembly/assembler.py`, `core/analyses/dynamic_reduction.py`) | `DofManager` numbers active named DOFs; `fixed_indices` returns homogeneous fixed indices. `DynamicDofReducer` additionally performs shell-director transformation and massless MITC drilling condensation; it is not a generic reduction abstraction. | Initial BEAM2-only route uses the same free-index selection for K, M, and G. | Add a small route-local selection/reduction step if needed; reject unsupported MPC/RBE and shell cases in the initial route. | Do not generalize or alter `DynamicDofReducer` for a case that has no shell drilling DOFs. | Applying different reductions to K/M/G gives a different eigenproblem; shell condensation cannot be assumed to commute with G. |
| Modal solver (`core/analyses/modal.py`) | Solves real symmetric generalized Kφ=μMφ with modal diagnostics, sparse/dense methods and shell reduction. | Remains unchanged; the new QEP path is an independent analysis solver. | None in WP02. | Do not overload `ModalAnalysisSolver` or change the classic modal contract. | Complex roots/vectors must not pass through real-only casts or alter existing modal results. |
| Result DTOs and serialization (`core/results.py`, `core/result_serialization.py`, `io/json_writer.py`) | `ModalResult` assumes real values; `HarmonicResult` holds complex responses and `complex_nodal_state` serializes real/imaginary/amplitude/phase; JSON calls `to_dict()`. | Add a separate `RotatingModalResult` DTO in WP05, with explicit complex scalar/vector encoding. | Add a new DTO and serialization helper only where needed, preserving complex data. | No widening or behavioral change to `ModalResult`; no implicit `complex → float`. | Loss of imaginary parts, phase, or eigenvalue growth rate would invalidate the result. |
| V&V (`verification/framework`, `verification/v2`, `verification/traceability.py`) | Existing framework generations have distinct resume and expected-failure guarantees; v2 binds source SHA and canonical model-input digest, while external-byte identity is not complete for every case. | Register new GYRO cases with explicit inputs, solver config, oracle, tolerances, environment and output identity; retain old records unchanged. | New prospective case contracts and runner integration in WP03/WP06 as scoped there. | No solver dependency on qualification files; no edits to old results or statuses. | A green harness test is not a qualification of the underlying physical case. |
| Post-processing | Existing plotters consume analysis results; no Campbell orchestration/tracking owner exists. | Tracking associates solved modes; Campbell orchestrates Ω sweeps; `post/campbell` only renders/exports already-tracked data. | Add separate components in WP06. | Plotting must not select or force modal branch continuity. | A visually smooth plot can conceal ambiguous or incorrect mode assignment. |

## 2. Frozen module ownership and dependency direction

```text
validated model / JSON
        ↓
AnalysisRouter ── common compatibility preflight
        ├── existing analysis solvers (unchanged)
        └── RotatingModalSolver [WP05, bounded EXPERIMENTAL]
              ├── existing GlobalAssembler ── K and M
              │      └── one RotatingDisk discrete entity contributes its M once
              ├── RotatingDiskGyroAssembler ── G only
              ├── route-local fixed-DOF selection ── same map for K, M, G
              └── ScipyDenseQEPSolver ── complex roots/vectors/residuals
                         ↓
                 RotatingModalResult
                         ↓
             ModalTracking [pairwise/cluster association, WP06]
                         ↓
              Campbell sweep orchestration [WP06]
                         ↓
              post/campbell [render/export only]
```

Dependency rules:

1. The router may dispatch to an analysis; an analysis may use assembly,
   numerical solvers, and result DTOs. Assembly and numerical solvers must not
   import the router, public API, CLI, or qualification data.
2. `RotatingModalSolver` composes existing K/M assembly with a rotor-only G
   assembler. `GlobalAssembler` does not know about Ω or G.
3. Result DTOs do not solve or track modes. Tracking consumes results but is
   not imported by a single-speed solve. Campbell orchestration calls solves
   and tracking; plotting consumes their output and never changes assignments.
4. Scientific source may emit evidence through the V&V API, but must not load
   `qualification/` files at runtime.
5. PETSc, SLEPc, MPI, distributed rotor assembly, and backend registries are
   not dependencies of the initial rotating route.
6. The existing compatibility preflight is a technical gate, not a maturity
   decision. WP05 must add the BEAM2 technical declaration and a dedicated
   rotating-input validator together; a descriptor entry alone is insufficient.

## 3. Frozen input and ownership contracts (future WP05 implementation)

### 3.1 `RotationConfig`

- **Home:** internal immutable type in
  `src/solveur/core/analyses/rotation_config.py`; parsed by the rotating-route
  validator from `analysis.parameters.rotation`.
- **Fields:** `axis_global: tuple[float, float, float]`, signed
  `speed_rad_s: float`, and `frame_convention` with the only initial accepted
  value `global_fixed_right_hand_rule`.
- **Axis:** finite, non-zero global vector, canonicalized to unit length while
  preserving direction. Its direction defines the positive right-hand rule;
  a negative speed reverses spin. Disk axes must be co-directed with this
  common rotor axis in the initial single-shaft scope.
- **Mutability:** frozen after validation; no solver-side mutation.
- **Serialization/API:** represented in model JSON under the rotating
  analysis parameters; no separate CLI flags. Serialization returns the
  canonical axis, signed speed and convention. No public `qf_solver` export
  before WP05 API review.
- **Validation:** reject non-finite speed/vector, zero axis, unsupported frame,
  incompatible disk axis, time-varying speed, damping, or unsupported backend
  before assembly. Ω=0 is valid and is the modal-recovery case.

### 3.2 `RotatingDisk` and single ownership of discrete inertia

- **Home:** typed discrete entity adjacent to `ConcentratedMass` in
  `src/solveur/elements/discrete.py`, carried once in the existing model
  discrete-mass collection.
- **Fields:** `node`, positive `mass`, positive `diametral_inertia` (`I_d`),
  positive `polar_inertia` (`I_p`), and `axis_global`. The initial disk has
  its center of mass at the attachment node and is axisymmetric.
- **Mass ownership:** the one `RotatingDisk` object is the sole source of its
  translational and rotary inertia in M. Its structural `active_dofs()` /
  `matrix()` contract lets the existing global discrete-mass path assemble M
  once. `RotatingDiskGyroAssembler` reads the same object and contributes G
  only; it never adds mass. A generic `ConcentratedMass` at a rotating-disk
  node is rejected in the first-scope validator to prevent ambiguous duplicate
  ownership.
- **Mass tensor:** for unit axis `a`, the disk rotary tensor is
  `I_d (I - a aᵀ) + I_p a aᵀ`; the center offset is zero. Its 6×6 spatial
  inertia block has `m I₃` translation, that tensor in rotation, and zero
  translation/rotation cross terms. Existing beam consistent mass remains
  separately assembled.
- **Axis/frame:** disk axis is expressed in the same fixed global frame as
  `RotationConfig`; its orientation must agree with the configured common
  shaft axis. Local element frames do not redefine spin direction.
- **Fail-closed checks:** unique disk node/entity; node is active in the model;
  no second generic lumped mass at that node; physical finite inertia; common
  axis; required rotational DOFs; initial BEAM2-only element set. No disk is
  silently ignored by a non-rotating analysis. The route-local validator must
  enumerate and validate the model's complete discrete-mass collection even
  when finite elements are also present; current common preflight does not
  separately check discrete entities in that mixed case. Reject springs or
  other unsupported discrete entities unless their rotating-route semantics
  are explicitly specified.

### 3.3 Assembly of K, M and G

- Keep `GlobalAssembler.assemble_stiffness_and_mass()` responsible for K/M.
  It already assembles element blocks plus discrete mass blocks; WP05 must
  prove the new disk entity enters that same path exactly once.
- Add a narrow `RotatingDiskGyroAssembler` in
  `src/solveur/core/assembly/rotating_disk_gyro.py`. It returns real sparse
  CSR G in the exact global `DofManager` ordering; it does not return ΩG and
  does not modify K or M.
- Require G shape to equal K and M shape, finite real entries, and
  `G.T = -G` under a predeclared assembly check. A G contribution is assembled
  only by `rotating_modal`; classic modal/Newmark/harmonic routes remain
  unaffected.
- Apply fixed-DOF reduction once: define `free` from the same global fixed
  indices and select `K[free,free]`, `M[free,free]`, and `G[free,free]` using
  the same ordering. No separate re-numbering is allowed.
- The initial route accepts homogeneous fixed DOFs only. MPC/RBE, shell
  drilling condensation, mixed element families, and any unimplemented
  constraint transform are rejected before solving. WP05 may expand this
  boundary only with a written derivation and tests.
- Do not extend `GlobalAssembler` with a general matrix plugin and do not
  reuse `DynamicDofReducer` as if its shell-specific transform were generic.

### 3.4 `QuadraticEigenSolver`

- **Home:** internal narrow solver in
  `src/solveur/core/analyses/qep.py`; no backend registry or public solver
  plugin API.
- **Initial implementation:** SciPy dense generalized eigensolve only, after
  resource characterization. Sparse K/M assembly may be converted at this
  boundary; the DDL limit must be established from measured time/memory on
  several model sizes, not guessed in WP02.
- **Contract:** `solve(M, K, G, omega_rad_s, options)` solves
  `(λ² M + λ Ω G + K) φ = 0` with `q(t)=φ exp(λt)`. M, K, G are same-size,
  finite real matrices in one reduced DOF map; Ω is finite and signed; M must
  be positive definite for the accepted initial scope.
- **Linearization:** WP05 may use the generalized companion pencil
  `A=[[0,I],[-K,-ΩG]]`, `B=[[I,0],[0,M]]`, solve `A y = λ B y`, and recover φ
  from the displacement half. Verify residuals against the original QEP, not
  only the linearized system.
- **Return:** finite complex eigenvalues, complex displacement eigenvectors,
  per-root QEP residuals, convergence/conditioning diagnostics, backend and
  solver metadata. Infinite/non-finite roots or malformed shapes fail closed;
  never coerce a complex result to real.
- No damping, speed sweep, forced response, centrifugal stress stiffening,
  sparse/PETSc/SLEPc/MPI solver, or nonlinear rotor in the initial route.

## 4. Complex result contract

`RotatingModalResult` is a distinct result DTO added only with WP05. Do not
reuse `ModalResult`: its current eigenvalue/mode serialization is real-valued.
Keep the classic modal schema byte-for-byte and behaviorally unchanged.

The new DTO contains:

- analysis/status/method, mesh and DOF metadata;
- the canonical global spin axis, signed Ω and frame convention;
- complex λ per root, with real and imaginary parts explicitly retained;
- complex eigenvector shape by global DOF/node;
- derived frequency `abs(Im(λ))/(2π)` and growth rate `Re(λ)` without
  discarding either part;
- scaled residual of the original quadratic polynomial;
- optional polarization/whirl descriptor with its basis and a status such as
  `DEFINED`, `AMBIGUOUS`, or `NOT_DEFINED`; no invented classification;
- solver diagnostics and bounded experimental maturity metadata.

JSON represents every complex scalar/vector using explicit `real` and `imag`
fields (optionally amplitude/phase for display), never a JSON-native complex
number and never an implicit `float`. Existing `complex_nodal_state()` is the
starting serializer for components. Non-JSON writers must either define an
explicit complex representation or reject this DTO clearly. Mode scaling and
phase normalization must be explicit in the DTO contract; degeneracy does not
imply a unique vector basis, so tracking compares subspaces where needed.

The single-speed solver returns roots and residuals only; it does not attach
cross-speed track IDs. A complex result or passing serialization test does not
promote the experimental maturity.

## 5. Tracking and Campbell ownership

| Layer | Owns | Must not own |
|---|---|---|
| `rotating_modal` | One solve for one fixed signed Ω and one input model. | Sweep loops, inter-speed IDs, plotting. |
| `modal_tracking` (WP06) | Pairwise/cluster matching between adjacent speed results, confidence and ambiguity reporting. | Solving mechanics or editing result eigenvectors to make a curve smooth. |
| `campbell` orchestration (WP06) | Frozen speed grid, repeated single-speed calls, persisted raw results and track table. | Hiding failed speeds, replacing physical roots, claiming forced response/critical operation. |
| `post/campbell` (WP06) | Plot/export existing frequencies and tracking states. | Assignment, thresholds, branch decisions. |

Tracking uses phase-invariant complex MAC as the primary vector similarity,
frequency proximity and declared polarization diagnostics as additional
evidence. Near-degenerate clusters use subspace similarity/principal angles;
individual identity is not asserted where a cluster basis is ambiguous.
Assignment/ambiguity criteria and thresholds must be frozen before looking at
the Campbell output. Keep unmatched modes and ambiguous intervals explicit;
never force a continuation merely to obtain smooth curves. A Campbell diagram
is natural frequency versus spin speed, not a forced response, amplitude
prediction, or operational criticality proof.

## 6. V&V, imports, and deferred interfaces

- Add new cases prospectively under the approved GYRO contracts. Each run must
  bind source SHA, canonical model/input identity, rotation and disk
  configuration, solver options, reference/oracle identity and digest,
  tolerance policy, environment and result digest. Existing WP01 inventory
  classifications remain unchanged.
- The existing v2 runner already binds source SHA and canonical case input;
  WP03 must decide how to bind external reference bytes and solver settings.
  Do not treat the old framework's source-only resume key as sufficient for a
  new gyro run. Do not alter old output to fit a new schema.
- Imports of `qf_solver`/`solveur` and non-rotating routes must not import
  optional PETSc/SLEPc/MPI packages. The dense SciPy QEP path is isolated and
  optional packages remain deferred.
- JSON remains the first input route; the current CLI analysis choices need
  an explicit synchronized update in WP05. Public stability classification
  for the new route/result starts `EXPERIMENTAL`/provisional, not STABLE.
- WP05 must update the BEAM2 compatibility descriptor so the common preflight
  does not reject the route as undeclared. This is a technical-route declaration
  only: do not add a compatible-maturity registry record merely to enable the
  route. Without an authoritative maturity combination, preflight/route
  reporting must remain explicitly experimental. Test both the technical
  declaration and the fail-closed disk validator; the validator must reject
  invalid or unsupported discrete entries before any matrix allocation.
- The first route is serial, linear flexible BEAM2 with rigid axisymmetric
  disks, constant prescribed signed speed, fixed spatial frame, small
  perturbations, no damping, simple homogeneous fixed constraints, and
  positive-definite reduced M. Unsupported combinations reject before
  allocation or solve.

## 7. Refactoring register

No source refactor is approved or necessary in WP02. The inspected extension
points already permit composition: explicit router dispatch; K/M assembly
plus a separate skew contribution; a discrete-mass protocol; a shared DOF
index map; independent result DTO serialization; and separate post-processing.
The one tempting generalization, extracting shell drilling condensation into a
universal reducer, has no demonstrated benefit for the first BEAM2-only scope
and is explicitly deferred.

| `BEFORE` | `AFTER` | `WHY` | `FILES` | `RISK` | `NON_REGRESSION_TESTS` |
|---|---|---|---|---|---|
| Existing architecture and distinct subsystem responsibilities. | Same code; these prospective contracts are frozen for later implementation. | Avoid premature physics and avoid broad refactoring; preserve existing public and numerical behavior. | This WP02 design record and its machine-readable companion only. | Documentation/schema drift if later code fails to implement this contract. | Exact WP01 `PR_REQUIRED` workflows on the WP02 head; no source-level numerical test changes. |

## 8. G01 acceptance record

`QF0211-G01 — ARCHITECTURE FROZEN` passes only when the WP02 head has the
approved contracts above, the complete `PR_REQUIRED` Quality and
Documentation workflows succeed on that exact head, the public API and
existing numerical behavior remain unchanged, and no physics has been
implemented early. A failed or unavailable required job is not PASS. A skip
remains SKIPPED under the WP01 selection policy.

The following are explicitly frozen as decisions; the physical disk G formula,
its sign verification, QEP residual acceptance values, dense-size boundary,
and mode tracking thresholds are not improvised here. They are WP05/WP06
inputs that must be independently derived/characterized and frozen before
their corresponding results are inspected.

### Gate record

| Criterion | Design decision |
|---|---|
| `MODULE_RESPONSIBILITIES_CLEAR` | YES |
| `ROTATION_CONFIG_CONTRACT_CLEAR` | YES |
| `ROTATING_DISK_OWNERSHIP_CLEAR` | YES; one entity owns M, rotor assembler contributes G only |
| `COMPATIBILITY_PREFLIGHT_INTEGRATION_CLEAR` | YES; BEAM2 technical declaration and route-local validation of all discrete entries are both required in WP05; technical support does not promote maturity |
| `ASSEMBLY_EXTENSION_CLEAR` | YES; compose K/M with narrow G assembler |
| `DOF_REDUCTION_CONTRACT_CLEAR` | YES; shared fixed-DOF selection for initial BEAM2; reject unsupported transforms |
| `QEP_INTERFACE_CLEAR` | YES; internal SciPy dense QEP contract, no backend framework |
| `COMPLEX_RESULT_CONTRACT_CLEAR` | YES; separate DTO, explicit real/imag serialization |
| `TRACKING_BOUNDARIES_CLEAR` | YES; solve / tracking / Campbell / plotting responsibilities distinct |
| `PUBLIC_API_PRESERVED` | YES; no public/runtime code changes in WP02 |
| `LEGACY_NON_REGRESSION` | Must be established by the WP01 `PR_REQUIRED` workflows on the exact WP02 head; WP01 exact-baseline CI is recorded separately |
| `NO_PHYSICS_IMPLEMENTED_PREMATURELY` | YES; no solver or formulation code is changed |

## 9. Deferred/out-of-scope register

No WP02 work on: numerical G derivation/implementation; QEP computation;
Campbell tracking; changing the classic modal contract; shell/mixed-family
rotor support; generalized MPC/RBE reduction; damping; variable speed;
stress-stiffening/centrifugal load; rotor-stator contact/rubbing; forced
unbalance response; nonlinear rotor; sparse QEP; PETSc/SLEPc/MPI; general
nonlinear/contact/J2 refactoring; G03 cleanup; WP14 promotion; maturity or
historical result changes; 0.2.10 files, tag, artifacts, or metadata.
