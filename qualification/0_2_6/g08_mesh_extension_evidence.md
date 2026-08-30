# 026-G08 Mesh Extension Evidence

Status: **PASS_WITH_LIMITATIONS**; official G08 status unchanged: **PASS_WITH_LIMITATIONS**

Extension source SHA: `151662ac4781718a7fbe3d1e527675ec9e513ad4`; dirty: `False`
Historical mesh source SHA: `6589443e1404a2749ac6c0a9b911f00dd9cb8753`

This supplemental run adds levels 16 and 32 for TET10, HEX8 and HEX20. It does not alter the official 1% policy or the historical Owner closeout.

## Extension counts

- Executed extension observations including replay: 12
- PASS observations: 12
- Reproducible observed limitations: 0
- Unexpected failures: 0

## Mesh series

| Family | Historical factors 1/2/4/8 | Added factors 16/32 | Final direct change | Classification |
|---|---|---|---:|---|
| TET10 | 12.3844983, 10.6196916, 9.85121878, 9.54786957 | 9.4770218, 9.48474693 | 0.081448% | CONVERGED_BOUNDED |
| HEX8 | 213.52352, 158.539513, 143.615287, 139.926369 | 139.000524, 138.768623 | 0.167113% | CONVERGED_BOUNDED |
| HEX20 | 12.5045366, 10.9853934, 9.96002141, 8.7414254 | 8.40967631, 8.33362196 | 0.912621% | CONVERGED_BOUNDED |

The classification rule is unchanged: `<=1%` is `CONVERGED_BOUNDED`; `1-4%` is `NEAR_CONVERGED_BOUNDED` for diagnostics only; `>4%` is `NOT_STABILIZED`. A missing terminal factor is not bridged across.

## HEX20 diagnosis

The high-order factor changes substantially on the coarse historical levels, then reaches a 0.912621% direct change from level 16 to level 32. Both added levels replay deterministically under the unchanged sparse route. The earlier exploratory ARPACK observation was not reproduced by the controlled replay and is retained separately, not used as a PASS basis.

- CalculiX retry: `BLOCKED_EXTERNAL_TOOL`.
- High-order analytical oracle: `NO_COMPARABLE_ANALYTICAL_ORACLE`.
- No solver or eigensolver modification was made.

## Limitations

- This is supplemental extension evidence; the historical G08 Owner closeout remains unchanged.
- TET4 is unchanged and not rerun in this extension.
- TET10 and HEX8 reach a <=1% final adjacent change at the added level 32, but this does not erase earlier non-monotone changes or create a universal convergence claim.
- HEX20 reaches the <=1% direct-change diagnostic classification in this two-level extension, but remains at its existing bounded G08 Owner decision; no retrospective promotion is proposed.
- The coarse-to-fine history remains strongly mesh-sensitive; no universal high-order convergence claim is made.
- No high-order analytical oracle was found.
- CalculiX HEX20 remains blocked by external execution; Code_Aster is not comparable for this route.
