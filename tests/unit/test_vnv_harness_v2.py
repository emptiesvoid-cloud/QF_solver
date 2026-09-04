"""Targeted WP04 contracts and representative legacy-route migrations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.core.router import AnalysisRouter
from solveur.compatibility import CompatibilityError
from solveur.verification.v2 import (
    VnvRunner,
    VnvSchemaError,
    canonical_json_bytes,
    canonical_sha256,
    load_cases,
    replay_case,
)


ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "qualification" / "0_2_7" / "vnv_v2" / "sample_cases.json"
SOURCE_SHA = "684c39c72191d43c53e1f21043dc746d213a561d"


def static_model() -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 210e9, "nu": 0.3}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": 1000.0}],
    )


def modal_model() -> FiniteElementModel:
    model = static_model()
    model.loads = []
    model.materials["steel"]["density"] = 7800.0
    model.analysis = {"type": "modal", "method": "eigh", "modes": 2}
    return model


def unknown_element_model() -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "PYRAMID5", "nodes": [0, 1, 2, 3, 0], "material": "steel"}],
        materials={"steel": {"type": "isotropic_3d", "E": 1.0, "nu": 0.3}},
    )


def test_case_catalog_validates_all_three_migrations() -> None:
    cases = load_cases(CASES)
    assert [case.case_id for case in cases] == [
        "WP04-STATIC-TET4-ANALYTICAL",
        "WP04-MODAL-TET4-INVARIANT",
        "WP04-PREFLIGHT-UNKNOWN-ELEMENT",
    ]


def test_schema_rejects_unknown_fields_and_unsupported_oracle() -> None:
    payload = json.loads(CASES.read_text(encoding="utf-8"))[0]
    payload["unknown"] = True
    with pytest.raises(VnvSchemaError, match="Unknown case fields"):
        load_case(payload)
    payload = json.loads(CASES.read_text(encoding="utf-8"))[0]
    payload["oracle"]["type"] = "GUESS"
    with pytest.raises(VnvSchemaError, match="Unsupported oracle type"):
        load_case(payload)


def load_case(payload: dict) -> object:
    from solveur.verification.v2 import validate_case

    return validate_case(payload)


def test_static_sample_runs_and_writes_machine_readable_evidence(tmp_path: Path) -> None:
    case = load_cases(CASES)[0]

    def execute(_case):
        result = solve_model(static_model()).to_dict()
        return {"observables": {"displacement_ux_node_1": result["displacements"][1]["dofs"]["UX"], "free_relative_residual": 0.0}}

    runner = VnvRunner(source_sha=SOURCE_SHA, environment={"python": "test", "platform": "test"})
    evidence = runner.run(case, execute)
    assert evidence.verdict == "PASS"
    assert evidence.source_sha == SOURCE_SHA
    assert evidence.input_digest == canonical_sha256(case.model_input)
    path = runner.write_evidence(evidence, tmp_path / "static.json")
    assert json.loads(path.read_text(encoding="utf-8"))["artifact_classification"] == "CONTROLLED_PROOF"


def test_modal_sample_uses_internal_invariant_oracle() -> None:
    case = load_cases(CASES)[1]

    def execute(_case):
        result = solve_model(modal_model())
        return {"observables": {"max_relative_residual": result.solver["max_relative_residual"], "mode_count": 2}}

    evidence = VnvRunner(source_sha=SOURCE_SHA, environment={"python": "test"}).run(case, execute)
    assert evidence.verdict == "PASS"
    assert evidence.oracle["type"] == "INTERNAL_INVARIANT"


def test_expected_failure_is_classified_without_silent_pass() -> None:
    case = load_cases(CASES)[2]

    def execute(_case):
        try:
            AnalysisRouter().solve(unknown_element_model())
        except CompatibilityError as exc:
            raise RuntimeError(exc.result.reason) from exc
        raise AssertionError("unknown element unexpectedly reached a solver")

    evidence = VnvRunner(source_sha=SOURCE_SHA, environment={"python": "test"}).run(case, execute)
    assert evidence.verdict == "EXPECTED_FAILURE_PASS"
    assert evidence.failure_reason == "UNKNOWN_ELEMENT"


def test_external_and_resource_verdicts_are_explicit() -> None:
    case = load_cases(CASES)[0]
    from solveur.verification.v2 import ExternalUnavailableError, ResourceLimitedError

    skipped = VnvRunner(source_sha=SOURCE_SHA).run(case, lambda _case: (_ for _ in ()).throw(ExternalUnavailableError("tool missing")))
    limited = VnvRunner(source_sha=SOURCE_SHA).run(case, lambda _case: (_ for _ in ()).throw(ResourceLimitedError("budget")))
    assert skipped.verdict == "SKIPPED_EXTERNAL_UNAVAILABLE"
    assert limited.verdict == "RESOURCE_LIMITED"


def test_replay_detects_source_input_and_result_mismatches() -> None:
    case = load_cases(CASES)[0]
    def execute(_case):
        return {"observables": {"displacement_ux_node_1": 2.122448979591837e-08}}
    runner = VnvRunner(source_sha=SOURCE_SHA, environment={"python": "test"})
    evidence = runner.run(case, execute)
    ok, status, replay = replay_case(case, execute, evidence, source_sha=SOURCE_SHA, environment={"python": "test"})
    assert (ok, status) == (True, "PASS")
    assert replay is not None
    assert replay_case(case, execute, evidence, source_sha="different")[1] == "SOURCE_SHA_MISMATCH"
    altered = dict(case.to_dict())
    altered["model_input"] = "fixture://changed"
    assert replay_case(altered, execute, evidence, source_sha=SOURCE_SHA)[1] == "INPUT_DIGEST_MISMATCH"
    def bad(_case):
        return {"observables": {"displacement_ux_node_1": 0.0}}
    assert replay_case(case, bad, evidence, source_sha=SOURCE_SHA)[1] == "RESULT_DIGEST_MISMATCH"


def test_canonical_serialization_is_stable() -> None:
    assert canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}\n'
