"""Build a global, non-promoting readiness table for stable scopes."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LEGACY_AUDIT = ROOT / "results" / "maturity_promotion_0_2_1" / "maturity_promotion_audit.json"
OUTPUT = ROOT / "results" / "stable_promotion_readiness_0_2_1"


def _latest_audit() -> Path:
    """Select the newest immutable promotion audit, with a legacy fallback."""
    candidates = [
        path
        for path in (ROOT / "results").glob("maturity_promotion_final_*/maturity_promotion_audit.json")
        if re.fullmatch(r"maturity_promotion_final_\d{8}_v\d+", path.parent.name)
    ]
    if candidates:
        return max(candidates, key=_audit_sort_key)
    return LEGACY_AUDIT


def _audit_sort_key(path: Path) -> tuple[str, int]:
    """Order dated audit directories numerically instead of lexicographically."""
    match = re.fullmatch(r"maturity_promotion_final_(\d{8})_v(\d+)", path.parent.name)
    if match is None:
        raise ValueError(f"unexpected maturity audit directory: {path.parent.name}")
    return match.group(1), int(match.group(2))


def _error_candidates(row: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for criterion in row.get("criteria", []):
        for assertion in criterion.get("assertions", []):
            path = str(assertion.get("path", ""))
            actual = assertion.get("actual")
            if isinstance(actual, (int, float)) and any(
                token in path.lower() for token in ("error", "difference", "increment", "drift")
            ):
                candidates.append({"criterion": criterion.get("id"), "path": path, "actual": actual, "expected": assertion.get("expected")})
    return candidates


def main() -> int:
    audit_path = _latest_audit()
    report = json.loads(audit_path.read_text(encoding="utf-8"))
    rows = []
    for row in report["scopes"]:
        target_status = row.get("target_status")
        candidate = target_status == "stable"
        candidates = _error_candidates(row)
        rows.append({
            "scope": row["scope"],
            "current_status": row["current_status"],
            "target_status": target_status,
            "maturity_target": row.get("maturity_target", target_status),
            "stable_candidate": candidate,
            "technical_status": row.get("technical_status", row["criteria_status"]),
            "owner_decision": row.get("owner_decision", row["owner_review"]),
            "release_readiness": row.get("release_readiness", "NOT_READY"),
            "blocking_criteria": row["blocking_criteria"],
            "promotion_gate": row["promotion_gate"],
            "owner_review": row["owner_review"],
            "owner_promotion_target": row["owner_promotion_target"],
            "evidence_count": row["existing_evidence_count"],
            "relative_error_candidates": candidates,
            "stable_error_limit": 0.01,
            "stable_decision": "owner_review_required" if candidate else "not_yet_eligible",
        })
    payload = {
        "schema_version": 1,
        "report_id": "QF-STABLE-SCOPE-READINESS-021-001",
        "source_audit": str(audit_path.relative_to(ROOT)).replace("\\", "/"),
        "automatic_promotion": False,
        "stable_error_limit": 0.01,
        "scope_count": len(rows),
        "scopes": rows,
        "interpretation": "All audited scopes are listed. Relative-error candidates are audit indicators, not a substitute for mechanical classification of the observable. A scope cannot become stable until its target is stable, its Owner review has promotion_target=stable, and all primary observables are at most 1 percent or formally justified.",
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "stable_scope_readiness.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Readiness de promotion vers stable",
        "",
        "Ce tableau ne modifie aucune maturite et ne declenche aucune promotion.",
        "La limite d'erreur finale des observables principales est `1 %`.",
        "",
        "| Scope | Statut | Cible | Technique | Decision Owner | Readiness | Gate | Criteres bloquants | Indicateurs d'erreur |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        indicators = ", ".join(f"{item['path']}={item['actual']}" for item in row["relative_error_candidates"][:4]) or "a classifier"
        blockers = ", ".join(row["blocking_criteria"]) or "aucun"
        lines.append(f"| `{row['scope']}` | `{row['current_status']}` | `{row['maturity_target']}` | `{row['technical_status']}` | `{row['owner_decision']}` | `{row['release_readiness']}` | `{row['promotion_gate']}` | `{blockers}` | `{indicators}` |")
    lines.extend(["", "## Decision", "", "Tous les scopes audites restent visibles. Les lignes dont la cible technique est `stable` exigent une Owner review specifique avec `promotion_target: stable`; les autres doivent d'abord fermer leur preuve de domaine ou rester explicitement bornes. Les valeurs d'erreur candidates doivent etre confirmees comme observables principales et controlees hors singularite.", ""])
    (OUTPUT / "stable_scope_readiness.md").write_text("\n".join(lines), encoding="utf-8")
    print(OUTPUT / "stable_scope_readiness.json")
    print(OUTPUT / "stable_scope_readiness.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
