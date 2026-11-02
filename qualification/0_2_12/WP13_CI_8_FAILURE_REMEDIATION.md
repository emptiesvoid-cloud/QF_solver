# WP13 CI #41509887231 — Remediation Record

## Changes

The remediation is based on `056b4405112de0681a9c34d236e9efe98f8f14eb` on branch `codex/wp13-ci-eight-failure-remediation-20261102`. The release branch was not modified.

1. **DA-001 test fixture:** the contact validation test now removes unsupported discrete springs and uses a valid TET4/material fixture. The production `nonlinear_static` spring rejection and its precedence are unchanged.
2. **DA-005 real CSR residual bound:** the certificate now uses `gamma_(2k)` for a real float64 CSR row with `k` stored entries and the operation model of at most one multiply and one accumulation per entry. It rounds the absolute-product sum outward, includes separate subnormal allowances, bounds the final subtraction, and rounds row, norm, denominator and ratio bounds in the conservative direction.
3. **Exact zero handling:** rows whose stored terms all have an exact zero operand have zero dot-product uncertainty; an exactly equal represented product and right-hand side has zero subtraction uncertainty. This preserves zero RHS/zero solution convergence without relaxing any threshold. Nonzero operands whose product rounds to zero still receive an underflow allowance.
4. **Input dispatch:** the tighter helper is selected only for native float64 real matrix, RHS, solution and product arrays. The validated solver path exactly promotes its inputs before reaching this helper. Complex, integer and wider direct helper inputs retain the legacy conservative path rather than being silently narrowed.
5. **Regression test:** a Fraction-based test compares the bound against exact binary64 rational arithmetic for severe cancellation and a half-minimum-subnormal product.

The unchanged default residual failure tolerance is `1e-7`. The float32 BiCGSTAB cancellation counterexample remains rejected after exact widening because its recalculated residual is above that threshold. Complex64 certification, CSC conversion, exact integer promotion, nonfinite handling and zero RHS contracts were retained.

## Targeted validation

The exact eight CI nodeids were run sequentially, one pytest process per nodeid, with a 180-second timeout per process and monitored output, process-count and RSS limits. All eight passed after the changes. Peak RSS observed ranged from about 126 to 214 MiB; the longest process took 7.3 seconds. The existing scientific/reference assertions ran unchanged. A second bounded capture of the same seven numerical nodeids recorded their returned oracle values: MITC4 displacement error `0.2191%` against a `0.3%` bound; arc-length branch/restart/rollback invariants passed; both TET runner outputs remained `WARNING` because the 1% reference check is false. Those TET tests validate report generation and load-contract metadata, not qualification.

Twenty-three additional exact DA-005 algebraic and unit nodeids were run sequentially: 22 passed and two `longdouble`-specific nodes were skipped because the Windows platform's `longdouble` offers no precision beyond float64. The regression set covered zero RHS, well-conditioned systems, underflow, overflow, strong cancellation, integer exactness, float32 false-pass protection, complex64, CSR/CSC, nonfinite values and serialization-compatible input checks. No full test module was selected.

Additional checks:

| Check | Result |
|---|---|
| Ruff on changed Python files | PASS |
| `py_compile` on changed Python files | PASS |
| `git diff --check` | PASS |
| Full CI rerun | NOT_RUN by mandate |
| Linux post-fix targeted tests | NOT_RUN |
| WP12 / v8 FEM campaigns | NOT_RUN |

Individual nodeids and numerical diagnostics are recorded in [WP13_CI_TARGETED_TEST_RESULTS.json](WP13_CI_TARGETED_TEST_RESULTS.json).

## Mathematical scope and residual risks

The new bound is limited to real native float64 CSR matvecs under IEEE-754 round-to-nearest with gradual underflow. For a row with `k` stored entries, the SciPy 1.15.2 CSR template initializes a row sum and loops once over each stored entry using `sum += Ax[jj] * Xx[Aj[jj]]`; the `2k` operation budget covers at most one multiplication and one accumulation per entry. FMA contraction reduces roundings and is covered by this larger operation budget. The formula fails closed on nonfinite intermediates or when its operation-count condition is not met.

The bound certifies a residual for the represented matrix, RHS and returned floating-point solution; it does not certify forward solution accuracy. Dense 2-norm condition estimates are diagnostic only. The outer stable-norm margin is conservative and documented in the implementation; platform/compiler behavior outside the stated IEEE and SciPy CSR assumptions has not been exhaustively characterized. Complex CSR remains on the prior, broader bound.

The targeted post-fix runs were local Windows/Python 3.13.1, whereas the failing reference run was Ubuntu/Python 3.13.17. No full CI rerun was authorized. The correction changes distributed solver code, so v8 package hashes and smoke results remain valid only for their original commit and must not be attributed to the corrective source.

## Integration and release state

The corrective branch is separate from `emptiesvoids-cloud/0.2.12`; no merge, tag or publication was performed. G03 remains `FAIL_PRESERVED`, legal review remains `NOT_ACQUIRED`, and release remains `BLOCKED`.
