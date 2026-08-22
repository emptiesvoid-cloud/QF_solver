import json
from types import SimpleNamespace

import pytest

from solveur.core.errors import InputValidationError
from solveur.verification.traceability import (
    FormulaRegistry,
    QualificationRegistry,
    _declared_scope_names,
    model_traceability_summary,
    qualification_readiness,
    scope_for_model,
)


def test_tet4_scope_has_no_orphan_requirement():
    report = qualification_readiness("tet4-linear-static")
    assert report.status == "PASS"
    assert report.requirement_count == report.covered_requirement_count
    assert report.orphan_requirements == ()
    assert report.missing_paths == ()
    assert report.formula_count == 6
    assert report.covered_formula_count == 6
    assert report.orphan_formulas == ()
    assert report.formula_issues == ()
    data = report.to_dict()
    assert data["scope"] == "tet4-linear-static"
    assert all(set(check) == {"id", "status", "detail"} for check in data["checks"])


def test_all_controlled_formulas_are_linked_by_requirements():
    registry = QualificationRegistry()
    linked = {
        formula
        for requirement in registry.requirements.values()
        for formula in requirement.get("formulas", [])
    }
    formulas = FormulaRegistry()
    report = formulas.validate(sorted(linked), set(registry.requirements))
    assert set(formulas.formulas) == linked
    assert report.status == "PASS"
    assert report.covered_count == 61
    assert report.issues == ()


def test_development_scope_cannot_be_reported_ready():
    report = qualification_readiness("material-nonlinear")
    assert report.status == "FAIL"
    assert report.scope_status == "development"
    assert any(check.identifier == "SCOPE-CANDIDATE" and check.status == "FAIL" for check in report.checks)


def test_total_lagrangian_candidate_scope_has_complete_internal_evidence():
    report = qualification_readiness("tet4-total-lagrangian")

    assert report.status == "PASS"
    assert report.scope_status == "candidate"
    assert report.orphan_requirements == ()
    assert report.missing_paths == ()


def test_total_lagrangian_structural_v2_is_candidate_after_review():
    report = qualification_readiness("tet4-total-lagrangian-structural-v2")

    assert report.status == "PASS"
    assert report.scope_status == "candidate"
    assert report.orphan_requirements == ()
    assert report.missing_paths == ()


def test_readiness_fails_for_orphan_requirement(tmp_path):
    registry = tmp_path / "requirements.json"
    registry.write_text(
        json.dumps(
            {
                "scopes": {"candidate": {"status": "candidate", "requirements": ["REQ-X-001", "REQ-X-404"]}},
                "requirements": [
                    {
                        "id": "REQ-X-001",
                        "design": ["README.md"],
                        "code": ["src/solveur/core/solver.py"],
                        "functions": ["LinearStaticSolver.solve"],
                        "tests": [],
                        "artifacts": ["examples/tet4_static.json"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    report = QualificationRegistry(registry).readiness("candidate")
    assert report.status == "FAIL"
    assert set(report.orphan_requirements) == {"REQ-X-001", "REQ-X-404"}


def test_registry_errors_are_typed(tmp_path):
    with pytest.raises(InputValidationError):
        QualificationRegistry(tmp_path / "missing.json")
    with pytest.raises(InputValidationError, match="Unknown qualification scope"):
        qualification_readiness("not-a-scope")


def test_mechanical_requirement_needs_independent_reference(tmp_path):
    registry = tmp_path / "requirements.json"
    registry.write_text(
        json.dumps(
            {
                "scopes": {"candidate": {"status": "candidate", "requirements": ["REQ-SOL-X"]}},
                "requirements": [
                    {
                        "id": "REQ-SOL-X",
                        "design": ["README.md"],
                        "code": ["src/solveur/core/solver.py"],
                        "tests": ["tests/unit/test_solver.py"],
                        "artifacts": ["examples/tet4_static.json"],
                        "independent_references": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    report = QualificationRegistry(registry).readiness("candidate")
    assert report.status == "FAIL"
    assert report.missing_independent_references == ("REQ-SOL-X",)


def test_formula_traceability_detects_missing_symbol(tmp_path):
    registry = tmp_path / "requirements.json"
    formulas = tmp_path / "formulas.json"
    registry.write_text(
        json.dumps(
            {
                "scopes": {"candidate": {"status": "candidate", "requirements": ["REQ-SOL-X"]}},
                "requirements": [
                    {
                        "id": "REQ-SOL-X",
                        "design": ["README.md"],
                        "code": ["src/solveur/core/solver.py"],
                        "functions": ["LinearStaticSolver.solve"],
                        "tests": ["tests/unit/test_solver.py"],
                        "artifacts": ["examples/tet4_static.json"],
                        "independent_references": ["closed form"],
                        "formulas": ["FORM-X"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    formulas.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "formulas": [
                    {
                        "id": "FORM-X",
                        "requirement": "REQ-SOL-X",
                        "document": "README.md",
                        "section": "# QF_solver",
                        "code": ["src/solveur/core/solver.py"],
                        "functions": ["LinearStaticSolver.missing_symbol"],
                        "tests": ["tests/unit/test_solver.py"],
                        "reference_id": "REF-FEM-BATHE",
                        "reference": "docs/reference/references.md#ref-fem-bathe",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    report = QualificationRegistry(registry, formulas).readiness("candidate")
    assert report.status == "FAIL"
    assert report.covered_formula_count == 0
    assert any("missing function" in issue for issue in report.formula_issues)


def test_formula_traceability_detects_orphan_formula(tmp_path):
    registry = tmp_path / "requirements.json"
    formulas = tmp_path / "formulas.json"
    registry.write_text(
        json.dumps(
            {
                "scopes": {"candidate": {"status": "candidate", "requirements": ["REQ-X"]}},
                "requirements": [
                    {
                        "id": "REQ-X",
                        "design": ["README.md"],
                        "code": ["src/solveur/core/solver.py"],
                        "functions": ["LinearStaticSolver.solve"],
                        "tests": ["tests/unit/test_solver.py"],
                        "artifacts": ["examples/tet4_static.json"],
                        "formulas": ["FORM-MISSING"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    formulas.write_text(json.dumps({"schema_version": 1, "formulas": []}), encoding="utf-8")
    report = QualificationRegistry(registry, formulas).readiness("candidate")
    assert report.status == "FAIL"
    assert report.orphan_formulas == ("FORM-MISSING",)


def test_formula_registry_rejects_invalid_controlled_inputs(tmp_path) -> None:
    missing = tmp_path / "missing-formulas.json"
    with pytest.raises(InputValidationError, match="Cannot load formula registry"):
        FormulaRegistry(missing)

    invalid_schema = tmp_path / "invalid-schema.json"
    invalid_schema.write_text(json.dumps({"schema_version": 2, "formulas": []}), encoding="utf-8")
    with pytest.raises(InputValidationError, match="schema_version"):
        FormulaRegistry(invalid_schema)

    missing_list = tmp_path / "missing-list.json"
    missing_list.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
    with pytest.raises(InputValidationError, match="formula list"):
        FormulaRegistry(missing_list)

    invalid_ids = tmp_path / "invalid-ids.json"
    invalid_ids.write_text(json.dumps({"schema_version": 1, "formulas": [{}, {}]}), encoding="utf-8")
    with pytest.raises(InputValidationError, match="invalid or duplicate"):
        FormulaRegistry(invalid_ids)


def test_formula_record_reports_all_missing_traceability_links() -> None:
    issues = FormulaRegistry._record_issues(
        {
            "requirement": "REQ-UNKNOWN",
            "document": "missing-document.md",
            "section": "# Missing",
            "code": ["missing-code.py"],
            "functions": ["Example.missing_function"],
            "tests": ["missing-test.py"],
            "reference_id": "REF-MISSING",
            "reference": "missing-reference.md#REF-MISSING",
        },
        {"REQ-KNOWN"},
    )

    assert "unknown requirement 'REQ-UNKNOWN'" in issues
    assert "missing document 'missing-document.md'" in issues
    assert "missing code path" in issues
    assert "missing test path" in issues
    assert "missing function Example.missing_function" in issues
    assert "missing reference 'missing-reference.md#REF-MISSING'" in issues


def test_formula_record_reports_empty_required_fields() -> None:
    issues = FormulaRegistry._record_issues({}, set())
    assert {f"missing {field}" for field in ("document", "section", "code", "functions", "tests", "reference_id", "reference")} <= set(issues)


def test_scope_declarations_and_mapping_tolerate_invalid_data(tmp_path) -> None:
    invalid_registry = tmp_path / "invalid-registry.json"
    invalid_registry.write_text("not json", encoding="utf-8")
    assert _declared_scope_names(invalid_registry) == ()

    model = SimpleNamespace(
        analysis=SimpleNamespace(type="linear_static"),
        elements=[SimpleNamespace(type="TET4")],
        materials=(),
    )
    assert scope_for_model(model) == "tet4-linear-static"


@pytest.mark.parametrize(
    ("analysis", "elements", "expected"),
    [
        ("nonlinear_static", ["TET4"], "material-nonlinear"),
        ("modal", ["TET4"], "tet4-modal"),
        ("transient_dynamic", ["TET4"], "tet4-transient-dynamic"),
        ("harmonic_response", ["TET4"], "tet4-harmonic-response"),
        ("modal", ["TET10"], "tet10-modal"),
        ("transient_dynamic", ["TET10"], "tet10-transient-dynamic"),
        ("harmonic_response", ["TET10"], "tet10-harmonic-response"),
        ("harmonic_response", ["MITC4"], "mitc4-harmonic-response"),
        ("modal", ["MITC4"], "mitc4-modal"),
        ("transient_dynamic", ["MITC4"], "mitc4-transient-dynamic"),
        ("harmonic_response", ["MITC3"], "mitc3-harmonic-response"),
        ("modal", ["MITC3"], "mitc3-modal"),
        ("transient_dynamic", ["MITC3"], "mitc3-transient-dynamic"),
        ("linear_static", ["TET4"], "tet4-linear-static"),
        ("linear_static", ["TET10"], "tet10-linear-static"),
        ("linear_static", ["MITC4"], "mitc4-linear-static"),
        ("linear_static", ["MITC3"], "mitc3-linear-static"),
        ("linear_static", ["BEAM2"], "beam2-linear-static"),
        ("geometric_nonlinear_static", ["TET4"], "tet4-total-lagrangian-structural-v2"),
        ("modal", ["TET4", "TET10"], "linear-dynamics"),
        ("linear_static", ["TET4", "MITC4"], None),
    ],
)
def test_model_scope_mapping(analysis: str, elements: list[str], expected: str | None):
    model = SimpleNamespace(
        analysis=SimpleNamespace(type=analysis),
        elements=[SimpleNamespace(type=element) for element in elements],
    )
    assert scope_for_model(model) == expected
    summary = model_traceability_summary(model)
    if expected is None:
        assert summary["status"] == "FAIL"
        assert summary["scope"] == "unscoped"
    else:
        assert summary["scope"] == expected


@pytest.mark.parametrize("analysis", ["modal", "transient_dynamic", "harmonic_response"])
def test_beam_and_discrete_dynamic_scopes_are_not_hidden_in_generic_scope(analysis: str):
    beam = SimpleNamespace(
        analysis=SimpleNamespace(type=analysis),
        elements=[SimpleNamespace(type="BEAM2")],
        materials={},
        springs=(),
        concentrated_masses=(),
    )
    discrete = SimpleNamespace(
        analysis=SimpleNamespace(type=analysis),
        elements=[],
        materials={},
        springs=(object(),),
        concentrated_masses=(),
    )
    assert scope_for_model(beam) == "beam2-linear-dynamics"
    assert scope_for_model(discrete) == "discrete-linear-dynamics"


def test_mitc3_laminate_static_scope_is_explicit() -> None:
    model = SimpleNamespace(
        analysis=SimpleNamespace(type="linear_static"),
        elements=[SimpleNamespace(type="MITC3", material="laminate")],
        materials={"laminate": {"type": "shell_laminate"}},
    )
    assert scope_for_model(model) == "mitc3-laminate-static"
