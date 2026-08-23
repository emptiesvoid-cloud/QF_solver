from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from solveur.core.errors import InfrastructureError
from solveur.large.assembler import (
    ChunkedScipyAssembler,
    _is_distributed_model,
    _material_cache,
    _petsc,
    _stiffness_batch,
    apply_homogeneous_element_constraints,
    assemble_loads,
    element_dofs,
    fixed_dof_indices,
)
from solveur.large.generator import generate_tet4_block
from solveur.large.optimization import (
    _accepted,
    _binary_metadata,
    _preconditioner_record,
    _scaling_record,
    _validate_scaling_records,
)


def test_large_assembly_helpers_cover_empty_and_multiple_load_paths(tmp_path: Path) -> None:
    model = generate_tet4_block(tmp_path / "model.npz", nx=1, ny=1, nz=1, total_load=12.0)

    loads = assemble_loads(model)
    assert loads.shape == (model.ndof,)
    assert np.isclose(loads.sum(), 12.0)
    fixed = fixed_dof_indices(model)
    assert fixed.size > 0
    assert np.array_equal(element_dofs(np.array([0, 1, 2, 3], dtype=np.int64)), np.arange(12))

    model.fixed_nodes = np.zeros(0, dtype=np.int64)
    model.fixed_components = np.zeros(0, dtype=np.int8)
    assert fixed_dof_indices(model).size == 0
    assert np.count_nonzero(assemble_loads(model)) > 0


def test_large_assembly_material_cache_and_chunk_kernel_are_reusable(tmp_path: Path) -> None:
    model = generate_tet4_block(tmp_path / "model.npz", nx=1, ny=1, nz=1)
    materials = _material_cache(model)
    stiffness = _stiffness_batch(model, 0, model.element_count, materials)
    chunk, kernel_time, conversion_time = ChunkedScipyAssembler._chunk_matrix(
        model, 0, model.element_count, materials
    )

    assert set(materials) == {0}
    assert stiffness.shape == (model.element_count, 12, 12)
    assert chunk.shape == (model.ndof, model.ndof)
    assert kernel_time >= 0.0
    assert conversion_time >= 0.0
    assert _is_distributed_model(model) is False
    assert _is_distributed_model(type("Distributed", (), {"global_tet4": None, "local_element_count": 0})())


def test_homogeneous_constraint_helper_returns_source_when_unconstrained() -> None:
    source = np.eye(12)
    dofs = np.arange(12, dtype=np.int64)

    result = apply_homogeneous_element_constraints(source, dofs, set())

    assert result is source
    assert np.array_equal(result, source)


def test_petsc_dependency_failure_is_explicit_when_unavailable() -> None:
    try:
        import petsc4py  # noqa: F401
    except ImportError:
        with pytest.raises(InfrastructureError, match="petsc4py"):
            _petsc()
    else:
        assert _petsc() is not None


def test_scaling_metadata_and_preconditioner_records_are_normalized(tmp_path: Path) -> None:
    displacement = tmp_path / "displacements.bin"
    np.zeros(6, dtype=np.float64).tofile(displacement)
    metadata_path = tmp_path / "displacements_metadata.json"
    metadata_path.write_text(
        json.dumps({"dtype": "float64", "flat_size": 6, "shape": [2, 3], "byte_order": "little"}),
        encoding="utf-8",
    )
    assert _binary_metadata(displacement)["flat_size"] == 6

    result = {
        "status": "PASS",
        "evidence_verification": {"status": "PASS"},
        "ndof": 12,
        "mpi": {"size": 2},
        "solve_pipeline_time_seconds": 1.5,
        "assembly_time_seconds": 0.4,
        "solver": {"iterations": 7, "residual_norm": 1.0e-10, "setup_time_seconds": 0.2},
        "memory_telemetry": {"process_peak_rss_bytes": 1024},
    }
    record = _preconditioner_record("gamg", result)
    assert record["preconditioner"] == "gamg"
    assert record["ranks"] == 2
    assert _accepted({**record, "relative_displacement_error": 1.0e-9}, 1.0e-8)
    assert not _accepted({**record, "relative_displacement_error": None}, 1.0e-8)

    benchmark = tmp_path / "benchmark.json"
    benchmark.write_text(
        json.dumps(
            {
                "ndof": 12,
                "element_count": 3,
                "solve_pipeline_time_seconds": 1.5,
                "assembly_time_seconds": 0.4,
                "solve_time_seconds": 1.0,
                "solver": {"iterations": 7, "residual_norm": 1.0e-10},
                "memory_telemetry": {"rank_count": 2, "process_peak_rss_bytes": 1024},
            }
        ),
        encoding="utf-8",
    )
    scaling = _scaling_record(benchmark)
    assert scaling["ranks"] == 2
    assert scaling["dofs_per_rank"] == 6.0


def test_scaling_record_validation_rejects_duplicate_ranks_and_strong_size_mismatch() -> None:
    records = [
        {"ranks": 1, "dofs": 100, "dofs_per_rank": 100.0},
        {"ranks": 1, "dofs": 100, "dofs_per_rank": 100.0},
    ]
    with pytest.raises(ValueError, match="distinct MPI"):
        _validate_scaling_records(records, "strong", 0.1)

    records[1] = {"ranks": 2, "dofs": 200, "dofs_per_rank": 100.0}
    _validate_scaling_records(records, "weak", 0.1)
    with pytest.raises(ValueError, match="same dof"):
        _validate_scaling_records(
            [{"ranks": 1, "dofs": 100, "dofs_per_rank": 100.0}, {"ranks": 2, "dofs": 200, "dofs_per_rank": 100.0}],
            "strong",
            0.1,
        )
