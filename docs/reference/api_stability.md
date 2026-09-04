---
doc_id: DOC-REF-API-002
revision: 1.0
status: controlled
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# API stability

## Public namespace

New integrations should import from `qf_solver`:

```python
from qf_solver import check_mesh, load_model, save_result, solve_model
```

The standard flow is `load_model -> check_mesh -> solve_model -> save_result`.
The package version is available without importing implementation modules:

```python
from qf_solver import __version__
print(__version__)
```

The `solveur` namespace remains a compatibility facade for existing 0.2.x
applications. The recommended CLI is `qf-solver`; legacy entry points remain
available for compatibility but should not be used in new integrations.

## Compatibility boundary

JSON v1 inputs remain supported where the documented schema permits them. CLI
commands and stable exit codes are part of the public interface. Interface
stability does not qualify every element, analysis or material combination;
the active [capability matrix](../verification/0_2_7/0_2_7_capability_matrix.md)
defines those boundaries.
