---
doc_id: DOC-029-WP03-004
revision: 0.1
status: planning
applicable_version: 0.2.9-development
---

# WP03-A — frozen robustness baseline campaign

> **Baseline definition only.** The campaign is frozen at
> ecc09f0bae2dab867c12d7e471860887f6ef0548. WP03-A does not invent result
> values or claim that these cases have been re-run.

The machine-readable record is
qualification/0_2_9/wp03_baseline_campaign.json.

## Comparison rules

- Easy-case preservation: relative difference <= 1e-9, absolute floor
  1e-12.
- Deterministic state and diagnostic digests: exact equality where the route
  is deterministic.
- A stricter existing repository tolerance remains authoritative.
- A missing result is NOT_DEMONSTRATED, never an implicit pass.

Each case must retain the model signature, displacement, load factor,
material/contact/continuation/composite digests, residual history, iteration
counts, accepted/rejected counts, cutback and line-search diagnostics, failure
reason/retry class and owner review.

## Sixteen frozen cases

| ID | Case | Route | Required baseline evidence |
| --- | --- | --- | --- |
| B01 | Easy elastic Newton | Fixed newton_raphson | Convergence and residual history |
| B02 | Small-strain J2 | Fixed material-state load control | State digest and physical result |
| B03 | Geometric TET4 | Fixed geometric nonlinear | Bounded research result and diagnostics |
| B04 | Geometric HEX8 | Fixed geometric nonlinear | Bounded research result and diagnostics |
| B05 | Frictionless penalty contact | Fixed penalty composition | Result and contact diagnostics where supported |
| B06 | Modified Newton | Fixed modified_newton | Compatibility result and iterations |
| B07 | Line-search challenge | Fixed newton_line_search | Alpha/reduction history and outcome |
| B08 | Adaptive easy increment | Adaptive load control | Growth policy and accepted history |
| B09 | Adaptive forced cutback | Adaptive load control | Rejection then accepted retry |
| B10 | Adaptive multiple cutbacks | Adaptive load control | Deterministic retry history |
| B11 | Minimum-increment terminal failure | Adaptive load control | MIN_INCREMENT_REACHED |
| B12 | Stagnation candidate | Fixed stagnation detection | Explicit convergence/stagnation decision |
| B13 | Singular tangent | Failure injection | SINGULAR_TANGENT and owner-policy class |
| B14 | Linear-solver failure | Failure injection | LINEAR_SOLVER_FAILURE and owner-policy class |
| B15 | Arc rejection and radius shrink | Arc-length | Radius/rejection history |
| B16 | Path-dependent restart/retry regression | Fixed or arc restart | Accepted-state and retry integrity record |

## Execution boundary

WP03-B/C/D capture the before results from this exact SHA before changing
the corresponding production policy. WP03-E independently replays selected
success and failure cases. No full repository suite is part of WP03-A.

The baseline campaign is therefore:

BASELINE_CASE_COUNT = 16

BASELINE_CAMPAIGN_FROZEN = YES; EXECUTION_DEFERRED_TO_WP03_IMPLEMENTATION
