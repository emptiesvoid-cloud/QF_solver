# WP12 Code_Aster R2 — Owner review

## Decision status

`READY_FOR_OWNER_REVIEW` — the four bounded R2 correlations are `PASS_CANDIDATE`. This report proposes **4/4 candidate points** (one per element family); it awards no official points. The current official WP12 score remains `0/4` pending an explicit Owner decision.

## Provenance and integrity

| Item | Verified value |
|---|---|
| Branch | `codex/wp12-external-vv` |
| Authorized base SHA | `48eadcbde3cfcf8b15f6cd2335afa3df17d8de37` |
| Execution SHA | `e3231fa386d2542841084e3be9843e7eca75acf4` |
| R2 contract SHA-256 | `f6154660635670c026354429894c9c7a6f7fa6d8bd6849edf44717a4bd43824a` |
| Runner SHA | `c4a772cd14921ca0b243c71b99a0f94f0ca210e8` |
| Independent auditor SHA | `c6626976d72a77fcf1233ea6c41b1f998be0e5bb` |
| Code_Aster image | `simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435` |
| Runtime | Code_Aster `18.1.0`; fresh container per family; serial, one CPU, MPI disabled |
| R2 manifest | 74 entries; SHA-256 `7a912a795bd57db6505ae100dd77a8480d3bf41a1229fd39644c298b294c4e8c` |
| R2 summary JSON | SHA-256 `a7f7222d03ef04662828ed1e1207a312487c958b5d948bd36f513102dacae138` |
| Independent audit JSON | SHA-256 `0be63ce3f98e7e785f0cdff8fda94b4495d4d95f5ae0ee50c5809ad181acbdcf` |

The R2 manifest was independently rehashed: all 74 listed files exist and match; the independent raw-evidence auditor returned `PASS_CANDIDATE`, with no errors. No active Code_Aster containers remained after execution. The worktree contained only the new R2 evidence and audit outputs before this report was added; no `src/` changes are present relative to the execution commit.

R1 is preserved as a launch/runtime failure, not a numerical failure. Its record, contract, summary, and manifest hashes remain recorded in the final machine-readable dossier. R2 uses a distinct output root; no R1 evidence was overwritten or relabeled.

## Frozen comparison scope

This is a separate Code_Aster FEM solve of the exact frozen WP11 M1 one-element static, small-strain linear-elastic models. Material, coordinates, connectivity mapping, fixed DOFs, and nodal load vectors are held identical to the QF inputs. The model uses `E = 210 GPa`, `nu = 0.30`, 3D formulation, and a 1,000 N downward resultant. The contract and image digest were frozen before R2 execution.

This is external-solver correlation for these four specific discrete models—not experimental validation, mesh-convergence evidence, stress-field equivalence, or general solver validation.

## R2 results

Every comparison/equilibrium gate is `1e-8`; fixed-DOF displacement is gated at `1e-12`. Values below are recomputed from raw QF and Code_Aster evidence and are relative errors unless marked absolute.

| Family | DOFs | `||Δu||₂/||u_A||₂` | Reaction L2 | Energy vs external work | QF force / moment balance | Aster force / moment balance | Max fixed `|u|` | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| TET4 | 12 | `1.782e-16` | `2.625e-16` | `1.824e-16` | `0 / 0` | `0 / 0` | `0` | PASS |
| HEX8 | 24 | `7.501e-16` | `1.046e-15` | `7.938e-16` | `4.348e-16 / 2.558e-16` | `8.789e-17 / 9.846e-17` | `4.463e-25` | PASS |
| TET10 | 30 | `4.734e-15` | `6.043e-15` | `4.252e-15` | `6.765e-15 / 3.794e-15` | `5.210e-16 / 2.558e-16` | `7.533e-24` | PASS |
| HEX20 | 60 | `1.210e-14` | `1.358e-14` | `1.110e-14` | `3.600e-15 / 4.433e-15` | `2.405e-16 / 1.241e-16` | `1.566e-24` | PASS |

The displacement L-infinity and reaction L-infinity checks also pass for every family. HEX20 uses the frozen explicit QF-to-Code_Aster local-node permutation. For TET4 and TET10, the full resultant is applied at the single `x=1` vertex; this is not a face-traction qualification.

## Validation and change scope

- Independent raw auditor: `PASS_CANDIDATE`, candidate `4/4`, zero errors.
- Targeted WP12 tests: `16 passed`.
- Ruff, targeted mypy, compileall, JSON validation, and source/documentation `git diff --check`: `PASS`.
- Full repository test suite: not run, as scoped.
- QF production mechanics, thresholds, solver policy, and fallback behavior: unchanged.
- No score-ledger update, merge, or push has been performed.

## Limitations

- One homogeneous, one-element, static elastic case per family only.
- Correlation applies only to the frozen WP11 M1 mesh, material, constraints, and nodal loads.
- No mesh convergence, stress-field or cross-family equivalence claim.
- No WP04/WP05 geometric nonlinearity, WP06 arc length, WP07/WP08 contact/friction, or WP09/WP10 J2/coupled-nonlinear correlation.
- No dynamics, MPI/PETSc, scaling, or experimental-validation claim.
- Independent Code_Aster solve shares the same mathematical model; it does not establish physical truth by itself.

## Owner decision requested

Please decide explicitly:

```text
OWNER_ACCEPTS_WP12_TET4 = YES/NO
OWNER_ACCEPTS_WP12_HEX8 = YES/NO
OWNER_ACCEPTS_WP12_TET10 = YES/NO
OWNER_ACCEPTS_WP12_HEX20 = YES/NO
OWNER_ACCEPTS_WP12_LIMITATIONS = YES/NO
OWNER_AWARDS_WP12_POINTS = 0..4/4
OWNER_AUTHORIZES_GOVERNING_MERGE = YES/NO
OWNER_AUTHORIZES_GOVERNING_PUSH = YES/NO
OWNER_AUTHORIZES_LEDGER_UPDATE = YES/NO
```

Until that decision is recorded, `WP12_OFFICIAL_POINTS = 0/4` and the project ledger is unchanged.
