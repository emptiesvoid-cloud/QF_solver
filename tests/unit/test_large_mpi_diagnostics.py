from __future__ import annotations

from solveur.large.mpi_diagnostics import communication_diagnostics, petsc_ksp_diagnostics


class FakePC:
    def getType(self):
        return "gamg"

    def getMGLevels(self):
        return 4


class FakeKSP:
    def __init__(self) -> None:
        self.pc = FakePC()

    def getType(self):
        return "cg"

    def getPC(self):
        return self.pc


class FakeMatrix:
    def getSize(self):
        return (100, 100)

    def getLocalSize(self):
        return (25, 100)

    def getOwnershipRange(self):
        return (25, 50)

    def getInfo(self):
        return {"nz_used": 1234.0, "memory": 4096.0}


def test_communication_diagnostics_estimates_halo_and_boundary_payloads() -> None:
    diagnostics = communication_diagnostics(
        node_counts=[10, 12],
        owned_node_counts=[8, 9],
        halo_node_counts=[2, 3],
        fixed_counts=[4, 1],
        load_counts=[0, 5],
        partition_details={"cut_face_count": 7, "cut_face_ratio": 0.25},
    )

    assert diagnostics["max_halo_node_count"] == 3
    assert diagnostics["halo_node_ratio_max"] == 0.25
    assert diagnostics["estimated_halo_coordinate_bytes_by_rank"] == [48, 72]
    assert diagnostics["estimated_boundary_payload_bytes_total"] == 5 * 9 + 5 * 17
    assert diagnostics["graph_cut_face_count"] == 7


def test_petsc_ksp_diagnostics_collects_available_fields() -> None:
    diagnostics = petsc_ksp_diagnostics(FakeKSP(), FakeMatrix())

    assert diagnostics["ksp_type"] == "cg"
    assert diagnostics["pc_type"] == "gamg"
    assert diagnostics["pc_mg_levels"] == 4
    assert diagnostics["matrix_global_size"] == [100, 100]
    assert diagnostics["matrix_local_size"] == [25, 100]
    assert diagnostics["matrix_ownership_range"] == [25, 50]
    assert diagnostics["matrix_info"]["nz_used"] == 1234.0
