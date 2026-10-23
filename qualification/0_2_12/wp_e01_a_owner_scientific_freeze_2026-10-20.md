# QF Solver v0.2.12 — WP-E01-A Owner Scientific Freeze

- **Owner decision date:** 2026-10-20
- **Scope:** WP-E01-A, bounded experimental incremental Newton–Raphson routes
- **Verified repository:** `C:\wpc01-frictionless-public-integration-wt\wp-e01`
- **Branch:** `codex/qf-wp-e01-recovery-review-20261020`
- **Verified starting HEAD:** `c8a2486d267f01787665a2ac37eb6292f50aa12a` (clean)
- **Decision:** `OWNER_APPROVED_EXPERIMENTAL`

This record freezes the experimental scientific contract stated below. It does not claim implementation correctness, numerical validation, general nonlinear qualification, or authorization to execute. It supersedes the earlier WP-E01-A recommendations as of this Owner decision. Earlier records remain historical evidence of the decision sequence.

## 1. Frozen experimental contract

### 1.1 Equilibrium residual and admissibility

On free equilibrium DOFs `f`, use the approved sign convention

\[
R_f=f_{\mathrm{target},f}-f_{\mathrm{internal},f},\qquad
S_F=\max\bigl(\lVert f_{\mathrm{target},f}\rVert_2,F_{\mathrm{ref}}\bigr),
\]

and accept equilibrium only when

\[
\lVert R_f\rVert_2\leq \tau_R S_F+F_{\mathrm{abs}},\qquad
\tau_R=10^{-8},\quad F_{\mathrm{abs}}=0\ \mathrm{N}\ \text{by default}.
\]

`F_ref` is a predeclared physical load-pattern envelope, independent of observed residuals. A justified nonnegative case-specific `F_abs` is permitted. `S_F` must be finite and strictly positive; missing or invalid scales fail closed. The norm is over free DOFs only and excludes prescribed-DOF reactions. The initial constraint scope eliminates prescribed-displacement DOFs and reconstructs their values at candidates. Unsupported constraints and a model with no free equilibrium DOFs fail closed. Displacement correction remains diagnostic.

### 1.2 Newton correction count

At most 25 correction updates may be applied per attempted increment. The initial residual check is not an update. After update 25, assemble and check the updated state residual before declaring convergence or failure. A correction-size diagnostic cannot replace the residual gate.

### 1.3 Armijo line search

For one line search, hold the load target, `S_F`, and

\[
T_R=\tau_R S_F+F_{\mathrm{abs}}>0
\]

fixed. Use the dimensionless merit

\[
\phi(u)=\frac12\left\lVert\frac{R_f(u)}{T_R}\right\rVert_2^2.
\]

For correction direction `p`, define `J_R=\partial R_f/\partial u_f` under the same residual sign and free-DOF convention, and

\[
D\phi[p]=\frac{R_f^T J_Rp}{T_R^2}.
\]

Armijo behavior is enabled for a route only after the residual derivative, its sign convention, and the directional derivative are independently verified for that route. The base state, `J_Rp`, and `D\phi[p]` must be finite, and verified descent requires `D\phi[p]<0`. With approved `c_1=10^{-4}`, try exactly 13 candidates

\[
\alpha_k=2^{-k},\qquad k=0,1,\ldots,12,
\]

and accept the first admissible trial satisfying

\[
\phi(u+\alpha_kp)\leq \phi(u)+c_1\alpha_kD\phi[p].
\]

Each trial is evaluated from the same accepted increment-base material state. A non-descent or unverified direction is terminal; it cannot be hidden by reducing the load step. Exhaustion after verified descent is a retryable increment failure only after complete rollback. No unsupported or nonsmooth route may assume a valid certificate. This contract is not evidence that any current route has passed the derivative check.

### 1.4 Load path, endpoint, and rejection budget

Use normalized load coordinate `\lambda\in[0,1]`. For case-declared initial increment `\Delta\lambda_0>0`, the ordinary minimum is

\[
\Delta\lambda_{\min}=10^{-4}\Delta\lambda_0.
\]

Cutback is `\beta=0.5`. Minimum equality is admissible. A single positive final remainder below the ordinary minimum may be clipped to reach the exact endpoint `\lambda=1`; only after equilibrium, admissibility, and state checks pass may that state be committed and recorded at exactly `1`. A failed final increment is not complete. If an eligible failure cannot be retried without violating the minimum-step rule or the single clipped-tail rule, terminate the path incomplete rather than inventing another subminimum step.

Count rejected increment attempts globally across the complete load path, including across a same-path restart. A rejected attempt consumes one count exactly once; an accepted increment consumes none. Permit at most 25 rejected attempts, then stop before attempt 26. Retry only after complete rollback and only for an approved retryable class. Terminal failures stop immediately. Successful completion requires an accepted state at exact `\lambda=1`; an epsilon-shortfall is not success.

### 1.5 Checkpoint and transaction invariants

Approve an additive, versioned WP-E01-A metadata subrecord compatible with the existing WP10 v2 checkpoint container. Preserve the historical WP10 v2 behavior and do not rewrite or migrate historical checkpoints under this decision. The E01-A record must bind at least:

- checkpoint sub-schema/version and analysis/formulation/control-profile identity;
- load-path identity and normalized accepted `\lambda`;
- material/model identity and accepted-state digest;
- element and integration-point identity through existing model/topology/material identities;
- accepted step and next increment;
- attempt intent/status and stable attempt identity;
- persistent global rejection count and its bounded ledger; and
- restart provenance.

Reject corrupt, incompatible, unknown-version, or insufficient E01-A restart records. Persist attempt intent so an interrupted attempt is resolved consistently and counted no more than once. Restarting the same path must not reset the global rejection ledger. Preserve the approved state lifecycle: trials are isolated; failed Newton work cannot mutate accepted history; rejected increments fully roll back displacements, strains, stresses, plastic variables, accumulated outputs, and relevant solver history; and an accepted increment commits exactly once. This approval is for the schema direction and these fields/invariants; it does not implement them or revise the WP10 v2 container.

### 1.6 Failure classification

Retryable only after successful complete rollback:

1. finite Newton correction-limit failure with otherwise valid state;
2. Armijo exhaustion after verified descent; and
3. explicitly typed, finite admissibility failures that depend on increment size.

Terminal failures include an unverified or non-descending direction, invalid input, unsupported constraints, corrupt state/checkpoint, singular linear solve, unknown/unclassified failure, and exhausted global rejection budget. Each rejected attempt is counted exactly once. A retryable class does not override an exhausted minimum-step/endpoint rule.

## 2. Implementation-readiness review

The source inspection below is read-only. The rows identify the difference between this approved contract and the source at the verified baseline.

| Contract item | Source finding at baseline | Status | Required independent verification before enabling the behavior |
| --- | --- | --- | --- |
| Physical residual scale and additive tolerance | `driver.py` uses `max(||target_free||₂, force_scale, 1.0)` and does not implement the approved case-declared `F_ref`/`F_abs` equation. | **NOT_IMPLEMENTED** | Check the free-DOF sign/reduction, units, zero/near-zero load cases, coherent force-unit rescaling, and constraint/reaction handling against independent equilibrium references. |
| 25 applied corrections | The Newton loop assembles before each update; it exits after the final loop update without checking the post-update state after correction 25. | **NOT_IMPLEMENTED** | Verify update counting and residual evaluation after every update, especially the final allowed update; independently verify residual against the accepted candidate state. |
| Armijo derivative and certificate | Current line search checks residual-merit reduction using a multiplicative rule; it does not verify `J_Rp` and the finite negative `D\phi[p]` required here. | **NOT_IMPLEMENTED** | For each supported route, compare `J_Rp` with an independent directional derivative using the frozen residual sign and DOF convention; verify finite negative descent and every accepted Armijo inequality. Keep unsupported/nonsmooth routes disabled. |
| 13-trial schedule and failure behavior | Current configured line-search profiles use other alpha minima/reduction counts and generic line-search failure handling. | **NOT_IMPLEMENTED** | Verify exact candidates `1, 1/2, …, 1/4096`, same-base trial isolation, exhaustion classification, and rollback before cutback. |
| Minimum step and exact endpoint | Adaptive control uses existing route controls and the loop can stop at `\lambda<1-10^{-12}`; these do not implement the frozen relative minimum plus exact endpoint contract. | **NOT_IMPLEMENTED** | Check minimum equality, one clipped positive endpoint remainder, exact `\lambda=1` only after full acceptance, and incomplete termination after a failed final attempt. |
| Failure classes and global ledger | Existing retry mapping includes broader classes such as stagnation and generic line-search failure; the route does not provide the frozen typed distinctions for every failure. | **NOT_IMPLEMENTED** | Inject each classified failure in future authorized V&V; verify retry only after rollback, terminal failures stop, and each rejected attempt is counted once up to the global limit. |
| E01-A checkpoint subrecord | WP10 v2 already supplies accepted-state transaction/digest, identity checks, metadata integrity, and atomic replacement. It has no E01-A attempt intent and persistent per-attempt ledger subrecord. | **NOT_IMPLEMENTED** (WP10 foundations exist) | Independently verify identity mismatch/corruption refusal, interruption resolution without double count, same-path ledger persistence, rollback, and restart equivalence while preserving historical v2 behavior. |
| Numerical correctness/qualification | No numerical V&V was performed for this decision. A frozen criterion alone does not establish equilibrium accuracy or route-wide validity. | **NOT_VERIFIED** | Execute only under a later explicit V&V authorization, with independent references preregistered for each supported route. |
| J2 tangent claim | `J2_TANGENT_CONSISTENCY` remains `BLOCKED_PENDING_INDEPENDENT_EVIDENCE`. | **BLOCKED** | Independent branch-aware material derivative evidence is required. No Full Newton J2 validation or qualification claim is permitted while blocked. |

No tests were created or run. No numerical calculations, FEM, solver, `solve_model`, or backend execution occurred. No production code was changed.

## 3. Status

- `E01_A_SCIENTIFIC_CONTRACT: FROZEN_EXPERIMENTAL`
- `E01_A_IMPLEMENTATION: NOT_AUTHORIZED`
- `E01_A_NUMERICAL_VNV: NOT_RUN`
- `J2_TANGENT_CONSISTENCY: BLOCKED_PENDING_INDEPENDENT_EVIDENCE`
- `WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET`

The approved scientific contract, implementation correctness, independent numerical V&V, and qualification status remain separate claims. Only the first is frozen here.
