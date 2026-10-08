# WP08-R3 — Tangent, Newton, results and checkpoint integration

**Record type:** bounded implementation verification, not qualification.
**Baseline:** `d19004f676f6f85716c0b331bfb08001e5a5bfdc` (WP08-R2).
**Branch:** `codex/v0.2.12-wp08-r3-tangent-integration`.
**Formulation:** `corrected_corotational_biot_j2/v1` (explicit opt-in; EXPERIMENTAL).

## Executive disposition

R3 connects the corrected R2 force to an unsymmetrized, fixed-accepted-state central-difference element Jacobian, admits only bounded full-Newton nonlinear-static runs, and adds formulation-bound results and checkpoint metadata. This is a numerical tangent, not a closed-form material/geometric tangent. It is verified on the bounded smooth branches and fixtures listed here; yield switching is flagged as nonsmooth and has no classical-derivative claim. No global maturity, qualification, or release gate is closed by these checks.

The legacy formulation remains the default and keeps its historical assembly, tangent, and output branch. A corrected selection cannot fall back to the legacy tangent. Corrected contact, modified Newton, arc-length, non-static analysis, mixed/unsupported element meshes, and local stretch strain above the R1 bound are rejected.

The final R3 source/test tree passed `tests/unit` with **3311 passed, 93 skipped, 0 failed** in 1335.99 seconds. The exact seven modified source/test files are SHA-256 recorded in `wp08_r3_integrated_vnv_matrix.json`; only qualification records changed after that run. This is bounded implementation verification, not qualification.

## Implemented equations and code path

At each integration point R2's frozen mechanics remain unchanged:

`F = R U`, `E_B = U - I`, the existing associative isotropic J2 return from the accepted material state, `P = R L_U*[T_B]`, and `f_int[a,i] = sum_q w_q P[i,J] N[a,J]`. The R2 polar-adjoint force is not symmetrized or calibrated to legacy results.

R3 computes each raw tangent column as

`K[:,j] = (f_corr(u + h e_j; xi_n) - f_corr(u - h e_j; xi_n)) / (2 h)`,

where `h = 1e-5 V0^(1/3)`. Each evaluation receives the same immutable accepted `xi_n`; only the returned trial state is eligible for commit after global convergence. The tangent is returned raw, including any numerical or constitutive asymmetry. Branch changes at integration points are counted and suppress a classical-derivative claim. The method is a finite-difference approximation to the derivative of the implemented corrected force, not the analytic/AD derivative specified as the preferred implementation in the R1 design record.

The directional audit uses the preregistered relative steps `{1e-4, 3e-5, 1e-5, 3e-6}` and a normalized direction. On the recorded smooth noncoaxial plastic TET4 probe, the scaled tangent/action error against the smallest-step reference was `2.351870888847e-8`; the `1e-5`/`3e-6` plateau delta was `5.196591020267e-8`; raw tangent relative skew was `4.425823883694e-8`; no yield branch switch occurred. The frozen R1-A10 thresholds remain unchanged (`2e-5`). A separate exact-yield test observes branch switches and confirms the implementation does not label that result a classical derivative.

## Newton, transactions and permitted domain

The existing `NonlinearStaticSolver`, Full Newton iteration, line search, adaptive cutback, sparse assembly, and state-commit lifecycle are reused. Corrected integration is restricted to `nonlinear_static`, `newton_raphson` or `newton_line_search`, no contact, and the existing homogeneous supported solid-family/material/small-local-strain checks. The explicit selector is part of the assembly plan identity. With no selector, the legacy route is selected.

Every element evaluation starts from the increment's accepted states. A rejected line-search candidate or load increment returns detached trial data and does not alter those accepted states. A converged increment commits once via the existing state transaction. Tests exercise plastic line search, rejected adaptive increment/cutback, checkpoint restart, and deterministic continuous/restarted results. This does not redesign Newton or the general NL migration policy.

## Result and checkpoint contract

Corrected outputs carry formulation ID, constitutive state schema, stress semantic version, result schema, EXPERIMENTAL maturity, and `NOT_ASSESSED` qualification. Generic `stress`, principal stress, von Mises, deviatoric stress, stress trace, and pressure use Cauchy stress in the current configuration; `strain` uses Biot strain in the declared material/reference frame. Integration-point and aggregate fields separately identify Biot-conjugate stress, first Piola (spatial/reference two-point), PK2, and Cauchy. No tensor is symmetrized to meet the output contract. Corrected checkpoints retain the repository checkpoint schema but add the corrected formulation/state-version identifiers; the model signature binds the selector and model/material inputs. Legacy or unidentified states are refused under the corrected route.

Historical R2 records and legacy result semantics are not rewritten. The generic legacy path is not migrated or relabelled. Corrected J2 remains EXPERIMENTAL; `NUMERICAL_PASS_IMPLIES_QUALIFICATION = NO`.

## Verification record

The R1/R2 mechanical properties were rerun through the named corrected tests, plus new tangent/Newton/result/checkpoint cases. Independent R2 tensor and incremental-potential evidence remains separately identified as inherited bounded evidence; it is not promoted to qualification. Final targeted NL/TL/checkpoint/assembly and WP02-WP07 tests passed (252 passed, 2 skipped); documentation generation passed (62 passed, 2 skipped); Ruff, formatting, targeted mypy (six source modules), `git diff --check`, and the full unit suite passed. Exact counts, durations, file hashes, and warnings are in `wp08_r3_integrated_vnv_matrix.json`.

`git diff --check` and changed-file classification are required before commit. Detailed tangent, convergence, stress-schema, checkpoint, and cost data are in the companion R3 records.

## Limits and status preservation

- Numerical central differences cost `2*n_dof + 1` corrected force evaluations per element tangent (25/61/49/121 for the tested TET4/TET10/HEX8/HEX20 fixtures). This cost is material, especially for HEX20.
- The tangent is verified for the frozen small-local-strain domain and tested smooth branches. At active-set switches, it is a central secant and is explicitly not claimed to be a classical derivative; broad semismooth/generalized-Newton guarantees are not established.
- Performance fixtures are local microbenchmarks, not scale or industrial evidence.
- Bounded implementation disposition: `WP08_R3_STATUS = PASS`; `WP08_STATUS = PASS_BOUNDED`. No global nonlinear qualification gate is closed.
- No WP09 general tangent robustness, WP10 general checkpoint migration, TL formulation changes, contact, or finite-strain plasticity were started.
- `HISTORICAL_G03 = FAIL_PRESERVED`; `HISTORICAL_WP14 = HOLD_NOT_PROMOTED`; `WHOLE_REPOSITORY_ARCHIVE_CLEARED = NO`; publication remains unauthorized.
