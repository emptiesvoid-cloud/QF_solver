# 026-WP06-G06 Deep V&V and Corpus Expansion

This document is the historical replay recorded at source SHA
`b9d523725ab2a6856256731e44921adf2837a1f3`. The current clean-source replay
is recorded separately in `0_2_6_g06_prequalification_evidence.md`.

## Status

`026-WP06-G06 = PASS_WITH_LIMITATIONS`

This work package expands the executable 0.2.6 V&V corpus. `READY` means that
the controlled runner can execute a case; it does not mean that the associated
element, material or analysis capability is qualified. The official gate
`026-G06` is the J2 maturity-extension gate. This historical package is
retained as supporting evidence; the later deep pack records the Owner's
bounded closeout decision.

## Controlled provenance

| Item | Value |
| --- | --- |
| Source SHA | `b9d523725ab2a6856256731e44921adf2837a1f3` |
| Source worktree | `clean` |
| Captured at | `2026-08-28T21:31:09.160647Z` |
| Solver | `qf_solver 0.2.6a0` |
| Registry digest | `d2e5f587ac2d67c3c875782c8558aa7aac60cec09df9f43614319eff1b99ea59` |
| Campaign manifest SHA-256 | `f8847759716bd7007c7e783338d7f0e6d4522fa6b709d39e2b2eec1cef578804` |
| Quantitative manifest SHA-256 | `4b5a7e96ac6c661edfdf3133cb6d12fb1e294b961756f1593b4973ab2bae34e1` |
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

## Quantitative studies

The final clean-source replay also ran 20 independent analytical cases:
TET4, TET10, HEX8 and HEX20 each use a constrained single-free-DOF model and
an independently integrated effective stiffness. All 20 cases passed with a
maximum relative displacement error of `0.0`.

The HEX8 bar series was evaluated at four levels (`nx=1,2,4,8`). The relative
tip-displacement error was respectively `9.000000e-2`, `5.777373e-2`,
`4.412610e-2` and `3.999261e-2`; the trend is non-increasing. The observed
successive orders were `0.6395`, `0.3888` and `0.1419`. This is a bounded
quantitative mesh study for this bar configuration, not a universal
convergence claim. The reference is `u_tip = F L / (E A)`.

The machine-readable quantitative summary and graph are produced by
`scripts/run_g06_quantitative.py` under the ignored raw result directory
`results/vnv_026_g06_quantitative_clean/`; the campaign and quantitative
manifest digests are recorded separately above.

## Internal verification

The existing independent element verifiers passed for TET10, HEX8 and HEX20.
The existing Total-Lagrangian TET4 kernel campaign also passed, including a
finite-difference tangent error of `4.295361499621963e-10`. These are internal
verification results and do not constitute external physical validation.

## Limits

- The controlled runner records executable solver outcomes and provenance; the
  analytical cases now also run the independent constrained free-DOF oracle
  described above.
- The 16 mesh cases remain executable corpus entries; the separate four-level
  study above is the quantitative evidence and is limited to the stated HEX8
  bar configuration.
- No Code_Aster or CalculiX run was available in this local campaign.
- No new maturity promotion is made. External correlation, general mesh
  convergence and official gate `026-G06` remain open evidence items.
- No FEM formulation, tolerance or public solver API was changed.

## Checks

- Framework tests: `7 passed`.
- G06 controlled campaign: `79 PASS / 1 EXPECTED_FAILURE / 0 FAIL / 0 BLOCKED`.
- Ruff: `PASS`.
- `compileall`: `PASS`.
- `git diff --check`: `PASS`.

Raw result files remain reproducible under `results/vnv_026_g06_final_clean/g06/`
and `results/vnv_026_g06_quantitative_clean/`; they are excluded from normal
source history. The compact evidence and manifest digests above are the
archived record.
