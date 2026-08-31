# G10 Selected External Campaign

Evidence ID: `026-G10-SELECTED-EXTERNAL-001`
Execution source SHA: `efed8c3e1bcf173d335b3b9a605febd0fa1084cb`
Worktree at capture: `dirty=false`
Overall campaign status: **PARTIAL**

This pack records only the two routes selected by the G10 Owner Review. It
does not close G10, reopen G07, promote Total-Lagrangian elasticity, or alter
any solver implementation. QF results, external results and derived metrics
are kept in separate sections of the machine-readable evidence.

## Commands and external tools

- QF arc-length: `run_common_fem_snap_through_benchmark(radius=0.02, max_arc_steps=80)`
- Code_Aster arc-length: `scripts/run_code_aster_arc_length_025.py --arc-length-end 1.0 --arc-length-steps 80`
- TET4 TL: `scripts/run_code_aster_tl_structural_vnv.py`
- HEX8 TL external: `scripts/run_tl_physical_branch_code_aster.py`
- HEX8 QF matched point: one-step QF solve at the first Code_Aster load point
- Code_Aster: `18.1.0`, pinned image recorded in the JSON evidence

All runs used the same clean source SHA `efed8c3e1bcf173d335b3b9a605febd0fa1084cb`;
the result directories are ignored generated output. Input decks and meshes
are archived under `qualification/0_2_6/g10_selected_external_inputs/`.

## Arc-length continuation

Classification: **PASS_WITH_LIMITATIONS**.

| Metric | QF Solver | Code_Aster |
| --- | ---: | ---: |
| Complete path points | 80 | 81 |
| Turning-point load factor | -0.0373265417695 | -0.0373215949542 |
| Turning-point control displacement | -0.893376943327 | -0.887500000002 |
| Branch turns | 1 | 1 |
| QF maximum relative residual | 2.811e-11 | not exported per step |

Derived peak differences are `0.013255%` in
load factor and `0.662191%` in
control displacement. The common displacement interpolation covers
`75` points, with a
maximum absolute load-factor difference of
`8.868625e-06`.
The branch and turning point agree qualitatively and quantitatively within
the different continuation point placement, but this remains bounded
external evidence rather than a new qualification threshold.

## Total-Lagrangian TET4

Classification: **PASS_WITH_LIMITATIONS**.

- Code_Aster status: `PASS_EXTERNAL_CORRELATION`.
- Stress-patch relative error: `8.544217e-05`.
- Imperfect-column maximum relative difference: `1.692986e-09`.
- Complete comparison points: `4` QF / `4` Code_Aster.
- Formulation: Code_Aster 3D/TETRA4, Green-Lagrange elastic route; same-mesh
  QF column and stress-patch calculations.

The column path stops at 80 percent of its same-mesh critical load. The
external run therefore supports a bounded compatible comparison, not a
general finite-deformation claim.

## Total-Lagrangian HEX8

Classification: **PASS_WITH_LIMITATIONS**.

- Code_Aster status: `OBSERVED_EXTERNAL_PATH` with
  `128` exported load points.
- Matched load factor: `0.0078125`.
- Displacement relative difference: `2.342974e-09`.
- Reaction relative difference after sign alignment:
  `1.319392e-11`.
- QF matched-point residual: `2.288833e-13`;
  `det(F)` range `0.999883042065` to
  `0.999937301077`.

The QF full instrumented path was not completed within the bounded campaign
budget, so this is a matched first-point comparison only. Code_Aster stress
and energy outputs are intentionally not mixed with QF measures.

## Decision boundary

This selected campaign remains a `PARTIAL` intermediate evidence record. The
later Owner closeout records `G10` as `PASS_WITH_LIMITATIONS`; no G07, G08,
G09, G11 or G12 decision changes are made by this campaign.
The selected route records are external evidence with limitations:

- `arc_length_continuation`: `PASS_WITH_LIMITATIONS`;
- `total_lagrangian_elasticity` TET4: `PASS_WITH_LIMITATIONS`;
- `total_lagrangian_elasticity` HEX8: `PASS_WITH_LIMITATIONS`.

Finite-kinematic J2, J2-plus-geometry, coupled contact and triple coupling
were not run. They remain at their prior classifications.

See `g10_selected_external_evidence.json` and
`g10_selected_external_manifest.json` for full compact curves, input
digests, runtime provenance, and explicit limitations.
