# WP06-D Owner decision — bounded experimental scope

**Decision ID:** `OD-029-WP06-D-EXP-01`
**Decision date:** 2026-09-19
**Status:** `CLOSED_OWNER_ACCEPTED_EXPERIMENTAL_WITH_LIMITATIONS`

## Decision

The Owner accepts the local-axial M2/M3 result as **experimental bounded
continuation evidence**. This acceptance does not award the formal WP06-D
limit-point points and does not convert the diagnostic into a postbuckling
qualification.

```text
OWNER_ACCEPTS_WP06D_EXPERIMENTAL_BOUNDED = YES
OWNER_AWARDS_WP06D_FORMAL_POINTS = 0/2
WP06D_STATUS = EXPERIMENTAL_BOUNDED_ACCEPTED
WP06E_STATUS = BLOCKED_FORMAL_D_DEPENDENCY
WP06F_STATUS = BLOCKED_FORMAL_D_AND_E_DEPENDENCY
WP06_OFFICIAL_POINTS = 4/8
GLOBAL_OFFICIAL_TOTAL = 70/100
```

## Accepted claim

The selected local-axial benchmark demonstrates that the declared M2/M3
production paths can accept 160 continuation states while preserving the
observed equilibrium and deformation envelope. The NumPy observable
recomputation and archival evidence replay support the integrity of that
bounded diagnostic result.

## Explicit exclusions

This decision does not claim:

- detection of a limit point;
- postbuckling or bifurcation qualification;
- an independent nonlinear path solve;
- a second production-solver FEM replay;
- full three-dimensional mesh convergence, because the transverse section
  remains `4x4`;
- general continuation or industrial robustness.

The historical WP06-D1 `FAIL_CLOSED` evidence remains preserved and
authoritative for its original contract. No historical result, threshold,
mechanics implementation or raw artifact is rewritten.

## Future work

If the project later requires a formal postbuckling claim, the Owner must
approve a separate frozen contract defining the benchmark, imperfection or
instability mechanism, transverse mesh hierarchy, limit-point detector,
independent nonlinear reference and production replay requirements.

Evidence: [local diagnostic requalification](wp06d-local-axial-diagnostic-requalification.md),
the independent-reference summary, and the evidence-replay record under
`qualification/0_2_9/wp06d_local_axial_diagnostic_20260919/`.
