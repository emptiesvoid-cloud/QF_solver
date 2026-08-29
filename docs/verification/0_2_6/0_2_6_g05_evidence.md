# 026-WP05-G05 V&V and Robustness Evidence

## Status

`026-WP05-G05 = PASS_WITH_LIMITATIONS`

This report records the bounded execution batch for G05. `READY` means that a
case has a controlled executable model; it does not mean that the capability
is qualified. The official foundation gate `026-G05` is closed as
`PASS_WITH_LIMITATIONS`, with bounded external coverage and no broader claim.
continues to mean Modal / dynamic / harmonic maturity.

## Controlled provenance

| Item | Value |
| --- | --- |
| Source SHA | `2a27b4423965f79ae2f3359dae6b7d93d3564eb8` |
| Source worktree | `clean` |
| Captured at | `2026-08-28T19:42:56.565693Z` |
| Solver | `qf_solver 0.2.6a0` |
| Registry digest | `ba2028115e08e1b02e5d773199ad08c2f1081b37e648d3c8216db59728b6d571` |
| Result manifest SHA-256 | `431d393ecf63b67144e956ab06183fcd20e7d386bc635142676da30f57c7531f` |
| Environment | Windows AMD64, CPython 3.13.1, NumPy 2.2.6, SciPy 1.15.2 |

## Execution summary

The batch converted 50 planned definitions into executable cases, increasing
the registry from 10 to 60 `READY` cases and leaving 120 definitions
`PLANNED`. All 50 G05 cases were executed by the controlled runner:

| Result | Count |
| --- | ---: |
| PASS | 47 |
| EXPECTED_FAILURE | 3 |
| FAIL | 0 |
| BLOCKED | 0 |

The three expected failures are deliberately invalid inverted-TET4 geometry
cases and all returned the `INVALID_ELEMENT` contract. The batch completed in
3.338 seconds of summed case wall time.

## Coverage of existing routes

| Family | PASS | Expected failure |
| --- | ---: | ---: |
| Linear solids (LIN) | 8 | 0 |
| Shell / beam / discrete (SHL) | 5 | 0 |
| Modal (MOD) | 5 | 0 |
| Transient dynamics (DYN) | 6 | 0 |
| Harmonic (HAR) | 5 | 0 |
| Small-strain J2 (J2) | 6 | 0 |
| Geometric nonlinear (GNL) | 3 | 0 |
| Linear buckling (BUC) | 3 | 0 |
| Frictionless contact (CON) | 4 | 0 |
| Adversarial (ADV) | 0 | 3 |
| Scaling routes (SCL) | 2 | 0 |

The execution exercised 22 linear-static, 5 modal, 6 transient, 5 harmonic,
6 nonlinear-static, 3 geometric-nonlinear and 3 linear-buckling routes.
Variants use only maintained public example models plus declared deterministic
load, analysis or material overrides recorded in `case_registry.json`.

## Verification boundary

The evidence demonstrates executable coverage, deterministic result manifests
and expected-failure handling. It does not, by case count alone, establish
analytical accuracy, mesh convergence, external correlation or a new maturity
claim. Those remain subject to the applicable campaign oracle and official
gate. No FEM formulation, public solver API or tolerance was weakened.

## Checks

- Framework contracts: `5 passed`.
- Ruff: `PASS`.
- `compileall`: `PASS`.
- `git diff --check`: `PASS`.

The reproducible raw result directory is intentionally excluded from normal
source history; the compact manifest digest and this summary are the archived
evidence.
