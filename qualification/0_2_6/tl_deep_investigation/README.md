# TL Deep Investigation

Status: `DIAGNOSTIC_ONLY` (not a qualification or promotion decision)

This corpus was run from `e522a24394e58d79266bcfde1b431b631381a231` using the
existing Total-Lagrangian verification builders. No solver formulation,
Newton strategy, tangent, assembly, tolerance, or release claim was changed.

## Executed observations

| Study | TET4 | HEX8 | Observation |
| --- | ---: | ---: | --- |
| Large rotation | 1 | 1 | Existing research path completed with finite residuals and positive det(F) |
| Mesh sensitivity, 1 to 2 cells | 1 | 1 | Existing bounded internal sensitivity path completed |
| Multi-element load-step sensitivity | 1 | 1 | Existing coarse/reference/refined load histories completed |
| Small-load finite-kinematic limit diagnostic | 1 | 1 | Existing research comparison completed |

Total executed family observations: **10**. The mesh study is intentionally
only a two-level diagnostic observation; it is not mesh qualification.

## Findings

- Small-strain and finite-kinematic comparisons remain research diagnostics;
  no numerical acceptance band was applied.
- Objectivity and large-rotation behavior were exercised through the existing
  rotation and geometric paths. No new solver defect was proven by this run.
- Mesh and increment results are recorded for follow-up; no convergence claim
  is made from the limited diagnostic levels.
- The finite-kinematic J2 path remains research-only and is not promoted.
- The current public TL route accepts nodal dead loads only; distributed-load
  rejection is retained as an explicit scope boundary.

## Failure zoo

`tl_failure_zoo.json` preserves two discriminating expected-boundary cases:

1. `invalid_current_configuration`: `EXPECTED_LIMITATION`; current det(F) is
   rejected by the existing TL contract.
2. `unsupported_distributed_load`: `EXPECTED_LIMITATION`; the public geometric
   nonlinear scope accepts nodal dead loads only.

These are not classified as solver bugs without a separate model, mesh, BC,
and physical-relevance audit. The machine-readable full report is in
`tl_investigation_report.json`.

## Follow-up only

The next planning step should audit the recorded mesh/increment trends, add
case-specific model checks for any anomaly, and review whether a broader
multi-level corpus is needed. Any solver correction requires a separate,
evidence-backed change and a new provenance SHA.
