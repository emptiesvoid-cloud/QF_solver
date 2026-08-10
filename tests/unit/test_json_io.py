from pathlib import Path

import numpy as np
import pytest

from solveur.core.results import SolveResult
from solveur.io.json_reader import JsonModelReader
from solveur.io.json_writer import JsonResultWriter
from solveur.mesh.validation import MeshReport


def test_json_reader_loads_tet4_model():
    data = {
        "schema_version": 1,
        "units": {"system": "SI", "length": "m", "force": "N"},
        "verification_profile": "strict",
        "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        "materials": {"steel": {"type": "isotropic_3d", "E": 1.0, "nu": 0.25}},
    }
    model = JsonModelReader().from_dict(data)
    assert model.node_count == 4
    assert model.elements[0].type == "TET4"
    assert model.schema_version == 1
    assert model.units["force"] == "N"
    assert model.verification_profile == "strict"


def test_json_reader_reports_missing_required_fields():
    with pytest.raises(ValueError, match="root.elements is required"):
        JsonModelReader().from_dict(
            {
                "nodes": [[0, 0, 0]],
                "materials": {"steel": {"type": "isotropic_3d", "E": 1.0, "nu": 0.25}},
            }
        )


def test_json_reader_reports_precise_element_errors():
    with pytest.raises(ValueError) as exc_info:
        JsonModelReader().from_dict(
            {
                "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
                "elements": [{"type": "TET4", "nodes": [0, 1, 9], "material": "ghost"}],
                "materials": {"steel": {"type": "isotropic_3d", "E": 1.0, "nu": 0.25}},
            }
        )
    message = str(exc_info.value)
    assert "elements[0].nodes must contain exactly 4 node indices" in message
    assert "elements[0].nodes[2] references node 9" in message
    assert "elements[0].material references unknown material 'ghost'" in message


def test_json_reader_rejects_unknown_fields_and_bad_analysis_method():
    with pytest.raises(ValueError) as exc_info:
        JsonModelReader().from_dict(
            {
                "analysis": {"type": "linear_static", "method": "lanczos"},
                "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
                "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel", "tag": "A"}],
                "materials": {"steel": {"type": "isotropic_3d", "E": 1.0, "nu": 0.25}},
            }
        )
    message = str(exc_info.value)
    assert "analysis.method 'lanczos' is unsupported for linear_static" in message
    assert "elements[0] has unknown field(s): tag" in message


def test_json_reader_rejects_bad_schema_metadata_and_missing_dynamic_parameters():
    with pytest.raises(ValueError) as exc_info:
        JsonModelReader().from_dict(
            {
                "schema_version": 2,
                "units": {"system": "SI", "bad": "unit"},
                "verification_profile": "certified",
                "analysis": "transient_dynamic",
                "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
                "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
                "materials": {"steel": {"type": "isotropic_3d", "E": 1.0, "nu": 0.25, "density": 1.0}},
            }
        )
    message = str(exc_info.value)
    assert "schema_version 2 is unsupported" in message
    assert "units has unknown field(s): bad" in message
    assert "verification_profile 'certified' is unsupported" in message
    assert "analysis must define one of: time_step, dt" in message
    assert "analysis must define one of: steps, time_steps" in message


def test_json_reader_rejects_missing_harmonic_frequencies():
    with pytest.raises(ValueError, match="analysis.frequencies_hz is required"):
        JsonModelReader().from_dict(
            {
                "analysis": {"type": "harmonic_response", "method": "direct_frequency"},
                "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
                "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
                "materials": {"steel": {"type": "isotropic_3d", "E": 1.0, "nu": 0.25, "density": 1.0}},
            }
        )


def test_json_reader_rejects_invalid_boundary_and_load_fields():
    with pytest.raises(ValueError) as exc_info:
        JsonModelReader().from_dict(
            {
                "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
                "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
                "materials": {"steel": {"type": "isotropic_3d", "E": 1.0, "nu": 0.25}},
                "fixed_dofs": [{"node": 0, "dofs": ["BAD"]}],
                "loads": [{"node": 5, "dof": "UX", "value": True}],
            }
        )
    message = str(exc_info.value)
    assert "fixed_dofs[0].dofs[0] has unknown dof name 'BAD'" in message
    assert "loads[0].node references node 5" in message
    assert "loads[0].value must be a finite number" in message


def test_json_writer_saves_result(tmp_path: Path):
    model = JsonModelReader().from_dict(
        {
            "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
            "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
            "materials": {"steel": {"type": "isotropic_3d", "E": 1.0, "nu": 0.25}},
        }
    )
    dofs = model.dof_manager()
    result = SolveResult("PASS", np.zeros(dofs.ndof), dofs, MeshReport("PASS"), 4, 1)
    target = tmp_path / "result.json"
    JsonResultWriter().write(result, target)
    assert '"status": "PASS"' in target.read_text(encoding="utf-8")
