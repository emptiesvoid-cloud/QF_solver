# WP09 TET4 — consistent-traction diagnostic R2

## Conclusion

```text
TET4_DIAGNOSTIC_STATUS = FAIL_CLOSED_MESH_CONVERGENCE
H1_PRIMARY / REPLAY = PASS / PASS
H2_PRIMARY / REPLAY = PASS / PASS
H3_PRIMARY / REPLAY = PASS / PASS
INDEPENDENT_OBSERVABLE_RECOMPUTATION = PASS
H2_TO_H3_MESH_GATE = FAIL_CLOSED
WP09_TET4_FORMAL_QUALIFICATION = NOT_CLAIMED
WP09_OFFICIAL_POINTS = UNCHANGED
```

All three TET4 meshes converged within the frozen corotational-strain bound and passed their per-run residual, equilibrium, determinant, step-count, fallback, and replay checks. The family does **not** pass the frozen H2→H3 mesh gate: displacement changes by `9.536863%` (limit `5%`) and energy by `9.963938%` (limit `5%`). Reaction and maximum von Mises stress pass their respective mesh limits. Therefore these results support a bounded diagnostic, not TET4 qualification or score attribution.

## Provenance and scope

- Study branch: `codex/wp09-tet4-extension-study`
- Governing source base: `cf832937404a14bb780778e2c0f6adc3efbfcc59`
- Frozen R2 execution commit: `b2fd8e929c51844d2a3076a45e3303d0a536442d`
- Frozen runner commit: `e3b987dfddbc519b30b6e7e67d2890c83f0f5943`
- Contract SHA-256: `2680b1cdbeebc92422d0b2058e77b98483798297dfc1b4a4fadf05c384b29c49`
- Runner SHA-256: `bc053494b263255805cd613c00bdea0a78be82ea2c02d4415be63c967334a87f`
- Reference-checker SHA-256: `8d50078d682e3f47d38f76929578d39d095a690b3e024ab3fb3a8df08cd21336`
- Policy code/runtime digests: `93a79d72…ea92ac` / `895d3c93…d9b0ef5`
- Production source diff from governing base: none (`src/` diff empty).
- Thresholds, material, boundary conditions, and loads: unchanged from the frozen diagnostic contract.
- One primary and one fresh-process replay per passing mesh; all six child processes exited `0`.
- Runs were sequential. Recorded wall times are observational only, not a performance benchmark.
- Raw primary/replay JSON is retained locally and ignored by Git; its SHA-256 values are in the accompanying manifest.
- No push, merge, formal requalification, or ledger update was performed.

This was a diagnostic-only authorization. The accepted WP09 scope and its official points remain unchanged; no TET4 extension points have been assigned.

## Frozen benchmark

- Unit cube `[0,1]³`; all three translations fixed on `x=0`.
- Total global `+UX` traction resultant `[0.25, 0, 0]` on all exterior triangular faces at `x=1`.
- Expected origin moment `[0, 0.125, -0.125]`.
- The force was integrated as a consistent face traction on linear TRI3 faces. Equal-share nodal forces were not used.
- Material: `E=1000`, `ν=0.3`, yield stress `0.02`, hardening modulus `10`.
- Corotational small-strain J2; local `||U-I||F` bound `0.05`; four load increments `[0.25, 0.5, 0.75, 1.0]`; Newton tolerance `1e-9`, maximum 40 iterations; contact disabled.
- Structured three-dimensional hierarchy, each brick cell split into five TET4 elements.

Preflight mesh quality passed at H1/H2/H3. The integrated load check matched the target resultant and moment within `1e-12` on all three meshes; the production load integration also matched an independent analytic triangle-area/centroid calculation.

## Primary results

| Level | Cells | Nodes / TET4 / DOFs | `max |u|` | Reaction norm | Energy | `max σVM` | `max ||U-I||F` | `min det(F)` | Free residual | Force / moment balance | Steps / fallback | Replay |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| H1 | 1×1×1 | 8 / 5 / 24 | 0.01535122746 | 0.250000000004 | 7.4829328713e-4 | 0.20204655455 | 0.02250886074 | 0.99984703075 | 1.672e-11 | 3.647e-12 / 2.613e-12 | 4/4, 0 | PASS |
| H2 | 2×2×2 | 27 / 40 / 81 | 0.01397558168 | 0.249999999999 | 6.8018411827e-4 | 0.21256801650 | 0.02379171760 | 0.99906173772 | 6.646e-12 | 5.796e-13 / 3.855e-13 | 4/4, 0 | PASS |
| H3 | 3×3×3 | 64 / 135 / 192 | 0.01264274954 | 0.250000000006 | 7.5545742638e-4 | 0.21072942401 | 0.02355780693 | 0.99849568869 | 4.110e-10 | 6.270e-12 / 4.487e-12 | 4/4, 0 | PASS |

All per-mesh equilibrium values are below the frozen `1e-8` limits; the largest free residual is `4.110e-10`. Minimum `det(F)` is positive and above the frozen `1e-10` lower bound. No rejected increments or solver fallback occurred.

### H2→H3 mesh gate

| Observable | Relative change | Limit | Result |
|---|---:|---:|---|
| Selected displacement | `9.536863%` | `5%` | **FAIL** |
| Reaction resultant | `2.73985e-9%` | `5%` | PASS |
| Energy | `9.963938%` | `5%` | **FAIL** |
| Maximum von Mises stress | `0.864943%` | `10%` | PASS |

The TET4 stress maximum is already close between H2 and H3, but displacement and energy are not. A good stress delta cannot substitute for the two failed gates.

## Replay, reference, and historical comparison

The fresh-process replay produced zero relative delta for every replayed observable on H1, H2, and H3. The NumPy reference checker independently recomputed the serialized displacement, reaction norm, energy, stress, plastic-state, and deformation summaries with zero reported arithmetic discrepancy. It is an **independent observable recomputation**, not an independent global FEM/Newton solve; it does not independently validate production equilibrium vectors.

The earlier TET4 remesh records are preserved and their hashes are listed in the manifest. They used four nodal loads and zero distributed loads. Their local-strain observations (`0.034728` at 1×1×1; `0.060633` at 2×2×2; `0.065229` at 4×4×4) are therefore not directly interchangeable with this consistent-traction H1/H2/H3 campaign. The old formal TET4 `FAIL_CLOSED` record is also preserved unchanged. The R2 results show that the prior strain-bound failure is not reproduced under the newly explicit, consistent face loading, but the mesh-convergence gate still fails; this study does not establish the cause of the historical discrepancy by itself.

The first orchestration attempt (R1) is separately classified as a runner/contract schema mismatch: H1 produced a raw `PASS`, then orchestration stopped before its gate and replay because the contract key was `primary_status` while the runner expected `production_status`. That raw result is hash-preserved, marked non-authoritative, and not reused in R2. The R2 runner consumes the frozen key and executes the whole campaign.

## Recommendation

Do not add TET4 to WP09’s qualified scope or award extension points from this study. Keep it as bounded diagnostic evidence. If TET4 coverage is still wanted, the next scientifically useful step is a new prospective diagnostic/qualification contract that retains the same physics, load integration, and gates, and extends the refinement sequence (for example 4×4×4 and 5×5×5) to determine whether displacement and energy settle. Do not change the current thresholds to make this H2→H3 pair pass. The Owner should decide separately whether that additional work is worthwhile; WP09 HEX8 remains accepted, with the previously accepted HEX20/TET10 bounded extensions unaffected.

## Final classification

```text
MESH_QUALITY = PASS
LOAD_RESULTANT_AND_MOMENT = PASS
H1/H2/H3_STRUCTURAL_GATES = PASS
H1/H2/H3_REPLAYS = PASS
OBSERVABLE_RECOMPUTATION = PASS_WITH_LIMITATION
H2_TO_H3_DISPLACEMENT_GATE = FAIL_CLOSED
H2_TO_H3_ENERGY_GATE = FAIL_CLOSED
TET4 = EXPERIMENTAL_BOUNDED_DIAGNOSTIC_ONLY
WP09_OFFICIAL_SCORE_CHANGE = NONE
```
