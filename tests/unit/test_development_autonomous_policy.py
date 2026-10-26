from __future__ import annotations

import importlib.util
import base64
import hashlib
import json
import math
import sys
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "development_autonomous.py"
SPEC = importlib.util.spec_from_file_location("development_autonomous", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

PLUGIN_PATH = SCRIPT_PATH.with_name("development_autonomous_pytest_plugin.py")
PLUGIN_SPEC = importlib.util.spec_from_file_location("development_autonomous_pytest_plugin", PLUGIN_PATH)
assert PLUGIN_SPEC is not None and PLUGIN_SPEC.loader is not None
PLUGIN = importlib.util.module_from_spec(PLUGIN_SPEC)
sys.modules[PLUGIN_SPEC.name] = PLUGIN
PLUGIN_SPEC.loader.exec_module(PLUGIN)


def _policy() -> dict:
    return MODULE.load_policy()


def test_policy_registers_only_owner_authorized_worktrees_and_keeps_qualification_separate() -> None:
    policy = _policy()
    assert policy["mode"] == "DEVELOPMENT_AUTONOMOUS"
    assert {"d01", "c01", "e01"}.issubset(policy["worktrees"])
    assert set(policy["worktrees"]).issubset({"d01", "c01", "e01", "hex8sri"})
    assert policy["worktrees"]["d01"]["attempt_limit_per_nodeid"] == 3
    assert policy["worktrees"]["d01"]["development_mandate_id"] == "DEVELOPMENT_AUTONOMOUS-FEM-2026-10-24-v2-d01"
    assert policy["worktrees"]["d01"]["node_attempt_ledger"]["path"] == "node-attempt-ledger-d01-v2.json"
    assert policy["worktrees"]["d01"]["node_attempt_ledger"]["predecessor"]["sha256"] == (
        "5a6f9693e3649e2269625eb9baeb6bf53c6f2fda89ccc6011f508922b808bbc2"
    )
    assert policy["worktrees"]["c01"]["attempt_limit_per_nodeid"] == 3
    assert policy["worktrees"]["e01"]["mode"] == "math_non_fem"
    assert policy["worktrees"]["d01"]["allowed_nodeids"] == list(MODULE.D01_NATIVE_NODEIDS)
    assert {
        name: policy["worktrees"]["d01"]["budgets"][name]
        for name in MODULE.D01_OWNER_BUDGETS
    } == MODULE.D01_OWNER_BUDGETS
    assert policy["worktrees"]["d01"]["attempt_limits_per_nodeid"] == {
        MODULE.D01_NATIVE_NODEIDS[0]: 1,
        MODULE.D01_NATIVE_NODEIDS[1]: 1,
        MODULE.D01_NATIVE_NODEIDS[2]: 3,
    }
    assert "QUALIFICATION_RELEASE" not in policy["worktrees"]


@pytest.mark.parametrize(
    ("field", "increased_value"),
    [("timeout_seconds", 181), ("rss_soft_limit_mib", 2049), ("output_total_limit_mib", 65)],
)
def test_d01_policy_rejects_budget_expansion_beyond_owner_envelope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, increased_value: int
) -> None:
    policy = MODULE.load_policy()
    policy["worktrees"]["d01"]["budgets"][field] = increased_value
    if field == "output_total_limit_mib":
        policy["worktrees"]["d01"]["budgets"]["output_stream_limit_mib"] = 33
    candidate = tmp_path / "candidate-policy.json"
    candidate.write_text(json.dumps(policy), encoding="utf-8")
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)
    with pytest.raises(MODULE.PolicyError, match="must match the Owner envelope exactly"):
        MODULE.load_policy(candidate)


def test_each_worktree_has_a_separate_output_namespace(tmp_path: Path) -> None:
    assert MODULE._series_root(tmp_path, "fem_exploratory", "d01") == tmp_path / "worktrees" / "d01"
    assert MODULE._series_root(tmp_path, "fem_exploratory", "c01") == tmp_path / "worktrees" / "c01"
    assert MODULE._series_root(tmp_path, "fem_exploratory", "hex8sri") == tmp_path / "worktrees" / "hex8sri"
    assert MODULE._series_root(tmp_path, "math_non_fem", "e01") == tmp_path / "worktrees" / "e01"
    assert MODULE._series_root(tmp_path, "unit", None) == tmp_path / "standard" / "unit"
    with pytest.raises(MODULE.PolicyError, match="unknown worktree"):
        MODULE._series_root(tmp_path, "fem_exploratory", "e02")


def test_run_provenance_records_controller_and_runtime_identity() -> None:
    provenance = MODULE._controller_provenance()
    assert provenance["identity"]["root"] == str(MODULE.ROOT.resolve())
    assert set(provenance["sha256"]) == {"runner", "pytest_plugin", "policy"}
    assert all(len(digest) == 64 for digest in provenance["sha256"].values())
    assert provenance["runtime"]["python_version"]
    assert provenance["runtime"]["pytest_version"]


def test_standard_test_target_is_confined_to_its_scope() -> None:
    policy = _policy()
    target = "tests/unit/test_execution_contract.py::test_invalid_contract_is_rejected"
    assert MODULE.resolve_targets("unit", target, policy) == [target]
    with pytest.raises(MODULE.PolicyError, match="broad suites are not auto-enabled"):
        MODULE.resolve_targets("unit", None, policy)
    with pytest.raises(MODULE.PolicyError, match="exact pytest test-function nodeid"):
        MODULE.resolve_targets("unit", "tests/unit/test_execution_contract.py", policy)
    with pytest.raises(MODULE.PolicyError, match="below tests/unit"):
        MODULE.resolve_targets(
            "unit",
            "tests/integration/test_demonstration_api.py::test_outside_scope",
            policy,
        )
    with pytest.raises(MODULE.PolicyError, match="cannot traverse"):
        MODULE.resolve_targets("unit", "tests/unit/../../scripts/test_release.py::test_outside", policy)


def test_fem_scope_accepts_only_exact_registered_nodeids_and_worktree_pairs() -> None:
    policy = _policy()
    d01 = policy["worktrees"]["d01"]["allowed_nodeids"]
    for nodeid in d01:
        assert MODULE.resolve_targets("fem_exploratory", nodeid, policy, worktree_id="d01") == [nodeid]
    with pytest.raises(MODULE.PolicyError, match="exact nodeid"):
        MODULE.resolve_targets("fem_exploratory", d01[2].replace("[M3]", "[OTHER]"), policy, worktree_id="d01")
    with pytest.raises(MODULE.PolicyError, match="worktree e01 is not authorized"):
        MODULE.resolve_targets("fem_exploratory", d01[2], policy, worktree_id="e01")
    with pytest.raises(MODULE.PolicyError, match="registered worktree ID"):
        MODULE.resolve_targets("fem_exploratory", d01[2], policy)


def test_hex8sri_is_a_separate_manifest_bound_research_scope() -> None:
    policy = _policy()
    hex8sri = policy["worktrees"].get("hex8sri")
    if hex8sri is None:
        pytest.skip("HEX8-SRI registration is added only after final source manifests are frozen")
    assert hex8sri["mode"] == "fem_exploratory"
    assert hex8sri["attempt_limit_per_nodeid"] == 1
    assert hex8sri["allow_native_vv_skip_override"] is False
    assert hex8sri["require_clean_worktree"] is True
    assert hex8sri["execution_authorized"] is False
    assert len(hex8sri["allowed_nodeids"]) == 6
    assert set(hex8sri["case_manifests"]) == set(hex8sri["allowed_nodeids"])
    for nodeid in hex8sri["allowed_nodeids"]:
        assert MODULE.resolve_targets("fem_exploratory", nodeid, policy, worktree_id="hex8sri") == [nodeid]
    with pytest.raises(MODULE.PolicyError, match="exact nodeid"):
        MODULE.resolve_targets(
            "fem_exploratory",
            hex8sri["allowed_nodeids"][0].replace("hex8_standard_nu_0p3", "unregistered"),
            policy,
            worktree_id="hex8sri",
        )


def test_c01_scope_contains_only_registered_legacy_dimensional_and_mechanics_nodes() -> None:
    policy = _policy()
    c01 = policy["worktrees"]["c01"]["allowed_nodeids"]
    assert len(c01) == 18
    assert any("frozen_legacy_counterexample" in nodeid for nodeid in c01)
    assert any("dimensional_v1" in nodeid for nodeid in c01)
    assert any("contact_equilibrium_diagnostic" in nodeid for nodeid in c01)
    assert all(nodeid.startswith("tests/unit/") for nodeid in c01)
    with pytest.raises(MODULE.PolicyError, match="exact nodeid"):
        MODULE.resolve_targets("fem_exploratory", "tests/unit/test_wpc01_gf5a_fe_qualification.py::test_case", policy, worktree_id="c01")


def test_e01_scope_is_math_only_and_rejects_element_or_fem_targets() -> None:
    policy = _policy()
    e01 = policy["worktrees"]["e01"]["allowed_nodeids"]
    assert len(e01) == 15
    assert all("test_wp_e01" in nodeid for nodeid in e01)
    assert all(not any(word in nodeid.lower() for word in ("tet", "hex", "beam", "assembly", "fem")) for nodeid in e01)
    assert MODULE.resolve_targets("math_non_fem", e01[0], policy, worktree_id="e01") == [e01[0]]
    with pytest.raises(MODULE.PolicyError, match="exact nodeid"):
        MODULE.resolve_targets("math_non_fem", "tests/unit/test_wp_e01m_hencky_material_point.py::test_tet4_force_adapter_matches_uniform_pk1_reference", policy, worktree_id="e01")


def test_registered_worktree_identity_and_solver_source_are_verified() -> None:
    policy = _policy()
    target = policy["worktrees"]["e01"]["allowed_nodeids"][0]
    entry, root, source_root, identity, fingerprint = MODULE._registered_worktree("e01", target, policy)
    assert root == Path(entry["git_root"]).resolve()
    assert source_root == (root / "src").resolve()
    assert identity["branch"] == entry["branch"]
    assert identity["head"]
    assert len(fingerprint) == 64
    assert (source_root / "solveur" / "__init__.py").is_file()


def test_child_environment_is_noninteractive_and_cannot_inherit_qualification_switches(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    environment = MODULE.build_child_environment(
        tmp_path / "scratch",
        {
            "WPC02_AR_NATIVE_OWNER_GO_TOKEN": "qualification-token",
            "WPC02_AR_NATIVE_OWNER_GO_MANIFEST_SHA256": "digest",
            "QF_SOLVER_RUN_EVIDENCE": "1",
            "QF_FAKE_QUALIFICATION_OWNER": "1",
            "QF_WP_D01_BJ_SOURCE_SHA": "stale",
            "PYTEST_ADDOPTS": "--collect-only",
            "PYTEST_PLUGINS": "unexpected",
            "PYTHONHOME": "unexpected",
            "KEEP_ME": "yes",
        },
        source_root=source_root,
        d01_source_sha="a" * 40,
    )
    assert "WPC02_AR_NATIVE_OWNER_GO_TOKEN" not in environment
    assert "WPC02_AR_NATIVE_OWNER_GO_MANIFEST_SHA256" not in environment
    assert "QF_FAKE_QUALIFICATION_OWNER" not in environment
    assert environment["QF_SOLVER_RUN_EVIDENCE"] == "0"
    assert environment["QF_WP_D01_BJ_SOURCE_SHA"] == "a" * 40
    assert environment["PYTHONPATH"] == str(source_root)
    assert environment["QF_DEVELOPMENT_AUTONOMOUS"] == "1"
    assert "PYTEST_ADDOPTS" not in environment and "PYTEST_PLUGINS" not in environment
    assert "PYTHONHOME" not in environment and "PYTHONSTARTUP" not in environment
    assert environment["KEEP_ME"] == "yes"
    assert environment["TMP"] == str(tmp_path / "scratch")


def test_registered_command_is_fixed_to_one_target_and_checks_import_origin(tmp_path: Path) -> None:
    policy = _policy()
    target = policy["worktrees"]["d01"]["allowed_nodeids"][0]
    command = MODULE.build_pytest_command(
        "fem_exploratory",
        [target],
        tmp_path / "tmp",
        repository_root=Path(policy["worktrees"]["d01"]["root"]),
        source_root=Path(policy["worktrees"]["d01"]["root"]) / "src",
        allow_native_skip_override=True,
    )
    assert command[:3] == [sys.executable, "-B", "-c"]
    assert "wrong solveur import origin" in command[3]
    assert "QF_DEV_SOLVER_ORIGIN=" in command[3]
    assert command[-1] == target
    with pytest.raises(MODULE.PolicyError, match="one exact nodeid"):
        MODULE.build_pytest_command("fem_exploratory", [target, target], tmp_path / "tmp", source_root=tmp_path)


def test_d01_collect_only_command_is_non_fem_and_keeps_exact_node_gate(tmp_path: Path) -> None:
    policy = _policy()
    target = MODULE.D01_NATIVE_NODEIDS[0]
    command = MODULE.build_pytest_command(
        "fem_exploratory",
        [target],
        tmp_path / "tmp",
        repository_root=Path(policy["worktrees"]["d01"]["root"]),
        source_root=Path(policy["worktrees"]["d01"]["root"]) / "src",
        allow_native_skip_override=True,
        collect_only=True,
    )
    assert "--collect-only" in command
    assert command[-1] == target
    assert "ExactNodeGate" in command[3]


def test_d01_run_command_persists_record_property_payload_as_junit_xml(tmp_path: Path) -> None:
    policy = _policy()
    target = MODULE.D01_NATIVE_NODEIDS[2]
    junit_path = tmp_path / "output" / "pytest-results.xml"
    command = MODULE.build_pytest_command(
        "fem_exploratory",
        [target],
        tmp_path / "tmp",
        repository_root=Path(policy["worktrees"]["d01"]["root"]),
        source_root=Path(policy["worktrees"]["d01"]["root"]) / "src",
        allow_native_skip_override=True,
        junit_xml_path=junit_path,
    )
    assert f"--junitxml={junit_path.resolve()}" in command
    assert "--collect-only" not in command


def test_d01_junit_payload_is_required_and_bound_to_mesh_and_two_mode_counts(tmp_path: Path) -> None:
    target = MODULE.D01_NATIVE_NODEIDS[2]
    elements, free_dofs = 32, 192

    def nested_values(shape: list[int], scalar: object) -> object:
        if len(shape) == 1:
            return [scalar] * shape[0]
        return [nested_values(shape[1:], scalar) for _ in range(shape[0])]

    def exact_array(shape: list[int], dtype: str = "<f8") -> dict[str, object]:
        count = math.prod(shape)
        prefix, kind, size = dtype[0], dtype[1], int(dtype[2:])
        format_code = {("f", 8): "d", ("c", 16): "d"}[kind, size]
        scalar_count = count * (2 if kind == "c" else 1)
        raw = struct.pack(f"{prefix}{scalar_count}{format_code}", *([1.0] * scalar_count))
        identity = json.dumps(
            {"dtype": dtype, "shape": shape, "order": "C"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        values: object = nested_values(shape, 1.0)
        if kind == "c":
            values = {"real": values, "imag": nested_values(shape, 1.0)}
        return {
            "dtype": dtype,
            "shape": shape,
            "order": "C",
            "values": values,
            "raw_bytes_base64": base64.b64encode(raw).decode("ascii"),
            "raw_representation_sha256": hashlib.sha256(identity + b"\0" + raw).hexdigest(),
        }

    def csr_snapshot(size: int, data_value: float = 1.0) -> dict[str, object]:
        raw_arrays = {
            "data": ("<f8", [data_value] * size, struct.pack(f"<{size}d", *([data_value] * size))),
            "indices": ("<i4", list(range(size)), struct.pack(f"<{size}i", *range(size))),
            "indptr": ("<i4", list(range(size + 1)), struct.pack(f"<{size + 1}i", *range(size + 1))),
        }
        digest = hashlib.sha256()
        digest.update(json.dumps({"shape": [size, size]}, sort_keys=True).encode("ascii"))
        arrays: dict[str, object] = {}
        for name, (dtype, values, raw) in raw_arrays.items():
            digest.update(name.encode("ascii"))
            digest.update(dtype.encode("ascii"))
            digest.update(raw)
            arrays[name] = {
                "dtype": dtype,
                "values": values,
                "raw_bytes_base64": base64.b64encode(raw).decode("ascii"),
            }
        return {
            "format": "CSR_COPY_WITH_STORED_ORDER",
            "shape": [size, size],
            "nnz_stored": size,
            "arrays": arrays,
            "stored_representation_sha256": digest.hexdigest(),
        }

    frequencies = [0.0, *[float(index) for index in range(1, 6)]]
    frequency_raw = struct.pack("<6d", *frequencies)
    frequency_identity = json.dumps(
        {"dtype": "<f8", "shape": [6], "order": "C"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    frequency_snapshot = {
        **exact_array([6]),
        "values": frequencies,
        "raw_bytes_base64": base64.b64encode(frequency_raw).decode("ascii"),
        "raw_representation_sha256": hashlib.sha256(frequency_identity + b"\0" + frequency_raw).hexdigest(),
    }
    source_arrays = {
        "frequencies_hz": frequency_snapshot,
        "normalized_equilibrium_residuals": exact_array([6]),
        "reduced_force": exact_array([free_dofs]),
        "responses_full_free_complex": [exact_array([free_dofs], "<c16") for _ in range(6)],
    }
    source_operators = {name: csr_snapshot(free_dofs) for name in ("M", "K", "C_used_by_experiment")}

    def projected_payload(mode_count: int) -> dict[str, object]:
        return {
            "mesh_id": "M3",
            "source_sha": "f" * 40,
            "operator_identity": "operator-identity-v2",
            "mode_count": mode_count,
            "frozen_symmetry_threshold": 1.0e-12,
            "acceptance_verdict": "DIAGNOSTIC_ONLY_NOT_AN_ACCEPTANCE_OVERRIDE",
            "input_damping": csr_snapshot(free_dofs),
            "exact_numeric_arrays": {
                "mode_matrix": exact_array([free_dofs, mode_count]),
                "eigenvalues_rad2_s2": exact_array([mode_count]),
                "damping_times_modes": exact_array([free_dofs, mode_count]),
                "projected_mass": exact_array([mode_count, mode_count]),
                "projected_stiffness": exact_array([mode_count, mode_count]),
                "projected_mass_gram": exact_array([mode_count, mode_count]),
                "projected_damping": exact_array([mode_count, mode_count]),
                "expected_projected_rayleigh_from_cached_operators": exact_array([mode_count, mode_count]),
            },
        }

    def response_rows(corrected: bool) -> list[dict[str, object]]:
        rows = []
        for mode_count in (2, 4):
            for frequency in frequencies:
                row: dict[str, object] = {
                    "frequency_hz": frequency,
                    "mode_count": mode_count,
                    "tip_uy_m": {"real": 0.1, "imag": 0.02},
                    "relative_full_free_displacement_error": 0.1,
                    "relative_tip_amplitude_error": 0.05,
                    "tip_phase_error_rad": 0.01,
                    "normalized_free_equilibrium_residual": 1.0e-8,
                    "direct_reference_residual": 1.0e-10,
                    "energy": {
                        "average_input_power_W": 1.0,
                        "average_rayleigh_dissipation_W": 0.9,
                        "absolute_balance_gap_W": 0.1,
                    },
                }
                if corrected:
                    row.update(
                        {
                            "correction_error_ratio": 0.8,
                            "correction_error_ratio_status": "DEFINED",
                            "correction_degraded_error": False,
                            "wp_d01_diagnostics": {"symmetry_relative_error": 1.0e-14},
                        }
                    )
                else:
                    row["wp05_diagnostic"] = {"frequency_hz": frequency, "status": "computed"}
                rows.append(row)
        return rows

    properties = {
        "wp_d01_cg_source_operands_json": json.dumps(
            {
                "mesh": {"id": "M3", "elements": elements, "free_dofs": free_dofs},
                "source_sha": "f" * 40,
                "operator_identity": "operator-identity-v2",
                "operators": source_operators,
                "exact_numeric_arrays": source_arrays,
            }
        ),
        "wp_d01_cg_projected_damping_m2_json": json.dumps(projected_payload(2)),
        "wp_d01_cg_projected_damping_m4_json": json.dumps(projected_payload(4)),
        "wp_d01_bj_experimental_results_json": json.dumps(
            {
                "mesh": {"id": "M3", "elements": elements, "free_dofs": free_dofs},
                "source_sha": "f" * 40,
                "operator_identity": "operator-identity-v2",
                "retained_mode_counts": [2, 4],
                "qualification": "NOT_CERTIFIED",
                "c4_official_status": "NOT_EVALUATED_BY_DESIGN",
                "c4_complete_spectrum_captured": False,
                "frequencies_hz": frequencies,
                "responses": {"uncorrected": response_rows(False), "corrected": response_rows(True)},
            }
        ),
    }

    def write_xml(
        path: Path,
        items: dict[str, str],
        *,
        name: str | None = None,
        classname: str = "tests.verification.test_wp_d01_bj_wp05_native_experiment",
        skipped: bool = False,
        failed: bool = False,
    ) -> None:
        case = ET.Element(
            "testcase",
            classname=classname,
            name=name or target.split("::")[-1],
        )
        props = ET.SubElement(case, "properties")
        for name, value in items.items():
            ET.SubElement(props, "property", name=name, value=value)
        if skipped:
            ET.SubElement(case, "skipped", message="synthetic skip")
        if failed:
            ET.SubElement(case, "failure", message="synthetic pytest failure")
        suite = ET.Element(
            "testsuite",
            tests="1",
            errors="0",
            failures="1" if failed else "0",
            skipped="1" if skipped else "0",
        )
        suite.append(case)
        suites = ET.Element("testsuites")
        suites.append(suite)
        ET.ElementTree(suites).write(path, encoding="utf-8", xml_declaration=True)

    complete_xml = tmp_path / "complete.xml"
    write_xml(complete_xml, properties)
    expected_source_sha = "f" * 40
    complete, errors, metadata = MODULE._validate_d01_junit_payload(complete_xml, target, expected_source_sha)
    assert complete, errors
    assert metadata == {
        "mesh_id": "M3",
        "elements": 32,
        "free_dofs": 192,
        "property_names": list(properties),
        "response_rows_per_treatment": 12,
        "symmetry_threshold": 1.0e-12,
    }

    for invalid_grid in (
        [-1.0, 1.0, 2.0, 3.0, 4.0, 5.0],
        [0.0, 1.0, 2.0, 3.0, 4.0, 4.0],
        [0.0, 1.0, 2.0, 3.0, 4.0],
        [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
    ):
        assert not MODULE._valid_d01_experimental_frequency_grid(invalid_grid)
    assert MODULE._valid_d01_experimental_frequency_grid(frequencies)

    missing_xml = tmp_path / "missing.xml"
    write_xml(missing_xml, {key: value for key, value in properties.items() if key != "wp_d01_bj_experimental_results_json"})
    complete, errors, _metadata = MODULE._validate_d01_junit_payload(missing_xml, target, expected_source_sha)
    assert not complete and "every required numerical property" in errors[0]

    wrong_mesh = dict(properties)
    wrong_mesh["wp_d01_bj_experimental_results_json"] = json.dumps(
        {**json.loads(properties["wp_d01_bj_experimental_results_json"]), "mesh": {"id": "M2"}}
    )
    wrong_mesh_xml = tmp_path / "wrong-mesh.xml"
    write_xml(wrong_mesh_xml, wrong_mesh)
    complete, errors, _metadata = MODULE._validate_d01_junit_payload(wrong_mesh_xml, target, expected_source_sha)
    assert not complete and "mesh identity" in errors[0]

    wrong_node_xml = tmp_path / "wrong-node.xml"
    write_xml(wrong_node_xml, properties, classname="tests.other_module")
    complete, errors, _metadata = MODULE._validate_d01_junit_payload(wrong_node_xml, target, expected_source_sha)
    assert not complete and "exact requested nodeid" in errors[0]

    skipped_xml = tmp_path / "skipped.xml"
    write_xml(skipped_xml, properties, skipped=True)
    complete, errors, _metadata = MODULE._validate_d01_junit_payload(skipped_xml, target, expected_source_sha)
    assert not complete and "was skipped" in errors[0]

    failed_xml = tmp_path / "failed-but-diagnostic-complete.xml"
    write_xml(failed_xml, properties, failed=True)
    complete, errors, _metadata = MODULE._validate_d01_junit_payload(
        failed_xml, target, expected_source_sha, pytest_return_code=1
    )
    assert complete and not errors
    assert MODULE._d01_final_state("PYTEST_FAILED", complete) == "PYTEST_FAILED"
    complete, errors, _metadata = MODULE._validate_d01_junit_payload(
        failed_xml, target, expected_source_sha, pytest_return_code=0
    )
    assert not complete and "successful exit code" in errors[0]

    malformed_row = json.loads(properties["wp_d01_bj_experimental_results_json"])
    malformed_row["responses"]["uncorrected"][0] = None
    malformed = dict(properties)
    malformed["wp_d01_bj_experimental_results_json"] = json.dumps(malformed_row)
    malformed_xml = tmp_path / "malformed-row.xml"
    write_xml(malformed_xml, malformed)
    complete, errors, _metadata = MODULE._validate_d01_junit_payload(malformed_xml, target, expected_source_sha)
    assert not complete and "non-object response row" in errors[0]

    empty_arrays_payload = json.loads(properties["wp_d01_bj_experimental_results_json"])
    empty_arrays_payload["responses"]["uncorrected"] = [
        {"mode_count": count} for count in [2] * 6 + [4] * 6
    ]
    empty_arrays_properties = dict(properties)
    empty_arrays_properties["wp_d01_bj_experimental_results_json"] = json.dumps(empty_arrays_payload)
    empty_arrays_xml = tmp_path / "empty-numerical-rows.xml"
    write_xml(empty_arrays_xml, empty_arrays_properties)
    complete, errors, _metadata = MODULE._validate_d01_junit_payload(empty_arrays_xml, target, expected_source_sha)
    assert not complete and "frequency grid" in errors[0]

    bad_array_payload = json.loads(properties["wp_d01_cg_source_operands_json"])
    bad_array_payload["exact_numeric_arrays"]["reduced_force"]["raw_representation_sha256"] = "0" * 64
    bad_array_properties = dict(properties)
    bad_array_properties["wp_d01_cg_source_operands_json"] = json.dumps(bad_array_payload)
    bad_array_xml = tmp_path / "bad-numeric-array-hash.xml"
    write_xml(bad_array_xml, bad_array_properties)
    complete, errors, _metadata = MODULE._validate_d01_junit_payload(bad_array_xml, target, expected_source_sha)
    assert not complete and "exact-byte hashes" in errors[0]

    empty_roundtrip = json.loads(properties["wp_d01_cg_source_operands_json"])
    empty_roundtrip["exact_numeric_arrays"]["reduced_force"]["values"] = []
    empty_roundtrip_properties = dict(properties)
    empty_roundtrip_properties["wp_d01_cg_source_operands_json"] = json.dumps(empty_roundtrip)
    empty_roundtrip_xml = tmp_path / "empty-json-values.xml"
    write_xml(empty_roundtrip_xml, empty_roundtrip_properties)
    complete, errors, _metadata = MODULE._validate_d01_junit_payload(
        empty_roundtrip_xml, target, expected_source_sha
    )
    assert not complete and "exact-byte hashes" in errors[0]

    wrong_source = dict(properties)
    wrong_source["wp_d01_cg_projected_damping_m4_json"] = json.dumps(
        {**json.loads(properties["wp_d01_cg_projected_damping_m4_json"]), "source_sha": "e" * 40}
    )
    wrong_source_xml = tmp_path / "wrong-source-identity.xml"
    write_xml(wrong_source_xml, wrong_source)
    complete, errors, _metadata = MODULE._validate_d01_junit_payload(
        wrong_source_xml, target, expected_source_sha
    )
    assert not complete and "bind to the exact D01 source" in errors[0]

    wrong_source_operator = dict(properties)
    source_operator_payload = json.loads(properties["wp_d01_cg_source_operands_json"])
    source_operator_payload["operator_identity"] = "different-operator-identity"
    wrong_source_operator["wp_d01_cg_source_operands_json"] = json.dumps(source_operator_payload)
    wrong_source_operator_xml = tmp_path / "wrong-source-operator-identity.xml"
    write_xml(wrong_source_operator_xml, wrong_source_operator)
    complete, errors, _metadata = MODULE._validate_d01_junit_payload(
        wrong_source_operator_xml, target, expected_source_sha
    )
    assert not complete and "do not share one operator identity" in errors[0]

    for property_name in (
        "wp_d01_cg_projected_damping_m2_json",
        "wp_d01_cg_projected_damping_m4_json",
    ):
        mismatched_damping = dict(properties)
        projection = json.loads(properties[property_name])
        projection["input_damping"] = csr_snapshot(free_dofs, data_value=2.0)
        mismatched_damping[property_name] = json.dumps(projection)
        mismatched_damping_xml = tmp_path / f"mismatched-damping-{property_name}.xml"
        write_xml(mismatched_damping_xml, mismatched_damping)
        complete, errors, _metadata = MODULE._validate_d01_junit_payload(
            mismatched_damping_xml, target, expected_source_sha
        )
        assert not complete and "does not exactly match source C_used_by_experiment" in errors[0]


def test_d01_incomplete_numerical_archive_cannot_leave_a_pass_status() -> None:
    assert MODULE._d01_final_state("PASS", True) == "PASS"
    assert MODULE._d01_final_state("PASS", False) == "RESULT_ARCHIVE_INCOMPLETE"
    assert MODULE._d01_final_state("PASS", None) == "RESULT_ARCHIVE_INCOMPLETE"
    assert MODULE._d01_final_state("FAIL", False) == "FAIL"
    assert MODULE._d01_final_state("TIMEOUT", None) == "TIMEOUT"


def test_exact_node_plugin_lifts_only_the_approved_native_skip() -> None:
    native_skip = SimpleNamespace(name="skip", kwargs={"reason": "tier NATIVE_AUTH_REQUIRED: offline route"})
    unrelated_skip = SimpleNamespace(name="skip", kwargs={"reason": "unrelated skip"})
    for nodeid in MODULE.D01_NATIVE_NODEIDS:
        item = SimpleNamespace(nodeid=nodeid, own_markers=[native_skip, unrelated_skip])
        PLUGIN.ExactNodeGate((nodeid,), allow_native_skip_override=True).pytest_collection_modifyitems(None, None, [item])
        assert item.own_markers == [unrelated_skip]
        ordinary = SimpleNamespace(nodeid=nodeid, own_markers=[native_skip])
        PLUGIN.ExactNodeGate((nodeid,)).pytest_collection_modifyitems(None, None, [ordinary])
        assert ordinary.own_markers == [native_skip]

    other = SimpleNamespace(nodeid="tests/verification/test_native.py::test_other", own_markers=[native_skip])
    with pytest.raises(pytest.UsageError, match="requires exactly its registered nodeid"):
        PLUGIN.ExactNodeGate((MODULE.D01_NATIVE_NODEIDS[0],), allow_native_skip_override=True).pytest_collection_modifyitems(
            None, None, [other]
        )
    arbitrary = SimpleNamespace(nodeid="tests/verification/test_other.py::test_native", own_markers=[native_skip])
    with pytest.raises(pytest.UsageError, match="restricted to one registered D01"):
        PLUGIN.ExactNodeGate((arbitrary.nodeid,), allow_native_skip_override=True).pytest_collection_modifyitems(
            None, None, [arbitrary]
        )


def test_d01_native_capability_is_scoped_only_to_the_exact_call(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = _policy()
    nodeid = policy["worktrees"]["d01"]["allowed_nodeids"][0]
    guard_path = Path(policy["worktrees"]["d01"]["root"]) / "src/solveur/core/execution_guard.py"
    guard_spec = importlib.util.spec_from_file_location("solveur.core.execution_guard", guard_path)
    assert guard_spec is not None and guard_spec.loader is not None
    guard = importlib.util.module_from_spec(guard_spec)
    guard_spec.loader.exec_module(guard)
    solveur_package = ModuleType("solveur")
    solveur_package.__path__ = []
    core_package = ModuleType("solveur.core")
    core_package.__path__ = []
    monkeypatch.setitem(sys.modules, "solveur", solveur_package)
    monkeypatch.setitem(sys.modules, "solveur.core", core_package)
    monkeypatch.setitem(sys.modules, "solveur.core.execution_guard", guard)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", f"{nodeid} (call)")
    gate = PLUGIN.ExactNodeGate((nodeid,), allow_native_skip_override=True)
    wrapper = gate.pytest_runtest_call(SimpleNamespace(nodeid=nodeid))
    next(wrapper)
    boundary = "solveur.core.analyses.reduced_harmonic.ReducedHarmonicResponseSolver.solve"
    guard.require_solver_execution_allowed(boundary)
    monkeypatch.setenv(guard.NO_NATIVE_EXECUTION_ENV, "1")
    with pytest.raises(guard.SolverExecutionBlockedError):
        guard.require_solver_execution_allowed(boundary)
    monkeypatch.delenv(guard.NO_NATIVE_EXECUTION_ENV)
    with pytest.raises(StopIteration):
        next(wrapper)
    with pytest.raises(guard.SolverExecutionBlockedError):
        guard.require_solver_execution_allowed(boundary)

    unrelated = gate.pytest_runtest_call(SimpleNamespace(nodeid="tests/unit/test_other.py::test_safe"))
    next(unrelated)
    with pytest.raises(guard.SolverExecutionBlockedError):
        guard.require_solver_execution_allowed(boundary)
    with pytest.raises(StopIteration):
        next(unrelated)


def test_d01_explicit_no_fem_environment_refuses_before_attempt_reservation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from contextlib import nullcontext

    nodeid = (
        "tests/verification/test_wp_d01_bj_wp05_native_experiment.py::"
        "test_wp05_native_modal_and_residual_flexibility_characterization[M3]"
    )
    source_root = tmp_path / "src"
    entry = {
        "allow_native_vv_skip_override": True,
        "attempt_limit_per_nodeid": 3,
        "budgets": {},
    }
    policy = {
        "mandate_id": "DEVELOPMENT_AUTONOMOUS-FEM-test-v1",
        "minimum_free_disk_mib": 1,
        "run_store": ".codex/development-runs",
        "worktrees": {"d01": entry},
    }
    monkeypatch.setattr(MODULE, "load_policy", lambda: policy)
    monkeypatch.setattr(MODULE, "resolve_targets", lambda *args, **kwargs: [nodeid])
    monkeypatch.setattr(
        MODULE,
        "_registered_worktree",
        lambda *args, **kwargs: (entry, tmp_path, source_root, {"head": "a" * 40}, "b" * 64),
    )
    monkeypatch.setattr(MODULE, "_exclusive_file_lock", lambda *_args, **_kwargs: nullcontext())
    monkeypatch.setattr(MODULE, "psutil", object())
    monkeypatch.setattr(MODULE.shutil, "disk_usage", lambda _path: SimpleNamespace(free=2 * 1024**3))
    monkeypatch.setattr(
        MODULE,
        "_next_attempt",
        lambda *_args, **_kwargs: pytest.fail("environment refusal must precede attempt reservation"),
    )
    for name in MODULE.NATIVE_GUARD_ENV_KEYS:
        for marker_name in MODULE.NATIVE_GUARD_ENV_KEYS:
            monkeypatch.delenv(marker_name, raising=False)
        monkeypatch.setenv(name, "1")
        with pytest.raises(MODULE.PolicyError, match="before reserving an attempt"):
            MODULE.run_pytest(
                "fem_exploratory",
                nodeid,
                "dev-no-fem-flag",
                worktree_id="d01",
                reason="verify fail-closed environment preflight",
                preflight_id="pf-000000000000",
                attempt_basis="baseline",
            )
        monkeypatch.delenv(name, raising=False)


def test_d01_missing_preflight_receipt_refuses_before_attempt_reservation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from contextlib import nullcontext

    target = MODULE.D01_NATIVE_NODEIDS[2]
    entry = {
        "allow_native_vv_skip_override": True,
        "attempt_limit_per_nodeid": 3,
        "attempt_limits_per_nodeid": {target: 3},
        "budgets": {},
    }
    policy = {
        "mandate_id": "DEVELOPMENT_AUTONOMOUS-FEM-2026-10-24-v1",
        "minimum_free_disk_mib": 1,
        "run_store": ".codex/development-runs",
        "worktrees": {"d01": entry},
    }
    store = tmp_path / "store"
    monkeypatch.setattr(MODULE, "load_policy", lambda: policy)
    monkeypatch.setattr(MODULE, "resolve_targets", lambda *args, **kwargs: [target])
    monkeypatch.setattr(
        MODULE,
        "_registered_worktree",
        lambda *args, **kwargs: (entry, tmp_path, tmp_path / "src", {"head": "a" * 40}, "b" * 64),
    )
    monkeypatch.setattr(MODULE, "_node_ledger_context", lambda *_args: (store / "v2.json", store / "v2.lock", "v2", {"path": "v1", "sha256": "c" * 64, "mandate_id": "v1"}))
    monkeypatch.setattr(MODULE, "_run_root", lambda _policy: store)
    monkeypatch.setattr(MODULE, "_exclusive_file_lock", lambda *_args, **_kwargs: nullcontext())
    monkeypatch.setattr(MODULE, "psutil", object())
    monkeypatch.setattr(MODULE.shutil, "disk_usage", lambda _path: SimpleNamespace(free=2 * 1024**3))
    monkeypatch.setattr(
        MODULE,
        "_validate_d01_preflight_receipt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(MODULE.PolicyError("missing preflight")),
    )
    monkeypatch.setattr(
        MODULE,
        "_next_attempt",
        lambda *_args, **_kwargs: pytest.fail("missing preflight must refuse before creating/reserving an attempt"),
    )
    for name in MODULE.NATIVE_GUARD_ENV_KEYS:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(MODULE.PolicyError, match="missing preflight"):
        MODULE.run_pytest(
            "fem_exploratory",
            target,
            "dev-no-preflight",
            worktree_id="d01",
            reason="preflight gate contract test",
            preflight_id="pf-000000000000",
            attempt_basis="baseline",
        )


def test_native_guard_environment_snapshot_matches_guard_semantics(tmp_path: Path) -> None:
    inherited = {
        "QF_SOLVER_NO_NATIVE_EXECUTION": "false",
        "WPC01_NO_NATIVE_EXECUTION": "0",
        "WPC01_SPATIAL_NO_FEM_TEST": "1",
        "WPC01_SPATIAL_TERMINAL_REHEARSAL": "0",
    }
    child = MODULE.build_child_environment(tmp_path, base=inherited)
    active = MODULE._native_guard_environment(child)
    assert active["active_markers"] == ["WPC01_SPATIAL_NO_FEM_TEST"]
    assert active["values"] == {
        "QF_SOLVER_NO_NATIVE_EXECUTION": "INACTIVE",
        "WPC01_NO_NATIVE_EXECUTION": "INACTIVE",
        "WPC01_SPATIAL_NO_FEM_TEST": "ACTIVE",
        "WPC01_SPATIAL_TERMINAL_REHEARSAL": "INACTIVE",
    }


def test_native_guard_snapshot_is_bound_to_the_child_environment() -> None:
    parent = {
        "QF_SOLVER_NO_NATIVE_EXECUTION": "0",
        "WPC01_NO_NATIVE_EXECUTION": "false",
        "WPC01_SPATIAL_NO_FEM_TEST": "0",
        "WPC01_SPATIAL_TERMINAL_REHEARSAL": "0",
    }
    unchanged_child = dict(parent)
    assert MODULE._validate_native_guard_environment(parent, unchanged_child) == (
        MODULE._native_guard_environment(parent)
    )

    altered_child = {**parent, "QF_SOLVER_NO_NATIVE_EXECUTION": "1"}
    with pytest.raises(MODULE.PolicyError, match="changed an explicit no-native marker"):
        MODULE._validate_native_guard_environment(parent, altered_child)


def test_retry_series_is_scoped_and_bounded(tmp_path: Path) -> None:
    series = tmp_path / "dev-12345678abcd"
    first, _ = MODULE._next_attempt(series, series.name, "unit", 2)
    second, _ = MODULE._next_attempt(series, series.name, "unit", 2)
    assert (first, second) == (1, 2)
    with pytest.raises(MODULE.PolicyError, match="exhausted"):
        MODULE._next_attempt(series, series.name, "unit", 2)
    with pytest.raises(MODULE.PolicyError, match="different scope"):
        MODULE._next_attempt(series, series.name, "integration", 2)


def test_per_nodeid_mandate_attempt_ledger_bounds_attempts_and_refuses_identical_retry(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    lock = tmp_path / "ledger.lock"
    kwargs = {
        "ledger_path": ledger,
        "lock_path": lock,
        "mandate_id": "DEVELOPMENT_AUTONOMOUS-FEM-test-v1",
        "worktree_id": "d01",
        "target": "tests/verification/test_case.py::test_m3[M3]",
        "source_fingerprint": "a" * 64,
        "maximum": 3,
    }
    key, first = MODULE._reserve_node_attempt(**kwargs, series_id="dev-11111111", reason="baseline diagnostic")
    assert first == 1
    with pytest.raises(MODULE.PolicyError, match="identical repeat"):
        MODULE._reserve_node_attempt(**kwargs, series_id="dev-22222222", reason="baseline diagnostic")
    _, second = MODULE._reserve_node_attempt(
        **{**kwargs, "source_fingerprint": "b" * 64},
        series_id="dev-22222222",
        reason="instrumented projection hypothesis",
    )
    assert second == 2
    _, third = MODULE._reserve_node_attempt(
        **kwargs,
        series_id="dev-33333333",
        reason="independent rounding hypothesis",
    )
    assert third == 3
    with pytest.raises(MODULE.PolicyError, match="exhausted 3 attempts"):
        MODULE._reserve_node_attempt(
            **{**kwargs, "source_fingerprint": "c" * 64},
            series_id="dev-44444444",
            reason="new attempt",
        )
    record = json.loads(ledger.read_text(encoding="utf-8"))
    assert len(record["entries"][key]) == 3


def test_d01_v2_ledger_is_linked_to_but_never_mutates_v1_predecessor(tmp_path: Path) -> None:
    import hashlib

    predecessor_mandate = "DEVELOPMENT_AUTONOMOUS-FEM-2026-10-24-v1"
    predecessor_path = tmp_path / "node-attempt-ledger.json"
    historical_key = f"{predecessor_mandate}:d01:{MODULE.D01_NATIVE_NODEIDS[2]}"
    predecessor_path.write_text(
        json.dumps(
            {
                "schema": "qfsolver-development-node-ledger-v1",
                "mandate_id": predecessor_mandate,
                "entries": {historical_key: [{"attempt": index} for index in range(1, 4)]},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    predecessor_hash = hashlib.sha256(predecessor_path.read_bytes()).hexdigest()
    policy = {
        "mandate_id": predecessor_mandate,
        "worktrees": {
            "d01": {
                "development_mandate_id": "DEVELOPMENT_AUTONOMOUS-FEM-2026-10-24-v2-d01",
                "node_attempt_ledger": {
                    "path": "node-attempt-ledger-d01-v2.json",
                    "predecessor": {
                        "path": "node-attempt-ledger.json",
                        "sha256": predecessor_hash,
                        "mandate_id": predecessor_mandate,
                    },
                },
            }
        },
    }
    ledger_path, lock_path, mandate_id, predecessor = MODULE._node_ledger_context(policy, tmp_path, "d01")
    old_bytes = predecessor_path.read_bytes()
    assert ledger_path == tmp_path / "node-attempt-ledger-d01-v2.json"
    assert ledger_path != predecessor_path
    assert mandate_id == "DEVELOPMENT_AUTONOMOUS-FEM-2026-10-24-v2-d01"
    assert predecessor is not None and predecessor["sha256"] == predecessor_hash

    key, attempt = MODULE._reserve_node_attempt(
        ledger_path,
        lock_path,
        mandate_id=mandate_id,
        worktree_id="d01",
        target=MODULE.D01_NATIVE_NODEIDS[0],
        series_id="dev-12345678",
        source_fingerprint="a" * 64,
        reason="new D01 envelope test",
        maximum=1,
        predecessor=predecessor,
        controller_fingerprint="d" * 64,
        attempt_basis="baseline",
    )
    new_ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert new_ledger["schema"] == "qfsolver-development-node-ledger-v2"
    assert new_ledger["predecessor"] == predecessor
    assert len(new_ledger["entries"][key]) == 1 and attempt == 1
    assert predecessor_path.read_bytes() == old_bytes
    assert hashlib.sha256(predecessor_path.read_bytes()).hexdigest() == predecessor_hash


def test_d01_v2_retry_requires_changed_inputs_or_unique_hypothesis(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger-d01-v2.json"
    lock = tmp_path / "ledger-d01-v2.lock"
    predecessor = {"path": "node-attempt-ledger.json", "sha256": "c" * 64, "mandate_id": "DEVELOPMENT_AUTONOMOUS-FEM-v1"}
    common = {
        "ledger_path": ledger,
        "lock_path": lock,
        "mandate_id": "DEVELOPMENT_AUTONOMOUS-FEM-2026-10-24-v2-d01",
        "worktree_id": "d01",
        "target": MODULE.D01_NATIVE_NODEIDS[2],
        "series_id": "dev-87654321",
        "source_fingerprint": "a" * 64,
        "reason": "M3 baseline collection and diagnostic payload attempt",
        "maximum": 3,
        "predecessor": predecessor,
        "controller_fingerprint": "d" * 64,
        "attempt_basis": "baseline",
    }
    MODULE._reserve_node_attempt(**common)
    with pytest.raises(MODULE.PolicyError, match="only valid for the first"):
        MODULE._reserve_node_attempt(**{**common, "series_id": "dev-87654322"})
    with pytest.raises(MODULE.PolicyError, match="changed D01 source fingerprint"):
        MODULE._reserve_node_attempt(
            **{
                **common,
                "series_id": "dev-87654323",
                "attempt_basis": "source_change",
                "reason": "Reworded but source did not change",
            }
        )
    _, number = MODULE._reserve_node_attempt(
        **{
            **common,
            "series_id": "dev-87654324",
            "attempt_basis": "new_diagnostic_hypothesis",
            "hypothesis_id": "M3-H2",
            "reason": "Test whether remaining discrepancy is dominated by projected modal conditioning",
        }
    )
    assert number == 2
    with pytest.raises(MODULE.PolicyError, match="already been used"):
        MODULE._reserve_node_attempt(
            **{
                **common,
                "series_id": "dev-87654325",
                "attempt_basis": "new_diagnostic_hypothesis",
                "hypothesis_id": "M3-H2",
                "reason": "Another wording for the same hypothesis ID",
            }
        )


def test_development_attempt_record_cannot_claim_qualification() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert '"qualification": "NOT_APPLICABLE_DEVELOPMENT_ONLY"' in source
    assert '"qualification_promotion": "PROHIBITED"' in source
    assert "qualification_release" not in source.lower()


def test_standard_pytest_command_excludes_release_evidence_markers(tmp_path: Path) -> None:
    command = MODULE.build_pytest_command("unit", ["tests/unit/test_contract.py"], tmp_path)
    assert command[:4] == [sys.executable, "-B", "-m", "pytest"]
    assert "not evidence and not benchmark and not large" in command
    assert not any("owner-go" in part.lower() for part in command)


def _monitor_limits(**overrides) -> dict:
    return {
        "timeout_seconds": 5,
        "rss_soft_limit_mib": 2048,
        "process_tree_limit": 8,
        "output_total_limit_mib": 1,
        "output_stream_limit_mib": 1,
        "temporary_limit_mib": 2,
        "archive_size_limit_mib": 2,
        **overrides,
    }


def test_supervisor_times_out_a_synthetic_child_without_interactive_input(tmp_path: Path) -> None:
    if MODULE.psutil is None:
        pytest.skip("psutil is required by the development runner")
    limits = _monitor_limits(timeout_seconds=0.2)
    result = MODULE.run_supervised_command(
        [sys.executable, "-c", "import time; time.sleep(20)"],
        cwd=tmp_path,
        environment=MODULE.build_child_environment(tmp_path),
        output_dir=tmp_path / "output",
        temporary_dir=tmp_path / "tmp",
        limits=limits,
        poll_interval=0.05,
    )
    assert result.status == "WALL_TIMEOUT_EXCEEDED"
    assert result.return_code is not None
    assert result.elapsed_seconds < 5


def test_timeout_terminates_a_synthetic_descendant(tmp_path: Path) -> None:
    if MODULE.psutil is None:
        pytest.skip("psutil is required by the development runner")
    child_pid_path = tmp_path / "child.pid"
    child_source = "import time; time.sleep(20)"
    parent_source = (
        "import pathlib,subprocess,sys,time;"
        f"child=subprocess.Popen([sys.executable, '-c', {child_source!r}]);"
        f"pathlib.Path({str(child_pid_path)!r}).write_text(str(child.pid));"
        "time.sleep(20)"
    )
    result = MODULE.run_supervised_command(
        [sys.executable, "-c", parent_source],
        cwd=tmp_path,
        environment=MODULE.build_child_environment(tmp_path),
        output_dir=tmp_path / "output",
        temporary_dir=tmp_path / "tmp",
        limits=_monitor_limits(timeout_seconds=0.3),
        poll_interval=0.03,
    )
    assert result.status == "WALL_TIMEOUT_EXCEEDED"
    child_pid = int(child_pid_path.read_text(encoding="ascii"))
    assert not MODULE.psutil.pid_exists(child_pid)


def test_supervisor_caps_captured_output(tmp_path: Path) -> None:
    if MODULE.psutil is None:
        pytest.skip("psutil is required by the development runner")
    result_dir = tmp_path / "output"
    result = MODULE.run_supervised_command(
        [sys.executable, "-c", "print('x' * 10000)"],
        cwd=tmp_path,
        environment=MODULE.build_child_environment(tmp_path),
        output_dir=result_dir,
        temporary_dir=tmp_path / "tmp",
        limits=_monitor_limits(output_total_limit_mib=0.001, output_stream_limit_mib=0.001),
        poll_interval=0.02,
    )
    assert result.status == "CAPTURED_OUTPUT_LIMIT_EXCEEDED"
    assert result.stdout_bytes <= int(0.001 * 1024 * 1024)
    assert (result_dir / "stdout.log").stat().st_size == result.stdout_bytes


def test_supervisor_monitors_archive_and_temporary_size_separately(tmp_path: Path) -> None:
    if MODULE.psutil is None:
        pytest.skip("psutil is required by the development runner")
    output_dir = tmp_path / "output"
    temporary_dir = tmp_path / "tmp"
    temporary_dir.mkdir()
    payload = temporary_dir / "payload.bin"
    source = f"from pathlib import Path; import time; Path({str(payload)!r}).write_bytes(b'x'*10000); time.sleep(20)"
    result = MODULE.run_supervised_command(
        [sys.executable, "-c", source],
        cwd=tmp_path,
        environment=MODULE.build_child_environment(temporary_dir),
        output_dir=output_dir,
        temporary_dir=temporary_dir,
        limits=_monitor_limits(temporary_limit_mib=0.002),
        poll_interval=0.03,
    )
    assert result.status == "TEMPORARY_SIZE_LIMIT_OBSERVED"
    assert result.temporary_bytes > int(0.002 * 1024 * 1024)


def test_supervisor_monitors_rss_as_a_soft_limit(tmp_path: Path) -> None:
    if MODULE.psutil is None:
        pytest.skip("psutil is required by the development runner")
    result = MODULE.run_supervised_command(
        [sys.executable, "-c", "data=bytearray(128*1024*1024); import time; time.sleep(20)"],
        cwd=tmp_path,
        environment=MODULE.build_child_environment(tmp_path),
        output_dir=tmp_path / "output",
        temporary_dir=tmp_path / "tmp",
        limits=_monitor_limits(rss_soft_limit_mib=48),
        poll_interval=0.03,
    )
    assert result.status == "RSS_SOFT_LIMIT_EXCEEDED"
    assert result.peak_rss_bytes > 48 * 1024 * 1024


def test_archive_writer_is_atomic_json(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    MODULE._atomic_json(path, {"state": "PASS", "attempt": 1})
    assert json.loads(path.read_text(encoding="utf-8")) == {"attempt": 1, "state": "PASS"}
    assert list(tmp_path.glob("*.tmp")) == []
