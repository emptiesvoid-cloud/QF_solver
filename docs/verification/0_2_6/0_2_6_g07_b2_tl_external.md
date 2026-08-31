# 0.2.6 G07 B2 — TL external completion

Evidence ID: `026-G07-B2-TL-EXTERNAL-001`
Gate: `026-G07`
Step: `B2_TL_EXTERNAL_COMPLETION`

## Decision

`G07_B2 = PARTIAL`. The run did not change the G07 gate status, TL
formulation, Newton/physics code, thresholds, or default path.

The TET4 bounded external path is complete and usable as
`PASS_WITH_LIMITATIONS`. The HEX8 Code_Aster path is complete, but the QF
path does not reach the end of the same case; therefore no HEX8 matched-path
claim is made.

## Controlled provenance

- B1 start / B2 baseline: `1fd3cd41d1dd21e26d90851d89aa60d9429dabd9`
- runner source: `scripts/run_g07_b2_tl_external.py`
- runner source SHA: `52e45e44ab3b38031dd5062b7ed85dcb30f53d4d`
- external solver: Code_Aster 18.1.0
- pinned image: `simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435`
- machine-readable evidence: `qualification/0_2_6/g07_b2_tl_external/g07_b2_tl_external_evidence.json`

The runner records case-definition hashes, input hashes, runtime status, and
UTC capture provenance in the JSON artifact.

## TET4 — complete bounded path

The same geometry, mesh, material, nodal loading, and bounded endpoint were
used for both paths. The imperfect column was evaluated over 16 increments,
from 0.2 through 0.8 of the documented critical-load estimate. All 16
Code_Aster and 16 QF points are finite, load-monotone, and path-continuous.

| Observable | Result |
|---|---:|
| displacement maximum relative difference | `1.4115368881294746e-14` |
| displacement maximum absolute difference | `6.245221350186542e-16` |
| signed reaction maximum relative difference | `6.204270246045218e-14` |
| signed reaction maximum absolute difference | `3.694859482287339e-12` |
| QF maximum relative residual | `1.3368719921494182e-09` |
| QF minimum `det(F)` | `0.9945552598356373` |
| matched points | `16/16` |

The QF physical support reaction is defined as the negative of the QF
external-minus-internal residual at fixed DOFs and is compared with the
Code_Aster `REAC_NODA` resultant. Column stress/strain fields are explicitly
not compared because integration measures and sampling are not mapped
one-to-one.

Result: `TL_TET4_EXTERNAL_COMPLETE = YES`,
`TL_TET4_RESULT = PASS_WITH_LIMITATIONS`.

Limitations are the tested bounded load domain, the incompatible stress/strain
field mapping, and the fact that this is not a general TL or large-deformation
qualification.

## HEX8 — complete external half, incomplete matched QF path

The existing bounded HEX8 compression case was used unchanged:
`HEX8_m4_a10_compression_l0.2_d0.12`, 128 increments, distortion `0.12`,
aspect `10.0`. Code_Aster completed all `128/128` external points with the
same case geometry, mesh, material, and nodal load definition.

The QF production path did not complete. It failed deterministically at
increment `48/128` with:

`NumericalConvergenceError: Full Newton did not converge at increment 48; relative residual=4.392803e-04.`

Because both full runtime paths are required for a matched comparison, the
HEX8 result is `FAIL` for this B2 proof. No external stress, energy, or
external `det(F)` comparison is claimed; those fields are not transformed
to directly comparable QF measures. A separate diagnostic probe with 512
increments also failed later in the same physical path region (increment
192), so it was not treated as a proof or used to alter the route.

Result: `TL_HEX8_EXTERNAL_COMPLETE = NO` for the matched proof,
`TL_HEX8_RESULT = FAIL`.

## Scope and remaining gaps

- No real solver bug was identified: the observed HEX8 outcome is an
  explicit production-path non-convergence, not a silent pass, NaN/Inf, state
  corruption, or changed classification.
- `REAL_BUG_FOUND = NO`.
- `FUNCTIONAL_SOURCE_CHANGED = NO`.
- `NUMERICAL_REGRESSION = NO`.
- Full regression is skipped by the B2 policy.
- `G07-TL-008-HEX8-COMPLETE-HISTORY` remains blocking for the requested
  complete HEX8 matched-path claim.
- The G07-B1 Arc-Length `G07-ARC-002` gap remains unchanged and is outside
  this B2 step.
- G07 Owner closeout is therefore not ready; no TL promotion is performed.
