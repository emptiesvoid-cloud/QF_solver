"""Small fail-closed helpers for collective large-run control flow."""

from __future__ import annotations

from typing import Any


def rank_error_payload(rank: int, stage: str, error: BaseException | None) -> dict[str, Any] | None:
    """Serialize a local failure without requiring an MPI operation."""
    if error is None:
        return None
    return {
        "rank": int(rank),
        "stage": str(stage),
        "exception_type": type(error).__name__,
        "message": str(error),
    }


def raise_if_rank_failures(comm: Any, rank: int, stage: str, error: BaseException | None) -> None:
    """Make a locally observed failure visible to every rank before the next collective."""
    failures = [item for item in comm.allgather(rank_error_payload(rank, stage, error)) if item is not None]
    if not failures:
        return
    details = "; ".join(
        f"rank {item['rank']} {item['exception_type']}: {item['message']}" for item in failures
    )
    raise RuntimeError(f"Collective stage {stage} failed: {details}")


def require_global_readiness(comm: Any, rank: int, readiness: dict[str, Any]) -> list[dict[str, Any]]:
    """Require every rank to report the same frozen-route readiness boundary."""
    local = {"rank": int(rank), **readiness}
    rows = [dict(item) for item in comm.allgather(local)]
    rejected = [row for row in rows if not bool(row.get("pc_ready"))]
    if rejected:
        details = "; ".join(
            f"rank {row['rank']} matrix={row.get('matrix_type')} ksp={row.get('ksp_type')} pc={row.get('pc_type')}"
            for row in rejected
        )
        raise RuntimeError(f"Frozen readiness mismatch across MPI ranks: {details}")
    return rows
