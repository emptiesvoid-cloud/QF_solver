# WP12-V2 — H1 TET4 operator audit

**PREPARATION_ONLY · NUMERICAL_EXECUTION_NOT_PERFORMED · WP12_STATUS=OPEN**
**Campaign status: PREPARED_NOT_AUTHORIZED**

This folder prepares one prospective H1 experiment, `TET4-H1-OPERATOR-AUDIT-002`. It investigates the archived 12-element H1 model and does not launch a solve, change the production formulation, revise U3, or qualify TET4 generally.

## Navigation

- [Experiment plan](V2_EXPERIMENT_PLAN.md)
- [Numerical criteria](V2_NUMERICAL_CRITERIA.md)
- [Frozen candidate manifest](V2_MANIFEST.json)
- [Owner decision package](V2_OWNER_DECISION_PACKAGE.md)
- [Results report stub](V2_RESULTS_REPORT.md)
- [Local V&V policy](../LOCAL_VV_POLICY.md)
- [WP12-V audit summary](../wp12_v_audit/SCIENTIFIC_AUDIT_SUMMARY.md)
- [Matrix-free/direct evidence review](../wp12_v_audit/MATRIX_FREE_DIRECT_EVIDENCE_REVIEW.md)
- [Prospective V2 test plan](../wp12_v_audit/PROSPECTIVE_V2_TEST_PLAN.md)

## Identity and scope

The scientific checkout is frozen at commit `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b`. The test checkout is pinned separately at commit `653fc0b9895c24429c5605e05fabf604cc358f48`, tree `6f973c272a65b1a07aec7bf968e8539b8236ddf2`. The local V&V runner is separately pinned at commit `9b1465d79cb19985c823c1329af2540de665a556`, tree `8b85486840de30f7e8ccd5cec1b5bc744c7fbcb0`.

The H1 input is 12 TET4, 12 nodes, 36 total DOFs and 24 free DOFs; its SHA-256 is `4807fea4cde876f57ef1e376f9b0791f5367526d182e236655b39e73e57baa7d`. The prospective test also binds a derived JSON subset of the verified U3 receipt. Its SHA-256 and the original receipt, manifest, fixture, test source and runner identities are recorded in that JSON and in the manifest. The derivative is a new input copy; the historical receipt and archive remain untouched.

The only proposed nodeid is `tests/unit/test_wp12_v2_tet4_operator_audit.py::test_tet4_h1_operator_audit_002`. The exact-one-node local V&V runner is required. The test performs stiffness assembly and matrix-free products for canonical vectors; it performs **no new linear solve**. Those operations still count as scientific execution and remain unauthorized here.

The existing U3 verdict remains `FAIL`; U1 and U2 remain `PYTEST_PASS_ONLY`. This prospective test has no result yet. A future `PYTEST_PASS_ONLY` would establish only the checks stated for this discrete H1 model, not continuum accuracy, convergence, or general TET4 equivalence. WP12 remains OPEN.
