"""Release-level verification and validation readiness for QF_solver.

The release pack deliberately separates numerical evidence from publication
readiness. A scope can therefore have passing calculations while remaining a
warning when its controlled evidence corpus or owner review is not present in
the public checkout.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from solveur.core.errors import InputValidationError
from solveur.io.manifest import (
    git_source_state,
    locked_environment_fingerprints,
    manifest_file_entry,
    runtime_fingerprint,
    sha256,
    utc_timestamp,
    write_json_file,
)
from solveur.paths import project_path, project_root
from solveur.verification.campaign import QualificationCampaignRunner
from solveur.verification.evidence_readiness import controlled_evidence_checks
from solveur.verification.traceability import qualification_readiness
from solveur.version import DISPLAY_NAME, __version__


DEFAULT_RELEASE_REGISTRY = project_path("qualification/release_vv_0_2_1.json")


class ReleaseVvRunner:
    """Build a reproducible V&V readiness package for one alpha release."""

    def __init__(self, registry_path: str | Path = DEFAULT_RELEASE_REGISTRY) -> None:
        self.registry_path = Path(registry_path)

    def run(
        self,
        output_dir: str | Path,
        *,
        execute_campaign: bool = False,
        campaign_manifest: str | Path | None = None,
    ) -> dict[str, Any]:
        """Evaluate the controlled release registry and write its artifacts."""
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
        registry = self._load_registry()
        root = project_root()
        checks: list[dict[str, Any]] = []
        checks.append(self._release_version_check(registry))
        checks.extend(self._baseline_checks(registry, root))
        checks.extend(controlled_evidence_checks(registry, root))
        scope_rows = self._scope_rows(registry)
        checks.extend(
            {
                "id": f"SCOPE-{row['id']}",
                "status": row["status"],
                "detail": row["detail"],
            }
            for row in scope_rows
        )

        campaign = self._campaign_record(
            registry,
            output,
            execute_campaign=execute_campaign,
            campaign_manifest=campaign_manifest,
        )
        checks.append(
            {
                "id": "CAMPAIGN-EXECUTION",
                "status": campaign["readiness_status"],
                "detail": campaign["detail"],
            }
        )
        owner_review = self._owner_review_record(registry)
        checks.append(
            {
                "id": "OWNER-REVIEW",
                "status": owner_review["status"],
                "detail": owner_review["detail"],
            }
        )

        source = git_source_state(root)
        if source["dirty"]:
            checks.append(
                {
                    "id": "SOURCE-CLEAN",
                    "status": "FAIL",
                    "detail": "source checkout is dirty; commit the release before tagging it",
                }
            )
        else:
            checks.append({"id": "SOURCE-CLEAN", "status": "PASS", "detail": "source checkout is clean"})

        status = self._global_status(checks)
        summary = self._summary(
            registry,
            root,
            status=status,
            checks=checks,
            scope_rows=scope_rows,
            campaign=campaign,
            owner_review=owner_review,
            source=source,
        )
        summary["manifest"] = "release_vv_manifest.json"
        summary_path = output / "release_vv_summary.json"
        markdown_path = output / "release_vv_summary.md"
        write_json_file(summary_path, summary)
        markdown_path.write_text(self._render_markdown(summary), encoding="utf-8")
        self._write_manifest(output, registry, summary_path, markdown_path)
        return summary

    def _load_registry(self) -> dict[str, Any]:
        try:
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InputValidationError(f"Cannot load release V&V registry {self.registry_path}: {exc}") from exc
        if not isinstance(data, dict) or int(data.get("schema_version", 0)) != 1:
            raise InputValidationError("Release V&V registry schema_version must be 1.")
        release = data.get("release")
        baseline = data.get("baseline")
        scopes = data.get("scopes")
        if not isinstance(release, dict) or not isinstance(baseline, dict) or not isinstance(scopes, list):
            raise InputValidationError("Release V&V registry requires release, baseline and scopes.")
        if not release.get("version") or not baseline.get("tag") or not baseline.get("commit"):
            raise InputValidationError("Release V&V registry has incomplete release or baseline identity.")
        if not scopes:
            raise InputValidationError("Release V&V registry must define at least one scope.")
        return data

    @staticmethod
    def _release_version_check(registry: dict[str, Any]) -> dict[str, Any]:
        expected = str(registry["release"].get("version"))
        status = "PASS" if expected == __version__ else "FAIL"
        detail = f"registry={expected}, runtime={__version__}"
        return {"id": "RELEASE-VERSION", "status": status, "detail": detail}

    @staticmethod
    def _baseline_checks(registry: dict[str, Any], root: Path) -> list[dict[str, Any]]:
        baseline = registry["baseline"]
        expected_commit = str(baseline["commit"])
        expected_tag = str(baseline["tag"])
        tag_commit = _git_output(root, "rev-parse", f"{expected_tag}^{{commit}}")
        commit_status = "PASS" if tag_commit == expected_commit else "FAIL"
        tag_detail = f"tag={expected_tag}, resolved={tag_commit or 'missing'}, expected={expected_commit}"
        return [
            {"id": "BASELINE-TAG", "status": commit_status, "detail": tag_detail},
            {
                "id": "BASELINE-VERSION",
                "status": "PASS" if str(baseline.get("version")) == "0.2.0a0" else "FAIL",
                "detail": f"baseline version={baseline.get('version')}",
            },
        ]

    def _scope_rows(self, registry: dict[str, Any]) -> list[dict[str, Any]]:
        matrix = self._load_element_analysis_matrix()
        raw_scopes = [dict(item) for item in registry["scopes"] if isinstance(item, dict)]
        matrix_policy = registry.get("policy", {}).get("matrix_scope_policy", {})
        excluded_statuses = {
            str(value) for value in matrix_policy.get("exclude_statuses", ["unsupported"])
        }
        if bool(matrix_policy.get("include_all", False)):
            known = {str(item.get("id")) for item in raw_scopes}
            for scope_id, row in matrix.items():
                if str(row.get("status", "")) in excluded_statuses:
                    continue
                if scope_id in known:
                    continue
                raw_scopes.append(
                    {
                        "id": scope_id,
                        "required": True,
                        "role": "matrix_scope",
                        "declared_status": row.get("status", "development"),
                        "target_status": str(matrix_policy.get("target_status", "stable")),
                        "proof_requirements": dict(matrix_policy.get("proof_requirements", {})),
                    }
                )
        matrix_scope_ids = set(matrix)
        rows: list[dict[str, Any]] = []
        seen_scope_ids: set[str] = set()
        for raw in raw_scopes:
            if not isinstance(raw, dict) or not raw.get("id"):
                raise InputValidationError("Each release V&V scope must define an id.")
            scope_id = str(raw["id"])
            if (
                scope_id not in matrix_scope_ids
                and bool(matrix_policy.get("include_all", False))
                and not bool(raw.get("required", False))
            ):
                continue
            if scope_id in seen_scope_ids:
                continue
            seen_scope_ids.add(scope_id)
            matrix_row = matrix.get(scope_id)
            matrix_status = str(matrix_row.get("status", "")) if matrix_row else ""
            required = bool(raw.get("required", False)) or (
                bool(matrix_policy.get("include_all", False))
                and matrix_status not in excluded_statuses
            )
            try:
                readiness = qualification_readiness(scope_id)
            except InputValidationError as exc:
                # A matrix row without a requirements registry entry is a
                # release failure, not a runner crash.
                readiness = SimpleNamespace(
                    status="FAIL",
                    missing_paths=(),
                    missing_independent_references=(),
                    orphan_requirements=(str(exc),),
                    orphan_formulas=(),
                    requirement_count=0,
                    covered_requirement_count=0,
                    formula_count=0,
                    covered_formula_count=0,
                )
            proof = self._proof_record(
                raw,
                matrix_row,
                readiness,
                dict(matrix_policy.get("proof_requirements", {})),
            )
            blockers = list(proof["blockers"])
            blocker_categories = list(proof["blocker_categories"])
            if readiness.status != "PASS":
                readiness_detail, readiness_categories = self._readiness_detail(readiness)
                blockers.append(readiness_detail)
                blocker_categories.extend(readiness_categories)
            if blockers:
                status = "FAIL" if required else "WARNING"
                detail = "; ".join(blockers)
            else:
                status = "PASS"
                detail = "stable matrix row and complete traceability evidence"
            rows.append(
                {
                    "id": scope_id,
                    "required": required,
                    "role": str(raw.get("role", "candidate")),
                    "declared_status": str(raw.get("declared_status", "candidate")),
                    "readiness_status": readiness.status,
                    "status": status,
                    "detail": detail,
                    "requirement_count": readiness.requirement_count,
                    "covered_requirement_count": readiness.covered_requirement_count,
                    "formula_count": readiness.formula_count,
                    "covered_formula_count": readiness.covered_formula_count,
                    "missing_paths": list(readiness.missing_paths),
                    "missing_independent_references": list(readiness.missing_independent_references),
                    "orphan_requirements": list(readiness.orphan_requirements),
                    "orphan_formulas": list(readiness.orphan_formulas),
                    "matrix_status": proof["matrix_status"],
                    "target_status": proof["target_status"],
                    "proof": proof,
                    "blocker_categories": sorted(set(blocker_categories)),
                }
            )
        return rows

    @staticmethod
    def _load_element_analysis_matrix() -> dict[str, dict[str, Any]]:
        path = project_path("qualification/element_analysis_matrix.json")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InputValidationError(f"Cannot load element-analysis matrix {path}: {exc}") from exc
        coverage_path = project_path("qualification/technical_content_coverage.json")
        pair_evidence: dict[tuple[str, str], list[str]] = {}
        try:
            coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            coverage = {}
        for pair in coverage.get("element_analysis_pairs", []) if isinstance(coverage, dict) else []:
            if not isinstance(pair, dict):
                continue
            oracle = pair.get("oracle", {})
            evidence = oracle.get("evidence", []) if isinstance(oracle, dict) else []
            key = (str(pair.get("family", "")), str(pair.get("analysis", "")))
            pair_evidence[key] = [str(item) for item in evidence if item]

        rows: dict[str, dict[str, Any]] = {}
        for family, analyses in data.get("families", {}).items():
            if not isinstance(analyses, dict):
                continue
            family_evidence = [str(path) for path in analyses.get("evidence", []) if path]
            for analysis, value in analyses.items():
                if not isinstance(value, dict) or not value.get("scope"):
                    continue
                row = dict(value)
                row["family"] = family
                row["analysis"] = analysis
                exact_evidence = pair_evidence.get((str(family), str(analysis)), [])
                row["evidence_origin"] = "technical_content_coverage" if exact_evidence else "family_matrix"
                row["evidence"] = list(
                    dict.fromkeys([*(exact_evidence or family_evidence), *row.get("evidence", [])])
                )
                scope_id = str(value["scope"])
                if scope_id in rows:
                    previous = rows[scope_id]
                    previous["evidence"] = list(
                        dict.fromkeys([*previous.get("evidence", []), *row["evidence"]])
                    )
                    previous.setdefault("matrix_entries", []).append(
                        {"family": family, "analysis": analysis, "status": row.get("status")}
                    )
                    if previous.get("status") != row.get("status"):
                        previous["status"] = "ambiguous"
                    if previous.get("evidence_origin") != row.get("evidence_origin"):
                        previous["evidence_origin"] = "technical_content_coverage"
                else:
                    row["matrix_entries"] = [
                        {"family": family, "analysis": analysis, "status": row.get("status")}
                    ]
                    rows[scope_id] = row
        return rows

    @staticmethod
    def _proof_record(
        raw: dict[str, Any],
        matrix_row: dict[str, Any] | None,
        readiness: Any,
        default_requirements: dict[str, Any],
    ) -> dict[str, Any]:
        target = str(raw.get("target_status", "stable"))
        status = str(matrix_row.get("status", "missing")) if matrix_row else "missing"
        blockers: list[str] = []
        blocker_categories: list[str] = []
        evidence = [str(path) for path in (matrix_row or {}).get("evidence", []) if path]
        missing_evidence = [path for path in evidence if not project_path(path).is_file()]
        if matrix_row is None:
            blockers.append("scope absent from element-analysis matrix")
            blocker_categories.append("matrix_missing")
        elif status != target:
            blockers.append(f"matrix status is {status}, target is {target}")
            blocker_categories.append("maturity_not_stable")
        proof_requirements = dict(default_requirements)
        proof_requirements.update(dict(raw.get("proof_requirements", {})))
        for key, label in (
            ("analytical_or_invariant", "analytical/invariant proof"),
            ("convergence", "multi-mesh convergence proof"),
            ("external_correlation", "external correlation"),
            ("owner_review", "Owner review"),
        ):
            if not bool(proof_requirements.get(key, False)):
                blockers.append(f"{label} not declared in release registry")
                blocker_categories.append("release_policy_incomplete")
        if not evidence:
            blockers.append("matrix evidence list is empty")
            blocker_categories.append("evidence_missing")
        if missing_evidence:
            blockers.append(f"{len(missing_evidence)} matrix evidence path(s) missing")
            blocker_categories.append("evidence_missing")
        return {
            "matrix_status": status,
            "target_status": target,
            "family": matrix_row.get("family") if matrix_row else None,
            "analysis": matrix_row.get("analysis") if matrix_row else None,
            "evidence_origin": matrix_row.get("evidence_origin") if matrix_row else None,
            "evidence": evidence,
            "missing_evidence": missing_evidence,
            "matrix_entries": matrix_row.get("matrix_entries", []) if matrix_row else [],
            "blockers": blockers,
            "blocker_categories": sorted(set(blocker_categories)),
            "readiness_status": readiness.status,
        }

    @staticmethod
    def _readiness_detail(readiness: Any) -> tuple[str, list[str]]:
        parts: list[str] = []
        categories: list[str] = []
        if readiness.missing_paths:
            parts.append(f"{len(readiness.missing_paths)} linked path(s) missing")
            categories.append("evidence_missing")
        if readiness.missing_independent_references:
            parts.append(f"{len(readiness.missing_independent_references)} independent reference(s) missing")
            categories.append("external_reference_missing")
        if readiness.orphan_requirements or readiness.orphan_formulas:
            parts.append("orphan traceability records present")
            categories.append("traceability_orphan")
        return "; ".join(parts) or "scope readiness is not PASS", categories or ["readiness_failed"]

    def _campaign_record(
        self,
        registry: dict[str, Any],
        output: Path,
        *,
        execute_campaign: bool,
        campaign_manifest: str | Path | None,
    ) -> dict[str, Any]:
        campaign_data = registry.get("campaign", {})
        manifest_value = campaign_manifest or campaign_data.get("manifest", "qualification/campaign.json")
        manifest_path = Path(manifest_value)
        if not manifest_path.is_absolute():
            manifest_path = project_root() / manifest_path
        if not execute_campaign:
            case_count = _campaign_case_count(manifest_path)
            return {
                "status": "NOT_EXECUTED",
                "readiness_status": "WARNING",
                "required": bool(campaign_data.get("required", False)),
                "manifest": _project_relative(manifest_path),
                "case_count": case_count,
                "detail": f"campaign not executed ({case_count} case(s)); use --execute-campaign",
            }
        campaign_output = output / "campaign"
        summary = QualificationCampaignRunner().run(manifest_path, campaign_output)
        campaign_status = str(summary.get("status", "FAIL"))
        required = bool(campaign_data.get("required", False))
        diagnostics = _campaign_diagnostics(summary)
        return {
            "status": campaign_status,
            "readiness_status": "PASS" if campaign_status == "PASS" else ("FAIL" if required else "WARNING"),
            "required": required,
            "manifest": _project_relative(manifest_path),
            "case_count": summary.get("case_count", 0),
            "passed_count": summary.get("passed_count", 0),
            **diagnostics,
            "summary_path": _project_relative(campaign_output / "qualification_campaign_summary.json"),
            "detail": f"campaign {campaign_status}: {summary.get('passed_count', 0)}/{summary.get('case_count', 0)} passed",
        }

    @staticmethod
    def _owner_review_record(registry: dict[str, Any]) -> dict[str, Any]:
        review = registry.get("owner_review", {})
        decision = str(review.get("decision", "pending")).lower()
        if decision in {
            "accepted",
            "accepted_with_recommendations",
            "accepted_for_release_preparation",
        }:
            return {"status": "PASS", "decision": decision, "detail": "owner review decision recorded"}
        return {
            "status": "FAIL",
            "decision": decision,
            "detail": "owner review is pending; release gate cannot pass",
        }

    @staticmethod
    def _global_status(checks: list[dict[str, Any]]) -> str:
        if any(check["status"] == "FAIL" for check in checks):
            return "FAIL"
        if any(check["status"] == "WARNING" for check in checks):
            return "WARNING"
        return "PASS"

    def _summary(
        self,
        registry: dict[str, Any],
        root: Path,
        *,
        status: str,
        checks: list[dict[str, Any]],
        scope_rows: list[dict[str, Any]],
        campaign: dict[str, Any],
        owner_review: dict[str, Any],
        source: dict[str, Any],
    ) -> dict[str, Any]:
        warnings = [check["detail"] for check in checks if check["status"] == "WARNING"]
        failures = [check["detail"] for check in checks if check["status"] == "FAIL"]
        runtime = runtime_fingerprint()
        runtime["python"].pop("executable", None)
        runtime.get("platform", {}).pop("processor", None)
        runtime["parallel_environment"] = {
            name: bool(value) for name, value in runtime.get("parallel_environment", {}).items()
        }
        return {
            "schema_version": 1,
            "release": {
                "name": DISPLAY_NAME,
                "version": str(registry["release"]["version"]),
                "channel": str(registry["release"].get("channel", "alpha")),
                "purpose": str(registry["release"].get("purpose", "")),
            },
            "status": status,
            "certification_claim": "none",
            "profile": str(registry.get("profile", "engineering")),
            "baseline": registry["baseline"],
            "source": source,
            "checks": checks,
            "scope_summary": {
                "count": len(scope_rows),
                "required_count": sum(1 for row in scope_rows if row["required"]),
                "pass_count": sum(1 for row in scope_rows if row["status"] == "PASS"),
                "warning_count": sum(1 for row in scope_rows if row["status"] == "WARNING"),
                "fail_count": sum(1 for row in scope_rows if row["status"] == "FAIL"),
            },
            "blocker_summary": _blocker_summary(scope_rows, campaign, owner_review, source),
            "scopes": scope_rows,
            "campaign": campaign,
            "owner_review": owner_review,
            "open_items": warnings + failures,
            "policy": registry.get("policy", {}),
            "provenance": {
                "generated_at_utc": utc_timestamp(),
                "registry": _project_relative(self.registry_path),
                "registry_sha256": sha256(self.registry_path),
                "runtime": runtime,
                "locked_environments": locked_environment_fingerprints(root),
            },
        }

    @staticmethod
    def _write_manifest(
        output: Path,
        registry: dict[str, Any],
        summary_path: Path,
        markdown_path: Path,
    ) -> dict[str, str]:
        manifest_path = output / "release_vv_manifest.json"
        files = [
            manifest_file_entry("summary", summary_path, output),
            manifest_file_entry("report", markdown_path, output),
        ]
        manifest = {
            "manifest_schema_version": 1,
            "release": registry["release"],
            "files": files,
        }
        write_json_file(manifest_path, manifest)
        return {"path": manifest_path.name, "sha256": sha256(manifest_path)}

    @staticmethod
    def _render_markdown(summary: dict[str, Any]) -> str:
        lines = [
            f"# QF_solver {summary['release']['version']} - pack V&V",
            "",
            f"Statut global : **{summary['status']}**",
            "",
            "Ce document décrit la readiness V&V de la release. Il ne constitue pas "
            "une certification externe.",
            "",
            "## Release candidate",
            "",
            f"- version cible : `{summary['release']['version']}` ;",
            f"- nom : `{summary['release'].get('name', 'QF_solver')}` ;",
            "- tag de release : non créé à ce stade ;",
            "",
            "## Baseline",
            "",
            f"- version : `{summary['baseline']['version']}` ;",
            f"- tag : `{summary['baseline']['tag']}` ;",
            f"- commit : `{summary['baseline']['commit']}` ;",
            f"- source courante propre : `{not summary['source']['dirty']}`.",
            "",
            "## Scopes",
            "",
            "| Scope | Requis | Role | Readiness | Verdict release | Detail |",
            "| --- | ---: | --- | --- | --- | --- |",
        ]
        for row in summary["scopes"]:
            lines.append(
                f"| `{row['id']}` | {'oui' if row['required'] else 'non'} | {row['role']} | "
                f"{row['readiness_status']} | {row['status']} | {row['detail']} |"
            )
        campaign = summary["campaign"]
        lines.extend(
            [
                "",
                "## Campagne",
                "",
                f"- statut : `{campaign['status']}` ;",
                f"- cas : `{campaign.get('passed_count', '-')}/{campaign.get('case_count', '-')}` ;",
                f"- manifeste : `{campaign['manifest']}` ;",
                f"- detail : {campaign['detail']}.",
                f"- diagnostic : {campaign.get('diagnostic', 'non disponible')}.",
                "",
                "## Diagnostic des blocages",
                "",
                "| Cause | Nombre |",
                "| --- | ---: |",
            ]
        )
        for category, count in summary.get("blocker_summary", {}).items():
            lines.append(f"| `{category}` | {count} |")
        lines.extend(
            [
                "",
                "## Revue propriétaire",
                "",
                f"- decision : `{summary['owner_review']['decision']}` ;",
                f"- statut : `{summary['owner_review']['status']}` ;",
                f"- detail : {summary['owner_review']['detail']}.",
                "",
                "## Points ouverts",
                "",
            ]
        )
        if summary["open_items"]:
            lines.extend(f"- {item}." for item in summary["open_items"])
        else:
            lines.append("- aucun.")
        lines.append("")
        return "\n".join(lines)


def _campaign_case_count(path: Path) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    cases = data.get("cases", []) if isinstance(data, dict) else []
    return len(cases) if isinstance(cases, list) else 0


def _campaign_diagnostics(summary: dict[str, Any]) -> dict[str, Any]:
    """Classify campaign failures without turning policy warnings into mechanics failures."""
    rows = [row for row in summary.get("cases", []) if isinstance(row, dict)]
    numerical_failures = sum(
        1
        for row in rows
        if row.get("failed_check_count", 0) or row.get("infrastructure_errors")
    )
    policy_blocked = sum(
        1
        for row in rows
        if not row.get("passed", False)
        and not row.get("failed_check_count", 0)
        and not row.get("infrastructure_errors")
    )
    verdict_mismatches = sum(
        1 for row in rows if str(row.get("actual_status")) != str(row.get("expected_status"))
    )
    if numerical_failures:
        diagnostic = "numerical_or_infrastructure_failures_present"
    elif policy_blocked:
        diagnostic = "calculation_checks_passed_but_qualification_policy_blocks"
    else:
        diagnostic = "all_campaign_cases_accepted"
    return {
        "numerical_or_infrastructure_failure_count": numerical_failures,
        "qualification_policy_blocked_count": policy_blocked,
        "verdict_mismatch_count": verdict_mismatches,
        "diagnostic": diagnostic,
    }


def _blocker_summary(
    scope_rows: list[dict[str, Any]],
    campaign: dict[str, Any],
    owner_review: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, int]:
    """Aggregate release blockers for a concise audit dashboard."""
    counts: dict[str, int] = {}
    for row in scope_rows:
        for category in row.get("blocker_categories", []):
            counts[str(category)] = counts.get(str(category), 0) + 1
    if campaign.get("readiness_status") != "PASS":
        counts["campaign_not_green"] = counts.get("campaign_not_green", 0) + 1
    if owner_review.get("status") != "PASS":
        counts["owner_review_pending"] = counts.get("owner_review_pending", 0) + 1
    if source.get("dirty"):
        counts["source_dirty"] = counts.get("source_dirty", 0) + 1
    return dict(sorted(counts.items()))


def _project_relative(path: str | Path) -> str:
    value = Path(path)
    root = project_root().resolve()
    try:
        return value.resolve().relative_to(root).as_posix()
    except ValueError:
        return value.name


def _git_output(root: Path, *arguments: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""
