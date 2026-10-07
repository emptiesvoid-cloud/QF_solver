---
doc_id: DOC-DEMO-000
revision: 1.0
status: controlled
applicable_version: 0.2.11
reviewer: ""
approver: ""
---

# Demonstrations

Demonstrations are small, reproducible examples with a declared observable,
reference or invariant. They are useful for learning and verification; they do
not establish universal element or solver qualification.

## Public examples

The maintained JSON examples are in [`examples/`](https://github.com/emptiesvoid-cloud/QF_solver/tree/main/examples). Choose examples from the same source revision as the solver. The
shortest path is the [TET4 static quickstart](../getting-started/quickstart.md).
The public Python API is available through `qf_solver`.

## Evidence-aware demonstrations

Some demonstrations generate a result directory containing inputs, outputs,
diagnostics and a manifest. Read the reported residual, reactions, energy and
mesh checks together. A plausible displacement alone is not sufficient.

The published 0.2.8 boundaries remain in the
[historical verification summary](../verification/0_2_8/README.md). For
the cumulative 0.2.11 solver, consult the [capability index](../capabilities/index.md),
[V&V summary](../verification/0_2_11/README.md), the inherited
[0.2.10 evidence](../verification/0_2_10/README.md), and the bounded
[nonlinear example](../getting-started/nonlinear-example.md). Large-model
examples are described in [Large models](../solveurs/grand_modele.md).

Experimental [rotating-modal](../mechanics/rotating-modal.md) and
[Campbell](../mechanics/campbell.md) demonstrations retain their bounded
BEAM2/disk scope. GYRO-06 is internal mesh-convergence evidence, not physical
validation, and the high-frequency ambiguity at 100 rad/s is preserved.
