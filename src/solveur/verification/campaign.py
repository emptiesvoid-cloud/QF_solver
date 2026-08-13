"""Executable qualification campaigns for sovereign solver evidence."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from solveur.core.router import AnalysisRouter
from solveur.io.evidence_verifier import EvidenceBundleVerifier
from solveur.io.evidence_writer import EvidenceBundleWriter
from solveur.io.json_reader import JsonModelReader
from solveur.io.json_writer import JsonResultWriter
from solveur.mesh.validation import MeshValidator
from solveur.verification.analytical_references import Tet4StaticClosedFormOracle


INDEPENDENT_REFERENCE_TYPES = {"analytic", "equilibrium_closed_form", "third_party", "experimental"}


@dataclass(frozen=True)
class QualificationCase:
    """One manifest entry describing a model and its expected verdict."""

    id: str
    requirement: str
    input_path: Path
    mode: str = "solve"
    profile: str = "engineering"
    expected_status: str = "PASS"
    description: str = ""
    checks: tuple[dict[str, Any], ...] = ()
    replacement_candidate: bool = False
    accepted_use: str = ""


class QualificationCampaignRunner:
    """Run a manifest of cases and write a reproducible campaign summary."""

    def run(self, manifest_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
        manifest_file = Path(manifest_path).resolve()
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        cases = self._cases(manifest, manifest_file)
        rows = [self._run_case(case, output) for case in cases]
        status = "PASS" if all(row["passed"] for row in rows) else "FAIL"
        reference_summary = _reference_summary(rows)
        solved_rows = [row for row in rows if row["mode"] == "solve"]
        summary = {
            "campaign": manifest.get("campaign", manifest_file.stem),
            "description": manifest.get("description", ""),
            "status": status,
            "case_count": len(rows),
            "passed_count": sum(1 for row in rows if row["passed"]),
            "failed_count": sum(1 for row in rows if not row["passed"]),
            "replacement_candidate_count": sum(1 for row in rows if row["replacement_candidate"]),
            "replacement_ready_count": sum(1 for row in rows if row["replacement_ready"]),
            "reference_check_count": reference_summary["count"],
            "independent_reference_check_count": reference_summary["independent_count"],
            "reference_types": reference_summary["types"],
            "evidence_manifest_schema_version": 2,
            "evidence_bundle_count": len(solved_rows),
            "evidence_verified_count": sum(
                1 for row in solved_rows if row.get("evidence_verification", {}).get("status") == "PASS"
            ),
            "requirement_coverage": _requirement_coverage(rows),
            "cases": rows,
        }
        self._write_json(output / "qualification_campaign_summary.json", summary)
        (output / "qualification_campaign_summary.md").write_text(self._render_markdown(summary), encoding="utf-8")
        return summary

    def run_case(
        self,
        manifest_path: str | Path,
        case_id: str,
        output_dir: str | Path,
    ) -> dict[str, Any]:
        """Run one named controlled case without executing its whole campaign."""
        manifest_file = Path(manifest_path).resolve()
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        normalized = str(case_id).strip().upper()
        case = next(
            (item for item in self._cases(manifest, manifest_file) if item.id.upper() == normalized),
            None,
        )
        if case is None:
            available = ", ".join(item.id for item in self._cases(manifest, manifest_file))
            raise ValueError(f"Unknown qualification case {case_id!r}; available: {available}.")
        row = self._run_case(case, output)
        self._write_json(output / "qualification_case_summary.json", row)
        (output / "qualification_case_summary.md").write_text(
            self._render_case_markdown(row), encoding="utf-8"
        )
        return row

    @staticmethod
    def _cases(manifest: dict[str, Any], manifest_file: Path) -> list[QualificationCase]:
        default_profile = str(manifest.get("default_profile", "engineering"))
        raw_cases = manifest.get("cases", [])
        if not isinstance(raw_cases, list) or not raw_cases:
            raise ValueError("Qualification campaign manifest must define a non-empty cases list.")
        cases: list[QualificationCase] = []
        for index, raw in enumerate(raw_cases):
            if not isinstance(raw, dict):
                raise ValueError(f"Campaign case {index} must be an object.")
            case_id = str(raw.get("id", "")).strip()
            if not case_id:
                raise ValueError(f"Campaign case {index} must define a non-empty id.")
            input_value = raw.get("input")
            if not isinstance(input_value, str) or not input_value:
                raise ValueError(f"Campaign case {case_id} must define an input path.")
            cases.append(
                QualificationCase(
                    id=case_id,
                    requirement=str(raw.get("requirement", "")),
                    input_path=(manifest_file.parent / input_value).resolve(),
                    mode=str(raw.get("mode", "solve")).lower(),
                    profile=str(raw.get("profile", default_profile)).lower(),
                    expected_status=str(raw.get("expected_status", "PASS")).upper(),
                    description=str(raw.get("description", "")),
                    checks=tuple(raw.get("checks", [])),
                    replacement_candidate=bool(raw.get("replacement_candidate", False)),
                    accepted_use=str(raw.get("accepted_use", "")),
                )
            )
        return cases

    def _run_case(self, case: QualificationCase, output_dir: Path) -> dict[str, Any]:
        if case.mode == "check_mesh":
            return self._run_mesh_case(case, output_dir)
        if case.mode != "solve":
            raise ValueError(f"Unsupported qualification case mode {case.mode!r} for {case.id}.")
        model = JsonModelReader().read(case.input_path)
        model.verification_profile = case.profile
        result = AnalysisRouter().solve(model)
        case_dir = output_dir / _safe_name(case.id)
        EvidenceBundleWriter().write(model=model, result=result, directory=case_dir, input_path=case.input_path)
        evidence_report = EvidenceBundleVerifier().verify(case_dir)
        result_data = result.to_dict()
        qualification = result_data.get("qualification_summary", {})
        actual_status = str(qualification.get("status", result.status)).upper()
        payload = {
            "result": result_data,
            "qualification": qualification,
            "evidence_verification": evidence_report.to_dict(),
            "_model": model,
        }
        return self._case_row(
            case,
            actual_status,
            evidence_dir=case_dir,
            payload=payload,
            extra={"qualification": qualification, "evidence_verification": evidence_report.to_dict()},
            infrastructure_errors=tuple(evidence_report.errors) if evidence_report.status == "FAIL" else (),
        )

    def _run_mesh_case(self, case: QualificationCase, output_dir: Path) -> dict[str, Any]:
        model = JsonModelReader().read(case.input_path)
        model.verification_profile = case.profile
        report = MeshValidator().validate(model)
        case_dir = output_dir / _safe_name(case.id)
        case_dir.mkdir(parents=True, exist_ok=True)
        report_path = case_dir / "mesh_report.json"
        JsonResultWriter().write(report, report_path)
        payload = {"mesh_report": report.to_dict()}
        return self._case_row(
            case,
            report.status,
            evidence_dir=case_dir,
            payload=payload,
            extra={"mesh_report": str(report_path)},
        )

    @staticmethod
    def _case_row(
        case: QualificationCase,
        actual_status: str,
        *,
        evidence_dir: Path,
        payload: dict[str, Any],
        extra: dict[str, Any],
        infrastructure_errors: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        check_results = [_evaluate_check(check, payload) for check in case.checks]
        failed_checks = [check for check in check_results if check["status"] == "FAIL"]
        readiness = _replacement_readiness(case, actual_status, check_results, failed_checks, payload)
        passed = actual_status == case.expected_status and not failed_checks and (
            not case.replacement_candidate or readiness["ready"]
        ) and not infrastructure_errors
        return {
            "id": case.id,
            "requirement": case.requirement,
            "description": case.description,
            "accepted_use": case.accepted_use,
            "mode": case.mode,
            "profile": case.profile,
            "input": str(case.input_path),
            "expected_status": case.expected_status,
            "actual_status": actual_status,
            "passed": passed,
            "replacement_candidate": case.replacement_candidate,
            "replacement_ready": readiness["ready"],
            "readiness_blockers": readiness["blockers"],
            "checks": check_results,
            "check_count": len(check_results),
            "failed_check_count": len(failed_checks),
            "infrastructure_errors": list(infrastructure_errors),
            "evidence_dir": str(evidence_dir),
            **extra,
        }

    @staticmethod
    def _write_json(path: Path, data: dict[str, Any]) -> None:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @staticmethod
    def _render_markdown(summary: dict[str, Any]) -> str:
        lines = [
            f"# Campagne qualification - {summary['campaign']}",
            "",
            f"Statut: **{summary['status']}**",
            "",
            f"Cas candidats remplacement prets: {summary['replacement_ready_count']}/"
            f"{summary['replacement_candidate_count']}",
            f"Comparaisons a reference: {summary['reference_check_count']} ({', '.join(summary['reference_types'])})",
            f"References independantes: {summary['independent_reference_check_count']}",
            f"Dossiers de preuve v2 verifies: {summary['evidence_verified_count']}/{summary['evidence_bundle_count']}",
            "",
            "| Cas | Exigence | Candidat | Pret | Mode | Profil | Attendu | Obtenu | Resultat |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for row in summary["cases"]:
            verdict = "PASS" if row["passed"] else "FAIL"
            lines.append(
                f"| {row['id']} | {row['requirement']} | {_yes_no(row['replacement_candidate'])} | "
                f"{_yes_no(row['replacement_ready'])} | {row['mode']} | {row['profile']} | "
                f"{row['expected_status']} | {row['actual_status']} | {verdict} |"
                )
            for check in row.get("checks", []):
                expected = check.get("expected", "")
                tolerance = check.get("tolerance")
                reference = check.get("reference_type") or check.get("reference") or ""
                if tolerance is not None:
                    expected = f"{expected} tol={tolerance}"
                if reference:
                    expected = f"{expected} ref={reference}"
                lines.append(
                    f"| - critere `{check['path']}` | {check['op']} | | | "
                    f"{expected} | {check.get('actual', '')} | {check['status']} |"
                )
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _render_case_markdown(row: dict[str, Any]) -> str:
        """Render a concise standalone evidence record for one public case."""
        lines = [
            f"# Cas de qualification - {row['id']}",
            "",
            f"Statut: **{'PASS' if row['passed'] else 'FAIL'}**",
            "",
            "| Champ | Valeur |",
            "| --- | --- |",
            f"| Exigence | {row['requirement']} |",
            f"| Mode | {row['mode']} |",
            f"| Profil | {row['profile']} |",
            f"| Verdict attendu | {row['expected_status']} |",
            f"| Verdict obtenu | {row['actual_status']} |",
            f"| Dossier de preuve | `{row['evidence_dir']}` |",
            "",
            "| Critere | Operateur | Valeur | Attendu | Verdict |",
            "| --- | --- | --- | --- | --- |",
        ]
        for check in row["checks"]:
            lines.append(
                f"| `{check['path']}` | {check['op']} | {check.get('actual', '')} | "
                f"{check.get('expected', '')} | {check['status']} |"
            )
        lines.append("")
        return "\n".join(lines)


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._") or "case"


def _replacement_readiness(
    case: QualificationCase,
    actual_status: str,
    check_results: list[dict[str, Any]],
    failed_checks: list[dict[str, Any]],
    payload: dict[str, Any],
) -> dict[str, Any]:
    if not case.replacement_candidate:
        return {"ready": False, "blockers": []}
    blockers: list[str] = []
    if case.expected_status != "PASS":
        blockers.append("replacement candidates must expect PASS.")
    if actual_status != "PASS":
        blockers.append(f"actual status is {actual_status}, not PASS.")
    if failed_checks:
        blockers.append(f"{len(failed_checks)} acceptance check(s) failed.")
    maturity = _optional_path(payload, "qualification.maturity.overall")
    if maturity != "stable":
        blockers.append(f"maturity is {maturity!r}, not 'stable'.")
    if case.profile not in {"strict", "qualification"}:
        blockers.append("replacement candidates must run with strict or qualification profile.")
    independent_references = [
        check
        for check in check_results
        if check["status"] == "PASS" and str(check.get("reference_type", "")) in INDEPENDENT_REFERENCE_TYPES
    ]
    if not independent_references:
        allowed = ", ".join(sorted(INDEPENDENT_REFERENCE_TYPES))
        blockers.append(f"replacement candidates require at least one independent reference: {allowed}.")
    return {"ready": not blockers, "blockers": blockers}


def _evaluate_check(check: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    path = str(check.get("path", ""))
    op = str(check.get("op", "exists"))
    formula = str(check.get("reference_formula", ""))
    expected = _reference_formula(formula, payload) if formula else check.get("expected")
    tolerance = check.get("tolerance")
    reference_type = check.get("reference_type", "analytic" if formula else "")
    try:
        actual = _resolve_path(payload, path)
        passed = _compare(actual, op, expected, tolerance)
        status = "PASS" if passed else "FAIL"
        message = ""
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        actual = None
        status = "FAIL"
        message = str(exc)
    return {
        "path": path,
        "op": op,
        "expected": expected,
        "tolerance": tolerance,
        "reference": check.get("reference", ""),
        "reference_type": reference_type,
        "reference_formula": formula,
        "actual": actual,
        "status": status,
        "message": message,
    }


def _resolve_path(payload: dict[str, Any], path: str) -> Any:
    if not path:
        raise ValueError("check path must not be empty.")
    value: Any = payload
    for part in path.split("."):
        if isinstance(value, dict):
            if part not in value:
                raise KeyError(f"{path!r} missing component {part!r}.")
            value = value[part]
        elif isinstance(value, list):
            value = value[int(part)]
        else:
            raise TypeError(f"{path!r} cannot descend into {type(value).__name__}.")
    return value


def _optional_path(payload: dict[str, Any], path: str) -> Any:
    try:
        return _resolve_path(payload, path)
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _compare(actual: Any, op: str, expected: Any, tolerance: Any = None) -> bool:
    if op == "exists":
        return actual is not None
    if op == "equals":
        return actual == expected
    if op == "not_equals":
        return actual != expected
    if op == "less_equal":
        return float(actual) <= float(expected)
    if op == "greater_equal":
        return float(actual) >= float(expected)
    if op == "between":
        low, high = expected
        return float(low) <= float(actual) <= float(high)
    if op == "abs_error":
        return abs(float(actual) - float(expected)) <= _required_tolerance(op, tolerance)
    if op == "relative_error":
        error = abs(float(actual) - float(expected))
        reference = max(abs(float(expected)), 1.0e-30)
        return error / reference <= _required_tolerance(op, tolerance)
    raise ValueError(f"Unsupported qualification check operator {op!r}.")


def _reference_formula(name: str, payload: dict[str, Any]) -> float:
    if name == "tet4_unit_uniaxial_ux_displacement":
        return _tet4_unit_uniaxial_reference(payload)["ux"]
    if name == "tet4_unit_uniaxial_von_mises":
        return _tet4_unit_uniaxial_reference(payload)["von_mises"]
    if name == "tet4_unit_body_force_ux_displacement":
        return _tet4_unit_body_force_reference(payload)["ux"]
    if name == "tet4_unit_first_shear_frequency_hz":
        return _tet4_unit_modal_reference(payload)["first_shear_frequency_hz"]
    if name == "tet4_unit_sdof_free_vibration_initial_energy":
        return _tet4_unit_sdof_dynamic_reference(payload)["initial_energy"]
    if name == "tet4_unit_sdof_free_vibration_frequency_hz":
        return _tet4_unit_sdof_dynamic_reference(payload)["frequency_hz"]
    if name == "tet4_unit_sdof_harmonic_static_amplitude":
        return _tet4_unit_sdof_harmonic_reference(payload, 0)["amplitude"]
    if name == "tet4_unit_sdof_harmonic_f1_amplitude":
        return _tet4_unit_sdof_harmonic_reference(payload, 1)["amplitude"]
    if name == "tet4_unit_sdof_harmonic_f1_phase_degrees":
        return _tet4_unit_sdof_harmonic_reference(payload, 1)["phase_degrees"]
    if name == "tet4_unit_sdof_harmonic_f2_amplitude":
        return _tet4_unit_sdof_harmonic_reference(payload, 2)["amplitude"]
    if name == "tet4_unit_sdof_harmonic_f2_phase_degrees":
        return _tet4_unit_sdof_harmonic_reference(payload, 2)["phase_degrees"]
    if name == "mitc4_edge_membrane_force_x":
        return _mitc4_edge_membrane_force_x(payload)
    raise ValueError(f"Unsupported reference formula {name!r}.")


def _tet4_unit_uniaxial_reference(payload: dict[str, Any]) -> dict[str, float]:
    model = payload["_model"]
    element = _canonical_unit_tet4_element(model, "tet4_unit_uniaxial")
    force = sum(load.value for load in model.loads if load.node == element.nodes[1] and load.dof == "UX")
    if force == 0.0:
        raise ValueError("tet4_unit_uniaxial formulas require a non-zero UX load on local node 1.")
    material = model.materials[element.material]
    young = float(material["E"])
    poisson = float(material["nu"])
    return Tet4StaticClosedFormOracle(young, poisson).constrained_uniaxial(force)


def _tet4_unit_body_force_reference(payload: dict[str, Any]) -> dict[str, float]:
    model = payload["_model"]
    element = _canonical_unit_tet4_element(model, "tet4_unit_body_force")
    body_force_x = 0.0
    for load in model.distributed_loads:
        if getattr(load, "type", "") != "body_force":
            continue
        if getattr(load, "coordinate_system", "global") != "global":
            raise ValueError("tet4_unit_body_force formulas require global body-force coordinates.")
        targets = getattr(load, "elements", None)
        if targets is None or 0 in targets:
            body_force_x += float(load.value[0])
    if body_force_x == 0.0:
        raise ValueError("tet4_unit_body_force formulas require a non-zero X body force.")
    material = model.materials[element.material]
    young = float(material["E"])
    poisson = float(material["nu"])
    oracle = Tet4StaticClosedFormOracle(young, poisson)
    return {"ux": oracle.consistent_body_force_displacement(body_force_x)}


def _tet4_unit_modal_reference(payload: dict[str, Any]) -> dict[str, float]:
    model = payload["_model"]
    element = _canonical_unit_tet4_element(model, "tet4_unit_modal")
    material = model.materials[element.material]
    young = float(material["E"])
    poisson = float(material["nu"])
    density = float(material.get("density", material.get("rho", 0.0)))
    if density <= 0.0:
        raise ValueError("tet4_unit_modal formulas require positive density.")
    shear_modulus = young / (2.0 * (1.0 + poisson))
    omega2 = 10.0 * shear_modulus / density
    return {"first_shear_frequency_hz": float(math.sqrt(omega2) / (2.0 * math.pi))}


def _tet4_unit_sdof_dynamic_reference(payload: dict[str, Any]) -> dict[str, float]:
    model = payload["_model"]
    element = _canonical_unit_tet4_element(model, "tet4_unit_sdof_free_vibration")
    _require_unit_sdof(model, element, "tet4_unit_sdof_free_vibration")
    stiffness, mass = _tet4_unit_sdof_stiffness_mass(model.materials[element.material], "tet4_unit_sdof_free_vibration")
    displacement = _initial_displacement(model, element.nodes[1], "UX")
    if displacement == 0.0:
        raise ValueError("tet4_unit_sdof_free_vibration formulas require a non-zero initial UX displacement.")
    omega = math.sqrt(stiffness / mass)
    return {
        "frequency_hz": float(omega / (2.0 * math.pi)),
        "initial_energy": float(0.5 * stiffness * displacement**2),
    }


def _tet4_unit_sdof_harmonic_reference(payload: dict[str, Any], frequency_index: int) -> dict[str, float]:
    model = payload["_model"]
    element = _canonical_unit_tet4_element(model, "tet4_unit_sdof_harmonic")
    _require_unit_sdof(model, element, "tet4_unit_sdof_harmonic")
    stiffness, mass = _tet4_unit_sdof_stiffness_mass(model.materials[element.material], "tet4_unit_sdof_harmonic")
    force = sum(load.value for load in model.loads if load.node == element.nodes[1] and load.dof == "UX")
    if force == 0.0:
        raise ValueError("tet4_unit_sdof_harmonic formulas require a non-zero UX load on local node 1.")
    frequencies = list(model.analysis.parameters.get("frequencies_hz", []))
    if frequency_index >= len(frequencies):
        raise ValueError("tet4_unit_sdof_harmonic formulas require explicit frequencies_hz.")
    frequency = float(frequencies[frequency_index])
    omega = 2.0 * math.pi * frequency
    alpha = float(model.analysis.parameters.get("rayleigh_alpha", 0.0))
    beta = float(model.analysis.parameters.get("rayleigh_beta", 0.0))
    damping = alpha * mass + beta * stiffness
    response = force / complex(stiffness - omega**2 * mass, omega * damping)
    return {
        "real": float(response.real),
        "imag": float(response.imag),
        "amplitude": float(abs(response)),
        "phase_degrees": float(math.degrees(math.atan2(response.imag, response.real))),
    }


def _require_unit_sdof(model: Any, element: Any, formula_name: str) -> None:
    expected_free = [(element.nodes[1], "UX")]
    if _free_dof_keys(model) != expected_free:
        raise ValueError(f"{formula_name} formulas require only node 1 UX to be free.")


def _tet4_unit_sdof_stiffness_mass(material: dict[str, Any], formula_name: str) -> tuple[float, float]:
    young = float(material["E"])
    poisson = float(material["nu"])
    density = float(material.get("density", material.get("rho", 0.0)))
    if density <= 0.0:
        raise ValueError(f"{formula_name} formulas require positive density.")
    volume = 1.0 / 6.0
    constrained_modulus = young * (1.0 - poisson) / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
    return volume * constrained_modulus, density * volume / 10.0


def _free_dof_keys(model: Any) -> list[tuple[int, str]]:
    dofs = model.dof_manager()
    fixed: set[int] = set()
    for condition in model.fixed_dofs:
        for dof in condition.dofs:
            if dofs.has(condition.node, dof):
                fixed.add(dofs.index(condition.node, dof))
    free: list[tuple[int, str]] = []
    for node, node_dofs in dofs.node_dofs.items():
        for dof in node_dofs:
            if dofs.index(node, dof) not in fixed:
                free.append((node, dof))
    return free


def _initial_displacement(model: Any, node: int, dof: str) -> float:
    entries = model.analysis.parameters.get("initial_displacements", [])
    if not isinstance(entries, list):
        return 0.0
    total = 0.0
    for entry in entries:
        if isinstance(entry, dict) and int(entry.get("node", -1)) == int(node) and str(entry.get("dof", "")).upper() == dof:
            total += float(entry.get("value", 0.0))
    return total


def _canonical_unit_tet4_element(model: Any, formula_name: str) -> Any:
    if len(model.elements) != 1 or model.elements[0].type != "TET4":
        raise ValueError(f"{formula_name} formulas require one TET4 element.")
    element = model.elements[0]
    coords = model.nodes[list(element.nodes)]
    expected_coords = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    if not _nested_close(coords.tolist(), expected_coords, 1.0e-12):
        raise ValueError(f"{formula_name} formulas require the canonical unit tetrahedron.")
    return element


def _mitc4_edge_membrane_force_x(payload: dict[str, Any]) -> float:
    model = payload["_model"]
    if len(model.elements) != 1 or model.elements[0].type != "MITC4":
        raise ValueError("mitc4_edge_membrane_force_x requires one MITC4 element.")
    element = model.elements[0]
    coords = model.nodes[list(element.nodes)]
    x_max = max(float(coord[0]) for coord in coords)
    edge_nodes = [node for node in element.nodes if abs(float(model.nodes[node, 0]) - x_max) <= 1.0e-12]
    edge_length = max(float(coord[1]) for coord in coords) - min(float(coord[1]) for coord in coords)
    if edge_length <= 0.0:
        raise ValueError("mitc4_edge_membrane_force_x requires a positive edge length in Y.")
    force = sum(load.value for load in model.loads if load.node in edge_nodes and load.dof == "UX")
    return float(force / edge_length)


def _required_tolerance(op: str, tolerance: Any) -> float:
    if tolerance is None:
        raise ValueError(f"Operator {op!r} requires a tolerance.")
    value = float(tolerance)
    if value < 0.0:
        raise ValueError(f"Operator {op!r} requires a non-negative tolerance.")
    return value


def _nested_close(left: list[Any], right: list[Any], tolerance: float) -> bool:
    if len(left) != len(right):
        return False
    for left_item, right_item in zip(left, right):
        if isinstance(left_item, list) and isinstance(right_item, list):
            if not _nested_close(left_item, right_item, tolerance):
                return False
        elif abs(float(left_item) - float(right_item)) > tolerance:
            return False
    return True


def _requirement_coverage(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    coverage: dict[str, list[str]] = {}
    for row in rows:
        requirement = str(row.get("requirement", ""))
        if requirement:
            coverage.setdefault(requirement, []).append(str(row["id"]))
    return dict(sorted(coverage.items()))


def _reference_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    types: set[str] = set()
    count = 0
    independent_count = 0
    for row in rows:
        for check in row.get("checks", []):
            reference_type = str(check.get("reference_type", "")).strip()
            if reference_type:
                count += 1
                types.add(reference_type)
                if reference_type in INDEPENDENT_REFERENCE_TYPES:
                    independent_count += 1
    return {"count": count, "independent_count": independent_count, "types": sorted(types)}


def _yes_no(value: object) -> str:
    return "oui" if value else "non"
