"""Structural validation of Owner and external review records."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ALLOWED_DECISIONS = frozenset(
    {
        "accepted_with_recommendations",
        "accepted_for_bounded_engineering_use",
        "more_evidence_required",
    }
)
ALLOWED_PROMOTION_TARGETS = frozenset(
    {"stable", "owner_accepted", "experimental", "research"}
)


@dataclass(frozen=True)
class ReviewValidation:
    """Machine-readable result of one review-record validation."""

    status: str
    path: str
    review_id: str | None
    scopes: tuple[str, ...]
    decision: str | None
    promotion_target: str | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["scopes"] = list(self.scopes)
        result["errors"] = list(self.errors)
        result["warnings"] = list(self.warnings)
        return result


def validate_owner_review(
    path: str | Path,
    *,
    scope: str | None = None,
    require_decision: bool = False,
    target_maturity: str | None = None,
) -> ReviewValidation:
    """Validate a review file without changing it or the maturity matrix."""
    review_path = Path(path)
    try:
        payload = json.loads(review_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _failure(review_path, "review file does not exist")
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return _failure(review_path, f"review file cannot be read as JSON: {error}")

    if not isinstance(payload, dict):
        return _failure(review_path, "review record root must be a JSON object")

    errors: list[str] = []
    warnings: list[str] = []
    review_id = _optional_text(payload.get("review_id"))
    if not review_id:
        errors.append("review_id is required")
    scopes = _scopes(payload.get("scope"))
    if not scopes:
        errors.append("scope must contain at least one scope identifier")
    if scope is not None and scope not in scopes:
        errors.append(f"review does not cover requested scope {scope}")

    decision = _optional_text(payload.get("decision") or payload.get("owner_decision"))
    promotion_target = _optional_text(payload.get("promotion_target"))
    if target_maturity is not None and promotion_target != target_maturity:
        errors.append(
            f"promotion_target must be {target_maturity} for this validation request"
        )
    if promotion_target is not None and promotion_target not in ALLOWED_PROMOTION_TARGETS:
        errors.append(f"unsupported promotion_target: {promotion_target}")
    if promotion_target == "stable" and decision == "more_evidence_required":
        errors.append("promotion_target=stable is incompatible with more_evidence_required")
    signature = payload.get("signature")
    if decision is None:
        if require_decision:
            errors.append("a decision is required by this gate")
        if signature is not None:
            errors.append("signature must remain empty while decision is pending")
        status = "PENDING" if not errors else "FAIL"
    else:
        if decision not in ALLOWED_DECISIONS:
            errors.append(f"unsupported decision: {decision}")
        if not isinstance(signature, dict):
            errors.append("a signed decision requires a signature object")
        else:
            if not _optional_text(signature.get("name")) and not _optional_text(payload.get("reviewer")):
                errors.append("signature.name or reviewer is required for a decision")
            if not _optional_text(signature.get("date")) and not _optional_text(payload.get("review_date")):
                errors.append("signature.date or review_date is required for a decision")
        status = "PASS" if not errors else "FAIL"

    claim = _optional_text(payload.get("certification_claim"))
    if claim is not None and claim.lower() not in {"none", ""}:
        warnings.append("certification_claim is not none; this record must not be used as an external certification claim")
    if payload.get("review_mode") == "self_review":
        warnings.append("review_mode=self_review is not an independent external audit")

    return ReviewValidation(
        status=status,
        path=str(review_path),
        review_id=review_id,
        scopes=scopes,
        decision=decision,
        promotion_target=promotion_target,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _failure(path: Path, message: str) -> ReviewValidation:
    return ReviewValidation(
        status="FAIL",
        path=str(path),
        review_id=None,
        scopes=(),
        decision=None,
        promotion_target=None,
        errors=(message,),
        warnings=(),
    )


def _scopes(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,) if value.strip() else ()
    if isinstance(value, list):
        values = tuple(str(item).strip() for item in value if str(item).strip())
        return tuple(dict.fromkeys(values))
    return ()


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
