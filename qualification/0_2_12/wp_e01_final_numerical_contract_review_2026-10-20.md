# QF Solver v0.2.12 — WP-E01 final numerical contract review

- **Review date:** 2026-10-20
- **Scope:** WP-E01-A and WP-E01-B only
- **Disposition:** updated Owner-review package; the partial approvals recorded in §10 are frozen for the bounded experimental profile, while all explicitly open parameters and schemas remain unfrozen.

## 1. Baseline and review limits

- Agent B worktree: C:\wpc01-frictionless-public-integration-wt\wp-e01
- Branch: codex/qf-wp-e01-recovery-review-20261020
- Verified review-start HEAD: bbb80f1978b62ae098628fe140a4fb3cb68906d4; worktree clean.
- Canonical checkout: C:\wpc01-frictionless-public-integration, branch emptiesvoids-cloud/wp-c01-contact-aware-equilibrium-audit, HEAD 3c0e0492104375fa01ce271896ca3e91c2cc53db; worktree clean.
- The canonical qualification/0_2_12/ROADMAP.md points to the byte-preserved Owner-approved roadmap and records WP-E01 as OPEN / EXPERIMENTAL_TARGET. Neither canonical file was changed.
- Read the WP-E01 candidate and 2026-10-20 D1-D4 Owner decision record, source in src/solveur/core/nonlinear/{controls.py,load_control.py,driver.py,iteration.py,robustness.py,state.py,checkpoint.py,solver.py}, src/solveur/materials/solid.py, and solid result recovery. Reviewed WP08 R1/R3, WP09 directional-derivative/perturbation, and WP10 transaction/checkpoint/restart records named below.

Contract/evidence references: [WP08 R1 constitutive-state contract](wp08_r1_constitutive_state_contract.json), [WP08 R1 acceptance matrix](wp08_r1_vnv_acceptance_matrix.json), [WP08 R3 Newton report](wp08_r3_newton_convergence_report.md), [WP08 R3 tangent evidence](wp08_r3_tangent_evidence.json), [WP09 perturbation policy](wp09_perturbation_policy.json), [WP09 directional-derivative evidence](wp09_directional_derivative_evidence.json), [WP10 transaction contract](wp10_state_transaction_contract.json), [WP10 checkpoint identity/migration contract](wp10_checkpoint_identity_migration_contract.json), [WP10 restart evidence](wp10_restart_equivalence_evidence.json), [WP-E01 candidate](wp_e01_nonlinear_foundations_candidate.md), and [Owner D1-D4 approval record](wp_e01_owner_decision_d1_d4_2026-10-20.md).

The reviewed source and WP08-WP10 contract paths have no content differences from canonical HEAD 3c0e0492104375fa01ce271896ca3e91c2cc53db.

This is source and documentary review only. Existing WP08-WP10 reports are cited as bounded historical evidence, not as evidence generated in this review. No test, Python calculation, solver, backend, solve_model, or FEM was run. D1-D4 Owner-approved principles are preserved; D5 remains BLOCKED_PENDING_INDEPENDENT_EVIDENCE.

## 2. D1 — Newton residual, force scales, and final-state check

### 2.1 Existing behavior and exact proposed gate

The current load-control Newton engine forms the signed residual

**R_f = (f_target − f_internal)_f**

and reduces it to the free DOFs. Fixed-DOF residuals are reported as reactions and are excluded from that Newton norm. The norm is the Euclidean 2-norm. The sign used by static_equilibrium_summary is the opposite, internal minus external; the norm is unchanged, but the stored sign must remain explicit.

The source currently normalizes by max(‖f_target,f‖₂, force_scale, 1.0) and accepts when the resulting ratio is at most the configured relative tolerance. The load-control caller also builds force_scale using a floor of 1.0 in the model's force units. There is no separate physical F_abs. Thus the common source 1e-8 is paired with a dimensionful, unit-dependent floor. The current accepted increment is committed after a trial residual check; after the load history, solver.py reassembles internal force from the committed material states and writes an equilibrium audit.

Preserve the Owner-approved definition:

**S_F = max(‖f_target,f‖₂, F_ref)**

**ρ_R = ‖R_f‖₂ / S_F**

**Accept equilibrium iff ρ_R ≤ τ_R + F_abs/S_F**

Equivalently, accept iff **‖R_f‖₂ ≤ τ_R S_F + F_abs**. For supported solid TET4/HEX8 routes, all reduced mechanical equations are translational force equations, so these norms and scales have force units (for example, N); τ_R is dimensionless. A route with mixed force and moment equations cannot use one unweighted Euclidean norm without a separately defined unit/scale convention.

### 2.2 Two defensible reference-scale policies

| Policy | Definition fixed before solving | Strength and risk |
| --- | --- | --- |
| **Load-pattern envelope — recommended for proportional E01 paths** | Write the free external load as f_target(λ)=Σ_j a_j(λ)p_j. Choose fixed, declared reference coefficients a_j,ref from the prescribed path, and set F_ref = Σ_j |a_j,ref| ‖p_j,f‖₂. For a single normalized pattern this reduces to its unfactored free-load norm. If this envelope is zero, require a separately declared positive physical F_char. | Force units; independent of the observed residual and resistant to cancellation between load patterns. The sum is a conservative envelope and can over-scale a route with many non-coincident load maxima, so the load decomposition and reference coefficients must be recorded. |
| **Owner-declared characteristic force** | Set F_ref = F_char > 0 from the model/route's stated characteristic force before solving; bind its value, units, source and route ID to the run. | Works for nominally unloaded or initially stressed cases and for load patterns whose decomposition is unavailable. It can falsely pass if the chosen characteristic force is unrelatedly large. |

Do not define F_ref from the residual, the current correction, or a changing internal-force norm. Those scales are solution-dependent and can make a poor equilibrium appear better as the iteration evolves. The current numerical 1.0 floor is not a physical reference policy.

F_abs is an absolute allowable free-force imbalance in the same force units. Two defensible policies are: (1) a route/model-specific physical imbalance allowance F_allow supported by the force-assembly and linear-solve error budget; or (2) F_abs = η_abs F_ref, where η_abs is a separately declared dimensionless absolute-floor fraction. The first gives an independently stated absolute requirement; the second scales covariantly with coherent unit changes. Neither may be inferred from an observed residual. If no absolute floor is justified, choosing zero is mathematically explicit but may reject roundoff-limited states. Owner must select the policy and its value.

### 2.3 Symbolic acceptance examples and edge cases

These are algebraic examples only; no numerical values were evaluated.

1. **Load-dominated single pattern.** Let f_target,f=λp_f, F_ref=‖p_f‖₂, and suppose ‖λp_f‖₂ ≥ F_ref. Then S_F=‖λp_f‖₂; a residual R_f=ε λp_f is accepted exactly when |ε| ≤ τ_R + F_abs/‖λp_f‖₂.
2. **Near-zero or zero external load.** If ‖f_target,f‖₂ ≤ F_ref, then S_F=F_ref. At nominal zero load, R_f=−f_internal,f; the criterion becomes ‖f_internal,f‖₂ ≤ τ_R F_ref + F_abs. Zero applied load is not an automatic zero residual and does not imply zero internal force or stress.
3. **Cancelling load patterns.** If f_target,f=a p_f+b q_f and the two terms nearly cancel, ‖f_target,f‖₂ can be small while each physical load contribution is large. The load-pattern envelope keeps F_ref tied to the uncancelled, preregistered components. The direct target-only scale does not.
4. **Mixed magnitudes within one force vector.** A global 2-norm is dominated by large components and can hide a local imbalance in a small-load region. For the solid routes, report per-component/element residual diagnostics. A max block-scaled norm could be an additional mandatory gate only after its blocks, scales and tolerances receive route-specific Owner approval; it must not silently replace the approved primary 2-norm.
5. **Badly scaled or mixed-unit DOFs.** TET4/HEX8 translation DOFs have a common force unit. If a route includes rotational, thermal, or other generalized equations, split by physical field and use declared block scales (or an explicitly approved weighting matrix); adding unlike units to the same raw 2-norm is not dimensionally valid.

The free-DOF reduction is mandatory. Reactions at prescribed DOFs are not included in R_f. The inspected Newton path reduces fixed DOFs; any affine constraint Cu=d must be represented in the reduced equations and checked separately in its own constraint units. Unsupported or inconsistent constraints are setup/admissibility failures, not convergence failures.

### 2.4 Tolerance, failure and post-commit policy

τ_R=1e-8 is **PROPOSED, NOT APPROVED**. It matches a common source default and a generic final-audit pass line, but that alone is not a scientific derivation. wp08_r3_newton_convergence_report.md records fixture-specific final residuals and explicitly says they are solver residuals, not estimates of constitutive, discretization, or physical error. WP08 R1-A12 reuses existing tolerances for its corrected route and is marked NOT_RUN in its frozen matrix. WP10's zero-load check uses the prior unit floor. None establishes τ_R for E01. A strict value may fail due to conditioning or assembly/linear-solve floors; a loose value may accept imbalance. Solver convergence is not independent FEM accuracy or qualification.

The generic audit currently reports a post-solve free residual with denominator max(‖f_external,f‖₂, 1.0) and has 1e-8 pass / 1e-6 warning bands. Separate global resultant force/moment checks use their own scales and 1e-10 pass / 1e-8 warning bands. Those audit observables and bands are not the proposed D1 gate and must not be silently substituted for it.

For the final committed-state check, use the final assembled internal force and the same free-DOF set, F_ref, F_abs, and τ_R that govern the increment. Evaluate equilibrium, admissibility, and result checks against the finalized detached trial before the atomic commit. Then commit exactly once and verify that the accepted digest and state identity match that audited candidate. The existing end-of-solve reassembly is useful evidence, but its current unit-floor audit does not implement this rule. If post-publication integrity or identity verification fails, do not publish a checkpoint or report success; restore the prior accepted snapshot (or invalidate the run without exposing the candidate as accepted) and fail explicitly. A candidate that fails the D1 audit must never be published as accepted.

Nonfinite residual, correction, tangent, required material state or result is terminal. Stagnation and divergence are failures, never convergence. The robustness controller defines a four-sample plateau and 1e-10 default relative change, but the ordinary load-control route constructs its controller with stagnation disabled. E01 adoption and any divergence trigger remain Owner choices. Max-iteration exhaustion and failed linear solve are nonconvergence; they are not evidence of acceptable equilibrium.

**Required independent V&V before a future numerical freeze:** independently reconstruct the free residual for an analytical spring/affine patch and a smooth J2 equilibrium; repeat under coherent force-unit changes; test zero/near-zero load, cancellation, constrained reactions, and residual concentration; verify that final committed-state reassembly satisfies the same gate. Preregister references, scales and threshold before execution. This review ran none of those checks.

## 3. D2 — Newton budget, Armijo line search and cutback

### 3.1 Existing code contracts and inconsistencies

- NonlinearSolverOptions has code defaults of 25 iterations, 1e-8 tolerance, line-search minimum 1e-4, 12 reductions and c=1e-4; adaptive stepping is opt-in. The Owner separately approves c1=1e-4, but that code default does not itself meet the approved verified-descent condition. The other cited defaults remain unapproved.
- The unified Newton loop iterates over residual/convergence evaluations. Successful convergence on evaluation n follows n−1 correction updates. If evaluation 25 is still unconverged, the loop can apply another correction and then exhaust without checking that updated state. The Owner-approved contract is **at most 25 correction updates per attempted increment**, with an initial residual evaluation and a residual check after every update; never declare failure before checking the state after update 25. The current loop does not yet implement this contract.
- The shared line-search controller tests α=1, 1/2, … and stops before a candidate below min_alpha. With 12 reductions it can test only through 2⁻¹²; that does **not** reach 1e-4. With 13 reductions, 2⁻¹³ is still above 1e-4, and the next halving would be below it. Thus the pair α_min=1e-4, 12 reductions does not sample the stated floor. It is bounded, but its smallest trial is the reduction-count limit, not α_min.
- line_search_c=1e-4 is accepted by the shared controller as a sufficient-decrease constant; the current norm-merit condition is ‖R(α)‖₂ ≤ (1−cα)‖R(0)‖₂. The method does not test a directional derivative. An experimental “existing” profile instead uses strict decrease, no Armijo constant, and different reduction settings. Do not mix those behaviors implicitly.
- Adaptive controls use load-factor increments, cutback 0.5, growth 1.5, default maximum cutbacks 25 and min(1e-4, initial_increment). The Owner now approves factor 0.5 and a global limit of 25 rejected attempts for the bounded experimental profile; existing defaults are compatibility evidence, not implementation or qualification evidence. The rejected count is cumulative across the solve and carried in accepted continuation metadata; the terminal rule is after the Nth rejection, with no N+1 attempt. The configured minimum remains open.

### 3.2 Bounded experimental profile: partial Owner freeze and open details

The Owner's dated [partial-freeze decision](wp_e01_owner_partial_freeze_newton_checkpoint_2026-10-20.md) approves a maximum of 25 correction updates, Armijo `c1=1e-4` conditional on verified descent, cutback `beta=0.5`, a global limit of 25 rejected attempts, and the checkpoint invariants. The exact merit and search schedule, retry classes, minimum increment, target rule, and schema remain open. The remaining proposals below are not frozen.

One prior proposed profile restricts load paths to quasi-static proportional loading parameterized by a dimensionless path coordinate λ over [λ₀, λ_t], with applied force f_ext(λ). That route boundary remains **PROPOSED**, not part of this partial freeze. Arc length, contact, buckling/postbuckling, finite-strain multiplicative J2, and general nonlinear dynamics remain outside the WP-E01-A/B scope stated in the earlier WP-E01 mandate.

1. **Fixed baseline:** use the preregistered load-factor sequence; no automatic growth or cutback. Each increment accepts only after D1, material admissibility and state/result checks. Failure is reported at the failed factor.
2. **Adaptive cutback experiment:** start from the last accepted factor and proposed increment. On an explicitly permitted retryable failure, first restore the exact last accepted composite state; then use the Owner-approved `Δλ_new=0.5 Δλ_old`. Stop after 25 rejected attempted increments over the complete load path; do not start attempt 26, and do not reset the count at an accepted increment. Continuation across restart must not evade the global limit, although its checkpoint representation remains open. Automatic growth and the detailed fixed/adaptive route profile remain open; the earlier no-growth suggestion is not an approval.
3. **Minimum increment:** prefer Δλ_min=η_min |λ_t−λ₀|, a dimensionless fraction of the declared path span, over min(1e-4, Δλ₀). Candidate η_min=1e-4 is unapproved. Require the initial increment to be at least this minimum. Retry only when the next cutback is at least the minimum; equality may be permitted if declared. This avoids hiding a zero/near-zero lower bound inside the initial step. A route may instead select an absolute dimensionless Δλ_min, but must bind it to a normalized path and justify it independently.
4. **Line search when explicitly selected:** the Owner approves the scalar `c1=1e-4` only for a selected merit function with a verified descent direction. A generic Armijo condition is `φ(u+αp)≤φ(u)+c1 α Dφ(u)[p]`, with `Dφ(u)[p]<0`; the merit function, derivative computation, line-search selection, and response when descent is absent remain open. The dimensionless residual merit `φ=½‖R_f/S_F‖₂²` is one proposal only, not an approved function. Every candidate must be recomputed from the same accepted constitutive state.
5. **Backtracking schedule:** the prior 12-reduction proposal, the 14-reduction alternative, and `α_min=1e-4` all remain proposals. No backtracking factor, minimum alpha, maximum reductions, or boundary behavior is approved. The selected schedule must be internally consistent and independently checked after separate authorization.
6. **Endpoint:** on the last clipped step assign the canonical requested λ_t value, rather than inferring target attainment from floating addition or the existing 1e-12 loop guard. Success requires accepted load-path identity equal to the requested target identity. Reaching the minimum step, retry budget or iteration budget short of λ_t is failure.

### 3.3 Failure classification

The existing canonical map contains retryable, terminal, and Owner-policy-dependent classes, but the Owner has not approved an E01 retry map. Any earlier suggested automatic retry list remains **PROPOSED**. Cutback may occur only after full rollback and only for a class later selected by the Owner. The terminal behavior for nonfinite values, invalid geometry/material state, incompatible constraints, corruption, checkpoint failure, unknown classes, exhausted rejection budget, and inadmissible next increment must be explicit before implementation. D5 remains blocked; a retry cannot imply tangent correctness.

There is a current classification hazard: the shared line-search loop converts ValueError/FloatingPointError from a trial evaluation to infinite merit; if every candidate fails it can report LINE_SEARCH_FAILURE, which the existing continuation map treats as retryable. Typed NumericalConvergenceError generally propagates. Before E01 use, distinguish a deliberately recoverable alpha-dependent trial-admissibility event from nonfinite/invalid material or assembly state; only the former may be reduced/retried. The current untyped conversion is not evidence that every such failure is retryable.

**Required independent V&V:** test every budget boundary, line-search sufficient-decrease/descent behavior, retryable and terminal failure classes, accepted-state digest before/after each rejection, minimum-step equality and below-minimum refusal, cumulative retry behavior through restart, and exact endpoint success/failure. Compare fixed and cutback paths at common accepted factors. None was executed.

## 4. D3 — Transaction and checkpoint contract

### 4.1 Existing behavior and evidence boundary

The Owner explicitly approves the lifecycle invariants in the [partial-freeze decision](wp_e01_owner_partial_freeze_newton_checkpoint_2026-10-20.md): isolate trial state; keep accepted material history unchanged through failed iterations; fully rollback rejected increments; commit once on acceptance; rollback all mechanical, constitutive, accumulated-output, and relevant solver-history state; prevent rejected-state contamination; and independently verify restart/checkpoint consistency. These are invariants only; no schema or serialization policy is approved. NonlinearState has outer state schema 1 and carries displacement, load factor, material/contact/continuation mappings and accepted-step metadata. NonlinearStateTransaction detaches a trial, marks it TRIAL, records the accepted digest, checks accepted-state integrity, validates a detached replacement and atomically replaces the accepted composite once. Rollback checks the accepted digest and discards the trial. The accepted-state accessor returns the mutable accepted object; digest checks detect changes during an open trial but do not make all external access read-only.

checkpoint.py implements checkpoint schema v2, deterministic component/composite SHA-256 digests, topology checks, accepted-state markers, canonical metadata identity and an atomic temporary-file replacement path. New bound v2 metadata includes a digest; SHA integrity is not authentication. The current E01 small-strain J2 route does not yet have an explicit constitutive state version/formulation identity mapping comparable to corrected-corotational J2. Stable E01 element/quadrature-point ordering must be confirmed in the E01 topology identity; do not infer it from a file name or array position.

The WP10 contract and restart record report bounded PASS for transaction commit/rollback, trial checkpoint refusal, identity mutation refusal and restart equivalence. They explicitly limit the claim: schema-v1 is readable for inspection but nonresumable/nonmigratable; existing v2 without component identities remains bound only by its historical full signature and topology, with no retroactive identity claim; bitwise_claim=false. These are recorded WP10 results, not rerun here and not general E01 qualification.

### 4.2 Proposed E01-compatible checkpoint policy

1. Treat the accepted composite Z_n=(u_n, λ_n, step_n, z_n, controller_n, provenance_n) as one logical state. Every line-search/Newton candidate starts from the same accepted state. A failed iteration or increment leaves every accepted field unchanged. One accepted increment replaces the composite exactly once, only after equilibrium, admissibility and result checks. Persist rejection diagnostics as controller provenance, not as constitutive accumulation.
2. Identify material state by stable element ID, element family, integration-rule ID, quadrature-point ID/order, material ID and a digest of E, ν, σ_y0, H plus units; bind formulation/kinematics, state-variable schema and component order. Persist the exact accepted variables required to resume: plastic strain, accumulated equivalent plastic strain, stress/history values the integrator consumes, and any Owner-approved work/storage/dissipation fields.
3. Reuse WP10's integrity envelope and fail-closed rules. For new E01 states, bind the small-strain J2 formulation/state version, element/IP topology, material parameters, load path/accepted factor, solver method and numerical policy/schema identities. Use the current v2 representation only if it can bind all these facts without changing the meaning of historical v2; otherwise define a new identity/checkpoint version. Never retrofit identities onto old records.
4. Checkpoint only a transaction-attested accepted state; refuse trial-marked, unmarked-new, partial, corrupt, unknown-version, identity-mismatched or unsupported states. Preserve v1 inspection-only refusal and existing v2 matching rules. No migration is permitted until an explicit map and independent physical/constitutive compatibility proof are approved. Do not rewrite historical archives.
5. For restart, require logical equality of accepted load identity, displacement and every constitutive variable, plus matching state and model identities. Require deterministic accepted-step/rejection/next-increment provenance. Exact digests are expected for deterministic canonical payloads in the same schema; do not promise cross-platform bitwise output. Any floating-field equivalence tolerance remains to be specified and independently checked.
6. Bind code/formulation provenance and the policy/schema versions. Hashes detect accidental corruption and mismatched metadata; they do not authenticate authorship or prevent intentional modification.

**WP10 compatibility classification:** detached trial/rollback, atomic commit, markers, validation and hash machinery are implemented and have bounded historical verification. The load-control bridge returns the accepted composite through compatibility outputs (displacement and material-state mappings); E01 must verify that the externally visible publication remains logically atomic. E01-specific formulation/state identity, quadrature ordering proof, accepted accessor immutability, restart tolerances and migration are not approved or independently demonstrated. A checkpoint-write failure is terminal for the run and never a reason to cut back a physical increment.

**Required independent V&V:** compare every accepted state component before/after rejected Newton and cutback; verify one commit per accepted increment; test stable element/IP and material identity mutations; checkpoint only accepted state; exercise corruption, unknown/mismatched version and v1/v2 legacy behavior; compare continuous and restarted load histories after retry at common accepted factors. No such E01 checks were run.

## 5. D4 — J2 state, work and energy contract

### 5.1 Approved constitutive convention

Use the Owner-approved small-strain associative isotropic J2 return map. With tensorial stress σ, deviator s=dev(σ), q=√(3/2 s:s), accumulated equivalent plastic strain α, initial yield σ_y0>0, shear modulus μ>0, bulk modulus K>0 and isotropic hardening H≥0:

- Trial stress: σ_trial=C:(ε−εᵖ_n).
- Trial yield: f_trial=q_trial−(σ_y0+H α_n).
- Elastic branch: if f_trial≤0, retain εᵖ, α and work history; return the trial stress and elastic tangent.
- Plastic branch: Δγ=f_trial/(3μ+H), Δα=Δγ, Δεᵖ=(3/2)Δγ s_trial/q_trial; update the deviator radially and leave the mean stress unchanged.
- H=0 is perfect plasticity; H>0 is linear isotropic hardening. Unloading is elastic. Reloading/reversal uses the same isotropically expanded surface; there is no kinematic hardening.

The source implements this radial predictor/corrector. It switches to elastic at f_trial≤0; there is no transition tolerance or substepping rule. The transition is therefore a branch boundary, not a place with one required classical tangent.

Voigt order is [xx, yy, zz, xy, yz, xz]; strain and plastic strain use engineering shear, stress uses tensorial shear. E, σ_y0, H, μ, K have stress units; ε, εᵖ, α, Δγ are dimensionless. Energy densities/work per reference volume use stress units (Pa = J/m³ in coherent SI); integrated energy uses J.

### 5.2 Exact meaning of current and proposed energy quantities

The current material state stores `plastic_dissipation`. On each plastic update source computes

**A_{n+1}=A_n + ½(σ_n+σ_{n+1}):Δεᵖ**

using tensorial stress and engineering-strain Voigt work conjugacy. This records the source's cumulative endpoint-trapezoid update formula for the stress/plastic-strain contraction. Preserve its name, formula and historical output. This review does not assign it a stronger physical interpretation, claim equivalence to the exact path integral for general histories, or identify it with thermodynamic dissipation. Do not migrate, rename, or alias it.

For the ideal associative rate-independent law, a distinct continuous-path thermodynamic definition is:

- hardening free energy: ψ_h(α)=½Hα²;
- plastic stress work: ΔW_p=∫σ:dεᵖ;
- thermodynamic dissipation: ΔD=ΔW_p−Δψ_h=σ_y0 Δα≥0;
- under the yield-surface path, ΔW_p=σ_y0Δα + ½H(α_{n+1}²−α_n²).

These identities define physical quantities for the approved constitutive model. They do not assert that the endpoint-trapezoid accumulator equals those path integrals at finite increment. Any new fields—work increment/cumulative work, hardening-energy density, dissipation increment/cumulative dissipation—must be separate, versioned, and calculated under an explicitly approved integration/path convention. Their AVAILABLE, NOT_COMPUTED, or UNAVAILABLE reason, integration-point location, units, measure, recovery and persistence must be explicit. Missing older values are unavailable, not numeric zero.

The source's point/element result serializer exposes stress/strain, α, plastic strain, multiplier and yield fields. The recovered material_state deliberately filters plastic_dissipation; load-step diagnostics can report its maximum. There is no current general public energy-field schema. Existing outputs therefore cannot be presumed equivalent to a new physical work/dissipation definition.

**Required independent V&V:** separately implemented tensor material oracle from the frozen equations; compare stress, plastic strain, α, yield state and energy identities on elastic, monotone plastic, unloading, reloading/reversal and noncoaxial histories from fixed incoming states. Check H=0, H>0, nonnegative ΔD, and distinguish the current trapezoidal estimator from exact model-path quantities. No evidence was generated by this review.

## 6. D5 — independent tangent protocol; remains blocked

### 6.1 Reference, branches and Voigt mapping

Keep **J2_TANGENT_CONSISTENCY = BLOCKED_PENDING_INDEPENDENT_EVIDENCE**. The source forms a basis-response tangent in engineering-strain/tensorial-stress Voigt convention and returns its symmetrized value. Symmetry of that returned value is guaranteed by the final averaging operation; it is not evidence that the unsymmetrized derivative is symmetric or correct.

For each preregistered symmetric tensor direction D with ‖D‖_F=1, encode engineering strain direction as (D_xx,D_yy,D_zz,2D_xy,2D_yz,2D_xz). Decode stress actions into full symmetric tensors before taking Frobenius norms. Compare the production tangent action with an independently authored tensor return-map oracle:

**FD_h(D; z_n) = [σ_ref(ε+hD; z_n)−σ_ref(ε−hD; z_n)]/(2h)**

The incoming accepted state z_n is held fixed and copied independently for the plus and minus returns. Cover the six component directions and preregistered volumetric, deviatoric, normal/shear mixed directions. Do not reuse production return helpers in the oracle.

- **Elastic branch:** select states safely inside yield; compare with C_e=K I⊗I+2μP_dev.
- **Smooth plastic branch:** select states with both perturbed returns on the same plastic branch; compare production action to independent central differences and an independently derived radial-return derivative.
- **Yield transition:** no single classical derivative is required. Use one-sided branch-preserving limits against the corresponding elastic/plastic references. A cross-branch central difference is NONSMOOTH_DIAGNOSTIC, never a smooth-tangent pass or automatic failure.
- **Loading/reversal histories:** prepare states independently, then freeze each incoming state for all tangent perturbations. Confirm exact state immutability.

### 6.2 Error scale, perturbation and plateau proposal

Use the absolute action error E_abs(h,D)=‖C_prod:D−FD_h(D)‖_F in stress units. A physically interpretable independent material scale for the tensor Frobenius map of isotropic elasticity is

**C_ref=max(3K, 2μ)**

in stress units: these are the volumetric and deviatoric eigenvalue scales of the isotropic elastic tensor. This replaces the earlier K+2μ proposal in the candidate for this review. Choose a positive, Owner-declared absolute stress floor σ_abs from the independent oracle/roundoff budget, not from the measured tangent error. Then use

**e_T(h,D)=E_abs(h,D) / max(C_ref ‖D‖_F, σ_abs)**.

Report absolute and normalized error. The proposed sweep is h_j=h_ref 10⁻ʲ, j=0,…,6, with dimensionless h_ref selected and recorded per fixture before inspecting tangent errors. The fixture must be chosen far enough inside a smooth branch that all intended plus/minus samples remain on it; branch margin and representability must be recorded. Transition fixtures use one-sided sweeps.

Define adjacent plateau difference

**p_j=‖FD_hj−FD_hj+1‖_F / max(C_ref ‖D‖_F, σ_abs)**.

Proposed pass structure: on every mandatory smooth branch/direction, require e_T≤τ_T at three consecutive geometric steps and p_j≤τ_plateau on the two adjacent comparisons spanning those steps. h_ref, σ_abs, τ_plateau, and exact range remain unapproved. If no branch-preserving plateau exists, classify FINITE_DIFFERENCE_UNRESOLVED; do not pass using the best-looking step. A branch change is BRANCH_CROSSING; a plateau with excessive derivative error is TANGENT_MISMATCH; a nonfinite/failed reference is INVALID_RESPONSE.

The previous candidate τ_T=2e-5 is **PROPOSED, NOT APPROVED**. The same number appears in WP08/WP09 for a different corrected-corotational element-force tangent metric, scaled by F_char/L_char; it is not inherited for this material-point derivative. It may remain a candidate only if a separately authored oracle demonstrates a stable finite-difference floor materially below it over the preregistered branch/direction set and the Owner accepts the error budget. No such E01 evidence exists.

The production tangent is symmetrized in source before exposure. Therefore a meaningful raw-skew gate requires a future diagnostic of the unsymmetrized matrix or an independently reconstructed raw derivative. Do not add an arbitrary symmetry threshold; report the raw skew in a work-conjugate tensor norm when available.

### 6.3 Claims that must remain separate

1. **Tangent implementation consistency** asks whether the returned local material tangent differentiates the specified stress update on a smooth branch.
2. **Constitutive stress accuracy** asks whether the stress/state update matches an independent material oracle.
3. **Newton convergence** asks whether the assembled free equilibrium residual meets D1 for the discrete model.
4. **FEM accuracy/qualification** asks whether the discretization and physical model meet independent accuracy/validation requirements.

None implies another. WP08/WP09 bounded element-force results do not verify this small-strain J2 tangent. This document claims no PASS and does not validate Full Newton.

## 7. Final Owner decision matrix (A-L)

The A-L matrix below is retained as review history. Its remaining open rows are superseded by the final consolidated recommendations in §11 and [WP-E01 final open decisions](wp_e01_final_open_decisions_2026-10-20.md). The Owner-approved rows remain authoritative through the dated Owner decision record.

“Ready for Owner freeze” below means a complete recommendation is prepared for decision; it does not mean an approval or a frozen value. Every unapproved value remains **PROPOSED**.

| ID / decision | Exact proposal, units and applicable E01 route | Existing compatibility and sensitivity | Mandatory gate / diagnostic and independent V&V | Recommendation; Owner decision |
| --- | --- | --- | --- | --- |
| **A. Newton τ_R** | ρ_R≤τ_R+F_abs/S_F; dimensionless; quasi-static solid E01-A/B. Candidate 1e-8. | Common code value, but current unit floor invalidates its transfer as a physical-scale contract. Too loose accepts imbalance; too tight hits conditioning/roundoff. | Mandatory primary gate. Independent analytical/patch force balance, load rescaling and threshold sensitivity. | **REVISE.** Decide τ_R; 1e-8 stays proposed. |
| **B. F_ref** | Positive fixed force scale; recommended sum of declared free load-pattern contribution norms, or Owner-declared F_char; force units. | Current code uses load norm plus 1.0; target-only scaling can collapse under cancellation. Overlarge reference can false-pass. | Mandatory denominator scale. Independent zero-load, mixed-load and coherent unit-rescaling references. | **REVISE.** Choose source/decomposition and value per route. |
| **C. F_abs** | Physical allowable free residual F_allow, or η_abs F_ref; force units (η_abs dimensionless). | Current engine has no separate absolute term; audit's unit floor is not equivalent. An oversized floor masks error. | Mandatory term only if selected; zero is explicit alternative. Independent force-error budget and near-zero-load reference. | **REVISE.** Choose policy/value and provenance. |
| **D. Newton limit** | **Owner-approved:** at most 25 applied corrections per attempted increment; evaluate the initial residual and residual after each correction, including correction 25. Count; E01-A/B bounded experimental routes. | Current loop bounds residual evaluations; it may apply an unchecked final update. Merely setting 25 does not implement the approved count. | Mandatory bounded failure gate. Independently verify count semantics and the final post-update residual check. | **OWNER_APPROVED_25.** Implementation must be changed only after separate authorization. |
| **E. Line-search merit/parameters** | **Owner-approved scalar:** `c1=1e-4`, only with a selected merit and verified negative directional derivative. Merit, derivative, backtracking factor, `alpha_min`, and budget are open. | Current controller/defaults do not prove the selected merit has descent; prior 12/14 reductions and `alpha_min=1e-4` are proposals. | Gate only for routes selecting Armijo. Independently verify derivative and sufficient decrease, state isolation, and no-descent handling. | **PARTIAL OWNER APPROVAL.** Choose remaining search policy; c1 alone does not define Armijo. |
| **F. Cutback/retry** | **Owner-approved:** `beta=0.5`; at most 25 rejected attempts globally per complete path; rollback before retry; no attempt 26. | Source uses factor 0.5 and global count with rollback, but E01 retry classes and minimum increment remain open. | Retry only after exact rollback and an explicitly permitted class. Verify full-state digest and global-budget boundaries. | **PARTIAL OWNER APPROVAL.** Retry/terminal class map remains open. |
| **G. Minimum increment/endpoint** | No approved minimum or target tolerance. Earlier `Δλ_min=η_min|λ_t−λ₀|`, `η_min=1e-4`, and endpoint proposals remain open. | Existing minimum and `1e-12` loop guard are implementation details, not Owner approval. | Independently check equality/below-minimum, clipped final increment, and target attainment. | **OPEN.** Choose minimum/equality and endpoint rule. |
| **H. Transaction/checkpoint** | **Owner-approved invariants:** trial isolation, unchanged accepted history on failure, full rollback, exactly-once commit, complete state coverage, no contamination, independently verifiable restart. Schema and identity are open. | WP10 machinery has bounded historical evidence. Preserve existing v1/v2 behavior; E01 formulation/IP identity, schema, migration and restart tolerances are unapproved. | Independently compare all state components after rejection, commit count, identity mismatch, corruption, and restart. | **PARTIAL OWNER APPROVAL.** Choose E01 schema, identity, versioning, migration and restart criteria. |
| **I. J2 work/storage/dissipation** | Preserve the existing update formula and `plastic_dissipation` name. Do not claim it equals a continuum plastic-work integral or thermodynamic dissipation. The distinct model energy definitions remain proposals. | The source applies an endpoint trapezoid to stress contracted with the plastic-strain increment; recovery filters the field from public material state. Any stronger interpretation or reclassification risks changing historical meaning. | Independent constitutive-path accounting and energy oracle; preserve prior outputs and availability. | **OPEN** beyond the documented source computation. Decide any stronger interpretation and new field names, accumulation, recovery and migration. |
| **J. Tangent norm/scale** | Tensor action error e_T=E_abs/max(C_ref‖D‖,σ_abs); C_ref=max(3K,2μ) in stress units; E01-B smooth branches. | Current tangent is symmetrized; K+2μ prior scale is superseded. Incorrect Voigt shear weighting can distort error. | Mandatory D5 gate after approval. Independent tensor oracle, correct shear mapping, raw/pre-sym diagnostic. | **APPROVE metric form as a proposal; REVISE σ_abs and raw-tangent reporting.** Owner choice required. |
| **K. Perturbation/plateau** | h_j=h_ref10⁻ʲ, j=0,…,6; require three error-qualified steps and two plateau comparisons; one-sided transition diagnostics; dimensionless strain. | WP09 uses element length-scaled force perturbations, not material strain; no direct threshold transfer. Too-large h truncates; too-small h rounds off or crosses yield. | Preregistered branch-aware protocol; independently authored stress oracle and fixed incoming state. | **REVISE.** Choose h_ref, branch margin, σ_abs, τ_plateau and exact step window. |
| **L. Tangent τ_T** | Proposed 2e-5, dimensionless; smooth-branch material action only. | Same number in WP08/WP09 measures a different element-force observable; no E01 material evidence. | Mandatory only after independent plateau and oracle agreement; transition is diagnostic. | **DEFER.** Do not freeze or promote D5. Owner must select a threshold only after evidence supports its attainable error floor. |

## 8. Minimum remaining Owner choices

The remaining decisions are consolidated in §11 and [WP-E01 final open decisions](wp_e01_final_open_decisions_2026-10-20.md). The 25-correction limit, `c1=1e-4`, `beta=0.5`, global rejection limit, and transaction invariants are already Owner-approved and do not need reapproval.

## 9. Status

- REPOSITORY_IDENTITY: VERIFIED
- WP_E01_D1_D4_OWNER_PRINCIPLES: PRESERVED
- WP_E01_D5_TANGENT: BLOCKED_PENDING_INDEPENDENT_EVIDENCE
- NEWTON_NUMERICAL_PROFILE: OWNER_PARTIAL_FREEZE_PRESERVED; remaining scale, line-search, retry and endpoint recommendations are READY_FOR_OWNER_DECISION.
- CHECKPOINT_CONTRACT: OWNER_INVARIANTS_PRESERVED; additive WP10-v2 identity proposal is READY_FOR_OWNER_DECISION.
- J2_ENERGY_CONTRACT: historical computations preserved; public-field deferral is READY_FOR_OWNER_DECISION.
- J2_TANGENT_VNV_PROTOCOL: READY_FOR_OWNER_DECISION as a preregistration proposal only; D5 remains blocked and no evidence or threshold approval is claimed.
- WP_E01_A_B_SCIENTIFIC_FREEZE: NOT_YET_APPROVED
- IMPLEMENTATION_AUTHORIZED: NO
- NUMERICAL_VNV_AUTHORIZED: NO
- NATIVE_FEM_AUTHORIZED: NO
- WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET

No tests, calculations, code, execution, qualification promotion, historical archive edit, merge or release action occurred. Stop for separate Owner approval of the remaining numerical criteria and checkpoint/output decisions.

## 10. Owner partial-freeze overlay — 2026-10-20

The [Owner partial-freeze record](wp_e01_owner_partial_freeze_newton_checkpoint_2026-10-20.md) is authoritative for decisions made after the initial A-L recommendation matrix above. It approves P1-P5 only: 25 correction updates with a post-update residual check, Armijo `c1=1e-4` conditional on verified descent, cutback `beta=0.5`, a global 25-rejected-attempt limit, and the listed checkpoint invariants. The prior matrix's D/E/F/H recommendations are superseded to that extent. Its other numerical proposals remain proposals/open; no merit function, search schedule, retry-class map, minimum increment, endpoint policy, checkpoint schema, J2 output semantics, or tangent threshold was frozen. The source loop does not yet implement P1 counting semantics. D5 remains blocked and WP-E01 remains open.

## 11. Final open-decision consolidation — 2026-10-20

The [final open-decision package](wp_e01_final_open_decisions_2026-10-20.md) is the current consolidated recommendation for unresolved WP-E01-A/B parameters and use boundaries. It preserves the D1-D4 principles and the Owner-approved experimental Newton/checkpoint profile; it does not freeze any new threshold, schema, output semantics or retry policy. It selects one proposed force-scale rule, one Armijo schedule, one normalized load-path policy, a backward-compatible WP10-v2 checkpoint proposal, deferral of new J2 public energy fields, and a branch-aware D5 verification protocol. Proposals remain subject to Owner approval. `J2_TANGENT_CONSISTENCY = BLOCKED_PENDING_INDEPENDENT_EVIDENCE`; `E01_A_B_COMPLETE_FREEZE = NOT_YET_APPROVED`; implementation, numerical V&V and native FEM remain unauthorized; WP-E01 remains `OPEN / EXPERIMENTAL_TARGET`.

## 12. Owner partial freeze — 2026-10-20

The later [Owner partial-freeze record for WP-E01 A/B](wp_e01_owner_partial_freeze_ab_contract_2026-10-20.md) supersedes this review's open-parameter statuses only for items explicitly accepted there. D1–D4 and earlier approved controls remain unchanged; the bounded alpha sequence is accepted as a control schedule, not a descent proof. `tau_R=1e-8` remains proposed; physical force-scale values are case-declared and missing values block execution. The merit/descent certificate, retry classes, endpoint tolerance/rule and exact checkpoint schema remain open. New public J2 energy outputs are deferred by Owner decision; historical `plastic_dissipation` semantics are preserved. D5 remains `BLOCKED_PENDING_INDEPENDENT_EVIDENCE`; no implementation, numerical V&V, native FEM, Full Newton qualification, merge or release is authorized. WP-E01 remains `OPEN / EXPERIMENTAL_TARGET`.
