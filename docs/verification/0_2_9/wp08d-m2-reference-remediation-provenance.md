# WP08-D M2 independent-reference remediation — provenance closure

## Root cause

At increment 5, production had the stable mixed state `SSK` on active
contacts `[3, 7, 11]`: contacts 3 and 7 stick; contact 11 slips.  The prior
independent NumPy/KKT runner discarded that observed classification after its
direct iteration limit and solved an all-slip root over all three contacts.
That created six tangential unknowns instead of two and failed closed with
`Independent active-slip root failed: residual=3.290e+00`.

The reference remedy in `scripts/run_wp08d_independent_reference.py` resolves
the fixed observed classification independently: stick pairs contribute their
elastic tangential KKT terms, and only observed slip pairs enter the nonlinear
root.  It does not import or call production contact/friction code, enumerate
modes, alter a frozen input, or change a tolerance/fallback/backend.

## Numerical comparison

| Increment 5 quantity | Before | After |
| --- | ---: | ---: |
| Tangential state | all-slip attempt | SSK |
| Tangential root dimension | 6 | 2 |
| Stick contacts | none | `[3, 7]` |
| Slip contacts | `[3, 7, 11]` | `[11]` |
| Root residual infinity norm | `3.290e+00` (FAIL) | `6.563638521583925e-13` (PASS) |
| Post-root normal set | unavailable after failure | `[3, 7, 11]` |

After the fix, M2 reference/production relative deltas are displacement
`2.7227553716208965e-14`, reaction `7.089409749226984e-14`, moment
`1.086498098778992e-13`, normal contact `2.905189642208704e-13`, tangential
contact `2.5848663343944946e-13`, and dissipation
`7.416413106477588e-14`.  All reference equilibrium, finiteness, active-set,
open-contact, and frozen-delta checks pass.

## Immutable M2 provenance

| Field | SHA | Meaning |
| --- | --- | --- |
| `AUTHORIZED_BASE_SHA` | `28cf9dd1886b72c6c7c9fc720dc778eddfce4441` | governing baseline required by the Phase-1 authorization guard |
| `PRODUCTION_REMEDIATION_SHA` | `b11726c6d7318762c3a892821f9fd3ca0a8a5eaf` | authorized hybrid production remedy already in the M2 candidate lineage |
| `REMEDIATION_SHA` | `5fe0451a21ac33de9ddaca6b480748238ac04779` | independent-reference mixed-mode remedy |
| `EXECUTION_SHA` | `5fe0451a21ac33de9ddaca6b480748238ac04779` | source recorded by the M2 independent-reference execution and M2 replay |
| `EVIDENCE_COMMIT_SHA` | `ab64fc5bc9373bb7c12e96d7259cc148a1fe1d8b` | immutable M2 reference/replay evidence commit |
| `FINAL_SHA` | `ab64fc5bc9373bb7c12e96d7259cc148a1fe1d8b` | final SHA of the M2-only evidence cut |
| `REMOTE_HEAD_AFTER_M2` | `ab64fc5bc9373bb7c12e96d7259cc148a1fe1d8b` | remote governing head when the M2 cut completed |

Later M3 evidence exists on a subsequent commit and is deliberately outside
this M2-only provenance cut.  It neither changes the executed M2 source nor
retroactively changes this result.

## Results and limits

- M2 production: `PASS`, 7/7 accepted increments, fallback disabled.
- M2 independent reference: `PASS_REFERENCE`, 7/7 accepted increments.
- M2 replay: `PASS`, 7/7 accepted increments.
- Targeted WP08 tests: 71 passed; Ruff, mypy, compileall, JSON and manifest
  validation pass.
- Formal award is not automatic: `WP08D = 0/2`, `WP08 = 0/8`, pending Owner
  review.

