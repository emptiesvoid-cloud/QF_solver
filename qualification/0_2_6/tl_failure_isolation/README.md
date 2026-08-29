# TL Failure Isolation

Status: `DIAGNOSTIC_ONLY`. No Total-Lagrangian, Newton, tangent, assembly,
tolerance, or release-scope change was made.

Source SHA: `e522a24394e58d79266bcfde1b431b631381a231`

## Baseline reproduction

| Case | Family/load | Mesh | Outcome | Failure step | Residual at failure |
| --- | --- | ---: | --- | ---: | ---: |
| CASE_1 | TET4 compression | 4, aspect 10 | `MAX_ITERATIONS` | 28 | `2.927069e-3` |
| CASE_2 | HEX8 compression | 4, aspect 10 | `MAX_ITERATIONS` | 12 | `1.530478e-4` |
| CASE_3 | HEX8 bending Z | 4, aspect 10 | `MAX_ITERATIONS` | 1 | `1.046399e-2` |

Each baseline reached 100 Newton iterations. The complete residual history,
assembly-call history, displacement fingerprints, state metrics and tangent
finite-difference results are stored in `tl_failure_isolation.json`.

## State and tangent observations

- CASE_1: last converged prefix had `det(F)` in `[0.978578, 0.997302]`,
  free residual `3.38e-12`, and reduced tangent condition estimate
  `1.01e6`. The last failed-step iterate remained at `det(F)` minimum
  `0.972042`; FD tangent relative error was `2.17e-9`.
- CASE_2: last converged prefix had `det(F)` in `[0.994693, 0.997156]`,
  free residual `4.10e-11`, and condition estimate `3.43e5`. The failed-step
  iterate reached condition estimate `1.91e7` with positive minimum tangent
  eigenvalue `2.32e-6`; FD tangent relative error was `2.12e-9`.
- CASE_3 fails on its first increment, so there is no previously committed
  increment. Its last iterate had `det(F)` minimum `0.992217`, condition
  estimate `2.89e4`, positive minimum tangent eigenvalue `1.53e-3`, and FD
  tangent relative error `2.01e-9`.

No baseline showed `det(F) <= 0`, a tangent-solver singularity exception, or a
finite-difference tangent discrepancy in the measured direction. These facts
do not qualify the TL route; they only bound this diagnosis.

## Controlled variations

- Doubling and quadrupling increments delayed the compressive failures but did
  not remove them. CASE_3 converged only with 4× the increments; 2× still
  failed.
- A 10% load reduction did not make any baseline converge.
- Aspect ratio 8 still failed for all three; aspect ratio 6 converged for all
  three. This is the strongest observed sensitivity and coincides with a much
  smaller tangent condition estimate.
- The neighboring three-cell mesh converged for CASE_1 but not CASE_2 or
  CASE_3.
- A `1e-3` geometry perturbation and a 90-degree rotation did not materially
  change the failure classifications.

## Classification

| Case | Diagnostic classification | Reason |
| --- | --- | --- |
| CASE_1 | `MESH_CONDITIONING` | Very high reduced tangent conditioning; aspect 6 and neighbor mesh recover it |
| CASE_2 | `MESH_CONDITIONING` | Condition estimate rises to `1.91e7`; aspect 6 recovers it |
| CASE_3 | `LOAD_STEP_TOO_LARGE` | 4× increments recover the path; 2× and smaller load do not |

The classifications are diagnostic, not acceptance decisions. Positive tangent
eigenvalues at the observed failure states do not prove absence of a physical
limit point, but no direct loss-of-stability signature was measured. The
current evidence therefore supports a Newton robustness/conditioning
investigation rather than a confirmed physical instability or solver bug.

## Provenance

The baselines and all controlled variants were run by
`scripts/run_tl_failure_isolation.py`. The harness delegates to the existing
production `solve_full_newton` and records the exact source SHA. No Arc-Length
path, solver correction, or TL promotion was performed.
