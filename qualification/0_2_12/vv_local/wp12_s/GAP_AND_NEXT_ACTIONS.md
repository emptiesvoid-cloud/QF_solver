# WP12-S gaps and next actions

**Status:** `EXECUTION_RECORDED`<br>
**Numerical execution:** `PERFORMED_FOR_EIGHT_AUTHORIZED_CASES`<br>
**WP12:** `OPEN`

## What remains

1. The Owner approved all eight case IDs individually against manifest SHA-256 `df8c1401a122d18be270ba25bbd0f77c92ede5ff667d9fe4b87da62c10745d9c`, including the accepted local non-attested limits. Each case was executed sequentially once. The original manifest remains unchanged and retains its prepared status.
2. The execution report records all eight results and the independent read-only review. Seven test processes reported `PYTEST_PASS_ONLY`; the polynomial modal case remains `FAIL`; the TET4 helper reports `WARNING`. None of these is a WP12 qualification verdict.
3. The independent reviewer checked receipt identities, output hashes, the exact polynomial assertion failure, and the bounded interpretation of TET4. No further execution is authorized by this campaign decision.
4. Any follow-up—investigating the zero-atol assertion, obtaining an independent modal oracle, temporal convergence, a justified 3-D TET4 reference/correlation, or broader tests and benchmarks—requires a separately reviewed scope and Owner decision.

## Known evidence gaps

- WP12-R stdout/receipts do not contain Q1–Q4 numerical values.
- Q3's old same-backend test is not an independent eigenvalue reference; the separate polynomial unit is independent only for scalar eigenvalues.
- Q4 tests one time step; no time convergence is established, and its analytic frequency is derived from the prepared FE K/M.
- BEAM2 covers one element and two principal planes; it is not a general beam convergence or 3-D validation study.
- TET4 lacks a validated independent 3-D reference. Its 1-D beam comparison is diagnostic, and three meshes may not establish the asymptotic regime.
- The prior TET4 plan's element counts need correction in any later normative summary; this package uses source-derived counts 12/96/768.
- Derived internal tables and figures now exist under the results directory. They are not publication approval and do not replace the raw external receipts.

## Independent review follow-up — 2026-10-26

- The reviewer identified that a pytest pass could be recorded even when an instrumented test emitted no quantitative marker. Resolved for this campaign: all eight cases pin the exact schema `qf-wp12-s-observables-v1`; the runner rejects an empty schema declaration, requires the marker when specified, and checks the case ID. A pass with a missing required payload becomes `INFRA_ERROR`. A scientific JUnit `FAIL` is preserved even if its numeric payload is absent or malformed. A synthetic regression test was added; it was not executed in this mission.
- The reviewer also reported that several wrappers emitted after their assertions. That finding is not reproducible in the pinned test source: each `_emit()` precedes its post-computation acceptance assertions (`tests/unit/test_wp12_s_quantitative_extraction.py`, lines 68/81, 104/117, 141/161, 196/227, 280/297, 321/345, and 400/430). TET4's initial output-absence and mesh-plan checks precede the solve; its calculated summary is emitted before the post-run result assertions.
- Runner identity is commit `0bd8ebb5a886ac89a8216e65ff37d59fb510fb61`, tree `e31931fefb7012171e7e1a9f03511cd1c9987eda`. The manifest binds that identity and has SHA-256 `df8c1401a122d18be270ba25bbd0f77c92ede5ff667d9fe4b87da62c10745d9c`.
- Static lint and formatting checks passed. No WP12-S test node, solver, FEM study, benchmark, or plotting code was executed. The earlier Owner decision remains inapplicable to this manifest; new per-case decisions are required.
