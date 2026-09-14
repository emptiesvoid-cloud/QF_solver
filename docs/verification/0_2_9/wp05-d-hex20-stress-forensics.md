# WP05-D HEX20 representative-stress forensic audit

The original frozen WP05-D result is preserved as **FAIL_CLOSED**: H2→H3 representative Cauchy `sigma_xx` delta `0.10427343557067302`, against the unchanged frozen limit `0.08`. This audit does not force qualification and does not alter the physical benchmark, observable definition, or threshold.

## Definition and independent checks

The observable is the positive reference-volume-weighted Cauchy `sigma_xx` at production integration points whose reference coordinates lie in `X/L = [0.40, 0.60]`, `Y/H = [0.70, 0.95]`, `Z/D = [0.20, 0.80]`. The H2 and H3 raw NPZ records use the production HEX20 27-point rule and `w_q det(J0)` weights.

| Quantity | H2 | H3 |
|---|---:|---:|
| Representative sigma_xx | 2914.8233075483 | 3254.14409184722 |
| Region integration points | 96 | 840 |
| Region elements | 16 | 72 |
| Region reference weight | 0.0288387345679013 | 0.0306471836419753 |
| Weighted normalized-Y centroid | 0.805555555555556 | 0.840277777777778 |
| Sigma_xx min/max | 1834.38578308055 / 4045.0423992473 | 1810.87830671972 / 5002.42866568495 |
| Weighted Y slope | 9754.54470760967 | 9773.12785040108 |

Independent raw recomputation matches the serialized production-extractor value exactly for both levels. Reversed/permuted enumeration changes the result by at most floating-point roundoff. Total reference volume is 1.0, Jacobians are positive, and the 27-point quadrature weights match the production rule to floating-point precision. H1 replay remains PASS.

## Cause localization

The region is at least 1.6 m from both the clamp (`X=0`) and loaded face (`X=4`), so clamp and load-boundary singularity sensitivity is **NO**. It is intentionally off-neutral-axis, and the bounded bending stress gradient is strong: sigma_xx is positively correlated with normalized Y (H2 `0.904469`, H3 `0.857007`).

H2 and H3 do not sample the indicator region at the same locations: H2 has weighted normalized-Y centroid `0.80555556`, H3 `0.84027778`. The resulting increase in the fixed-region quadrature estimator is therefore a mesh-location sampling effect compounded by ordinary discretization convergence. This is not a quadrature-weight, serialization, Cauchy-measure, or production-mechanics defect.

## Decision

- Defect proven: **NO**.
- Correction applied: **NO**.
- Optional H4: **NOT RUN**; no qualification rescue is implied.
- WP05-D: **FAIL_CLOSED** under the unchanged 8% threshold.
- WP05-E: **NOT RUN / dependency-blocked**.

No production mechanics or thresholds changed. Full repository suite was not run.
