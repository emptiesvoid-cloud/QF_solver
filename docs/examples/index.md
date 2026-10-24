---
doc_id: DOC-EXAMPLES-000
revision: 1.0
status: controlled
applicable_version: 0.2.11
reviewer: ""
approver: ""
---

# Examples

The maintained examples live in the repository `examples/` directory and use
the public `qf_solver` API or the `qf-solver` CLI. Start with
[`tet4_static.json`](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/examples/tet4_static.json) and the
[first-calculation guide](../getting-started/quickstart.md).

Examples demonstrate a concrete workflow; they do not qualify every possible
combination of element, load, material and solver.

The repository also contains an internal 0.2.12 integration-candidate example
for [experimental B* frictional contact](../../examples/contact/frictional_bstar_small_rotation/README.md).
It is explicitly opt-in, never runs during test or documentation generation,
and does not change the published 0.2.11 capability claims.

Use examples from the same source revision as the installed solver. For a
bounded nonlinear workflow, see the
[nonlinear example](../getting-started/nonlinear-example.md). It is a smoke
test for one research-profile Total-Lagrangian TET4 route, not a general
qualification claim.

The [rotating-modal guide](../mechanics/rotating-modal.md) and
[Campbell guide](../mechanics/campbell.md) cover the experimental disk-gyroscopic
API. Their scope is not general rotordynamics; see the explicit limitations
and ambiguity diagnostics before interpreting results.
