import pytest

from solveur.api import InputValidationError as PublicInputValidationError
from solveur.api import RunVerdict
from solveur.core.errors import ExitCode, QualificationGateError
from solveur.core.qualification import (
    enforce_qualification_policy,
    model_maturity,
    model_qualification_domain,
    qualification_summary,
    verification_profile,
)
from solveur.cli.verification import _verify_all_commands
from solveur.core.model import FiniteElementModel
from solveur.io.json_reader import JsonModelReader


def test_verification_profile_normalizes_policy():
    profile = verification_profile("qualification")
    assert profile.name == "qualification"
    assert profile.fail_on_warning is True
    assert profile.allow_experimental is False
    assert RunVerdict.PASS.value == "PASS"
    assert PublicInputValidationError is not None


def test_model_maturity_marks_nonlinear_as_experimental():
    model = JsonModelReader().from_dict(
        {
            "analysis": {"type": "nonlinear_static", "method": "newton_raphson", "load_steps": 2},
            "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
            "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "rubber"}],
            "materials": {"rubber": {"type": "nonlinear_isotropic_3d", "E": 1.0, "nu": 0.25, "hardening": 1.0}},
        }
    )
    maturity = model_maturity(model)
    assert maturity["overall"] == "experimental"
    assert maturity["analysis"] == "experimental"


def test_qualification_profile_blocks_experimental_maturity():
    model = JsonModelReader().from_dict(
        {
            "verification_profile": "qualification",
            "analysis": {"type": "nonlinear_static", "method": "newton_raphson", "load_steps": 2},
            "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
            "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "rubber"}],
            "materials": {"rubber": {"type": "nonlinear_isotropic_3d", "E": 1.0, "nu": 0.25, "hardening": 1.0}},
        }
    )
    summary = qualification_summary(object(), model)
    assert summary["status"] == "FAIL"
    assert "not allowed by qualification profile" in summary["blocking_errors"][0]

    with pytest.raises(QualificationGateError) as exc_info:
        enforce_qualification_policy(object(), model)
    assert exc_info.value.exit_code == ExitCode.QUALIFICATION_REJECTED
    assert exc_info.value.result is not None
    assert exc_info.value.summary["run_verdict"] == "FAIL"

    model.verification_profile = "engineering"
    engineering = qualification_summary(object(), model)
    assert engineering["status"] == "WARNING"
    assert "experimental" in engineering["warnings"][0]
    assert any("readiness PASS" in warning for warning in engineering["warnings"])


def test_qualification_verify_all_contains_coverage_typing_and_readiness():
    commands = _verify_all_commands("qualification", "tet4-linear-static")
    flattened = [" ".join(command) for command in commands]
    assert any("pytest --cov=solveur" in command for command in flattened)
    assert any("mypy" in command for command in flattened)
    assert any("check_p0_coverage.py" in command for command in flattened)
    assert any("qualification-readiness --scope tet4-linear-static" in command for command in flattened)
    assert any("qf_solver.py verify" in command and "--quick" not in command for command in flattened)


@pytest.mark.parametrize("profile", ["engineering", "strict", "qualification"])
def test_verify_all_core_pytest_excludes_generated_documentation_and_optional_campaigns(profile: str):
    commands = _verify_all_commands(profile, "tet4-linear-static")
    pytest_commands = [command for command in commands if command[1:3] == ["-m", "pytest"]]
    assert len(pytest_commands) == 1
    command = pytest_commands[0]
    assert "--ignore=tests/documentation" in command
    marker_index = command.index("-m", 3)
    assert command[marker_index + 1] == "not benchmark and not large"


def test_api_qualification_policy_rejects_non_si_model_built_without_json():
    model = FiniteElementModel.from_raw(
        analysis="linear_static",
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 1.0, "nu": 0.25}},
        units={"system": "custom", "length": "mm"},
        verification_profile="qualification",
    )
    summary = qualification_summary(object(), model)
    assert summary["status"] == "FAIL"
    assert any("SI unit system" in error for error in summary["blocking_errors"])


def test_tet4_qualification_domain_reports_material_and_numerical_bounds():
    model = FiniteElementModel.from_raw(
        analysis="linear_static",
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
    )
    domain = model_qualification_domain(model)
    assert domain["status"] == "PASS"
    assert domain["limits"]["poisson_ratio"] == {"minimum": 0.0, "maximum": 0.45}
    assert domain["limits"]["reduced_stiffness_condition_estimate_max"] == 1.0e12
    assert domain["materials"][0]["E"] == 210.0e9


def test_qualification_profile_rejects_tet4_outside_bounded_poisson_domain():
    model = FiniteElementModel.from_raw(
        analysis="linear_static",
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "nearly_incompressible"}],
        materials={"nearly_incompressible": {"type": "isotropic_3d", "E": 1.0e6, "nu": 0.49}},
        verification_profile="qualification",
    )
    summary = qualification_summary(object(), model)
    assert summary["status"] == "FAIL"
    assert summary["qualification_domain"]["status"] == "WARNING"
    assert any("0 <= nu <= 0.45" in error for error in summary["blocking_errors"])

    model.verification_profile = "engineering"
    engineering = qualification_summary(object(), model)
    assert engineering["status"] == "WARNING"
    assert any("Qualification domain violation" in warning for warning in engineering["warnings"])
