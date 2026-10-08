# WP09 plastic-branch diagnostics

**Record type:** bounded numerical diagnostics, not qualification.

## Classification contract

The corrected tangent reports one of:

- `SMOOTH_ELASTIC`: all integration points expose boolean elastic-branch evidence and base/plus/minus remain elastic.
- `SMOOTH_PLASTIC`: all relevant points remain on the same plastic branch for the production stencil.
- `BRANCH_TRANSITION`: at least one plus/minus evaluation differs from the base active branch. The matrix is a central secant; a classical Jacobian is not claimed.
- `NUMERICALLY_AMBIGUOUS`: branch metadata is unavailable, the reference geometry or stencil is below floating-point resolution, or the numerical derivative cannot be interpreted as a smooth-branch derivative.
- `INVALID_STATE`: local force evaluation or finite-value checks fail. The tangent call raises; no fallback matrix is returned.

Per-column and per-integration-point classifications are available in the element's last corrected tangent diagnostics. Perturbed constitutive states are discarded. All evaluations use the same accepted state, and no perturbed state is committed.

## Evidence

On the WP08-R3 exact-yield fixture, six integration-point branch switches were observed in the production central stencil. Its one-sided plastic and elastic diagnostics each showed a plateau delta around `3.72e-11`, but the production result is still labeled `BRANCH_TRANSITION`; those one-sided numbers do not establish a classical derivative at yield.

On the tested smooth noncoaxial plastic history, three independent direction seeds stayed on the plastic branch. The maximum scaled derivative error at the frozen production-step set was `1.5469e-5`, below the unchanged R1 limit `2e-5`; the production/independent-step plateau comparison was `1.42165e-7`. Smooth elastic directions had maximum error `3.16e-13`.

The multi-step sweep documented in `wp09_directional_derivative_evidence.json` shows truncation error at large `h`, a middle stable region, and roundoff growth at very small `h`. This is a bounded characterization, not an adaptive per-call step selector. The production step remains unchanged.

## Limits

The current branch signal is based on the material update's elastic/plastic diagnostic. It does not characterize every possible internal constitutive sub-branch or prove generalized differentiability. No automatic one-sided or regularized production tangent is introduced. Newton retains its existing failure/line-search/cutback behavior; no new semismooth method is claimed. Missing branch evidence suppresses a classical derivative claim rather than defaulting to elastic.
