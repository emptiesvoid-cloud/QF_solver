# Owner decisions required before any WP12 V&V execution

**Status:** DECISION_REQUEST — no approval implied.
**Execution:** NUMERICAL_EXECUTION_NOT_PERFORMED.
**WP12:** OPEN.

Please record decisions against this plan revision. Silence, a prior general agreement, or a commit of these documents is not approval to execute a scientific test.

## A. Policy and governance

1. Accept or reject `QUALIFICATION_LOCAL_VV` in [LOCAL_VV_POLICY_PROPOSAL.md](LOCAL_VV_POLICY_PROPOSAL.md).
2. Approve an explicit repository-policy amendment path for qualification-only exact-node runs, consistent with AGENTS.md. Until amended and reviewed, development test permissions do not authorize a qualification run.
3. Confirm that ordinary local runs remain non-attested and do not meet the signed WP12 runner’s cryptographic or sandbox guarantees.
4. Confirm that the historic runner, trust requirements, execution denial, manifests and evidence records remain unchanged.

## B. Scope and priority

1. Approve the capability rows marked P0 as the initial mandatory scope, or provide a bounded alternative.
2. Decide whether inherited rotor preservation, RBE/MPC, optional backend behavior, and experimental E01 functions are MUST, SHOULD, or DEFERRED for the WP12 gate.
3. Confirm that WP-C01 negative/remediation-open, WP-C02 AR/N03-only, WP-D01 INCONCLUSIVE, WP-D02 CLOSED_BOUNDED, WP-E01 OPEN_WITH_BOUNDED_CERTIFICATES and WP11 CLOSED API-only remain unmodified.

## C. Criteria and references

1. Confirm which frozen contract tolerances apply without translation.
2. Resolve every CRITERION_TO_REVIEW before its measured case starts.
3. Approve the observable and reference for FEM-TET4-H-001, including mesh levels and smooth sampling region.
4. Approve the parameter case for STAT-BEAM-001 after resolving exact pytest parameter ID.
5. Decide whether a new exact analytic direct-Newmark node is required.
6. Approve correlation mappings individually; no broad Code_Aster equivalence is assumed.

## D. First campaign

Proposed order: ALG-PROJ-001; MODAL-DISCRETE-001; MODAL-2DOF-001; DYN-SDOF-001; then one static analytic and one multi-mesh FEM case after exact node/criteria review.

For each case, approve:

- One exact nodeid or a new bounded harness.
- Exact source/test/fixture hashes and science commit/tree.
- Absolute Python executable and venv; import-origin check.
- Command, working directory, environment variables and dependencies.
- Result directory and no-overwrite/archive method.
- Attempt count, timeout/resources and stop-on-failure rule.
- Frozen oracle, criteria, output interpretation and reviewer.

The commands in the catalog are proposals only. A proposed command cannot override the current repository policy.

## E. Historical identities and future releases

Confirm the separate identity fields for science, runner/integration, tests/fixtures, and environment. Confirm how v0.2.11 evidence is cited without being relabeled as a v0.2.12 run. Future v0.3.0 work should fork this template and replace release-specific identity/status records without rewriting this historic v0.2.12 plan.
