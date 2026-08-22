"""Release checks for controlled evidence bundles."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from solveur.io.evidence_verifier import EvidenceBundleVerifier
from solveur.paths import project_root


def controlled_evidence_checks(
    registry: dict[str, Any],
    root: Path | None = None,
) -> list[dict[str, Any]]:
    """Verify the integrity of evidence bundles declared by a release registry.

    The check deliberately validates bundle integrity only. Mechanical verdicts,
    maturity and Owner decisions remain separate release checks.
    """
    base = (root or project_root()).resolve()
    entries = registry.get("evidence_bundles", [])
    if not isinstance(entries, list) or not entries:
        return [
            {
                "id": "EVIDENCE-BUNDLE-REGISTRY",
                "status": "FAIL",
                "detail": "no controlled evidence bundle is declared in the release registry",
            }
        ]

    checks: list[dict[str, Any]] = []
    verifier = EvidenceBundleVerifier()
    for raw in entries:
        if not isinstance(raw, dict) or not raw.get("id") or not raw.get("path"):
            checks.append(
                {
                    "id": "EVIDENCE-BUNDLE-REGISTRY",
                    "status": "FAIL",
                    "detail": "each evidence bundle requires id and path",
                }
            )
            continue
        bundle_id = str(raw["id"])
        required = bool(raw.get("required", False))
        bundle = Path(str(raw["path"]))
        if not bundle.is_absolute():
            bundle = base / bundle
        report = verifier.verify(bundle)
        status = report.status
        if status != "PASS" and not required:
            status = "WARNING"
        detail = (
            f"bundle={_relative(bundle, base)}, integrity={report.status}, "
            f"checked_files={report.checked_file_count}, errors={len(report.errors)}"
        )
        checks.append(
            {
                "id": f"EVIDENCE-BUNDLE-{bundle_id.upper().replace('_', '-')}",
                "status": status,
                "detail": detail,
                "required": required,
                "path": _relative(bundle, base),
                "manifest_status": report.status,
                "checked_file_count": report.checked_file_count,
                "error_count": len(report.errors),
            }
        )
    return checks


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.name
