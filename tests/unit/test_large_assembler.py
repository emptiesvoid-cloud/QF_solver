import numpy as np
from scipy.sparse import coo_matrix

from solveur.elements.solid.tet4 import Tet4Element
from solveur.large.assembler import ChunkedScipyAssembler
from solveur.large.generator import generate_tet4_block
from solveur.large.materials import create_large_material


def test_large_scipy_assembly_reports_pairwise_accumulation(tmp_path) -> None:
    model = generate_tet4_block(tmp_path / "model.npz", nx=2, ny=1, nz=1)
    assembly = ChunkedScipyAssembler(chunk_size=2).assemble(model)

    assert assembly.stiffness.shape == (model.ndof, model.ndof)
    assert np.all(np.isfinite(assembly.stiffness.data))
    assert assembly.diagnostics is not None
    assert assembly.diagnostics["chunk_count"] == 6
    assert assembly.diagnostics["final_nnz"] == assembly.stiffness.nnz
    assert assembly.diagnostics["accumulator_occupied_levels"] >= 1
    assert assembly.diagnostics["sparse_memory_bytes"] > 0
    assert assembly.diagnostics["material_cache_reused"] is True
    assert assembly.diagnostics["sparse_conversion_method"] == "csr_constructor"
    phases = assembly.diagnostics["assembly_phase_seconds"]
    assert all(float(phases[name]) >= 0.0 for name in phases)
    assert phases["chunk_build"] == phases["element_kernel"] + phases["chunk_sparse_conversion"]


def test_centered_tet4_assembly_matches_element_reference(tmp_path) -> None:
    model = generate_tet4_block(
        tmp_path / "centered.npz",
        nx=1,
        ny=1,
        nz=1,
        decomposition="centered",
        material={"type": "isotropic_3d", "E": 70.0e9, "nu": 0.27, "density": 2700.0},
    )
    assembled = ChunkedScipyAssembler(chunk_size=3).assemble(model).stiffness
    material = Tet4Element(create_large_material(model.materials["steel"]))
    rows: list[int] = []
    cols: list[int] = []
    values: list[float] = []
    for nodes in model.tet4:
        local = material.stiffness(model.nodes[nodes])
        dofs = (3 * nodes[:, None] + np.arange(3, dtype=np.int64)).reshape(-1)
        rows.extend(np.repeat(dofs, 12).tolist())
        cols.extend(np.tile(dofs, 12).tolist())
        values.extend(local.reshape(-1).tolist())
    reference = coo_matrix((values, (rows, cols)), shape=assembled.shape).tocsr()
    reference.sum_duplicates()
    reference.eliminate_zeros()

    np.testing.assert_allclose(assembled.toarray(), reference.toarray(), rtol=1.0e-12, atol=1.0e-5)
    assert assembled.nnz == reference.nnz
