# WP-E01 — Nonlinear Calculation Foundations

**Document status:** Revised technical contract candidate for Owner review.
**Package status:** OPEN / EXPERIMENTAL_TARGET; not qualified.
**Authorization:** Documentation and source review only. No implementation, test execution, numerical V&V, native FEM, solver execution, qualification promotion, or release action was performed or authorized by this document.

## 1. Provenance, baseline, and evidence labels

This document revises the recovered candidate whose original source was branch codex/wp-e01, commit f5b894938c0b8350f32e2577ba847d160d0dec55, file qualification/0_2_12/wp_e01_nonlinear_foundations_candidate.md, SHA-256 B0C46C92251833F38C4D91F18B4595D648008774D090DB5F0F12661C7598BCB0. The recovered documentary branch was reconciled in codex/qf-wp-e01-recovery-review-20261020 and rebased onto the verified canonical baseline before this revision. The original candidate and its provenance are retained in Git history.

**Verified repository baseline:** canonical checkout C:\wpc01-frictionless-public-integration, branch emptiesvoids-cloud/wp-c01-contact-aware-equilibrium-audit, HEAD 3c0e0492104375fa01ce271896ca3e91c2cc53db, clean at inspection. The mandatory entry point qualification/0_2_12/ROADMAP.md and the Owner-provided roadmap were present. The Owner roadmap places WP-E01 in OPEN / EXPERIMENTAL_TARGET; WP08, WP09, and WP10 are bounded closures, not general nonlinear qualification.

**Verified E01 worktree:** C:\wpc01-frictionless-public-integration-wt\wp-e01, branch codex/qf-wp-e01-recovery-review-20261020, rebased onto canonical HEAD 3c0e0492104375fa01ce271896ca3e91c2cc53db before this revision. Only this E01 candidate document is in scope for changes.

Evidence labels used below:

- **VERIFIED — source:** directly observed in source during read-only inspection. This is not a claim that the source behavior was executed or independently validated in this task.
- **VERIFIED — bounded record:** an existing versioned report records the stated result for its own route, fixture, metric, and threshold. It does not transfer qualification to E01.
- **PROPOSED:** a contract or acceptance rule for Owner decision; it is not implemented or approved.
- **BLOCKED:** absent, unverified, or dependent on a decision/evidence gate.

### E01 scope

The Owner-approved A–E scope is:

- **E01-A:** incremental Newton–Raphson, convergence controls, load stepping, line search/cutback, and transactional states.
- **E01-B:** small-strain J2 plasticity with von Mises yielding, radial return, perfect plasticity and linear isotropic hardening, including loading, unloading, reloading, dissipation, and algorithmic tangent evidence.
- **E01-C:** Total Lagrangian finite elastic deformation using F, Green–Lagrange strain, Piola stresses, material/geometric tangents, StVK and a bounded Neo-Hookean model.
- **E01-D:** independent constitutive, element, and multi-increment V&V, including tangents, objectivity, mesh sensitivity, and controlled failure.
- **E01-E:** experimental TET4/HEX8 integration, result/API/state contracts, diagnostics, and explicit support limits.

Out of scope are multiplicative finite-strain J2 plasticity F=FeFp, general nonlinear dynamics, unsupported frictional-contact coupling, general postbuckling qualification, automatic promotion of high-order elements, and unrelated refactoring.

## 2. Existing implementation and reuse matrix

| Area | Observed implementation | Evidence boundary / gap | E01 reuse recommendation |
| --- | --- | --- | --- |
| Newton driver and linear correction | src/solveur/core/nonlinear/iteration.py routes full Newton through UnifiedNewtonEngine; the driver records residual and correction histories and uses the configured residual tolerance. | The existence of convergence on bounded paths is not a general convergence guarantee. A universal independent correction-norm gate is not established. | Reuse the driver, residual plumbing, typed failures, and bounded line-search route. Freeze the exact norm, scaling, and tolerance for each E01 target before execution. |
| Adaptive load control | src/solveur/core/nonlinear/load_control.py uses a continuation controller and adaptive step policy. Failed attempts can be rolled back, classified, cut back, and retried. Rejection history and terminal minimum-step / cutback conditions are represented. | Existing rules and thresholds are route-specific. They do not prove convergence for every constitutive law or mesh. | Reuse with explicit E01 load-control configuration and retain rejection diagnostics. Do not silently change retry policy or accept a failed attempt. |
| Transactional nonlinear state | src/solveur/core/nonlinear/state.py::NonlinearStateTransaction detaches accepted/trial states, checks accepted-state integrity, validates a detached replacement before commit, and rolls back trial state. Checkpoint and restart contracts exist under WP10. | Bounded software evidence is not a proof of every material/continuation/checkpoint combination. | Reuse the composite transaction. Bind persisted state to formulation, material, mesh/integration identity, load state, and schema; fail closed on invalid or incompatible state. |
| Small-strain J2 material | src/solveur/materials/solid.py::VonMisesElastoplasticMaterial.stress_tangent_state implements a 3D radial-return update with accumulated equivalent plastic strain, plastic strain, stress, and plastic dissipation state. It has perfect plasticity at H=0 and linear isotropic hardening for H>0. | The current algorithmic tangent is assembled through basis variations and symmetrized. That construction is not independent evidence that it equals the derivative of the branch-specific return map. | Reuse the local constitutive update only after independent branch-aware tangent evidence; do not promote tangent consistency now. |
| Corrected corotational J2 route | WP08-R3 records a corrected, explicitly selected experimental path with fixed-state force/tangent probes and bounded smooth-branch and one-sided yield evidence. | Its evidence is bounded and route-specific. It does not qualify all J2 material use or all E01 element combinations. | Use as implementation evidence and a source of state/diagnostic patterns only. Keep its existing route restrictions. |
| Historical corotational output | qualification/0_2_12/wp08_nonlinear_stress_measures_contract.json records BLOCKED_RESCOPE_REQUIRED for the historical producer: its legacy second_piola_stress payload is not generally PK2 under the recorded force construction. | This is a physical measure/force consistency issue, not a naming-only issue. It does not identify the distinct TL StVK producer as the same route. | Do not use legacy corotational stress payloads as an oracle or claim their measures are validated. Any rescope is an Owner decision outside this document. |
| TL StVK | TotalLagrangianTet4Kernel, TET4 and HEX8 assembly routes implement F, E, StVK S, P=FS, reference-volume force integration, material/geometric tangent contributions, and stress/energy output. The TET4 kernel rejects det F <= 1e-10; HEX8 uses eight 2x2x2 Gauss points. | These are implementation facts, not a global E01 qualification. The observed determinant guard is a code limit, not a physically justified universal J_min. Some result paths provide element-volume-weighted averages; location and averaging need explicit output contracts. | Reuse the bounded StVK TET4/HEX8 paths as initial experimental targets after parameter/domain decisions and independent element/tangent verification. Preserve integration-point values as the primary local result. |
| TL J2 | TotalLagrangianJ2Element exists and applies the available J2 law to a Green–Lagrange strain route. | It is not multiplicative F=FeFp, and its existence does not establish a general finite-strain plasticity model. | Keep separate from E01-B small-strain J2 and do not use it to claim multiplicative finite-strain plasticity. |
| Neo-Hookean | No Neo-Hookean constitutive law was found in the inspected src/solveur sources. | BLOCKED / missing in inspected scope. No support, tangent, element assembly, result serialization, or V&V is established. | Treat the model below as a proposal only. Implement and verify it as a separate constitutive route after Owner selection. |
| TET4/HEX8 and public result plumbing | TET4 constant-gradient and HEX8 2x2x2 element infrastructure, nonlinear response contracts, integration-point output, and WP08 result-schema records exist. | Existing APIs and output paths do not establish complete, uniform measure/frame/unit/location metadata for every E01 field. Mixed families, materials, contact, and all formulations are not thereby supported. | Keep an explicit opt-in experimental route, publish only fields from the accepted state, and fail closed for unsupported combinations. |
| Prior V&V | WP08–WP10 contain material, tangent, route, transaction, restart, and element checks. Their records use bounded scopes and explicitly do not imply general qualification. | No test or V&V was run in this task. Existing numeric gates are not automatically transferable. | Treat prior results as evidence for exact matching claims only. Preregister independent E01 references and gates. |

## 3. WP-E01-A — incremental Newton–Raphson and state contract

### 3.1 Equilibrium and convergence

**PROPOSED mathematical convention.** At load parameter lambda, define equilibrium by

\[
R(u,z;\lambda)=f_{\mathrm{ext}}(\lambda)-f_{\mathrm{int}}(u,z)=0,
\]

where u is the free displacement vector and z is the accepted constitutive/continuation state. The linearized correction solves \(K_T\Delta u=R\) under the implementation's corresponding sign convention. The public contract must state the sign convention even though residual norms are sign-invariant.

**VERIFIED current acceptance behavior.** The driver forms the target load `f_target = λ f_ext` and free-DOF residual `R_f = (f_target - f_int)_f`. It uses the Euclidean norm `||R_f||₂`, divided by

\[
S_F=\max(\|f_{target,f}\|_2,\;F_{scale},\;1.0),
\]

where `F_scale` is the supplied force scale or zero. The `1.0` value is in the caller's force units, so the current policy is unit-dependent below that floor. The configured/default tolerance (common default `1e-8`, dimensionless) is applied to `||R_f||₂ / S_F`. The driver accepts the residual criterion before solving a further Newton correction; correction telemetry of zero on this path is a sentinel, not a solved correction. Nonfinite residuals fail with a typed error. This is the actual source behavior, not a general scientific endorsement.

**PROPOSED dimensionally explicit E01 criterion.** Define positive, run-fixed, serialized reference force `F_ref` [force units], a physical absolute residual tolerance `F_abs >= 0` [force units], and a dimensionless relative tolerance `τ_R`:

\[
\|R_f\|_2 \le F_{abs}+\tau_R\max(\|f_{target,f}\|_2,F_{ref}).
\]

This remains a proposed alternative to the implementation's unit floor. The existing default `1e-8` is a compatibility starting point for `τ_R`, not an approved or universally justified value. No value is selected here for `F_ref` or `F_abs`; those need a declared characteristic load and allowable force imbalance for each application. At zero/near-zero applied load, `F_ref > 0` keeps normalization finite. A hard-coded one-unit floor is not scale invariant.

Define the free-DOF correction diagnostic `||Δu_f||₂` [length units] and normalized diagnostic

\[
\eta_u=\frac{\|\Delta u_f\|_2}{\max(\|u_f\|_2,U_{ref})},
\]

where `U_ref > 0` [length units] is a declared characteristic displacement, fixed for the run. An optional absolute correction threshold `U_abs` also has length units. If `U_ref` is absent, report the absolute correction and mark `η_u` unavailable; do not substitute an arbitrary machine-tiny floor. The correction is a diagnostic for progress/stagnation, not a mandatory primary equilibrium gate: a small correction alone can accompany a poor tangent or stagnation, while a sufficiently small force residual is the equilibrium condition. Requiring a second correction gate would change current solver behavior and needs an Owner decision.

The current stagnation policy is a failure diagnostic: over four residual samples it flags a plateau when the final residual has not fallen by the configured relative plateau threshold (default \(10^{-10}\)); it does not declare convergence. An experimental floor-aware termination exists only when explicitly enabled and reached after line-search failure with an evidence callback. Its conjunction includes a normalized residual below an estimated state-resolution threshold, a four-sample residual-history spread below that threshold, normalized correction no greater than `max(8 ε_machine, 4 × component-ULP displacement ratio)`, linear backward error at most `1e-10`, no accepted line-search improvement, valid-state evidence, and force and moment equilibrium measures each at most `1e-8`. These are dimensionless route-specific gates, not the ordinary acceptance rule. The special correction ratio uses `||Δu_f||₂ / max(||u_f||₂, displacement_scale, machine_tiny)`; this is not the proposed E01 physical `U_ref` normalization. Nonfinite residuals or corrections fail, and max-iteration or stagnation outcomes remain failures. A successful increment also requires valid accepted-state data and completion at the declared load target; convergence of one substep alone does not establish completion of the full load path.

All accepted outputs (displacement, load factor, material state, residual, iteration data, and derived fields) must come from the same finalized trial. A failed linear solve, constitutive error, nonfinite value, exhausted iteration limit, failed line search, terminal cutback, or commit/checkpoint validation failure is not convergence.

### 3.2 Load steps, line search, cutback

**PROPOSED contract:**

1. Start an increment from the last accepted composite state and target a declared load parameter.
2. Full Newton reassembles the residual and consistent tangent for the current trial. A line-search candidate evaluates the same accepted internal state and may be accepted only under the selected merit/acceptance rule.
3. A rejected line-search candidate is discarded; it does not update material history.
4. A load increment rejected by a retryable failure is rolled back to the last accepted composite state. The adaptive policy may reduce the increment and retry; it records the failure reason, base and rejected load factors, retry increment, and retry count.
5. A terminal minimum increment, exhausted cutback budget, or any non-retryable constitutive/linear-solver failure returns a typed failure. It does not produce a converged result for the rejected increment.
6. The policy for accepting an increment, minimum step, maximum retries, line-search merit function, and whether line search is required for each E01 route must be configured before execution.

**PROPOSED initial E01 profile, pending Owner approval:** at most 25 correction iterations per attempted increment. The candidate line-search merit is `m(u) = ||R_f(u)||₂`; backtracking starts at `α = 1`, halves alpha, and accepts only when `m(u + α Δu) <= (1 - c α) m(u)`, with proposed `c = 1e-4`, `α_min = 1e-4`, and at most 12 reductions. Invalid/nonfinite assembly has infinite merit; exhaustion is `LINE_SEARCH_FAILURE`, with no least-bad acceptance. The shared controller's no-experimental-options path currently uses `α_min=1e-4`, at most 12 reductions, and strict residual decrease (`armijo_c=None`); its experimental `existing` profile uses `α_min=0` and 14 reductions. An explicit Armijo profile is a new E01 selection, not the universal current default. All values remain proposals.

The common adaptive-control defaults are \(\Delta\lambda_0=1/N_{load}\), \(\Delta\lambda_{min}=\min(10^{-4},\Delta\lambda_0)\), \(\Delta\lambda_{max}=\max(\Delta\lambda_0,1/N_{load})\), cutback 0.5, growth 1.5, maximum 25 rejected attempts, and (for 25 Newton iterations) grow/shrink thresholds 6/12. These are existing configurable controls, not a universally approved E01 policy. The candidate profile proposes growing after an accepted increment at or below 6 iterations, shrinking at or above 12, otherwise holding; retrying only after rollback to the exact accepted state and only for a failure classified `RETRYABLE`, or `OWNER_POLICY_DEPENDENT` under an explicitly selected Owner policy; and terminating after the Nth rejected attempt or when the reduced increment would be below minimum. Equality with the minimum is permitted by the current policy. Fixed stepping remains an explicit alternative.

The adaptive controller clips each proposed increment to the remaining distance to target load factor 1.0; the driver loop uses a `1e-12` endpoint guard. This implementation detail does not itself define an approved endpoint tolerance. The public run-success contract should require an explicit final load factor and target discrepancy within a dimensionless `τ_λ`, with its value approved for the route. A terminal cutback, retry exhaustion, minimum-step failure, or nonretryable failure must not report the requested target as attained.

### 3.3 Transaction, commit, rollback, persistence

Let \(z_n\) be the accepted state and \(z^{trial}\) the candidate state. Material evaluation is a pure trial update in the sense that it cannot mutate \(z_n\). Every Newton and line-search candidate for the same increment starts from \(z_n\), not from a previously rejected candidate. After global equilibrium and result validation, prepare and validate the complete replacement \((u_{n+1},z_{n+1},\lambda_{n+1},m_{n+1})\), then atomically commit it. If any preparation, validation, serialization, or commit step fails, preserve the old accepted state and report failure.

Rollback discards the complete trial, including all integration-point variables, accumulated plastic strain, plastic strain tensor, dissipation, continuation metadata, and any future stateful contributions. Restart must restore the same accepted increment and reject corrupted, mismatched, unknown, or trial-marked checkpoint state.

Persisted state identity should include formulation/model identifier, material identifier and parameters with units, mesh/connectivity identity, element family, integration rule and point ordering, state schema/version, accepted load state, and an integrity digest. Migration between legacy and corrected formulations is not automatic.

### 3.4 Diagnostics

Expose status and typed failure reason, attempted and accepted load factors, increment size, Newton iteration count, residual norm/scale/history, correction history, line-search reductions/factors, cutback history, linear-solver diagnostics, constitutive failure location, state digest/commit count, and checkpoint outcome. Do not reduce all failures to converged=false without preserving the failure classification.

**Existing bounded evidence:** WP10 preserves distinctions including CONVERGED, MAX_ITERATIONS, LINEAR_SOLVER_FAILURE, CONSTITUTIVE_FAILURE, CUTBACK_REQUIRED, and checkpoint incompatibility/corruption. The existing report says these software checks do not prove general nonlinear convergence or a semi-smooth Newton theorem.

### 3.5 Transaction and checkpoint acceptance invariant

For every rejected Newton candidate or load increment, the digest of the complete accepted composite state before and after rejection must be identical. A successful increment has exactly one atomic replacement of displacement, load identity, every integration-point state, and accepted diagnostics. A checkpoint contains only that accepted replacement, its model/material/mesh/integration/schema identity, and an integrity digest; a trial-marked, corrupt, missing-point, or incompatible checkpoint is refused before result fields are exposed. WP10 records bounded accepted-checkpoint restart equivalence and schema/identity refusal; they do not establish universal bitwise serialized equality. Require exact digest preservation for in-memory rollback, and verify restart against the accepted checkpoint's logical state and identity. Bitwise restart equality is a separate serialization property, not a general nonlinear-state invariant.

## 4. WP-E01-B — small-strain J2 contract

### 4.1 Kinematics and yield surface

**PROPOSED constitutive contract, consistent with the observed implementation:** use infinitesimal strain in a fixed material/reference basis:

\[
\varepsilon = \varepsilon^e+\varepsilon^p,\qquad
\sigma_{trial}=\mathsf C:(\varepsilon_{n+1}-\varepsilon^p_n),\qquad
\sigma = \mathsf C:(\varepsilon-\varepsilon^p),\qquad
s=\operatorname{dev}(\sigma),\qquad
q=\sqrt{\frac32\,s:s}.
\]

Let alpha be accumulated equivalent plastic strain, initial yield stress sigma_y0 > 0, and linear isotropic hardening modulus H >= 0. The yield function is

\[
f=q-(\sigma_{y0}+H\alpha)\le0.
\]

The associative flow increment is

\[
\Delta\varepsilon^p = \Delta\gamma\,\frac{3}{2}\frac{s_{trial}}{q_{trial}},\qquad
\Delta\alpha=\Delta\gamma\ge0.
\]

Use a small-strain isotropic elastic tensor with mu > 0 and positive bulk modulus. H=0 is perfect plasticity; H>0 is linear isotropic hardening. Kinematic hardening is excluded.

### 4.2 Radial return and active-set branches

For trial stress s_trial=dev(sigma_trial), define q_trial=sqrt(3 s_trial:s_trial/2) and

\[
f_{trial}=q_{trial}-(\sigma_{y0}+H\alpha_n).
\]

If f_trial <= 0, accept the elastic predictor and leave epsilon_p, alpha unchanged. If f_trial > 0, for q_trial > 0,

\[
\Delta\gamma=\frac{f_{trial}}{3\mu+H},\qquad
q_{n+1}=q_{trial}-3\mu\Delta\gamma=\sigma_{y0}+H(\alpha_n+\Delta\gamma),
\]

\[
s_{n+1}=\frac{q_{n+1}}{q_{trial}}s_{trial},\qquad
\varepsilon^p_{n+1}=\varepsilon^p_n+\frac32\Delta\gamma\frac{s_{trial}}{q_{trial}},
\qquad \alpha_{n+1}=\alpha_n+\Delta\gamma.
\]

The hydrostatic trial stress is unchanged, so \(\sigma_{n+1}=\tfrac13\operatorname{tr}(\sigma_{trial})I+s_{n+1}\). The zero-q_trial case must not divide by zero and cannot activate plastic flow from a hydrostatic predictor. At accepted increments, alpha is nondecreasing and the plastic strain increment is symmetric and deviatoric. Unloading follows the elastic branch until yield is reached again; reloading/reversal is handled by the same isotropic yield surface and does not imply kinematic hardening.

### 4.3 Tangent, Voigt mapping, and dissipation

The algorithmic tangent contract is

\[
\mathsf C_{alg}=\left.\frac{\partial\sigma_{n+1}}{\partial\varepsilon_{n+1}}\right|_{z_n,\;\mathrm{fixed\ active\ branch}}.
\]

It must differentiate the actual return-map update with the incoming state held fixed. The classical derivative is not asserted at the yield switch. Verify elastic and active plastic branches separately; near yield, use one-sided perturbations that remain on their designated branches and mark cross-branch central differences as nondifferentiable diagnostics.

**VERIFIED ordering:** existing helpers use symmetric Voigt order [xx,yy,zz,xy,yz,xz]; strain shear entries are engineering shear gamma_ij=2 epsilon_ij, while stress shear entries are tensorial tau_ij=sigma_ij. The mapping is part of the public contract; “Voigt” alone is insufficient metadata. The stress/tangent is a small-strain Cauchy-stress response expressed in the declared fixed material/reference axes. Do not claim finite-rotation objectivity for this infinitesimal-strain law.

For the independent material-energy reference, use elastic free-energy density and isotropic hardening storage

\[
\psi(\varepsilon,\varepsilon^p,\alpha)
=\frac12(\varepsilon-\varepsilon^p):\mathsf C:(\varepsilon-\varepsilon^p)
+\frac12H\alpha^2.
\]

This is energy per unit volume in the declared coherent unit system. For isotropic hardening energy \(\psi_h=\frac12H\alpha^2\), associative flow gives \(d\alpha=d\gamma\) and \(\sigma_{eq}=\sigma_{y0}+H\alpha\). The thermodynamic rate-independent dissipation along the constitutive path is therefore

\[
\Delta\mathcal D
=\int_{\alpha_n}^{\alpha_{n+1}}(\sigma_{y0}+H\alpha)\,d\alpha
-\left[\frac12H\alpha_{n+1}^2-\frac12H\alpha_n^2\right]
=\sigma_{y0}\Delta\alpha=\sigma_{y0}\Delta\gamma\ge0.
\]

The plastic-work increment \(\Delta W_p=\int\sigma:d\varepsilon^p\) includes the hardening-energy change, so \(\Delta\mathcal D=\Delta W_p-\Delta\psi_h\). For proportional fixed-direction return, the code's trapezoidal endpoint stress-work increment can equal \(\Delta W_p\), not \(\Delta\mathcal D\); for general noncoaxial increments its physical interpretation has not been independently established. The inspected small-strain routine accumulates \(\tfrac12(\sigma_n+\sigma_{n+1}):\Delta\varepsilon^p\), with engineering-strain Voigt shear entries work-conjugate to tensorial stress shear entries. Do not rename, relabel, or compare this existing field to \(\Delta\mathcal D\) as though they were identical. WP08's separate corrected-corotational Biot-J2 contract defines a route-specific increment as `sigma_y * delta_gamma` and separate hardening storage; its stress measure/kinematics differ, so that record is not proof of this small-strain output's semantics. Owner approval and independent path-based evidence are required before changing or assigning physical dissipation semantics to the existing field.

**BLOCKED:** source inspection found a basis-response tangent followed by symmetrization. No independent branch-aware derivative verification was run here. Do not call J2 tangent consistency established until that evidence passes.

For an isotropic elastic tensor with bulk modulus \(K_b=\lambda+2\mu/3\), define the deviatoric fourth-order projector \(\mathbb P_{dev}\) and, on the smooth plastic branch, \(\beta=q_{n+1}/q_{trial}\), \(D=3\mu+H\), and \(\mathbf n=3\mathbf s_{trial}/(2q_{trial})\). A closed-form candidate derivative is

\[
\mathbb C_{alg}=K_b I\otimes I+2\mu\beta\,\mathbb P_{dev}
+\frac{4\mu}{3}\left(\frac{H}{D}-\beta\right)\mathbf n\otimes\mathbf n.
\]

Here \(\mathbf n:\mathbf n=3/2\) and \(\mathbb P_{dev}=\mathbb I_s-\frac13\mathbf I\otimes\mathbf I\), with \(\mathbb I_{s,ijkl}=\frac12(\delta_{ik}\delta_{jl}+\delta_{il}\delta_{jk})\). It gives a radial deviatoric eigenvalue \(2\mu H/D\), zero for perfect plasticity, and transverse deviatoric eigenvalue \(2\mu\beta\). On the elastic branch \(\mathbb C_{alg}=K_b\mathbf I\otimes\mathbf I+2\mu\mathbb P_{dev}\). These formulae are candidate mathematics, not evidence about the current assembled matrix. The elastic/plastic switching surface has no single classical derivative; preregister branch-preserving central differences away from it and one-sided differences at it. Compare the unsymmetrized production tangent before any symmetrization, in tensor form and under the stated engineering-strain/tensorial-stress Voigt mapping.

## 5. WP-E01-C — Total Lagrangian finite elastic contract

### 5.1 Kinematics, stress measures, and tangents

For reference coordinates X and displacement u(X), define

\[
F=I+\nabla_Xu,\qquad C=F^TF,\qquad E=\frac12(C-I),\qquad J=\det F.
\]

For a hyperelastic energy density W(E) per reference volume:

- S=partial W/partial E is second Piola–Kirchhoff stress (reference/reference).
- P=FS is first Piola–Kirchhoff stress (spatial/reference, two-point, generally nonsymmetric).
- sigma=J^-1 P F^T=J^-1 F S F^T is Cauchy stress (spatial/spatial, current frame).
- The material tangent is the derivative of S with respect to E; the element tangent also includes the geometric/initial-stress contribution from the finite-deformation force linearization.

Integrate internal virtual work and strain energy in the reference configuration. A route may expose all three stress measures only when each is computed from the same accepted F, with its measure and frames declared.

### 5.2 StVK model and admissibility

**VERIFIED source formula:** the observed TL kernels implement

\[
W(E)=\mu E:E+\frac{\lambda}{2}(\operatorname{tr}E)^2,\qquad
S=2\mu E+\lambda\operatorname{tr}(E)I,\qquad P=FS.
\]

The isotropic material-parameter conditions proposed for a positive-definite infinitesimal elastic modulus are

\[
\mu>0,\qquad K=\lambda+\frac{2}{3}\mu>0
\quad\text{(equivalently }3\lambda+2\mu>0\text{)}.
\]

These conditions should be validated before assembly. Kinematic admissibility requires finite F and positive determinant above an Owner-selected numerical guard J_min > 0. The TET4 source currently rejects J <= 10^-10; that is an observed implementation guard, not a proven physical limit, a universal numerical safety margin, or an approved E01 threshold. Do not silently transfer it to every route.

StVK is an objective hyperelastic law under proper superposed spatial rotations, but its quadratic Green-strain energy is not a general-purpose finite-strain material calibration. The Owner must bound the experimental deformation/material claim; do not use element success at large strain as a constitutive validity claim.

### 5.3 Candidate compressible Neo-Hookean model

**BLOCKED / not implemented in inspected source.** The following is one explicit candidate among several compressible Neo-Hookean energies:

\[
W(F)=\frac{\mu}{2}\left(J^{-2/3}\operatorname{tr}C-3\right)
+\frac{K}{2}(\ln J)^2,\qquad J>J_{min}>0,\quad\mu>0,\ K>0.
\]

It uses an isochoric/volumetric split, where K is the infinitesimal bulk modulus. Its PK2 response is

\[
S=\mu J^{-2/3}\left[I-\frac{\operatorname{tr}C}{3}C^{-1}\right]+K\ln(J)C^{-1},
\qquad P=FS,\qquad \sigma=J^{-1}PF^T.
\]

**Recommendation among formulations:** select this isochoric/volumetric form for an optional future E01-C route, with mu the infinitesimal shear modulus and K the infinitesimal bulk modulus. A second common alternative is

\[
W_{alt}=\frac{\mu}{2}(I_1-3)-\mu\ln J+\frac{\lambda}{2}(\ln J)^2,
\qquad I_1=\operatorname{tr}C,
\]

with \(K=\lambda+2\mu/3\). Both have the same infinitesimal isotropic moduli and the same quadratic small-strain energy \(\mu\,\mathrm{dev}(E):\mathrm{dev}(E)+K(\operatorname{tr}E)^2/2\), but they differ at finite deformation. The split form makes the chosen bulk modulus explicit and separates isochoric and volumetric contributions; the alternative is simpler in Lamé parameters. Selection of one does not imply calibration or broader material validity. Near-incompressible use can still lock in low-order displacement elements and is outside support without separate evidence.

For the recommended energy, let \(B=C^{-1}\), \(I_1=\operatorname{tr}C\), \(a=J^{-2/3}\), and \(A=I-(I_1/3)B\). For any symmetric material strain increment \(H=dE\), \(dC=2H\), \(d(\ln J)=B:H\), \(da=-(2/3)a(B:H)\), \(dB=-2BHB\), and \(dI_1=2\operatorname{tr}H\). Therefore the exact material tangent action is

\[
\begin{aligned}
dS={}&\mu a\left[-\frac23(B:H)A-\frac23\operatorname{tr}(H)B+\frac{2I_1}{3}BHB\right]\\
&+K\left[(B:H)B-2\ln(J)BHB\right].
\end{aligned}
\]

Equivalently, with minor symmetry in K,L,

\[
\mathbb C_{IJKL}=-\frac{2\mu a}{3}A_{IJ}B_{KL}-\frac{2\mu a}{3}B_{IJ}\delta_{KL}
+\frac{2\mu a I_1}{3}B_{I(K}B_{L)J}+K B_{IJ}B_{KL}-2K\ln(J)B_{I(K}B_{L)J}.
\]

The Total Lagrangian first-Piola tangent follows by differentiating P=FS:

\[
\mathcal A_{iJkL}=\delta_{ik}S_{LJ}+F_{iI}\mathbb C_{IJKL}F_{kK},\qquad
K_{ai,bk}=\int_{\Omega_0}N_{a,J}\mathcal A_{iJkL}N_{b,L}\,dV.
\]

For StVK, use the same geometric term with \(\mathbb C_{IJKL}=\lambda\delta_{IJ}\delta_{KL}+\mu(\delta_{IK}\delta_{JL}+\delta_{IL}\delta_{JK})\). These are analytic candidate derivatives to be checked independently; no tangent evidence is claimed.

The algorithmic material and geometric tangents must be obtained consistently from this energy/response. The model is defined only for finite nonsingular F with J>J_min. Reject invalid input and trial states; do not clip J, regularize silently, or continue through inversion.

**Owner choice required:** select this model or another named compressible Neo-Hookean variant, and approve the supported deformation interval. Do not assign a numeric J_min by convention or by copying the StVK 10^-10 guard. First define an application-based admissible deformation domain, then study log-spaced J values and isochoric/shear states inside that domain using independent energy/stress/tangent derivatives and conditioning of F and C. A candidate floor is the smallest lower J bound in that declared domain for which the preregistered derivative/conditioning limits hold with margin; if no physically justified domain and stable bound are agreed, keep the Neo-Hookean route disabled. Reject nonfinite F and J<=0 immediately, reject 0<J<=J_min once a justified J_min is selected, and never clip J or regularize silently.

### 5.4 Objectivity and coordinate transformation contract

For any proper orthogonal spatial rotation Q, F'=QF must satisfy E'=E, S'=S, W'=W, P'=QP, and sigma'=Q sigma Q^T. For a pure rigid rotation F=Q, E=0, so the reference StVK state has zero stress and energy. These are mathematical identities; numerical acceptance margins remain PROPOSED until the independent V&V preregistration is approved.

### 5.5 Tensor serialization

Use explicit field metadata: stress_measure, row and column frame, physical units, result location, component order, formulation/material identity, load-state identity, schema version, availability, and provenance/recovery method.

- Symmetric Cauchy and PK2 fields may use [xx,yy,zz,xy,yz,xz]. For strain fields, declare engineering shear; for stress fields, declare tensorial shear.
- PK1 is a full two-point 3x3 tensor. Serialize all nine components with an explicit row-major order and spatial row/reference column frames; never force it into six-component symmetric Voigt form.
- F also requires nine components and explicit spatial/reference frames.
- Integration-point values are the primary local constitutive outputs. Any element/nodal averaging or extrapolation is a distinct derived field with a declared method. Never average unlike measures or frames.
- Units are the model's coherent declared units. Do not infer SI or silently convert PK1/PK2/Cauchy values.

## 6. WP-E01-D — independent, preregistered nonlinear V&V protocol

This section is a protocol candidate, not execution evidence. Before any future run, freeze the source commit, model equations, material values and units, geometry, boundary/loading path, mesh and integration rule, reference implementation/provenance, output observables, norms/scales, numerical thresholds, finite-difference steps, branch labels, and pass/fail rules. Hash the frozen protocol and its independent reference before evaluating the QF route. The reference must not call the production constitutive or element routine under test.

### 6.1 Independent constitutive references

**J2 material:**

1. Hydrostatic 3D strain: q=0, no plastic flow, and unchanged alpha.
2. Pure shear: compare the yield threshold, stress, return increment, plastic strain, accumulated plastic strain, and hardening response against an independent tensor oracle; the convention implies |tau_xy|=sigma_y/sqrt(3) at first yield for a pure-shear state.
3. Uniaxial stress with free lateral surfaces: elastic response, first yield, plastic loading, unloading, reverse loading, and reloading compared with an independently coded one-dimensional branch solution.
4. Proportional and noncoaxial multiaxial histories compared with an independently written tensor return map. Check deviatoric plastic increments, yield-surface consistency, state evolution, and dissipation.
5. Tangent: for each unit-Frobenius symmetric tensor-strain direction D, hold incoming state \(z_n\) fixed and form \(FD_h=[\sigma(\varepsilon+hD;z_n)-\sigma(\varepsilon-hD;z_n)]/(2h)\). Encode strain shear as engineering shear and decode stress shear as tensorial stress before comparing in tensor Frobenius norm. Use multiple non-axis-aligned directions and candidate step sweep \(h=\varepsilon_{ref}10^{-2},\ldots,\varepsilon_{ref}10^{-7}\), where \(\varepsilon_{ref}\) is a declared dimensionless strain scale. Label each perturbation's active branch. Establish a preregistered plateau on each smooth branch. Use one-sided differences near yield and make no classical derivative claim at the switch.

**StVK and, only after implementation, Neo-Hookean:**

1. Use independent energy derivatives to obtain S and P for uniaxial stretch, volumetric stretch, and simple shear.
2. Compare material and assembled-force directional tangents with an independent derivative of energy/internal force at smooth states.
3. Verify J guard behavior on both sides of the preregistered domain boundary; invalid and nonfinite trial states must be rejected without changing accepted state.
4. Apply proper rigid rotations and compare E,S,W invariance and P,sigma transformation laws.
5. For Neo-Hookean, separately check energy/response only in the Owner-approved sampled domain; do not infer global stability from a few paths.

### 6.2 Independent element and assembly references

- **TET4:** homogeneous affine deformation and constant strain/stress; independent volume and virtual-work integration; compare integrated force and energy to closed-form constant-field values. Test proper rigid rotation and positive reference/current Jacobians.
- **HEX8:** affine fields on an undistorted cube and selected distorted-but-valid geometry; independently evaluate all eight 2x2x2 points and integrate reference-volume energy/force. Check rigid rotation and coordinate transformation identities. Do not claim reduced integration or hourglass stabilization.
- Compare each material point before comparing global sums so a quadrature/assembly defect cannot hide a constitutive defect.
- For the nonlinear element tangent, compare the tangent action against independent directional differences of the assembled internal force at fixed accepted material state. Freeze direction and differencing strategy in the protocol.

### 6.3 Multi-increment, transaction, and failure references

Use a homogeneous bar or block with analytically controlled uniaxial stress and free transverse surfaces. Run load, unload, and reversal through multiple accepted increments; compare the same load factors with an independent incremental material oracle. Repeat with a refined load-step partition. Force a retryable increment failure and verify the cutback begins from the exact last accepted displacement, load factor, and material-state digest.

Controlled negative cases include: maximum iterations, line-search failure, linear-solver failure, constitutive/domain rejection, nonfinite trial data, J <= J_min, invalid material parameters, minimum increment, exhausted cutback budget, corrupt/mismatched checkpoint, and failed state validation. Every negative case must produce its declared typed failure, preserve the previous accepted state, and contain diagnostics adequate to identify the failing increment and cause.

### 6.4 Mesh sensitivity and acceptance measures

Use at least three systematically refined meshes for any claimed spatial sensitivity/convergence study, with one or more preselected observables and a separately frozen reference. A uniform affine patch checks implementation and patch consistency; it is not itself evidence of general mesh convergence. Do not require monotonic convergence unless the selected formulation/reference mathematically justifies it.

Candidate error measures:

- Scalar/vector/tensor comparison: scaled norm error ||x-x_ref||/max(||x_ref||,x_scale); set a dimensional absolute error rule when the reference is zero or near zero.
- Tangent action: scaled difference between C d and the independent branch-preserving directional derivative. Report raw values, direction, perturbation sizes, branch labels, and the observed plateau range.
- Objectivity: compare the transformed fields in their declared frames, with separate dimensional scaling for stress and energy.
- Energy and force: compare each with the independent reference and report equilibrium residual separately; a small residual does not establish a small constitutive error.
- Mesh study: report each mesh, quantity of interest, reference, and convergence trend. A numerical mesh-sensitivity threshold is a separate Owner-approved gate.

### 6.5 Threshold policy

**All criteria below are PROPOSED and unfrozen. No execution evidence is claimed.** Proposed values are planning targets. A prior numeric value is inherited only if formulation, observable, norm, scale, route, and domain are identical; otherwise the value is not transferred as a pass gate.

| ID / check | Norm and scaling | Proposed threshold and applicability | Independent reference and status |
| --- | --- | --- | --- |
| VV-01 Newton equilibrium | Free-DOF 2-norm and dimensioned scale: `||R_f||₂ <= F_abs + τ_R max(||f_target,f||₂,F_ref)`; `F_ref>0` and `F_abs>=0` are fixed model inputs. Record absolute residual and normalized residual. Correction `||Δu_f||₂` and `η_u` are diagnostics. | Candidate `τ_R=1e-8` is PROPOSED, dimensionless. `F_abs` and `F_ref` are in force units and have no selected values. No mandatory correction gate; if Owner selects one, `U_abs`/`U_ref` are in length units and must be separately preregistered. Nonfinite, stagnation and max-iteration cases fail. | Zero-load and unit-rescaling checks; analytic linear equilibrium plus independently assembled force/energy references for each nonlinear route. The current unit floor is not dimensionally invariant; no tolerance is inherited as an E01 pass result. |
| VV-02 line search and cutback | Residual 2-norm merit; public controller default accepts strict merit decrease, while explicit profiles may apply Armijo; load-factor increments are recorded. | Candidate E01 Armijo profile `c=1e-4`, alpha halving from 1, `alpha_min=1e-4`, at most 12 reductions; max 25 Newton iterations and 25 rejected increments. Retry policy and endpoint tolerance are route-selected in §3.2. Every candidate must either satisfy its selected rule or reject; zero unclassified acceptances. | Independent evaluation of the same residual from a separately coded oracle on selected smooth fixtures; decision ledger records retry classification and final load discrepancy. Armijo constants are proposed for E01; other controller defaults remain route-specific. |
| VV-03 transaction and restart | Digest equality for rollback; compare every accepted field and identity. | Exactly zero accepted-state digest changes on rejection, zero trial commits, one atomic commit on acceptance; corrupted/incompatible checkpoints expose zero numerical fields. Restart must restore the checkpoint's accepted logical state under matching schema/identity; no universal bitwise serialized-equality claim. | Independent serialized-state ledger and recomputed digest; no solver-result comparison substitutes for state identity. Boolean/identity gates are PROPOSED; WP10 evidence remains bounded to its recorded routes. |
| VV-04 J2 stress/state/energy/consistency | Stress and plastic-strain tensor errors use separate positive stress/strain scales; free-energy error uses an energy-density scale; alpha error is absolute; yield overrun is `max(f,0)` normalized by a positive stress scale. A separate independent thermodynamic-dissipation reference uses `ΔD=σ_y0 Δα`; do not compare the existing endpoint-trapezoid accumulator to it as if they were the same field. | Candidate stress/plastic-strain/free-energy relative errors `<=1e-10`; `|alpha-alpha_ref|<=1e-12`; normalized yield residual `<=1e-10`. If a separately typed `ΔD` output is approved, proposed comparison error `<=1e-10` and `ΔD>=-1e-12 D_ref`, with `D_ref` in energy/volume units. Applies to elastic, smooth plastic, loading/unloading/reloading states. All thresholds are PROPOSED. | Independent 3D tensor return map plus closed-form uniaxial solution and the declared free-energy/storage convention. Similar WP08 R1 numeric gates are route-specific and are not inherited for this small-strain route. |
| VV-05 J2 tangent | Fixed incoming state; compare the production tangent action with branch-preserving independent central differences of stress. Use a unit-Frobenius symmetric tensor-strain direction; encode its shear components as engineering shear and decode the resulting six-component stress with tensorial shear before taking tensor Frobenius norms. Use positive `C_ref` [stress units] and dimensionless error `||C_prod:D-FD_h(D)||_F / max(||C_prod:D||_F,C_ref||D||_F)`. | Candidate relative error `<=2e-5` for at least three consecutive geometric step sizes on each smooth elastic/plastic branch. Candidate schedule `h=ε_ref × (1e-2,...,1e-7)` with dimensionless `ε_ref`; `C_ref`, schedule, plateau definition and threshold are PROPOSED. One-sided transition checks are diagnostics; no classical derivative gate at switching. | Independent tensor return-map derivative with fixed incoming state, non-axis-aligned directions, and raw pre-symmetrization comparison. The numeric gate resembles a WP08 FE-force tangent threshold but is not inherited for this material tangent. `J2_TANGENT_CONSISTENCY` remains BLOCKED until evidence exists. |
| VV-06 StVK and future Neo-Hookean energy/stress | Material stress error normF(S-S_ref)/max(normF(S_ref),S_scale); energy error abs(W-W_ref)/max(abs(W_ref),W_scale); tangent derivative error scaled as VV-05. | Stress and energy relative errors <=1e-10 against exact/independent derivatives. Tangent directional error <=2e-5 at a three-step plateau. Applies only to preregistered admissible states; NH disabled until its model and J_min are approved. | Closed-form StVK and independent differentiation of the selected energy. Thresholds resemble bounded WP08 energy/stress/tangent records but are not inherited for these TL formulations. |
| VV-07 objectivity | Frobenius differences after applying the exact proper-rotation transformation; use separate positive characteristic scales for strain E, stresses S/P/sigma, and energy W. | Relative transformed-field error <=5e-11 for E, S, W, P, sigma on preregistered rotations; pure rotation zero-strain/stress/energy errors use those declared scales. | Exact identities E'=E, S'=S, W'=W, P'=QP, sigma'=Q sigma Q^T; proposed planning target informed by bounded prior objectivity records, not inherited. |
| VV-08 TET4/HEX8 patch and element tangent | Relative force, energy, stress, and tangent-action norms divided by max(reference norm, declared dimensional scale). | Affine patch force/stress/energy error <=1e-10; tangent action <=2e-5 at a finite-difference plateau. TET4 one point and HEX8 full 2x2x2 only. | Independently integrated constant-field patch oracle; separately coded quadrature at each integration point. Values are proposed and do not establish general mesh accuracy. |
| VV-09 multi-increment path | Same state/field scaling as VV-04 and VV-01 at matched load factors; compare complete accepted state at every increment. | Same VV-04 material tolerances and VV-01 equilibrium gates; rollback digest mismatch count=0. The retry path must match an independently stepped reference at shared load factors within those tolerances. | Independent 1D/3D incremental oracle and accepted-state ledger. Proposed; no multi-increment evidence was generated here. |
| VV-10 invalid-state refusal | Count invalid cases accepted or numeric result fields emitted; compare accepted-state digest. | Zero invalid inputs accepted, zero result fields for a rejected trial, and exactly zero accepted-state digest changes. This includes nonfinite inputs, J<=0 and (after selection) 0<J<=J_min. | Independent determinant/parameter-domain checks and state ledger. Boolean gate; no numeric J_min is proposed. |
| VV-11 mesh refinement | Report QoI sequence and error against a separately frozen continuum/reference solution, with norm and scale selected per QoI. | Diagnostic only: at least three systematically refined meshes. No universal numerical pass threshold or monotonicity requirement is proposed; an Owner-selected QoI threshold is required before claiming spatial convergence. | Manufactured/analytical continuum solution or an independently refined reference model. No E01 mesh-sensitivity result is claimed. |
| VV-12 result and checkpoint schema | Exact comparison of schema/version, measure, frames, units, component order, location, state identity, availability and unavailable reason; independently decode numeric payload. | Zero semantic metadata mismatches; PK1 and F always have nine ordered components; symmetric stress/strain use the declared six-component order and shear meaning; NOT_COMPUTED has no numeric payload and is never replaced by zero. Numeric payload round-trip must preserve each binary64 value under the approved serializer. | Independent schema validator plus known tensor fixtures and accepted-state ledger. Proposed exact semantic gate; no schema implementation or run is claimed. |

**Threshold provenance:** VV-04 and VV-08 values are planning targets informed by similarly named WP08 R1 records; VV-05, VV-06, and VV-07 are analogical planning targets from bounded prior derivative/objectivity evidence, not inherited criteria. VV-01 uses a current default relative value but introduces new explicit scales and a correction gate. No WP08–WP10 result passes any E01 gate by transference. The existing StVK determinant guard 1e-10 is code behavior, not an accepted J_min or test tolerance. Owner approval is required for every numeric value and for the scale definitions before preregistration.

## 7. WP-E01-E — experimental FEM integration, API, and limits

### 7.1 Candidate support matrix

| Material law / formulation | Element and quadrature | Kinematics and solver target | Result fields and state | Evidence / boundary |
| --- | --- | --- | --- | --- |
| Small-strain J2 material point, H>=0 | No FEM element or quadrature | Infinitesimal strain in fixed material axes; local elastic predictor/radial return, no global Newton | Small-strain Cauchy stress, symmetric plastic strain, alpha, and a dissipation field only after its semantics are settled; report branch and trial state separately | Constitutive routine exists. Material-point use is the first bounded target. Tangent consistency BLOCKED; current dissipation accumulator is not yet the proposed thermodynamic quantity. |
| Small-strain J2 in a nonlinear FEM solve | TET4/HEX8 combination is a future opt-in target only; element quadrature and state ordering must be specified per family | Infinitesimal constitutive law, Full Newton only after D5 passes or after Owner explicitly approves a different tangent strategy; load stepping/line search per §3 | Same J2 point fields at integration points and accepted-state history; no finite-strain measure inferred | Existing J2 element routes do not by themselves establish this exact combination. Do not dispatch as supported until independently checked. No contact. |
| StVK Total Lagrangian | TET4, one constant-gradient integration point; HEX8, full 2x2x2 eight-point Gauss rule | F=I+grad_X u, E Green-Lagrange; Full Newton static with explicit load stepping, line-search/cutback settings from §3 | F (nine spatial/reference components), E, PK2 S, PK1 P (nine spatial/reference components), Cauchy sigma, W per reference volume, J; integration-point and accepted-step identity | Kernels/assembly exist. Bounded experimental target after admissibility, independent patch/tangent evidence, and Owner domain approval. No reduced integration. |
| Recommended compressible Neo-Hookean Total Lagrangian | TET4/HEX8 only as a later target with the same respective rules above | Recommended split energy in §5.3; Full Newton only after a selected J_min/domain and independently verified material and element tangents | Same finite-elastic fields as StVK from one accepted F | Not implemented in inspected sources. Disabled until separately implemented and verified. |
| TL J2, multiplicative finite-strain J2, general contact, general nonlinear dynamics, general postbuckling | Any | Excluded | No E01 result support | Do not infer these capabilities from existing class names or neighboring routes. |
| Mixed families/materials, high-order elements, reduced/selective integration, unsupported loads/BCs | Any | Fail closed unless separately decided and independently verified | No converged-looking result for unsupported combinations | Explicit experimental route selection is mandatory. |

### 7.2 Quadrature and local state

The candidate first target retains TET4's one-point constant-gradient rule and HEX8's eight-point 2x2x2 Gauss rule. These are different integration patterns, and a result or checkpoint must include the rule and stable integration-point order. Each stateful Gauss point owns a detached trial material state. On increment acceptance, all point states are committed together; on any rejection, all point states roll back. No selective/reduced integration is proposed for HEX8.

### 7.3 API, result schema, and availability

Expose nonlinear capabilities through explicit experimental selectors and return the selected formulation, element/material scope, load-control policy, and schema version. Unsupported combinations must fail before producing a converged-looking result.

Each field record includes: field name; measure; row/column frames; component order; units; result location; accepted load-step identity; state/provenance identity; recovery/averaging method; availability; unavailable reason; and schema version. Stress measures remain separate. Integration-point response is authoritative; derived element/nodal fields are named and marked as extrapolated or averaged.

Availability states should distinguish at least AVAILABLE, NOT_COMPUTED, UNAVAILABLE, and FAILED. NOT_COMPUTED means no numeric value exists; it must not serialize as a zero tensor. UNAVAILABLE carries a reason (for example, unsupported route or invalid deformation). FAILED identifies a failed evaluation. Persist only data from the accepted state; preserve trial/rejected values only in diagnostics if explicitly needed and clearly marked non-result.

Diagnostics include formulation and material IDs, element/integration-point location, load factor/increment, Newton and line-search/cutback history, residual and scales, J minimum and guard status for TL, constitutive branch and return increment for J2, state/checkpoint digests, and typed failure reason.

## 8. Development dependency map

This is a scientific sequencing proposal, not implementation authorization.

1. **Owner decisions and preregistration schema:** decide convergence norms/scales, state transaction invariant, material models, admissible domains, integration rules, result measures/frames, numerical reference models, thresholds, and support limits.
2. **A foundation:** reuse Newton/load control/transaction infrastructure; document and close any failure/rollback gaps for the selected E01 route.
3. **B constitutive point law:** retain small-strain J2 equations and convention; independently verify elastic/plastic branch derivatives and dissipation before relying on the tangent in a global Newton solve. Tangent correction, if required, is a focused implementation task.
4. **C elastic finite deformation:** independently validate StVK TET4/HEX8 energy, stress, and tangent. Treat a selected Neo-Hookean material as a separate implementation and V&V dependency; it is not a prerequisite for StVK-only experiments.
5. **E assembly and API:** integrate only Owner-approved combinations, preserve per-point state transaction, and implement explicit result/availability metadata. Do not couple J2 small strain to a finite-strain plasticity interpretation.
6. **D independent V&V:** execute only after Owner approval and a frozen protocol. Material-point tests precede element tests; element tests precede multi-increment and mesh-sensitivity claims. Failure/rollback and restart evidence is required before any accepted-state result claim.
7. **Status:** report bounded experimental findings separately. WP-E01 stays OPEN until Owner reviews the full evidence and makes a separate status decision.

## 9. Detailed Owner decision matrix

Every recommendation below is PROPOSED. No numeric tolerance or model choice in this matrix has Owner approval merely by appearing here.

### D1 — Newton convergence norms and thresholds

- **Alternatives:** retain the current WP10 relative residual and its force scale/floor; replace it with a dimensionally explicit residual scale; or require both residual and scaled correction gates.
- **Recommendation:** retain current behavior only for exact reuse of its bounded route. For a new E01 claim, specify a free-DOF residual norm and dimensional force reference, report a separately scaled correction norm, and do not let correction size alone establish convergence. Decide whether a dual gate is needed per route.
- **Mathematical justification:** equilibrium is R=0; a correction may be small under stagnation or a poor tangent while force imbalance remains. A dimensional floor is needed at zero load, but a fixed numeric floor depends on units.
- **Existing compatibility:** current driver reports residual and correction histories; WP10 explicitly retains a force-scale/floor policy and says it is unit-dependent below the floor. No general correction gate is established.
- **Required V&V:** zero load, near-zero reference load, scaled-unit cases, smooth elastic and plastic paths, stagnation, and forced maximum-iteration failure.
- **Owner approval:** PENDING for the norm, scale, tolerance, and correction-gate policy. Numeric threshold must be frozen before any E01 run.

### D2 — Load increment acceptance, line search, and cutback

- **Alternatives:** fixed load increments; adaptive increments with rollback/cutback; line search always enabled; or line search enabled only for selected routes.
- **Recommendation:** use adaptive retry only from the exact last accepted state; accept an increment only after equilibrium and state validation; retain every rejection reason. Make the selected line-search merit rule and terminal min-step/cutback budget explicit per route.
- **Mathematical justification:** local nonlinear failure may be recoverable by reducing load increment, but retry must not carry any rejected path-dependent material state.
- **Existing compatibility:** adaptive load-control, line-search, retry classification, rejection logs, and bounded cutback results already exist. They are not universal convergence evidence.
- **Required V&V:** accepted fixed path, accepted line-search path, forced retry/cutback path compared at matching load factors, terminal minimum increment, exhausted retries, and nonretryable failure.
- **Owner approval:** PENDING for route coverage, merit rule, min increment, and retry budget.

### D3 — Internal-state transaction semantics

- **Alternatives:** mutable state updated in place; detached trial state with commit/rollback; per-material transactions; or one composite transaction covering displacement, material points, continuation, and accepted metadata.
- **Recommendation:** one composite detached trial and atomic accepted-state replacement. All local evaluations use the same accepted state; rejected line-search/load trials are discarded. Checkpoint only a validated accepted state.
- **Mathematical justification:** path-dependent constitutive evolution is a function of the accepted history; a retry from a modified rejected history solves a different problem.
- **Existing compatibility:** NonlinearStateTransaction implements detached trial/commit/rollback and integrity validation; WP10 has bounded transaction/checkpoint records.
- **Required V&V:** digest unchanged after each rejection/failure; exactly one commit per accepted increment; retry equivalence to a reference split path; checkpoint resume and mismatch/corruption refusal.
- **Owner approval:** PENDING for exact composite fields, checkpoint identity, and compatibility/migration rules.

### D4 — J2 yield and hardening conventions

- **Alternatives:** von Mises q=sqrt(3s:s/2) with isotropic H>=0; kinematic or mixed hardening; alternative definitions of accumulated plastic strain and dissipation.
- **Recommendation:** use associative small-strain von Mises radial return with linear isotropic hardening, f=q-(sigma_y0+H alpha), d-alpha=d-gamma, and H=0 for perfect plasticity. Keep kinematic hardening and finite-strain multiplicative plasticity out of E01.
- **Mathematical justification:** this convention yields the stated radial-return denominator 3mu+H, nondecreasing accumulated plastic strain, hardening storage \(\psi_h=H\alpha^2/2\), and thermodynamic dissipation \(\Delta\mathcal D=\sigma_{y0}\Delta\gamma\) after subtracting the storage increment from plastic work.
- **Existing compatibility:** the existing material routine implements these branches/variables; stress response is small-strain Cauchy. Its `plastic_dissipation` accumulator is endpoint trapezoidal stress work. It is not established as thermodynamic dissipation for arbitrary paths; do not rename or reclassify it. WP08's Biot-J2 dissipation contract is a different route. The tangent is not independently verified.
- **Required V&V:** hydrostatic, pure shear, uniaxial loading/unloading/reversal, noncoaxial path, yield consistency, state evolution, and energy/dissipation against independent tensor and 1D oracles.
- **Owner approval:** PENDING for parameter domain, initial yield/hardening interpretation, stored state variables, thermodynamic dissipation output, and semantics/preservation of the current accumulator.

### D5 — J2 algorithmic tangent acceptance

- **Alternatives:** accept the current basis-response/symmetrized matrix; derive a branch-specific analytic tangent; or retain a numerical tangent for a bounded experimental route.
- **Recommendation:** do not claim consistency until an independent fixed-state, branch-aware directional derivative check passes. Compare the current matrix before changing it; any symmetrization correction requires evidence.
- **Mathematical justification:** Newton's local linearization needs C_alg=partial sigma_n+1/partial epsilon_n+1 on each smooth active branch; a yield switch is nonsmooth and has no single classical derivative.
- **Existing compatibility:** source constructs and symmetrizes tangent via basis variations. WP08/WP09 tangent evidence concerns different, bounded routes and must not be treated as J2-material proof.
- **Required V&V:** independent oracle, multiple non-axis-aligned directions, fixed incoming state, geometrically decreasing perturbation sweep with a preregistered three-step error plateau, branch-preserving central differences away from the switch, one-sided checks near the switch, and raw pre-symmetrization versus returned tangent comparison. A proposed directional relative error of 2e-5 is dimensionless and not inherited from WP08/WP09; both its stiffness reference scale and exact plateau test require Owner approval.
- **Owner approval:** PENDING on the acceptance metric and preregistered threshold. Tangent status remains UNVERIFIED/BLOCKED until evidence.

### D6 — StVK admissibility

- **Alternatives:** accept any finite F with positive determinant; enforce positive-definite isotropic moduli and a J guard; or impose an additional bounded strain/domain envelope.
- **Recommendation:** require finite inputs, mu>0, K=lambda+2mu/3>0, and J>J_min. Limit the experimental claim to a preregistered deformation domain; do not imply general material validity at arbitrary finite strain.
- **Mathematical justification:** the modulus conditions yield positive infinitesimal isotropic stiffness; J>0 preserves orientation. Neither condition alone establishes that StVK is a suitable material law for arbitrary large deformation.
- **Existing compatibility:** TL TET4/HEX8 routes implement StVK and reject J<=10^-10 in observed code. That guard is not independently justified as a physical or universal numerical bound.
- **Required V&V:** material input rejection, energy/stress/tangent derivatives, positive and near-boundary J, rigid-rotation objectivity, and bounded stretch/shear paths.
- **Owner approval:** PENDING for parameter domain, numerical guard, and experimental strain envelope.

### D7 — Neo-Hookean energy and J_min

- **Alternatives:** the proposed isochoric/volumetric split with logarithmic volumetric energy; another explicitly named compressible Neo-Hookean form; or defer Neo-Hookean and run StVK-only experiments.
- **Recommendation:** select one energy by formula, name it unambiguously, define K as the infinitesimal bulk modulus, derive stress/tangent from that energy, and choose J_min only after a conditioning/domain study. Deferral is a valid first experimental scope.
- **Mathematical justification:** compressible Neo-Hookean variants differ materially; J^-2/3, ln J, and C^-1 sensitivities make near-singular F especially sensitive to the lower bound.
- **Existing compatibility:** no Neo-Hookean law was found in the inspected material/kernel sources. Existing StVK guard 10^-10 cannot justify Neo-Hookean J_min.
- **Required V&V:** independent energy derivatives, stress/tangent directional checks, objectivity, sampled volumetric/isochoric response, domain rejection and accepted-state preservation.
- **Owner approval:** PENDING for model variant, moduli, J_min, and whether to defer implementation. Neo-Hookean is NOT IMPLEMENTED.

### D8 — TET4/HEX8 quadrature and supported combinations

- **Alternatives:** observed TET4 one-point and HEX8 full 2x2x2; alternative reduced/selective quadrature; or broader element/material combinations.
- **Recommendation:** initially retain the observed TET4 constant-gradient one-point rule and HEX8 eight-point full rule. Do not add reduced integration, mixed families, high-order elements, or new couplings without separate decisions and evidence.
- **Mathematical justification:** TET4 has constant element gradients; HEX8 full integration samples varying gradients and state at eight points. Reduced integration changes rank/stability behavior and is a separate formulation.
- **Existing compatibility:** these rules are present in the observed TL infrastructure; the J2 global experimental route's exact supported family/load combinations remain to be frozen.
- **Required V&V:** independent affine patch and virtual-work/energy checks; distorted valid HEX8; per-point material comparison; positive reference Jacobians; assembled tangent directional checks; multi-mesh observables.
- **Owner approval:** PENDING for each material × formulation × element × load-control combination.

### D9 — Stress measures, frames, units, and component ordering

- **Alternatives:** generic stress tensor; one selected measure per route; or separate Cauchy, PK1, and PK2 fields with explicit metadata.
- **Recommendation:** keep small-strain Cauchy, PK1, and PK2 separately identified; use reference/reference PK2, spatial/reference full-tensor PK1, and current/current Cauchy. Use symmetric order [xx,yy,zz,xy,yz,xz] with engineering strain shear and tensorial stress shear; use all nine explicit components for PK1 and F.
- **Mathematical justification:** stress measures transform differently and PK1 is generally nonsymmetric; engineering shear strain preserves the work-conjugate Voigt dot product with tensorial shear stress.
- **Existing compatibility:** the solid material helpers and WP08 result record use the six-component ordering and distinct shear semantics. Some existing fields/averages do not carry complete metadata. Historical corotational output is separately blocked from general measure claims.
- **Required V&V:** round-trip tensor/Voigt conversion, work conjugacy, stress transformation identities, serialization round-trip, no cross-measure averaging, and explicit units/location checks.
- **Owner approval:** PENDING for canonical metadata names/schema, units source, location policy, and legacy-field handling.

### D10 — Independent references and numerical acceptance thresholds

- **Alternatives:** reuse bounded WP08–WP10 thresholds wholesale; inherit a threshold only for an identical metric/route/domain; or define E01-specific thresholds from independent reference error and numerical plateaus.
- **Recommendation:** use independent analytical/material/energy/force oracles. Inherit a numeric gate only for an identical observable, formulation, norm, scale, and domain; otherwise derive and preregister a new threshold with Owner approval. Treat each existing pass only within its record's scope.
- **Mathematical justification:** threshold meaning depends on the norm, scale, reference accuracy, active branch, finite-difference step, and discretization error. A number without these definitions is not a reproducible scientific criterion.
- **Existing compatibility:** WP08-R3 and WP09 records contain numeric gates for their bounded corrected-corotational routes; WP10 retains its configured residual policy. None is a universal E01 threshold.
- **Required V&V:** freeze exact reference/provenance, observables, scales, finite-difference sweep, mesh series, tolerance source/rationale, and decision rules before running. Preserve failures and raw metrics.
- **Owner approval:** PENDING for all new numeric tolerances, mesh criteria, and threshold inheritance.

### D11 — Experimental capability boundaries

- **Alternatives:** enable current APIs by default; expose explicit opt-in bounded routes; or expose only material-point/element experimental interfaces until integrated evidence is complete.
- **Recommendation:** opt-in and fail closed. Start with Owner-approved material-point checks and StVK TL TET4/HEX8; make global small-strain J2 use conditional on the D5 tangent gate or an explicitly approved alternative tangent strategy. Keep Neo-Hookean disabled until implemented and verified; exclude contact coupling, general nonlinear dynamics, multiplicative finite-strain J2, general postbuckling, and automatic high-order claims.
- **Mathematical justification:** nonlinear material history, stress measures, and tangent domains differ by formulation; routing a model into the wrong kinematics or result contract can produce plausible but physically mislabeled output.
- **Existing compatibility:** corrected routes and solver dispatch already demonstrate explicit bounded selectors; legacy defaults and some output semantics remain distinct.
- **Required V&V:** API selection/rejection, full accepted-state serialization, rollback/restart, route identity, explicit result metadata, and regression of unaffected routes.
- **Owner approval:** PENDING for public selectors, initial combinations, result schema, and failure behavior.

### 9.1 Final WP-E01-A/B D1–D5 Owner decision matrix

This focused matrix supersedes earlier D1–D5 summary rows in this candidate. The Owner's D1–D4 principle approval and D5 block are recorded in [the D1-D4 Owner decision record](wp_e01_owner_decision_d1_d4_2026-10-20.md); the later partial approvals are recorded in the [Newton/checkpoint partial-freeze record](wp_e01_owner_partial_freeze_newton_checkpoint_2026-10-20.md). P1-P4 and checkpoint invariants in that partial record are OWNER_APPROVED for its bounded experimental scope. All other unapproved numeric values remain PROPOSED or OPEN; the matrix below is updated by that scope-limited overlay.

| Decision | Existing implementation behavior | Exact proposed contract and gate/diagnostic role | Proposed threshold, units and evidence status | Scientific justification / compatibility risk | Independent V&V reference | Owner recommendation and unresolved choice |
| --- | --- | --- | --- | --- | --- | --- |
| **D1 Newton convergence** | `src/solveur/core/nonlinear/load_control.py` forms the target and free-DOF residual and normalizes by `max(‖f_target,f‖₂, supplied_force_scale, 1.0)`. The common relative tolerance is `1e-8`; it accepts before solving another correction. The hard-coded `1.0` carries caller force units. `robustness.py` reports correction telemetry and treats four-sample residual stagnation (default relative threshold `1e-10`) as failure. The optional floor-aware route is a separate evidence-backed conjunction. | For free DOFs, `R_f=(f_target-f_int)_f`; choose a positive, run-fixed physical force scale `F_ref` and physical absolute force tolerance `F_abs`, set `S_F=max(‖f_target,f‖₂,F_ref)` and `ρ_R=‖R_f‖₂/S_F`, then require the **mandatory primary equilibrium gate** `ρ_R <= τ_R + F_abs/S_F`. At zero/near-zero load, `F_ref` keeps the scale finite; if no valid scale is supplied, configuration is invalid, not a zero denominator. Report `‖Δu_f‖₂` [length] and, when a positive physical `U_ref` exists, `η_u=‖Δu_f‖₂/max(‖u_f‖₂,U_ref)` as **diagnostics**. They are not a second convergence gate. Nonfinite residual/correction, singular/failed linear solve, max iterations, and stagnation are failures. For eliminated prescribed-DOF constraints, check prescribed values separately and exclude their reaction residual from `R_f`; for supported affine constraints `Cu=d`, require `rank(C)=rank([C d])` before solve and separately require `‖Cu-d‖₂≤G_abs+τ_g max(‖d‖₂,G_ref)`, with `G_abs≥0` and `G_ref>0` in length units. Unsupported or inconsistent constraints fail model setup and can never yield convergence. | `τ_R=1e-8` is **PROPOSED, NOT APPROVED**; it is dimensionless. `F_ref>0` and `F_abs≥0` are in the model's force unit and must be selected from a declared characteristic load and allowable imbalance. `U_ref>0` and optional `U_abs` are length units. Existing `1e-8` and `1e-10` are code defaults, not E01-qualified gates. WP08–WP10 residual thresholds belong to different bounded observables/routes and do not transfer without identical norm, scale, and scope. | Force balance is equilibrium; a small correction does not establish equilibrium and can reflect stagnation or a poor tangent. A positive physical reference makes the zero-load behavior dimensionally meaningful. Replacing the present unit floor may change accepted states. | Independent reference equilibrium residuals for zero/near-zero load and elastic/plastic states; repeat with coherent force-unit rescaling and show the normalized decision is invariant; verify prescribed/MPC consistency, reaction exclusion, stagnation/nonfinite/max-iteration refusal. Record correction norms but do not gate on them. | **APPROVED_PRINCIPLE; PENDING_NUMERICAL_FREEZE.** Owner approved the residual form and correction-as-diagnostic principle on 2026-10-20. Owner must still set `F_ref`, `F_abs`, `τ_R`, route-specific `U_ref` reporting, supported constraint forms/scales, and any exceptional route-specific gate. |
| **D2 Load steps, line search, cutback** | The current Newton loop counts residual evaluations, not correction updates; it can apply its final update without checking that state. Existing controls have cutback `0.5` and a cumulative rejection count; line-search defaults/configurations are route-specific. Growth `1.5`, minimum `min(1e-4,Δλ₀)`, alpha limits and endpoint guard are implementation details, not Owner-approved E01 policy. | **Owner-approved for bounded experimental incremental routes:** no more than 25 applied displacement corrections per attempt, with the residual checked after each update including update 25; Armijo `c1=1e-4` only with a selected merit and verified descent; `Δλ_new=0.5Δλ_old` only after complete rollback and an explicitly permitted failure; max 25 rejected attempts per complete path, no attempt 26. Exact merit/search behavior, retry classes, minimum increment, endpoint and growth policy remain OPEN. Any additional failure-class mapping in this candidate is a proposal only. | `N_corr=25` (count) OWNER_APPROVED; `c1=1e-4` dimensionless OWNER_APPROVED conditionally; `beta=0.5` dimensionless OWNER_APPROVED; 25 rejected attempts per path OWNER_APPROVED (count). The prior 12/14 line-search reductions, `alpha_min=1e-4`, proposed minimum increment, growth settings and failure mapping remain unapproved. | Accepted increments consume no rejection; each rejected attempt and retry are counted. Existing factor/counter behavior is compatibility evidence, but the Newton count does not implement P1 and no existing configuration proves the open Armijo descent condition. | Verify residual after update 25, count semantics, merit derivative/decrease, rollback before retry, permitted-class handling, global rejection boundary/no attempt 26, minimum-step and endpoint decisions after they are approved. | **PARTIAL OWNER APPROVAL.** P1-P4 are approved within the stated scope; approve remaining merit/search, retry classes, minimum increment/equality, endpoint and route details. |
| **D3 Transactional state** | `NonlinearStateTransaction` in `src/solveur/core/nonlinear/state.py` supports detached trials, integrity checking, commit and rollback. WP10 records bounded rollback and accepted-checkpoint identity/refusal behavior. Existing schema/version behavior remains unchanged. | **Owner-approved invariants:** isolate trial from accepted state; failed Newton iterations do not mutate accepted material history; rejected increment fully rolls back; accepted increment commits once; rollback covers displacement, strain, stress, plastic variables, accumulated outputs and solver history; rejected attempts do not contaminate future increments; checkpoint/restart consistency is independently verifiable. A checkpoint may persist only a consistent accepted state, but exact checkpoint structure/identity is not specified here. | Exact state invariants; no numeric/physical tolerance. Any proposed element/IP/formulation identity binding is unapproved; schema, identity, serialization, migration, backward compatibility and restart tolerances remain OPEN. | History-dependent plastic variables make partial rollback unsafe. WP10 supports detached trial, rollback, one composite commit and fail-closed checkpoint behavior; retain existing WP10 v1/v2 boundaries. | Independent field-by-field comparison across rejected Newton/load increments; exactly-once commit; corruption/mismatch refusal and restart equivalence under a future approved schema. | **OWNER_APPROVED invariants; OPEN checkpoint contract.** Owner approval does not freeze E01 schema, state identity/version, migration or restart tolerances. |
| **D4 Small-strain J2** | `VonMisesElastoplasticMaterial` in `src/solveur/materials/solid.py` implements infinitesimal-strain associative radial return for `H=0` and `H>0`, updating plastic strain and accumulated equivalent plastic strain. It updates the historical `plastic_dissipation` field by the source's endpoint trapezoid formula; stronger physical semantics remain open. | Owner-approved formulation: preserve the bounded return-map convention `q=√(3 s:s/2)`, `f=q-(σ_y0+Hα)`, elastic for `f_trial≤0`; plastic `Δγ=f_trial/(3μ+H)`, `Δα=Δγ`, `Δεᵖ=(3/2)Δγ s_trial/q_trial`; `H=0` perfect plasticity and `H>0` linear isotropic hardening; elastic unloading and isotropic reload/reversal without kinematic hardening. The principles distinguish plastic stress work, hardening storage and thermodynamic dissipation. Preserve the historical accumulator unchanged; no new energy output semantics are approved. | Candidate material gates remain **PROPOSED**. `σ_y0,H,μ,K_b` have stress units; `ε,εᵖ,α,γ` are dimensionless. New energy fields, if later approved, require separately declared units and availability. | The denominator `3μ+H` follows the approved isotropic radial-return convention. Existing Voigt is `[xx,yy,zz,xy,yz,xz]`, engineering strain shear and tensorial stress shear. Do not infer an integral or thermodynamic meaning for `plastic_dissipation` beyond its recorded source formula. | Independent closed-form uniaxial/tensor oracle; hydrostatic `q=0`, pure shear, monotone loading, unloading, reload, reversal and noncoaxial paths from fixed incoming states. Verify stress/yield/state/energy identities; compare the legacy accumulator without reclassifying it. | **APPROVED_PRINCIPLE; NUMERICAL GATES AND OUTPUT SEMANTICS OPEN.** Keep D5 separate and blocked. |
| **D5 J2 algorithmic tangent** | Source assembles basis-response tangent and symmetrizes it; no independent branch-aware derivative evidence exists for this small-strain material. WP08/WP09 element force-tangent records concern other formulations. `J2_TANGENT_CONSISTENCY` remains **BLOCKED**. | Require `C_alg=∂σ_{n+1}/∂ε_{n+1} at fixed z_n and branch`. Elastic branch is `C_e=K_b I⊗I+2μP_dev`; on a smooth plastic branch use the candidate derivative in §4.3, with incoming state fixed. Let `D` be a symmetric unit-Frobenius strain direction and evaluate independent central differences `FD_h(D)=[σ(ε+hD;z_n)-σ(ε-hD;z_n)]/(2h)`, with strain shear encoded as engineering shear and stress shear decoded as tensorial. Both perturbed returns must stay on the same smooth branch. At the switch there is no unique classical derivative: perform one-sided branch-selection/limit checks and label cross-branch central differences `NONSMOOTH_DIAGNOSTIC`, not pass/fail tangent evidence. Compare the unsymmetrized production tangent before symmetrization. | Candidate dimensionless error: `e_T(h)=‖C_prod:D-FD_h(D)‖_F/max(‖C_prod:D‖_F,C_ref‖D‖_F)`. Recommend `C_ref=K_b+2μ` [stress], fixed by the elastic material, and `h=ε_ref×10^{-j}`, `j=2,…,7`, where positive dimensionless `ε_ref` is preregistered per fixture. Proposed `τ_T=2e-5`: require `e_T≤τ_T` at three consecutive geometric steps and a finite-difference plateau, defined by `p_T(h)=‖FD_h-FD_{h/10}‖_F/max(‖FD_{h/10}‖_F,C_ref‖D‖_F)≤τ_T` for the two adjacent comparisons spanning those three steps. `C_ref`, `ε_ref`, schedule, plateau and threshold are all **PROPOSED**. No WP08/WP09 threshold transfers. | Tangent consistency is a local derivative property at fixed incoming state, not a global nonlinear convergence result. The elastic and smooth associative plastic tangent should be symmetric under the stated work-conjugate mapping; current symmetrization can hide an incorrect raw skew part or Voigt scaling. No derivative pass is claimed at the yield switch. | Independent material implementation/closed-form derivative and branch-preserving FD sweep over multiple normal, shear and mixed directions; confirm a plateau and threshold; compare raw and returned matrices; report `FINITE_DIFFERENCE_UNRESOLVED`, `BRANCH_CROSSING`, `TANGENT_MISMATCH` or nonfinite refusal distinctly. Transition checks are separate. A bounded force/tangent FEM result is not an oracle for this material derivative. | **BLOCKED_PENDING_INDEPENDENT_EVIDENCE.** Owner must approve `C_ref`, per-fixture `ε_ref`, `τ_T`, plateau rule and use of this tangent in Full Newton. No Full Newton validation until independent evidence passes. |

**Owner decisions recorded on 2026-10-20:** D1-D4 mathematical principles remain approved; the later partial-freeze record additionally approves the bounded experimental P1-P4 values and checkpoint lifecycle invariants. D1 force scales/residual threshold, the remaining D2 search/retry/minimum/endpoint rules, D3 schema/identity/migration/restart rules, and D4 numerical gates/output semantics remain OPEN or PROPOSED. D5 is `BLOCKED_PENDING_INDEPENDENT_EVIDENCE`. See both [the D1-D4 principle record](wp_e01_owner_decision_d1_d4_2026-10-20.md) and [the partial-freeze record](wp_e01_owner_partial_freeze_newton_checkpoint_2026-10-20.md).

**Decisions still requiring Owner choice or further evidence:** D1 physical force and constraint scales/tolerances; D2 merit/descent calculation, backtracking schedule, retry classes, minimum increment and endpoint rule; D3 checkpoint identity/schema/migration/restart criteria; D4 numerical material thresholds, any new energy-output semantics, and legacy accumulator interpretation beyond its source formula; D5 finite-difference scales, plateau and threshold plus independent branch-aware evidence. The approved P1-P4 values and checkpoint invariants do not complete the contract freeze. No tangent-consistency or Full Newton validation claim is available. See the two linked Owner decision records above.

### 9.2 Broader E01 decision rows D6–D11 (retained unchanged from prior candidate)

These rows concern E01-C–E and are preserved for context; they are outside this focused D1–D5 review.

| ID / priority | Existing implementation and alternatives | Recommended formulation and mathematical reason | Proposed acceptance criteria | Dependencies and remaining uncertainty | Agent recommendation |
| --- | --- | --- | --- | --- | --- |
| D6 StVK admissibility — later | TL StVK kernels exist and reject J<=1e-10 in observed TET4 code. Alternatives: positive J only, fixed numeric floor, or an application-bounded domain with justified floor. | Require finite F, mu>0, K=lambda+2mu/3>0, orientation-preserving F, and an Owner-approved domain. A code guard is not a physical domain or universal J_min. | VV-06 and VV-07: energy/stress derivative and objectivity gates in preregistered states; invalid cases meet VV-10. No numeric J_min proposed. | Depends on use-case domain, mesh distortion and conditioning evidence. Existing 1e-10 is not transferable as approved threshold. | REVISE until domain/guard chosen. |
| D7 Neo-Hookean model and J_min — later | No implementation found in inspected source. Alternatives: split isochoric/volumetric energy, Lamé-parameter compressible form, or defer. | Prefer W=mu/2(J^-2/3 I1-3)+K/2(ln J)^2; PK2 stress and exact tangent in §5.3. It has the same infinitesimal moduli as StVK but distinct finite response. Defer the route until its domain-based J_min is justified. | VV-06/07/10 with independent energy/stress/tangent oracle. No numeric J_min; 0<J<=J_min must reject after Owner selection. | New formulation and implementation; near-incompressible locking risk; requires domain and conditioning study. | REVISE / defer support until decisions and evidence. |
| D8 Element/quadrature support — later | TET4 constant-gradient one point and HEX8 full 2x2x2 integration exist. Alternatives: reduced/selective rules or wider element/material matrix. | Start with TET4 one point and HEX8 eight points only; separate state per point. Reduced integration changes stability and is out of scope. | VV-08 affine patch force/stress/energy <=1e-10 and element tangent action <=2e-5, proposed; per-point independent oracle. | Depends on each material/kinematics combination and stable point order; thresholds are not inherited from unrelated routes. | APPROVE initial quadrature target; Owner approval of combinations remains required. |
| D9 Stress measures and schema — later | Symmetric Voigt [xx,yy,zz,xy,yz,xz] and engineering-strain/tensorial-stress shear semantics exist; some outputs lack full metadata. Alternatives: generic tensor fields or separately typed measures. | Keep small-strain Cauchy, TL PK2, TL PK1, and TL Cauchy distinct; symmetric fields use six components, PK1/F use all nine row-major components with declared frames. Metadata also carries units, location, state, provenance, availability and schema. | VV-12: zero semantic mismatches; exact component shape/order/frame/measure round-trip; NOT_COMPUTED has no numeric payload and is not zero-filled. | Depends on public schema/version, units source, averaging/location rule, and legacy corotational labels. | APPROVE conventions; Owner schema naming/compatibility decision required. |
| D10 References and thresholds — all phases | WP08-WP10 provide bounded records with different observables and scopes; wholesale inheritance is not valid. Alternatives: copy prior gates, or preregister per-observable targets. | Use independent closed-form/material/energy/force/rotation references; reuse a numeric gate only for an identical route, observable, norm, scale and domain. Keep mesh study diagnostic until an observable-specific target is approved. | VV-01 through VV-12; explicit norms, scales, limits and references above. All numeric values remain PROPOSED; no result is claimed. | Requires Owner signoff on numeric thresholds, oracle provenance, finite-difference plateau and QoI-specific mesh target. | REVISE / thresholds not frozen. |
| D11 Capability limits/API — later | Explicit selectors and bounded routes exist, but not all combinations or outputs have complete fail-closed semantics. Alternatives: broad defaults or explicit opt-in experimental routes. | Opt-in and fail closed. Initial targets are J2 material point and StVK TL TET4/HEX8. Disable Neo-Hookean and integrated small-strain J2 until their dependencies pass. Exclude contact, general dynamics, multiplicative J2, postbuckling and high-order claims. | VV-10/VV-12 plus zero unsupported route producing a converged result; expose only accepted-state fields. | Depends on D1-D10 decisions, public selectors and failure/status schema. | APPROVE boundaries in principle; Owner route/API list remains pending. |

## 10. Remaining decisions before a future E01-A/B freeze

The Owner has approved D1–D4 principles, not their parameterization or public/persistence contracts. Remaining A/B decisions are enumerated in [the dedicated Owner decision record](wp_e01_owner_decision_d1_d4_2026-10-20.md): physical residual scales and thresholds; route-specific Newton/line-search/cutback/retry profile; checkpoint schema, identity and migration; material acceptance references; J2 output/legacy-field semantics; and the D5 tangent scale, step sweep, plateau, threshold and independent evidence. D5 remains a blocking eligibility condition for claiming this tangent consistent or validating Full Newton with it.

The broader D6–D11 questions remain separate: StVK admissibility, any Neo-Hookean formulation, element/quadrature combinations, result schema/API, independent C–E thresholds, and E01-C/D/E capability boundaries. The D1–D4 approval does not approve those packages or choices.

A separate explicit implementation GO and a separate V&V authorization are still required. This specification record does not authorize production implementation, numerical V&V, native FEM, qualification promotion, or release.

## 11. Unresolved scientific blockers and readiness

- **E01-A:** the Owner partial freeze approves 25 correction updates with a residual check after every update, `c1=1e-4` only with verified descent, `beta=0.5`, and a global limit of 25 rejected attempts. The current Newton loop does not implement the approved correction-count/check semantics. Force scales, `tau_R`, merit/search details, retry classes, minimum increment and target acceptance remain open. No general Newton convergence claim.
- **E01-B:** J2 radial-return equations and state are present. Algorithmic tangent consistency is unverified and blocks a consistency claim until independent branch-aware evidence exists.
- **E01-C:** StVK TL TET4/HEX8 code exists with a determinant guard, but admissible parameter/deformation limits and numeric acceptance gates remain to be approved. Neo-Hookean is not found/implemented in inspected sources.
- **E01-D:** independent protocol is prepared but NOT EXECUTED. No new PASS is claimed.
- **E01-E:** element, nonlinear driver, state, and result infrastructure can be reused, but exact combinations, field metadata, persistence, and fail-closed API behavior need Owner decisions and bounded evidence.
- Historical WP08–WP10 status is unchanged. No scientific qualification has been promoted.

**WP_E01_SPEC_REVIEW: PARTIAL_OWNER_FREEZE_RECORDED.** D1-D4 principles and the explicitly listed P1-P5 partial decisions are recorded; remaining parameters and schemas stay open. This does not complete the A/B freeze, authorize execution, or close WP-E01.
**WP_E01_SPEC_READY: YES — ready for Owner specification review, with explicit blockers and decisions above.**
**WP_E01_A_STATUS:** D1/D2 principles OWNER_APPROVED; bounded P1-P4 parameters OWNER_APPROVED; force scales, merit/search details, retry classes, minimum increment and endpoint policy OPEN.
**WP_E01_B_STATUS:** D4 principles OWNER_APPROVED; numerical gates and energy-output semantics OPEN; J2 tangent BLOCKED_PENDING_INDEPENDENT_EVIDENCE.
**WP_E01_C_STATUS:** StVK TET4/HEX8 bounded implementation; domain decisions pending; Neo-Hookean BLOCKED / not found in inspected source.
**WP_E01_D_STATUS:** preregistered protocol candidate ready; V&V NOT RUN.
**WP_E01_E_STATUS:** experimental integration contract candidate; exact supported combinations and schema pending Owner decisions.
**WP_E01_D1_D5_DECISION_READY:** YES — the focused D1-D5 matrix and remaining Owner choices are updated with the partial freeze.
**D1_D5_OWNER_DECISION_MATRIX:** UPDATED_WITH_PARTIAL_FREEZE.
**D1_NEWTON_PRINCIPLE:** OWNER_APPROVED.
**D2_CUTBACK_PRINCIPLE:** OWNER_APPROVED.
**D3_TRANSACTION_INVARIANTS:** OWNER_APPROVED.
**D4_J2_PRINCIPLES:** OWNER_APPROVED.
**D5_J2_TANGENT:** BLOCKED_PENDING_INDEPENDENT_EVIDENCE.
**WP_E01_A_B_SPEC:** PARTIAL_OWNER_FREEZE_RECORDED; COMPLETE_FREEZE_NO.
**CHECKPOINT_SCHEMA_APPROVED:** NO.
**J2_ENERGY_OUTPUT_SEMANTICS_APPROVED:** NO.
**NUMERICAL_VNV_AUTHORIZED:** NO.
**J2_TANGENT_CONSISTENCY:** BLOCKED — no independent branch-aware evidence was run or claimed.
**E01_A_FREEZE_RECOMMENDATION:** PARTIAL_OWNER_FREEZE — D1/D2 principles, P1-P4 and transaction invariants are approved within the bounded experimental scope; D1 force scales/tolerance and remaining line-search, retry, minimum-step and target rules stay open.
**E01_B_FREEZE_RECOMMENDATION:** APPROVED_PRINCIPLE / OPEN_OUTPUTS — Owner approved the small-strain radial-return principles; preserve the historical accumulator computation without stronger semantics; keep the tangent BLOCKED_PENDING_INDEPENDENT_EVIDENCE.
**E01_C_FREEZE_RECOMMENDATION:** REVISE — StVK scope can proceed after admissibility/domain choice; approve a Neo-Hookean energy only with a justified J_min, otherwise defer that route.
**E01_D_FREEZE_RECOMMENDATION:** REVISE — approve the protocol structure, then freeze every applicable threshold and reference before any execution.
**E01_E_FREEZE_RECOMMENDATION:** APPROVE boundaries in principle — initial routes remain opt-in, bounded and fail-closed, subject to exact Owner-approved combinations and schema.
**ACCEPTANCE_CRITERIA_FROZEN:** PARTIAL ONLY — P1-P4 are Owner-approved as stated; the complete A/B criteria set is not frozen and remaining values are OPEN/PROPOSED.
**OWNER_DECISIONS_PENDING:** D1 scales and `tau_R`; line-search merit/derivative and search budget; retry classes, minimum increment and endpoint; E01 checkpoint schema/identity/restart/migration; J2 numerical gates and output semantics; D5 independent evidence/criteria. D6-D11 remain separate broader E01-C-E decisions and are not approved here.
**IMPLEMENTATION_AUTHORIZED:** NO.
**NATIVE_FEM_AUTHORIZED:** NO.
**WP_E01_STATUS:** OPEN / EXPERIMENTAL_TARGET.

## 12. Read-only inspection record

Mandatory roadmap and Owner source: qualification/0_2_12/ROADMAP.md; qualification/0_2_12/owner_provided/QF_Solver_v0.2.12_roadmap_WPE01.md (§3 and §F).

Source families read for this E01 review:

- src/solveur/core/nonlinear/iteration.py, driver.py, load_control.py, state.py, and contracts.py.
- src/solveur/materials/solid.py.
- src/solveur/elements/solid/corotational_j2.py, total_lagrangian_j2.py, tet4_total_lagrangian.py, tet4_total_lagrangian_batch.py, hex8_total_lagrangian_batch.py, and hex8.py.
- src/solveur/core/analyses/geometric_nonlinear.py.

Records read:

- wp08_r1_constitutive_state_contract.json
- wp08_r1_vnv_acceptance_matrix.json
- wp08_r2_objectivity_and_plasticity_report.md
- wp08_r2_equation_implementation_test_map.json
- wp08_r3_newton_convergence_report.md
- wp08_r3_tangent_evidence.json
- wp08_r3_stress_results_contract.json
- wp08_r3_integrated_vnv_matrix.json
- wp08_nonlinear_stress_measures_contract.json and wp08_nonlinear_stress_measures_report.md
- wp09_tangent_robustness_report.md and wp09_directional_derivative_evidence.json
- wp10_state_transaction_contract.json, wp10_convergence_criteria_report.md, wp10_nonlinear_state_checkpoint_report.md, wp10_checkpoint_identity_migration_contract.json, and wp10_restart_equivalence_evidence.json

Read-only searches found the expected Newton, state-transaction, J2, StVK, and TET4/HEX8 symbols. A search for Neo-Hookean terms in the inspected src/solveur scope found no implementation. This bounded source search does not assert that no external prototype exists elsewhere.

The focused D1–D5 follow-up started from E01 branch HEAD `3b38c2c1823334d549d7bc119008955ca52f4340`; it rechecked the exact Newton residual/correction path, default and experimental line-search profiles, adaptive endpoint/cutback policy, small-strain J2 return and accumulator, WP08 route-specific dissipation contract, and WP10 transaction/restart records. The only changed file for this follow-up is this candidate document.

The Owner decision consolidation was prepared from the verified clean E01 branch HEAD `dfd2a6f3e857e3b738f5340b860fb9275383628c` and canonical roadmap checkout HEAD `3c0e0492104375fa01ce271896ca3e91c2cc53db`. It refines only the D1–D5 matrix in this document. Numeric gates remain proposals; no execution or implementation occurred.

The Owner's D1–D4 principle approvals and D5 block were recorded on 2026-10-20 in qualification/0_2_12/wp_e01_owner_decision_d1_d4_2026-10-20.md. That record adds only proposed freeze parameters and a future sequence; it does not change any production implementation or qualification status.

**V&V execution:** NOT RUN, as required. No tests were created or executed. No production code was modified. No solver, FEM, or backend was run.

## 13. Final numerical contract review — 2026-10-20

This section records the review state before the Owner partial-freeze decision in §14. Where its proposals or status differ, §14 and the linked dated Owner record govern.

The [final numerical contract review](wp_e01_final_numerical_contract_review_2026-10-20.md) is the current Owner-review package for D1-D5. It preserves the Owner-approved D1-D4 principles and the D5 block. It does not freeze numerical thresholds, checkpoint schema, or energy-output semantics.

The detailed parameter rows in §9.1 remain historical proposals and are superseded where the final review makes a more exact recommendation. In particular:

- The current load-control scale includes a force-unit floor of 1.0; it does not implement the approved physical F_ref/F_abs form. The proposed τ_R=1e-8 remains unapproved.
- A halving search with 12 reductions does not sample α_min=1e-4. The final review gives consistent alternatives; no line-search profile is frozen.
- The proposed 25-iteration limit must be defined as correction updates or residual evaluations. The current Newton loop counts residual evaluations.
- The E01 checkpoint policy must bind formulation, constitutive state version and stable element/quadrature-point identity while preserving WP10 v1/v2 history.
- The J2 C_ref proposal K+2μ is superseded by the tensor-action recommendation max(3K, 2μ). Both are proposals; the tangent remains blocked.

**Pre-partial-freeze decision status:** Newton numerical profile, checkpoint contract, J2 energy contract, and tangent V&V protocol were READY_FOR_OWNER_FREEZE as decision packages. WP_E01_A_B_SCIENTIFIC_FREEZE remained NOT_YET_APPROVED; all unapproved values remained PROPOSED; implementation, numerical V&V and native FEM remained unauthorized; WP-E01 remained OPEN / EXPERIMENTAL_TARGET.

## 14. Owner partial freeze — 2026-10-20

The [Owner partial-freeze decision record](wp_e01_owner_partial_freeze_newton_checkpoint_2026-10-20.md) and updated [final numerical contract review](wp_e01_final_numerical_contract_review_2026-10-20.md) supersede the pre-freeze proposals in §13 only for explicitly approved items. The Owner approves, for bounded experimental incremental WP-E01-A/B routes: 25 applied Newton correction updates per attempt with a residual check after every update; Armijo `c1=1e-4` only when a selected merit has a verified descent direction; cutback factor `beta=0.5` after complete rollback; a global limit of 25 rejected attempts per complete load path; and the stated checkpoint invariants. This does not approve an Armijo merit function, search schedule, retry-class map, minimum increment, endpoint rule, checkpoint schema/identity/migration policy, stronger physical interpretation of the legacy `plastic_dissipation` accumulator, new J2 energy fields, or D5 threshold. The existing Newton loop does not yet meet the approved correction-count semantics. D5 remains `BLOCKED_PENDING_INDEPENDENT_EVIDENCE`; WP-E01 remains `OPEN / EXPERIMENTAL_TARGET`. No implementation, executable tests, numerical V&V, solver/FEM execution, qualification promotion, or release action is authorized.

## 15. Final open decisions — 2026-10-20

This section records the decision-preparation status before the latest Owner partial freeze. The subsequent §16 and [dated Owner partial-freeze record](wp_e01_owner_partial_freeze_ab_contract_2026-10-20.md) govern current statuses. The [final open-decision matrix](wp_e01_final_open_decisions_2026-10-20.md) remains the source for open proposals and blockers. No Full Newton validation claim, implementation, numerical V&V, native FEM, qualification promotion, merge, or release is authorized.

## 16. Owner partial freeze — 2026-10-20

The dated [Owner partial-freeze record for WP-E01 A/B](wp_e01_owner_partial_freeze_ab_contract_2026-10-20.md) and the [updated decision matrix](wp_e01_final_open_decisions_2026-10-20.md) record the latest partial freeze. They preserve D1–D4 and the approved 25-correction, `c1=1e-4`, `beta=0.5`, global 25-rejection and transaction decisions. The bounded alpha schedule is accepted as an experimental control profile, but merit/descent verification and line-search failure actions remain open. `tau_R=1e-8` remains proposed; missing case force scales block the route. The normalized path and case-declared minimum-increment requirement are recorded, while retry classes and endpoint tolerance/rule remain open. The checkpoint direction is additive and fail-closed, but no exact schema or migration is approved or implemented. New public J2 energy fields are deferred, and the historical `plastic_dissipation` endpoint trapezoid is preserved. `J2_TANGENT_CONSISTENCY` remains `BLOCKED_PENDING_INDEPENDENT_EVIDENCE`; no J2 Full Newton validation, implementation, numerical V&V, native FEM or qualification promotion is authorized. WP-E01 remains `OPEN / EXPERIMENTAL_TARGET`.

## 17. WP-E01-A final contract proposal — 2026-10-20

The focused [WP-E01-A Newton contract proposal](wp_e01_a_final_contract_proposal_2026-10-20.md) records the contract progression. Its earlier proposal status is superseded by the final decision in §20.

## 18. Prior WP-E01-A residual approval — historical state

This section records the earlier residual-only approval before the final A–D freeze. Its residual equation and constraint boundary remain approved; its following “remaining decisions” status was superseded by §20 and the dated [Owner scientific-freeze record](wp_e01_a_owner_scientific_freeze_2026-10-20.md).

## 19. Prior WP-E01-A final recommendations — historical state

This section records the A–D recommendations before Owner approval. They are no longer pending approval; the final experimental contract and source-readiness findings are in §20 and the linked [Owner decision matrix](wp_e01_a_final_owner_decision_matrix_2026-10-20.md).

## 20. WP-E01-A scientific freeze — Owner decision 2026-10-20

This is the current WP-E01-A status overlay and supersedes earlier `OPEN`, `PROPOSED`, or `READY_FOR_OWNER_APPROVAL` statements about WP-E01-A in §§1–19. Earlier text remains historical context. It does not change WP-E01-B’s D5 block or approve E01-C/D/E, implementation, numerical execution, or qualification.

The [Owner decision record](wp_e01_a_owner_residual_approval_2026-10-20.md), [frozen experimental contract](wp_e01_a_final_contract_proposal_2026-10-20.md), and [A–D decision matrix](wp_e01_a_final_owner_decision_matrix_2026-10-20.md) now consistently record the approved residual and constraint contract, 25-correction count with post-correction residual check, derivative-certified Armijo merit and 13-trial sequence, normalized minimum increment and exact endpoint, WP10 v2-compatible additive checkpoint subrecord, full rollback, global once-only rejection ledger, and typed retry/terminal failure map.

| Status label | Current WP-E01-A meaning |
| --- | --- |
| `OWNER_APPROVED_EXPERIMENTAL` | Scientific control contract is frozen for the stated bounded route. |
| `NOT_IMPLEMENTED` | Current source has the deviations listed below; this freeze changed documentation only. |
| `NOT_VERIFIED` | No independent numerical V&V or route-specific Armijo derivative evidence was run. |
| `BLOCKED` | `J2_TANGENT_CONSISTENCY = BLOCKED_PENDING_INDEPENDENT_EVIDENCE`; no Full Newton J2 validation claim. |

### Implementation-readiness checklist

- [ ] Replace the current force-unit floor with the approved predeclared physical `F_ref` and additive `F_abs` gate; retain fail-closed scale and constraint handling. **Source: NOT_IMPLEMENTED.**
- [ ] Check the residual after correction update 25. **Source: NOT_IMPLEMENTED.**
- [ ] Implement `φ=½||R_f/T_R||₂²`, verify `J_Rp` and finite negative descent independently for each enabled route, and apply exactly `α_k=2^-k`, `k=0,…,12`. **Source: NOT_IMPLEMENTED; evidence: NOT_VERIFIED.**
- [ ] Implement the relative minimum, one clipped exact endpoint, approved failure classes, complete rollback, and 25-entry global rejection budget. Current endpoint uses a tolerance; minimum/retry behavior differs. **Source: NOT_IMPLEMENTED.**
- [ ] Add the versioned E01-A attempt-intent and rejection-ledger metadata while preserving WP10 v2 transaction, identity, integrity, and historical restart behavior. **Source: NOT_IMPLEMENTED; WP10 base transaction/checkpoint mechanisms exist.**
- [ ] Under a separate future V&V authorization, verify route derivatives/Armijo inequality, Newton correction counting, endpoint/cutback/failure accounting, corruption/interruption handling, rollback, and restart equivalence against independent references. **Evidence: NOT_RUN.**

**Current verdict:** `E01_A_SCIENTIFIC_CONTRACT: FROZEN_EXPERIMENTAL`; `E01_A_IMPLEMENTATION: NOT_AUTHORIZED`; `E01_A_NUMERICAL_VNV: NOT_RUN`; `J2_TANGENT_CONSISTENCY: BLOCKED_PENDING_INDEPENDENT_EVIDENCE`; `WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET`.

No production source or executable test was changed or run. No numerical calculation, `solve_model`, FEM, solver, or backend was executed.

## 21. WP-E01-C1 source and verification-preparation overlay — 2026-10-20

This dated overlay updates the source inventory only for the C1 work recorded in [the finite-strain and residual-Jacobian review](wp_e01_c1_finite_strain_and_residual_jacobian_review_2026-10-20.md). It does not change any frozen E01-A control, E01-B principle, E01-D/E criterion, or scientific qualification status.

`src/solveur/materials/finite_strain_elastic.py` now contains isolated material-point StVK and isochoric/volumetric compressible Neo-Hookean response/tangent kernels. They are not exported by the materials facade, connected to `MaterialFactory`, element assembly, a solver route, or result serialization. The previous statement in §2 / §5.3 that no Neo-Hookean implementation was found remains accurate for the earlier source snapshot, but is superseded for the presence of this new material-point kernel only. No Neo-Hookean FEM route is implemented or verified.

The new kernel follows §5.3's isochoric/volumetric candidate, which remains a proposal and not an Owner-frozen material law. A distinct Lamé-log-J alternative has the same infinitesimal limit under consistent moduli but a different finite-strain response; it is not implemented. Owner approval is required before E01-C contract freeze or element integration. The existing TET4/HEX8 StVK routes and their `J <= 1e-10` code guards are unchanged; that guard is not an approved universal or physical `J_min`.

Two exact-hash-bound `NUMERICAL_UNIT` modules were prepared as NOT RUN: a direct independent six-mode synthetic residual/Jacobian J2 oracle and element-independent finite-strain material-point checks. After the separate Owner exact-path GO, the B6 module passed 10/10 and the C1 module passed 17/17; the scoped results and remediation history are recorded in the linked review's execution addendum. The proposed J2 tangent/plateau threshold carries forward B4's `1e-8` candidate and remains unapproved. `J2_TANGENT_CONSISTENCY` remains `BLOCKED_PENDING_INDEPENDENT_EVIDENCE`; the production Armijo certificate registry is unchanged. No finite-strain element assembly or FEM V&V was performed.

Updated disposition:

```text
RESIDUAL_JACOBIAN_ORACLE: VERIFIED_BOUNDED_SYNTHETIC
NEWTON_J2_SYNTHETIC: VERIFIED_BOUNDED_PREVIOUS_EVIDENCE (historical; not rerun)
J2_TANGENT_GATE: READY_FOR_OWNER_FREEZE (candidate only)
J2_TANGENT_CONSISTENCY: BLOCKED_PENDING_INDEPENDENT_EVIDENCE
FINITE_STRAIN_ELASTIC_FORMULATION: PROPOSED / INCOMPLETE
FINITE_STRAIN_CONSTITUTIVE_IMPLEMENTATION: IMPLEMENTED_BY_SOURCE (isolated material points only)
FINITE_STRAIN_MATERIAL_POINT_VNV: VERIFIED_BOUNDED
FINITE_STRAIN_FEM_VNV: NOT_RUN
ARMIJO_PRODUCTION_CERTIFICATE: NOT_VERIFIED
SCIENTIFIC_QUALIFICATION: NOT_ACQUIRED
WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET
```
