---
doc_id: DOC-DEMO-000
revision: 1.0
status: controlled
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# Demonstrations

Demonstrations are small, reproducible examples with a declared observable,
reference or invariant. They are useful for learning and verification; they do
not establish universal element or solver qualification.

## Public examples

The maintained JSON examples are in [`examples/`](../../examples/). The
shortest path is the [TET4 static quickstart](../getting-started/quickstart.md).
The public Python API is available through `qf_solver`.

## Evidence-aware demonstrations

Some demonstrations generate a result directory containing inputs, outputs,
diagnostics and a manifest. Read the reported residual, reactions, energy and
mesh checks together. A plausible displacement alone is not sufficient.

The active 0.2.7 capability and evidence boundaries are in the
[verification summary](../verification/0_2_7/README.md). Large-model examples
are described in [Large models](../solveurs/grand_modele.md).
