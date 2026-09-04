"""Targeted WP15 contracts for the structured matrix-free TET4 route."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from scripts.benchmark_wp15_matrix_free import _relative_norm
from solveur.large.assembler import ChunkedScipyAssembler
from solveur.large.generator import generate_tet4_block
from solveur.large.matrix_free import StructuredBlockOperator


def _model(tmp_path: Path):
    return generate_tet4_block(
        tmp_path / "wp15_model.h5",
        nx=2,
        ny=2,
        nz=2,
        total_load=1.0e6,
        load_component=0,
        load_distribution="uniform",
        decomposition="six",
    )


def _operator(model) -> tuple[StructuredBlockOperator, np.ndarray]:
    fixed = np.unique(3 * model.fixed_nodes[:, None] + np.asarray(model.fixed_components))
    free = np.setdiff1d(np.arange(model.ndof, dtype=np.int64), fixed)
    return StructuredBlockOperator(model, free=free, chunk_size=4096), free


def test_matrix_free_workspace_matches_assembled_and_keeps_results_independent(tmp_path: Path) -> None:
    model = _model(tmp_path)
    operator, free = _operator(model)
    assembled = ChunkedScipyAssembler(chunk_size=4096).assemble(model).stiffness
    first = np.arange(free.size, dtype=float) + 1.0
    second = 2.0 * first
    first_result = operator @ first
    expected_first = (assembled @ np.bincount(free, weights=first, minlength=model.ndof))[free]
    assert _relative_norm(first_result, expected_first) <= 1.0e-12
    saved_first = first_result.copy()
    operator @ second
    assert np.array_equal(first_result, saved_first)


def test_matrix_free_operator_satisfies_empirical_spd_contract(tmp_path: Path) -> None:
    model = _model(tmp_path)
    operator, free = _operator(model)
    x = np.sin(np.arange(free.size, dtype=float) + 0.5)
    y = np.cos(np.arange(free.size, dtype=float) + 1.25)
    ax = operator @ x
    ay = operator @ y
    bilinear_scale = max(abs(float(x @ ay)), abs(float(y @ ax)), 1.0)
    assert abs(float(x @ ay - y @ ax)) / bilinear_scale <= 1.0e-12
    assert float(x @ ax) > 0.0
    assert float(y @ ay) > 0.0


def test_wp15_benchmark_records_frozen_wp14_contract() -> None:
    benchmark = Path("qualification/0_2_7/wp15_matrix_free_benchmark.json")
    assert benchmark.exists()
    document = __import__("json").loads(benchmark.read_text(encoding="utf-8"))
    assert document["baseline"]["parameters"]["chunk_size"] == 4096
    assert document["baseline"]["parameters"]["rtol"] == 1.0e-8
    assert document["baseline"]["parameters"]["atol"] == 0.0
    assert [item["ndof"] for item in document["baseline"]["levels"]] == [81, 375, 2187, 14739]
    assert document["comparison"]["levels"]
