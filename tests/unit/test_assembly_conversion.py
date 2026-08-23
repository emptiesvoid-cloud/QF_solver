from __future__ import annotations

import pytest

from scripts.benchmark_assembly_conversion import run_conversion_probe


def test_conversion_probe_preserves_sparse_matrix_identity(tmp_path) -> None:
    report = run_conversion_probe(1000, chunk_size=64, repeats=1, output=tmp_path / "probe.json")

    assert report["variants"]
    assert all(row["difference_nnz"] == 0 for row in report["variants"])
    assert all(row["max_abs_difference"] == 0.0 for row in report["variants"])
    assert (tmp_path / "probe.json").is_file()


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"target_dofs": 1}, "target_dofs"),
        ({"chunk_size": 0}, "chunk_size"),
        ({"repeats": 0}, "repeats"),
    ],
)
def test_conversion_probe_rejects_invalid_configuration(kwargs, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        run_conversion_probe(**kwargs)
