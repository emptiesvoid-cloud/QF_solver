# 026-WP06-G06 Deep V&V and Corpus Expansion

## Status

`026-WP06-G06 = PASS_WITH_LIMITATIONS`

This work package expands the executable 0.2.6 V&V corpus. `READY` means that
the controlled runner can execute a case; it does not mean that the associated
element, material or analysis capability is qualified. The official gate
`026-G06` remains the J2 maturity-extension gate and is unchanged.

## Controlled provenance

| Item | Value |
| --- | --- |
| Source SHA | `77b8f30314356b24c231c51a16d2b66bf6753548` |
| Source worktree | `clean` |
| Captured at | `2026-08-28T21:02:34.656502Z` |
| Solver | `qf_solver 0.2.6a0` |
| Registry digest | `c9ada9eb9ea2307f9e34032ea80099b6cb29b25dfcb483bd97edd890bd244731` |
| Result manifest SHA-256 | `973cb5b044d6a60f6f1820d181258ae2918e46b8319d012c8de10527504ebc09` |
| Environment | Windows AMD64, CPython 3.13.1, NumPy 2.2.6, SciPy 1.15.2 |

## Corpus and execution

The registry contains 180 definitions: 140 `READY` and 40 `PLANNED`. The G06
batch converted 80 definitions into executable cases and ran all of them:

| Result | Count |
| --- | ---: |
| PASS | 79 |
| EXPECTED_FAILURE | 1 |
| FAIL | 0 |
| BLOCKED | 0 |

The batch contains 20 analytical equilibrium variants across TET4, TET10,
HEX8 and HEX20; 16 structured HEX8 mesh cases at `nx=1,2,4,8`; 20 HEX8/HEX20
common analysis routes; and 24 robustness routes. The expected failure is an
inverted TET4 returning `INVALID_ELEMENT`.

## Internal verification

The existing independent element verifiers passed for TET10, HEX8 and HEX20.
The existing Total-Lagrangian TET4 kernel campaign also passed, including a
finite-difference tangent error of `4.295361499621963e-10`. These are internal
verification results and do not constitute external physical validation.

## Limits

- The controlled runner records executable solver outcomes and provenance; it
  does not calculate an analytical error merely because a case declares an
  analytical oracle.
- The 16 mesh cases are executable HEX8 refinements, not by themselves a
  quantitative mesh-convergence claim.
- No Code_Aster or CalculiX run was available in this local campaign.
- No new maturity promotion is made. External correlation, quantitative mesh
  convergence and official gate `026-G06` remain open evidence items.
- No FEM formulation, tolerance or public solver API was changed.

## Checks

- Framework tests: `6 passed`.
- G06 controlled campaign: `79 PASS / 1 EXPECTED_FAILURE / 0 FAIL`.
- Ruff: `PASS`.
- `compileall`: `PASS`.
- `git diff --check`: `PASS`.

Raw result files remain reproducible under `results/vnv_026_g06_final/g06/`
and are excluded from normal source history; the compact evidence and manifest
digest above are the archived record.
