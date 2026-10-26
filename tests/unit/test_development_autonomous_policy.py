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

WP12_DYNAMICS_NODEIDS = (
    "tests/unit/test_modal_newmark.py::test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables",
    "tests/unit/test_reduced_harmonic.py::test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation",
    "tests/unit/test_wp07_uniform_base_acceleration.py::test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization",
    "tests/unit/test_modal_basis_damping.py::test_analytical_coupled_two_dof_eigenproblem_and_projected_operators",
    "tests/unit/test_reduced_harmonic.py::test_reduced_impedance_matches_independent_analytical_sdof_amplitude_and_phase",
    "tests/unit/test_reduced_harmonic.py::test_coupled_two_dof_complex_response_uses_full_projected_operators",
    "tests/unit/test_reduced_harmonic.py::test_reduced_impedance_detects_exact_and_near_resonance_before_solving",
    "tests/unit/test_reduced_harmonic.py::test_full_basis_reduced_harmonic_matches_direct_rayleigh_route_and_zero_hz",
    "tests/unit/test_modal_newmark.py::test_sdof_free_undamped_matches_analytic_solution_and_initial_projection",
    "tests/unit/test_modal_newmark.py::test_sdof_free_damped_matches_under_damped_analytic_solution",
    "tests/unit/test_wp07_uniform_base_acceleration.py::test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames",
    "tests/unit/test_wp07_uniform_base_acceleration.py::test_transient_base_sdof_matches_independent_constant_acceleration_solution",
    "tests/unit/test_result_serialization_contracts.py::test_reduced_harmonic_json_round_trip_preserves_signed_zero_phase_metadata",
)
WP12_ELEMENTS_VERIFICATION_NODEIDS = (
    "tests/verification/test_wp12_hex8_sri_diagnostics.py::test_wp12_hex8_sri_near_incompressible_nu04999_nx16",
    "tests/verification/test_wp12_hex8_sri_diagnostics.py::test_wp12_hex8_sri_near_degenerate_nu0495_nx4",
)
WP12_TET4_NODEIDS = (
    "tests/unit/test_wp12_tet4_prepared_fem.py::test_wp12_tet4_refinement_factor_1",
    "tests/unit/test_wp12_tet4_prepared_fem.py::test_wp12_tet4_refinement_factor_2",
    "tests/unit/test_wp12_tet4_prepared_fem.py::test_wp12_tet4_refinement_factor_4",
    "tests/unit/test_wp12_tet4_prepared_fem.py::test_wp12_tet4_refinement_factor_8",
    "tests/unit/test_wp12_tet4_prepared_fem.py::test_wp12_tet10_family_comparison_factor_4",
    "tests/unit/test_wp12_tet4_prepared_fem.py::test_wp12_hex8_family_comparison_factor_4",
)
WP12_ELEMENTS_LOADS_NODEIDS = (
    "tests/unit/test_wp12b_beam2_continuity.py::test_wp12b_beam2_rotated_uniform_line_load",
    "tests/unit/test_wp12b_tet10_curved_load.py::test_wp12b_tet10_curved_face_pressure_solve",
    "tests/unit/test_wp12b_hex20_affine_patch.py::test_wp12b_hex20_uniaxial_traction_patch",
)


def _policy() -> dict:
    return MODULE.load_policy()


def test_policy_registers_only_owner_authorized_worktrees_and_keeps_qualification_separate() -> None:
    policy = _policy()
    assert policy["mode"] == "DEVELOPMENT_AUTONOMOUS"
    assert set(policy["worktrees"]) == {
        "d01",
        "c01",
        "e01",
        "wp12_wp07",
        "wp12_tet4",
        "wp12_elements",
        "wp12_elements_loads",
        "wp12_dynamics",
    }
    assert policy["worktrees"]["d01"]["attempt_limit_per_nodeid"] == 3
    assert policy["worktrees"]["d01"]["development_mandate_id"] == "DEVELOPMENT_AUTONOMOUS-FEM-2026-10-24-v2-d01"
    assert policy["worktrees"]["d01"]["node_attempt_ledger"]["path"] == "node-attempt-ledger-d01-v2.json"
    assert policy["worktrees"]["d01"]["node_attempt_ledger"]["predecessor"]["sha256"] == (
        "5a6f9693e3649e2269625eb9baeb6bf53c6f2fda89ccc6011f508922b808bbc2"
    )
    assert policy["worktrees"]["c01"]["attempt_limit_per_nodeid"] == 3
    assert policy["worktrees"]["e01"]["mode"] == "math_non_fem"
    assert policy["worktrees"]["wp12_wp07"]["attempt_limit_per_nodeid"] == 10
    assert policy["worktrees"]["wp12_tet4"]["max_total_attempts"] == 12
    assert policy["worktrees"]["wp12_tet4"]["target_max_dofs"] == 50000
    assert policy["worktrees"]["wp12_elements"]["max_total_attempts"] == 20
    assert policy["worktrees"]["wp12_elements"]["target_max_dofs"] == 30000
    assert policy["worktrees"]["wp12_elements_loads"]["max_total_attempts"] == 3
    assert policy["worktrees"]["wp12_elements_loads"]["attempt_limit_per_nodeid"] == 1
    assert policy["worktrees"]["wp12_elements_loads"]["target_max_dofs"] == 30000
    assert policy["worktrees"]["wp12_elements_loads"]["allowed_nodeids"] == list(WP12_ELEMENTS_LOADS_NODEIDS)
    assert policy["worktrees"]["wp12_dynamics"]["attempt_limit_per_nodeid"] == 10
    assert policy["worktrees"]["wp12_dynamics"]["max_total_attempts"] == 130
    assert policy["worktrees"]["wp12_dynamics"]["max_timeout_seconds"] == 300
    assert policy["worktrees"]["d01"]["allowed_nodeids"] == list(MODULE.D01_NATIVE_NODEIDS)
    assert {
        name: policy["worktrees"]["d01"]["budgets"][name] for name in MODULE.D01_OWNER_BUDGETS
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
    assert MODULE._series_root(tmp_path, "math_non_fem", "e01") == tmp_path / "worktrees" / "e01"
    assert MODULE._series_root(tmp_path, "unit", None) == tmp_path / "standard" / "unit"
    with pytest.raises(MODULE.PolicyError, match="unknown worktree"):
        MODULE._series_root(tmp_path, "fem_exploratory", "e02")


def test_wp12_registry_has_five_distinct_exact_worktree_envelopes() -> None:
    policy = _policy()
    expected = {
        "wp12_wp07": ("E:\\QFSolverAgents\\wp07", "fix/wp12-wp07-serialization", 300, 10, None),
        "wp12_tet4": ("E:\\QFSolverAgents\\tet4", "experiment/wp12-tet4-convergence", 900, 12, 50000),
        "wp12_elements": ("E:\\QFSolverAgents\\vv-elements", "test/wp12-fem-regressions", 300, 20, 30000),
        "wp12_elements_loads": (
            "C:\\Users\\fari\\.codex\\worktrees\\verify-wp12-elements-loads\\qf_solver",
            "verify/wp12-elements-loads",
            300,
            3,
            30000,
        ),
        "wp12_dynamics": (
            "E:\\QFSolverAgents\\wp12-dynamics",
            "codex/wp12-dynamic-harmonic-verification",
            300,
            130,
            None,
        ),
    }
    for worktree_id, (root, branch, timeout, attempts, max_dofs) in expected.items():
        entry = policy["worktrees"][worktree_id]
        assert entry["root"] == entry["git_root"] == root
        assert entry["branch"] == branch
        assert entry["mode"] == "fem_exploratory"
        assert entry["baseline_commit"] == MODULE.WP12_BASELINE_COMMIT
        assert entry["budgets"]["timeout_seconds"] == timeout
        assert entry["max_total_attempts"] == attempts
        assert entry["target_max_dofs"] == max_dofs
        if worktree_id == "wp12_dynamics":
            assert entry["allowed_nodeids"] == list(WP12_DYNAMICS_NODEIDS)
            records = entry["nodeid_registration_records"]
            assert len(records) == 20
            assert all(len(record["worktree_head"]) == 40 for record in entry["nodeid_registration_records"])
            assert all(len(record["source_fingerprint"]) == 64 for record in entry["nodeid_registration_records"])
            newmark_target = "tests/unit/test_modal_newmark.py::test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables"
            newmark_records = [record for record in records if record["target"] == newmark_target]
            assert len(newmark_records) == 4
            assert (newmark_records[0]["worktree_head"], newmark_records[0]["source_fingerprint"]) == (
                "e64493e90b428ec3f41da0dcbc3ebfb5fd4cbc3d",
                "63e2972018db9bd4f8fc50947504da886e2de29ee4494c3c78422f5ec5c1536d",
            )
            assert (newmark_records[1]["worktree_head"], newmark_records[1]["source_fingerprint"]) == (
                "ed24d6b00d95e339b288a8ec8fa0edf16149be5a",
                "0174c88cd3aa03529c0e6fd6d6ab2e7ef728586ecd2e71f27330c42ffda5811d",
            )
            assert (newmark_records[2]["worktree_head"], newmark_records[2]["source_fingerprint"]) == (
                "1f609e52fe7838a8e2c61684a2658429fac00a5e",
                "6d50810fee371a96f4ea240bd767000924cc80e9d1173a04e0db5f9dd3392438",
            )
            assert (newmark_records[3]["worktree_head"], newmark_records[3]["source_fingerprint"]) == (
                "d9deddbd6b42467c5fdc9e278bd54e97605f5738",
                "65e4078b1735de9adb258d1438fed39dcd69c1b68fa3560afb69896da60bdff8",
            )
            harmonic_target = "tests/unit/test_reduced_harmonic.py::test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation"
            harmonic_records = [record for record in records if record["target"] == harmonic_target]
            assert len(harmonic_records) == 3
            assert (harmonic_records[0]["worktree_head"], harmonic_records[0]["source_fingerprint"]) == (
                "e64493e90b428ec3f41da0dcbc3ebfb5fd4cbc3d",
                "ff58a607ad1a5f4d3c1c632cb448219bc24746cb80623abab3886917ba749074",
            )
            assert (harmonic_records[1]["worktree_head"], harmonic_records[1]["source_fingerprint"]) == (
                "1f609e52fe7838a8e2c61684a2658429fac00a5e",
                "b203b2fd8cf786e86c1a33b65a1160268a763b7ec0d895d07e6826ef915d7c94",
            )
            assert (harmonic_records[2]["worktree_head"], harmonic_records[2]["source_fingerprint"]) == (
                "d9deddbd6b42467c5fdc9e278bd54e97605f5738",
                "bd65535cfeaff0af932fb33e556ded5c1762f2dd90a5467793bdc01c6daca50c",
            )
            base_target = "tests/unit/test_wp07_uniform_base_acceleration.py::test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization"
            base_records = [record for record in records if record["target"] == base_target]
            assert len(base_records) == 3
            assert (base_records[0]["worktree_head"], base_records[0]["source_fingerprint"]) == (
                "e64493e90b428ec3f41da0dcbc3ebfb5fd4cbc3d",
                "6db5b4597252082012fa38b1ed5cba02190562746556d5eabd1f74a256e0f8da",
            )
            assert (base_records[1]["worktree_head"], base_records[1]["source_fingerprint"]) == (
                "1f609e52fe7838a8e2c61684a2658429fac00a5e",
                "04461145a495ff3f3aebfe573ad3d8859befb7ec9a99bd7d54dd6cf486ae4d56",
            )
            assert (base_records[2]["worktree_head"], base_records[2]["source_fingerprint"]) == (
                "d9deddbd6b42467c5fdc9e278bd54e97605f5738",
                "969dd0276e4b9b9d4963751bcf1c06603e122aac623852f3c7a3a2c4496745c6",
            )
            for record in (newmark_records[3], harmonic_records[2], base_records[2]):
                assert (
                    record["selected_dofs"] == {newmark_target: 1, harmonic_target: 3, base_target: 1}[record["target"]]
                )
                assert record["timeout_seconds"] == 300
        elif worktree_id == "wp12_tet4":
            assert entry["allowed_nodeids"] == list(WP12_TET4_NODEIDS)
            records = entry["nodeid_registration_records"]
            assert [record["selected_dofs"] for record in records] == [72, 297, 1575, 9963, 9963, 1575]
            assert all(record["worktree_head"] == "619fddd97d56936ca3333cbeca9e7ae46dbd6a8e" for record in records)
            assert all(
                record["source_fingerprint"] == "eb29d0c88cd5be1fb238b8472b1bf3b970f5aa2a743ecc8fca7a6a44e54b87df"
                for record in records
            )
        elif worktree_id == "wp12_elements":
            assert entry["allowed_nodeids"] == list(WP12_ELEMENTS_VERIFICATION_NODEIDS)
            records = entry["nodeid_registration_records"]
            assert [record["selected_dofs"] for record in records] == [459, 135]
            assert all(record["worktree_head"] == "fa889f480766506787941617fa0db4124381c63b" for record in records)
            assert all(
                record["source_fingerprint"] == "12a935bd4e926eb53d31372e93f1c9d5f991a3900c8b2bac2d74103ee7401104"
                for record in records
            )
        elif worktree_id == "wp12_elements_loads":
            assert entry["allowed_nodeids"] == list(WP12_ELEMENTS_LOADS_NODEIDS)
            records = entry["nodeid_registration_records"]
            assert [record["target"] for record in records] == list(WP12_ELEMENTS_LOADS_NODEIDS)
            assert [record["selected_dofs"] for record in records] == [12, 30, 60]
            assert all(record["worktree_head"] == "8818b1b4095bd7f5c1303d640375c2c577bdc4d8" for record in records)
            assert [record["source_fingerprint"] for record in records] == [
                "d7eeaa57fac7b124eeeb34d6886420fa4dc0a2f6dd588e3c4df440d00c673896",
                "53b10b6ffb8bead69f5c31e4529c542eefd3a97d23dbbf763d0851846903e953",
                "eb43367d0c044afb20df5693715a056c8ced622ead545b799dcb6d9e19ce3d77",
            ]
            assert all(record["timeout_seconds"] == 300 for record in records)
        else:
            assert entry["allowed_nodeids"] == []
            assert entry["nodeid_registration_records"] == []
        assert entry["nodeid_registration"]["enabled"] is True
        assert entry["max_timeout_seconds"] == (900 if worktree_id in {"wp12_tet4", "wp12_elements"} else 300)
        assert entry["concurrency_class"] == "parallel"

    with pytest.raises(MODULE.PolicyError, match="exact nodeid in the registered worktree allowlist"):
        MODULE.resolve_targets(
            "fem_exploratory",
            "tests/unit/test_modal_newmark.py::test_unregistered_case",
            policy,
            worktree_id="wp12_dynamics",
        )


def test_dynamic_nodeids_are_allowlisted_only_for_the_dynamics_worktree() -> None:
    policy = _policy()
    for nodeid in WP12_DYNAMICS_NODEIDS:
        assert MODULE.resolve_targets("fem_exploratory", nodeid, policy, worktree_id="wp12_dynamics") == [nodeid]
        with pytest.raises(MODULE.PolicyError, match="exact nodeid in the registered worktree allowlist"):
            MODULE.resolve_targets("fem_exploratory", nodeid, policy, worktree_id="wp12_wp07")

    unknown_nodeid = "tests/unit/test_modal_newmark.py::test_unregistered_dynamic_case"
    with pytest.raises(MODULE.PolicyError, match="exact nodeid in the registered worktree allowlist"):
        MODULE.resolve_targets("fem_exploratory", unknown_nodeid, policy, worktree_id="wp12_dynamics")


def test_each_wp12_worktree_resolves_its_registered_test_and_solver_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = _policy()
    monkeypatch.setattr(
        MODULE,
        "_git_identity",
        lambda root, **kwargs: {
            "root": str(root),
            "branch": kwargs["expected_branch"],
            "head": "a" * 40,
            "tree": "b" * 40,
            "status_short": "",
        },
    )
    monkeypatch.setattr(MODULE, "_worktree_source_fingerprint", lambda *_args: "c" * 64)
    for index, worktree_id in enumerate(MODULE.WP12_OWNER_ENVELOPES):
        root = tmp_path / worktree_id
        (root / "src" / "solveur").mkdir(parents=True)
        (root / "src" / "solveur" / "__init__.py").write_text("\n", encoding="utf-8")
        (root / "tests" / "unit").mkdir(parents=True)
        test_file = root / "tests" / "unit" / "test_registered.py"
        test_file.write_text(f"def test_case_{index}():\n    pass\n", encoding="utf-8")
        target = f"tests/unit/test_registered.py::test_case_{index}"
        entry = policy["worktrees"][worktree_id]
        entry.update({"root": str(root), "git_root": str(root), "allowed_nodeids": [target]})
        assert MODULE.resolve_targets("fem_exploratory", target, policy, worktree_id=worktree_id) == [target]
        registered, resolved_root, source_root, identity, fingerprint = MODULE._registered_worktree(
            worktree_id, target, policy
        )
        assert registered is entry
        assert resolved_root == root.resolve()
        assert source_root == (root / "src").resolve()
        assert identity["branch"] == entry["branch"]
        assert identity["status_short"] == ""
        assert fingerprint == "c" * 64


def test_wp12_dirty_scientific_worktree_is_refused_before_registration_or_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "agent"
    (root / "src" / "solveur").mkdir(parents=True)
    (root / "src" / "solveur" / "__init__.py").write_text("\n", encoding="utf-8")
    (root / "tests" / "unit").mkdir(parents=True)
    test_file = root / "tests" / "unit" / "test_case.py"
    test_file.write_text("def test_case():\n    pass\n", encoding="utf-8")
    policy = _policy()
    entry = policy["worktrees"]["wp12_wp07"]
    entry.update({"root": str(root), "git_root": str(root), "allowed_nodeids": ["tests/unit/test_case.py::test_case"]})
    monkeypatch.setattr(
        MODULE,
        "_git_identity",
        lambda root, **kwargs: {
            "root": str(root),
            "branch": kwargs["expected_branch"],
            "head": "a" * 40,
            "tree": "b" * 40,
            "status_short": " M src/solveur/results.py",
        },
    )
    with pytest.raises(MODULE.PolicyError, match="must be clean"):
        MODULE._registered_worktree("wp12_wp07", "tests/unit/test_case.py::test_case", policy)


def _prepare_wp12_registration_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, str]:
    controller = tmp_path / "controller"
    agent_root = tmp_path / "agent"
    evidence_root = tmp_path / "evidence" / "wp12_wp07"
    coordination_root = tmp_path / "evidence" / ".wp12-coordination"
    for directory in (controller, agent_root / "src" / "solveur", agent_root / "tests" / "unit"):
        directory.mkdir(parents=True, exist_ok=True)
    (agent_root / "src" / "solveur" / "__init__.py").write_text('"synthetic package"\n', encoding="utf-8")
    module = agent_root / "tests" / "unit" / "test_candidate.py"
    module.write_text("def test_candidate_case():\n    assert True\n", encoding="utf-8")

    envelope = dict(MODULE.WP12_OWNER_ENVELOPES["wp12_wp07"])
    envelope["root"] = str(agent_root)
    envelope["evidence_root"] = str(evidence_root)
    monkeypatch.setitem(MODULE.WP12_OWNER_ENVELOPES, "wp12_wp07", envelope)
    monkeypatch.setattr(MODULE, "WP12_COORDINATION_ROOT", coordination_root)
    monkeypatch.setattr(MODULE, "ROOT", controller)
    policy_path = controller / "development_autonomous_policy.json"
    policy = json.loads((SCRIPT_PATH.parents[1] / "development_autonomous_policy.json").read_text(encoding="utf-8"))
    policy["resource_coordination_root"] = str(coordination_root)
    entry = policy["worktrees"]["wp12_wp07"]
    entry.update(
        {
            "root": str(agent_root),
            "git_root": str(agent_root),
            "evidence_root": str(evidence_root),
        }
    )
    policy_path.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(MODULE, "POLICY_PATH", policy_path)
    monkeypatch.setattr(
        MODULE,
        "_git_identity",
        lambda root, **kwargs: {
            "root": str(root),
            "branch": kwargs["expected_branch"],
            "head": "a" * 40,
            "tree": "b" * 40,
            "status_short": "",
        },
    )
    monkeypatch.setattr(MODULE, "_worktree_source_fingerprint", lambda *_args: "c" * 64)
    return agent_root, policy_path, "tests/unit/test_candidate.py::test_candidate_case"


def _prepare_wp12_elements_verification_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, tuple[str, str]]:
    controller = tmp_path / "controller"
    agent_root = tmp_path / "agent"
    evidence_root = tmp_path / "evidence" / "vv-elements"
    coordination_root = tmp_path / "evidence" / ".wp12-coordination"
    for directory in (
        controller,
        agent_root / "src" / "solveur",
        agent_root / "tests" / "unit",
        agent_root / "tests" / "verification",
    ):
        directory.mkdir(parents=True, exist_ok=True)
    (agent_root / "src" / "solveur" / "__init__.py").write_text('"synthetic package"\n', encoding="utf-8")
    module_file = agent_root / "tests" / "verification" / "test_wp12_hex8_sri_diagnostics.py"
    module_file.write_text(
        "def test_wp12_hex8_sri_near_incompressible_nu04999_nx16():\n    pass\n"
        "def test_wp12_hex8_sri_near_degenerate_nu0495_nx4():\n    pass\n"
        "def test_unregistered_element_case():\n    pass\n",
        encoding="utf-8",
    )

    envelope = dict(MODULE.WP12_OWNER_ENVELOPES["wp12_elements"])
    envelope.update({"root": str(agent_root), "evidence_root": str(evidence_root)})
    monkeypatch.setitem(MODULE.WP12_OWNER_ENVELOPES, "wp12_elements", envelope)
    monkeypatch.setattr(MODULE, "WP12_COORDINATION_ROOT", coordination_root)
    monkeypatch.setattr(MODULE, "ROOT", controller)
    policy_path = controller / "development_autonomous_policy.json"
    policy = json.loads((SCRIPT_PATH.parents[1] / "development_autonomous_policy.json").read_text(encoding="utf-8"))
    policy["resource_coordination_root"] = str(coordination_root)
    policy["worktrees"]["wp12_elements"].update(
        {
            "root": str(agent_root),
            "git_root": str(agent_root),
            "evidence_root": str(evidence_root),
            "allowed_nodeids": [],
            "nodeid_registration_records": [],
        }
    )
    policy_path.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(MODULE, "POLICY_PATH", policy_path)
    monkeypatch.setattr(
        MODULE,
        "_git_identity",
        lambda root, **kwargs: {
            "root": str(root),
            "branch": kwargs["expected_branch"],
            "head": "a" * 40,
            "tree": "b" * 40,
            "status_short": "",
        },
    )
    monkeypatch.setattr(MODULE, "_worktree_source_fingerprint", lambda *_args: "c" * 64)
    targets = (
        "tests/verification/test_wp12_hex8_sri_diagnostics.py::test_wp12_hex8_sri_near_incompressible_nu04999_nx16",
        "tests/verification/test_wp12_hex8_sri_diagnostics.py::test_wp12_hex8_sri_near_degenerate_nu0495_nx4",
    )
    return agent_root, policy_path, targets


def test_wp12_elements_registers_only_the_two_exact_verification_nodeids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from contextlib import nullcontext

    agent_root, policy_path, targets = _prepare_wp12_elements_verification_context(tmp_path, monkeypatch)
    monkeypatch.setattr(
        MODULE,
        "run_supervised_command",
        lambda *_args, **_kwargs: pytest.fail("nodeid registration must not launch pytest"),
    )
    monkeypatch.setattr(MODULE, "_exclusive_file_lock", lambda _path: nullcontext())
    selections = {
        targets[0]: (
            459,
            "Regular HEX8-SRI cantilever nx=16, ny=nz=2: 27*(nx+1)=459 total DDL before x=0 supports; 432 free DDL.",
        ),
        targets[1]: (
            135,
            "Near-degenerate-valid HEX8-SRI cantilever nx=4, ny=nz=2: 27*(nx+1)=135 total DDL before x=0 supports; 108 free DDL.",
        ),
    }
    for target in targets:
        selected_dofs, selection_basis = selections[target]
        result = MODULE.register_wp12_nodeid(
            "wp12_elements",
            target,
            "Reproduce a frozen HEX8-SRI diagnostic with raw force, moment and energy evidence.",
            selected_dofs=selected_dofs,
            selection_basis=selection_basis,
            timeout_seconds=300,
        )
        assert result["state"] == "NODEID_REGISTERED"
        assert result["selected_dofs"] == selected_dofs
        assert result["timeout_seconds"] == 300

    policy = MODULE.load_policy(policy_path)
    entry = policy["worktrees"]["wp12_elements"]
    assert entry["pytest_root"] == "tests/unit"
    assert entry["allowed_nodeids"] == list(targets)
    records = entry["nodeid_registration_records"]
    assert [record["selected_dofs"] for record in records] == [459, 135]
    assert all(record["timeout_seconds"] == 300 for record in records)
    assert all(record["worktree_head"] == "a" * 40 for record in records)
    assert all(record["source_fingerprint"] == "c" * 64 for record in records)
    for target in targets:
        assert MODULE.resolve_targets("fem_exploratory", target, policy, worktree_id="wp12_elements") == [target]
        registered, root, source_root, _identity, fingerprint = MODULE._registered_worktree(
            "wp12_elements", target, policy
        )
        assert registered is entry
        assert root == agent_root.resolve()
        assert source_root == (agent_root / "src").resolve()
        assert fingerprint == "c" * 64

    unregistered = "tests/verification/test_wp12_hex8_sri_diagnostics.py::test_unregistered_element_case"
    with pytest.raises(MODULE.PolicyError, match="exact registered wp12_elements verification nodeids"):
        MODULE._validate_wp12_nodeid_syntax(unregistered, worktree_id="wp12_elements")
    with pytest.raises(MODULE.PolicyError, match="exact registered wp12_elements verification nodeids"):
        MODULE._validate_wp12_nodeid_syntax(targets[0], worktree_id="wp12_tet4")


def test_wp12_exact_nodeid_registration_and_allowlist_selection_are_synthetic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from contextlib import nullcontext

    _agent_root, policy_path, target = _prepare_wp12_registration_context(tmp_path, monkeypatch)
    monkeypatch.setattr(
        MODULE, "run_supervised_command", lambda *_args, **_kwargs: pytest.fail("registration must not launch pytest")
    )
    lock_paths: list[Path] = []
    monkeypatch.setattr(
        MODULE,
        "_exclusive_file_lock",
        lambda path: lock_paths.append(path) or nullcontext(),
    )
    result = MODULE.register_wp12_nodeid(
        "wp12_wp07",
        target,
        "bounded synthetic registration check",
        selected_dofs=12,
        selection_basis="Two-node BEAM2 reduced-harmonic reproduction",
    )
    policy = MODULE.load_policy(policy_path)
    assert result["state"] == "NODEID_REGISTERED"
    assert MODULE.resolve_targets("fem_exploratory", target, policy, worktree_id="wp12_wp07") == [target]
    assert len(policy["worktrees"]["wp12_wp07"]["nodeid_registration_records"]) == 1
    registration = policy["worktrees"]["wp12_wp07"]["nodeid_registration_records"][0]
    assert registration["selected_dofs"] == 12
    assert registration["timeout_seconds"] == 300
    assert registration["source_fingerprint"] == "c" * 64
    assert lock_paths == [MODULE.WP12_COORDINATION_ROOT / "locks" / "nodeid-registration.lock"]
    with pytest.raises(MODULE.PolicyError, match="exact nodeid"):
        MODULE.resolve_targets(
            "fem_exploratory",
            "tests/unit/test_candidate.py::test_unregistered_case",
            policy,
            worktree_id="wp12_wp07",
        )


def test_wp12_manifest_stays_unapproved_until_exact_owner_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _agent_root, policy_path, target = _prepare_wp12_registration_context(tmp_path, monkeypatch)
    details = {
        "selected_dofs": 12,
        "selection_basis": "Two-node BEAM2 reduced-harmonic reproduction",
    }
    MODULE.register_wp12_nodeid("wp12_wp07", target, "synthetic manifest registration", **details)
    provenance = {"identity": {"root": "synthetic-controller"}, "sha256": {"policy": "d" * 64}}
    monkeypatch.setattr(MODULE, "_controller_provenance", lambda: provenance)
    prepared = MODULE.prepare_wp12_execution_manifest("wp12_wp07", target, "wp12-test-0001")
    manifest_path = Path(prepared["path"])
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["state"] == "PREPARED_NOT_AUTHORIZED"
    assert payload["limits"]["selected_dofs"] == 12
    policy = MODULE.load_policy(policy_path)
    entry = policy["worktrees"]["wp12_wp07"]
    with pytest.raises(MODULE.PolicyError, match="distinct, explicit Owner decision"):
        MODULE._validate_wp12_execution_manifest(
            manifest_path,
            worktree_id="wp12_wp07",
            target=target,
            entry=entry,
            identity=payload["identity"],
            source_fingerprint=payload["source_fingerprint"],
            controller_fingerprint=payload["controller_fingerprint"],
            selection=MODULE._wp12_active_registration("wp12_wp07", target, entry, "c" * 64),
        )
    payload["state"] = "OWNER_AUTHORIZED"
    payload["owner_decision"] = {
        "status": "APPROVED",
        "approved_by": "Owner",
        "approved_at_utc": "2026-10-26T12:00:00Z",
        "reason": "Synthetic exact-case development authorization validation.",
    }
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    receipt = MODULE._validate_wp12_execution_manifest(
        manifest_path,
        worktree_id="wp12_wp07",
        target=target,
        entry=entry,
        identity=payload["identity"],
        source_fingerprint=payload["source_fingerprint"],
        controller_fingerprint=payload["controller_fingerprint"],
        selection=MODULE._wp12_active_registration("wp12_wp07", target, entry, "c" * 64),
    )
    assert receipt["authorization_id"] == "wp12-test-0001"
    assert len(receipt["sha256"]) == 64


def test_wp12_run_refuses_before_attempt_reservation_without_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _agent_root, policy_path, target = _prepare_wp12_registration_context(tmp_path, monkeypatch)
    MODULE.register_wp12_nodeid(
        "wp12_wp07",
        target,
        "synthetic manifest gate check",
        selected_dofs=12,
        selection_basis="Two-node BEAM2 reduced-harmonic reproduction",
    )
    load_policy = MODULE.load_policy
    monkeypatch.setattr(MODULE, "load_policy", lambda *_args, **_kwargs: load_policy(policy_path))
    monkeypatch.setattr(
        MODULE, "run_supervised_command", lambda *_args, **_kwargs: pytest.fail("refusal must precede FEM")
    )
    with pytest.raises(MODULE.PolicyError, match="require a distinct Owner-authorized execution manifest"):
        MODULE.run_pytest(
            "fem_exploratory",
            target,
            "dev-12345678",
            worktree_id="wp12_wp07",
            reason="synthetic missing manifest gate",
        )
    assert not (tmp_path / "evidence" / "wp12_wp07" / "node-attempt-ledger.json").exists()


def test_wp12_case_selection_enforces_ddl_caps_and_timeout_exceptions() -> None:
    tet4 = MODULE._validate_wp12_case_selection(
        "wp12_tet4",
        selected_dofs=50000,
        selection_basis="TET4 refinement level L3 has 50,000 assembled DDL",
    )
    assert tet4["timeout_seconds"] == 900
    with pytest.raises(MODULE.PolicyError, match="exceeds the 50000-DDL cap"):
        MODULE._validate_wp12_case_selection(
            "wp12_tet4",
            selected_dofs=50001,
            selection_basis="TET4 refinement level L4 exceeds the registered DDL cap",
        )
    with pytest.raises(MODULE.PolicyError, match="exceeds the 30000-DDL cap"):
        MODULE._validate_wp12_case_selection(
            "wp12_elements",
            selected_dofs=30001,
            selection_basis="HEX8-SRI mesh selection exceeds the registered DDL cap",
        )
    with pytest.raises(MODULE.PolicyError, match="exceptional 900-second"):
        MODULE._validate_wp12_case_selection(
            "wp12_elements",
            selected_dofs=30000,
            selection_basis="HEX8-SRI boundary case at the DDL ceiling",
            timeout_seconds=900,
        )
    exceptional = MODULE._validate_wp12_case_selection(
        "wp12_elements",
        selected_dofs=30000,
        selection_basis="HEX8-SRI boundary case at the DDL ceiling",
        timeout_seconds=900,
        timeout_reason="The boundary case requires a longer sparse factorization window.",
    )
    assert exceptional["timeout_seconds"] == 900
    with pytest.raises(MODULE.PolicyError, match="must be 300 seconds by default"):
        MODULE._validate_wp12_case_selection(
            "wp12_elements",
            selected_dofs=12000,
            selection_basis="HEX8-SRI ordinary regression mesh",
            timeout_seconds=600,
        )


def test_wp12_registration_revisions_preserve_history_and_reject_stale_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _agent_root, policy_path, target = _prepare_wp12_registration_context(tmp_path, monkeypatch)
    fingerprint = ["c" * 64]
    monkeypatch.setattr(MODULE, "_worktree_source_fingerprint", lambda *_args: fingerprint[0])
    details = {
        "selected_dofs": 12,
        "selection_basis": "Two-node BEAM2 reduced-harmonic reproduction",
    }
    MODULE.register_wp12_nodeid("wp12_wp07", target, "first source revision", **details)
    fingerprint[0] = "d" * 64
    MODULE.register_wp12_nodeid("wp12_wp07", target, "inspected serialization fix revision", **details)
    policy = MODULE.load_policy(policy_path)
    records = policy["worktrees"]["wp12_wp07"]["nodeid_registration_records"]
    assert len(records) == 2
    assert policy["worktrees"]["wp12_wp07"]["allowed_nodeids"] == [target]
    active = MODULE._wp12_active_registration("wp12_wp07", target, policy["worktrees"]["wp12_wp07"], "d" * 64)
    assert active["selected_dofs"] == 12
    with pytest.raises(MODULE.PolicyError, match="source fingerprint changed"):
        MODULE._wp12_active_registration("wp12_wp07", target, policy["worktrees"]["wp12_wp07"], "e" * 64)


def test_wp12_registration_rejects_bad_paths_functions_and_repeats(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _agent_root, _policy_path, target = _prepare_wp12_registration_context(tmp_path, monkeypatch)
    with pytest.raises(MODULE.PolicyError, match="below tests/unit"):
        MODULE.register_wp12_nodeid(
            "wp12_wp07",
            "tests/unit/../../outside.py::test_case",
            "path traversal test",
            selected_dofs=12,
            selection_basis="Synthetic path traversal refusal check",
        )
    with pytest.raises(MODULE.PolicyError, match="does not name a test function"):
        MODULE.register_wp12_nodeid(
            "wp12_wp07",
            "tests/unit/test_candidate.py::test_absent",
            "missing test function",
            selected_dofs=12,
            selection_basis="Synthetic missing function refusal check",
        )
    MODULE.register_wp12_nodeid(
        "wp12_wp07",
        target,
        "bounded synthetic registration check",
        selected_dofs=12,
        selection_basis="Two-node BEAM2 reduced-harmonic reproduction",
    )
    with pytest.raises(MODULE.PolicyError, match="already registered"):
        MODULE.register_wp12_nodeid(
            "wp12_wp07",
            target,
            "duplicate registration check",
            selected_dofs=12,
            selection_basis="Two-node BEAM2 reduced-harmonic reproduction",
        )


def test_wp12_registered_worktree_rejects_wrong_root_and_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "agent"
    (root / "src" / "solveur").mkdir(parents=True)
    (root / "src" / "solveur" / "__init__.py").write_text("\n", encoding="utf-8")
    (root / "tests" / "unit").mkdir(parents=True)
    module = root / "tests" / "unit" / "test_case.py"
    module.write_text("def test_case():\n    pass\n", encoding="utf-8")
    policy = _policy()
    entry = policy["worktrees"]["wp12_wp07"]
    entry["root"] = str(root)
    wrong_root = root / "different"
    wrong_root.mkdir()
    entry["git_root"] = str(wrong_root)
    with pytest.raises(MODULE.PolicyError, match="root identity changed"):
        MODULE._registered_worktree("wp12_wp07", "tests/unit/test_case.py::test_case", policy)
    entry["git_root"] = str(root)
    monkeypatch.setattr(
        MODULE,
        "_git_identity",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(MODULE.PolicyError("worktree branch mismatch")),
    )
    with pytest.raises(MODULE.PolicyError, match="branch mismatch"):
        MODULE._registered_worktree("wp12_wp07", "tests/unit/test_case.py::test_case", policy)


def test_wp12_wrong_solver_import_origin_is_refused() -> None:
    source_root = Path("/synthetic/source")
    with pytest.raises(MODULE.PolicyError, match="wrong solveur import origin"):
        MODULE._verify_solver_import_origin(source_root, Path("/other/solveur/__init__.py"))
    assert MODULE._verify_solver_import_origin(source_root, source_root / "solveur" / "__init__.py") == (
        (source_root / "solveur" / "__init__.py").resolve()
    )


def test_wp12_selected_ddl_is_passed_to_the_test_process(tmp_path: Path) -> None:
    environment = MODULE.build_child_environment(
        tmp_path / "scratch",
        {"QF_DEV_SELECTED_DOFS": "999999"},
        wp12_entry={
            "worktree_id": "wp12_tet4",
            "max_fem_cases_per_attempt": 1,
            "target_max_dofs": 50000,
            "evidence_root": str(tmp_path / "evidence" / "tet4"),
        },
        wp12_selection={"selected_dofs": 48000},
    )
    assert environment["QF_DEV_WORKTREE_ID"] == "wp12_tet4"
    assert environment["QF_DEV_MAX_FEM_CASES"] == "1"
    assert environment["QF_DEV_MAX_DOFS"] == "50000"
    assert environment["QF_DEV_SELECTED_DOFS"] == "48000"
    assert environment["QF_DEV_EVIDENCE_ROOT"] == str((tmp_path / "evidence" / "tet4").resolve())


def test_wp12_budget_expansion_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original_policy = _policy()
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)
    policy = json.loads(json.dumps(original_policy))
    policy["worktrees"]["wp12_tet4"]["budgets"]["timeout_seconds"] = 901
    candidate = tmp_path / "policy-too-large.json"
    candidate.write_text(json.dumps(policy), encoding="utf-8")
    with pytest.raises(MODULE.PolicyError, match="Owner-approved resource envelope"):
        MODULE.load_policy(candidate)
    policy = json.loads(json.dumps(original_policy))
    policy["worktrees"]["wp12_elements"]["max_timeout_seconds"] = 901
    candidate.write_text(json.dumps(policy), encoding="utf-8")
    with pytest.raises(MODULE.PolicyError, match="Owner authorization exactly"):
        MODULE.load_policy(candidate)
    policy = json.loads(json.dumps(original_policy))
    policy["worktrees"]["wp12_tet4"]["max_total_attempts"] = 13
    candidate.write_text(json.dumps(policy), encoding="utf-8")
    with pytest.raises(MODULE.PolicyError, match="Owner authorization exactly"):
        MODULE.load_policy(candidate)


def test_wp12_attempt_ledger_enforces_total_cap_across_nodeids(tmp_path: Path) -> None:
    common = {
        "ledger_path": tmp_path / "ledger.json",
        "lock_path": tmp_path / "ledger.lock",
        "mandate_id": "DEVELOPMENT_AUTONOMOUS-WP12-TET4-2026-10-26-v1",
        "worktree_id": "wp12_tet4",
        "series_id": "dev-12345678",
        "source_fingerprint": "a" * 64,
        "reason": "synthetic cap accounting",
        "maximum": 12,
        "total_maximum": 1,
    }
    MODULE._reserve_node_attempt(**common, target="tests/unit/test_mesh.py::test_first")
    with pytest.raises(MODULE.PolicyError, match="mission cap"):
        MODULE._reserve_node_attempt(**common, target="tests/unit/test_mesh.py::test_second")


def test_wp12_dynamics_attempt_ledger_preserves_authorized_node_and_total_caps(tmp_path: Path) -> None:
    envelope = MODULE.WP12_OWNER_ENVELOPES["wp12_dynamics"]
    per_node_limit = envelope["attempt_limit_per_nodeid"]
    total_limit = envelope["max_total_attempts"]
    common = {
        "ledger_path": tmp_path / "dynamics-ledger.json",
        "lock_path": tmp_path / "dynamics-ledger.lock",
        "mandate_id": envelope["development_mandate_id"],
        "worktree_id": "wp12_dynamics",
        "source_fingerprint": "a" * 64,
        "total_maximum": total_limit,
    }

    for node_index, target in enumerate(WP12_DYNAMICS_NODEIDS):
        for attempt_index in range(per_node_limit):
            MODULE._reserve_node_attempt(
                **common,
                target=target,
                series_id=f"dev-dynamics-{node_index:02d}-{attempt_index:02d}",
                reason=f"synthetic authorized dynamics attempt {node_index:02d}-{attempt_index:02d}",
                maximum=per_node_limit,
            )
        if node_index == 0:
            with pytest.raises(MODULE.PolicyError, match=f"exhausted {per_node_limit} attempts for this nodeid"):
                MODULE._reserve_node_attempt(
                    **common,
                    target=target,
                    series_id="dev-dynamics-node-cap",
                    reason="synthetic dynamics attempt above the authorized per-node cap",
                    maximum=per_node_limit,
                )

    with pytest.raises(MODULE.PolicyError, match=f"exhausted its {total_limit}-attempt mission cap"):
        MODULE._reserve_node_attempt(
            **common,
            target="tests/unit/test_dynamic_synthetic.py::test_after_authorized_cap",
            series_id="dev-dynamics-mission-cap",
            reason="synthetic dynamics attempt above the authorized mission cap",
            maximum=per_node_limit,
        )


def test_wp12_execution_authorization_id_is_durable_and_single_use(tmp_path: Path) -> None:
    common = {
        "ledger_path": tmp_path / "ledger.json",
        "lock_path": tmp_path / "ledger.lock",
        "mandate_id": "DEVELOPMENT_AUTONOMOUS-WP12-TET4-2026-10-26-v1",
        "worktree_id": "wp12_tet4",
        "series_id": "dev-12345678",
        "source_fingerprint": "a" * 64,
        "reason": "synthetic manifest authorization ledger check",
        "maximum": 12,
        "total_maximum": 12,
        "authorization_id": "wp12-test-run-0001",
    }
    MODULE._reserve_node_attempt(**common, target="tests/unit/test_mesh.py::test_first")
    with pytest.raises(MODULE.PolicyError, match="already been consumed"):
        MODULE._reserve_node_attempt(**common, target="tests/unit/test_mesh.py::test_second")


def test_wp12_shared_resource_slots_allow_three_parallel_runs_and_exclude_overflow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(MODULE, "WP12_COORDINATION_ROOT", tmp_path / "coordination")
    first = MODULE._wp12_resource_lock(MODULE.WP12_COORDINATION_ROOT, "parallel")
    second = MODULE._wp12_resource_lock(MODULE.WP12_COORDINATION_ROOT, "parallel")
    third = MODULE._wp12_resource_lock(MODULE.WP12_COORDINATION_ROOT, "parallel")
    first.__enter__()
    second.__enter__()
    third.__enter__()
    with pytest.raises(MODULE.PolicyError, match="all shared.*busy"):
        with MODULE._wp12_resource_lock(MODULE.WP12_COORDINATION_ROOT, "parallel"):
            pass
    with pytest.raises(MODULE.PolicyError, match="another authorized scenario"):
        with MODULE._wp12_resource_lock(MODULE.WP12_COORDINATION_ROOT, "exclusive"):
            pass
    third.__exit__(None, None, None)
    second.__exit__(None, None, None)
    first.__exit__(None, None, None)
    with MODULE._wp12_resource_lock(MODULE.WP12_COORDINATION_ROOT, "exclusive"):
        pass


def test_wp12_evidence_namespaces_never_overlap(tmp_path: Path) -> None:
    roots = [
        MODULE._series_root(tmp_path / name, "fem_exploratory", worktree_id)
        for name, worktree_id in (
            ("wp07", "wp12_wp07"),
            ("tet4", "wp12_tet4"),
            ("elements", "wp12_elements"),
            ("elements-loads", "wp12_elements_loads"),
            ("dynamics", "wp12_dynamics"),
        )
    ]
    assert len(set(roots)) == 5
    for index, root in enumerate(roots):
        root.mkdir(parents=True)
        (root / "marker.json").write_text(json.dumps({"agent": index}), encoding="utf-8")
    assert [json.loads((root / "marker.json").read_text(encoding="utf-8"))["agent"] for root in roots] == [
        0,
        1,
        2,
        3,
        4,
    ]


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


def test_c01_scope_contains_only_registered_legacy_dimensional_and_mechanics_nodes() -> None:
    policy = _policy()
    c01 = policy["worktrees"]["c01"]["allowed_nodeids"]
    assert len(c01) == 18
    assert any("frozen_legacy_counterexample" in nodeid for nodeid in c01)
    assert any("dimensional_v1" in nodeid for nodeid in c01)
    assert any("contact_equilibrium_diagnostic" in nodeid for nodeid in c01)
    assert all(nodeid.startswith("tests/unit/") for nodeid in c01)
    with pytest.raises(MODULE.PolicyError, match="exact nodeid"):
        MODULE.resolve_targets(
            "fem_exploratory", "tests/unit/test_wpc01_gf5a_fe_qualification.py::test_case", policy, worktree_id="c01"
        )


def test_e01_scope_is_math_only_and_rejects_element_or_fem_targets() -> None:
    policy = _policy()
    e01 = policy["worktrees"]["e01"]["allowed_nodeids"]
    assert len(e01) == 15
    assert all("test_wp_e01" in nodeid for nodeid in e01)
    assert all(not any(word in nodeid.lower() for word in ("tet", "hex", "beam", "assembly", "fem")) for nodeid in e01)
    assert MODULE.resolve_targets("math_non_fem", e01[0], policy, worktree_id="e01") == [e01[0]]
    with pytest.raises(MODULE.PolicyError, match="exact nodeid"):
        MODULE.resolve_targets(
            "math_non_fem",
            "tests/unit/test_wp_e01m_hencky_material_point.py::test_tet4_force_adapter_matches_uniform_pk1_reference",
            policy,
            worktree_id="e01",
        )


def test_registered_worktree_identity_and_solver_source_are_verified() -> None:
    policy = _policy()
    target = policy["worktrees"]["e01"]["allowed_nodeids"][0]
    entry = policy["worktrees"]["e01"]
    assert MODULE._registered_root(entry["root"]) == MODULE.ROOT
    with pytest.raises(MODULE.PolicyError, match="branch mismatch"):
        MODULE._registered_worktree("e01", target, policy)


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
    assert "_verify_solver_import_origin(src, origin)" in command[3]
    assert "solveur.__file__" in command[3]
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
    write_xml(
        missing_xml, {key: value for key, value in properties.items() if key != "wp_d01_bj_experimental_results_json"}
    )
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
    empty_arrays_payload["responses"]["uncorrected"] = [{"mode_count": count} for count in [2] * 6 + [4] * 6]
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
    complete, errors, _metadata = MODULE._validate_d01_junit_payload(empty_roundtrip_xml, target, expected_source_sha)
    assert not complete and "exact-byte hashes" in errors[0]

    wrong_source = dict(properties)
    wrong_source["wp_d01_cg_projected_damping_m4_json"] = json.dumps(
        {**json.loads(properties["wp_d01_cg_projected_damping_m4_json"]), "source_sha": "e" * 40}
    )
    wrong_source_xml = tmp_path / "wrong-source-identity.xml"
    write_xml(wrong_source_xml, wrong_source)
    complete, errors, _metadata = MODULE._validate_d01_junit_payload(wrong_source_xml, target, expected_source_sha)
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
        PLUGIN.ExactNodeGate((nodeid,), allow_native_skip_override=True).pytest_collection_modifyitems(
            None, None, [item]
        )
        assert item.own_markers == [unrelated_skip]
        ordinary = SimpleNamespace(nodeid=nodeid, own_markers=[native_skip])
        PLUGIN.ExactNodeGate((nodeid,)).pytest_collection_modifyitems(None, None, [ordinary])
        assert ordinary.own_markers == [native_skip]

    other = SimpleNamespace(nodeid="tests/verification/test_native.py::test_other", own_markers=[native_skip])
    with pytest.raises(pytest.UsageError, match="requires exactly its registered nodeid"):
        PLUGIN.ExactNodeGate(
            (MODULE.D01_NATIVE_NODEIDS[0],), allow_native_skip_override=True
        ).pytest_collection_modifyitems(None, None, [other])
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
    monkeypatch.setattr(
        MODULE,
        "_node_ledger_context",
        lambda *_args: (
            store / "v2.json",
            store / "v2.lock",
            "v2",
            {"path": "v1", "sha256": "c" * 64, "mandate_id": "v1"},
        ),
    )
    monkeypatch.setattr(MODULE, "_run_root", lambda _policy, _worktree_id=None: store)
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
    predecessor = {
        "path": "node-attempt-ledger.json",
        "sha256": "c" * 64,
        "mandate_id": "DEVELOPMENT_AUTONOMOUS-FEM-v1",
    }
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
