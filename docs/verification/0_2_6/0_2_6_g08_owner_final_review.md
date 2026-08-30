# 026-G08 Active Owner Final Review

## Decision

`026-G08` remains **PASS_WITH_LIMITATIONS** under the active Owner decision
`APPROVED_BOUNDED_WITH_FAMILY_LIMITATIONS`. No requirement was lowered and no
solver, formulation or eigensolver code changed.

This document and
`qualification/0_2_6/g08_owner_final_review.json` are the active review record.
The earlier `g08_owner_closeout.json` is retained as historical evidence and is
not silently rewritten; its family interpretation is superseded by this review
where the later corrected Euler and CalculiX evidence applies.

## Provenance chain

| Evidence role | Artifact | Source SHA |
| --- | --- | --- |
| Approved contract | `g08_requirements.json` | `4145f1f42ed5aec513ccf05e215e16e590132546` |
| Controlled execution | `g08_execution_evidence.json` | `6589443e1404a2749ac6c0a9b911f00dd9cb8753` |
| Corrected high-order analytical screen | `g08_high_order_analytical_evidence.json` | `4c45b46cfa7c9a664986bb49a53ef25fa570c030` |
| Active Euler prevalidation | `g08_euler_prevalidation_evidence.json` | `75fbe03a414969d26dee9f0df84ff1c5dcd1661e` |
| HEX20 external rescue | `g08_hex20_calculix_rescue_evidence.json` | `8ee87e5f4093f9152a2e4e5b52cbfafec22c2d7b` |

The positive-load/tension comparison in `g08_euler_reference.json` is retained
as superseded history and is excluded from active metrics. The review artifact
itself is documentary evidence at the review HEAD and does not replace any
execution source SHA.

## Family decisions

| Family | Decision | Active basis | Limitation |
| --- | --- | --- | --- |
| TET4 | `QUALIFIED_BOUNDED` | Historical bounded Euler evidence, eligible mesh sequence, residual/mode/replay and bounded CalculiX evidence | Only the declared first-factor/first-mode domain is covered |
| TET10 | `PASS_WITH_LIMITATIONS` | Corrected Euler trend reaches 3.269%; active mesh change 0.081448%; residual/replay and CalculiX evidence pass | No universal analytical or mesh-convergence claim; transverse diagnostic remains less accurate |
| HEX8 | `MORE_EVIDENCE_REQUIRED` | C3D8 agrees with QF within 0.0003835% and 0.0004065%; mode/KG diagnostics are coherent | Corrected Euler error remains 298.413%; low-order locking/discretization limitation is likely, not a demonstrated QF bug |
| HEX20 | `PASS_WITH_LIMITATIONS` | Corrected Euler trend reaches 3.622%; active mesh change 0.912621%; three-level C3D20 correlation passes | Coarse-history sensitivity remains; no universal analytical claim |

The HEX8 result is deliberately not promoted. Agreement with C3D8 is useful
independent evidence about the discretization behaviour, but it does not make a
poor continuum-oracle result a qualified physical result.

## Requirement disposition

| Disposition | Requirements |
| --- | --- |
| `OWNER_APPROVED_FULL` | `G08-001`, `G08-002`, `G08-004`, `G08-006`, `G08-007`, `G08-009` |
| `OWNER_APPROVED_BOUNDED` | `G08-003`, `G08-005`, `G08-008` |
| `DEFERRED` | None at gate level |
| `BLOCKING` | None for the bounded gate; HEX8 remains blocked at family-claim level |

## Evidence summary

- **Euler:** corrected signed compression/load-factor comparison is active; the
  high-order trends are TET10 `27.278% -> 8.465% -> 3.269%` and HEX20
  `22.956% -> 8.072% -> 3.622%`. HEX8 remains `298.413%` at its final axial
  screen.
- **External:** bounded CalculiX evidence is available for the four families
  across the retained evidence chain. Code_Aster is
  `SKIPPED_NOT_COMPARABLE` for this 3D solid eigen-buckling route.
- **Mesh:** active adjacent changes are TET10 `0.081448%`, HEX8 `0.167113%`
  and HEX20 `0.912621%`; these are bounded tested-domain observations, not
  universal convergence laws.
- **Mode/residual:** finite deterministic first-mode evidence passes; the
  active HEX8 diagnostic maximum residual is `2.39e-8`, below the declared
  `1e-7` pass band.

## Qualified boundary

The bounded claim is limited to linear buckling, the first linearized
tangent-instability factor and first mode, homogeneous isotropic 3D material,
nodal dead loads, and the sparse SciPy route in the tested domain. TET4 is the
qualified family; TET10 and HEX20 have bounded limitations; HEX8 is excluded
from the qualified family subset pending further evidence.

Post-buckling, collapse, arc-length, multi-mode qualification, shell/beam/
discrete routes and general physical validation are excluded.
