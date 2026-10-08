# WP09 bounded Newton robustness report

**Record type:** bounded implementation verification, not qualification. The corrected route remains `EXPERIMENTAL` and explicitly selected; legacy remains the default.

## Methods

No Newton algorithm, line search, cutback, convergence criterion, or state transaction was redesigned. The corrected force and raw corrected tangent remain paired. Every tangent column evaluation starts from the same accepted material state. An invalid stencil or failed perturbed force raises with a status and does not return a fallback tangent. Existing Newton logic determines whether to line-search, cut back, or fail.

The targeted WP09 regressions cover corrected elastic/plastic solves, noncoaxial history, line-search and cutback paths, failed trial-state isolation, corrected checkpoint/restart, and legacy/TL routes. The exact targeted and final full-suite counts are recorded in `wp09_regression_matrix.json` after the final run.

## Translation robustness fixture

The same bounded corrected global model was solved at its original origin and after translating all nodes by `[1e6,-0.6e6,0.4e6]`. Both returned `PASS`; physical displacement arrays and material-state digests matched exactly in the run, as did per-step iterations. Each used four load steps and five Newton iterations per step. This tests a representable translated mesh, not arbitrary coordinate magnitudes.

## Paired timing fixture

The exact WP08-R3 element implementation was loaded from the base commit for a paired comparison with the WP09 implementation in the same process. A bounded TET4 corrected nonlinear-static case was run three times per implementation. WP08-R3 median was `2.5312119 s`; WP09 median was `2.5417024 s` (ratio `1.00414`). Both converged in four steps and 20 iterations with zero cutbacks and zero line-search reductions. The difference is within timing variability; no speedup or material regression is inferred.

Separate WP09 tests exercise line search and cutback on the existing corrected route. Their success establishes those bounded paths only; it does not guarantee convergence for all plastic histories, particularly at branch transitions.

## Interpretation and limits

Translation conditioning improved without changing the constitutive equations or solver logic. The new fail-closed guards make unresolvable geometry/stencils explicit; they are not a new Newton recovery policy. Plastic branch transitions continue to use existing solver behavior while the tangent reports that a classical derivative is not established. Non-converged solutions remain failures; no test converts them into successful results.

WP09 does not claim global Newton robustness, quadratic convergence at nonsmooth yield points, industrial scaling, or broad restart migration. WP10 remains unauthorized and unstarted.
