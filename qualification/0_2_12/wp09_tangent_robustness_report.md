# WP09 — Corotational tangent robustness

**Record type:** bounded implementation report; not qualification.
**Branch:** `codex/v0.2.12-wp09-corotational-tangent-robustness`
**Base:** WP08-R3 `ef139f0cef60718407391a1ec0e5d956e5ecc86f`
**Formulation:** `corrected_corotational_biot_j2/v1` (explicit opt-in; `EXPERIMENTAL`).

## Result in brief

WP09 removes a demonstrated origin-cancellation path in the corrected element geometry and its displacement-gradient evaluation, adds fail-closed floating-point resolution diagnostics, and makes branch status and tangent strategy visible to callers. The force equations, constitutive update, production finite-difference step, accepted-state transaction, and unsymmetrized tangent are unchanged in meaning. Numerical comparisons against the exact WP08-R3 implementation show force/tangent agreement at the reference geometry to numerical precision on the four tested solid families; translated fixtures improve substantially and unresolved inputs are refused.

This is bounded numerical verification, not a qualification or a general guarantee for arbitrary meshes. The central-difference tangent remains expensive (`2*n_dof+1` corrected force evaluations) and is not a classical derivative at a detected branch transition. No general semismooth Newton guarantee is claimed.

## Baseline audit and cause

The WP08-R3 production formula was already

`K[:,j] = (f_corr(u + h e_j; state_n) - f_corr(u - h e_j; state_n))/(2h)`,

with fixed accepted material state, `h = 1e-5 V0^(1/3)`, and no tangent symmetrization. Thus, the remaining origin dependence was **not** caused by the corrected-route `h` formula directly containing `max(abs(coords))`; that dependency had already been removed by R3. The observed residual mechanism was cancellation in forming quadrature geometry/Jacobians from uncentered absolute coordinates and in evaluating a displacement gradient from a large common nodal displacement. At sufficiently large offsets, the stored coordinates themselves also lose local geometric information.

| Numerical risk | WP08-R3 implementation / root cause | WP09 response | Validation | Cost / regression risk |
|---|---|---|---|---|
| Origin cancellation in quadrature geometry | Shape gradients contracted with absolute coordinates; floating summation loses translation invariance | Center reference coordinates at node 0, normalize by maximum pairwise distance, then restore weights by `L^3` and gradients by `1/L` | Independent comparison to R3 plus translated TET4/TET10/HEX8/HEX20 fixtures | Small local preprocessing; bounded risk, scale covariance tested |
| Common rigid nodal displacement cancellation | `local.T @ gradients` evaluated before removing common translation | Compute `(local-local[0]).T @ gradients`; this subtracts a rigid translation and leaves the exact affine gradient identity unchanged | Rigid displacement sweep and full corrected Newton translated mesh | One subtraction per node; no constitutive change |
| Unresolvable reference coordinates | No explicit ratio of coordinate ULP to local length | Reject corrected route when `spacing(max(abs(coords)))/L_pairwise > 1e-8` | Pass at 0 through `5e7` on the sampled fixture; reject at `1e9` | Intentional narrower corrected-route admission; legacy route unchanged |
| Unrepresentable tangent stencil | Perturbations can be rounded away around very large supplied `u` | Reject if `spacing(max(abs(u))) >= h`, with `NUMERICALLY_AMBIGUOUS` diagnostics | A `1e12` common displacement fails closed; accepted state unchanged | No changed step; fail-closed behavior |
| Plastic branch crossing | A central difference may span elastic and plastic active sets | Per-integration-point status distinguishes smooth, transition, ambiguous, invalid; no classical derivative claim on crossing | Frozen-yield fixture and one-sided branch diagnostics | Same force count; no unsupported semi-smooth claim |
| Repeated quadrature preparation | Geometry data could be recomputed repeatedly for each force evaluation | Exact-input, element-instance cache; changed coordinates miss and recompute | Hit/miss assertions and performance measurements | No global cache; a retained cache entry per element instance |

The metric uses the maximum pairwise nodal distance for local scale, not `V^(1/3)`, to assess whether the stored coordinates resolve the element. The production tangent step remains the R1/R3 contract `1e-5 V0^(1/3)` for all translational DOFs. Geometric scale changes and coordinate-origin shifts are treated separately; the geometry is not silently repaired.

## Implemented behavior and invariants

The corrected element now stores normalized, centered reference quadrature data in an exact-coordinate-keyed **instance-local** cache. Cache invalidation is exact: any change to shape, dtype, or coordinate bytes changes the key. There is no global mutable cache. Restored quadrature weights/gradients are dimensionally equivalent to the original geometry data. The corrected route rejects non-finite and unresolved geometry; the legacy branch retains its historical calculation.

The tangent remains a raw central difference of the corrected force. It continues to use one base force and two force evaluations per displacement DOF, each from the same accepted state. Trial states returned by perturbed calls are discarded. It is not symmetrized. Failed force evaluations invalidate the tangent and identify side/column; they do not trigger a fallback. The caller receives diagnostics for strategy version, length and step, coordinate resolution, cache counts, branch counts, raw skew, failure cause, and whether a classical derivative claim is warranted. Solver result provenance records strategy version `origin_centered_scaled_geometry/v2` without changing checkpoint schemas.

Constitutive equations and force outputs are not intentionally changed. At an unshifted reference geometry, a dynamic comparison against source loaded from the exact WP08-R3 commit found maximum relative force differences `0` (TET4), `1.41e-13` (TET10), `2.995e-13` (HEX8), `2.403e-13` (HEX20); maximum tangent differences were `0`, `8.33e-11`, `1.30e-10`, and `5.48e-11`, respectively. Force counts remain `25/61/49/121` for those families.

## Frozen numerical checks

Thresholds in `wp08_r1_vnv_acceptance_matrix.json` were not changed. In particular, the strict R1 origin-invariance threshold `1e-9` through `1e3` characteristic lengths remains intact. The preregistered WP09 extension checks are additional bounded observations, not replacements for R1 acceptance.

On one integer-coordinate TET4 fixture with unchanged nodal displacement, offsets `0`, `1e3`, `1e6`, and `5e7` produced identical force/tangent arrays; maximum coordinate-resolution ratio remained within `1e-8`. Offset `1e9` was refused at ratio `8.43e-8`. At the largest offset, the result is no longer silently treated as equivalent because input quantization is observable.

Adding common rigid displacement components of magnitude `1e3` and `1e6` left the step unchanged. At `1e6`, observed relative force and tangent differences were `1.86e-8` and `4.90e-6`, within the frozen `2e-5` directional/tangent verification bound on that fixture. At magnitude `1e12`, the central stencil is unresolvable and is refused. No accuracy claim is made for displacements beyond the tested representable band.

For smooth branches, the independent multi-step directional sweep showed an elastic maximum scaled error `3.16e-13`. On three smooth noncoaxial plastic directions, the maximum at the frozen production-step set was `1.5469e-5` (limit `2e-5`); production versus the independent `3e-6 L` step differed by `1.73185e-7`, with a `1e-5 L`/`3e-6 L` plateau delta `1.42165e-7`. A broader step sweep exhibits the expected truncation-dominated large-step region, a stable middle plateau, and roundoff growth at the smallest steps. The exact-yield test is reported separately: six integration-point branch switches occur in the production stencil, so the result is a bounded secant and not a classical derivative.

See `wp09_perturbation_policy.json` and `wp09_directional_derivative_evidence.json` for machine-readable criteria and observations.

## Newton, mechanics, and compatibility

The global corrected Newton fixture translated by `[1e6,-0.6e6,0.4e6]` passed with identical displacements and material states and the same iteration count at every step (4 load steps, 5 iterations each). Paired repeated runs of the bounded WP08-R3 global fixture remained converged: WP08-R3 median `2.53121 s`, WP09 median `2.54170 s`, ratio `1.00414`; both used 4 steps/20 iterations, zero cutbacks and zero line-search reductions. This is within run noise; it is not a speedup claim.

The direct WP08 mechanical checks (objectivity, virtual work, angular momentum, Cauchy/PK2 symmetry, noncoaxial plastic history, transaction/restart, legacy and TL J2) are rerun as tests. WP09 changes no constitutive formula, stress semantics, state schema, checkpoint format, or force/tangent pairing. Existing restart identity remains formulation-bound. The tangent strategy version is additive result provenance; it is not silently migrated into old result records. Historical gates, maturities, and release status remain unchanged.

## Limits and gate interpretation

The coordinate resolution guard is an explicit numerical-domain boundary, not an altered physical scope. Its ratio is conservative and tested on the listed fixtures only. Floating-point precision still imposes an unavoidable ceiling on representing small local geometry after large global translation; refusing that input is preferable to computing an apparently valid but corrupted Jacobian.

The production tangent still costs `2*n_dof+1` force evaluations. WP09 does not establish a universal improvement in element or global runtime, does not prove all possible plastic paths differentiable, and does not provide semi-smooth Newton theory. A future analytic/algorithmic tangent could reduce cost, but would require a separately derived and independently verified implementation.

The complete unit run emits the repository's non-failing source-size advisory for `corotational_j2.py` (766 lines at the WP08-R3 base; 978 lines after WP09). WP09 keeps the changes localized to the existing corrected-route mixin rather than introducing another tangent framework; a later maintainability review may consider extracting helpers without changing the numerical contract.

This report does not close QF0212 gates. Preserve `WP08_STATUS=PASS_BOUNDED`, `CORRECTED_J2_MATURITY=EXPERIMENTAL`, `HISTORICAL_G03=FAIL_PRESERVED`, `HISTORICAL_WP14=HOLD_NOT_PROMOTED`, `WHOLE_REPOSITORY_ARCHIVE_CLEARED=NO`, and `RELEASE_PUBLICATION_AUTHORIZED=NO`.

## Validation run record

On the final WP09 source/test tree: corrected WP09 tests `39 passed`; selected legacy/TL/Newton/state/checkpoint and WP02-WP07 regressions `188 passed`; full `tests/unit` `3322 passed, 93 skipped, 0 failed` in `1353.83 s` with six warnings (one source-size advisory and five NumPy determinant warnings from intentional failure-path tests); documentation tests `88 passed, 6 skipped`; Ruff lint/format passed; targeted mypy passed for the two modified source modules. The exact commands and classifications are recorded in `wp09_regression_matrix.json`. No source or test files were changed after the full unit run; only qualification records were edited afterward.
