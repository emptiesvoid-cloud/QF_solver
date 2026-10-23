# WP-E01-B2 J2 Tangent and Constitutive Robustness Campaign

**Date:** 2026-10-20  
**Branch:** `codex/qf-wp-e01-a-implementation-20261020`  
**Baseline:** `49c9d95d2a193947713fd7e157080d78e3724163`  
**Implementation/evidence commit:** recorded below; this report is documentation-only.

## Executive result

The small-strain J2 stress update matched the independent tensor-form material-point oracle over elastic, plastic, hydrostatic, shear, loading, unloading, reloading, reverse-loading, perfect-plasticity and linear-hardening cases. A branch-aware directional sweep for the elastic and smooth-plastic branches found a local two-decade finite-difference stability window in the tested cases. At that window the worst reported normalized tangent error was below `8e-10`; error increased at the smallest steps, consistent with cancellation. This supports a **candidate** tangent criterion for Owner review; it does not freeze the threshold or qualify J2.

Finite-output guards now reject nonrepresentable elastic stiffness, trial stress, corrected state/work values and malformed or nonfinite algorithmic tangents before a trial state is returned. The historical direct-route `plastic_dissipation` computation and field name were preserved.

The E01-A checkpoint ledger remains structurally useful and validates identities, chronology, intervals, retry counts and half-step transitions. It does not persist the typed increment-dependent admissibility evidence behind a retryable classification. Adding that evidence requires a reviewed schema extension, so no checkpoint schema or WP10 behavior was changed.

## Scientific boundary

The governing Owner freeze remains in force:

- `J2_TANGENT_CONSISTENCY = BLOCKED_PENDING_INDEPENDENT_EVIDENCE` until the Owner freezes an acceptance criterion and reviews the evidence.
- No Full Newton J2 validation claim is made.
- No production Armijo derivative certificate was registered; `E01A_VERIFIED_DERIVATIVE_CERTIFICATES` remains empty.
- No native FEM, public solver, `solve_model`, backend or production J2 element/Newton integration was run.
- `plastic_dissipation` remains a historical result with route-specific computation; it is not declared thermodynamic dissipation.

## Constitutive contract traced in source

For the direct material-point route, the code uses small-strain engineering-Voigt strain and symmetric tensor-stress components ordered `[xx, yy, zz, xy, yz, xz]`. The elastic matrix uses shear modulus `mu` on shear diagonals, so the strain shear entries are engineering shear while stress shear entries are tensorial shear.

With `eps_e = eps - eps_p^n`, the discrete update is:

\[
\sigma^{tr}=C:eps_e,\quad s^{tr}=dev(\sigma^{tr}),\quad q^{tr}=\sqrt{\frac32 s^{tr}:s^{tr}},
\]
\[
f^{tr}=q^{tr}-(\sigma_{y0}+H\alpha_n).
\]

If `f_trial <= 0`, the update is elastic. Otherwise:

\[
\Delta\gamma=\frac{f^{tr}}{3\mu+H},\quad \alpha_{n+1}=\alpha_n+\Delta\gamma,
\]
\[
\Delta eps_p=\frac32\Delta\gamma\frac{s^{tr}}{q^{tr}},\quad
s_{n+1}=\frac{q_{n+1}}{q^{tr}}s^{tr},\quad
q_{n+1}=\sigma_{y0}+H\alpha_{n+1}.
\]

The implemented engineering-Voigt algorithmic tangent is assembled from the radial-return derivative and then symmetrized. The independent derivative sweeps compare the returned tangent action with directional finite differences of a separate tensor-form reference from a fixed incoming state. They do not differentiate a mutated material history.

Source locations: `src/solveur/materials/solid.py:102-307` (parameters, return map, tangent), `:310-345` (Voigt/tensor and equivalent-stress helpers), and `tests/unit/test_wp_e01b_j2_constitutive_oracles.py:1-470` (independent reference and regressions).

## Tangent evidence

The smooth plastic sweep used `H = 0` and `H = 1500 MPa`, with normal-mixed, engineering-xy-shear and six-component normalized perturbation directions. It held the incoming state fixed, verified both perturbed states remained on the plastic branch, and used logarithmic steps `h = 1e-3 ... 1e-10` in engineering strain. The tested smooth-branch minimum trial-yield margins were approximately `561 MPa` (normal-mixed), `751 MPa` (engineering xy shear), and `708 MPa` (six-component), so the reported local window did not approach the yield switch.

The normalization used in the diagnostic was:

\[
C_{ref}=K+2\mu,\qquad
 e_T(h,p)=\frac{\|C_{alg}p-D_h\sigma\|_2}
 {\max(\|C_{alg}p\|_2,C_{ref}\|p\|_2)}.
\]

`C_ref` has stress units; `e_T` is dimensionless. The adjacent finite-difference change was normalized by `max(||D_h sigma||, C_ref ||p||)`.

| Engineering-strain step `h` | Maximum `e_T` across tested H/directions | Interpretation |
|---:|---:|---|
| `1e-6` | `7.930e-10` | In local stable window |
| `1e-7` | `1.028e-11` | In local stable window; minimum observed error |
| `1e-8` | `7.138e-11` | In local stable window |
| `1e-9` | `8.845e-10` | Cancellation begins to increase error |
| `1e-10` | `4.817e-9` | Small-step cancellation is material |

Across all tested directions, the maximum adjacent finite-difference change was about `7.901e-10` from `1e-6` to `1e-7`, and `6.686e-11` from `1e-7` to `1e-8`. At larger steps, the error decreased with step refinement, consistent with centered-difference truncation. At smaller steps, it rose, consistent with floating-point cancellation.

The elastic sweep checked normal, pure engineering-shear and six-component directions at `h = 1e-6, 1e-8, 1e-10`, with both perturbations remaining elastic and the incoming state unchanged. Its source assertions require finite errors and correct branch selection; the test does not impose an elastic tangent threshold.

At the yield switch, the test deliberately uses one-sided behavior rather than a centered derivative across branches. In its engineering-shear fixture the elastic-side slope is `400 MPa` and the plastic-side slope is approximately `30.769 MPa`; the jump is expected from the active-set change and is not a smooth-branch tangent failure criterion.

### Recommended Owner decision, not frozen

Replace the older proposed `tau_T = 2e-5` with a **proposed** smooth-branch threshold `tau_T = 1e-8`, using the normalized error above and `C_ref=K+2mu`. Require both (a) tangent error and (b) adjacent centered-difference change to be at most `1e-8` over at least two consecutive decade refinements in a branch-stable window, for at least three independent directions, with the incoming state fixed and positive branch margin verified on both sides. Retain one-sided checks at the yield switch as a separately reported active-set characterization, not as the smooth tangent gate.

The tested window satisfies this proposal with at least about a 12x error margin in the worst listed point. The proposal is limited to the current material parameter fixtures and double-precision implementation. Broader parameter, loading-path and independent-oracle coverage is still needed before Owner freeze. The source test prints these diagnostics and does **not** assert the proposed threshold or plateau rule.

## Robustness correction and evidence

`solid.py` now checks the computed 6x6 elastic stiffness for shape/finiteness; catches overflow or zero-division while forming it; checks trial stress and trial yield scalars; and checks corrected scalar outputs, stress/state arrays, and tangent shape/finiteness before returning a plastic trial state. Arithmetic that may overflow is contained under NumPy error-state handling, followed by explicit refusal. No material formula, supported finite-input criterion or public field meaning was changed.

The prepared regressions cover finite-but-unrepresentable stiffness (`E=1e308`, `nu=0.49`), finite strain that overflows the trial stress, and a nonfinite tangent injected at the material method seam. They passed in the authorized numerical-unit module. This is bounded material-point evidence, not proof for every parameter or integration-point route. Prior accepted state values are checked for input shape/finiteness and basic scalar admissibility, but the method does not add a full cross-field consistency proof for an arbitrary externally supplied state.

## E01-A checkpoint rejection-ledger provenance

The current producer records rejection index, attempt ID, accepted step/load coordinate, base and accepted-state identities, attempted target/increment, failure reason, retryability and rollback verification (`src/solveur/core/nonlinear/load_control.py:578-593, 754-770`). The validator checks count/ledger agreement, unique IDs, identity agreement, load interval/minimum-step validity, permitted retry reason classes, chronology, half-step ratio, attempt ordinal and active-attempt reconciliation (`src/solveur/core/nonlinear/e01a.py:634-856`).

This catches inconsistent and impossible history in the reviewed paths. However, `failure_reason` is a string and `retryable` a boolean; the ledger does not persist the typed contributor evidence or its source/identity that justified an increment-dependent retry. The current runtime check can validate the recorded class but cannot independently reconstruct that contributor evidence from historical metadata. Recommended minimal future design: an additive versioned `retry_evidence` subrecord containing evidence type/schema, contributor identity, attempted interval, accepted-state identity, and a canonical digest or immutable reference to the typed evidence payload. Require the validator to bind it to the attempt and reject missing evidence for any retryable admissibility reason. This is an Owner decision/schema change; it was not implemented. WP10 v2 behavior and the frozen global 25-rejection budget are unchanged.

## Legacy `plastic_dissipation` semantics

| Route | Source computation | Measures/convention | Meaning supported by source | Public-result limitation |
|---|---|---|---|---|
| Direct small-strain material point | `D_n + 0.5 * (sigma_n + sigma_{n+1}) dot Delta_eps_p` | Tensorial stress Voigt dotted with engineering plastic-strain Voigt; stress × strain, i.e. energy density | Endpoint-trapezoidal plastic stress-work accumulation for that update path; not proven equal to thermodynamic dissipation | Historical name/value preserved; generic state serialization filters the field and the solid public subset does not include it |
| Corrected corotational J2 state | `sigma_y0 * alpha_{n+1}` | Stress × equivalent plastic strain, energy density | Distinct accumulated yield-work/dissipation-like state; source also stores `0.5 * H * alpha^2` as hardening energy | Generic serializer filters `plastic_dissipation`; public solid subset omits both this and `hardening_energy` |

Under ideal linear isotropic hardening, `sigma_y0 alpha` and `H alpha^2/2` have a thermodynamic derivation when the internal-variable and work conventions are those of that model. That does not make the direct endpoint-trapezoid history identical, nor does it establish route-wide API semantics. Recommendation: preserve old values and names; defer public energy-field harmonization until the Owner approves definitions, cumulative/incremental semantics, availability and schema versioning.

Source locations: `src/solveur/materials/solid.py:219-225`; `src/solveur/elements/solid/corotational_j2.py:408-459`; `src/solveur/post/solid_results.py:512-539`; `src/solveur/post/solid_recovery.py:167-194`.

## Newton/J2 integration readiness

The production nonlinear path creates an isolated trial state, calls the owner's internal-force/tangent assembly with trial displacement and material state, applies returned material-state updates to the trial, and commits only after the increment passes the controller's acceptance route (`src/solveur/core/nonlinear/load_control.py:175-198, 271-282, 372-390, 997-1009`; transaction operations are in `src/solveur/core/nonlinear/state.py:150-240`). The J2 material is consumed by solid elements, including the corotational route (`src/solveur/elements/solid/corotational_j2.py:408-465, 657-795`).

A bounded next synthetic campaign is prepared but **not run**:

1. Define a test-only one-DOF kinematic map `eps(u)=B u` and scalar quadrature weight `w`; independently form `R(u,lambda,z_n)=lambda*fbar - w*B^T sigma(Bu,z_n)` and `dR/du=-w*B^T C_alg B` from a fixed accepted state.
2. Compare the assembled directional derivative against centered residual differences on elastic and smooth plastic branches, with branch margins and Voigt work-conjugacy checked. Keep the material state immutable for every perturbation.
3. Exercise accepted/trial state isolation, forced synthetic increment failure, rollback, half-step retry and exactly-once commit through the internal transaction seam, with state digests before and after rejection.
4. Exercise the E01-A fail-closed behavior while the production Armijo certificate registry is empty. Do not run a J2 production route through Armijo until a route certificate has been separately reviewed and approved; do not add one in this campaign.
5. Cover rejection/checkpoint identity, restart ledger persistence and invalid metadata at the already-reviewed policy/helper level. Keep crash durability and native element assembly out of scope.

This separates material derivative/transaction evidence from a route-certified nonlinear solve. The current production Armijo registry is empty, so the exact blocker to an integrated E01-A/J2 Newton solve is route-level derivative certification, not a missing claim of successful convergence.

## Test chronology and safety

All executions were limited to the already reviewed Python numerical-unit modules and the pure-unit collection-safety module. The selected imports reach NumPy algebra and Python synthetic helpers only; static import-closure review found no reachable Gmsh/native FEM, public solver, backend, worker or child-process path. The one preflight attempt that mistakenly expected the collection-safety module to be `NUMERICAL_UNIT` was corrected after confirming its existing `PURE_UNIT` classification; no pytest ran during that blocked preflight. The J2 test remained registered as `NUMERICAL_UNIT` with an exact SHA-256 digest; classifications were not broadened.

| Execution | Command | Result | Wall time |
|---|---|---:|---:|
| J2 material-point oracle, initial scale review | `python -m pytest -q -s tests/unit/test_wp_e01b_j2_constitutive_oracles.py` | 28 passed | 0.80 s |
| J2 material-point oracle, final `C_ref=K+2mu` | `python -m pytest -q -s tests/unit/test_wp_e01b_j2_constitutive_oracles.py` | 28 passed | 0.78 s |
| E01-A synthetic integrated regression | `python -m pytest -q tests/unit/test_wp_e01a_integrated_vnv.py` | 39 passed | 2.00 s |
| E01-A policy and collection safety | `python -m pytest -q tests/unit/test_wp_e01a_policy.py tests/unit/test_pytest_collection_safety.py` | 25 passed | 1.41 s |

No test failures occurred. The tangent module's thresholds remain diagnostic-only; no qualification gate was added. Static AST parsing passed for changed Python files, `git diff --check` passed, the J2 test registry digest matched, and the production Armijo certificate registry remained empty.

## Independent read-only review

An existing reviewer performed a source-only pass after the changes. This was not a blind review because the reviewer shared task history; it did not edit source or run tests/calculations. It reported no P0/P1 findings and raised these P2 items:

1. The tangent sweep prints finite-difference stability metrics but does not assert a plateau or threshold; the observed runtime evidence here must not be described as a test-enforced gate.
2. Checkpoint retry records omit typed increment-dependent contributor evidence; a versioned schema decision is needed for stronger provenance.
3. Direct and corotational `plastic_dissipation` semantics differ and are not harmonized through the public result subset.

## Decisions for Owner review

1. **Tangent:** approve, revise or defer the proposed `tau_T=1e-8`, normalized scale, two-decade plateau rule and branch-aware scope. Until then, keep `J2_TANGENT_CONSISTENCY` blocked.
2. **Retry provenance:** decide whether to add the versioned retry-evidence subrecord and specify compatibility/migration behavior. No schema change is included here.
3. **Energy semantics:** keep public energy outputs deferred, or approve a later versioned field contract separating plastic stress work, hardening storage and thermodynamic dissipation. No historical values were changed.
4. **Integrated solve:** separately authorize any executable Newton/J2 integration campaign and any test-only or production route derivative certificate. Production Armijo certification remains absent.

## Files, hashes and commits

Implementation commit: `6a751b7a92f77f083201888bdb1a289a649d6015`.

| File | SHA-256 |
|---|---|
| `src/solveur/materials/solid.py` | `7d8223c81999d037900c26bf1a6a2abc9f4b47c0cff597f4be0cf0163e8092aa` |
| `tests/unit/test_wp_e01b_j2_constitutive_oracles.py` | `e7327058ddb5d107b7788dd69d1727794a2f4c22598c03426bb01253257703be` |
| `tests/conftest.py` | `5f90d53935a25bbfab31818d6988d30c3fdecfb74a573273e270311d468111b8` |

No roadmap, historical qualification record, WP-D01 or WP-D02 file was modified.
