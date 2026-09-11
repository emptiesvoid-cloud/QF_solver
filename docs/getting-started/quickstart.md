---
doc_id: DOC-START-PUB-002
revision: 1.0
status: controlled
applicable_version: 0.2.8
reviewer: ""
approver: ""
---

# First calculation

## CLI

From a checkout containing the maintained example:

```powershell
qf-solver check-mesh --input .\examples\tet4_static.json
qf-solver solve --input .\examples\tet4_static.json --output .\results\tet4.json
```

The output JSON contains the solved fields and the diagnostics produced for
the selected route. Inspect the reported residual and reaction balance before
using a result.

## Python API

```python
from qf_solver import check_mesh, load_model, save_result, solve_model

model = load_model("examples/tet4_static.json")
check_mesh(model)
result = solve_model(model)
save_result(result, "results/tet4.json")
```

Use the public namespace for new integrations. The internal `solveur` package
is retained as a compatibility facade and is not the recommended application
surface.

## Before a production decision

Confirm that the element, analysis, material, loading, boundary conditions and
solver backend all fall within the
[0.2.8 consolidated registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/consolidated_registry.json)
and, for mixed workflows or separate capabilities, the linked delivery record.
Read the [known limitations](../etat/limites.md) and retain the input,
configuration and result files with the calculation record.
