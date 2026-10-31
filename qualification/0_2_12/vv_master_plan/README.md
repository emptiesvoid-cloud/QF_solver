# WP12 scientific V&V master plan

**Document status:** PREPARATION_ONLY
**Execution status:** NUMERICAL_EXECUTION_NOT_PERFORMED
**Status at this plan’s review snapshot (2026-10-26):** WP12 OPEN
**Current WP12 status (Owner decision 2026-10-31):** `WP12_CLOSED_BOUNDED_FOR_0_2_12_ALPHA` — [bounded global decision](../WP12_GLOBAL_OWNER_BOUNDED_CLOSURE_DECISION_20261031.md)
**Reviewed:** 2026-10-26; status cross-reference updated 2026-10-31
**Repository snapshot inspected:** integration branch emptiesvoids-cloud/0.2.12, commit aba532b6f4bb7b81a17ace3e9631fc2ce99d0b6b, tree 6fea918568d47464bf78b49aaf6b34d6e1584642
**Frozen scientific candidate:** commit 00428adf38e9397340ac136f6f503a268eb671da, tree df4ec667bf746b042c900fad1f86bf542e1a437b

This folder proposes a progressive verification and validation program for the implemented QF Solver v0.2.12 candidate. It is a planning record, not an execution authorization, new qualification decision, or release approval. The present review used source, contracts, tests, and reports as static records only. No pytest, solver, FEM calculation, benchmark, Code_Aster, or Docker process was run.

The integration branch contains later runner and documentation work. The scientific source identity remains the frozen candidate listed above; these identities must not be collapsed into one. Existing reports retain the source, model, environment, and manifest identities recorded by their authors.

## Read in this order

1. [VV_MASTER_PLAN.md](VV_MASTER_PLAN.md) — scope, evidence vocabulary, acceptance method, and governance.
2. [CAPABILITY_TEST_MATRIX.csv](CAPABILITY_TEST_MATRIX.csv) — filterable map from capability to code, tests, contracts, evidence, gaps, and proposed wave.
3. [BENCHMARK_CATALOG.md](BENCHMARK_CATALOG.md) — proposed cases and first local campaign.
4. [ANALYTICAL_REFERENCE_PLAN.md](ANALYTICAL_REFERENCE_PLAN.md) and [FEM_CONVERGENCE_PLAN.md](FEM_CONVERGENCE_PLAN.md) — oracles and discretization studies.
5. [EXTERNAL_CORRELATION_BACKLOG.md](EXTERNAL_CORRELATION_BACKLOG.md) — Code_Aster / independent-code candidates.
6. [GAP_ANALYSIS.md](GAP_ANALYSIS.md), [EXECUTION_WAVES.md](EXECUTION_WAVES.md), and [HISTORICAL_EVIDENCE_CROSSWALK.md](HISTORICAL_EVIDENCE_CROSSWALK.md) — risks, sequencing, and bounded historical claims.
7. [LOCAL_VV_POLICY_PROPOSAL.md](LOCAL_VV_POLICY_PROPOSAL.md), [OWNER_PLAN_DECISION.md](OWNER_PLAN_DECISION.md), and [INVENTORY_AUDIT.md](INVENTORY_AUDIT.md) — decisions and independent challenge.

## Normative boundaries

- At the 2026-10-26 plan review snapshot, WP11 was CLOSED for its approved API/integration scope, and WP12/WP13 remained OPEN. The later bounded WP12 closure is administrative and does not grant general qualification or publication approval; operational WP13 remains OPEN.
- WP-C01 remains CLOSED_NEGATIVE with remediation open. WP-C02 remains CLOSED_BOUNDED for AR/N03 only. WP-D01 remains INCONCLUSIVE. WP-D02 remains CLOSED_BOUNDED. WP-E01 remains OPEN_WITH_BOUNDED_CERTIFICATES.
- Historical v0.2.11 rotating-modal and Campbell evidence remains EXPERIMENTAL.
- The historical WP12 security runner and its refusal behavior remain intact. The local route in this folder is a proposal and does not override AGENTS.md or authorize execution.
- A file containing a test, benchmark, route, report, or PASS label is not by itself evidence that the frozen candidate was run and accepted.

See the [roadmap](../ROADMAP.md), [repository execution policy](../../../AGENTS.md), and [AI knowledge base](../../../docs/ai/INDEX.md) for source navigation and current governance.
