# WP08-R1 implementation plan for R2/R3

**Planning status:** design only. WP08 remains blocked; no R2/R3 work is authorized by this record.

## Dependency order

    R2A: explicit formulation/state identity
      -> R2B: reference-frame state and objective Biot-strain update
      -> R2C: exact polar-adjoint P and force assembly
      -> R2D: independent local/element physical checks
      -> R3A: consistent algorithmic tangent of corrected force
      -> R3B: semantic result fields and aggregations
      -> R3C: checkpoint/result migration and fail-closed restart
      -> R3D: full targeted V&V, regression, evidence and WP08 gate review

The tangent and output migrations must not precede the frozen force/state semantics. WP09 general finite-difference robustness remains separate; WP10 general checkpoint/restart remains separate, while corrected-formulation state schema and its specific resume rejection are necessary dependencies in R3.

## Concrete file/change plan

| File | Current responsibility | R2/R3 change | Contract/equation | Main risk | Required evidence |
|---|---|---|---|---|---|
| src/solveur/elements/solid/corotational_j2.py | Polar kinematics, state rotation, local return, P=R T, element force, central-difference tangent, IP results | Keep one element family/kernel; add an explicit formulation strategy or shared helper selecting legacy v1 versus corrected Biot v1. For corrected: no state transport by R; compute exact polar-adjoint P; assemble its force; expose corrected trial state. R3 supplies the consistent corrected tangent and versioned IP payload. Keep legacy path callable with old semantics. | E_B=U-I; T_B conjugate; P=R L_U*[T_B]; force integral; state contract v2 | Highest: force and plastic history both change, Newton response changes | A02-A10, A12-A15; old route regression |
| src/solveur/materials/solid.py | Isotropic J2 radial return, state variables, local algorithmic tangent and legacy plastic-work accumulator | Reuse the same radial return. Add only an explicit opt-in state/response contract seam if the element adapter cannot keep corrected state semantics without mutating TL behavior. Do not globally change Total-Lagrangian J2. Make dissipation versus plastic work explicit for corrected state. | Tensor return equations in formulation record; D_p += sigma_y*delta_alpha; hardening storage H alpha^2/2 | Accidental cross-route state/output changes; shear-Voigt mismatch | Independent material-point oracle, A08-A09, TL regression |
| src/solveur/core/assembly/nonlinear.py | Selects element formulation from nonlinear analysis parameters | Resolve and validate explicit formulation ID; absent old field maps only to legacy ID; unknown ID fails closed. Instantiate shared element implementation in the selected mode. | legacy_corotational_j2/v1 vs corrected_corotational_biot_j2/v1 | Default/API behavior changes; cache or element-state mismatch | Input validation, identity, both formulation route tests, existing assembly tests |
| src/solveur/core/nonlinear/solver.py | Validates nonlinear kinematics and invokes nonlinear assembly/solve | Carry formulation identity through analysis, provenance, accepted state and checkpoint calls; do not change Newton/line-search defaults. | formulation ID part of execution/state identity | Solver-wide behavior or historical defaults drift | Legacy run regression; corrected Newton and state transaction tests |
| src/solveur/core/nonlinear/contracts.py and src/solveur/core/nonlinear/material_state.py | Constitutive response adapter and material-state ownership/copy semantics | Change only if needed to make trial state detached, versioned, and accepted-state safe. Avoid introducing a general constitutive framework. | trial from accepted, commit once, rollback discards | State aliasing or changed behavior for all materials | A09, A14, existing nonlinear state tests |
| src/solveur/post/stress.py | Recomputes IP state and aggregates local stresses/principal/von Mises and output fields | R3 only: branch by explicit formulation ID; corrected result carries all measure/frame/version metadata; generic corrected stress/principal/von Mises use Cauchy; never average unlike measures/frames. Preserve legacy serializer path. | result semantics corotational_stress/v2 | Consumers misinterpret changed generic stress; inconsistent recomputation state | A04-A05, output/aggregation tests, old result compatibility |
| src/solveur/post/solid_results.py | Solid result field shaping/availability | R3 only if the actual corrected IP fields traverse this layer; add explicit availability/reason and semantic metadata without changing unrelated element outputs. | WP01 availability values and v2 stress contract | Broad result schema changes | Corrected/legacy serialization round trips and unavailable-field refusal |
| src/solveur/core/results.py, src/solveur/core/result_serialization.py | Result containers and JSON-compatible serialization | R3 only if required by existing result path; preserve old JSON read; serialize new formulation/stress semantic versions and identities without embedding new solver objects. | historical semantics distinct from corrected semantics | Schema drift and silent reinterpretation | Legacy reading and v2 round trip; unknown versions fail closed where required |
| src/solveur/io/csv_writer.py, src/solveur/io/vtu_writer.py | Flatten and export result fields | R3: emit explicit metadata/field names where format permits; do not export absent or invalid transformed stresses; keep generic stress consistent with declared corrected Cauchy field. | per-field measure/frame/availability | Loss of metadata in flat formats; incorrect field name | CSV/VTU fixtures for corrected and legacy; no invalid output |
| src/solveur/io/nonlinear_checkpoint.py, src/solveur/core/nonlinear/checkpoint.py | Persist/validate nonlinear accepted state | R3: bind formulation and state schema to checkpoint identity; corrected resumes only exact compatible identity; old/unknown checkpoints remain readable where possible but are not resumable as corrected. Do not rewrite checkpoints. | WP01 checkpoint policy; state v2 | Unsafe state migration or restart under different force law | A14, corruption/mutation rejection, legacy read-only behavior |
| src/solveur/core/assembly/geometric.py, src/solveur/core/analyses/geometric_nonlinear.py | Separate Total-Lagrangian/geometric consumer of PK2 stress | No change is planned. Change only if a direct dependency on the corotational producer is demonstrated; otherwise test and preserve. | Route-specific producer/consumer separation | Incorrectly broadening rescope into TL route | Existing TL/geometric regression and consumer audit |
| tests/unit/test_corotational_j2.py | Legacy corotational tests, including old state-transport expectation | Preserve legacy assertions; add explicit corrected-formulation tests rather than rewriting expected legacy behavior. | formulation-selective compatibility | Hiding legacy change by rewriting tests | Legacy snapshot plus corrected A02/A03/A09/A12 |
| New focused WP08 tests under tests/unit/ | No implementation tests yet | Add independent polar-adjoint, Biot-work, force, tangent, state and migration tests in R2/R3. Name by corrected formulation; no blanket changes to unrelated NL tests. | Acceptance matrix R1-A01..A15 | Oracle shares production helpers | Independent formulas/reference, mutation checks, all required families |
| qualification/0_2_12/ | WP records and contracts | R2/R3 add versioned implementation evidence/report/contract records; do not edit prior WP08 or audit records in place. | evidence linked to exact source/test hashes | Historical evidence overwritten or gate prematurely passed | Diff confirms additive records; gate review exact SHA |

Paths are the repository paths at the R1 baseline. If an implementation discovers that a listed module is not on the actual data path, prove that by a consumer trace before adding a different file. Do not widen scope on the basis of filenames alone.

## WP08-R2 — state, kinematics, transformations, corrected force, first proofs

R2 scope:

1. Introduce explicit formulation ID dispatch while retaining legacy v1 behavior and defaults.
2. Define corrected v2 state in the fixed reference/material frame; no R_current^T R_old state rotation.
3. Reuse the existing local J2 radial-return algorithm on E_B=U-I; verify engineering-Voigt work equivalence.
4. Implement the exact polar differential/adjoint and corrected P; update corrected internal force only.
5. Add first independent material-point/element checks: pure spatial spin after plastic preload, rotation covariance, polar adjoint identity, tensor transformations, Cauchy/PK2 symmetry, and nodal force versus incremental-potential gradient.
6. Do not claim global tangent completion, result migration completion, WP08 PASS, or qualification. Return R2 evidence for an Owner/design review if results violate a frozen criterion.

R2 must stop if the local response is not the derivative/conjugate of the stated incremental J2 update, objectivity fails, the exact-force potential comparison does not converge, or a multiplicative/general finite-strain law is required.

## WP08-R3 — tangent, stress outputs, serialization, migration, full targeted V&V

R3 begins only after R2 results are reviewed/authorized:

1. Implement the corrected algorithmic tangent for the corrected force, or stop if a compatible tangent cannot be constructed without an unauthorized global Newton redesign. Keep raw tangent diagnostics; no blind symmetrization.
2. Version the corrected stress result fields and aggregates. Test the actual producer-to-postprocessor-to-JSON/CSV/VTU paths. Preserve old output semantics and mark historical ambiguity.
3. Bind state/checkpoints/results to the formulation/schema identity. Refuse cross-formulation resume and incomplete historical identity. No automatic migration or rewriting.
4. Run the complete preregistered acceptance matrix, element-family checks, relevant historical regressions, serializers/exports, and targeted Newton/restart tests. Record PASS/FAIL/SKIPPED/NOT_RUN and exact commands/SHA.
5. Only after evidence review may a separate Owner-authorized WP08 gate decision be made. Numerical PASS does not qualify or promote maturity.

## Dependency and authorization boundary

R1 is design-only and commits only its documents. R2 is not authorized by the R1 approval. R3 is dependent on R2 and also not authorized. WP09 remains unauthorized. The corrected force derivative is required for R3 correctness, but no generic WP09 tangent robustness work is started here. WP10's generic checkpoint integrity work can be separately considered later; corrected formulation migration/restart is not safe until this state and force identity is implemented and tested.
