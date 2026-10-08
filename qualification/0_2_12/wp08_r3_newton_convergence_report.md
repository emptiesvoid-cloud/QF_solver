# WP08-R3 — Newton convergence evidence

**Status:** bounded integration checks; not qualification.  The corrected route remains EXPERIMENTAL.

## Route and state contract

Only explicit `corrected_corotational_biot_j2/v1` selection activates this path. The existing nonlinear static Newton engine and sparse assembly are reused. Accepted material states are fixed for the whole increment and every force/tangent probe; trial states are detached. The solver's existing finalizer commits the accepted trial once, while line-search rejection and adaptive load-step rejection discard trial state.

Supported method selectors are `newton_raphson` and `newton_line_search`. Corrected modified Newton, arc-length, contact, non-`nonlinear_static` analysis, and unsupported mesh/material/domain combinations fail closed. Legacy remains the default if the selector is absent.

## Bounded convergence cases

| Case | Outcome | Quantitative observation | Meaning |
|---|---|---|---|
| Elastic TET4, reduced load | PASS | No accumulated plastic strain; status PASS | Corrected route traverses elastic assembly and Newton. |
| Plastic TET4, four fixed increments, Full Newton | PASS | 20 total Newton iterations; final recorded increment residual `8.7886e-11` in the timed comparison; status PASS | Bounded plastic equilibrium. |
| Plastic TET4, `newton_line_search` | PASS | 4 accepted load increments, 20 iterations, 4 total reductions, minimum accepted alpha `0.5`, final residual `1.436719640e-9` | Existing line search is used with corrected assembly. |
| Adaptive cutback TET4 | PASS | Initial full increment rejected at max iterations; retry at load increment `0.5`; 6 accepted increments, 30 iterations, final residual `1.604861092e-10`; 1 rejection | Failed trial did not prevent later accepted increments. |
| Continuous vs accepted-checkpoint restart | PASS | Displacements agree at `rtol=1e-11`, `atol=1e-12`; accepted state digests equal | Bounded deterministic restart from a corrected checkpoint. |

Residuals above are solver residuals for these fixtures and existing solver tolerances; they are not estimates of constitutive, truncation, or general physical error.

## Legacy comparison and run cost

Same TET4 refinement fixture, load scale `0.25`, four fixed increments, Full Newton, after two warm-up solves; one measured solve per route:

| Route | Wall time | Steps | Iterations | Final residual | Cutbacks |
|---|---:|---:|---:|---:|---:|
| Legacy corotational J2 | 1417.164 ms | 4 | 22 | `7.9823e-11` | 0 |
| Corrected corotational J2 | 2516.043 ms | 4 | 20 | `8.7886e-11` | 0 |

This single local timing is noisy and is not a performance claim. On this fixture corrected Newton used fewer iterations but took about `1.78x` the elapsed time. The finite-difference tangent adds substantial force evaluations. It is not established that this approach is economical for larger systems.

## Nonsmoothness and convergence claims

The R1 smooth-branch directional check passes on the reported noncoaxial plastic TET4 case. A separate constructed yield-surface probe detects six branch changes in the production stencil and sets `classical_derivative_claim=false`. The preregistered four-step one-sided check remains on the active plastic branch for positive perturbations and the elastic branch for negative perturbations; the last-step plateau deltas are `3.7171e-11` and `3.7216e-11`, respectively, below the frozen `2e-5` bound. The current production matrix at that point is still a central secant across the sampled active-set branches; no classical differentiability or general semismooth convergence guarantee is asserted. Global tests show convergence on the listed load paths only.

No convergence claim is made for contact, arc-length, modified Newton, mixed element families, arbitrary finite-strain plasticity, or states outside the R1 local-strain bound. These restrictions remain runtime guards, not merely documentation.

## Evidence sources

- `tests/unit/test_corotational_j2_corrected.py`: corrected elastic/plastic route, line search, cutback, restart and tangent checks.
- `tests/unit/test_corotational_j2.py`: legacy route non-regression.
- `tests/unit/test_total_lagrangian_j2.py`, `tests/unit/test_nonlinear_checkpoint.py`, `tests/unit/test_wp02_b_checkpoint_v2.py`, `tests/unit/test_nonlinear_assembly_plan.py`, `tests/unit/test_wp02_d1_arc_length_material_state.py`: neighboring integration and state paths.
- Exact final broad unit-suite and documentation results are in `wp08_r3_integrated_vnv_matrix.json`.
