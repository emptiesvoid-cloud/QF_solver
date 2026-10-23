# QF Solver v0.2.12 — WP-E01 Owner partial freeze: Newton and checkpoint invariants

- **Owner decision date:** 2026-10-20
- **Scope:** WP-E01-A/B; bounded experimental incremental Newton routes only
- **Decision status:** Partial freeze. This record does not complete the E01-A/B contract freeze, authorize implementation or V&V, qualify any route, or close WP-E01.

## 1. Verified baseline and authority

- Agent B worktree: `C:\wpc01-frictionless-public-integration-wt\wp-e01`
- Branch: `codex/qf-wp-e01-recovery-review-20261020`
- Verified clean starting HEAD: `ba5026cf5afc709ef42f948766e0a9baf6493c2a`
- Canonical checkout: `C:\wpc01-frictionless-public-integration`, branch `emptiesvoids-cloud/wp-c01-contact-aware-equilibrium-audit`
- Verified canonical HEAD: `3c0e0492104375fa01ce271896ca3e91c2cc53db`; worktree clean.
- Read the canonical `qualification/0_2_12/ROADMAP.md`, the WP-E01 D1-D4 Owner record, the candidate and final numerical review, and applicable WP08-WP10 contracts. The roadmap and historical qualification records were not modified.

This dated record adds only the partial Owner approvals stated below. The earlier D1-D4 approval record remains unchanged. WP-E01 stays `OPEN / EXPERIMENTAL_TARGET`; D5 remains blocked.

## 2. OWNER_APPROVED_EXPERIMENTAL_PROFILE

The approved parameters apply only to bounded experimental incremental Newton routes within WP-E01-A/B.

### P1 — Maximum Newton corrections

- Maximum: **25 correction updates per attempted load increment**.
- A correction update is counted when the Newton displacement update is applied.
- The initial residual evaluation is not a correction update.
- The residual of every updated state must be evaluated before declaring convergence or failure. Thus an attempt that applies 25 corrections must check the state after the 25th correction before reporting iteration-limit failure.
- Do not reinterpret the limit as 25 residual evaluations.

### P2 — Armijo parameter

- Approved: **`c1 = 1e-4`**, dimensionless.
- Use this constant only with a selected merit function and a verified descent direction for that merit function.
- If descent is not established, the method must not report that Armijo was satisfied. The response to a non-descent direction remains part of the open route policy.
- The merit function, derivative calculation, backtracking factor, minimum accepted alpha, and search budget remain **OPEN**. The earlier 12-reduction and `alpha_min=1e-4` proposals are not frozen.

### P3 — Load cutback

- Approved: **`beta = 0.5`**, dimensionless, for the bounded experimental profile.
- A retry is permitted only after rollback to the complete last accepted incremental and constitutive state, and only when the failure is in an explicitly permitted retry class.
- The minimum admissible increment and retryable/terminal failure map remain **OPEN**. If cutback produces a zero, non-finite, unrepresentable, or below-minimum increment, or the failure is terminal, the run must fail explicitly without another attempt. The rule for equality with a future minimum is still open.

### P4 — Global rejected-increment budget

- Approved maximum: **25 rejected attempted load increments per complete load-path execution**.
- Each rejected attempted increment consumes one rejection. An accepted increment consumes none. A retry is a new attempted increment.
- Count across the whole path; do not reset at each accepted load increment. After the 25th rejection, stop explicitly and do not start attempt 26.
- If a checkpoint resumes the same load-path execution, the budget must not be evaded by resetting the count. The checkpoint representation and restart rules needed to preserve that count remain **OPEN**.
- Terminal failures must be recorded and cannot trigger unbounded retries. The retryable/terminal classification itself remains **OPEN**.

## 3. OWNER_APPROVED_CHECKPOINT_INVARIANTS

The Owner approves these lifecycle invariants for WP-E01-A/B:

1. Trial state is isolated from accepted state.
2. Failed Newton iterations cannot mutate accepted material history.
3. Rejected increments cause full rollback to the last accepted state.
4. An accepted increment commits its internal state exactly once.
5. Rollback covers displacement, strain, stress, plastic variables, accumulated outputs, and relevant solver history.
6. Rejected attempts cannot contaminate later accepted increments.
7. Restart and checkpoint consistency must be independently verifiable.

These invariants do **not** approve a checkpoint schema, serialization version, identity or hashing rules, migration policy, backward-compatibility changes, or restart tolerances. Preserve existing WP10 behavior and history. No incompatible checkpoint format or historical rewrite is approved.

## 4. Compact Owner approval and open-decision matrix

All future V&V listed here is a preregistered requirement, not evidence obtained in this documentation review.

| Decision ID | Mathematical or algorithmic definition | Status | Applicable route | Units / dimensionless status | Required future V&V | Remaining Owner decisions |
| --- | --- | --- | --- | --- | --- | --- |
| P1 | At most 25 applied displacement correction updates per attempted increment; evaluate the initial state and every updated state, including after update 25. | **OWNER_APPROVED** | Bounded experimental WP-E01-A/B incremental Newton | Update count | Verify count boundaries, initial evaluation, post-update residual evaluation, and failure only after the final checked state. | None for the count; route implementation still requires separate authorization. |
| P2 | Armijo scalar `c1=1e-4`; apply only when the chosen merit has a verified negative directional derivative. | **OWNER_APPROVED** | Same bounded experimental routes, only when Armijo is selected | Dimensionless | Independently verify derivative sign and sufficient decrease for the chosen merit; verify refusal/classification when descent is absent. | Merit function, derivative method, and action when descent cannot be established. |
| P3 | Retry step size `Δλ_new=0.5 Δλ_old`; retry only after complete rollback and for a permitted failure class. | **OWNER_APPROVED** | Same bounded experimental routes | `beta` dimensionless; `Δλ` dimensionless normalized path coordinate | Verify rollback before retry, exact factor use, and state identity across repeated rejections. | Retryable/terminal failure map; minimum increment and equality behavior. |
| P4 | Global maximum 25 rejected attempted increments per complete load path; accepted attempts do not consume count; retry is a new attempt; no attempt 26. | **OWNER_APPROVED** | Same bounded experimental routes | Count | Verify count spans accepted increments, terminal boundary after rejection 25, deterministic diagnostics, and no reset on continuation/restart of the same path. | Checkpoint representation of the count and same-path restart binding. |
| P5 | Isolated trial, unchanged accepted state on failure, complete rollback, one commit on acceptance, no rejected-state contamination, independently verifiable restart. | **OWNER_APPROVED** | WP-E01-A/B transaction and persistence lifecycle | No units | Compare every approved state component across rejected iterations/increments, commit exactly once, and independently compare restart state. | No additional invariant; schema, identity, version, migration, and tolerances are separate open decisions. |
| A | `rho_R=||R_f||₂/S_F`; accept only if `rho_R≤tau_R+F_abs/S_F`. The earlier `tau_R=1e-8` is not frozen. | **OPEN** (`1e-8` remains **PROPOSED**) | WP-E01-A/B free-DOF equilibrium | `tau_R` dimensionless; residual scales have force units | Independent free-force reconstruction, coherent unit rescaling, zero/near-zero and constrained cases, final-state check. | Set `tau_R` and any route-specific applicability. |
| B | Positive fixed `F_ref`, independent of the observed residual. | **OPEN** | WP-E01-A/B | Force units | Verify declared scale against load-pattern, cancellation, and near-zero-load references. | Choose the physical scale policy, value, units, and provenance. |
| C | Optional independently justified `F_abs` in the D1 gate. | **OPEN** | WP-E01-A/B | Force units | Establish error budget and test near-zero-load behavior. | Choose physical allowance, scale fraction, or explicit zero, with value and provenance. |
| D | Select a merit `phi` and verify `Dphi[p] < 0` before applying Armijo sufficient decrease with approved `c1`. | **OPEN** | WP-E01-A/B routes selecting line search | Merit-dependent; `c1` dimensionless | Independent merit/derivative checks, inexact-direction checks, and accepted/exhausted search cases. | Exact merit, directional derivative computation, and no-descent response. |
| E | Define backtracking factor, minimum accepted `alpha`, and maximum search attempts/reductions. | **OPEN** (prior settings remain **PROPOSED**) | WP-E01-A/B routes selecting line search | Alpha and factor dimensionless; reductions are a count | Exercise every boundary, finite-step refusal, and exhaustion classification. | Select a consistent sequence and budget. Neither 12 reductions nor `alpha_min=1e-4` is approved. |
| F | Explicit failure-to-retry classification, evaluated only after rollback. | **OPEN** | WP-E01-A/B adaptive paths | Typed failure classes | Inject each class and verify retry/terminal result and diagnostics. | Approve permitted retry classes and terminal classes. |
| G | Positive minimum normalized increment and eligibility rule for proposed cutback. | **OPEN** | WP-E01-A/B adaptive paths | Dimensionless path increment | Verify equality, below-minimum, zero/unrepresentable step, and clipped target remainder cases. | Set minimum and equality/endpoint interaction. |
| H | Exact requested final load-path identity must be attained and accepted before success is reported. | **OPEN** | WP-E01-A/B incremental paths | Dimensionless path coordinate; target tolerance not set | Verify clipped final step and terminal failure before target. | Select endpoint identity/tolerance and any shortfall rule. |
| I | Versioned checkpoint identity/schema, serialization, migration, and restart acceptance. Preserve WP10 behavior. | **OPEN** | WP-E01-A/B persistence | Schema/version identifiers; state values retain physical units | Verify round-trip, identity mismatch, corruption, legacy refusal/compatibility, and restart equivalence after rejections. | Schema, state/formulation identity, IP ordering, migration, restart tolerances, and rejection-count persistence. |
| J | Preserve the existing `plastic_dissipation` name and recorded source computation; make no stronger physical claim from this partial freeze. | **OPEN** beyond historical computation | WP-E01-B | Existing source units/aggregation must be preserved | Independent material-path accounting and comparison with the historical accumulator. | Any interpretation or reclassification beyond documented source behavior. |
| K | Define any new plastic-work, hardening-storage, or thermodynamic-dissipation output separately. | **OPEN** | WP-E01-B | Energy density or integrated energy, explicitly declared | Independent energy balance and output-availability checks. | Names, units, point/element recovery, availability, and incremental/cumulative semantics. |
| L | Define tangent error norm/scale, fixed-state perturbation sweep, branch-aware plateau policy. | **OPEN** | WP-E01-B tangent work | Strain perturbation dimensionless; error scale in stress units | Independent elastic/plastic branch oracle, step-size plateau, and transition diagnostics. | Error normalization, absolute floor, step range, and plateau threshold. |
| M | Tangent acceptance threshold; prior `tau_T=2e-5` is not frozen. | **BLOCKED** pending independent evidence | WP-E01-B smooth-branch tangent consistency | Dimensionless only after approved normalization | Independent branch-aware derivative evidence under an authorized V&V plan. | Select threshold only after evidence; no Full Newton validation claim. |

## 5. Scientific consistency and source compatibility

- **Correction counting:** the source `UnifiedNewtonEngine` currently bounds a loop of residual/convergence evaluations. It checks the residual before applying each correction; on the final loop pass it can apply a correction and exit without checking that updated state. Therefore the approved 25-correction contract is **not yet implemented** by merely setting `max_iterations=25`. Future implementation must count applied updates and perform the residual check after update 25 before declaring nonconvergence.
- **Armijo:** the current options expose a `line_search_c` value, but the Owner approval of `c1` alone does not approve the merit function or demonstrate a descent direction. No existing default may be treated as satisfying P2 without that check.
- **Cutback and rejection count:** source controls already use `0.5` and a global rejected-attempt counter with a terminal decision after the configured Nth rejection; the controller rolls back and checks the accepted digest before policy selection. Those source behaviors are compatibility evidence only. They do not freeze minimum increment, retry classes, a particular E01 route, or a checkpoint schema.
- **Minimum increment and endpoint:** the source has a configurable minimum and target loop guard; neither is approved by this record. A cutback that cannot produce an admissible next increment, an exhausted global budget, a terminal failure class, or an unattained target must produce explicit terminal failure. Do not infer a successful path from small increments or an unapproved tolerance.
- **Force scaling:** the D1 equation remains the approved principle, but `tau_R`, `F_ref`, and `F_abs` remain open. Current source normalization includes a caller-unit-dependent `1.0` floor and does not implement the full physical scale contract. No equilibrium or qualification claim may rely solely on that unapproved threshold/scale.
- **J2 and D5:** preserve the approved small-strain radial-return principles and keep historical accumulator computation separate from thermodynamic dissipation. `J2_TANGENT_CONSISTENCY = BLOCKED_PENDING_INDEPENDENT_EVIDENCE`; no Full Newton validation claim is authorized.

## 6. Minimal decisions before a future E01-A/B implementation GO

Before a separate implementation GO, the Owner still needs to decide:

1. Freeze the D1 residual threshold, physical `F_ref`, `F_abs` policy/value, and any route-specific constraint or additional gate policy.
2. Select the line-search merit and verified directional derivative; choose backtracking factor, minimum alpha and search budget; approve retryable/terminal failures, minimum load increment and endpoint acceptance.
3. Approve E01 checkpoint/state identity, schema/version, restart compatibility, migration boundaries and tolerances, including preservation of the global rejection count when continuing the same path.
4. Decide whether E01-B implementation will defer new energy outputs (preserving only the legacy field computation) or define their names, units, availability and accumulation semantics.
5. Explicitly bound the allowed experimental use of J2 while D5 remains blocked; no tangent consistency or Full Newton validation claim may be made without separate independent evidence.

The approved P1-P5 items are frozen only as principles/parameters for the bounded experimental profile. This checklist and the OPEN rows above show why the full E01-A/B contract is not frozen.

## 7. Authorization and status

- WP-E01-A/B: `OPEN / EXPERIMENTAL_TARGET`
- D1-D4 principles: preserved; approved partial-profile parameters and checkpoint invariants recorded above.
- D5: `BLOCKED_PENDING_INDEPENDENT_EVIDENCE`
- Complete E01-A/B specification freeze: **NO**.
- Production implementation, executable tests, numerical V&V, solver/FEM execution, native FEM, `solve_model`, backend work, merge, release, and qualification promotion: **NOT AUTHORIZED**.

Stop after documentation delivery. Wait for separate Owner authorization before implementation or V&V.
