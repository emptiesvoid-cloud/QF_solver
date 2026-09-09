---
doc_id: DOC-REF-API-002
revision: 1.0
status: controlled
applicable_version: 0.2.8-development
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
The complete symbol inventory, signatures, stability categories, and exception
contract are maintained in the [`qf_solver` API contract](qf_solver_api.md).
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
the active [0.2.8 consolidated registry](../../qualification/0_2_8/consolidated_registry.json)
and separate mixed-workflow/capability records define those boundaries.

`qf_solver.read_inp(path)` remains `PROVISIONAL`; it covers only the documented
bounded Abaqus/CalculiX subset and is not a full-format compatibility claim.

The family-aware mixed HDF5 functions are also `PROVISIONAL` and
`EXPERIMENTAL_BOUNDED`: they cover the documented schema-v1.0 TET4/WEDGE6/HEX8
result-storage path only. Internal implementation symbols under `solveur` are
not stable API exports unless listed in the API contract.
