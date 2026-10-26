# WP12 scientific verification and validation master plan

**Status:** PREPARATION_ONLY
**Numerical execution:** NUMERICAL_EXECUTION_NOT_PERFORMED
**WP12:** OPEN
**Plan revision date:** 2026-10-26

## 1. Purpose and decision boundary

This plan structures future evidence for the capabilities actually present in the v0.2.12 scientific candidate. It separates implementation, route declarations, test availability, recorded results, evidence scope, and Owner maturity decisions. It does not change any work-package status, solve a model, authorize a test, or claim that the frozen candidate currently passes a new campaign.

The inspected integration checkout is aba532b6f4bb7b81a17ace3e9631fc2ce99d0b6b with tree 6fea918568d47464bf78b49aaf6b34d6e1584642. The frozen science candidate is 00428adf38e9397340ac136f6f503a268eb671da with tree df4ec667bf746b042c900fad1f86bf542e1a437b. Runner, test, fixture, and environment identities must be recorded separately from the science identity. A report is reusable only inside its original source, model, parameters, environment, and oracle scope.

## 2. Scope model

The plan covers the implemented capabilities and meaningful refusal boundaries in:

- Solid, beam, shell, discrete, and rotating-disk elements; geometric checks; element matrices; stress/result recovery.
- Isotropic, orthotropic, laminate, nonlinear, J2, and source-level experimental material kernels.
- Linear static, modal, linearized buckling, direct Newmark, direct harmonic, prepared dynamic operators, modal basis and damping, reduced harmonic, modal Newmark, and uniform base acceleration.
- Nonlinear static state updates, J2/corotational and total-Lagrangian routes, contact, restart/checkpoints, and experimental finite-strain foundations.
- MPC, RBE2, RBE3 modes, assembly, loads, constraints, reactions, IO, results, public API/CLI, optional backends, and large-model tools.
- Inherited rotating modal / QEP / Campbell behavior, with its historical experimental maturity and explicit scope.
- Verification, convergence, performance, and external comparison facilities, including cases whose tests are not currently authorized or whose historical artifacts cannot be replayed from the integration checkout.

Element registries, compatibility descriptors, material factories, and analysis settings are independent inventories. They do not prove every Cartesian combination of element × material × analysis. Each row in the [matrix](CAPABILITY_TEST_MATRIX.csv) names a bounded capability or states where route-level compatibility remains unresolved.

## 3. Evidence vocabulary

### 3.1 Type of evidence

Use these stable evidence classes:

- **A — Algebraic / invariant:** matrix symmetry, rank, residual, conservation, equilibrium identity, orthogonality, serialization identity, constitutive identity, or refusal behavior.
- **B — Analytical:** comparison against an independently derived closed-form or semi-analytical solution. Record whether the reference is exact, approximate, or asymptotic.
- **C — FEM discretization:** patch behavior, mesh refinement, timestep refinement, mesh sensitivity, or a manufactured-solution study. Report the discretization and the observable.
- **D — Independent numerical implementation:** Code_Aster or another solver, with formulation and observable compatibility established. This is numerical correlation, not physical validation.
- **E — Robustness / refusal:** distorted and limiting cases, invalid inputs, branch transitions, reproducibility, and fail-closed behavior.

Separately classify the claim: equation verification, implementation verification, approximation/discretization study, cross-solver correlation, experimental physical validation, or bounded qualification. These are not synonyms.

### 3.2 Result states

- **TEST_PRESENT:** source contains a test definition; execution is unknown.
- **HISTORICAL_RESULT:** a named report records a result tied to its original identity and scope.
- **CURRENT_CANDIDATE_RESULT:** a recorded run explicitly proves the tested files and runtime correspond to the frozen science candidate. This plan creates none.
- **NOT_RUN:** no execution is claimed for this plan or target campaign.
- **FAIL_PRESERVED:** an existing failure remains in the record and is not averaged away or overwritten.
- **INCONCLUSIVE / NOT_ACQUIRED / NOT_VERIFIED:** use the exact meaning in the normative contract or decision.
- **NOT_APPLICABLE:** a proposed oracle does not fit the method or scope; explain why.

Do not infer a numerical PASS from static source inspection or test presence. Do not total test counts across overlapping campaigns. A report’s status applies only to its bound manifest, node selection, model, source identity, environment, and acceptance criteria.

## 4. Acceptance criteria

Before a future execution, every measured quantity must have a preregistered oracle and criterion. Use the contract’s frozen tolerance when the same quantity, convention, method, and domain apply. Otherwise set **CRITERION_TO_REVIEW** and ask the Owner/scientific reviewer to approve a justification before the run.

Keep separate error budgets for:

1. Reference uncertainty and modelling assumptions.
2. Spatial approximation and stress recovery.
3. Time integration and interpolation.
4. Algebraic solve and eigenpair residual.
5. Nonlinear iteration and constitutive integration.
6. Conditioning, floating-point precision, and result transformation.

Do not relax a threshold after seeing the evaluated result. If no defensible bound exists, the outcome is characterization or INCONCLUSIVE, not PASS. Compare only observables with matching units, frames, sign, phase, constraints, and recovery points. For modes, account for sign/complex phase and compare degenerate subspaces using a contract-defined invariant.

## 5. Scientific gates

### Gate 0 — owner review of the plan

Approve matrix scope, benchmark fiches, criteria, the local execution policy proposal, and the order of work. Resolve conflicts with AGENTS.md before any test command. No execution begins just because this plan is committed.

### Gate 1 — component identities and analytic cases

Start with low-cost algebraic and analytic checks whose oracle can be evaluated independently. Require exact test selection, frozen input and source identities, reproducible environment metadata, and no hidden multi-case sweep.

### Gate 2 — bounded FEM and convergence

Use a small number of representative element families and observables. Confirm the mesh generator, boundary conditions, load resultants, reference regime, and output sampling before solving. Include at least one multi-level spatial study where the claimed feature depends on discretization. Do not use a singular stress maximum as a convergent observable without a fixed finite sampling region or a separate singularity analysis.

### Gate 3 — dynamic and reduced routes

Verify sign, units, frame, phase, initial-state projection, damping interpretation, reaction availability, and time/frequency sampling. Compare direct and reduced routes only when their assumptions are identical, and label such a comparison as internal consistency if both share assembly/operators.

### Gate 4 — advanced bounded domains

Run nonlinear, contact, shell/composite, and rotor cases only under a specific contract and authorized scope. Preserve negative and inconclusive histories. Do not generalize one material point, one contact mesh, one rotor model, or one benchmark family.

### Gate 5 — independent correlations and performance

Use external solver comparisons only after a formulation mapping and output extraction audit. Performance work records machine, environment, model size, solver, resources, warm-up/repetition method, and raw observations. Existing one-off timing is not a scaling law.

## 6. Traceability record for each future case

Store a non-overwriting campaign folder with:

- Case/campaign ID; scientific commit/tree; runner/test repository identity; clean/dirty status.
- Exact command and nodeid; parameters; test file and fixture hashes; model/mesh generator identity.
- Python executable, environment, package origins, NumPy/SciPy/native library versions, thread variables, OS/architecture, backend and solver options.
- Inputs, units, frames, constraints, boundary/load resultants, output selection, and random seeds if any.
- Frozen contract and oracle; criterion source and version; raw output; parsed measures; logs and process exit status.
- Verdict per criterion; overall PASS/FAIL/INCONCLUSIVE/NOT_RUN; explanations and limitations.
- SHA-256 of the full evidence bundle and a read-only archival copy. Never replace a failed run.

The version/detail of Windows is diagnostic metadata, not a scientific acceptance criterion by itself. This local record is deliberately independent of the historical signed WP12 runner and does not claim cryptographic attestation.

## 7. First local campaign proposal

See the detailed six-case proposal in [BENCHMARK_CATALOG.md](BENCHMARK_CATALOG.md). Recommended ordering:

1. Structured symmetric projection identity, using its existing exact test nodeid and the dense bilinear form as the algebraic oracle.
2. A discrete spring-mass modal frequency with the closed-form eigenfrequency. This invokes a solver route; it is not a purely algebraic test.
3. A coupled 2-DOF modal case. The existing test uses SciPy `eigh` to form its expected eigenvalues while the production route also uses SciPy `eigh`; treat it as same-backend consistency unless an independently derived scalar characteristic-polynomial oracle is added and reviewed.
4. An undamped SDOF transient oracle for modal Newmark. This invokes the Newmark route and compares against the test's closed-form solution.
5. A single static analytic BEAM2 case, only after the parameter suffix and observable are resolved through an approved static workflow. The existing test is parameterized and is not yet an exact executable nodeid.
6. One representative multi-mesh static FEM study using `run_structured_tet4_study`, only after a small nested plan and a new output directory are approved. Do not mistake `test_timoshenko_reference_and_convergence_metrics` for an FEM convergence run.

Exact nodeids for cases 1–4 are recorded in the catalog. Cases 2–4 execute analysis routes; case 1 is an algebraic projection check. The beam cantilever test has parameter IDs that must be resolved before it can enter an exact-node manifest. Case 6 has an existing public API utility and an illustrative, explicitly bounded call, but its output root, nested levels, implementation defaults and acceptance interpretation require Owner approval. All proposed commands remain forbidden until the Owner approves the separate local policy and an exact per-run scope.

## 8. Status preservation

This plan neither changes the [roadmap](../ROADMAP.md) nor reopens WP11. It preserves WP-C01’s negative verdict, WP-C02’s AR/N03 boundary, WP-D01’s inconclusive state, WP-D02’s bounded closure, WP-E01’s open bounded-certificate disposition, experimental rotor maturity, and WP12/WP13 OPEN. See [historical evidence crosswalk](HISTORICAL_EVIDENCE_CROSSWALK.md).

## 9. Explicit exclusions

No V&V test, test collection, solver, FEM, benchmark, Code_Aster, Docker, or runner execution was performed for this plan. No source, test, manifest, evidence archive, runner protection, tolerance, maturity, or work-package status was modified.
