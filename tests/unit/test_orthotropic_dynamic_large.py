from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from solveur.api import (
    generate_large_tet4_block,
    load_large_model,
    postprocess_large_model,
    solve_large_model,
    solve_model,
)
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.large.io import from_finite_element_model, save_large_model


def _isotropic_material() -> dict[str, float | str]:
    return {"type": "isotropic_3d", "E": 1000.0, "nu": 0.25, "density": 10.0}


def _equivalent_orthotropic_material() -> dict[str, float | str]:
    young = 1000.0
    poisson = 0.25
    shear = young / (2.0 * (1.0 + poisson))
    return {
        "type": "orthotropic_3d",
        "E1": young,
        "E2": young,
        "E3": young,
        "nu12": poisson,
        "nu13": poisson,
        "nu23": poisson,
        "G12": shear,
        "G13": shear,
        "G23": shear,
        "density": 10.0,
        "orientation": [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
    }


def _anisotropic_material() -> dict[str, object]:
    return {
        "type": "orthotropic_3d",
        "E1": 145.0e9,
        "E2": 12.0e9,
        "E3": 9.0e9,
        "nu12": 0.24,
        "nu13": 0.21,
        "nu23": 0.28,
        "G12": 5.5e9,
        "G13": 4.8e9,
        "G23": 3.9e9,
        "density": 1580.0,
        "e1": [2.0**-0.5, 2.0**-0.5, 0.0],
        "e2_hint": [-(2.0**-0.5), 2.0**-0.5, 0.0],
    }


def _solid_model(
    element_type: str,
    material: dict[str, object],
    analysis: dict[str, object],
) -> FiniteElementModel:
    if element_type == "TET4":
        nodes = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
        connectivity = list(range(4))
        fixed_nodes = (0, 2, 3)
    else:
        nodes = [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
            [0.5, 0, 0],
            [0.5, 0.5, 0],
            [0, 0.5, 0],
            [0, 0, 0.5],
            [0.5, 0, 0.5],
            [0, 0.5, 0.5],
        ]
        connectivity = list(range(10))
        fixed_nodes = (0, 2, 3, 6, 7, 9)
    return FiniteElementModel.from_raw(
        analysis=analysis,
        nodes=nodes,
        elements=[{"type": element_type, "nodes": connectivity, "material": "solid"}],
        materials={"solid": material},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=([{"node": 1, "dof": "UX", "value": 1000.0}] if analysis["type"] == "linear_static" else []),
    )


@pytest.mark.parametrize("element_type", ["TET4", "TET10"])
def test_orthotropic_modal_matches_equivalent_isotropic(element_type: str) -> None:
    analysis = {"type": "modal", "method": "eigh", "modes": 3}
    isotropic = solve_model(_solid_model(element_type, _isotropic_material(), analysis))
    orthotropic = solve_model(_solid_model(element_type, _equivalent_orthotropic_material(), analysis))

    assert np.allclose(orthotropic.frequencies_hz, isotropic.frequencies_hz, rtol=1.0e-11)
    assert orthotropic.solver["max_relative_residual"] < 1.0e-10
    assert orthotropic.solver["mass_orthogonality_error"] < 1.0e-10


@pytest.mark.parametrize("element_type", ["TET4", "TET10"])
def test_orthotropic_newmark_matches_equivalent_isotropic(element_type: str) -> None:
    analysis = {
        "type": "transient_dynamic",
        "method": "newmark",
        "time_step": 0.001,
        "steps": 12,
        "newmark_beta": 0.25,
        "newmark_gamma": 0.5,
        "load_factors": [0.0],
        "initial_displacements": [{"node": 1, "dof": "UX", "value": 1.0e-3}],
    }
    isotropic = solve_model(_solid_model(element_type, _isotropic_material(), analysis))
    orthotropic = solve_model(_solid_model(element_type, _equivalent_orthotropic_material(), analysis))

    assert np.allclose(orthotropic.displacements, isotropic.displacements, rtol=1.0e-10, atol=1.0e-13)
    assert np.allclose(orthotropic.velocities, isotropic.velocities, rtol=1.0e-10, atol=1.0e-13)
    assert max(orthotropic.solver["residual_history"]) < 1.0e-9
    assert all(np.isfinite(row["total_energy"]) for row in orthotropic.solver["time_history"])


def test_orthotropic_large_scipy_matches_standard_solver(tmp_path: Path) -> None:
    analysis = {"type": "linear_static", "method": "direct"}
    model = _solid_model("TET4", _anisotropic_material(), analysis)
    large = from_finite_element_model(model)
    path = save_large_model(large, tmp_path / "orthotropic.npz")
    loaded = load_large_model(path)

    standard = solve_model(model)
    large_result = solve_large_model(loaded, tmp_path / "large", solver_backend="scipy")
    displacement = _large_displacement(tmp_path / "large")

    assert large_result.status == "PASS"
    assert large_result.audit.status == "PASS"
    assert loaded.materials["solid"]["type"] == "orthotropic_3d"
    assert np.allclose(displacement.ravel(), standard.displacements, rtol=1.0e-10, atol=1.0e-13)


def test_orthotropic_large_matrix_free_matches_assembled(tmp_path: Path) -> None:
    path = tmp_path / "block.npz"
    generated = generate_large_tet4_block(path, nx=1, ny=1, nz=1)
    orthotropic = replace(
        generated,
        materials={"steel": _anisotropic_material()},
    )
    scipy = solve_large_model(orthotropic, tmp_path / "scipy", solver_backend="scipy")
    matrix_free = solve_large_model(
        orthotropic,
        tmp_path / "matrix_free",
        solver_backend="matrix_free",
    )
    scipy_u = _large_displacement(tmp_path / "scipy")
    matrix_free_u = _large_displacement(tmp_path / "matrix_free")

    assert scipy.status == matrix_free.status == "PASS"
    assert np.allclose(matrix_free_u, scipy_u, rtol=1.0e-7, atol=1.0e-13)


def test_large_generator_preserves_orthotropic_material_metadata(tmp_path: Path) -> None:
    path = tmp_path / "orthotropic_block.npz"
    generated = generate_large_tet4_block(
        path,
        nx=1,
        ny=1,
        nz=1,
        material=_anisotropic_material(),
    )
    loaded = load_large_model(path)

    assert generated.materials["steel"] == _anisotropic_material()
    assert loaded.materials["steel"] == _anisotropic_material()


def test_orthotropic_large_postprocess_recovers_finite_stress(tmp_path: Path) -> None:
    generated_path = tmp_path / "generated.h5"
    generated = generate_large_tet4_block(generated_path, nx=1, ny=1, nz=1)
    orthotropic = replace(generated, materials={"steel": _anisotropic_material()})
    model_path = save_large_model(orthotropic, tmp_path / "orthotropic.h5")
    solve_large_model(orthotropic, tmp_path / "solve", solver_backend="scipy")

    summary = postprocess_large_model(
        model_path,
        tmp_path / "solve" / "displacements.h5",
        tmp_path / "post",
        chunk_size=2,
    )

    assert summary["status"] == "PASS"
    assert np.isfinite(summary["von_mises_max"])
    assert summary["strain_energy_sum"] > 0.0


def test_large_scope_still_rejects_nonlinear_material() -> None:
    model = _solid_model(
        "TET4",
        {"type": "nonlinear_isotropic_3d", "E": 1000.0, "nu": 0.25, "density": 10.0},
        {"type": "linear_static", "method": "direct"},
    )
    with pytest.raises(InputValidationError, match="invalid or unsupported"):
        from_finite_element_model(model)


def test_large_scope_rejects_elementwise_orientation_field() -> None:
    data = _anisotropic_material()
    data["orientation_field"] = {
        "type": "cylindrical_tangent",
        "origin": [0.0, 0.0, 0.0],
        "axis": [0.0, 0.0, 1.0],
    }
    from solveur.large.materials import create_large_material

    with pytest.raises(ValueError, match="does not yet support orientation_field"):
        create_large_material(data)


def _large_displacement(directory: Path) -> np.ndarray:
    hdf5 = directory / "displacements.h5"
    if hdf5.exists():
        import h5py

        with h5py.File(hdf5, "r") as handle:
            return np.asarray(handle["displacements"])
    return np.load(directory / "displacements.npz")["displacements"]
