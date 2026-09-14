# WP05 overnight structural qualification checkpoint (R2)

This checkpoint was derived from the flushed raw records under `qualification/0_2_9/overnight_r2/`. The previous HOLD record remains immutable and is referenced, not rewritten. No production mechanics, thresholds, meshes, loads, or solver settings were changed.

## Execution status

- Branch: `0.2.9-overnight-wp05-wp07`
- Final tooling SHA: `8dd1445f685187ee3ffd1373d966cc5f37272bd8`
- Contract SHA-256: `e8ce5ed095bf3f142b64d5a5838682c638478a5a92c8330a10af88584f52d680`
- Governing policy digest: `895d3c932278c0207b207318216c263a427636d57738bef730917fdc7d9b0ef5`
- Route: MINRES + Jacobi, canonical line search, floor-aware termination, 12 increments, no direct fallback
- Previous HOLD preserved: **YES**

## WP05-C — TET10

H1, H2 and H3 completed. H1 replay completed with exact recorded displacement/reaction arrays, load path and Newton count. The frozen H2→H3 checks are: **FAIL**.

| Observable | H2→H3 relative delta | Frozen limit | Result |
|---|---:|---:|---|
| displacement | 0.00776329330247684 | 0.02 | True |
| reaction | 4.39247180510037e-14 | 0.02 | True |
| moment | 2.28997728749573e-05 | 0.02 | True |
| energy | 0.00775875510527221 | 0.02 | True |
| stress | 0.11604713189563 | 0.08 | False |

The representative stress delta is above the frozen 8% limit, so WP05-C is **FAIL_CLOSED**. This is preserved as qualification evidence; no rescue threshold or mesh was introduced.

## WP05-D — HEX20

H1, H2 and H3 completed. H1 replay passed. The frozen H2→H3 checks are: **PASS**. All five observable limits, equilibrium limits, and the deformation envelope pass. WP05-D is **PASS_CANDIDATE** pending Owner review.

## WP05-E

**NOT_RUN / dependency-blocked.** The frozen contract permits cross-family execution only when both WP05-C and WP05-D pass. Since WP05-C failed its stress limit, no cross-family result is claimed.

## Governance

- WP05 candidate points: C `0/1`, D `1/1`, E `0/1`; no official points awarded.
- Official total remains `50/100` pending Owner review; potential total from this campaign is `51/100`.
- Structural solves were run only for the declared WP05-C/D meshes and H1 replays.
- Full repository suite: **NO**.
- WP06/WP08: untouched.

