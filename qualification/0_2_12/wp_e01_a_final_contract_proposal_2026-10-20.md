# QF Solver v0.2.12 — WP-E01-A frozen experimental contract

- **Owner decision date:** 2026-10-20
- **Scope:** WP-E01-A bounded experimental incremental Newton–Raphson
- **Worktree / branch:** `C:\wpc01-frictionless-public-integration-wt\wp-e01` / `codex/qf-wp-e01-recovery-review-20261020`
- **Initial reviewed proposal HEAD:** `e549cf52bfc960ad4f1423d382dcde716867bc39`
- **Verified freeze-update baseline HEAD:** `c8a2486d267f01787665a2ac37eb6292f50aa12a` (clean)
- **Canonical checkout:** `C:\wpc01-frictionless-public-integration`, `emptiesvoid-cloud/wp-c01-contact-aware-equilibrium-audit`, `3c0e0492104375fa01ce271896ca3e91c2cc53db`
- **Canonical roadmap:** `qualification/0_2_12/ROADMAP.md`, SHA-256 `48021A7773895C354806446AB89E317B968CFEE5F2618790F4487FBF11195A6D` (unchanged)
- **Disposition:** A–D are `OWNER_APPROVED_EXPERIMENTAL`; implementation is not authorized and numerical V&V is not run.

This current contract supersedes the earlier proposed/open statuses in this file's prior revision. The signed-off decision is recorded in the [WP-E01-A Owner scientific freeze](wp_e01_a_owner_scientific_freeze_2026-10-20.md). Approval freezes the scientific contract only; it does not establish software correctness, route eligibility, numerical accuracy, or qualification.

## Owner decision matrix

| ID | Frozen experimental contract | Source/compatibility status | Verification required before enabling |
| --- | --- | --- | --- |
| **A — Residual and admissibility** | On free DOFs, `R_f=f_target,f−f_internal,f`, `S_F=max(||f_target,f||₂,F_ref)`, and `||R_f||₂≤τ_R S_F+F_abs`, with `τ_R=1e-8`. `F_ref` is a predeclared physical load-pattern envelope, independent of observed residuals. Default `F_abs=0 N`; a justified case-declared nonnegative value is allowed. Require finite `S_F>0`, else fail closed. Eliminate/reconstruct prescribed-displacement DOFs; exclude their reactions. Unsupported constraints and no free equilibrium DOFs fail closed. Correction norm remains diagnostic. | Current force scale includes a `1.0` force-unit floor and does not implement the additive allowance. **NOT_IMPLEMENTED.** | Independent free-DOF equilibrium references; zero/nearly-zero and mixed-scale cases; unit-rescaling invariance; constraint and reaction exclusion; nonfinite refusal. |
| **A — Newton updates** | Maximum 25 applied correction updates per attempted increment. Initial residual check is not counted. Check the updated state residual after every correction, including correction 25. | Current loop exits after the final applied update without checking that updated state. **NOT_IMPLEMENTED.** | Verify update counting and residual evaluation after update 25 against an independent equilibrium calculation. |
| **A — Armijo** | Hold `T_R=τ_R S_F+F_abs>0` fixed during the search. `φ(u)=½||R_f(u)/T_R||₂²`; with `J_R=∂R_f/∂u_f`, `Dφ[p]=R_fᵀJ_Rp/T_R²`. Require route-specific independent verification of `J_Rp`, sign convention, finiteness, and `Dφ[p]<0`. With `c1=1e-4`, test `α_k=2^-k`, `k=0,…,12` (13 trials, last `1/4096`) and accept only `φ(u+α_kp)≤φ(u)+c1 α_kDφ[p]`. Each trial starts from the same accepted increment-base material state. Unverified/non-descent direction is terminal. Exhaustion after verified descent permits cutback only after complete rollback. | Existing line search checks merit reduction without this derivative certificate and has other configured schedules. **NOT_IMPLEMENTED.** Route derivative certificate **NOT_VERIFIED**. | For each supported route, independently compare `J_Rp` with a directional derivative, verify sign and finite descent, check every Armijo acceptance and same-base state isolation. No unsupported or nonsmooth route may assume descent. |
| **B — Load-path endpoint** | Use `λ∈[0,1]`, case-declared `Δλ₀>0`, and `Δλ_min=1e-4 Δλ₀`; equality is allowed. Cutback `β=0.5`. Permit one positive clipped final remainder below the floor solely to reach literal `λ=1`. Commit only after equilibrium, admissibility, and state checks; failure of the final increment is incomplete. Count rejections globally (including across same-path restart), once each, maximum 25; stop before attempt 26. | Current loop can stop at `λ<1−1e-12`; current minimum-increment profile differs. **NOT_IMPLEMENTED.** | Verify minimum equality, bounded cutback, a single clipped endpoint, exact `λ=1` after acceptance, no false endpoint success, and incomplete failure behavior. |
| **B — Failure classes** | Retry after complete rollback only for finite Newton correction-limit failure; Armijo exhaustion after verified descent; or explicitly typed finite increment-dependent admissibility failure. Terminal: unverified/non-descending direction, invalid input, unsupported constraints, corrupt state/checkpoint, singular linear solve, unknown failure, or exhausted global rejection budget. Count every rejected increment attempt once. Minimum-step/endpoint exhaustion also stops the path; no retry may override it. | Existing retry map includes broader generic line-search/stagnation classes. **NOT_IMPLEMENTED.** | Independently verify class mapping, exact rollback before retry, once-only counting (including terminal attempts), and refusal of unknown classes. |
| **C — Checkpoints and transactions** | Preserve outer WP10 `NonlinearCheckpointV2` and historical WP10 v2 behavior. Add a versioned E01-A metadata subrecord binding accepted-state identity, normalized load coordinate, attempt intent/stable identity, persistent global rejection ledger, load-path/control identity, and restart provenance. Preserve accepted state, attempt ordinal/status/ID, retry history, parent/state digest, and version fields. Reject corrupt, incompatible, unknown-version or insufficient E01-A records. Resolve an interrupted intent once by stable attempt identity and count it no more than once; interrupted attempts are terminal absent another approved retry class. Keep accepted/trial isolation, full rollback, exactly-once commit, and no trial checkpointing. Do not rewrite/migrate old WP10 checkpoints; legacy records retain historical semantics and are insufficient for E01-A same-path restart without the subrecord. | WP10 already provides detached trial state, accepted composite commit, state/identity digests, metadata integrity and atomic replacement. No E01-A attempt-intent/ledger subrecord is present. **NOT_IMPLEMENTED** (WP10 foundations exist). | Future independent checks must cover identity mismatch/corruption refusal, rollback, interruption deduplication, persistent global count, restart reproducibility, and unchanged historical WP10 v2 behavior. |

## Source/contract compatibility findings

Read-only inspection of `driver.py`, `iteration.py`, `load_control.py`, `controls.py`, `robustness.py`, `state.py`, and `checkpoint.py` found the implementation gaps summarized above. The current line-search controller can perform other robustness phases; E01-A must select only its approved derivative-certified policy and must not silently fall back. Current retry behavior does not yet distinguish verified-descent exhaustion from no descent. Existing WP10 transaction and checkpoint foundations are reusable, but the additive E01-A metadata and write-ahead attempt accounting require new implementation. No production source was changed.

## Implementation-readiness checklist

- [ ] Implement the approved physical residual scale and additive force gate; fail closed on missing scales and unsupported constraints.
- [ ] Count correction updates and evaluate residual after update 25.
- [ ] Implement the exact 13-trial derivative-certified Armijo rule; keep a route disabled until its independent derivative evidence passes.
- [ ] Implement relative minimum increment, one clipped final endpoint, exact `λ=1`, approved typed retries, and global once-only rejection accounting.
- [ ] Add the versioned WP10 v2-compatible E01-A metadata/attempt ledger while preserving existing WP10 behavior.
- [ ] Obtain separate authorization before implementation or executable V&V; preregister route-specific independent references before numerical execution.

**V&V execution:** `NOT_RUN`. No tests were created or executed; no numerical calculations, solver, `solve_model`, native FEM, or backend were run.

## Final status

- `E01_A_SCIENTIFIC_CONTRACT: FROZEN_EXPERIMENTAL`
- `E01_A_IMPLEMENTATION: NOT_AUTHORIZED`
- `E01_A_NUMERICAL_VNV: NOT_RUN`
- `J2_TANGENT_CONSISTENCY: BLOCKED_PENDING_INDEPENDENT_EVIDENCE`
- `WP_E01_STATUS: OPEN / EXPERIMENTAL_TARGET`