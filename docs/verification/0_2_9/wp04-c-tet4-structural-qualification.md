# WP04-C — TET4 bounded structural qualification

Status: **HOLD — G04-10 does not meet the frozen mesh-convergence gate**.

This controlled campaign used the frozen record
`qualification/0_2_9/wp04_c_tet4_campaign.json`, created before result
execution at SHA `48bfa83bc517e031cdab4876970a4f511f744e35`. It is a
qualification-only harness: no production numerical source, formulation,
tolerance, maturity claim, or historical 0.2.8 evidence was changed.

## Frozen campaign

The bounded problem is a `4.0 x 0.5 x 0.5` Total-Lagrangian StVK TET4
cantilever, with `E=1.0e6`, `nu=0.30`, all translations fixed on the `x=0`
face, and a total mesh-independent nodal dead load `(0, -50, 0)` distributed
over the complete `x=4` face. The conforming six-TET cell split is evaluated
at `8x4x4`, `16x8x8`, and `24x12x12` cells, respectively 768, 6144, and
20736 TET4 elements.

The stress observable is the volume-weighted Cauchy `sigma_xx` over reference
element centroids satisfying `0.40 <= x/L <= 0.60`, `0.75 <= y/H <= 0.90`,
and `0.25 <= z/D <= 0.75`. It excludes clamp and loaded-face singular zones.
Force and moment balance use deformed physical nodal coordinates about the
global origin; this is required for finite-kinematics rotational balance.

## Outcome

The local formulation identities retained from WP04-B remain positive. The
TET4 structural campaign also passes its bounded small-displacement, global
equilibrium, final load-step, replay, envelope, and explicit-failure checks:

- Smallest-load (`1e-3`) nonlinear-to-linear displacement error:
  `2.1032185690777483e-05`; reaction error: `3.384021633463905e-11`.
- Maximum force and moment balance errors across structural meshes are below
  `1e-8`; the M2 full-load values are `4.8614534847223086e-14` and
  `4.6952491717050014e-15`.
- The 6/12/24/48 full-load paths converge to the same M2 final equilibrium;
  the largest final relative difference against 48 steps is
  `8.512408733079143e-14`.
- Three M2 replays are bitwise-identical for displacement, accepted state and
  semantic digests.
- The structural envelope remains conservative: M2 has minimum `det(F)`
  `0.9953204032824443`, principal stretches
  `[0.9929869288961893, 1.007307780867781]`, and maximum
  `||E||_F` `0.0076601460588609695`.

G04-10 fails exactly at the frozen fine-vs-medium comparison:

| Observable | Frozen limit | M3 vs M2 |
| --- | ---: | ---: |
| Loaded-face transverse displacement | 2% | 16.40618103457515% |
| Reaction resultant | 2% | 3.055478863890379e-12% |
| Strain energy | 2% | 16.379509145773455% |
| Representative `sigma_xx` | 10% | 24.310580151133324% |

The coarse-to-medium-to-fine changes are monotone for all recorded
observables, but the fine/medium differences remain far outside the frozen
acceptance bounds. This is an in-scope qualification failure, not a numerical
source repair request. It prevents a TET4 structural qualification claim and
therefore blocks WP04-C from passing.

## Decision boundary

`G04-06`, `G04-07`, and `G04-09` are
`PASS_TET4_PENDING_HEX8`; `G04-10` is `FAIL`; `G04-11` and `G04-12` remain
pending. TET4 and HEX8 maturity remain `RESEARCH_ONLY`, WP04 stays at `0/12`,
and the validated roadmap stays at `29/100`.

The next action requires Owner direction. Any choice to alter the frozen
structural campaign, re-scope WP04, use a different TET4 structural envelope,
or remediate formulation/element behavior is outside this WP04-C execution.

Raw controlled evidence is in
`qualification/0_2_9/wp04_c_tet4_structural_summary.json` and
`qualification/0_2_9/wp04_c_tet4_structural_raw.npz`; the harness is
`tests/verification/test_wp04_c_tet4_structural.py`.
