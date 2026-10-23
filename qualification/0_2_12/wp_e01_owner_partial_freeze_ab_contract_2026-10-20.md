# QF Solver v0.2.12 — WP-E01 A/B Owner partial-freeze record

- **Owner decision date:** 2026-10-20
- **Scope:** WP-E01-A incremental Newton and WP-E01-B small-strain isotropic J2
- **Disposition:** partial experimental contract freeze; required definitions remain open where stated
- **Worktree:** `C:\wpc01-frictionless-public-integration-wt\wp-e01`
- **Branch:** `codex/qf-wp-e01-recovery-review-20261020`
- **Verified starting HEAD:** `7835b0cb120190296b9f93f12c64240527e1da0c` (clean)
- **Canonical baseline:** `C:\wpc01-frictionless-public-integration`, branch `emptiesvoids-cloud/wp-c01-contact-aware-equilibrium-audit`, HEAD `3c0e0492104375fa01ce271896ca3e91c2cc53db` (clean)
- **Canonical roadmap:** `qualification/0_2_12/ROADMAP.md`; unchanged, SHA-256 `48021A7773895C354806446AB89E317B968CFEE5F2618790F4487FBF11195A6D`

This record documents the current Owner mandate. It does not change the canonical roadmap, historical qualification records, WP-D01/WP-D02, production code, or any WP08–WP10 contract. Contract approval is not implementation correctness, V&V evidence, qualification, or execution authorization. WP-E01 remains `OPEN / EXPERIMENTAL_TARGET`.

## 1. Freeze ledger

| Area | Owner-approved / accepted for the bounded experimental contract | Status after this partial freeze | Still open or blocked |
| --- | --- | --- | --- |
| D1 equilibrium principle | Free-DOF equilibrium residual is mandatory; displacement correction is diagnostic. Keep `R_f=(f_target-f_internal)_f` and exclude fixed-DOF reactions. | **OWNER_APPROVED** principle | `τ_R` remains proposed; case-specific physical scales and any separate constraint residual tolerance are not numerically frozen. |
| Newton correction budget | At most 25 applied correction updates per attempted increment; initial residual is not counted; evaluate residual after correction 25 before failure. | **OWNER_APPROVED_25** | Implementation is not verified to follow this count; no implementation is authorized. |
| Armijo coefficient and schedule | `c1=1e-4`, conditional on verified descent. Use the accepted experimental candidate sequence `α_k=2^-k`, `k=0,…,12`; the last tested value is `1/4096`. | `c1`: **OWNER_APPROVED_1E-4**. Sequence: **OWNER_ACCEPTED_EXPERIMENTAL_PROFILE**. | The schedule does not prove descent. Merit function selection, directional-derivative/descent certificate, and failure-class actions remain **OPEN**; no unconditional acceptance or unrelated fallback. |
| Cutback and rejected attempts | `β=0.5` after complete rollback; no more than 25 rejected increment attempts per complete load path; rejection 25 terminates before attempt 26. | **OWNER_APPROVED** | Specific retryable/terminal failure classes remain **OPEN**. |
| Load-path parameterization | Use a normalized case path `λ∈[0,1]`; every case must declare a positive minimum admissible increment before execution. Stop explicitly if the next admissible retry cannot be formed. | **OWNER_ACCEPTED_REQUIREMENT**; no universal increment value | Case value/equality behavior, retry classes, final endpoint tolerance and target-acceptance rule remain **OPEN**. The same-path rejection count must survive restart. |
| Transaction lifecycle | Trial/accepted isolation; rejected work cannot mutate accepted history; rollback restores the last accepted composite; accepted state commits exactly once; restart consistency is independently verifiable. | **OWNER_APPROVED** invariants | No transaction implementation or new checkpoint schema is approved by these invariants. |
| Checkpoint direction | Additive, fail-closed extension direction that preserves WP10 v2 behavior. Required identity concepts include formulation/version, material and parameters, mesh/elements, integration points, accepted displacement/material state, accepted `λ`, rejection count, schema version and restart provenance. | **OWNER_ACCEPTED_DESIGN_DIRECTION** | Exact field names, identities, hashes, schema/version binding, serialization, migration, restart tolerances and compatibility specification are **PROPOSED / OPEN**. Schema is not implemented or fully approved. |
| J2 constitutive model | Preserve small-strain isotropic J2 radial return, associated flow, perfect plasticity (`H=0`) and linear isotropic hardening (`H≥0`), with transactional state. | **OWNER_APPROVED_PRINCIPLES** | No claim that a current implementation is independently verified follows from this approval. |
| J2 energy outputs | Defer new public energy fields. Preserve existing `plastic_dissipation` name, values, route-specific availability and reviewed endpoint-trapezoidal computation; do not equate it to thermodynamic dissipation. | **OWNER_APPROVED_DEFERRAL** | New public fields and any reclassification remain out of scope; no historical result changes. |
| J2 algorithmic tangent | Preserve `J2_TANGENT_CONSISTENCY = BLOCKED_PENDING_INDEPENDENT_EVIDENCE`. `τ_T=2e-5` remains proposed. | **BLOCKED** | Independent branch-aware derivative evidence is required before tangent-consistency or Full Newton claims. |
| J2 experimental use | Constitutive-point, independent radial-return and transaction/rollback experiments may be considered later. | **NOT AUTHORIZED** by this record | Each executable activity requires separate explicit Owner authorization. J2 Full Newton FEM and qualification are not authorized. |

## 2. E01-A — Newton residual and force-scale policy

The experimental target is:

```text
S_F = max(||f_target,f||_2, F_ref)
||R_f||_2 <= tau_R * S_F + F_abs
```

with `R_f=(f_target-f_internal)_f`, the free-DOF Euclidean force norm, and fixed-DOF reactions excluded. `τ_R=1e-8` is **PROPOSED**, not a demonstrated accuracy or qualification threshold. `F_ref` must be a physically meaningful, predeclared force scale independent of the observed residual; `F_ref>0`. `F_abs` must be declared for each case, nonnegative, measured in force units and independently justified by the allowed force imbalance and numerical error budget. These are fixed case inputs; `S_F` must be strictly positive. A missing or invalid scale blocks the experimental route: do not insert a unit-dependent floor or infer a scale from residuals/internal forces.

For a proportional or coupled load path, the recommended case-scale construction is the full-path envelope of declared free-load pattern contributions. A zero envelope requires a separate declared positive characteristic force. This is a **PROPOSED case-scale method**, not a universal value or route-independent numeric default; the case must record the load-pattern identity and scale provenance. Near-zero external load does not imply zero residual: test the same force gate against the declared physical scales. If the free-DOF set is empty, the zero norm is vacuous and cannot by itself establish equilibrium.

Prescribed DOFs are eliminated and checked as prescribed. Any non-eliminated constraint formulation requires its own admissibility definition and units; unsupported or inconsistent constraints fail closed. A constraint tolerance not already specified by the supported route remains **OPEN**. NaN/Inf in residuals, corrections, tangent, material state or required results is a terminal numerical failure. Stagnation or a rising residual is not convergence; a trend may be diagnostic, and any stagnation/divergence failure signal and retry action must be classified before use. The approved 25-correction cap does not replace those decisions. The residual after the 25th correction must be evaluated before reporting convergence or iteration-limit failure.

`τ_R=1e-8` is only an experimental target. It does not establish solution accuracy for every nonlinear model, prove stress accuracy, or replace independent element/global V&V.

## 3. E01-A — Line-search partial freeze

The following control parameters are accepted for the bounded experimental profile:

```text
c1 = 1e-4
alpha_k = 2^(-k), k = 0, 1, ..., 12
alpha_min_tested = 1/4096
```

Armijo is permitted only when the selected merit has a verified descent direction. The previous review's candidate merit was `φ=½||R_f/S_F||²` with `Dφ[p]=(R_f/S_F)^T(J_R p/S_F)` for fixed `S_F`; its candidate Armijo test is `φ(u+αp) ≤ φ(u)+c1 α Dφ[p]` with `Dφ[p]<0`. It remains a **candidate**, not a frozen method. This derivative is a valid certificate only if `J_R` is the derivative of the selected residual for that route. The blocked J2 tangent does not supply independent evidence of that fact. A separate verified directional derivative or justified certificate may be needed.

Therefore the **line-search control schedule is partially frozen**, while the merit/descent certificate and exhaustion/failure mapping remain **OPEN**. A small `α` alone does not establish descent or permit acceptance. A failed or non-finite candidate is classified explicitly. Every permitted retry follows complete rollback; no silent switch to an unrelated globalization method is allowed. If the merit/descent definition is not frozen, the Armijo route is blocked.

## 4. E01-A — Load path, cutback and endpoint

The normalized path coordinate is `λ∈[0,1]`. Every case supplies a positive minimum admissible `Δλ_min` in this dimensionless coordinate before execution; no universal physical-load increment is introduced. A failed step is rolled back before any retry, and only a predeclared retryable failure may trigger the already approved factor `0.5`. A zero, non-finite, unrepresentable or below-minimum proposed retry terminates explicitly. The global rejected-attempt count is at most 25 over the entire path, survives same-path restart, and is not reset by accepted increments.

The actual retryable/terminal failure map remains **OPEN**. Unknown or unclassified failures cannot trigger retry. The exact endpoint comparison/tolerance and clipped final-step acceptance rule remain **OPEN**; no success may be reported before the declared final target is attained. Each accepted increment still requires the approved equilibrium gate, admissibility, valid finite material/result state and exactly-once commit. No cutback policy may turn an unconverged or invalid state into an accepted increment.

## 5. E01-A — Transaction and checkpoint direction

The Owner-approved invariants apply unchanged: trial state is isolated; a failed iteration or rejected increment leaves the last accepted mechanical and constitutive state unchanged; rollback includes displacements, strains, stresses, plastic variables, accumulated outputs and relevant solver history; accepted state commits exactly once; rejected work cannot accumulate invisibly; and restart consistency is independently verifiable.

The additive, fail-closed design direction is accepted, but the schema is not. A future proposal must identify analysis/formulation version, material model and parameter identity, physical mesh and element identity, element family/integration rule/integration-point ordering, accepted displacement and constitutive state identity, accepted load coordinate/path identity, global rejection count/history, checkpoint/state/identity schema versions, and restart provenance. It must save only the accepted composite, preserve the rejection budget, and reject corruption, mismatch, unknown versions or unbound identity. Existing WP10 v2 bytes and semantics remain unchanged; no migration or historical rewrite is approved. Exact field names, hash composition, versioning, compatibility, migration and restart tolerances remain **PROPOSED / OPEN** until separately reviewed. The exact checkpoint schema is **not implemented**.

## 6. E01-B — Small-strain isotropic J2 contract

Use small-strain kinematics and isotropic linear elasticity with shear modulus `μ>0`. For deviatoric stress `s=dev(σ)`:

```text
q = sqrt(3/2 * s:s)
f = q - (sigma_y0 + H * alpha)
Delta_gamma = max(f_trial, 0) / (3 * mu + H)
Delta_alpha = Delta_gamma
Delta_epsilon_p = Delta_gamma * (3/2) * s_trial / q_trial   (plastic branch)
```

If `f_trial≤0`, the response is elastic and `Δγ=0`; if `f_trial>0`, perform the associated radial return. `sigma_y0>0`, `H≥0`; `H=0` is perfect plasticity and `H>0` is linear isotropic hardening. `alpha` is accumulated equivalent plastic strain and evolves monotonically. The accepted state is the source of each trial; loading, unloading and reloading update only the trial state until acceptance. No new yield smoothing or branch tolerance is introduced here. Stress and hardening modulus have stress units; strain, `alpha`, and `Delta_gamma` are dimensionless.

Retain the existing material Voigt convention: `[xx, yy, zz, xy, yz, xz]`, with engineering shear strain entries and tensorial shear stress entries. The internal contraction/update must respect that work-conjugate mapping. The approved scope excludes multiplicative finite-strain J2, coupled frictional plastic contact, general nonlinear dynamics, and general postbuckling qualification.

Keep the conceptual quantities distinct:

- Plastic stress work: `W_p = ∫ σ : dε_p` (energy per volume at material point).
- Linear-hardening stored energy: `ψ_h(α)=½ H α²` (energy per volume).
- Thermodynamic dissipation: `D_p = ∫ σ : dε_p - Δψ_h`; under the stated active associated ideal/linear isotropic J2 assumptions this reduces incrementally to `sigma_y0 * Δalpha`.

These are scientific definitions, not approval to expose new result fields. For the existing small-strain material route, preserve the historical update exactly:

```text
plastic_dissipation_(n+1) = plastic_dissipation_n
  + 1/2 * (sigma_n + sigma_(n+1)) : Delta_epsilon_p
```

Preserve the field name, values, endpoint trapezoid, availability and aggregation. It is not proven to equal the path integral or thermodynamic dissipation. New public plastic-work, hardening-energy or thermodynamic-dissipation fields are **DEFERRED**; do not migrate or reinterpret historical outputs. Unavailable outputs are not numeric zero.

## 7. D5 — Tangent and use restrictions

`J2_TANGENT_CONSISTENCY = BLOCKED_PENDING_INDEPENDENT_EVIDENCE`. The current exposed tangent is symmetrized; its symmetry is not independent evidence of consistency. `tau_T=2e-5` remains **PROPOSED / NOT FROZEN** and cannot be inherited from WP08/WP09's different element-force metric.

The future protocol must hold the incoming material state fixed; cover elastic and smooth plastic branches; use an independent stress derivative in multiple tensor directions; handle engineering-shear/tensorial-stress conversion; preregister stress scaling, absolute floor and perturbation sweep; demonstrate a stable finite-difference plateau; and treat yield-switch cross-branch differences as nonsmooth diagnostics with branch-preserving one-sided checks. No PASS is claimed, and no Full Newton J2 qualification/validation claim is allowed.

Constitutive-point experiments, independent radial-return verification and transaction/rollback verification may be proposed for separate Owner authorization. This record authorizes none of them. J2 Full Newton FEM, tangent-driven scientific qualification, public nonlinear J2 accuracy claims and support-maturity promotion are not authorized.

## 8. Compact decision and V&V matrix

| Decision class | Current decision | Required future independent V&V / blocker |
| --- | --- | --- |
| **OWNER_APPROVED principles** | D1 free-DOF residual gate; D2 rollback-before-retry and bounded recovery; D3 transactional states; D4 small-strain isotropic J2 equations/scope. | Independently verify implementation; this record is not correctness evidence. |
| **OWNER_APPROVED experimental controls** | 25 applied Newton corrections with post-correction residual checks; `c1=1e-4` with verified descent; `β=0.5`; global 25 rejections; approved transaction invariants; normalized `λ`; bounded alpha sequence through `1/4096`; rejection budget persists. | Control-boundary, rollback, count, restart, endpoint and descent checks; no execution occurred. |
| **PROPOSED numerical target** | `τ_R=1e-8`; case values `F_ref>0`, `F_abs≥0`; case minimum `Δλ_min>0`; candidate `φ`/descent formula; `τ_T=2e-5` and tangent plateau parameters. | Freeze values/definitions only after explicit Owner decision. Force scales missing from a case block the route. |
| **OPEN mandatory definitions** | Merit/descent certificate; per-case constraint admissibility scale where needed; retryable/terminal failure map; endpoint tolerance and clipped-target rule; exact checkpoint fields/schema/version/migration/restart policy. | Independent residual-direction checks; failure injection; endpoint and restart tests; no failure may silently retry or pass. |
| **BLOCKED claims** | J2 tangent consistency; Full Newton J2 validation/qualification; generalized nonlinear qualification. | Independent branch-aware tangent and separate global/element V&V plus later Owner decision. |
| **Deferred public semantics** | New public J2 energy fields. Historical `plastic_dissipation` unchanged. | Any future field needs an independent energy balance, specified units/aggregation/availability and separate Owner approval. |

## 9. Minimum implementation-readiness checklist

Before a future E01-A/B implementation GO, the Owner must separately resolve or authorize:

1. The proposed `τ_R=1e-8` target and case-level `F_ref`/`F_abs` input rules; specify any constraint type/tolerance in scope. Missing values remain fail-closed.
2. The exact merit function and verified descent certificate; define what happens on non-descent and line-search exhaustion.
3. The retryable/terminal failure map, case `Δλ_min`, and endpoint tolerance/clipped-final-increment rule. Preserve approved cutback and global rejection limits.
4. The exact additive checkpoint identity fields, schema/version binding, migration refusal/compatibility boundary, and restart acceptance criteria. Preserve WP10 v2 semantics and rejection count.
5. The allowed experimental J2 work boundary while D5 is blocked. Any executable tests, material-point experiments, FEM or V&V requires its own explicit authorization.

The alpha sequence, `c1`, Newton correction count, cutback factor, global rejection budget and transaction invariants do not need reapproval. `τ_T` does not need to be frozen for pointwise stress/state development, but D5 remains a hard blocker for tangent-consistency and Full Newton claims.

## 10. Final status

- `REPOSITORY_IDENTITY: VERIFIED`
- `WP_E01_D1_D4_PRINCIPLES: OWNER_APPROVED`
- `NEWTON_MAX_CORRECTIONS: OWNER_APPROVED_25`
- `ARMIJO_C1: OWNER_APPROVED_1E-4`
- `CUTBACK_FACTOR: OWNER_APPROVED_0.5`
- `GLOBAL_REJECTION_BUDGET: OWNER_APPROVED_25`
- `TRANSACTION_INVARIANTS: OWNER_APPROVED`
- `NEWTON_RESIDUAL_TARGET: PROPOSED_1E-8`
- `FORCE_SCALE_POLICY: CASE_DECLARED / BLOCKED`
- `LINE_SEARCH_POLICY: PARTIALLY_FROZEN / BLOCKED`
- `LOAD_PATH_POLICY: PARTIALLY_FROZEN / BLOCKED`
- `CHECKPOINT_SCHEMA: PROPOSED_NOT_IMPLEMENTED`
- `J2_NEW_PUBLIC_ENERGY_FIELDS: DEFERRED`
- `J2_TANGENT_CONSISTENCY: BLOCKED`
- `WP_E01_A_B_EXPERIMENTAL_CONTRACT: PARTIALLY_FROZEN / BLOCKED`
- `IMPLEMENTATION_AUTHORIZED: NO`
- `NUMERICAL_VNV_AUTHORIZED: NO`
- `NATIVE_FEM_AUTHORIZED: NO`
- `WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET`

Documentation only. No code, executable tests, numerical calculations, solver/backend, `solve_model`, native FEM, historical archive changes, qualification promotion, merge or release action occurred. Stop for Owner review; no automatic next step is authorized.
