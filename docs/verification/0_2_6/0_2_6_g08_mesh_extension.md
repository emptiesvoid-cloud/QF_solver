# 026-G08 Mesh Extension

## Purpose

This page records supplemental mesh evidence for the existing `026-G08`
linear-buckling gate. It does not reopen or replace the historical Owner
closeout, and it does not change the official one-percent policy.

## Provenance

- Baseline checkpoint: `c9d5ce8d7ce456c5d3fdcc5ff43d0fcebb2c0c4c`
- Extension execution source: `151662ac4781718a7fbe3d1e527675ec9e513ad4`
- Historical mesh evidence source: `6589443e1404a2749ac6c0a9b911f00dd9cb8753`
- Source worktree at execution: clean
- Solver version: `0.2.6a0`

The machine-readable record is
`qualification/0_2_6/g08_mesh_extension_evidence.json`; the generated
evidence report is
`qualification/0_2_6/g08_mesh_extension_evidence.md`.

## Controlled extension

The historical levels 1, 2, 4 and 8 are reused without recomputation. Levels
16 and 32 are executed for TET10, HEX8 and HEX20. Every added level is replayed
twice. The existing classification is retained:

- `<=1%`: `CONVERGED_BOUNDED`
- `1-4%`: `NEAR_CONVERGED_BOUNDED` for diagnostics only
- `>4%`: `NOT_STABILIZED`

| Family | Level 16 factor | Level 32 factor | Direct change | Classification |
|---|---:|---:|---:|---|
| TET10 | 9.4770217961 | 9.4847469311 | 0.081448% | `CONVERGED_BOUNDED` |
| HEX8 | 139.0005235350 | 138.7686228488 | 0.167113% | `CONVERGED_BOUNDED` |
| HEX20 | 8.4096763077 | 8.3336219585 | 0.912621% | `CONVERGED_BOUNDED` |

All 12 extension observations passed, including deterministic replays. The
maximum eigenpair residual remained below the existing `1e-7` PASS policy for
the added rows. No solver, formulation or eigensolver code was changed.

## HEX20 interpretation

HEX20 reaches the direct-change diagnostic band in this two-level extension,
but its historical coarse-to-fine series remains strongly mesh-sensitive. This
is bounded supplemental evidence, not a universal convergence claim and not a
retrospective change to the existing Owner decision.

The retry of the same one-cell C3D20-style external deck remains
`BLOCKED_EXTERNAL_TOOL`. Code_Aster is not comparable for this route, and no
independent high-order analytical buckling oracle was identified in the
controlled repository evidence.

One exploratory inline run before the controlled harness observed an ARPACK
non-convergence at HEX20 level 32. The controlled two-replay harness did not
reproduce it; the observation is retained in the JSON record and is excluded
from acceptance decisions rather than silently discarded.

## Gate impact

`026-G08` remains `PASS_WITH_LIMITATIONS`. The historical family decisions
remain unchanged: TET4 is `QUALIFIED_BOUNDED`, TET10 and HEX8 are
`PASS_WITH_LIMITATIONS`, and HEX20 is `MORE_EVIDENCE_REQUIRED`. No post-
buckling, multi-mode, or general physical-validation claim is added.
