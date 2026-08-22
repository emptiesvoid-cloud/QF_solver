"""Auditable readiness checks for the 0.2.1a0 maturity-promotion plan."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from solveur.io.manifest import sha256, write_json_file
from solveur.paths import project_root
from solveur.verification.maturity_promotion_reports import (
    build_owner_review_packet,
    render_markdown as _render_markdown,
    render_owner_packet as _render_owner_packet,
)
from solveur.verification.maturity_promotion_helpers import (
    compare as _compare,
    get_path as _get_path,
    relative as _relative,
    unique as _unique,
)


_OWNER_DECISIONS = frozenset(
    {
        "accepted_with_recommendations",
        "accepted_for_bounded_engineering_use",
    }
)


PAIR_IDS_BY_SCOPE: dict[str, tuple[str, ...]] = {
    "beam2-linear-dynamics": ("PAIR-BEAM2-MODAL", "PAIR-BEAM2-NEWMARK", "PAIR-BEAM2-HARMONIC"),
    "beam2-linear-static": ("PAIR-BEAM2-STATIC",),
    "contact-frictional-static": ("PAIR-CONTACT-FRICTION",),
    "contact-v1-linear-static-bounded": ("PAIR-CONTACT-NORMAL",),
    "discrete-linear": ("PAIR-DISCRETE-STATIC",),
    "discrete-linear-dynamics": ("PAIR-DISCRETE-MODAL", "PAIR-DISCRETE-NEWMARK", "PAIR-DISCRETE-HARMONIC"),
    "mitc3-harmonic-response": ("PAIR-MITC3-HARMONIC",),
    "mitc3-laminate-dynamic": ("PAIR-MITC3-LAMINATE-DYN",),
    "mitc3-laminate-static": ("PAIR-MITC3-LAMINATE",),
    "mitc3-laminate-static-curved": ("PAIR-MITC3-LAMINATE-CURVED-PROJECTED",),
    "mitc3-linear-static": ("PAIR-MITC3-STATIC",),
    "mitc3-modal": ("PAIR-MITC3-MODAL",),
    "mitc3-transient-dynamic": ("PAIR-MITC3-NEWMARK",),
    "mitc4-harmonic-response": ("PAIR-MITC4-HARMONIC",),
    "mitc4-laminate-dynamic": ("PAIR-MITC4-LAMINATE-DYN",),
    "mitc4-laminate-static": ("PAIR-MITC4-LAMINATE",),
    "mitc4-linear-static": ("PAIR-MITC4-STATIC",),
    "mitc4-modal": ("PAIR-MITC4-MODAL",),
    "mitc4-transient-dynamic": ("PAIR-MITC4-NEWMARK",),
    "tet10-harmonic-response": ("PAIR-TET10-HARMONIC",),
    "tet10-linear-static": ("PAIR-TET10-STATIC",),
    "tet10-material-nonlinear": ("PAIR-TET10-NONLINEAR",),
    "tet10-modal": ("PAIR-TET10-MODAL",),
    "tet10-transient-dynamic": ("PAIR-TET10-NEWMARK",),
    "tet4-harmonic-response": ("PAIR-TET4-HARMONIC",),
    "tet4-linear-static": ("PAIR-TET4-STATIC",),
    "tet4-material-nonlinear": ("PAIR-TET4-J2",),
    "tet4-modal": ("PAIR-TET4-MODAL",),
    "tet4-total-lagrangian-structural-v2": ("PAIR-TET4-TL",),
    "tet4-transient-dynamic": ("PAIR-TET4-NEWMARK",),
}


class MaturityPromotionAuditor:
    """Check promotion inputs without changing the authoritative matrix."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or project_root()).resolve()

    def audit(
        self,
        *,
        plan_path: str | Path | None = None,
        matrix_path: str | Path | None = None,
        coverage_path: str | Path | None = None,
        criteria_path: str | Path | None = None,
    ) -> dict[str, Any]:
        plan_file = self._path(plan_path or "qualification/maturity_promotion_0_2_1.json")
        matrix_file = self._path(matrix_path or "qualification/element_analysis_matrix.json")
        coverage_file = self._path(coverage_path or "qualification/technical_content_coverage.json")
        criteria_file = self._path(criteria_path or "qualification/maturity_criteria_0_2_1.json")
        plan = self._read_json(plan_file)
        matrix = self._read_json(matrix_file)
        coverage = self._read_json(coverage_file)
        criteria_registry = self._read_json(criteria_file)
        stable_error_limit = float(criteria_registry.get("policy", {}).get("final_relative_error_limit", 0.01))
        matrix_statuses = _matrix_statuses(matrix)
        pairs = {str(pair["id"]): pair for pair in coverage.get("element_analysis_pairs", [])}
        criteria_by_scope = {
            str(entry["scope"]): entry
            for entry in criteria_registry.get("scopes", [])
            if entry.get("scope")
        }
        rows = [
            self._audit_scope(
                entry,
                matrix_statuses,
                pairs,
                plan.get("evidence_templates", {}),
                criteria_by_scope,
                stable_error_limit,
            )
            for entry in plan.get("scope_plans", [])
        ]
        rows.extend(
            self._audit_supplementary(
                entry,
                plan.get("evidence_templates", {}),
                criteria_by_scope,
                stable_error_limit,
            )
            for entry in plan.get("supplementary_material_scopes", [])
        )
        blocked = [
            row
            for row in rows
            if row["promotion_gate"]
            not in {"NO_PROMOTION_REQUIRED", "READY_FOR_OWNER_REVIEW", "READY_FOR_RELEASE_ACTION"}
        ]
        summary = {
            "scope_count": len(rows),
            "blocked_scope_count": len(blocked),
            "path_integrity_pass_count": sum(row["path_integrity"] == "PASS" for row in rows),
            "owner_review_present_count": sum(row["owner_review"] == "ACCEPTED" for row in rows),
            "owner_decision_pending_scope_count": sum(
                row["blocking_classification"] == "owner_decision_pending" for row in rows
            ),
            "target_stable_count": sum(row["target_status"] == "stable" for row in rows),
        }
        return {
            "schema_version": 1,
            "audit_id": "QF-MATURITY-PROMOTION-AUDIT-021-001",
            "status": "PASS" if not blocked else "WARNING",
            "policy": {
                "matrix_modified": False,
                "automatic_maturity_promotion": False,
                "owner_review_required": True,
                "unstructured_template_criteria_block_stable": True,
                "final_relative_error_limit": criteria_registry.get("policy", {}).get(
                    "final_relative_error_limit", 0.01
                ),
                "engineering_primary_observable_limit": criteria_registry.get("policy", {}).get(
                    "engineering_primary_observable_limit", 0.01
                ),
                "primary_engineering_error_limit": criteria_registry.get("policy", {}).get(
                    "primary_engineering_error_limit", 0.01
                ),
                "primary_engineering_error_limit_unit": criteria_registry.get("policy", {}).get(
                    "primary_engineering_error_limit_unit", "relative_fraction"
                ),
                "primary_engineering_error_policy": criteria_registry.get("policy", {}).get(
                    "primary_engineering_error_policy",
                    "Every primary engineering observable must have a relative error <= 1 percent.",
                ),
                "final_relative_error_policy": criteria_registry.get("policy", {}).get(
                    "final_relative_error_policy",
                    "Primary comparison observables must be no greater than 1 percent for stable promotion.",
                ),
                "singularity_policy": criteria_registry.get("policy", {}).get(
                    "singularity_policy",
                    "Point peaks at singularities are informative only.",
                ),
            },
            "sources": {
                "plan": _relative(plan_file, self.root),
                "plan_sha256": sha256(plan_file),
                "matrix": _relative(matrix_file, self.root),
                "matrix_sha256": sha256(matrix_file),
                "coverage": _relative(coverage_file, self.root),
                "coverage_sha256": sha256(coverage_file),
                "criteria": _relative(criteria_file, self.root),
                "criteria_sha256": sha256(criteria_file),
            },
            "summary": summary,
            "scopes": rows,
        }

    def write_reports(self, output: str | Path, report: dict[str, Any]) -> dict[str, Path]:
        destination = self._path(output)
        destination.mkdir(parents=True, exist_ok=True)
        json_path = destination / "maturity_promotion_audit.json"
        markdown_path = destination / "maturity_promotion_audit.md"
        packet_json_path = destination / "owner_review_packet.json"
        packet_markdown_path = destination / "owner_review_packet.md"
        write_json_file(json_path, report)
        markdown_path.write_text(_render_markdown(report), encoding="utf-8")
        packet = build_owner_review_packet(report)
        write_json_file(packet_json_path, packet)
        packet_markdown_path.write_text(_render_owner_packet(packet), encoding="utf-8")
        return {
            "json": json_path,
            "markdown": markdown_path,
            "owner_packet_json": packet_json_path,
            "owner_packet_markdown": packet_markdown_path,
        }

    def _audit_scope(
        self,
        entry: dict[str, Any],
        matrix_statuses: dict[str, str],
        pairs: dict[str, dict[str, Any]],
        templates: dict[str, dict[str, Any]],
        criteria_by_scope: dict[str, dict[str, Any]],
        stable_error_limit: float,
    ) -> dict[str, Any]:
        scope = str(entry["scope"])
        current = matrix_statuses.get(scope, "missing")
        pair_ids = PAIR_IDS_BY_SCOPE.get(scope, ())
        pair_records = [pairs[pair_id] for pair_id in pair_ids if pair_id in pairs]
        evidence = _unique(
            path
            for pair in pair_records
            for path in pair.get("oracle", {}).get("evidence", [])
        )
        evidence.extend(_family_evidence(scope, self._read_json(self.root / "qualification" / "element_analysis_matrix.json")))
        criteria_entry = criteria_by_scope.get(scope)
        evidence.extend(_criteria_evidence_paths(criteria_entry))
        evidence = _unique(evidence)
        return self._build_row(
            entry,
            current,
            evidence,
            pair_records,
            templates,
            criteria_by_scope.get(scope),
            stable_error_limit,
        )

    def _audit_supplementary(
        self,
        entry: dict[str, Any],
        templates: dict[str, dict[str, Any]],
        criteria_by_scope: dict[str, dict[str, Any]],
        stable_error_limit: float,
    ) -> dict[str, Any]:
        row = dict(entry)
        row["current_status"] = "supplementary_scope"
        row["priority"] = "P2"
        criteria_entry = criteria_by_scope.get(str(entry["scope"]))
        return self._build_row(
            row,
            "supplementary_scope",
            _criteria_evidence_paths(criteria_entry),
            [],
            templates,
            criteria_entry,
            stable_error_limit,
        )

    def _build_row(
        self,
        entry: dict[str, Any],
        current: str,
        evidence: list[str],
        pair_records: list[dict[str, Any]],
        templates: dict[str, dict[str, Any]],
        criteria_entry: dict[str, Any] | None,
        stable_error_limit: float,
    ) -> dict[str, Any]:
        scope = str(entry["scope"])
        target = str(entry.get("target_status", ""))
        existing = [path for path in evidence if (self.root / path).is_file()]
        missing = [path for path in evidence if not (self.root / path).is_file()]
        reviews = [
            path
            for path in existing
            if "review" in path.lower() and Path(path).suffix.lower() == ".json"
        ]
        owner_review = _review_state(self.root, reviews, scope)
        owner_promotion_target = _signed_promotion_target(self.root, reviews, scope)
        pair_oracle = sorted({str(pair.get("oracle", {}).get("kind", "unknown")) for pair in pair_records})
        required = list(templates.get(str(entry.get("template", "")), {}).get("required", []))
        criteria_report = _evaluate_criteria(self.root, criteria_entry)
        stable_error_violations = (
            _stable_error_violations(criteria_report, stable_error_limit)
            if target == "stable"
            else []
        )
        if stable_error_violations:
            criteria_report.append(
                {
                    "id": "STABLE-1PCT-POLICY",
                    "title": "Erreur relative finale maximale pour promotion stable",
                    "kind": "stable_policy",
                    "required": True,
                    "status": "FAIL",
                    "limit": stable_error_limit,
                    "violations": stable_error_violations,
                    "reference": "qualification/maturity_criteria_0_2_1.json policy.final_relative_error_limit",
                }
            )
        blocking_criteria = [
            criterion["id"]
            for criterion in criteria_report
            if criterion["required"] and criterion["status"] not in {"PASS", "NOT_APPLICABLE"}
        ]
        criteria_by_id = {str(criterion["id"]): criterion for criterion in criteria_report}
        pending_blockers = {
            identifier
            for identifier in blocking_criteria
            if criteria_by_id.get(identifier, {}).get("kind") in {"pending", "owner_review"}
        }
        if not blocking_criteria:
            blocking_classification = "none"
        elif pending_blockers == set(blocking_criteria):
            blocking_classification = "owner_decision_pending"
        else:
            blocking_classification = "technical_criteria_failed"
        gate = "NO_PROMOTION_REQUIRED" if current == target else "READY_FOR_OWNER_REVIEW"
        if current == "missing":
            gate = "BLOCKED_MATRIX_SCOPE_MISSING"
        elif missing:
            gate = "BLOCKED_EVIDENCE_MISSING"
        elif criteria_entry and blocking_criteria:
            owner_review_blockers = all(
                criteria_by_id.get(identifier, {}).get("kind") in {"pending", "owner_review"}
                for identifier in blocking_criteria
            )
            gate = "BLOCKED_OWNER_REVIEW" if owner_review_blockers else "BLOCKED_CRITERIA_FAILED"
        elif current == target:
            gate = "NO_PROMOTION_REQUIRED"
        elif target == "stable" and not criteria_entry:
            gate = "BLOCKED_CRITERIA_NOT_STRUCTURED"
        elif target == "stable":
            gate = (
                "READY_FOR_RELEASE_ACTION"
                if owner_promotion_target == target and not blocking_criteria
                else "READY_FOR_OWNER_REVIEW"
            )
        elif owner_promotion_target == target and not blocking_criteria:
            gate = "READY_FOR_RELEASE_ACTION"
        elif owner_review != "ACCEPTED":
            gate = "BLOCKED_OWNER_REVIEW"
        return {
            "scope": scope,
            "priority": str(entry.get("priority", "P2")),
            "current_status": current,
            "planned_current_status": str(entry.get("current_status", "")),
            "target_status": target,
            "maturity_target": target,
            "template": str(entry.get("template", "")),
            "required_template_criteria": required,
            "template_criteria_status": "STRUCTURED" if criteria_entry else "UNSTRUCTURED",
            "criteria_scope": criteria_entry.get("scope") if criteria_entry else None,
            "criteria_status": (
                "PASS"
                if criteria_entry and not blocking_criteria
                else "BLOCKED"
                if criteria_entry
                else "UNSTRUCTURED"
            ),
            "technical_status": (
                "PASS"
                if criteria_entry and not blocking_criteria
                else "BLOCKED"
                if criteria_entry
                else "UNSTRUCTURED"
            ),
            "criteria": criteria_report,
            "stable_error_violations": stable_error_violations,
            "blocking_criteria": blocking_criteria,
            "blocking_classification": blocking_classification,
            "pair_ids": [str(pair["id"]) for pair in pair_records],
            "oracle_kinds": pair_oracle,
            "evidence_paths": evidence,
            "existing_evidence_count": len(existing),
            "missing_evidence": missing,
            "path_integrity": "PASS" if not missing else "FAIL",
            "owner_review": owner_review,
            "owner_decision": owner_review,
            "owner_promotion_target": owner_promotion_target,
            "owner_review_paths": reviews,
            "promotion_gate": gate,
            "release_readiness": _release_readiness(gate, blocking_classification),
            "next_action": _next_action(gate, target, blocking_classification),
        }

    def _path(self, path: str | Path) -> Path:
        candidate = Path(path)
        return candidate if candidate.is_absolute() else self.root / candidate

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))


def audit_maturity_promotion(**kwargs: Any) -> dict[str, Any]:
    """Run the promotion audit using the current project files."""
    return MaturityPromotionAuditor().audit(**kwargs)


def write_maturity_promotion_reports(output: str | Path, report: dict[str, Any]) -> dict[str, Path]:
    return MaturityPromotionAuditor().write_reports(output, report)


def _matrix_statuses(matrix: dict[str, Any]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for family in matrix.get("families", {}).values():
        for entry in family.values():
            if isinstance(entry, dict) and entry.get("scope"):
                statuses[str(entry["scope"])] = str(entry.get("status", "missing"))
    return statuses


def _family_evidence(scope: str, matrix: dict[str, Any]) -> list[str]:
    family_name = scope.split("-", 1)[0].upper()
    if family_name == "BEAM2":
        family_name = "BEAM2"
    if scope.startswith("discrete-"):
        family_name = "SPRING_MASS"
    if scope.startswith("contact-"):
        family_name = "CONTACT"
    family = matrix.get("families", {}).get(family_name, {})
    evidence = [str(path) for path in family.get("evidence", [])]
    for entry in family.values():
        if not isinstance(entry, dict) or str(entry.get("scope", "")) != scope:
            continue
        review = entry.get("owner_review")
        if isinstance(review, str) and review:
            evidence.append(review)
    return _unique(evidence)


def _review_state(root: Path, paths: list[str], scope: str | None = None) -> str:
    if not paths:
        return "MISSING"
    paths = [path for path in paths if Path(path).suffix.lower() == ".json"]
    if not paths:
        return "MISSING"
    decisions: list[str] = []
    for path in paths:
        try:
            payload = json.loads((root / path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        matched_scope = False
        if scope and payload.get("scope"):
            payload_scope = payload["scope"]
            matched_scope = (
                scope in payload_scope
                if isinstance(payload_scope, list)
                else str(payload_scope) == scope
            )
        for key in ("decisions", "reviews"):
            records = payload.get(key)
            if not isinstance(records, list):
                continue
            for record in records:
                if not isinstance(record, dict):
                    continue
                if scope and str(record.get("scope", "")) != scope:
                    continue
                matched_scope = True
                for decision_key in ("decision", "owner_decision", "status"):
                    value = record.get(decision_key)
                    if value is not None:
                        decisions.append(str(value).lower())
        for key in ("decision", "owner_decision", "status"):
            value = payload.get(key)
            if value is not None and (not scope or not payload.get("scope") or matched_scope):
                decisions.append(str(value).lower())
    if any("pending" in decision or not decision for decision in decisions):
        return "PENDING"
    if any("accepted" in decision for decision in decisions):
        return "ACCEPTED"
    return "PRESENT_NO_DECISION"


def _signed_promotion_target(root: Path, paths: list[str], scope: str) -> str | None:
    """Return a matching signed promotion target, without changing the matrix."""
    targets: list[str] = []
    for path in paths:
        if Path(path).suffix.lower() != ".json":
            continue
        try:
            payload = json.loads((root / path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        records: list[dict[str, Any]] = []
        if isinstance(payload, dict):
            records.append(payload)
            for key in ("decisions", "reviews"):
                values = payload.get(key)
                if isinstance(values, list):
                    records.extend(item for item in values if isinstance(item, dict))
        for record in records:
            record_scope = record.get("scope")
            scopes = record_scope if isinstance(record_scope, list) else [record_scope]
            if scope not in {str(item) for item in scopes if item is not None}:
                continue
            target = record.get("promotion_target")
            decision = record.get("decision") or record.get("owner_decision")
            signature = record.get("signature")
            if (
                isinstance(target, str)
                and target
                and isinstance(signature, dict)
                and decision in _OWNER_DECISIONS
                and decision != "more_evidence_required"
            ):
                targets.append(target)
    return targets[-1] if targets else None


def _next_action(gate: str, target: str, blocking_classification: str = "none") -> str:
    if blocking_classification == "owner_decision_pending":
        return "Faire enregistrer une owner_review datee apres lecture des preuves."
    actions = {
        "BLOCKED_EVIDENCE_MISSING": "Regenerer ou archiver les preuves manquantes avant toute revue.",
        "BLOCKED_CRITERIA_NOT_STRUCTURED": f"Structurer les criteres du gabarit puis ouvrir l'owner_review pour la cible {target}.",
        "BLOCKED_CRITERIA_FAILED": "Corriger ou completer les criteres atomiques signales avant owner_review.",
        "BLOCKED_OWNER_REVIEW": "Faire enregistrer une owner_review datee apres lecture des preuves.",
        "BLOCKED_MATRIX_SCOPE_MISSING": "Ajouter le scope dans la matrice autoritative avant promotion.",
        "READY_FOR_RELEASE_ACTION": "Executer l'action de release controlee apres revue des preuves et sauvegarde de la matrice.",
        "NO_PROMOTION_REQUIRED": "Maintenir le scope et surveiller les non-regressions.",
        "READY_FOR_OWNER_REVIEW": "Faire relire le dossier et enregistrer la decision owner_review.",
    }
    return actions.get(gate, "Analyser le blocage signale.")


def _release_readiness(gate: str, blocking_classification: str) -> str:
    """Expose a release verdict without conflating it with maturity status."""
    if gate == "READY_FOR_RELEASE_ACTION":
        return "READY_FOR_RELEASE_ACTION"
    if gate == "NO_PROMOTION_REQUIRED":
        return "NO_PROMOTION_REQUIRED"
    if blocking_classification == "technical_criteria_failed" or gate in {
        "BLOCKED_CRITERIA_FAILED",
        "BLOCKED_EVIDENCE_MISSING",
        "BLOCKED_CRITERIA_NOT_STRUCTURED",
        "BLOCKED_MATRIX_SCOPE_MISSING",
    }:
        return "NOT_READY_TECHNICAL"
    if gate in {"BLOCKED_OWNER_REVIEW", "READY_FOR_OWNER_REVIEW"}:
        return "NOT_READY_OWNER_REVIEW"
    return "NOT_READY"


def _evaluate_criteria(root: Path, entry: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Evaluate only explicit criteria; absence remains visibly unstructured."""
    if not entry:
        return []
    results: list[dict[str, Any]] = []
    for criterion in entry.get("criteria", []):
        results.append(_evaluate_criterion(root, criterion))
    return results


_PRIMARY_ERROR_TOKENS = (
    "relative_error",
    "relative_difference",
    "response_error",
    "frequency_error",
    "displacement_difference",
    "displacement_error",
    "displacement_vector_error",
    "fine_displacement",
    "history_error",
    "peak_difference",
    "deflection_error",
    "vector_difference",
    "terminal_rotation_relative_error",
    "final_normalized_rms",
    "relative_rms_error",
    "energy_error",
    "stress_error",
    "strain_error",
    "reaction_error",
    "resultant_error",
    "frequency_difference",
    "force_difference",
)

_NON_PRIMARY_ERROR_TOKENS = (
    "mesh_increment",
    "refinement_error",
    "energy_drift",
    "residual",
    "orthogonality",
    "balance",
    "identity",
)


def _stable_error_violations(criteria: list[dict[str, Any]], limit: float) -> list[dict[str, Any]]:
    """Find measured primary comparison errors that exceed the stable limit."""
    violations: list[dict[str, Any]] = []
    for criterion in criteria:
        # Optional probes may document an excluded sub-domain. They must remain
        # visible in the audit, but cannot block the stable sub-scope selected
        # by the required criteria.
        if not bool(criterion.get("required", True)):
            continue
        for assertion in criterion.get("assertions", []):
            path = str(assertion.get("path", ""))
            actual = assertion.get("actual")
            if not isinstance(actual, (int, float)) or isinstance(actual, bool):
                continue
            normalized = path.lower()
            if not any(token in normalized for token in _PRIMARY_ERROR_TOKENS):
                continue
            if any(token in normalized for token in _NON_PRIMARY_ERROR_TOKENS):
                continue
            if float(actual) > limit:
                violations.append(
                    {
                        "criterion_id": str(criterion.get("id", "")),
                        "path": path,
                        "actual": float(actual),
                        "limit": limit,
                        "relative_excess": float(actual) - limit,
                    }
                )
    return violations


def _criteria_evidence_paths(entry: dict[str, Any] | None) -> list[str]:
    """Expose supplementary-scope sources to the same path-integrity audit."""
    if not entry:
        return []
    paths: list[str] = []
    for criterion in entry.get("criteria", []):
        source = criterion.get("source")
        if source:
            paths.append(str(source))
        if str(criterion.get("kind", "")) == "file_set":
            paths.extend(str(path) for path in criterion.get("paths", []))
    return _unique(paths)


def _evaluate_criterion(root: Path, criterion: dict[str, Any]) -> dict[str, Any]:
    kind = str(criterion.get("kind", ""))
    identifier = str(criterion.get("id", "missing-id"))
    required = bool(criterion.get("required", True))
    source = criterion.get("source")
    source_path = root / str(source) if source else None
    base = {
        "id": identifier,
        "title": str(criterion.get("title", "")),
        "kind": kind,
        "required": required,
        "source": str(source) if source else None,
        "reference": str(criterion.get("reference", "")),
    }
    if kind == "not_comparable":
        base.update({"status": "NOT_APPLICABLE", "reason": str(criterion.get("reason", ""))})
        return base
    if kind == "pending":
        base.update({"status": "FAIL", "reason": str(criterion.get("reason", ""))})
        return base
    if kind == "file_set":
        paths = [str(path) for path in criterion.get("paths", [])]
        missing = [path for path in paths if not (root / path).is_file()]
        base.update({"status": "PASS" if not missing else "FAIL", "paths": paths, "missing": missing})
        return base
    if source_path is None or not source_path.is_file():
        base.update({"status": "FAIL", "error": "source_missing"})
        return base
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        base.update({"status": "FAIL", "error": f"source_invalid:{exc}"})
        return base
    if kind == "campaign_cases":
        available = {str(case.get("id")) for case in payload.get("cases", [])}
        expected = [str(case_id) for case_id in criterion.get("case_ids", [])]
        missing = [case_id for case_id in expected if case_id not in available]
        base.update({"status": "PASS" if not missing else "FAIL", "case_ids": expected, "missing": missing})
        return base
    assertions = criterion.get("assertions", [])
    checks = [_evaluate_assertion(payload, assertion) for assertion in assertions]
    base.update({
        "status": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL",
        "assertions": checks,
    })
    return base


def _evaluate_assertion(payload: Any, assertion: dict[str, Any]) -> dict[str, Any]:
    path = str(assertion.get("path", ""))
    value, found = _get_path(payload, path)
    op = str(assertion.get("op", "exists"))
    expected = assertion.get("expected")
    passed = found and _compare(value, op, expected)
    return {
        "path": path,
        "op": op,
        "expected": expected,
        "actual": value if found else None,
        "status": "PASS" if passed else "FAIL",
    }

