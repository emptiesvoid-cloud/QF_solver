"""Conservative, non-authoritative budget arithmetic: never reserves or writes a ledger."""
from __future__ import annotations

from dataclasses import dataclass
import math

MAX_ATTEMPTS = 24
MAX_SECONDS = 28_800
MAX_ATTEMPT_SECONDS = 1_200
MAX_RSS_MIB = 4_096
MAX_DOFS = 30_000


@dataclass(frozen=True)
class BudgetSnapshot:
    consumed_attempts: int
    consumed_seconds: float


def check_plan(snapshot: BudgetSnapshot, *, timeout_seconds: int, rss_mib: int, dofs: int) -> None:
    """Pure planning only. An official runner must lock and maintain its own immutable ledger."""
    if (isinstance(snapshot.consumed_attempts, bool) or not isinstance(snapshot.consumed_attempts, int)
            or snapshot.consumed_attempts < 0 or isinstance(snapshot.consumed_seconds, bool)
            or not isinstance(snapshot.consumed_seconds, (int, float)) or not math.isfinite(snapshot.consumed_seconds)
            or snapshot.consumed_seconds < 0):
        raise ValueError("invalid accounting snapshot")
    if any(isinstance(x, bool) or not isinstance(x, int) or x <= 0 for x in (timeout_seconds, rss_mib, dofs)):
        raise ValueError("invalid proposed budget")
    if (snapshot.consumed_attempts >= MAX_ATTEMPTS or timeout_seconds > MAX_ATTEMPT_SECONDS
            or rss_mib > MAX_RSS_MIB or dofs > MAX_DOFS
            or snapshot.consumed_seconds + timeout_seconds > MAX_SECONDS):
        raise ValueError("proposed attempt exceeds the global or per-case cap")
