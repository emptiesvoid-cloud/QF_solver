from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from solveur.core.errors import InputValidationError
from solveur.io.model_writer import (
    _contact,
    _concentrated_mass,
    _distributed_load,
    _rbe2,
    _rbe3,
    _spring,
    model_to_dict,
)
from solveur.io.json_reader import JsonModelReader
from solveur.loads.entities import BodyLoad, EdgeLoad, GravityLoad, LineLoad, SurfaceLoad
from solveur.large.audit import LargeAuditReport
from solveur.large.generator import generate_tet4_block
from solveur.large.optimization import (
    _binary_relative_error,
    _display,
    _mpi_broadcast,
)
from solveur.large.solver import (
    LargeSolveResult,
    _audit_from_dict,
    _guard_scipy_size,
    _summary,
    _write_outputs,
)


def test_large_solver_size_guard_accepts_override_and_rejects_over_limit(tmp_path: Path) -> None:
    model = generate_tet4_block(tmp_path / "model.npz", nx=1, ny=1, nz=1)
    _guard_scipy_size(model, {"scipy_max_dofs": model.ndof})
    with pytest.raises(InputValidationError, match="memory explosion"):
        _guard_scipy_size(model, {"scipy_max_dofs": model.ndof - 1})


def test_large_solver_summary_and_audit_conversion_are_stable() -> None:
    audit = LargeAuditReport(status="PASS", errors=(), warnings=("warning",), details={"ndof": 12})
    summary = _summary(
        SimpleNamespace(
            analysis={"type": "linear_static"},
            node_count=4,
            element_count=1,
            ndof=12,
            nodes=np.zeros((4, 3)),
            tet4=np.zeros((1, 4), dtype=np.int64),
        ),
        "matrix_free",
        {"converged": True},
        0.25,
        0.5,
        audit,
    )
    assert summary["backend"] == "matrix_free"
    assert summary["audit_status"] == "PASS"
    converted = _audit_from_dict({"status": "WARNING", "warnings": ["w"], "details": {"x": 1}})
    assert converted.status == "WARNING"
    assert converted.warnings == ("w",)


def test_large_solver_writes_file_backed_outputs(tmp_path: Path) -> None:
    model = generate_tet4_block(tmp_path / "model.npz", nx=1, ny=1, nz=1)
    audit = LargeAuditReport(status="PASS", errors=(), warnings=(), details={})
    result = LargeSolveResult("PASS", "scipy", {"ndof": model.ndof}, audit)
    files = _write_outputs(model, result, np.zeros(model.ndof), tmp_path / "outputs")

    assert set(files) == {"summary", "audit_large", "displacements"}
    assert (tmp_path / "outputs" / files["summary"]).is_file()
    assert (tmp_path / "outputs" / files["audit_large"]).is_file()
    assert (tmp_path / "outputs" / files["displacements"]).is_file()


def test_model_writer_optional_entity_fields_are_json_compatible() -> None:
    spring = _spring(
        SimpleNamespace(
            node_a=0,
            node_b=1,
            dofs=("UX",),
            stiffness=((10.0,),),
            coordinate_system="local",
            orientation=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        )
    )
    assert spring["node_b"] == 1
    assert spring["orientation"][0] == [1.0, 0.0, 0.0]

    contact = _contact(
        SimpleNamespace(
            name="contact",
            slave_node=2,
            gap_tolerance=1.0e-8,
            master_nodes=(0, 1, 3),
            master_faces=None,
            friction_coefficient=0.2,
            tangential_stiffness=100.0,
        )
    )
    assert contact["master_nodes"] == [0, 1, 3]
    assert contact["friction_coefficient"] == 0.2

    surface = _distributed_load(SurfaceLoad(0, "pressure", 2.0, face=1))
    edge = _distributed_load(EdgeLoad(0, 2, (1.0, 2.0, 3.0), "local"))
    line = _distributed_load(LineLoad(0, (1.0, 2.0, 3.0)))
    gravity = _distributed_load(GravityLoad((0.0, 0.0, -9.81), elements=(0, 1)))
    body = _distributed_load(BodyLoad((1.0, 0.0, 0.0), elements=(0,), coordinate_system="local"))
    pressure = _distributed_load(SurfaceLoad(0, "pressure", 2.0, face=2))
    mass = _concentrated_mass(
        SimpleNamespace(
            node=0,
            mass=1.0,
            center_of_mass=(0.0, 0.0, 0.0),
            inertia=((1.0, 0.0, 0.0),) * 3,
        )
    )
    assert surface["face"] == 1
    assert edge["edge"] == 2
    assert line["type"] == "line_load"
    assert gravity["elements"] == [0, 1]
    assert body["coordinate_system"] == "local"
    assert pressure["face"] == 2
    assert mass["inertia"][0] == [1.0, 0.0, 0.0]


def test_model_writer_rbe_and_round_trip_keep_controlled_fields() -> None:
    assert _rbe2(SimpleNamespace(name="r", master=0, slaves=(1, 2), tie_rotations=True)) == {
        "name": "r",
        "master": 0,
        "slaves": [1, 2],
        "tie_rotations": True,
    }
    assert _rbe3(
        SimpleNamespace(
            name="w",
            reference=0,
            independents=((1, 0.5), (2, 0.5)),
            dofs=("UX",),
            mode="average",
        )
    )["independents"] == [{"node": 1, "weight": 0.5}, {"node": 2, "weight": 0.5}]

    root = Path(__file__).resolve().parents[2]
    model = JsonModelReader().read(root / "examples" / "frictionless_contact_surface.json")
    encoded = model_to_dict(model)
    restored = JsonModelReader().from_dict(encoded)
    assert restored.contacts == model.contacts
    assert restored.springs == model.springs


def test_scaling_binary_error_handles_zero_reference_and_rejects_bad_metadata(tmp_path: Path) -> None:
    reference = tmp_path / "reference.bin"
    candidate = tmp_path / "candidate.bin"
    np.zeros(3, dtype=np.float64).tofile(reference)
    np.ones(3, dtype=np.float64).tofile(candidate)
    metadata = {"dtype": "float64", "byte_order": "little", "shape": [1, 3], "flat_size": 3}
    for path in (reference, candidate):
        path.with_name("displacements_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    assert _binary_relative_error(reference, candidate) == pytest.approx(np.sqrt(3.0))

    bad = tmp_path / "bad.bin"
    np.zeros(3, dtype=np.float64).tofile(bad)
    bad.with_name("displacements_metadata.json").write_text(
        json.dumps({**metadata, "dtype": "float32"}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Invalid distributed"):
        _binary_relative_error(reference, bad)


def test_scaling_display_and_non_mpi_broadcast_contract() -> None:
    assert _display(None) == ""
    assert _display(1.23456789) == "1.23457"
    assert _display(4) == "4"
    try:
        import mpi4py  # noqa: F401
    except ImportError:
        value = {"status": "PASS"}
        assert _mpi_broadcast(value) == value
