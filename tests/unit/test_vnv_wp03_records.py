"""Prospective WP03 contracts for identity, resume, failures and public records."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from solveur.verification.v2 import (
    ExecutionIdentity,
    ExecutionIdentityError,
    ExpectedFailureContract,
    InputFileIdentity,
    PublicBenchmarkRecord,
    PublicProjectionError,
    ResumeArtifact,
    SafeResumeRecord,
    VnvExecutionError,
    VnvRunner,
    VnvSchemaError,
    assess_safe_resume,
    load_cases,
    load_evidence_from_dict,
    load_prospective_cases,
    render_public_benchmark,
    validate_case,
)


ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "qualification" / "0_2_7" / "vnv_v2" / "sample_cases.json"
SOURCE_SHA = "c37179dae53604126aa6aa0d834770dfa4d2db37"


def _input(content: bytes = b"mesh-v1", *, availability: str = "AVAILABLE_AND_REPRODUCIBLE") -> InputFileIdentity:
    return InputFileIdentity.from_bytes(
        logical_role="mesh",
        logical_id="models/beam.mesh",
        content=content,
        provenance="REPOSITORY",
        availability_status=availability,
        public_identifier="models/beam.mesh",
    )


def _identity(**changes: object) -> ExecutionIdentity:
    values: dict[str, object] = {
        "source_sha": SOURCE_SHA,
        "case_contract_version": "0.2.11-v1",
        "units_resolved": True,
        "case_definition": {"case_id": "WP03-IDENTITY", "analysis": "linear_static"},
        "model_input": {"nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]},
        "input_files": (_input(),),
        "mesh": {"element": "BEAM2", "count": 1},
        "material_data": {"E": 210.0, "unit": "GPa"},
        "boundary_conditions": {"fixed_node": 0},
        "loads": {"node": 1, "force_N": 10.0},
        "solver_configuration": {"method": "direct"},
        "resolved_overrides": {},
        "reference_identity": {"id": "WP03-REF-01", "version": "1"},
        "reference_files": (),
        "tolerance_policy": {"relative": 1.0e-8, "unit": "dimensionless"},
        "metric_definitions": {"observable": "tip_displacement", "unit": "m"},
        "software_versions": {"qf_solver": "0.2.11-dev", "numpy": "2.x"},
        "numerical_environment": {"dtype": "float64", "backend": "scipy"},
        "rotation_configuration": {},
    }
    values.update(changes)
    return ExecutionIdentity(**values)  # type: ignore[arg-type]


def _schema2_case(*, expected_failure: object = None, solver_option: str = "direct") -> dict:
    case = load_cases(CASES)[0].to_dict()
    case["schema_version"] = 2
    case["expected_failure"] = expected_failure
    case["execution_identity"] = {
        "case_contract_version": "0.2.11-v1",
        "units_resolved": True,
        "input_files": [_input().to_dict()],
        "mesh": {"element": "TET4"},
        "material_data": {"E": 210.0e9},
        "boundary_conditions": {"fixed_nodes": [0, 2, 3]},
        "loads": {"node": 1, "dof": "UX", "value": 1000.0},
        "solver_configuration": {"method": solver_option},
        "resolved_overrides": {},
        "reference_identity": {"id": "WP03-STATIC-TET4-REF"},
        "reference_files": [],
        "tolerance_policy": {"policy_id": "WP03-ABS-01"},
        "metric_definitions": {"displacement_ux_node_1": "m"},
        "software_versions": {"qf_solver": "0.2.11-dev"},
        "numerical_environment": {"dtype": "float64"},
        "rotation_configuration": {},
    }
    return case


def test_execution_identity_is_canonical_and_excludes_operational_metadata() -> None:
    first = _identity()
    reordered = replace(
        first,
        case_definition={"analysis": "linear_static", "case_id": "WP03-IDENTITY"},
    )
    assert first.execution_key() == reordered.execution_key()
    assert first.execution_key(
        operational_context={"timestamp": "2026-10-05T12:00:00Z", "output_directory": "C:\\tmp\\run-a"}
    ) == first.execution_key(
        operational_context={"timestamp": "2027-01-01T00:00:00Z", "temp_path": "D:\\work\\run-b"}
    )
    assert first.execution_key() == ExecutionIdentity.from_dict(first.to_dict()).execution_key()
    with pytest.raises(ExecutionIdentityError, match="schema version"):
        ExecutionIdentity.from_dict({**first.to_dict(), "schema_version": 1.0})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mesh", {"element": "TET10", "count": 1}),
        ("material_data", {"E": 200.0, "unit": "GPa"}),
        ("solver_configuration", {"method": "iterative", "rtol": 1.0e-9}),
        ("tolerance_policy", {"relative": 1.0e-9, "unit": "dimensionless"}),
        ("reference_identity", {"id": "WP03-REF-02", "version": "1"}),
    ],
)
def test_scientifically_relevant_identity_changes_change_key(field: str, value: object) -> None:
    assert _identity().execution_key() != _identity(**{field: value}).execution_key()


def test_future_rotation_identity_slots_are_keyed_as_declared_data() -> None:
    assert _identity().execution_key() != _identity(
        rotation_configuration={"rotation_axis": [0.0, 0.0, 1.0], "speed_rad_s": 25.0}
    ).execution_key()


def test_actual_input_file_bytes_and_file_order_are_bound() -> None:
    original = _identity()
    assert original.execution_key() != replace(original, model_input={"nodes": [[0.0, 0.0, 0.0]]}).execution_key()
    changed = replace(original, input_files=(_input(b"mesh-v2"),))
    assert original.execution_key() != changed.execution_key()
    another_file = InputFileIdentity.from_bytes(
        logical_role="material",
        logical_id="materials/steel.json",
        content=b"{\"E\":210000000000}",
        provenance="EXTERNAL_VERSIONED",
        availability_status="AVAILABLE_AND_REPRODUCIBLE",
        public_identifier="materials/steel-v1.json",
    )
    ordered = replace(original, input_files=(_input(), another_file))
    reversed_order = replace(original, input_files=(another_file, _input()))
    assert ordered.execution_key() == reversed_order.execution_key()
    reference_a = InputFileIdentity.from_bytes(
        logical_role="oracle",
        logical_id="references/beam-reference.csv",
        content=b"f,u\n1,2\n",
        provenance="EXTERNAL_VERSIONED",
        availability_status="AVAILABLE_AND_REPRODUCIBLE",
    )
    reference_b = InputFileIdentity.from_bytes(
        logical_role="oracle",
        logical_id="references/beam-reference.csv",
        content=b"f,u\n1,3\n",
        provenance="EXTERNAL_VERSIONED",
        availability_status="AVAILABLE_AND_REPRODUCIBLE",
    )
    assert replace(original, reference_files=(reference_a,)).execution_key() != replace(
        original, reference_files=(reference_b,)
    ).execution_key()


def test_evidence_availability_is_explicit_but_not_part_of_scientific_key() -> None:
    original = _identity()
    local_only = replace(original, input_files=(_input(availability="AVAILABLE_LOCAL_ONLY"),))
    assert original.execution_key() == local_only.execution_key()
    assert original.input_files[0].availability_status == "AVAILABLE_AND_REPRODUCIBLE"
    assert local_only.input_files[0].availability_status == "AVAILABLE_LOCAL_ONLY"
    missing = InputFileIdentity(
        logical_role="optional-oracle",
        logical_id="references/not-installed.csv",
        sha256=None,
        size_bytes=None,
        provenance="MISSING",
        availability_status="MISSING",
    )
    assert missing.to_dict()["sha256"] is None
    assert replace(original, reference_files=(missing,)).execution_key() != original.execution_key()


def test_operational_metadata_is_excluded_but_private_identity_paths_are_rejected() -> None:
    first = _identity(case_definition={"case_id": "A"})
    second = _identity(case_definition={"case_id": "A"})
    assert first.execution_key(operational_context={"timestamp": "t1", "output_dir": "C:\\tmp\\one"}) == second.execution_key(
        operational_context={"timestamp": "t2", "output_dir": "D:\\tmp\\two"}
    )
    assert first.execution_key() != _identity(case_definition={"case_id": "A", "timestamp": "scientific-time"}).execution_key()
    with pytest.raises(ExecutionIdentityError, match="Absolute local path"):
        _identity(case_definition={"model_path": "C:\\Users\\private\\model.json"})
    with pytest.raises(ExecutionIdentityError, match="resolved"):
        _identity(units_resolved=False)


def test_safe_resume_requires_identity_schema_and_all_artifact_hashes() -> None:
    content = b"result payload"
    artifact = ResumeArtifact("results/case.json", hashlib.sha256(content).hexdigest(), len(content))
    record = SafeResumeRecord(1, _identity().execution_key(), (artifact,))
    assert assess_safe_resume(
        record,
        current_execution_key=record.execution_key,
        artifact_bytes={artifact.logical_id: content},
    ).status == "REUSE"
    assert assess_safe_resume(
        record,
        current_execution_key="0" * 64,
        artifact_bytes={artifact.logical_id: content},
    ).status == "REEXECUTE"
    assert assess_safe_resume(
        record,
        current_execution_key=record.execution_key,
        artifact_bytes={},
    ).status == "REEXECUTE"
    assert assess_safe_resume(
        record,
        current_execution_key=record.execution_key,
        artifact_bytes={artifact.logical_id: b"corrupted"},
    ).status == "REEXECUTE"
    invalid_schema = {**record.to_dict(), "schema_version": 99}
    assert assess_safe_resume(
        invalid_schema,
        current_execution_key=record.execution_key,
        artifact_bytes={artifact.logical_id: content},
    ).status == "REFUSE_RESUME"
    assert assess_safe_resume(
        {**record.to_dict(), "unexpected": True},
        current_execution_key=record.execution_key,
        artifact_bytes={artifact.logical_id: content},
    ).status == "REFUSE_RESUME"
    assert assess_safe_resume(
        record,
        current_execution_key=record.execution_key,
        artifact_bytes=None,  # type: ignore[arg-type]
    ).status == "REFUSE_RESUME"
    assert assess_safe_resume(
        record,
        current_execution_key=record.execution_key,
        artifact_bytes={artifact.logical_id: content},
        compatible_schema_versions=1,  # type: ignore[arg-type]
    ).status == "REFUSE_RESUME"
    with pytest.raises(ValueError, match="schema"):
        SafeResumeRecord.from_dict({**record.to_dict(), "schema_version": 1.0})


def test_schema2_case_emits_execution_key_and_rejects_changed_resume_identity() -> None:
    case = validate_case(_schema2_case())
    evidence = VnvRunner(source_sha=SOURCE_SHA).run(
        case,
        lambda _case: {"observables": {"displacement_ux_node_1": 2.122448979591837e-08}},
    )
    assert evidence.execution_key is not None
    assert evidence.identity_schema_version == 1
    changed_case = validate_case(_schema2_case(solver_option="iterative"))
    from solveur.verification.v2 import replay_case

    accepted, reason, _ = replay_case(
        changed_case,
        lambda _case: {"observables": {"displacement_ux_node_1": 2.122448979591837e-08}},
        evidence,
        source_sha=SOURCE_SHA,
    )
    assert not accepted
    assert reason == "EXECUTION_KEY_MISMATCH"


def test_schema2_expected_failure_matches_full_contract_not_arbitrary_exception() -> None:
    expected_type = f"{VnvExecutionError.__module__}.{VnvExecutionError.__qualname__}"
    expectation = {
        "expected_stage": "assembly",
        "expected_error_type": expected_type,
        "expected_error_code": "UNSUPPORTED_CONFIG",
        "expected_reason": "discrete preflight required",
        "optional_message_pattern": "preflight",
    }
    case = validate_case(_schema2_case(expected_failure=expectation))
    expected = VnvRunner(source_sha=SOURCE_SHA).run(
        case,
        lambda _case: (_ for _ in ()).throw(
            VnvExecutionError(
                stage="assembly",
                error_code="UNSUPPORTED_CONFIG",
                reason="discrete preflight required",
            )
        ),
    )
    assert expected.verdict == "EXPECTED_FAILURE_PASS"
    wrong_type = VnvRunner(source_sha=SOURCE_SHA).run(
        case,
        lambda _case: (_ for _ in ()).throw(FileNotFoundError("discrete preflight required")),
    )
    assert wrong_type.verdict == "INVALID_EVIDENCE"
    wrong_code = VnvRunner(source_sha=SOURCE_SHA).run(
        case,
        lambda _case: (_ for _ in ()).throw(
            VnvExecutionError(stage="assembly", error_code="TIMEOUT", reason="discrete preflight required")
        ),
    )
    assert wrong_code.verdict == "INVALID_EVIDENCE"
    unexpected_success = VnvRunner(source_sha=SOURCE_SHA).run(
        case,
        lambda _case: {"observables": {"displacement_ux_node_1": 2.122448979591837e-08}},
    )
    assert unexpected_success.verdict == "FAIL"


def test_schema1_cases_and_evidence_remain_readable() -> None:
    legacy_case = load_cases(CASES)[2]
    assert legacy_case.schema_version == 1
    assert isinstance(legacy_case.expected_failure, str)
    evidence = VnvRunner(source_sha=SOURCE_SHA).run(
        load_cases(CASES)[0], lambda _case: {"observables": {"displacement_ux_node_1": 2.122448979591837e-08}}
    )
    historical_payload = evidence.to_dict()
    assert "execution_key" not in historical_payload
    assert "identity_schema_version" not in historical_payload
    loaded = load_evidence_from_dict(historical_payload)
    assert loaded.execution_key is None
    assert loaded.source_sha == SOURCE_SHA


def test_public_projection_is_stable_and_does_not_promote_maturity() -> None:
    source = _input().to_dict()
    record = {
        "record_schema_version": 1,
        "benchmark_id": "GYRO-FOUNDATION-PLACEHOLDER",
        "source_sha": SOURCE_SHA,
        "execution_key": _identity().execution_key(),
        "numerical_status": "PASS",
        "metrics": {"residual": 1.0e-12, "frequency_hz": 12.5},
        "limitations": ["Scope remains experimental."],
        "provenance": [source],
        "evidence_availability": "AVAILABLE_AND_REPRODUCIBLE",
        "maturity_status": "EXPERIMENTAL",
        "maturity_authority": "explicit owner decision",
        "maturity_decision_id": "QF0211-DECISION-EXAMPLE",
        "evidence_link": "qualification/0_2_11/example-evidence.json",
    }
    parsed = PublicBenchmarkRecord.from_dict(record)
    assert parsed.numerical_status == "PASS"
    assert parsed.maturity_status == "EXPERIMENTAL"
    assert render_public_benchmark(parsed) == render_public_benchmark(dict(reversed(list(record.items()))))
    public_json = json.dumps(parsed.to_dict(), sort_keys=True)
    assert "C:\\Users" not in public_json
    with pytest.raises(PublicProjectionError, match="non-public/unknown"):
        PublicBenchmarkRecord.from_dict({**record, "local_artifact_path": "C:\\private\\evidence.json"})
    with pytest.raises(PublicProjectionError, match="Absolute local path"):
        PublicBenchmarkRecord.from_dict({**record, "evidence_link": "C:\\private\\evidence.json"})
    with pytest.raises(PublicProjectionError, match="Absolute local path"):
        PublicBenchmarkRecord.from_dict(
            {**record, "limitations": ["Local fixture at C:\\Users\\private\\model.json"]}
        )
    with pytest.raises(PublicProjectionError, match="Absolute local path"):
        PublicBenchmarkRecord.from_dict(
            {**record, "limitations": ["Local fixture at /home/runner/private/model.json"]}
        )


def test_expected_failure_v2_rejects_legacy_free_text_contract() -> None:
    with pytest.raises(VnvSchemaError, match="structured object"):
        validate_case(_schema2_case(expected_failure="UNKNOWN_ELEMENT"))
    with pytest.raises(VnvSchemaError, match="expected_failure is missing fields"):
        ExpectedFailureContract.from_dict({"expected_stage": "assembly"})
    missing_expectation = _schema2_case()
    del missing_expectation["expected_failure"]
    with pytest.raises(VnvSchemaError, match="explicitly declare expected_failure"):
        validate_case(missing_expectation)
    with pytest.raises(VnvSchemaError, match="must explicitly use schema_version 2"):
        load_prospective_cases(CASES)


def test_public_projection_rejects_coerced_schema_versions() -> None:
    record = {
        "benchmark_id": "WP03-CASE",
        "source_sha": SOURCE_SHA,
        "execution_key": _identity().execution_key(),
        "numerical_status": "PASS",
        "metrics": {},
        "limitations": ["Bounded scope."],
        "provenance": [_input().to_dict()],
        "evidence_availability": "AVAILABLE_AND_REPRODUCIBLE",
        "maturity_status": "EXPERIMENTAL",
        "maturity_authority": "owner record",
        "maturity_decision_id": "DECISION-01",
        "evidence_link": "qualification/0_2_11/example.json",
    }
    for invalid_version in (True, 1.0, "1"):
        with pytest.raises(PublicProjectionError, match="integer 1"):
            PublicBenchmarkRecord.from_dict({**record, "record_schema_version": invalid_version})
