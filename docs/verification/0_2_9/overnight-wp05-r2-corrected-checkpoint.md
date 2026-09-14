# WP05 overnight structural qualification checkpoint (corrected observables)

This checkpoint was derived from completed, preserved solver outputs under `qualification/0_2_9/overnight_r2/` and re-extracted into `qualification/0_2_9/overnight_r2_corrected/`. The earlier checkpoint remains immutable and is superseded for qualification observables because it used an element-centroid stress proxy. No production mechanics, thresholds, meshes, loads, solver settings, or completed displacement fields were changed.

## Execution status

- Branch: `0.2.9-overnight-wp05-wp07`
- Final tooling SHA: `dc8442fed3bf74e1fb90818378fd36f709bb846e`
- Contract SHA-256: `e8ce5ed095bf3f142b64d5a5838682c638478a5a92c8330a10af88584f52d680`
- Governing policy digests retained from completed solves: TET10 `45e52d0e143001ee979d8df711831871cb69e5ff53e7fb9086bb23bdeba6b0ea`, HEX20 `895d3c932278c0207b207318216c263a427636d57738bef730917fdc7d9b0ef5`
- Route: MINRES + Jacobi, canonical line search, floor-aware termination, 12 increments, no direct fallback
- Previous HOLD preserved: **YES**
- Corrected stress observable: reference integration-point coordinates, positive reference-volume weights `w_q det(J0)`, production Cauchy stress

## Harness correction

The first WP05 result records remain at their original paths and are not overwritten. Their stress field was labeled `FROZEN_CENTROID_REGION`; that is not the frozen WP05 integration-point contract. The corrected records use production quadrature fields and map the same quadrature points through the production TET10/HEX20 shape functions. The original solver displacement, reactions, solver diagnostics, load path, and energy are retained.

## WP05-C — TET10

H1, H2 and H3 completed. H1 replay completed with exact recorded displacement/reaction arrays, load path and Newton count. The corrected frozen H2→H3 checks are: **PASS**.

| Observable | H2→H3 relative delta | Frozen limit | Result |
|---|---:|---:|---|
| displacement | 0.00776329330247684 | 0.02 | True |
| reaction | 4.39247180510037e-14 | 0.02 | True |
| moment | 2.28997728749573e-05 | 0.02 | True |
| energy | 0.00775875510527221 | 0.02 | True |
| stress | 0.0423950241613546 | 0.08 | True |

The corrected representative stress delta is within the frozen 8% limit. TET10 equilibrium, envelope, and replay evidence also pass. WP05-C is **PASS_CANDIDATE** pending Owner review.

## WP05-D — HEX20

H1, H2 and H3 completed. H1 replay passed after the same corrected extraction. The corrected frozen H2→H3 checks are: **FAIL**. The representative stress delta is above the frozen 8% limit (`0.104273435570673`), so WP05-D is **FAIL_CLOSED**. This is a result of the frozen observable and threshold; no rescue threshold or mesh was introduced.

## WP05-E

**NOT_RUN / dependency-blocked.** The frozen contract permits cross-family execution only when both WP05-C and WP05-D pass. Since corrected WP05-D fails its stress limit, no cross-family result is claimed.

## Governance

- WP05 candidate points: C `1/1`, D `0/1`, E `0/1`; no official points awarded.
- Official total remains `50/100` pending Owner review; potential total from this campaign is `51/100`.
- Structural solver runs were not repeated; corrected evidence is a qualification-only postprocessing of completed H1/H2/H3 outputs and H1 replays.
- Full repository suite: **NO**.
- WP06/WP08: untouched.

