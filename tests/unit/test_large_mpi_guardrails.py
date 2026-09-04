from __future__ import annotations

import pytest

from solveur.large.mpi_guardrails import raise_if_rank_failures, require_global_readiness


class RecordingComm:
    def __init__(self, responses: list[list[object]]) -> None:
        self.responses = list(responses)
        self.calls: list[object] = []

    def allgather(self, value: object) -> list[object]:
        self.calls.append(value)
        return self.responses.pop(0)


def test_rank_failure_is_raised_consistently_before_the_next_collective() -> None:
    comm = RecordingComm([[None, {"rank": 1, "stage": "PCSETUP", "exception_type": "RuntimeError", "message": "bad pc"}]])

    with pytest.raises(RuntimeError, match="rank 1 RuntimeError: bad pc"):
        raise_if_rank_failures(comm, 0, "PCSETUP", None)

    assert comm.calls == [None]


def test_global_readiness_requires_every_rank_to_confirm_the_frozen_route() -> None:
    comm = RecordingComm(
        [
            [
                {"rank": 0, "pc_ready": True, "matrix_type": "mpiaij", "ksp_type": "cg", "pc_type": "gamg"},
                {"rank": 1, "pc_ready": False, "matrix_type": "mpiaij", "ksp_type": "cg", "pc_type": "none"},
            ]
        ]
    )

    with pytest.raises(RuntimeError, match="rank 1 matrix=mpiaij ksp=cg pc=none"):
        require_global_readiness(
            comm,
            0,
            {"pc_ready": True, "matrix_type": "mpiaij", "ksp_type": "cg", "pc_type": "gamg"},
        )


def test_global_readiness_returns_all_rank_rows_when_the_route_is_consistent() -> None:
    rows = [
        {"rank": 0, "pc_ready": True, "matrix_type": "mpiaij", "ksp_type": "cg", "pc_type": "gamg"},
        {"rank": 1, "pc_ready": True, "matrix_type": "mpiaij", "ksp_type": "cg", "pc_type": "gamg"},
    ]
    comm = RecordingComm([rows])

    assert require_global_readiness(
        comm,
        0,
        {"pc_ready": True, "matrix_type": "mpiaij", "ksp_type": "cg", "pc_type": "gamg"},
    ) == rows
