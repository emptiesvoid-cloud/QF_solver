from __future__ import annotations

import json
import copy
from pathlib import Path
from typing import Callable

import pytest

from solveur.api import run_vnv_study
from solveur.core.errors import InputValidationError
from solveur.verification.vnv_schema import VnvResultLoader, VnvStudyLoader
from tests.helpers.vnv import build_vnv_study


def test_vnv_study_generates_markdown_convergence_and_manifest(tmp_path: Path) -> None:
    study = build_vnv_study(tmp_path)
    output = tmp_path / "evidence"

    run = run_vnv_study(study, output)

    assert run.automated_verdict == "PASS"
    assert run.owner_decision == "pending"
    assert run.status == "PENDING_REVIEW"
    assert run.convergence[0]["observed_order"] == pytest.approx(2.0)
    assert run.convergence[0]["monotonic"] is True
    assert len(run.artifacts) == 19
    assert (output / "comparison.json").is_file()
    assert (output / "convergence.png").stat().st_size > 1000
    assert (output / "vnv_manifest.json").is_file()
    assert (output / "inputs" / "study.json").is_file()
    assert (output / "inputs" / "h3_reference.json").is_file()
    report = (output / "study_report.md").read_text(encoding="utf-8")
    assert "Quentin Farinazzo" in report
    assert "auto-revue" in report
    assert "![Deformee QF_solver]" in report
    assert "VTU reference" in report
    manifest = json.loads((output / "vnv_manifest.json").read_text(encoding="utf-8"))
    assert manifest["study_id"] == "VNV-TET4-TEST-001"
    assert manifest["owner_decision"] == "pending"
    assert len(manifest["source_inputs"]) == 7


def test_vnv_accepted_self_review_is_explicit_and_does_not_override_checks(tmp_path: Path) -> None:
    accepted = build_vnv_study(tmp_path / "accepted", decision="accepted")
    accepted_run = run_vnv_study(accepted, tmp_path / "accepted_output")
    assert accepted_run.status == "ACCEPTED"
    assert accepted_run.study.validation["independence"] == "not_independent"
    accepted_report = (tmp_path / "accepted_output" / "study_report.md").read_text(encoding="utf-8")
    assert "- [x] Decision, date et commentaires renseignes" in accepted_report

    failed = build_vnv_study(tmp_path / "failed", decision="accepted", qf_error_scale=2.0)
    failed_run = run_vnv_study(failed, tmp_path / "failed_output")
    assert failed_run.automated_verdict == "FAIL"
    assert failed_run.status == "FAIL"


def test_vnv_missing_required_deformations_is_an_acceptance_failure(tmp_path: Path) -> None:
    study = build_vnv_study(tmp_path, include_artifacts=False, deformation_requirement="finest")
    run = run_vnv_study(study, tmp_path / "output")
    assert run.automated_verdict == "FAIL"
    assert sum(check["id"].startswith("ART-") for check in run.checks) == 4
    assert all(check["status"] == "FAIL" for check in run.checks if check["id"].startswith("ART-"))


def test_vnv_rejects_unit_mismatch_and_false_independence(tmp_path: Path) -> None:
    wrong_units = build_vnv_study(tmp_path / "units", qf_unit="mm")
    with pytest.raises(InputValidationError, match="Unit mismatch"):
        run_vnv_study(wrong_units, tmp_path / "units_output")

    wrong_review = build_vnv_study(tmp_path / "review", validation_mode="independent_review")
    with pytest.raises(InputValidationError, match="identical"):
        VnvStudyLoader().load(wrong_review)


def test_vnv_accepts_a_genuinely_independent_reviewer(tmp_path: Path) -> None:
    study = build_vnv_study(
        tmp_path,
        validation_mode="independent_review",
        validator_name="Mechanical Reviewer",
    )
    loaded = VnvStudyLoader().load(study)
    assert loaded.validation["independence"] == "independent"


def test_vnv_study_requires_decreasing_mesh_sizes(tmp_path: Path) -> None:
    study = build_vnv_study(tmp_path)
    data = json.loads(study.read_text(encoding="utf-8"))
    data["levels"][1]["characteristic_size"] = 0.5
    study.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(InputValidationError, match="coarse to fine"):
        VnvStudyLoader().load(study)


def _set(path: tuple[object, ...], value: object) -> Callable[[dict[str, object]], None]:
    def mutate(data: dict[str, object]) -> None:
        target: object = data
        for key in path[:-1]:
            target = target[key]  # type: ignore[index]
        target[path[-1]] = value  # type: ignore[index]

    return mutate


def _duplicate(path: tuple[object, ...]) -> Callable[[dict[str, object]], None]:
    def mutate(data: dict[str, object]) -> None:
        target: object = data
        for key in path:
            target = target[key]  # type: ignore[index]
        target.append(copy.deepcopy(target[0]))  # type: ignore[attr-defined,index]

    return mutate


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda data: data.update({"unknown": True}), "unsupported fields"),
        (_set(("schema_version",), 2), "schema_version"),
        (_set(("title",), ""), "non-empty string"),
        (_set(("reference", "version"), "A_RENSEIGNER"), "placeholder"),
        (_set(("acceptance", "deformation_requirement"), "sometimes"), "must be none"),
        (_set(("validation", "mode"), "peer"), "validation.mode"),
        (_set(("validation", "decision"), "maybe"), "validation.decision"),
        (_set(("validation", "decision"), "accepted"), "validation.date"),
        (_set(("quantities", 0, "metric"), "ratio"), "Quantity metric"),
        (_set(("quantities", 0, "limit"), 0.0), "strictly positive"),
        (_set(("quantities", 0, "absolute_floor"), -1.0), "non-negative"),
        (_set(("quantities", 0, "id"), "UPPER"), "invalid identifier"),
        (_duplicate(("quantities",)), "Duplicate V&V quantity"),
        (_duplicate(("levels",)), "Duplicate V&V mesh level"),
        (_set(("levels", 1, "characteristic_size"), 0.4), "unique"),
        (_set(("convergence", 0, "quantity"), "unknown"), "Invalid or duplicate"),
        (_set(("quantities",), []), "cannot be empty"),
        (_set(("levels",), {}), "JSON array"),
    ],
)
def test_vnv_study_schema_rejects_malformed_protocols(
    tmp_path: Path,
    mutation: Callable[[dict[str, object]], None],
    message: str,
) -> None:
    study = build_vnv_study(tmp_path)
    data = json.loads(study.read_text(encoding="utf-8"))
    mutation(data)
    study.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(InputValidationError, match=message):
        VnvStudyLoader().load(study)


def test_vnv_reservations_require_comments_and_completed_decisions_require_dates(tmp_path: Path) -> None:
    study = build_vnv_study(tmp_path)
    data = json.loads(study.read_text(encoding="utf-8"))
    data["validation"].update(
        {"decision": "accepted_with_reservations", "date": "2026-07-13", "comments": ""}
    )
    study.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(InputValidationError, match="requires explicit"):
        VnvStudyLoader().load(study)


def test_vnv_convergence_needs_three_levels(tmp_path: Path) -> None:
    study = build_vnv_study(tmp_path)
    data = json.loads(study.read_text(encoding="utf-8"))
    data["levels"] = data["levels"][:2]
    study.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(InputValidationError, match="at least three"):
        VnvStudyLoader().load(study)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda data: data.update({"unknown": True}), "unsupported fields"),
        (_set(("schema_version",), 2), "schema_version"),
        (_set(("case_id",), "OTHER-CASE"), "does not match"),
        (_set(("producer", "name"), "Other"), "producer must be"),
        (_set(("units_system",), "MM-N"), "does not match study"),
        (_set(("quantities",), {}), "cannot be empty"),
        (_set(("quantities", "tip_uz", "value"), float("nan")), "must be finite"),
        (_set(("mesh", "nodes"), -1), "non-negative"),
        (_set(("visualization", "deformation_scale"), 0), "strictly positive"),
        (_set(("artifacts",), {"Bad Key": "field.vtu"}), "Invalid artifact key"),
    ],
)
def test_vnv_normalized_result_rejects_invalid_evidence(
    tmp_path: Path,
    mutation: Callable[[dict[str, object]], None],
    message: str,
) -> None:
    study_path = build_vnv_study(tmp_path)
    study = VnvStudyLoader().load(study_path)
    result_path = study.levels[0].qf_result
    data = json.loads(result_path.read_text(encoding="utf-8"))
    mutation(data)
    result_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(InputValidationError, match=message):
        VnvResultLoader().load(result_path, study=study, role="qf")


def test_vnv_result_reports_missing_and_malformed_json(tmp_path: Path) -> None:
    study_path = build_vnv_study(tmp_path)
    study = VnvStudyLoader().load(study_path)
    with pytest.raises(InputValidationError, match="Cannot read"):
        VnvResultLoader().load(tmp_path / "missing.json", study=study, role="qf")
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(InputValidationError, match="Malformed JSON"):
        VnvResultLoader().load(malformed, study=study, role="qf")


def test_vnv_visualization_metadata_must_match(tmp_path: Path) -> None:
    study = build_vnv_study(tmp_path)
    data = json.loads((tmp_path / "references" / "h2_reference.json").read_text(encoding="utf-8"))
    data["visualization"]["deformation_scale"] = 20.0
    data["visualization"]["field"] = "von_mises"
    data["visualization"]["view"] = "front"
    (tmp_path / "references" / "h2_reference.json").write_text(json.dumps(data), encoding="utf-8")
    run = run_vnv_study(study, tmp_path / "output")
    visual = [check for check in run.checks if check["id"].startswith("VIS-h2")]
    assert {check["status"] for check in visual} == {"FAIL"}
    assert run.automated_verdict == "FAIL"


def test_vnv_declared_artifact_must_exist(tmp_path: Path) -> None:
    study = build_vnv_study(tmp_path)
    (tmp_path / "results" / "h1_qf.png").unlink()
    with pytest.raises(InputValidationError, match="artifact does not exist"):
        run_vnv_study(study, tmp_path / "output")


def test_vnv_can_generate_a_scalar_only_report_without_convergence(tmp_path: Path) -> None:
    study = build_vnv_study(tmp_path, include_artifacts=False, deformation_requirement="none")
    data = json.loads(study.read_text(encoding="utf-8"))
    data["convergence"] = []
    data["quantities"][0]["metric"] = "absolute_error"
    data["quantities"][0]["limit"] = 2.0
    study.write_text(json.dumps(data), encoding="utf-8")
    run = run_vnv_study(study, tmp_path / "output")
    assert run.convergence == []
    assert "convergence_plot" not in run.files
    report = (tmp_path / "output" / "study_report.md").read_text(encoding="utf-8")
    assert "Aucun critere de convergence" in report
    assert "Aucun artefact graphique" in report
