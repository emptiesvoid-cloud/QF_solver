# WP12-T — modal and TET4 scientific audit

**Scope:** `AUDIT_ONLY`; documentary additions and independent analytical recalculation.<br>
**Reviewed:** 2026-10-26.<br>
**New QF Solver tests, FEM solves, mesh generation and benchmarks:** `NOT_PERFORMED`.<br>
**WP11:** `CLOSED`; **WP12:** `OPEN`; **WP13:** `OPEN`.

This folder investigates the preserved modal `FAIL` and TET4 `WARNING` from WP12-S. It does not change their records, assertions, tolerances, model, implementation or qualification disposition. The audit distinguishes an observed cause from a plausible mechanism and from an unperformed discriminating experiment.

## Reading order

1. [Scientific audit summary](SCIENTIFIC_AUDIT_SUMMARY.md) — findings, confidence, limitations and decisions needed.
2. [Modal root cause](MODAL_2DOF_ROOT_CAUSE.md) and [prospective numerical criteria](MODAL_NUMERICAL_CRITERION_PROPOSAL.md).
3. [TET4 reference](TET4_REFERENCE_AUDIT.md), [implementation and model investigation](TET4_ROOT_CAUSE_INVESTIGATION.md), and [hypothesis matrix](TET4_HYPOTHESIS_MATRIX.md).
4. [Minimal prospective test plan](PROSPECTIVE_TEST_PLAN.md) — questions, dependencies and acceptance preparation; no execution authorization.

## Git identities and continuity

| Role | Commit | Tree |
|---|---|---|
| Integration/documentation snapshot at audit start | `8e3afe8ba89208c986e559712179fc992aa66c9d` | `a3b99ba6fa638b94bd91b0cd431f769cb2b4ff3c` |
| Frozen scientific candidate | `00428adf38e9397340ac136f6f503a268eb671da` | `df4ec667bf746b042c900fad1f86bf542e1a437b` |
| WP12-S runner, as recorded in receipts | `0bd8ebb5a886ac89a8216e65ff37d59fb510fb61` | `e31931fefb7012171e7e1a9f03511cd1c9987eda` |
| WP12-S tests and wrappers | `cb445462e3e59fa487c28a0914d8d23ad47205e6` | `92feabc4dc86f142e5c042a232c9c529ec6210bf` |

Local and remote integration HEAD agreed at the first row before edits; the integration checkout and scientific checkout were clean. `src/` has no Git differences between the frozen scientific commit and the integration snapshot. The modal oracle, extraction wrapper, modal projection/basis tests and structured-TET4 tests inspected here have no differences from the WP12-S test identity. These comparisons establish file continuity, not a numerical replay. This audit's later documentary commit does not replace any execution identity above.

## Existing evidence inspected

The [WP12-S execution report](../wp12_s/WP12_S_EXECUTION_REPORT.md), [frozen manifest](../wp12_s/WP12_S_QUANTITATIVE_MANIFEST.json), and [derived evidence index](../wp12_s/results/WP12-S-QUANT-001-20261026T095251Z/RESULTS_INDEX.json) provide the archive locator, case selection and identities. The manifest SHA-256 remains `df8c1401a122d18be270ba25bbd0f77c92ede5ff667d9fe4b87da62c10745d9c`.

The local raw archive was accessible. A read-only standard-library SHA-256 verification checked all eight raw receipts against the versioned index and each receipt sidecar, and checked all 38 declared output files against the raw receipt inventories. All matched. For the two focal cases, the before/after input inventories also agreed; their 20 distinct bound files matched the recorded SHA-256 values in the actual science/test/runner checkouts. Their before/after Git identities agreed, and each recorded attempt number is one. The verification reads bytes and JSON; it does not import the solver or rerun a test.

| Case | Existing run ID | Preserved status | Receipt SHA-256 |
|---|---|---|---|
| `MODAL-2DOF-POLY-001` | `20261026T095500Z-0494258ea65e` | `FAIL` | `a46d0d62740f79128552982ffd9c1835d458307bf6f9b261ba40320b02d3fd31` |
| `FEM-TET4-H-001` | `20261026T095627Z-aedceeb89280` | `PYTEST_PASS_ONLY`; helper `WARNING` | `e8d93fae9cc07021e89444727551e39313a59c292305f7d0643dd27e2b23f8be` |

Hash agreement supports integrity relative to the recorded local archive; it is not cryptographic proof of authorship or independent physical validity. Input inventories cover their named files, while the frozen Git identities identify the source trees. A historical output remains evidence for its recorded candidate, environment and criterion; this audit creates no current-HEAD numerical result.

## Authority and freshness

Read [AGENTS.md](../../../../AGENTS.md), the adopted [local V&V policy](../LOCAL_VV_POLICY.md), [qualification definitions](../../../../docs/ai/QUALIFICATION.md), the [V&V master plan](../../vv_master_plan/README.md), and the release [roadmap](../../ROADMAP.md) for their distinct scopes. Master-plan and early preparation pages are dated planning snapshots; statements there that a wrapper is absent or not yet run do not supersede the later WP12-S evidence. Existing dated documents remain unmodified.

The audit may recommend new test definitions and criteria for prospective review. It grants no new campaign attempt. Any implementation, changed criterion or replay needs a separately identified revision and explicit Owner authorization under the applicable policy.

## Documentary checks

The eight requested Markdown files are present. Static checks verified 66 relative links, Markdown heading anchors and source-line targets, consistent table column counts, and referenced test-function existence using Python AST inspection only. No pytest collection or test import was used. The new documents contain no employer references or personal-profile absolute paths. Final SHA-256 checks again matched the unchanged manifest, all eight historical receipts and all 38 recorded output files. Git delivery checks must retain this folder as the exclusive change scope.
