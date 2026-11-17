from __future__ import annotations

import json

import numpy as np
import pytest

from research.j16.harmonic_mesh_study import (
    _frequency_checkpoint,
    _load_resultant,
    _quadratic_peak,
    _sparse_backward_error_eta_inf,
)
from scipy.sparse import csr_matrix


class _TwoNodeModel:
    node_count = 2


class _SixDofMap:
    _components = {"UX": 0, "UY": 1, "UZ": 2}

    def has(self, node: int, component: str) -> bool:
        return node in (0, 1) and component in self._components

    def index(self, node: int, component: str) -> int:
        return 3 * node + self._components[component]


def test_quadratic_peak_recovers_vertex_of_log_parabolic_samples() -> None:
    frequencies = np.arange(5.0)
    amplitudes = np.exp(-0.5 * (frequencies - 2.2) ** 2)

    result = _quadratic_peak(frequencies, amplitudes, 2)

    assert result["frequency_hz"] == pytest.approx(2.2)
    assert result["amplitude_mm"] == pytest.approx(1.0)


def test_sparse_backward_error_uses_sparse_infinity_norms() -> None:
    matrix = csr_matrix([[3.0, 1.0], [0.0, 2.0]])
    rhs = np.asarray([4.5, 4.0])
    solution = np.asarray([1.0, 2.0])
    residual = matrix @ solution - rhs

    assert _sparse_backward_error_eta_inf(matrix, rhs, solution, residual) == pytest.approx(0.04)


def test_load_resultant_reports_assembled_and_direct_sums() -> None:
    loads = np.asarray([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    diagnostics = {"resultant": [5.0, 7.0, 9.0], "moment_about_origin": [0.0, 0.0, 0.0]}

    result = _load_resultant(_TwoNodeModel(), _SixDofMap(), loads, diagnostics)

    assert result["assembler_load_balance_resultant_n"] == [5.0, 7.0, 9.0]
    assert result["direct_sum_of_nodal_translational_load_dofs_n"] == [5.0, 7.0, 9.0]
    assert result["direct_minus_assembler_resultant_n"] == [0.0, 0.0, 0.0]
    assert result["direct_minus_analytic_expected_force_n"] == [5.0, 7.0, 10009.0]


def test_frequency_checkpoint_keeps_pending_then_rejected_status_and_uses_supplied_scale(tmp_path) -> None:
    reduced = np.asarray([1.0 + 2.0j, 3.0 + 4.0j])
    full = np.asarray([2.0 + 3.0j, 4.0 + 5.0j])
    metrics = {
        "raw_reduced_residual_l2": 1.0e-12,
        "raw_reduced_relative_residual_l2": 1.0e-10,
        "raw_reduced_backward_error_eta_inf": 1.0e-15,
    }

    pending = _frequency_checkpoint(
        tmp_path, 8, 2.375, "QF_ROUTE_PENDING", {"phase": "pre-route"}, reduced, full,
        metrics, 3.0 + 4.0j, 2.0 + 3.0j, None, True, 0.01,
    )
    key = "frequency_2p375000000"
    assert pending["qf_route_status"] == "QF_ROUTE_PENDING"
    assert pending["complex_error_normalized_by_reference_band_peak"] == pytest.approx(np.sqrt(2.0) / 0.01)

    completed = _frequency_checkpoint(
        tmp_path, 8, 2.375, "QF_GUARD_REJECTED", {"upper_bound": 2.0e-7}, reduced, full,
        metrics, 3.0 + 4.0j, 2.0 + 3.0j, None, True, 0.01,
    )
    assert completed["qf_route_status"] == "QF_GUARD_REJECTED"
    saved = json.loads((tmp_path / f"mesh_08_{key}.json").read_text(encoding="utf-8"))
    assert saved["qf_route_status"] == "QF_GUARD_REJECTED"
    assert saved["raw_solution_status"] == "RAW_UNGUARDED_QF_ASSEMBLED_SYSTEM_SPSOLVE"
    with np.load(tmp_path / f"mesh_08_{key}.npz") as archive:
        assert {"raw_reduced_real", "raw_reduced_imag", "raw_full_real", "raw_full_imag"}.issubset(archive.files)
        assert "qf_center_uz_real" in archive.files
        assert np.all(np.isfinite(archive["raw_reduced_real"]))
