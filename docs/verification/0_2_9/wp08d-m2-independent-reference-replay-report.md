# WP08-D M2 — independent hybrid reference and replay

## Scope

This evidence requalifies the existing M2 production candidate at source
`5fe0451a21ac33de9ddaca6b480748238ac04779`.  It adds an independent NumPy
dense-KKT reference route that resolves the direct iteration's observed fixed
stick/slip classification; it does not import or call production contact
routines.  The structural replay uses the same frozen M2 contract and the
already-authorized execution scope.  M3 was not run.

## Independent reference

- Status: `PASS_REFERENCE`; 7/7 increments accepted; fallback count 0.
- Step 5: active contacts `[3, 7, 11]`, mode `SSK`, with contacts 3 and 7
  elastic stick contributions and contact 11 the only slip-root pair (two
  tangential unknowns).
- Reference/production deltas: displacement `2.7228e-14`, reaction
  `7.0894e-14`, moment `1.0865e-13`, normal contact `2.9052e-13`, tangential
  contact `2.5849e-13`, dissipation `7.4164e-14`.
- Reference force and moment equilibrium: `4.5813e-14` and `6.3492e-14`.

## Replay

- Status: `PASS`; 7/7 increments accepted; fallback disabled.
- Replay comparison: `PASS` for terminal status, mesh identity, selected
  displacement, cumulative local dissipation, and force/moment-balance
  observables at `rtol=1e-12`, `atol=1e-14`.
- Both reference and replay manifests, including every recorded raw artifact
  hash, were verified before this report.

## Governance

- Production mechanics, thresholds, solver parameters, and fallback policy
  were not changed in this evidence/replay task.
- The independent-reference implementation changed only.  Its observed-mode
  hybrid root is a fixed-candidate solve, not a mode search.
- This is M2 Phase-1 evidence only. `WP08D_FORMAL_POINTS = 0/2` and
  `WP08_FORMAL_POINTS = 0/8` pending Owner review; M3 remains `NOT_RUN`.

