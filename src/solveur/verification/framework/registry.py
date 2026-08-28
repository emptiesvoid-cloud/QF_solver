"""Deterministic case registry loading, selection and digesting."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .case import VnvCase, VnvCaseError


class VnvRegistry:
    """Validated authoritative registry of current and planned 0.2.6 cases."""

    def __init__(self, cases: Iterable[VnvCase], *, metadata: dict[str, Any] | None = None) -> None:
        ordered = tuple(sorted(cases, key=lambda case: case.case_id))
        ids = [case.case_id for case in ordered]
        if len(ids) != len(set(ids)):
            duplicates = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
            raise VnvCaseError(f"Duplicate V&V case ids: {', '.join(duplicates)}.")
        self._cases = ordered
        self.metadata = metadata or {}

    @classmethod
    def from_file(cls, path: str | Path) -> "VnvRegistry":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        raw_cases = data.get("cases")
        if not isinstance(raw_cases, list):
            raise VnvCaseError("V&V registry must define a cases list.")
        return cls((VnvCase.from_mapping(raw) for raw in raw_cases), metadata=data.get("metadata"))

    @property
    def cases(self) -> tuple[VnvCase, ...]:
        return self._cases

    @property
    def digest(self) -> str:
        payload = {"metadata": self.metadata, "cases": [case.to_mapping() for case in self._cases]}
        return _canonical_digest(payload)

    def select(
        self,
        *,
        case_ids: Iterable[str] = (),
        profile: str | None = None,
        tags: Iterable[str] = (),
        ready_only: bool = True,
    ) -> tuple[VnvCase, ...]:
        requested_ids = {item.upper() for item in case_ids}
        requested_tags = {item.lower() for item in tags}
        normalized_profile = profile.upper() if profile else None
        selected = []
        for case in self._cases:
            if requested_ids and case.case_id.upper() not in requested_ids:
                continue
            if normalized_profile and normalized_profile not in case.ci_profiles:
                continue
            if requested_tags and not requested_tags.intersection(tag.lower() for tag in case.tags):
                continue
            if ready_only and case.execution_state != "READY":
                continue
            selected.append(case)
        if requested_ids:
            missing = requested_ids.difference(case.case_id.upper() for case in selected)
            if missing:
                raise VnvCaseError(f"Unknown or non-executable V&V case ids: {', '.join(sorted(missing))}.")
        return tuple(selected)


def canonical_json(data: Any) -> str:
    """Serialize controlled metadata deterministically for its digest."""

    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _canonical_digest(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()
