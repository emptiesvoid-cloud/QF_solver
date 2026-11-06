from __future__ import annotations

import json

import numpy as np
import pytest

from solveur.core.audit import SolverAudit, static_equilibrium_summary
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel, NodalLoad
from solveur.core.results import SolveResult
from solveur.io.json_reader import JsonModelReader
from solveur.mesh.validation import MeshValidator


def _model_with_nodal_load(value: object) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 0, "dof": "UX", "value": value}],
    )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), True, np.bool_(True), "2.5", "bad"])
def test_mesh_validator_rejects_nonfinite_or_nonnumeric_nodal_load_values(value: object) -> None:
    model = _model_with_nodal_load(1.0)
    model.loads[0] = NodalLoad(node=0, dof="UX", value=value)  # type: ignore[arg-type]
    report = MeshValidator().validate(model)

    assert report.status == "FAIL"
    assert "Nodal load 0: value must be a finite scalar." in report.errors
    assert report.details["mechanical_rank"] == {"checked": False, "reason": "input validation failed"}
    assert any("input validation failed" in warning for warning in report.warnings)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), True, np.bool_(True), "2.5", "bad"])
def test_from_raw_rejects_nonfinite_or_implicitly_coerced_nodal_load_values(value: object) -> None:
    with pytest.raises(InputValidationError, match=r"loads\[0\]\.value"):
        _model_with_nodal_load(value)


def test_from_raw_accepts_finite_python_and_numpy_numeric_load_scalars() -> None:
    values = (2, 2.5, np.int64(3), np.float32(4.0))

    for value in values:
        model = _model_with_nodal_load(value)
        assert model.loads[0].value == pytest.approx(float(value))


def test_json_schema_rejects_unrepresentable_integer_nodal_load_cleanly() -> None:
    data = {
        "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        "materials": {"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        "fixed_dofs": [
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        "loads": [{"node": 0, "dof": "UX", "value": 10**400}],
    }

    with pytest.raises(InputValidationError, match=r"loads\[0\]\.value must be a finite number"):
        JsonModelReader().from_dict(data)


def test_finite_nodal_load_on_fixed_dof_remains_reportable_and_json_serializable() -> None:
    model = _model_with_nodal_load(2.0)
    report = MeshValidator().validate(model)
    assert report.status != "FAIL"

    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    fixed = assembler.fixed_indices(model, dofs)
    free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
    loads = assembler.assemble_loads(model, dofs)
    equilibrium = static_equilibrium_summary(
        model=model,
        dofs=dofs,
        loads=loads,
        internal=np.zeros(dofs.ndof),
        displacement=np.zeros(dofs.ndof),
        fixed=fixed,
        free=free,
    )
    audit = SolverAudit(
        analysis=model.analysis.type,
        method=model.analysis.method,
        node_count=model.node_count,
        element_count=len(model.elements),
        ndof=dofs.ndof,
        mesh_status=report.status,
        equilibrium=equilibrium,
        detail="values",
    )
    result = SolveResult(
        status="PASS",
        displacements=np.zeros(dofs.ndof),
        dofs=dofs,
        mesh_report=report,
        node_count=model.node_count,
        element_count=len(model.elements),
        audit=audit,
    )

    exported = json.loads(json.dumps(result.to_dict(), allow_nan=False))
    reaction = next(row for row in exported["audit"]["equilibrium"]["reactions"] if row["dof"] == "UX")
    assert reaction["node"] == 0
    assert reaction["value"] == pytest.approx(-2.0)
