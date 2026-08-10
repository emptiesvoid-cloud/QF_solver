import builtins
from pathlib import Path

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.core.errors import InfrastructureError, InputValidationError, NumericalConvergenceError
from solveur.core.linear_methods import LinearSystemSolver
from solveur.io.json_reader import JsonModelReader
from solveur.large.io import load_large_model
from solveur.large.solver import _petsc
from solveur.materials.solid import SolidMaterial, VonMisesElastoplasticMaterial
from solveur.post.stress import StressPostProcessor
from tests.helpers.models import tet10_nodes


@pytest.mark.parametrize(
    ("hardening", "strain"),
    [
        (1000.0, np.array([0.005, 0.0, 0.0, 0.0, 0.0, 0.0])),
        (1000.0, np.array([0.003, -0.001, 0.0, 0.004, 0.0, 0.002])),
        (0.0, np.array([0.005, 0.0, 0.0, 0.003, 0.0, 0.0])),
    ],
)
def test_j2_consistent_tangent_matches_finite_differences(hardening: float, strain: np.ndarray):
    material = VonMisesElastoplasticMaterial(
        E=210000.0,
        nu=0.3,
        yield_stress=250.0,
        hardening_modulus=hardening,
    )
    _, tangent, state = material.stress_tangent_state(strain, material.initial_state())
    finite_difference = _finite_difference_tangent(material, strain, material.initial_state())
    relative_error = np.linalg.norm(tangent - finite_difference) / np.linalg.norm(finite_difference)
    assert state["elastic"] is False
    assert relative_error < 1.0e-6
    assert np.allclose(tangent, tangent.T, rtol=1.0e-12, atol=1.0e-10)


def test_j2_consistent_tangent_uses_committed_previous_state():
    material = VonMisesElastoplasticMaterial(E=210000.0, nu=0.3, yield_stress=250.0, hardening_modulus=1000.0)
    _, _, committed = material.stress_tangent_state(
        np.array([0.004, 0.0, 0.0, 0.0, 0.0, 0.0]), material.initial_state()
    )
    strain = np.array([0.008, -0.001, 0.0, 0.002, 0.0, 0.0])
    _, tangent, state = material.stress_tangent_state(strain, committed)
    finite_difference = _finite_difference_tangent(material, strain, committed)
    relative_error = np.linalg.norm(tangent - finite_difference) / np.linalg.norm(finite_difference)
    assert state["elastic"] is False
    assert relative_error < 1.0e-6


def test_j2_loading_unloading_reloading_and_perfect_plasticity():
    material = VonMisesElastoplasticMaterial(E=1000.0, nu=0.25, yield_stress=5.0, hardening_modulus=100.0)
    _, _, loaded = material.stress_tangent_state(np.array([0.04, 0, 0, 0, 0, 0]), material.initial_state())
    _, _, unloaded = material.stress_tangent_state(np.array([0.039, 0, 0, 0, 0, 0]), loaded)
    _, _, reloaded = material.stress_tangent_state(np.array([0.08, 0, 0, 0, 0, 0]), unloaded)
    assert loaded["elastic"] is False
    assert unloaded["elastic"] is True
    assert unloaded["equivalent_plastic_strain"] == loaded["equivalent_plastic_strain"]
    assert reloaded["elastic"] is False
    assert reloaded["equivalent_plastic_strain"] > loaded["equivalent_plastic_strain"]

    perfect = VonMisesElastoplasticMaterial(E=1000.0, nu=0.25, yield_stress=5.0, hardening_modulus=0.0)
    _, _, perfect_state = perfect.stress_tangent_state(np.array([0.08, 0, 0, 0, 0, 0]), perfect.initial_state())
    assert perfect_state["yield_stress"] == pytest.approx(5.0)
    assert perfect_state["equivalent_stress"] == pytest.approx(5.0)


def test_tet10_post_processing_uses_committed_integration_states():
    material = SolidMaterial(E=1000.0, nu=0.25)
    states = [
        {
            "model": "test_path_material",
            "stress": [10.0 * (index + 1), 0.0, 0.0, 0.0, 0.0, 0.0],
            "equivalent_plastic_strain": 0.01 * (index + 1),
            "plastic_multiplier": 0.001 * (index + 1),
            "yield_function": 0.0,
            "yield_stress": 5.0,
            "plastic_strain": [0.0] * 6,
        }
        for index in range(4)
    ]
    result = StressPostProcessor._tet10_result(
        0,
        "TET10",
        tuple(range(10)),
        material,
        np.asarray(tet10_nodes(), dtype=float),
        np.zeros(30),
        states,
    )
    assert result["location"] == "integration_average"
    assert result["material_state"]["source"] == "committed_integration_point_average"
    assert result["stress"][0] == pytest.approx(25.0)
    assert result["equivalent_plastic_strain"] == pytest.approx(0.025)


def test_direct_sparse_solve_rejects_singular_matrix():
    with pytest.raises(NumericalConvergenceError, match="singular"):
        LinearSystemSolver().solve(csr_matrix((2, 2)), np.array([1.0, 0.0]), method="direct")


@pytest.mark.parametrize(
    "analysis",
    [
        {
            "type": "transient_dynamic",
            "method": "newmark",
            "time_step": 0.01,
            "steps": 2,
            "newmark_beta": 0.1,
            "newmark_gamma": 0.5,
        },
        {
            "type": "transient_dynamic",
            "method": "newmark",
            "time_step": 0.01,
            "steps": 2,
            "rayleigh_alpha": -0.1,
        },
        {
            "type": "transient_dynamic",
            "method": "newmark",
            "time_step": 0.01,
            "steps": 2,
            "load_table": [{"time": 1.0, "factor": 1.0}, {"time": 0.5, "factor": 0.5}],
        },
    ],
)
def test_json_rejects_unsafe_dynamic_parameters(analysis: dict[str, object]):
    with pytest.raises(InputValidationError):
        JsonModelReader().from_dict(_model_data(analysis=analysis, density=1.0))


def test_qualification_profile_rejects_non_si_units():
    data = _model_data()
    data["verification_profile"] = "qualification"
    data["units"] = {"system": "custom", "length": "mm", "force": "N"}
    with pytest.raises(InputValidationError, match="only the SI"):
        JsonModelReader().from_dict(data)


def test_corrupted_hdf5_is_reported_as_input_error(tmp_path: Path):
    path = tmp_path / "corrupted.h5"
    path.write_bytes(b"not-an-hdf5-file")
    with pytest.raises(InputValidationError, match="corrupted HDF5"):
        load_large_model(path)


def test_missing_petsc_dependency_is_infrastructure_error(monkeypatch: pytest.MonkeyPatch):
    real_import = builtins.__import__

    def blocked_import(name: str, *args: object, **kwargs: object):
        if name == "petsc4py":
            raise ImportError("simulated missing dependency")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    with pytest.raises(InfrastructureError, match="petsc4py"):
        _petsc()


def _finite_difference_tangent(
    material: VonMisesElastoplasticMaterial,
    strain: np.ndarray,
    state: dict[str, object],
) -> np.ndarray:
    step = 1.0e-7 * max(float(np.linalg.norm(strain)), 1.0)
    tangent = np.zeros((6, 6), dtype=float)
    for column in range(6):
        increment = np.zeros(6, dtype=float)
        increment[column] = step
        plus, _, _ = material.stress_tangent_state(strain + increment, state)
        minus, _, _ = material.stress_tangent_state(strain - increment, state)
        tangent[:, column] = (plus - minus) / (2.0 * step)
    return tangent


def _model_data(*, analysis: object = "linear_static", density: float | None = None) -> dict[str, object]:
    material: dict[str, object] = {"type": "isotropic_3d", "E": 1000.0, "nu": 0.25}
    if density is not None:
        material["density"] = density
    return {
        "analysis": analysis,
        "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        "materials": {"steel": material},
    }
