---
title: Nonlinear example
doc_id: DOC-START-NONLINEAR-001
revision: 1.0
applicable_version: 0.2.11
status: controlled_candidate
reviewer: ""
approver: ""
---

# Nonlinear example

This short example runs a repository fixture for the bounded
Total-Lagrangian TET4 static route. It demonstrates that the CLI route can run;
it is not a qualification claim. The solver intentionally reports a
`WARNING` maturity verdict for this research-profile route.

## 1. Input

Use the checked-in fixture
[`examples/tet4_geometric_nonlinear_static.json`](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/examples/tet4_geometric_nonlinear_static.json).
It defines a small static TET4 problem using the geometric-nonlinear analysis
route.

## 2. Install and solve

From the repository root, install the source checkout into an environment with
the project dependencies available, then run the tested CLI entry script:

```bash
python -m pip install -e .
python qf_solver.py solve \
  --input examples/tet4_geometric_nonlinear_static.json \
  --output nonlinear-result.json
```

This checked-in example is also exercised by the CLI integration test. The
same installed environment can use `qf-solver --help` to inspect the installed
entry point and other available options.

## 3. Check the result

The fixture returns `status: success`, `solver.converged: true`, and writes
the result to `nonlinear-result.json`. Inspect the nonlinear convergence
summary with:

```python
import json
from pathlib import Path

result = json.loads(Path("nonlinear-result.json").read_text(encoding="utf-8"))
solver = result["solver"]
print(solver["converged"], solver["newton_iterations"])
print(solver["final_relative_residual"], solver["scope"])
print(result["run_verdict"], solver["maturity"])
```

Its overall run verdict is `WARNING`, because the maturity profile is
`research` under the selected engineering profile. That warning is expected
and must not be relabeled as a qualified engineering result.

Inspect the JSON result and solver diagnostics before using any output. A
successful nonlinear iteration only establishes that this input completed on
this route; it does not validate the physical model or establish accuracy for
another mesh, element family, constitutive model, or load path.

## 4. Applicable limitation

The current geometric campaign covers selected Total-Lagrangian St.
Venant–Kirchhoff static serial TET4/HEX8 cases with explicit deformation and
formulation bounds. The final audit recorded `GO_WITH_LIMITATIONS` without a
maturity promotion. This example is a convenient smoke test, not a replacement
for the [0.2.10 V&V summary](../verification/0_2_10/README.md) or the
[known limitations](../etat/limites.md).
