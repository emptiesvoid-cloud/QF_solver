---
doc_id: DOC-START-PUB-002
revision: 1.0
status: controlled_candidate
applicable_version: 0.2.11
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
report = check_mesh(model)
if report.status == "FAIL":
    raise RuntimeError(report.errors)
result = solve_model(model)
save_result(result, "results/tet4.json")
```

Use the public namespace for new integrations. The internal `solveur` package
is retained as a compatibility facade and is not the recommended application
surface.

## Before a production decision

Confirm that the element, analysis, material, loading, boundary conditions and
solver backend fall within a matching evidence scope. The linked 0.2.8
consolidated registry remains the authority for its 46 published
element-analysis records; the [current capability index](../capabilities/index.md)
adds separate later evidence without rewriting those historical decisions. For
mixed workflows or separate capabilities, read the controlling record. Review
the [known limitations](../etat/limites.md) and retain the input,
configuration and result files with the calculation record.

## Nonlinear example

The linear first calculation above remains the recommended first run. To
inspect one small nonlinear route, use the separate
[Total-Lagrangian TET4 example](nonlinear-example.md). It converges for its
declared input but reports an engineering-profile `WARNING`; that warning and
the route's maturity boundary are part of the example, not an error to
ignore or a general qualification claim.
