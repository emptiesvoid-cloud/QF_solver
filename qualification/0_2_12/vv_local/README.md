# Local V&V preparation — QF Solver v0.2.12

**Document status:** `PREPARATION_ONLY`<br>
**Numerical execution:** `NUMERICAL_EXECUTION_NOT_PERFORMED`<br>
**WP12:** `OPEN`<br>
**Reference science identity:** commit `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b`.

This folder defines a small, non-attested local verification route approved in principle by the Owner. It prepares four exact cases and a separate 2-DOF characteristic-polynomial oracle. No case-specific execution decision exists here, and the manifest is not an execution authorization.

## Start here

1. Read [the local policy](LOCAL_VV_POLICY.md) and [the recorded Owner policy decision](WP12_Q_OWNER_POLICY_DECISION.md).
2. Review the case-by-case oracle analysis in [FIRST_CAMPAIGN_ORACLE_REVIEW.md](FIRST_CAMPAIGN_ORACLE_REVIEW.md).
3. Inspect the frozen identities, source/test hashes and proposed operational budgets in [FIRST_CAMPAIGN_MANIFEST.json](FIRST_CAMPAIGN_MANIFEST.json). Verify its detached SHA-256 using [the sidecar](FIRST_CAMPAIGN_MANIFEST.sha256).
4. Follow [the execution plan](FIRST_CAMPAIGN_EXECUTION_PLAN.md) and [local runner design](LOCAL_RUNNER_DESIGN.md). A separate Owner decision for a specific case is still required before any run.
5. Use [WP12_R_READINESS.md](WP12_R_READINESS.md) to see what is ready, what remains conditional and what is explicitly not demonstrated.

The JSON schemas are [the campaign manifest schema](LOCAL_VV_MANIFEST_SCHEMA.json), [the per-case decision schema](OWNER_EXECUTION_DECISION_SCHEMA.json) and [the publication-data schema](PUBLICATION_DATA_SCHEMA.json). [The report template](PUBLICATION_REPORT_TEMPLATE.md) has separate detailed and public-facing sections; it contains no fabricated values or figures.

## Boundaries

- The local runner is separate from and does not modify or bypass the WP12-A/B/C signed runner.
- `VALIDATE` checks source, environment and import provenance without creating evidence directories. Its isolated diagnostic subprocess imports the frozen package plus NumPy/SciPy and reports native thread pools; it performs no FEM solve.
- `run` accepts one exact case from a frozen manifest and a separate decision record. The decision file's author is **not cryptographically authenticated** by this local runner. Owner review remains an external procedural requirement.
- Local execution is not a sandbox. It provides no hard CPU or memory quota, no guaranteed process-tree termination and no filesystem isolation. The current user account's filesystem permissions remain effective.
- Every result is at most a `PYTEST_PASS_ONLY` until its stated oracle is independently reviewed. Existing test assertions do not expose numerical values suitable for publication; the runner records `NOT_EXPOSED` unless a reviewed structured-result marker is emitted.
- WP11 remains `CLOSED` on its API/integration scope. WP12 and WP13 remain `OPEN`. No maturity, release or publication status is changed here.

## Scope at a glance

| Order | Case | Exact existing node | Evidence type | Preparation status |
|---|---|---|---|---|
| 1 | `ALG-PROJ-001` | Structured symmetric projection | Algebraic identity | Prepared; not authorized |
| 2 | `MODAL-DISCRETE-001` | Ground spring and concentrated mass | Closed-form discrete eigenfrequency | Prepared; not authorized |
| 3 | `MODAL-2DOF-001` | Coupled two-DOF modal basis | Existing same-SciPy-backend consistency; separate independent oracle test also prepared | Prepared; not authorized |
| 4 | `DYN-SDOF-001` | Undamped modal Newmark response | Analytic time response conditional on assembled FE operators | Prepared; not authorized |

The additional test `tests/unit/test_modal_two_dof_independent_oracle.py::test_two_dof_eigenvalues_match_independent_characteristic_polynomial` is a distinct scientific test. It is not included among the four executable manifest cases and has not been run.
