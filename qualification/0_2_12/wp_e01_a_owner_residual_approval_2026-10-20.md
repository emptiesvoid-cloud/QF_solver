# QF Solver v0.2.12 — WP-E01-A Owner decision record

- **Owner decision date:** 2026-10-20
- **Scope:** WP-E01-A bounded experimental Newton routes only
- **Verified repository:** `C:\wpc01-frictionless-public-integration-wt\wp-e01`
- **Branch:** `codex/qf-wp-e01-recovery-review-20261020`
- **Prior residual-decision HEAD:** `7d0b3ea8166c1c2f510b998158eb19b8a7f8de22`
- **Verified final-freeze update baseline:** `c8a2486d267f01787665a2ac37eb6292f50aa12a` (clean)
- **Record type:** Owner-approved experimental residual and final A–D contract freeze

This record preserves the earlier Owner residual decision and records the later Owner approval of the complete bounded WP-E01-A experimental contract. The detailed, current contract and readiness review are in the [WP-E01-A Owner scientific-freeze record](wp_e01_a_owner_scientific_freeze_2026-10-20.md). Earlier open/proposed recommendation status in the historical record is superseded by this freeze.

## 1. Approved residual and Newton principles

On free equilibrium DOFs `f`, use

\[
R_f=f_{\mathrm{target},f}-f_{\mathrm{internal},f},\qquad
S_F=\max(\lVert f_{\mathrm{target},f}\rVert_2,F_{\mathrm{ref}}),
\]

and require

\[
\lVert R_f\rVert_2\leq 10^{-8}S_F+F_{\mathrm{abs}}.
\]

`F_ref` is a predeclared physical load-pattern envelope, independent of observed residuals. `F_abs=0 N` is the experimental default; a justified case-declared nonnegative force allowance is permitted. `S_F` must be finite and positive or the route fails closed. Exclude prescribed-DOF reactions. Initial constraints eliminate prescribed-displacement DOFs and reconstruct their values. Unsupported constraints and a model with no free equilibrium DOFs fail closed. Displacement correction remains diagnostic.

Maximum Newton corrections are 25 applied updates per attempted increment. The initial residual evaluation is not an update. Check the state residual after every update, including update 25.

## 2. Final Owner-approved experimental decisions

| Decision | Owner-approved contract | Status and limit |
| --- | --- | --- |
| **A — Armijo** | `T_R=10^-8 S_F+F_abs>0`; `φ=½||R_f/T_R||₂²`; `Dφ[p]=R_fᵀJ_Rp/T_R²`, `J_R=∂R_f/∂u_f`. Require independent route-specific verification of derivative, sign convention, and finite `Dφ[p]<0`. Use `c1=1e-4`; test `α_k=2^-k`, `k=0,…,12` (13 trials through `1/4096`). No descent/unverified derivative is terminal. Exhaustion after verified descent may cut back only after full rollback. | `OWNER_APPROVED_EXPERIMENTAL`; route derivative and Armijo behavior `NOT_VERIFIED` until independent evidence exists. Unsupported/nonsmooth routes cannot assume a descent certificate. |
| **B — Load path and endpoint** | `λ∈[0,1]`; `Δλ_min=10^-4 Δλ₀` for a case-declared positive initial increment; minimum equality is permitted. Cutback `β=0.5`. One positive final remainder below the minimum may be clipped solely to reach exact `λ=1`. Commit only after all equilibrium, admissibility and state checks; a failed final attempt is incomplete. A global maximum of 25 rejected attempts applies per complete path and persists across same-path restart. | `OWNER_APPROVED_EXPERIMENTAL`; no epsilon-shortfall endpoint success, unlimited retries, or minimum-step override. |
| **C — Transactions and checkpoint** | Trial state remains isolated. Failed Newton work cannot mutate accepted state. Rejected increments fully roll back all relevant mechanical/constitutive state. Accepted increment commits exactly once. Approve the additive, versioned WP10 v2-compatible E01-A metadata subrecord carrying accepted-state identity, normalized `λ`, attempt intent/identity, persistent rejection ledger, and restart provenance. Reject corrupt, incompatible, unknown-version, or insufficient records. Resolve interrupted attempts consistently and count each no more than once. Preserve historical WP10 v2 behavior. | Lifecycle invariants and E01-A metadata direction `OWNER_APPROVED_EXPERIMENTAL`; implementation `NOT_IMPLEMENTED`. No historical checkpoint migration/rewrite. |
| **D — Failure classification** | Retry after complete rollback only for finite Newton correction-limit failure, Armijo exhaustion after verified descent, or explicitly typed finite increment-dependent admissibility failure. Terminal: unverified/non-descending direction, invalid input, unsupported constraints, corrupt state/checkpoint, singular linear solve, unknown failure, or exhausted global rejection budget. Count each rejected increment once. | `OWNER_APPROVED_EXPERIMENTAL`; a retryable classification cannot override minimum-step or endpoint exhaustion. |

## 3. Implementation and evidence boundary

The [updated final decision matrix](wp_e01_a_final_owner_decision_matrix_2026-10-20.md) and [contract proposal](wp_e01_a_final_contract_proposal_2026-10-20.md) record current source deviations and implementation implications. At the verified source baseline, force normalization still contains a unit floor, the Newton loop does not check the post-correction-25 state, line search lacks the approved derivative certificate, endpoint completion is tolerance-based, and E01-A attempt-intent/ledger metadata is absent. These are `NOT_IMPLEMENTED` source deviations, not changes made by this record. Independent numerical evidence is `NOT_VERIFIED`; no tests or numerical V&V were run.

`J2_TANGENT_CONSISTENCY: BLOCKED_PENDING_INDEPENDENT_EVIDENCE`. This WP-E01-A freeze does not authorize or validate J2 Full Newton behavior.

## 4. Final status

- `E01_A_SCIENTIFIC_CONTRACT: FROZEN_EXPERIMENTAL`
- `E01_A_IMPLEMENTATION: NOT_AUTHORIZED`
- `E01_A_NUMERICAL_VNV: NOT_RUN`
- `J2_TANGENT_CONSISTENCY: BLOCKED_PENDING_INDEPENDENT_EVIDENCE`
- `WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET`