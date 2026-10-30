from __future__ import annotations

import importlib.util
import base64
import copy
import hashlib
import json
import math
import subprocess
import sys
import struct
import xml.etree.ElementTree as ET
from datetime import timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

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

WP12_DYNAMICS_PREFLIGHT_NODEID = WP12_DYNAMICS_NODEIDS[0]
WP12_DYNAMICS_P0_NEW_NODEIDS = tuple(MODULE.WP12_DYNAMICS_P0_BATCH_NODEIDS[1:])
WP12B_HEX20_DIAGNOSTIC_NODEID = MODULE.WP12B_HEX20_DIAGNOSTIC_NODEID
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
WP12_ELEMENTS_LOADS_CORRECTIVE_NODEIDS = WP12_ELEMENTS_LOADS_NODEIDS
WP12_ELEMENTS_LOADS_CORRECTIVE_FINGERPRINTS = (
    "f55021a05cca3cde5014584d7236823a0936df2e6eca97887c910d99468be107",
    "cb601689e3e34227f4403ddb4108962d312fd0300a49c597775ee6c3eaf322bb",
    "34709c5f7485a55cf9debc3952927a02639cf9c57ea4a945d19829945448962e",
)


def _policy() -> dict:
    return MODULE.load_policy()


def _assert_wp12a_p0_registration_extension(current: dict[str, Any], baseline: dict[str, Any]) -> None:
    """Require a five-node append-only proposal while preserving all original entries."""
    new_nodeids = list(WP12_DYNAMICS_P0_NEW_NODEIDS)
    assert baseline["nodeid_registration"]["max_nodeids"] == 13
    assert current["nodeid_registration"] == {"enabled": True, "max_nodeids": 18}
    assert current["allowed_nodeids"] == baseline["allowed_nodeids"] + new_nodeids
    old_records = baseline["nodeid_registration_records"]
    current_records = current["nodeid_registration_records"]
    assert current_records[: len(old_records)] == old_records
    assert [record["target"] for record in current_records[-5:]] == new_nodeids
    normalized = copy.deepcopy(current)
    normalized["allowed_nodeids"] = baseline["allowed_nodeids"]
    normalized["nodeid_registration_records"] = old_records
    normalized["nodeid_registration"] = baseline["nodeid_registration"]
    # The tracked baseline predates the separately approved Dynamics v2 ledger
    # migration; this test's callers assert that predecessor link independently.
    normalized.pop("node_attempt_ledger", None)
    assert normalized == baseline


def test_release_controller_designation_is_unambiguous_and_pinned() -> None:
    import re

    repository_root = Path(__file__).resolve().parents[2]
    agents_text = (repository_root / "AGENTS.md").read_text(encoding="utf-8")
    r1_path = (
        r"E:\QFSolverAgents\controllers\wp12-vv3d-initial-controller-cda19da9\qf_solver"
        r"\scripts\development_autonomous.py"
    )
    r2_path = (
        r"E:\QFSolverAgents\controllers\wp12-vv3d-r2-controller-5e2e722\qf_solver"
        r"\scripts\development_autonomous.py"
    )
    previous_diagnostic_path = (
        r"E:\QFSolverAgents\controllers\wp12-vv3d-tet4-l3-diagnostic-controller-b6255ce7\qf_solver"
        r"\scripts\development_autonomous.py"
    )
    optimized_diagnostic_path = (
        r"E:\QFSolverAgents\controllers\wp12-vv3d-tet4-l3-optimized-98819a45\qf_solver"
        r"\scripts\development_autonomous.py"
    )
    declarations = []
    for line in agents_text.splitlines():
        if line.startswith("- "):
            paths = [
                token
                for token in re.findall(r"`([^`]+)`", line)
                if re.fullmatch(r"[A-Za-z]:\\.*\\scripts\\development_autonomous\.py", token)
            ]
            declarations.extend((path, line) for path in paths)
    assert [path for path, _ in declarations].count(r1_path) == 1
    assert [path for path, _ in declarations].count(r2_path) == 1
    assert [path for path, _ in declarations].count(previous_diagnostic_path) == 1
    assert [path for path, _ in declarations].count(optimized_diagnostic_path) == 1
    assert len(declarations) == 4
    r1 = next(line for path, line in declarations if path == r1_path)
    r2 = next(line for path, line in declarations if path == r2_path)
    previous_diagnostic = next(line for path, line in declarations if path == previous_diagnostic_path)
    optimized_diagnostic = next(line for path, line in declarations if path == optimized_diagnostic_path)
    assert "outside VV3D R2" in r1
    assert "VV3D R2 only" in r2
    assert "`wp12_vv3d_recovery_r2`" in r2
    assert "`wp12_vv3d_recovery_r2`" not in r1
    assert "TET4-L3 diagnostic only" in previous_diagnostic
    assert "`wp12_vv3d_tet4_l3_diagnostic`" in previous_diagnostic
    assert "`wp12_vv3d_tet4_l3_diagnostic`" not in r1
    assert "`wp12_vv3d_tet4_l3_diagnostic`" not in r2
    assert "VV3D TET4-L3 optimized diagnostic only" in optimized_diagnostic
    assert "`wp12_vv3d_tet4_l3_optimized_diagnostic`" in optimized_diagnostic
    assert "`wp12_vv3d_recovery_r2`" not in optimized_diagnostic
    assert "`wp12_vv3d_tet4_l3_optimized_diagnostic`" not in r1
    assert "`wp12_vv3d_tet4_l3_optimized_diagnostic`" not in r2
    assert "`wp12_vv3d_tet4_l3_diagnostic`" not in optimized_diagnostic
    assert "`wp12_vv3d_tet4_l3_optimized_diagnostic`" not in previous_diagnostic

    def assert_pin(declaration: str, label: str, value: str) -> None:
        assert re.search(rf"\b{re.escape(label)}\s+`{value}`", declaration)

    assert_pin(r1, "HEAD", "cda19da911217e2f302c295b380332d0fe34b95b")
    assert_pin(r1, "tree", "de18d79a17a4ec1722e2d83c89f4a692a00beb4a")
    assert_pin(r1, "VV3D-scope provenance fingerprint", "00f89f5dcf8540a1d257afe9f1e668b9b7bafc4a25d46436447f43a9c2cbef04")
    assert_pin(r1, "generic controller fingerprint", "d2709a82882a546613e291f56e8c561604ee6c002999518dca753ca8db37585e")
    assert_pin(r2, "HEAD", "5e2e7224661afea975cc902dae1f19bd6cdfdeb9")
    assert_pin(r2, "tree", "33970cead41711b24c3d52889de2ec8bd991189c")
    assert_pin(r2, "generic fingerprint", "5094c1f7024105b967b7718582639c77bc78f72741b0a0e7189d5ac81cc72fb5")
    assert_pin(r2, "VV3D R2-scope fingerprint", "851194718819999d483710435d0e119c799787e5962148b3e50672a99f6f387e")
    assert_pin(previous_diagnostic, "HEAD", "b6255ce70953552ca1874842d7099cde796a8a66")
    assert_pin(previous_diagnostic, "tree", "5d8435c3ae170969434315b1dab1c3ef36f6c02c")
    assert_pin(previous_diagnostic, "diagnostic-scope fingerprint", "c3d2d0946b9bf2063d4cb3bf4143877eaec0f93d2c4751178baad427d2e0c987")
    assert_pin(
        r2,
        "VV3D R1-scope fingerprint (recorded for comparison only)",
        "f4c6056d22801f7d5e3ed55013eae1e1a24d8cf73df32efe271f49b23731396e",
    )
    assert_pin(optimized_diagnostic, "HEAD", "98819a45ae5d525a670ad345a01c670721a2e67d")
    assert_pin(optimized_diagnostic, "tree", "03df7312767502014215a70e8877d9d2fa8079e3")
    assert_pin(optimized_diagnostic, "diagnostic fingerprint", "306903e538a0eb98c1805f6c443bd0c408ea836dd8b7e0cd508f09cddadcbbe8")
    assert "Controller selection is resolved only by this canonical release-branch `AGENTS.md` entry." in agents_text
    assert "do not recursively follow its snapshot `AGENTS.md`" in agents_text
    assert "wp12-shared-controller-081d788" not in agents_text
    assert "wp12-shared-controller-148f850" not in agents_text
    assert "wp12-shared-controller-final-e420c6a" not in agents_text

    tracked_agents = subprocess.run(
        ["git", "ls-files", "-z", "--", "AGENTS.md", "**/AGENTS.md"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert tracked_agents.split("\0")[:-1] == ["AGENTS.md"]

    runner_text = (repository_root / "scripts" / "development_autonomous.py").read_text(encoding="utf-8")
    assert "ROOT = Path(__file__).resolve().parents[1]" in runner_text
    workflow_text = (repository_root / ".github" / "workflows" / "wp12-controller-validation.yml").read_text(
        encoding="utf-8"
    )
    assert '      - "AGENTS.md"' in workflow_text


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
        "wp12_elements_loads_corrective",
        "wp12_dynamics",
        "rotor",
        MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID,
        MODULE.WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID,
        MODULE.WP12B_HEX20_R2_WORKTREE_ID,
        MODULE.VV3D_WORKTREE_ID,
        MODULE.VV3D_R2_WORKTREE_ID,
    }
    assert policy["worktrees"][MODULE.VV3D_WORKTREE_ID]["execution_authorized"] is False
    assert policy["worktrees"][MODULE.VV3D_R2_WORKTREE_ID]["execution_authorized"] is False
    assert policy["worktrees"][MODULE.VV3D_R2_WORKTREE_ID]["allowed_nodeids"] == list(MODULE.VV3D_INITIAL_NODEIDS)
    assert policy["worktrees"]["d01"]["attempt_limit_per_nodeid"] == 3


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ("path", "ledger path or historical predecessor identity is invalid"),
        ("mandate", "ledger path or historical predecessor identity is invalid"),
        ("sha256", "ledger path or historical predecessor identity is invalid"),
    ],
    ids=["generic-path", "wrong-predecessor-mandate", "malformed-predecessor-hash"],
)
def test_wp12_dynamics_policy_rejects_unsafe_ledger_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str, expected_error: str
) -> None:
    policy = json.loads(json.dumps(_policy()))
    config = policy["worktrees"]["wp12_dynamics"]["node_attempt_ledger"]
    if mutation == "path":
        config["path"] = "node-attempt-ledger.json"
    elif mutation == "mandate":
        config["predecessor"]["mandate_id"] = "DEVELOPMENT_AUTONOMOUS-OTHER-SCOPE"
    else:
        config["predecessor"]["sha256"] = "not-a-sha256"
    policy_path = tmp_path / "development_autonomous_policy.json"
    policy_path.write_text(json.dumps(policy, sort_keys=True) + "\n", encoding="utf-8")
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)

    with pytest.raises(MODULE.PolicyError, match=expected_error):
        MODULE.load_policy(policy_path)


def test_hex8sri_source_identity_inventory_freezes_exact_raw_worktree_bytes() -> None:
    policy = _policy()
    entry = policy["worktrees"][MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID]
    inventory_path = MODULE.ROOT / MODULE.HEX8SRI_CONVERGENCE24_SOURCE_INVENTORY_PATH
    inventory = MODULE._read_strict_json(inventory_path)
    assert MODULE._sha256(inventory_path) == MODULE.HEX8SRI_CONVERGENCE24_SOURCE_INVENTORY_SHA256
    inventory_relative = inventory_path.relative_to(MODULE.ROOT).as_posix()
    attributes = subprocess.run(
        ["git", "check-attr", "text", "--", inventory_relative],
        cwd=MODULE.ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert attributes.strip().endswith(": text: unset")
    assert entry["source_identity"] == MODULE.HEX8SRI_CONVERGENCE24_SOURCE_IDENTITY
    files = inventory["files_sha256"]
    assert len(files) == MODULE.HEX8SRI_CONVERGENCE24_SOURCE_INVENTORY_FILE_COUNT
    assert MODULE._source_inventory_fingerprint(files) == MODULE.HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT
    identity = {
        "branch": MODULE.HEX8SRI_CONVERGENCE24_SOURCE_IDENTITY["branch"],
        "head": MODULE.HEX8SRI_CONVERGENCE24_SOURCE_HEAD,
        "tree": MODULE.HEX8SRI_CONVERGENCE24_SOURCE_TREE,
    }
    MODULE._validate_hex8sri_registered_source_identity(
        Path("synthetic-source-root"),
        entry,
        identity,
        MODULE.HEX8SRI_FIRST6_NODEIDS[0],
        files,
        MODULE.HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT,
    )
    assert inventory["checkout_comparison"]["eol_only_differences"] == []
    changed_identity = {**identity, "head": "0" * 40}
    with pytest.raises(MODULE.PolicyError, match="registered science HEAD, tree or raw-byte fingerprint is stale"):
        MODULE._validate_hex8sri_registered_source_identity(
            Path("synthetic-source-root"),
            entry,
            changed_identity,
            MODULE.HEX8SRI_FIRST6_NODEIDS[0],
            files,
            MODULE.HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT,
        )
    modified_files = dict(files)
    modified_files[next(iter(modified_files))] = "0" * 64
    with pytest.raises(MODULE.PolicyError, match="source bytes differ from the registered raw-byte inventory"):
        MODULE._validate_hex8sri_registered_source_identity(
            Path("synthetic-source-root"),
            entry,
            identity,
            MODULE.HEX8SRI_FIRST6_NODEIDS[0],
            modified_files,
            MODULE.HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT,
        )
    without_criteria = dict(files)
    del without_criteria["experiments/hex8_sri_equilibrium/criteria_contract.py"]
    assert len(without_criteria) == MODULE.HEX8SRI_CONVERGENCE24_SOURCE_INVENTORY_FILE_COUNT - 1
    with pytest.raises(MODULE.PolicyError, match="source bytes differ from the registered raw-byte inventory"):
        MODULE._validate_hex8sri_registered_source_identity(
            Path("synthetic-source-root"), entry, identity, MODULE.HEX8SRI_FIRST6_NODEIDS[0],
            without_criteria, MODULE.HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT,
        )
    with pytest.raises(MODULE.PolicyError, match="registered science HEAD, tree or raw-byte fingerprint is stale"):
        MODULE._validate_hex8sri_registered_source_identity(
            Path("synthetic-source-root"), entry, identity, MODULE.HEX8SRI_FIRST6_NODEIDS[0], files, "0" * 64,
        )
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
    corrective = policy["worktrees"]["wp12_elements_loads_corrective"]
    assert corrective["execution_scope_id"] == "wp12_elements_loads"
    assert corrective["campaign_id"] == "WP12B-CORRECTIVE-R1-2026-10-26"
    assert corrective["branch"] == "emptiesvoids-cloud/fix-wp12b-scope-identity-guard"
    assert corrective["max_total_attempts"] == 3
    assert corrective["attempt_limit_per_nodeid"] == 1
    assert corrective["evidence_root"] != policy["worktrees"]["wp12_elements_loads"]["evidence_root"]
    assert corrective["development_mandate_id"] != policy["worktrees"]["wp12_elements_loads"]["development_mandate_id"]
    assert corrective["allowed_nodeids"] == list(WP12_ELEMENTS_LOADS_CORRECTIVE_NODEIDS)
    assert [record["source_fingerprint"] for record in corrective["nodeid_registration_records"]] == list(
        WP12_ELEMENTS_LOADS_CORRECTIVE_FINGERPRINTS
    )
    assert [record["selected_dofs"] for record in corrective["nodeid_registration_records"]] == [12, 30, 60]
    assert all(
        record["campaign_id"] == corrective["campaign_id"] for record in corrective["nodeid_registration_records"]
    )
    assert policy["worktrees"]["wp12_dynamics"]["attempt_limit_per_nodeid"] == 10
    assert policy["worktrees"]["wp12_dynamics"]["max_total_attempts"] == 130
    assert policy["worktrees"]["wp12_dynamics"]["max_timeout_seconds"] == 300
    assert policy["worktrees"]["wp12_dynamics"]["node_attempt_ledger"] == {
        "path": MODULE.WP12_DYNAMICS_LEDGER,
        "predecessor": {
            "path": "node-attempt-ledger.json",
            "sha256": "20670ceedfe1cc969ce614df13b8bd94b108f43e2e2892cf1601a8607a3dad37",
            "mandate_id": MODULE.WP12_DYNAMICS_LEGACY_MANDATE_ID,
        },
    }
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


def test_source_inventory_binds_recursive_test_local_imports_and_pytest_conftests(tmp_path: Path) -> None:
    root = tmp_path / "science"
    paths = {
        "tests/__init__.py": '"tests package"\n',
        "tests/unit/__init__.py": '"unit package"\n',
        "conftest.py": "from root_test_fixture import ROOT_MARKER\n",
        "root_test_fixture.py": "ROOT_MARKER = True\n",
        "tests/unit/test_hex20_diagnostic.py": (
            "from solveur.core import VALUE\nfrom wp12b_hex20_diagnostic_support import capture\n"
            "import importlib as il\nfrom importlib import import_module as load_module\n"
            "import builtins as bi\nfrom builtins import __import__ as import_by_name\n"
            "il.import_module('tests.local_importlib_helper')\nload_module('tests.local_imported_helper')\n"
            "__import__('tests.fromlist_package', fromlist=['helper'])\n"
            "bi.__import__('tests.builtins_mod_helper')\nimport_by_name('tests.builtins_alias_helper')\n"
            "def test_hex20_diagnostic():\n    assert capture() and VALUE == 1\n"
        ),
        "tests/unit/wp12b_hex20_diagnostic_support.py": (
            "from wp12b_hex20_oracle import reference\ndef capture():\n    return reference()\n"
        ),
        "tests/unit/wp12b_hex20_oracle.py": "def reference():\n    return True\n",
        "tests/conftest.py": "pytest_plugins = ['local_pytest_plugin']\nfrom common_test_fixture import FIXTURE\n",
        "tests/local_pytest_plugin.py": "from plugin_helpers import PLUGIN_MARKER\n",
        "tests/plugin_helpers.py": "PLUGIN_MARKER = True\n",
        "tests/local_importlib_helper.py": "IMPORTLIB_MARKER = True\n",
        "tests/local_imported_helper.py": "IMPORTED_MARKER = True\n",
        "tests/builtins_mod_helper.py": "BUILTINS_MARKER = True\n",
        "tests/builtins_alias_helper.py": "BUILTINS_ALIAS_MARKER = True\n",
        "tests/fromlist_package/__init__.py": '"fromlist package"\n',
        "tests/fromlist_package/helper.py": "HELPER_MARKER = True\n",
        "tests/common_test_fixture.py": "FIXTURE = True\n",
        "tests/unit/conftest.py": "from unit_test_fixture import FIXTURE\n",
        "tests/unit/unit_test_fixture.py": "FIXTURE = True\n",
        "tests/unit/test_unrelated.py": "def test_unrelated():\n    pass\n",
        "src/solveur/__init__.py": '"solver"\n',
        "src/solveur/core.py": "VALUE = 1\n",
        "experiments/hex20/reference.py": "VALUE = 1\n",
        "pyproject.toml": "[tool.pytest.ini_options]\n",
        "pytest.ini": "[pytest]\n",
    }
    for relative, content in paths.items():
        file_path = root / relative
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "--quiet"], cwd=root, check=True, capture_output=True, text=True)

    target = "tests/unit/test_hex20_diagnostic.py::test_hex20_diagnostic"
    inventory = MODULE._worktree_source_inventory(root, target)
    dependency_inventory = MODULE._test_source_dependency_inventory(root, target.split("::", maxsplit=1)[0])

    assert {
        "tests/unit/wp12b_hex20_diagnostic_support.py",
        "tests/unit/wp12b_hex20_oracle.py",
        "tests/__init__.py",
        "tests/unit/__init__.py",
        "tests/common_test_fixture.py",
        "tests/unit/unit_test_fixture.py",
        "conftest.py",
        "root_test_fixture.py",
        "tests/local_pytest_plugin.py",
        "tests/plugin_helpers.py",
        "tests/local_importlib_helper.py",
        "tests/local_imported_helper.py",
        "tests/builtins_mod_helper.py",
        "tests/builtins_alias_helper.py",
        "tests/fromlist_package/__init__.py",
        "tests/fromlist_package/helper.py",
    } <= set(dependency_inventory)
    assert {
        "tests/unit/test_hex20_diagnostic.py",
        "tests/unit/wp12b_hex20_diagnostic_support.py",
        "tests/unit/wp12b_hex20_oracle.py",
        "tests/__init__.py",
        "tests/unit/__init__.py",
        "tests/conftest.py",
        "tests/common_test_fixture.py",
        "tests/unit/conftest.py",
        "tests/unit/unit_test_fixture.py",
        "conftest.py",
        "root_test_fixture.py",
        "tests/local_pytest_plugin.py",
        "tests/plugin_helpers.py",
        "tests/local_importlib_helper.py",
        "tests/local_imported_helper.py",
        "tests/builtins_mod_helper.py",
        "tests/builtins_alias_helper.py",
        "tests/fromlist_package/__init__.py",
        "tests/fromlist_package/helper.py",
        "src/solveur/core.py",
        "experiments/hex20/reference.py",
        "pyproject.toml",
        "pytest.ini",
    } <= set(inventory)
    assert "tests/unit/test_unrelated.py" not in inventory
    original_fingerprint = MODULE._source_inventory_fingerprint(inventory)
    (root / "tests/unit/wp12b_hex20_oracle.py").write_text("def reference():\n    return False\n", encoding="utf-8")
    changed_fingerprint = MODULE._source_inventory_fingerprint(MODULE._worktree_source_inventory(root, target))
    assert changed_fingerprint != original_fingerprint


def test_source_inventory_rejects_unresolvable_dynamic_test_imports(tmp_path: Path) -> None:
    target = tmp_path / "tests" / "unit" / "test_dynamic_import.py"
    target.parent.mkdir(parents=True)
    target.write_text(
        "from importlib import import_module as load_module\n"
        "def test_dynamic_import():\n    load_module(module_name)\n",
        encoding="utf-8",
    )

    with pytest.raises(MODULE.PolicyError, match="dynamic test import cannot be source-inventoried statically"):
        MODULE._test_source_dependency_inventory(tmp_path, "tests/unit/test_dynamic_import.py")


def test_source_inventory_rejects_local_wildcard_imports(tmp_path: Path) -> None:
    package = tmp_path / "tests" / "unit" / "test_helpers"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('"helper package"\n', encoding="utf-8")
    (tmp_path / "tests" / "unit" / "test_wildcard.py").write_text(
        "from test_helpers import *\ndef test_wildcard():\n    pass\n", encoding="utf-8"
    )

    with pytest.raises(MODULE.PolicyError, match="wildcard import from a repository-local module"):
        MODULE._test_source_dependency_inventory(tmp_path, "tests/unit/test_wildcard.py")


@pytest.mark.parametrize(
    "source",
    [
        "pytest_plugins += plugin_names\n",
        "pytest_plugins.extend(plugin_names)\n",
    ],
)
def test_source_inventory_rejects_dynamic_pytest_plugin_mutations(tmp_path: Path, source: str) -> None:
    target = tmp_path / "tests" / "unit" / "test_dynamic_plugins.py"
    target.parent.mkdir(parents=True)
    target.write_text(source + "def test_dynamic_plugins():\n    pass\n", encoding="utf-8")

    with pytest.raises(MODULE.PolicyError, match="pytest_plugins mutations must be statically resolvable"):
        MODULE._test_source_dependency_inventory(tmp_path, "tests/unit/test_dynamic_plugins.py")


def test_wp12b_corrective_campaign_sets_canonical_scope_and_separate_evidence_root(tmp_path: Path) -> None:
    policy = _policy()
    original = policy["worktrees"]["wp12_elements_loads"]
    corrective = policy["worktrees"]["wp12_elements_loads_corrective"]
    environment = MODULE.build_child_environment(
        tmp_path,
        base={},
        wp12_entry={**corrective, "worktree_id": "wp12_elements_loads_corrective"},
        wp12_selection={"selected_dofs": 12},
    )
    assert environment["QF_DEV_WORKTREE_ID"] == "wp12_elements_loads"
    assert environment["QF_DEV_EVIDENCE_ROOT"] == str(Path(corrective["evidence_root"]).resolve())
    assert environment["QF_DEV_SELECTED_DOFS"] == "12"
    assert corrective["evidence_root"] != original["evidence_root"]
    assert corrective["development_mandate_id"] != original["development_mandate_id"]
    with pytest.raises(MODULE.PolicyError, match="execution-scope identity is inconsistent"):
        MODULE.build_child_environment(
            tmp_path,
            base={},
            wp12_entry={
                **corrective,
                "worktree_id": "wp12_elements_loads_corrective",
                "execution_scope_id": "wp12_elements",
            },
            wp12_selection={"selected_dofs": 12},
        )


def test_wp12b_corrective_manifest_binds_campaign_and_remains_unapproved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = WP12_ELEMENTS_LOADS_CORRECTIVE_NODEIDS[0]
    policy = _policy()
    entry = policy["worktrees"]["wp12_elements_loads_corrective"]
    test_module = tmp_path / target.split("::", maxsplit=1)[0]
    test_module.parent.mkdir(parents=True)
    test_module.write_text("def test_wp12b_beam2_rotated_uniform_line_load():\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(MODULE, "_registered_root", lambda *_args, **_kwargs: tmp_path)
    monkeypatch.setattr(MODULE, "load_policy", lambda *_args, **_kwargs: policy)
    monkeypatch.setattr(
        MODULE,
        "_registered_worktree",
        lambda *_args, **_kwargs: (
            entry,
            tmp_path,
            tmp_path / "src",
            {"head": "a" * 40},
            WP12_ELEMENTS_LOADS_CORRECTIVE_FINGERPRINTS[0],
        ),
    )
    monkeypatch.setattr(
        MODULE,
        "_wp12_active_registration",
        lambda *_args, **_kwargs: {
            "selected_dofs": 12,
            "selection_basis": "Synthetic BEAM2 total DDL selection",
            "timeout_seconds": 300,
            "timeout_reason": None,
        },
    )
    monkeypatch.setattr(MODULE, "_controller_provenance", lambda: {"identity": "synthetic"})
    evidence = tmp_path / "campaign-evidence"
    monkeypatch.setattr(MODULE, "_run_root", lambda *_args, **_kwargs: evidence)

    prepared = MODULE.prepare_wp12_execution_manifest(
        "wp12_elements_loads_corrective", target, "WP12B-CORRECTIVE-BEAM2-0001"
    )
    manifest = json.loads(Path(prepared["path"]).read_text(encoding="utf-8"))
    assert manifest["state"] == "PREPARED_NOT_AUTHORIZED"
    assert manifest["campaign_id"] == "WP12B-CORRECTIVE-R1-2026-10-26"
    assert manifest["worktree_id"] == "wp12_elements_loads_corrective"
    assert manifest["limits"]["timeout_seconds"] == 300
    assert manifest["limits"]["rss_soft_limit_mib"] == 4096
    assert manifest["owner_decision"]["status"] == "NOT_AUTHORIZED"


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


def test_wp12_registry_has_distinct_exact_worktree_envelopes() -> None:
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
        "rotor": (
            "C:\\Users\\fari\\.codex\\worktrees\\wp12-rotor-performance\\qf_solver",
            "verify/wp12-rotor-performance",
            300,
            8,
            12,
        ),
        "wp12_hex20_affine_diagnostic": (
            "C:\\Users\\fari\\.codex\\worktrees\\wp12b-hex20-r4-restore\\qf_solver",
            "emptiesvoids-cloud/wp12b-hex20-r4-assertions",
            300,
            1,
            60,
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
            assert entry["allowed_nodeids"] == [*WP12_DYNAMICS_NODEIDS, *WP12_DYNAMICS_P0_NEW_NODEIDS]
            records = entry["nodeid_registration_records"]
            assert all(len(record["worktree_head"]) == 40 for record in entry["nodeid_registration_records"])
            assert all(len(record["source_fingerprint"]) == 64 for record in entry["nodeid_registration_records"])
            assert {record["target"] for record in records} == set(
                [*WP12_DYNAMICS_NODEIDS, *WP12_DYNAMICS_P0_NEW_NODEIDS]
            )
            assert all(record["target"] in entry["allowed_nodeids"] for record in records)
            assert all(record["selected_dofs"] > 0 and record["timeout_seconds"] == 300 for record in records)
            newmark_target = "tests/unit/test_modal_newmark.py::test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables"
            newmark_records = [record for record in records if record["target"] == newmark_target]
            assert (
                "e64493e90b428ec3f41da0dcbc3ebfb5fd4cbc3d",
                "63e2972018db9bd4f8fc50947504da886e2de29ee4494c3c78422f5ec5c1536d",
            ) in {(record["worktree_head"], record["source_fingerprint"]) for record in newmark_records}
            assert (
                "d9deddbd6b42467c5fdc9e278bd54e97605f5738",
                "65e4078b1735de9adb258d1438fed39dcd69c1b68fa3560afb69896da60bdff8",
            ) in {(record["worktree_head"], record["source_fingerprint"]) for record in newmark_records}
            harmonic_target = "tests/unit/test_reduced_harmonic.py::test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation"
            harmonic_records = [record for record in records if record["target"] == harmonic_target]
            assert (
                "e64493e90b428ec3f41da0dcbc3ebfb5fd4cbc3d",
                "ff58a607ad1a5f4d3c1c632cb448219bc24746cb80623abab3886917ba749074",
            ) in {(record["worktree_head"], record["source_fingerprint"]) for record in harmonic_records}
            assert (
                "d9deddbd6b42467c5fdc9e278bd54e97605f5738",
                "bd65535cfeaff0af932fb33e556ded5c1762f2dd90a5467793bdc01c6daca50c",
            ) in {(record["worktree_head"], record["source_fingerprint"]) for record in harmonic_records}
            base_target = "tests/unit/test_wp07_uniform_base_acceleration.py::test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization"
            base_records = [record for record in records if record["target"] == base_target]
            assert (
                "e64493e90b428ec3f41da0dcbc3ebfb5fd4cbc3d",
                "6db5b4597252082012fa38b1ed5cba02190562746556d5eabd1f74a256e0f8da",
            ) in {(record["worktree_head"], record["source_fingerprint"]) for record in base_records}
            assert (
                "630d22b7667a0d84dd7b136b9f8c7d89ae00fc66",
                "969dd0276e4b9b9d4963751bcf1c06603e122aac623852f3c7a3a2c4496745c6",
            ) in {(record["worktree_head"], record["source_fingerprint"]) for record in records}
            assert all(record["timeout_seconds"] == 300 for record in records)
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
        elif worktree_id == "rotor":
            assert set(entry["allowed_nodeids"]) == MODULE.WP12_ROTOR_NODEIDS
            assert entry["attempt_limit_per_nodeid"] == 1
            assert entry["nodeid_registration"]["max_nodeids"] == 8
            assert len(entry["nodeid_registration_records"]) == 8
        elif worktree_id == "wp12_hex20_affine_diagnostic":
            assert entry["development_mandate_id"] == MODULE.WP12_OWNER_ENVELOPES[worktree_id]["development_mandate_id"]
            assert entry["campaign_id"] == MODULE.WP12_OWNER_ENVELOPES[worktree_id]["campaign_id"]
            assert entry["attempt_limit_per_nodeid"] == entry["max_total_attempts"] == 1
            assert entry["max_fem_cases_per_attempt"] == 1
            assert entry["nodeid_registration"]["max_nodeids"] == 1
            assert entry["allowed_nodeids"] in ([], [WP12B_HEX20_DIAGNOSTIC_NODEID])
            records = entry["nodeid_registration_records"]
            assert {record["target"] for record in records} == set(entry["allowed_nodeids"])
            if entry["allowed_nodeids"]:
                assert len(records) == 2
                historical, registration = records
                assert historical["target"] == registration["target"] == WP12B_HEX20_DIAGNOSTIC_NODEID
                assert historical["worktree_head"] == "31ef7593eeefa339aa1a5768df0b9c5751d66206"
                assert (
                    historical["source_fingerprint"]
                    == "0d4838a1db01ba0690fb6fcce61244f5031c4ab86fccc3ecacd9a47687209cef"
                )
                assert registration["target"] == WP12B_HEX20_DIAGNOSTIC_NODEID
                assert registration["worktree_head"] == "8f2b02b053af70cbaa23378adbd783dd99669b1b"
                assert (
                    registration["source_fingerprint"]
                    == "efe44ae1505eb130e15e8ce8c4ae5311b639353b674c94b393d75387655227fb"
                )
                assert registration["selected_dofs"] == 60
                assert registration["timeout_seconds"] == 300
                assert registration["test_source_dependencies"] == {
                    "tests/conftest.py": "8bbc1d99632bf3ba9563769100e88eaf8a8c645fc240d4e56e2e339b276669a0",
                    "tests/unit/conftest.py": "71ed98e5a7c11c64529a1098518c6e16467dc6f84d45336d4103ebf74e6fc2f6",
                    "tests/unit/wp12b_hex20_diagnostic_support.py": "865d38430e5044d72916cc7d1be42bad4cdf2f8628e0a232748168161cd52925",
                }
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


def test_dynamic_nodeids_are_allowlisted_only_for_the_dynamics_worktree(monkeypatch: pytest.MonkeyPatch) -> None:
    policy = _policy()
    monkeypatch.setattr(MODULE, "_registered_root", lambda *_args, **_kwargs: MODULE.ROOT)
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
    module.write_text(
        "from candidate_support import SUPPORT_MARKER\n\ndef test_candidate_case():\n    assert SUPPORT_MARKER\n",
        encoding="utf-8",
    )
    (agent_root / "tests" / "unit" / "candidate_support.py").write_text(
        "from candidate_oracle import ORACLE_MARKER\n\nSUPPORT_MARKER = ORACLE_MARKER\n",
        encoding="utf-8",
    )
    (agent_root / "tests" / "unit" / "candidate_oracle.py").write_text(
        "ORACLE_MARKER = True\n",
        encoding="utf-8",
    )

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

    agent_root, policy_path, target = _prepare_wp12_registration_context(tmp_path, monkeypatch)
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
    assert registration["test_source_dependencies"] == {
        "tests/unit/candidate_oracle.py": MODULE._sha256(agent_root / "tests" / "unit" / "candidate_oracle.py"),
        "tests/unit/candidate_support.py": MODULE._sha256(agent_root / "tests" / "unit" / "candidate_support.py"),
    }
    active = MODULE._wp12_active_registration("wp12_wp07", target, policy["worktrees"]["wp12_wp07"], "c" * 64)
    assert active["test_source_dependencies"] == registration["test_source_dependencies"]
    (agent_root / "tests" / "unit" / "candidate_oracle.py").write_text("ORACLE_MARKER = False\n", encoding="utf-8")
    with pytest.raises(MODULE.PolicyError, match="test-source dependency inventory changed"):
        MODULE._wp12_active_registration("wp12_wp07", target, policy["worktrees"]["wp12_wp07"], "c" * 64)
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


def test_wp12_registration_refreshes_missing_dependency_inventory_append_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _agent_root, policy_path, target = _prepare_wp12_registration_context(tmp_path, monkeypatch)
    dependencies = {
        "tests/conftest.py": "1" * 64,
        "tests/unit/candidate_support.py": "2" * 64,
        "tests/unit/candidate_oracle.py": "3" * 64,
    }
    monkeypatch.setattr(MODULE, "_test_source_dependency_inventory", lambda *_args: dependencies)
    details = {
        "selected_dofs": 12,
        "selection_basis": "Two-node BEAM2 reduced-harmonic registration metadata refresh",
    }
    MODULE.register_wp12_nodeid("wp12_wp07", target, "initial inspected source registration", **details)
    policy = MODULE.load_policy(policy_path)
    records = policy["worktrees"]["wp12_wp07"]["nodeid_registration_records"]
    records[-1].pop("test_source_dependencies")
    policy_path.write_text(json.dumps(policy, sort_keys=False) + "\n", encoding="utf-8")

    refreshed = MODULE.register_wp12_nodeid(
        "wp12_wp07",
        target,
        "Append the dependency inventory required by the controller provenance contract.",
        **details,
    )
    assert refreshed["state"] == "NODEID_REGISTERED"
    assert refreshed["revision"] == 2
    policy = MODULE.load_policy(policy_path)
    records = policy["worktrees"]["wp12_wp07"]["nodeid_registration_records"]
    assert len(records) == 2
    assert "test_source_dependencies" not in records[0]
    assert records[1]["source_fingerprint"] == records[0]["source_fingerprint"]
    assert records[1]["test_source_dependencies"] == dependencies
    active = MODULE._wp12_active_registration("wp12_wp07", target, policy["worktrees"]["wp12_wp07"], "c" * 64)
    assert active["test_source_dependencies"] == dependencies
    with pytest.raises(MODULE.PolicyError, match="already registered"):
        MODULE.register_wp12_nodeid("wp12_wp07", target, "duplicate refreshed source", **details)


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


def test_wp12_dynamics_attempt_ledger_preserves_authorized_node_and_total_caps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    envelope = MODULE.WP12_OWNER_ENVELOPES["wp12_dynamics"]
    per_node_limit = envelope["attempt_limit_per_nodeid"]
    predecessor_mandate = MODULE.WP12_DYNAMICS_LEGACY_MANDATE_ID
    predecessor_path = tmp_path / "node-attempt-ledger.json"
    predecessor_entries = {
        f"{predecessor_mandate}:wp12_dynamics:{target}": [{"attempt": index} for index in range(1, count + 1)]
        for target, count in zip(MODULE.WP12_DYNAMICS_PREFLIGHT_NODEIDS[:4], (3, 1, 1, 0), strict=True)
        if count
    }
    predecessor_path.write_text(
        json.dumps(
            {"schema": "qfsolver-development-node-ledger-v1", "mandate_id": predecessor_mandate, "entries": predecessor_entries},
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    predecessor = {
        "path": predecessor_path.name,
        "sha256": MODULE._sha256(predecessor_path),
        "mandate_id": predecessor_mandate,
    }
    policy = json.loads(json.dumps(MODULE.load_policy()))
    policy["worktrees"]["wp12_dynamics"]["node_attempt_ledger"]["predecessor"]["sha256"] = predecessor[
        "sha256"
    ]
    monkeypatch.setattr(MODULE, "load_policy", lambda *_args, **_kwargs: policy)
    common = {
        "ledger_path": tmp_path / MODULE.WP12_DYNAMICS_LEDGER,
        "lock_path": (tmp_path / MODULE.WP12_DYNAMICS_LEDGER).with_suffix(".lock"),
        "mandate_id": envelope["development_mandate_id"],
        "worktree_id": "wp12_dynamics",
        "source_fingerprint": "a" * 64,
        "total_maximum": envelope["max_total_attempts"],
        "predecessor": predecessor,
    }

    target_with_history = WP12_DYNAMICS_NODEIDS[0]
    for attempt_index in range(per_node_limit - 3):
        MODULE._reserve_node_attempt(
            **common,
            target=target_with_history,
            series_id=f"dev-dynamics-history-{attempt_index:02d}",
            reason=f"synthetic attempt accounting after legacy attempt {attempt_index:02d}",
            maximum=per_node_limit,
        )
    with pytest.raises(MODULE.PolicyError, match=f"exhausted {per_node_limit} attempts for this nodeid"):
        MODULE._reserve_node_attempt(
            **common,
            target=target_with_history,
            series_id="dev-dynamics-node-cap",
            reason="synthetic dynamics attempt above inherited per-node cap",
            maximum=per_node_limit,
        )
    node_ledger = json.loads(common["ledger_path"].read_text(encoding="utf-8"))
    node_key = f"{envelope['development_mandate_id']}:wp12_dynamics:{target_with_history}"
    assert node_ledger["predecessor"] == predecessor
    assert len(node_ledger["entries"][node_key]) == per_node_limit - 3
    assert node_ledger["entries"][node_key][-1]["predecessor_attempts_for_nodeid"] == 3

    mission_store = tmp_path / "dynamics-mission"
    mission_store.mkdir()
    (mission_store / predecessor_path.name).write_bytes(predecessor_path.read_bytes())
    policy["worktrees"]["wp12_dynamics"]["max_total_attempts"] = 6
    mission_common = {
        **common,
        "ledger_path": mission_store / MODULE.WP12_DYNAMICS_LEDGER,
        "lock_path": (mission_store / MODULE.WP12_DYNAMICS_LEDGER).with_suffix(".lock"),
        "total_maximum": 6,
    }
    MODULE._reserve_node_attempt(
        **mission_common,
        target=WP12_DYNAMICS_NODEIDS[10],
        series_id="dev-dynamics-mission-0001",
        reason="first synthetic attempt after five inherited attempts",
        maximum=per_node_limit,
    )
    with pytest.raises(MODULE.PolicyError, match="exhausted its 6-attempt mission cap"):
        MODULE._reserve_node_attempt(
            **mission_common,
            target=WP12_DYNAMICS_NODEIDS[11],
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


def test_fem_scope_accepts_only_exact_registered_nodeids_and_worktree_pairs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = _policy()
    for nodeid in policy["worktrees"]["d01"]["allowed_nodeids"]:
        module_path = tmp_path / nodeid.split("::", maxsplit=1)[0]
        module_path.parent.mkdir(parents=True, exist_ok=True)
        module_path.write_text("def test_synthetic_registered_node():\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(MODULE, "_registered_root", lambda *_args, **_kwargs: tmp_path)
    d01 = policy["worktrees"]["d01"]["allowed_nodeids"]
    for nodeid in d01:
        assert MODULE.resolve_targets("fem_exploratory", nodeid, policy, worktree_id="d01") == [nodeid]
    with pytest.raises(MODULE.PolicyError, match="exact nodeid"):
        MODULE.resolve_targets("fem_exploratory", d01[2].replace("[M3]", "[OTHER]"), policy, worktree_id="d01")
    with pytest.raises(MODULE.PolicyError, match="worktree e01 is not authorized"):
        MODULE.resolve_targets("fem_exploratory", d01[2], policy, worktree_id="e01")
    with pytest.raises(MODULE.PolicyError, match="registered worktree ID"):
        MODULE.resolve_targets("fem_exploratory", d01[2], policy)


def test_wp12_rotor_scope_is_exact_and_separate_from_dynamics() -> None:
    policy = _policy()
    rotor = MODULE.WP12_ROTOR_NODEIDS
    assert len(rotor) == 8
    assert set(policy["worktrees"]["rotor"]["allowed_nodeids"]) == rotor
    dynamics = policy["worktrees"]["wp12_dynamics"]
    assert len(dynamics["allowed_nodeids"]) == 18
    assert dynamics["nodeid_registration"]["max_nodeids"] == 18
    assert dynamics["max_total_attempts"] == 130
    assert dynamics["attempt_limit_per_nodeid"] == 10
    assert set(MODULE.WP12_DYNAMICS_P0_BATCH_NODEIDS).issubset(dynamics["allowed_nodeids"])
    assert set(MODULE.WP12_DYNAMICS_P0_BATCH_NODEIDS).issubset(MODULE.WP12_DYNAMICS_PREFLIGHT_NODEIDS)
    assert dynamics["allowed_nodeids"][-5:] == list(MODULE.WP12_DYNAMICS_P0_BATCH_NODEIDS[1:])
    assert policy["worktrees"]["rotor"]["attempt_limit_per_nodeid"] == 1
    assert policy["worktrees"]["rotor"]["max_total_attempts"] == 8

    with pytest.raises(MODULE.PolicyError, match="target must be one exact nodeid"):
        MODULE.resolve_targets(
            "fem_exploratory",
            "tests/unit/test_rotating_qep.py::test_gyro04_signed_spin_reverses_pencil_term_but_preserves_unordered_frequencies",
            policy,
            worktree_id="rotor",
        )
    with pytest.raises(MODULE.PolicyError, match="worktree rotor is not authorized"):
        MODULE.resolve_targets("math_non_fem", next(iter(rotor)), policy, worktree_id="rotor")
    with pytest.raises(MODULE.PolicyError, match="exact approved sentinel nodeids"):
        MODULE._validate_wp12_nodeid_syntax(
            "tests/unit/test_rotating_qep.py::test_unreviewed_rotor_case", worktree_id="rotor"
        )


def test_wp12_rotor_registration_and_manifest_are_synthetic_and_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from contextlib import nullcontext

    controller = tmp_path / "controller"
    agent_root = tmp_path / "rotor-agent"
    evidence_root = tmp_path / "evidence" / "rotor"
    coordination_root = tmp_path / "evidence" / ".wp12-coordination"
    controller.mkdir(parents=True)
    (agent_root / "src" / "solveur").mkdir(parents=True)
    test_root = agent_root / "tests" / "unit"
    test_root.mkdir(parents=True)
    (agent_root / "src" / "solveur" / "__init__.py").write_text('"synthetic solver"\n', encoding="utf-8")
    target = "tests/unit/test_rotating_disk_gyro.py::test_disk_mass_and_unit_speed_gyro_blocks_match_contract"
    (agent_root / target.split("::", 1)[0]).write_text(
        "def test_disk_mass_and_unit_speed_gyro_blocks_match_contract():\n    pass\n", encoding="utf-8"
    )

    envelope = dict(MODULE.WP12_OWNER_ENVELOPES["rotor"])
    envelope.update({"root": str(agent_root), "evidence_root": str(evidence_root)})
    monkeypatch.setitem(MODULE.WP12_OWNER_ENVELOPES, "rotor", envelope)
    monkeypatch.setattr(MODULE, "WP12_COORDINATION_ROOT", coordination_root)
    monkeypatch.setattr(MODULE, "ROOT", controller)
    policy_path = controller / "development_autonomous_policy.json"
    policy = json.loads((SCRIPT_PATH.parents[1] / "development_autonomous_policy.json").read_text(encoding="utf-8"))
    policy["resource_coordination_root"] = str(coordination_root)
    policy["worktrees"]["rotor"].update(
        {"root": str(agent_root), "git_root": str(agent_root), "evidence_root": str(evidence_root)}
    )
    policy_path.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(MODULE, "POLICY_PATH", policy_path)
    monkeypatch.setattr(
        MODULE,
        "_git_identity",
        lambda root, **kwargs: {
            "root": str(root),
            "branch": kwargs.get("expected_branch", "controller"),
            "head": "a" * 40,
            "tree": "b" * 40,
            "status_short": "",
        },
    )
    monkeypatch.setattr(MODULE, "_worktree_source_fingerprint", lambda *_args: "c" * 64)
    monkeypatch.setattr(MODULE, "_exclusive_file_lock", lambda _path: nullcontext())
    monkeypatch.setattr(MODULE, "_controller_provenance", lambda: {"identity": "synthetic"})
    monkeypatch.setattr(
        MODULE, "run_supervised_command", lambda *_args, **_kwargs: pytest.fail("registration must not launch pytest")
    )

    result = MODULE.register_wp12_nodeid(
        "rotor",
        target,
        "Synthetic registration of an exact rotor algebraic sentinel.",
        selected_dofs=6,
        selection_basis="Six rotational/translational DDL in the isolated disk matrix block.",
    )
    assert result["state"] == "NODEID_REGISTERED"
    assert result["timeout_seconds"] == 300
    assert MODULE.resolve_targets("fem_exploratory", target, MODULE.load_policy(policy_path), worktree_id="rotor") == [
        target
    ]
    with pytest.raises(MODULE.PolicyError, match="exact approved sentinel nodeids"):
        MODULE.register_wp12_nodeid(
            "rotor",
            "tests/unit/test_rotating_disk_gyro.py::test_disk_mass_and_gyro_are_covariant_under_global_frame_rotation",
            "Synthetic attempt to expand the rotor allowlist.",
            selected_dofs=6,
            selection_basis="An unapproved disk sentinel used only to test fail-closed behavior.",
        )

    prepared = MODULE.prepare_wp12_execution_manifest("rotor", target, "rotor-synth-0001")
    manifest = json.loads(Path(prepared["path"]).read_text(encoding="utf-8"))
    assert manifest["state"] == "PREPARED_NOT_AUTHORIZED"
    assert manifest["owner_decision"]["status"] == "NOT_AUTHORIZED"
    assert manifest["mandate_id"] == policy["worktrees"]["rotor"]["development_mandate_id"]
    assert manifest["limits"]["timeout_seconds"] == 300


@pytest.mark.parametrize("worktree_id", sorted(MODULE.WP12_OWNER_ENVELOPES))
def test_wp12_manifest_requires_the_exact_scope_mandate(tmp_path: Path, worktree_id: str) -> None:
    policy = _policy()
    entry = dict(policy["worktrees"][worktree_id])
    evidence_root = tmp_path / worktree_id
    entry["evidence_root"] = str(evidence_root)
    target = (
        entry["allowed_nodeids"]
        or [
            "tests/unit/test_wp07_uniform_base_acceleration.py::test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames"
        ]
    )[0]
    selection = {
        "timeout_seconds": entry["budgets"]["timeout_seconds"],
        "selected_dofs": 1,
        "selection_basis": "synthetic scope-mandate contract test",
        "timeout_reason": None,
    }
    payload = {
        "schema": "qfsolver-wp12-development-execution-v1",
        "state": "OWNER_AUTHORIZED",
        "authorization_id": "synthetic-mandate-0001",
        "worktree_id": worktree_id,
        "mandate_id": entry["development_mandate_id"],
        "target": target,
        "identity": {"head": "a" * 40},
        "source_fingerprint": "b" * 64,
        "controller_fingerprint": "c" * 64,
        "limits": MODULE._wp12_manifest_limits(entry, selection),
        "owner_decision": {
            "status": "APPROVED",
            "decision_id": "owner-synthetic-mandate-0001",
            "approved_by": "Owner",
            "approved_at_utc": "2026-10-27T10:00:00Z",
            "reason": "Synthetic unit test of the scope-bound mandate contract.",
        },
    }
    preflight_id = None
    preflight_receipt = None
    if worktree_id in {"wp12_dynamics", MODULE.WP12B_HEX20_R2_WORKTREE_ID}:
        payload["execution_authorized"] = True
        payload["do_not_execute"] = False
        preflight_id = "pf-123456789abc"
        preflight_path = evidence_root / "worktrees" / worktree_id / "preflight" / preflight_id / "preflight.json"
        preflight_receipt = (preflight_path, "d" * 64)
        payload["preflight"] = {
            "preflight_id": preflight_id,
            "receipt_path": str(preflight_path),
            "receipt_sha256": preflight_receipt[1],
        }
    if "campaign_id" in entry:
        payload["campaign_id"] = entry["campaign_id"]
    if worktree_id == MODULE.WP12B_HEX20_R2_WORKTREE_ID:
        payload["scientific_criteria"] = MODULE.WP12B_HEX20_R2_CRITERIA
    path = evidence_root / "authorizations" / worktree_id / "synthetic-mandate-0001.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(payload), encoding="utf-8")

    receipt = MODULE._validate_wp12_execution_manifest(
        path,
        worktree_id=worktree_id,
        target=target,
        entry=entry,
        identity=payload["identity"],
        source_fingerprint=payload["source_fingerprint"],
        controller_fingerprint=payload["controller_fingerprint"],
        selection=selection,
        preflight_id=preflight_id,
        preflight_receipt=preflight_receipt,
    )
    assert receipt["mandate_id"] == entry["development_mandate_id"]

    payload["mandate_id"] = policy["mandate_id"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(MODULE.PolicyError, match="does not bind this exact worktree"):
        MODULE._validate_wp12_execution_manifest(
            path,
            worktree_id=worktree_id,
            target=target,
            entry=entry,
            identity=payload["identity"],
            source_fingerprint=payload["source_fingerprint"],
            controller_fingerprint=payload["controller_fingerprint"],
            selection=selection,
            preflight_id=preflight_id,
            preflight_receipt=preflight_receipt,
        )


@pytest.mark.parametrize("worktree_id", sorted(MODULE.WP12_OWNER_ENVELOPES))
def test_wp12_runner_selects_scope_mandate_without_launching(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, worktree_id: str
) -> None:
    from contextlib import nullcontext

    policy = _policy()
    entry = policy["worktrees"][worktree_id]
    targets = {
        "wp12_wp07": [
            "tests/unit/test_wp07_uniform_base_acceleration.py::test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames"
        ],
        "wp12_tet4": WP12_TET4_NODEIDS,
        "wp12_elements": WP12_ELEMENTS_VERIFICATION_NODEIDS,
        "wp12_elements_loads": WP12_ELEMENTS_LOADS_NODEIDS,
        "wp12_elements_loads_corrective": WP12_ELEMENTS_LOADS_CORRECTIVE_NODEIDS,
        "wp12_dynamics": WP12_DYNAMICS_NODEIDS,
        "wp12_hex20_affine_diagnostic": (WP12B_HEX20_DIAGNOSTIC_NODEID,),
        MODULE.WP12B_HEX20_R2_WORKTREE_ID: (WP12B_HEX20_DIAGNOSTIC_NODEID,),
        "rotor": tuple(MODULE.WP12_ROTOR_NODEIDS),
    }
    target = targets[worktree_id][0]
    store = tmp_path / "store" / worktree_id
    if worktree_id == "wp12_dynamics":
        store.mkdir(parents=True)
        predecessor_path = store / "node-attempt-ledger.json"
        predecessor_payload = {
            "schema": "qfsolver-development-node-ledger-v1",
            "mandate_id": MODULE.WP12_DYNAMICS_LEGACY_MANDATE_ID,
            "entries": {},
        }
        predecessor_path.write_text(json.dumps(predecessor_payload, sort_keys=True) + "\n", encoding="utf-8")
        entry["node_attempt_ledger"]["predecessor"]["sha256"] = MODULE._sha256(predecessor_path)
    observed: dict[str, str] = {}

    class StopBeforeAttempt(Exception):
        pass

    monkeypatch.setattr(MODULE, "load_policy", lambda: policy)
    monkeypatch.setattr(MODULE, "resolve_targets", lambda *_args, **_kwargs: [target])
    monkeypatch.setattr(
        MODULE,
        "_registered_worktree",
        lambda *_args, **_kwargs: (entry, tmp_path, tmp_path / "src", {"head": "a" * 40}, "b" * 64),
    )
    monkeypatch.setattr(
        MODULE,
        "_wp12_active_registration",
        lambda *_args, **_kwargs: {
            "timeout_seconds": entry["budgets"]["timeout_seconds"],
            "selected_dofs": 1,
            "selection_basis": "synthetic runner contract test",
            "timeout_reason": None,
        },
    )
    monkeypatch.setattr(MODULE, "_controller_provenance", lambda: {"identity": "synthetic"})
    monkeypatch.setattr(MODULE, "_stable_fingerprint", lambda _value: "c" * 64)
    synthetic_manifest = tmp_path / "synthetic-authorized-manifest.json"
    synthetic_manifest.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        MODULE,
        "_validate_wp12_execution_manifest",
        lambda *_a, **_kw: {
            "authorized": True,
            "decision_id": "owner-synthetic-0001",
            "owner_decision": {"decision_id": "owner-synthetic-0001"},
            "path": str(synthetic_manifest),
            "sha256": MODULE._sha256(synthetic_manifest),
        },
    )
    if worktree_id == "wp12_dynamics":
        synthetic_preflight = tmp_path / "preflight.json"
        synthetic_preflight.write_text(json.dumps({"attempt_ledger": {"sha256_after": None}}), encoding="utf-8")
        monkeypatch.setattr(
            MODULE,
            "_validate_wp12_dynamics_preflight_receipt",
            lambda *_args, **_kwargs: (synthetic_preflight, MODULE._sha256(synthetic_preflight)),
        )
    elif worktree_id == MODULE.WP12B_HEX20_R2_WORKTREE_ID:
        synthetic_preflight = tmp_path / "preflight.json"
        synthetic_preflight.write_text(json.dumps({"attempt_ledger": {"sha256_after": None}}), encoding="utf-8")
        monkeypatch.setattr(
            MODULE, "_validate_wp12b_hex20_r2_preflight_receipt",
            lambda *_args, **_kwargs: (synthetic_preflight, MODULE._sha256(synthetic_preflight)),
        )
    monkeypatch.setattr(MODULE, "_run_root", lambda *_args, **_kwargs: store)
    monkeypatch.setattr(MODULE, "_wp12_resource_lock", lambda *_args, **_kwargs: nullcontext())
    monkeypatch.setattr(MODULE, "psutil", object())
    monkeypatch.setattr(MODULE.shutil, "disk_usage", lambda _path: SimpleNamespace(free=2 * 1024**3))
    original_ledger_context = MODULE._node_ledger_context

    def observe_ledger_context(*args: Any) -> tuple[Path, Path, str, dict[str, str] | None]:
        context = (
            (store / "synthetic.json", store / "synthetic.lock", entry["development_mandate_id"], None)
            if worktree_id == MODULE.WP12B_HEX20_R2_WORKTREE_ID else original_ledger_context(*args)
        )
        observed["mandate_id"] = context[2]
        return context

    monkeypatch.setattr(MODULE, "_node_ledger_context", observe_ledger_context)
    monkeypatch.setattr(
        MODULE,
        "_next_attempt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(StopBeforeAttempt()),
    )
    monkeypatch.setattr(
        MODULE,
        "run_supervised_command",
        lambda *_args, **_kwargs: pytest.fail("synthetic contract test must never launch a process"),
    )

    with pytest.raises(StopBeforeAttempt):
        MODULE.run_pytest(
            "fem_exploratory",
            target,
            "dev-mandate-propagation",
            worktree_id=worktree_id,
            reason="Synthetic pre-attempt mandate propagation test.",
            preflight_id="pf-123456789abc"
            if worktree_id in {"wp12_dynamics", MODULE.WP12B_HEX20_R2_WORKTREE_ID} else None,
            execution_manifest=tmp_path / "synthetic-authorized-manifest.json",
        )
    assert observed["mandate_id"] == entry["development_mandate_id"]


def test_wp12_scope_mandate_change_refuses_legacy_ledger_without_rewriting_it(tmp_path: Path) -> None:
    policy = _policy()
    rotor_mandate = policy["worktrees"]["rotor"]["development_mandate_id"]
    legacy_mandate = policy["mandate_id"]
    ledger = tmp_path / "node-attempt-ledger.json"
    lock = tmp_path / "node-attempt-ledger.lock"
    legacy_payload = {
        "schema": "qfsolver-development-node-ledger-v1",
        "mandate_id": legacy_mandate,
        "entries": {f"{legacy_mandate}:rotor:synthetic-node": [{"state": "PASS"}]},
    }
    ledger.write_text(json.dumps(legacy_payload), encoding="utf-8")
    original = ledger.read_bytes()

    with pytest.raises(MODULE.PolicyError, match="ledger identity/schema mismatch"):
        MODULE._reserve_node_attempt(
            ledger,
            lock,
            mandate_id=rotor_mandate,
            worktree_id="rotor",
            target="synthetic-node",
            series_id="dev-synthetic-legacy-ledger",
            source_fingerprint="a" * 64,
            reason="Synthetic ledger continuity guard.",
            maximum=1,
            total_maximum=8,
        )
    assert ledger.read_bytes() == original


def test_wp12b_corrective_manifest_and_reservation_share_scope_mandate(tmp_path: Path) -> None:
    policy = _policy()
    worktree_id = "wp12_elements_loads_corrective"
    entry = dict(policy["worktrees"][worktree_id])
    evidence_root = tmp_path / "corrective-evidence"
    entry["evidence_root"] = str(evidence_root)
    target = WP12_ELEMENTS_LOADS_CORRECTIVE_NODEIDS[0]
    registration = next(record for record in entry["nodeid_registration_records"] if record["target"] == target)
    selection = MODULE._validate_wp12_case_selection(
        worktree_id,
        selected_dofs=registration["selected_dofs"],
        selection_basis=registration["selection_basis"],
        timeout_seconds=registration["timeout_seconds"],
        timeout_reason=registration["timeout_reason"],
    )
    identity = {"head": "d" * 40, "tree": "e" * 40, "status_short": ""}
    source_fingerprint = registration["source_fingerprint"]
    controller_fingerprint = "f" * 64
    authorization_id = "wp12b-corrective-synthetic-001"
    payload = {
        "schema": "qfsolver-wp12-development-execution-v1",
        "state": "OWNER_AUTHORIZED",
        "authorization_id": authorization_id,
        "worktree_id": worktree_id,
        "campaign_id": entry["campaign_id"],
        "mandate_id": entry["development_mandate_id"],
        "target": target,
        "identity": identity,
        "source_fingerprint": source_fingerprint,
        "controller_fingerprint": controller_fingerprint,
        "limits": MODULE._wp12_manifest_limits(entry, selection),
        "owner_decision": {
            "status": "APPROVED",
            "approved_by": "Owner",
            "approved_at_utc": "2026-10-27T10:00:00Z",
            "reason": "Synthetic test of corrective scope manifest and reservation identity.",
        },
    }
    manifest_path = evidence_root / "authorizations" / worktree_id / f"{authorization_id}.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    manifest_receipt = MODULE._validate_wp12_execution_manifest(
        manifest_path,
        worktree_id=worktree_id,
        target=target,
        entry=entry,
        identity=identity,
        source_fingerprint=source_fingerprint,
        controller_fingerprint=controller_fingerprint,
        selection=selection,
    )

    ledger_path = tmp_path / "corrective-ledger.json"
    ledger_key, attempt_number = MODULE._reserve_node_attempt(
        ledger_path,
        tmp_path / "corrective-ledger.lock",
        mandate_id=manifest_receipt["mandate_id"],
        worktree_id=worktree_id,
        target=target,
        series_id="dev-corrective-manifest-test",
        source_fingerprint=source_fingerprint,
        reason="Synthetic manifest-to-reservation identity test.",
        maximum=entry["attempt_limit_per_nodeid"],
        total_maximum=entry["max_total_attempts"],
        wp12_selection={**registration, **selection},
        authorization_id=manifest_receipt["authorization_id"],
        controller_fingerprint=controller_fingerprint,
    )
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert attempt_number == 1
    assert ledger["mandate_id"] == entry["development_mandate_id"]
    assert ledger_key.startswith(f"{entry['development_mandate_id']}:{worktree_id}:")
    assert ledger["entries"][ledger_key][0]["authorization_id"] == authorization_id


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


@pytest.mark.parametrize(
    "target",
    [
        "tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[100.0]",
        "tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[-100.0]",
    ],
)
def test_rotor_collect_only_command_keeps_exact_parameterized_nodeid(tmp_path: Path, target: str) -> None:
    policy = _policy()
    command = MODULE.build_pytest_command(
        "fem_exploratory",
        [target],
        tmp_path / "tmp",
        repository_root=Path(policy["worktrees"]["rotor"]["root"]),
        source_root=Path(policy["worktrees"]["rotor"]["root"]) / "src",
        rotor_collect_only_attestation=True,
        collect_only=True,
    )
    assert "--collect-only" in command
    assert command[-1] == target
    assert "rotor-preflight" in command[3]
    assert "ExactCollectOnlyAttestor" in command[3]
    assert "mode == 'd01' and False" in command[3]
    with pytest.raises(MODULE.PolicyError, match="requires collect-only"):
        MODULE.build_pytest_command(
            "fem_exploratory",
            [target],
            tmp_path / "tmp",
            source_root=Path(policy["worktrees"]["rotor"]["root"]) / "src",
            rotor_collect_only_attestation=True,
        )


def test_rotor_collect_only_attestation_rejects_nodeid_outside_rotor_allowlist(tmp_path: Path) -> None:
    policy = _policy()
    with pytest.raises(MODULE.PolicyError, match="exact rotor nodeid allowlist"):
        MODULE.build_pytest_command(
            "fem_exploratory",
            ["tests/unit/test_static_linear.py::test_anything"],
            tmp_path / "tmp",
            repository_root=Path(policy["worktrees"]["rotor"]["root"]),
            source_root=Path(policy["worktrees"]["rotor"]["root"]) / "src",
            rotor_collect_only_attestation=True,
            collect_only=True,
        )


@pytest.mark.parametrize(
    "target",
    [
        "tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[100.0]",
        "tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[-100.0]",
    ],
)
def test_rotor_collect_attestor_reports_exact_node_scope_and_no_body(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], target: str
) -> None:
    monkeypatch.setenv("QF_DEV_WORKTREE_ID", "rotor")
    monkeypatch.setenv("QF_DEV_SELECTED_DOFS", "2")
    monkeypatch.setenv("QF_DEV_MAX_DOFS", "12")
    item = SimpleNamespace(nodeid=target, iter_markers=lambda: iter(()))
    attestor = PLUGIN.ExactCollectOnlyAttestor(
        target,
        solver_origin=r"C:\synthetic\src\solveur\__init__.py",
        selected_dofs=2,
        max_dofs=12,
    )
    attestor.pytest_collection_finish(SimpleNamespace(items=[item]))
    attestor.pytest_sessionfinish(SimpleNamespace(), 0)
    output = capsys.readouterr().out
    state, payload = MODULE._validate_rotor_collect_attestation(
        output,
        target=target,
        solver_origin=r"C:\synthetic\src\solveur\__init__.py",
        selected_dofs=2,
        max_dofs=12,
    )
    assert state == "PREFLIGHT_PASS"
    assert payload is not None
    assert payload["collected_nodeids"] == [target]
    assert payload["skip_markers"] == []
    assert payload["bodies_executed"] is False


@pytest.mark.parametrize(
    ("payload_changes", "expected_state"),
    [
        ({"collected_nodeids": ["tests/unit/test_rotating_qep.py::test_other"]}, "PREFLIGHT_NODEID_NOT_CONFIRMED"),
        ({"solver_origin": r"C:\\global\\site-packages\\solveur\\__init__.py"}, "PREFLIGHT_WRONG_SOLVER_ORIGIN"),
        ({"skip_markers": [{"nodeid": "target", "marker": "skip", "reason": "synthetic"}]}, "PREFLIGHT_SKIPPED"),
        ({"bodies_executed": True}, "PREFLIGHT_BODY_EXECUTION_DETECTED"),
        ({"worktree_id": "wp12_dynamics"}, "PREFLIGHT_SCOPE_MISMATCH"),
    ],
)
def test_rotor_collect_attestation_rejects_wrong_scope_skip_import_or_selection(
    payload_changes: dict[str, object], expected_state: str
) -> None:
    payload: dict[str, object] = {
        "schema": "qfsolver-rotor-collect-only-v1",
        "expected_nodeid": "target",
        "collected_nodeids": ["target"],
        "skip_markers": [],
        "bodies_executed": False,
        "solver_origin": "expected-origin",
        "worktree_id": "rotor",
        "selected_dofs_expected": 2,
        "selected_dofs": "2",
        "max_dofs_expected": 12,
        "max_dofs": "12",
        "exitstatus": 0,
    }
    payload.update(payload_changes)
    output = MODULE.ROTOR_PREFLIGHT_ATTESTATION_PREFIX + json.dumps(payload)
    state, _ = MODULE._validate_rotor_collect_attestation(
        output, target="target", solver_origin="expected-origin", selected_dofs=2, max_dofs=12
    )
    assert state == expected_state


def test_rotor_preflight_refuses_a_fake_solver_import_path(tmp_path: Path) -> None:
    source_root = tmp_path / "source" / "src"
    expected = source_root / "solveur" / "__init__.py"
    wrong = tmp_path / "venv" / "site-packages" / "solveur" / "__init__.py"
    expected.parent.mkdir(parents=True)
    wrong.parent.mkdir(parents=True)
    expected.write_text("", encoding="utf-8")
    wrong.write_text("", encoding="utf-8")
    with pytest.raises(MODULE.PolicyError, match="wrong solveur import origin"):
        MODULE._verify_solver_import_origin(source_root, wrong)


@pytest.mark.parametrize(
    ("worktree_id", "expected_message"),
    [
        ("wp12_dynamics", "limited to its reviewed exact registered nodeids"),
        ("wp12_hex20_affine_diagnostic", "limited to its exact registered nodeid"),
        ("wp12_elements", "enabled only for D01, rotor, WP12 dynamics, WP12-B HEX20 diagnostic"),
        ("c01", "enabled only for D01, rotor, WP12 dynamics, WP12-B HEX20 diagnostic"),
        ("e01", "enabled only for D01, rotor, WP12 dynamics, WP12-B HEX20 diagnostic"),
    ],
)
def test_collect_only_preflight_does_not_expand_to_other_scopes(
    monkeypatch: pytest.MonkeyPatch, worktree_id: str, expected_message: str
) -> None:
    monkeypatch.setattr(MODULE, "load_policy", lambda *_args, **_kwargs: {})
    with pytest.raises(MODULE.PolicyError, match=expected_message):
        MODULE.preflight_pytest(worktree_id, "tests/unit/test_anything.py::test_case")


def test_preflight_cli_routes_only_explicit_registered_scopes(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    target = "tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[100.0]"
    monkeypatch.setattr(
        MODULE,
        "preflight_pytest",
        lambda worktree, nodeid, preflight_id=None: {
            "state": "PREFLIGHT_PASS",
            "worktree": worktree,
            "nodeid": nodeid,
        },
    )
    assert MODULE.main(["preflight", "--worktree", "rotor", "--target", target]) == 0
    assert json.loads(capsys.readouterr().out)["worktree"] == "rotor"
    dynamics_target = WP12_DYNAMICS_PREFLIGHT_NODEID
    assert MODULE.main(["preflight", "--worktree", "wp12_dynamics", "--target", dynamics_target]) == 0
    assert json.loads(capsys.readouterr().out)["worktree"] == "wp12_dynamics"
    hex20_target = WP12B_HEX20_DIAGNOSTIC_NODEID
    assert MODULE.main(["preflight", "--worktree", "wp12_hex20_affine_diagnostic", "--target", hex20_target]) == 0
    assert json.loads(capsys.readouterr().out)["worktree"] == "wp12_hex20_affine_diagnostic"
    with pytest.raises(SystemExit) as exc:
        MODULE.main(["preflight", "--worktree", "unknown", "--target", target])
    assert exc.value.code == 2


def test_rotor_preflight_uses_rotor_evidence_and_never_reserves_an_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = "tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[100.0]"
    policy = json.loads(json.dumps(_policy()))
    entry = policy["worktrees"]["rotor"]
    fake_root = tmp_path / "rotor-source"
    source_root = fake_root / "src"
    (source_root / "solveur").mkdir(parents=True)
    (source_root / "solveur" / "__init__.py").write_text("", encoding="utf-8")
    (fake_root / "tests" / "unit").mkdir(parents=True)
    (fake_root / "tests" / "unit" / "test_rotating_qep.py").write_text("", encoding="utf-8")
    evidence_root = tmp_path / "evidence" / "rotor"
    coordination_root = tmp_path / "coordination"
    entry["root"] = entry["git_root"] = str(fake_root)
    entry["evidence_root"] = str(evidence_root)
    selection = {
        "selected_dofs": 2,
        "selection_basis": "synthetic selection",
        "timeout_seconds": 300,
        "timeout_reason": None,
    }
    identity = {
        "root": str(fake_root),
        "branch": entry["branch"],
        "head": "a" * 40,
        "tree": "b" * 40,
        "status_short": "",
    }
    monkeypatch.setattr(MODULE, "load_policy", lambda *_args, **_kwargs: policy)
    monkeypatch.setattr(MODULE, "WP12_COORDINATION_ROOT", coordination_root)
    monkeypatch.setattr(
        MODULE.shutil,
        "disk_usage",
        lambda *_args: SimpleNamespace(free=2 * 1024 * 1024 * 1024),
    )
    monkeypatch.setattr(
        MODULE, "_registered_worktree", lambda *_args, **_kwargs: (entry, fake_root, source_root, identity, "c" * 64)
    )
    monkeypatch.setattr(MODULE, "_wp12_active_registration", lambda *_args, **_kwargs: selection)
    monkeypatch.setattr(MODULE, "_controller_provenance", lambda: {"identity": "synthetic"})
    monkeypatch.setattr(MODULE, "psutil", object())
    monkeypatch.setattr(
        MODULE,
        "_reserve_node_attempt",
        lambda *_args, **_kwargs: pytest.fail("collect-only preflight must not reserve a scientific attempt"),
    )

    def fake_supervised(command, *, cwd, environment, output_dir, temporary_dir, limits, poll_interval):
        assert command[-1] == target and "--collect-only" in command
        assert environment["QF_DEV_WORKTREE_ID"] == "rotor"
        assert environment["QF_DEV_SELECTED_DOFS"] == "2"
        assert environment["QF_DEV_MAX_DOFS"] == "12"
        origin = str((source_root / "solveur" / "__init__.py").resolve())
        payload = {
            "schema": "qfsolver-rotor-collect-only-v1",
            "expected_nodeid": target,
            "collected_nodeids": [target],
            "skip_markers": [],
            "bodies_executed": False,
            "solver_origin": origin,
            "worktree_id": "rotor",
            "selected_dofs_expected": 2,
            "selected_dofs": "2",
            "max_dofs_expected": 12,
            "max_dofs": "12",
            "exitstatus": 0,
        }
        (output_dir / "stdout.log").write_text(
            f"QF_DEV_SOLVER_ORIGIN={origin}\n{MODULE.ROTOR_PREFLIGHT_ATTESTATION_PREFIX}{json.dumps(payload)}\n",
            encoding="utf-8",
        )
        (output_dir / "stderr.log").write_text("", encoding="utf-8")
        return SimpleNamespace(
            status="PASS",
            return_code=0,
            elapsed_seconds=0.1,
            peak_rss_bytes=1,
            peak_process_count=1,
            stdout_bytes=10,
            stderr_bytes=0,
            archive_bytes=0,
            temporary_bytes=0,
            stop_reason=None,
        )

    monkeypatch.setattr(MODULE, "run_supervised_command", fake_supervised)
    result = MODULE.preflight_pytest("rotor", target, "pf-0123456789ab")
    assert result["state"] == "PREFLIGHT_PASS"
    assert result["bodies_executed"] is False
    assert result["nodeid"] == target
    receipt = json.loads(Path(result["receipt"]).read_text(encoding="utf-8"))
    assert receipt["attempt_reserved"] is False
    assert receipt["collected_nodeids"] == [target]
    assert receipt["worktree_id_observed"] == "rotor"
    receipt_hash = json.loads((Path(result["receipt"]).parent / "preflight.sha256.json").read_text(encoding="utf-8"))
    assert receipt_hash["sha256"] == MODULE._sha256(Path(result["receipt"]))


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
    from contextlib import contextmanager
    import os

    policy = _policy()
    nodeid = policy["worktrees"]["d01"]["allowed_nodeids"][0]
    boundary = "solveur.core.analyses.reduced_harmonic.ReducedHarmonicResponseSolver.solve"
    active_scope: dict[str, str | None] = {"nodeid": None}
    guard = ModuleType("solveur.core.execution_guard")
    guard.NO_NATIVE_EXECUTION_ENV = "QF_DEV_NO_NATIVE_EXECUTION"

    class SolverExecutionBlockedError(RuntimeError):
        pass

    @contextmanager
    def authorized_native_test_scope(authorized_nodeid: str):
        previous = active_scope["nodeid"]
        active_scope["nodeid"] = authorized_nodeid
        try:
            yield
        finally:
            active_scope["nodeid"] = previous

    def require_solver_execution_allowed(requested_boundary: str) -> None:
        if (
            requested_boundary != boundary
            or active_scope["nodeid"] != nodeid
            or guard.NO_NATIVE_EXECUTION_ENV in os.environ
        ):
            raise SolverExecutionBlockedError("synthetic native execution denied")

    guard.SolverExecutionBlockedError = SolverExecutionBlockedError
    guard.authorized_native_test_scope = authorized_native_test_scope
    guard.require_solver_execution_allowed = require_solver_execution_allowed
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


HEX8SRI_PRE_REFRESH_POLICY_BASELINE = "326b357fe752b33bb034c46ed546973abb1d2cb0"


def _hex8sri_pre_refresh_baseline() -> dict:
    payload = subprocess.run(
        ["git", "show", f"{HEX8SRI_PRE_REFRESH_POLICY_BASELINE}:development_autonomous_policy.json"],
        cwd=MODULE.ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return json.loads(payload)["worktrees"][MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID]


def _assert_hex8sri_source_refresh_only(current: dict, baseline: dict) -> None:
    mutable = {"branch", "source_identity", "source_fingerprint_sha256", "case_manifests"}
    assert set(current) == set(baseline)
    assert {key: current[key] for key in current if key not in mutable} == {
        key: baseline[key] for key in baseline if key not in mutable
    }
    assert current["source_identity"] == MODULE.HEX8SRI_CONVERGENCE24_SOURCE_IDENTITY
    assert current["source_fingerprint_sha256"] == MODULE.HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT
    current_cases, baseline_cases = current["case_manifests"], baseline["case_manifests"]
    assert set(current_cases) == set(baseline_cases) == set(MODULE._hex8sri_convergence24_nodeids())
    for nodeid in current_cases:
        assert current_cases[nodeid]["path"] == baseline_cases[nodeid]["path"]
        if nodeid in MODULE.HEX8SRI_REFINED3_NODEIDS:
            assert current_cases[nodeid]["sha256"] != baseline_cases[nodeid]["sha256"]
        else:
            assert current_cases[nodeid]["sha256"] == baseline_cases[nodeid]["sha256"]
        assert len(current_cases[nodeid]["sha256"]) == 64


def test_hex8sri_convergence24_registration_preserves_all_existing_scope_bytes_semantically() -> None:
    policy = _policy()
    worktrees = policy["worktrees"]
    scope_id = MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID
    baseline = json.loads(
        subprocess.run(
            ["git", "show", "e25b32272d974dd1f34c03617721f95befde87de:development_autonomous_policy.json"],
            cwd=MODULE.ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    hex20_scope_id = MODULE.WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID
    assert set(worktrees) == set(baseline["worktrees"]) | {
        hex20_scope_id, MODULE.WP12B_HEX20_R2_WORKTREE_ID, MODULE.VV3D_WORKTREE_ID,
        MODULE.VV3D_R2_WORKTREE_ID,
    }
    existing = {key: value for key, value in worktrees.items() if key != hex20_scope_id}
    for worktree_id, baseline_entry in baseline["worktrees"].items():
        if worktree_id == "wp12_dynamics":
            continue
        if worktree_id == scope_id:
            _assert_hex8sri_source_refresh_only(existing[worktree_id], _hex8sri_pre_refresh_baseline())
            continue
        assert existing[worktree_id] == baseline_entry
    dynamics_baseline = baseline["worktrees"]["wp12_dynamics"]
    dynamics_current = existing["wp12_dynamics"]
    assert dynamics_current["node_attempt_ledger"] == {
        "path": MODULE.WP12_DYNAMICS_LEDGER,
        "predecessor": {
            "path": "node-attempt-ledger.json",
            "sha256": "20670ceedfe1cc969ce614df13b8bd94b108f43e2e2892cf1601a8607a3dad37",
            "mandate_id": MODULE.WP12_DYNAMICS_LEGACY_MANDATE_ID,
        },
    }
    _assert_wp12a_p0_registration_extension(dynamics_current, dynamics_baseline)
    assert (
        dynamics_current["nodeid_registration_records"][: len(dynamics_baseline["nodeid_registration_records"])]
        == (dynamics_baseline["nodeid_registration_records"])
    )
    current_wp07_target = (
        "tests/unit/test_wp07_uniform_base_acceleration.py::"
        "test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames"
    )
    current_wp07_registrations = {
        (record["worktree_head"], record["source_fingerprint"], record["timeout_seconds"])
        for record in dynamics_current["nodeid_registration_records"]
        if record["target"] == current_wp07_target
    }
    assert (
        "630d22b7667a0d84dd7b136b9f8c7d89ae00fc66",
        "969dd0276e4b9b9d4963751bcf1c06603e122aac623852f3c7a3a2c4496745c6",
        300,
    ) in current_wp07_registrations
    entry = worktrees[scope_id]
    assert entry["allowed_nodeids"] == list(MODULE._hex8sri_convergence24_nodeids())
    assert len(entry["allowed_nodeids"]) == 24
    assert entry["execution_authorized"] is False
    assert entry["attempt_limit_per_nodeid"] == 1
    assert entry["node_attempt_ledger"]["path"] == MODULE.HEX8SRI_CONVERGENCE24_LEDGER
    hex20_entry = worktrees[hex20_scope_id]
    assert hex20_entry["allowed_nodeids"] in ([], [WP12B_HEX20_DIAGNOSTIC_NODEID])
    assert hex20_entry["max_total_attempts"] == hex20_entry["attempt_limit_per_nodeid"] == 1


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ("execution_authorized", "preparation-only mandate is invalid"),
        ("nodeid", "preparation-only mandate is invalid"),
        ("ledger", "preparation-only mandate is invalid"),
        ("budget", "shared budget must equal the largest registered case budget"),
    ],
    ids=("auth", "nodeid", "ledger", "budget"),
)
def test_hex8sri_convergence24_policy_refuses_scope_tampering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    expected_error: str,
) -> None:
    policy = _policy()
    scope_id = MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID
    entry = policy["worktrees"][scope_id]
    if mutation == "execution_authorized":
        entry["execution_authorized"] = True
    elif mutation == "nodeid":
        entry["allowed_nodeids"].append("tests/verification/test_elsewhere.py::test_extra")
    elif mutation == "ledger":
        entry["node_attempt_ledger"]["path"] = "node-attempt-ledger.json"
    else:
        entry["budgets"]["rss_soft_limit_mib"] = 1024
    policy_path = tmp_path / "development_autonomous_policy.json"
    policy_path.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)
    with pytest.raises(MODULE.PolicyError, match=expected_error):
        MODULE.load_policy(path=policy_path)


@pytest.mark.parametrize(
    ("mesh_token", "expected"),
    [
        ("4x2x2", (16, 45, 135, 27, 108)),
        ("8x4x4", (128, 225, 675, 75, 600)),
        ("16x8x8", (1024, 1377, 4131, 243, 3888)),
        ("32x16x16", (8192, 9537, 28611, 867, 27744)),
    ],
)
def test_hex8sri_convergence24_mesh_contract_is_algebraic_and_exact(
    mesh_token: str, expected: tuple[int, int, int, int, int]
) -> None:
    nx, ny, nz = (int(part) for part in mesh_token.split("x"))
    manifest = {
        "mesh": {
            "divisions_xyz": [nx, ny, nz],
            "element_count": expected[0],
            "node_count": expected[1],
            "dof_count": expected[2],
            "fixed_dof_count": expected[3],
            "free_dof_count": expected[4],
        }
    }
    contract = MODULE._hex8sri_convergence24_case_contract(manifest)
    assert (
        tuple(
            contract[key] for key in ("element_count", "node_count", "dof_count", "fixed_dof_count", "free_dof_count")
        )
        == expected
    )
    manifest["mesh"]["free_dof_count"] += 1
    with pytest.raises(MODULE.PolicyError, match="DDL or element counts"):
        MODULE._hex8sri_convergence24_case_contract(manifest)


def test_hex8sri_convergence24_collect_command_is_exact_collect_only(tmp_path: Path) -> None:
    target = MODULE._hex8sri_convergence24_nodeids()[0]
    command = MODULE.build_pytest_command(
        "fem_exploratory",
        [target],
        tmp_path / "tmp",
        repository_root=tmp_path,
        source_root=tmp_path / "src",
        controller_root=tmp_path,
        collect_only=True,
        hex8sri_convergence24_collect_only_attestation=True,
    )
    assert command[-1] == target
    assert "--collect-only" in command
    bootstrap = command[command.index("-c") + 1]
    assert "Hex8SRIConvergence24Attestor" in bootstrap
    assert "allow_native_skip_override=True" not in bootstrap
    with pytest.raises(MODULE.PolicyError, match="exact preparation-only collect-only"):
        MODULE.build_pytest_command(
            "fem_exploratory",
            [target],
            tmp_path / "tmp",
            repository_root=tmp_path,
            source_root=tmp_path / "src",
            controller_root=tmp_path,
            collect_only=False,
            hex8sri_convergence24_collect_only_attestation=True,
        )


def test_preflight_cli_routes_hex8sri_scope_without_execution(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    target = MODULE._hex8sri_convergence24_nodeids()[0]
    monkeypatch.setattr(
        MODULE,
        "preflight_pytest",
        lambda worktree, nodeid, preflight_id=None: {
            "state": "PREFLIGHT_PASS",
            "worktree": worktree,
            "nodeid": nodeid,
            "bodies_executed": False,
        },
    )
    assert MODULE.main(["preflight", "--worktree", MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID, "--target", target]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["worktree"] == MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID
    assert result["nodeid"] == target
    assert result["bodies_executed"] is False


def test_hex8sri_convergence24_attestor_records_skip_status_and_body_execution(tmp_path: Path, monkeypatch) -> None:
    target = MODULE._hex8sri_convergence24_nodeids()[0]
    report_path = tmp_path / "collection-report.json"
    monkeypatch.setenv("QF_DEV_PREFLIGHT_COLLECTION_REPORT", str(report_path))
    item = SimpleNamespace(nodeid=target, iter_markers=lambda: iter(()))
    session = SimpleNamespace(items=[item])
    attestor = PLUGIN.Hex8SRIConvergence24Attestor(target, scope_id=MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID)
    attestor.pytest_collection_finish(session)
    attestor.pytest_sessionfinish(session, 0)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["collected_nodeids"] == [target]
    assert report["skip_markers"] == []
    assert report["bodies_executed"] is False
    assert report["exitstatus"] == 0

    skipped_path = tmp_path / "skipped-report.json"
    monkeypatch.setenv("QF_DEV_PREFLIGHT_COLLECTION_REPORT", str(skipped_path))
    skipped = SimpleNamespace(
        nodeid=target,
        iter_markers=lambda: iter((SimpleNamespace(name="skipif"),)),
    )
    attestor = PLUGIN.Hex8SRIConvergence24Attestor(target, scope_id=MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID)
    attestor.pytest_collection_finish(SimpleNamespace(items=[skipped]))
    attestor.pytest_sessionfinish(SimpleNamespace(items=[skipped]), 0)
    assert json.loads(skipped_path.read_text(encoding="utf-8"))["skip_markers"] == ["skipif"]


def _write_synthetic_hex8sri_convergence24_receipt(
    store: Path,
    *,
    target: str,
    identity: dict[str, Any],
    source_fingerprint: str,
    controller_provenance: dict[str, Any],
    manifest_binding: dict[str, Any],
    attempt_ledger: dict[str, Any],
) -> tuple[str, Path, dict[str, Any]]:
    preflight_id = "pf-24abcdeffedc"
    receipt_dir = MODULE._preflight_directory(store, MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID, preflight_id)
    receipt_dir.mkdir(parents=True)
    record_path = receipt_dir / "preflight.json"
    origin = str((Path(identity["root"]) / "src" / "solveur" / "__init__.py").resolve())
    receipt = {
        "schema": "qfsolver-development-hex8sri-convergence24-preflight-v1",
        "state": "PREFLIGHT_PASS",
        "mandate_id": MODULE.HEX8SRI_CONVERGENCE24_MANDATE_ID,
        "campaign_id": MODULE.HEX8SRI_CONVERGENCE24_CAMPAIGN_ID,
        "bodies_executed": False,
        "attempt_reserved": False,
        "execution_authorized": False,
        "worktree_id": MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID,
        "target": target,
        "preflight_id": preflight_id,
        "identity": identity,
        "source_fingerprint": source_fingerprint,
        "controller_provenance": controller_provenance,
        "case_manifest": manifest_binding,
        "solver_origin_expected": origin,
        "solver_origin_observed": origin,
        "collected_nodeids": [target],
        "skip_status": "NO_SKIP_MARKERS",
        "attempt_ledger": attempt_ledger,
        "collection_report": {
            "schema": "qfsolver-hex8sri-convergence24-collection-v1",
            "scope_id": MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID,
            "target": target,
            "collected_nodeids": [target],
            "skip_markers": [],
            "bodies_executed": False,
            "exitstatus": 0,
        },
    }
    record_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    (receipt_dir / "preflight.sha256.json").write_text(
        json.dumps({"sha256": MODULE._sha256(record_path)}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return preflight_id, record_path, receipt


def test_hex8sri_convergence24_receipt_validator_accepts_synthetic_receipt(tmp_path: Path) -> None:
    target = MODULE._hex8sri_convergence24_nodeids()[0]
    identity = {
        "root": str(tmp_path / "research"),
        "branch": MODULE.HEX8SRI_CONVERGENCE24_SOURCE_IDENTITY["branch"],
        "head": "a" * 40,
    }
    source_fingerprint = "b" * 64
    controller = {"identity": {"branch": "codex/hex8sri-convergence24-minimal", "head": "c" * 40}, "sha256": {}}
    binding = {
        "path": "manifest.json",
        "sha256": "d" * 64,
        "registration_sha256": "e" * 64,
        "case_id": "synthetic",
        "scope_id": MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID,
    }
    ledger = {
        "path": "dedicated-ledger.json",
        "mandate_id": MODULE.HEX8SRI_CONVERGENCE24_MANDATE_ID,
        "attempts_reserved": False,
    }
    preflight_id, record_path, _ = _write_synthetic_hex8sri_convergence24_receipt(
        tmp_path,
        target=target,
        identity=identity,
        source_fingerprint=source_fingerprint,
        controller_provenance=controller,
        manifest_binding=binding,
        attempt_ledger=ledger,
    )
    validated_path, validated_sha = MODULE._validate_hex8sri_convergence24_preflight_receipt(
        tmp_path,
        preflight_id,
        target=target,
        identity=identity,
        source_fingerprint=source_fingerprint,
        controller_provenance=controller,
        manifest_binding=binding,
        attempt_ledger=ledger,
    )
    assert validated_path == record_path
    assert validated_sha == MODULE._sha256(record_path)


def test_hex8sri_convergence24_receipt_validator_rejects_identity_drift(tmp_path: Path) -> None:
    target = MODULE._hex8sri_convergence24_nodeids()[0]
    identity = {
        "root": str(tmp_path / "research"),
        "branch": MODULE.HEX8SRI_CONVERGENCE24_SOURCE_IDENTITY["branch"],
        "head": "a" * 40,
    }
    controller = {"identity": {"branch": "codex/hex8sri-convergence24-minimal", "head": "c" * 40}, "sha256": {}}
    binding = {
        "path": "manifest.json",
        "sha256": "d" * 64,
        "registration_sha256": "e" * 64,
        "case_id": "synthetic",
        "scope_id": MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID,
    }
    ledger = {
        "path": "dedicated-ledger.json",
        "mandate_id": MODULE.HEX8SRI_CONVERGENCE24_MANDATE_ID,
        "attempts_reserved": False,
    }
    preflight_id, record_path, receipt = _write_synthetic_hex8sri_convergence24_receipt(
        tmp_path,
        target=target,
        identity=identity,
        source_fingerprint="b" * 64,
        controller_provenance=controller,
        manifest_binding=binding,
        attempt_ledger=ledger,
    )
    receipt["identity"] = {**receipt["identity"], "head": "f" * 40}
    record_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    (record_path.parent / "preflight.sha256.json").write_text(
        json.dumps({"sha256": MODULE._sha256(record_path)}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(MODULE.PolicyError, match="does not match this source, controller"):
        MODULE._validate_hex8sri_convergence24_preflight_receipt(
            tmp_path,
            preflight_id,
            target=target,
            identity=identity,
            source_fingerprint="b" * 64,
            controller_provenance=controller,
            manifest_binding=binding,
            attempt_ledger=ledger,
        )


def test_hex8sri_convergence24_preflight_writer_emits_validator_accepted_synthetic_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = json.loads(json.dumps(_policy()))
    scope_id = MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID
    entry = policy["worktrees"][scope_id]
    target = "tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p3-4x2x2]"
    repository = tmp_path / "research"
    source_root = repository / "src"
    solver_file = source_root / "solveur" / "__init__.py"
    solver_file.parent.mkdir(parents=True)
    solver_file.write_text("# synthetic origin\n", encoding="utf-8")
    manifest_dir = repository / "registered_manifests"
    manifest_dir.mkdir()
    common_path = manifest_dir / "common_problem.json"
    common_path.write_text('{"synthetic": true}\n', encoding="utf-8")
    hashes = {"runner": "1" * 64, "pytest_plugin": "2" * 64, "policy": "3" * 64}
    controller = {
        "identity": {"branch": "codex/hex8sri-convergence24-minimal", "head": "c" * 40},
        "sha256": hashes,
        "runtime": {"python_version": "test", "pytest_version": "test", "psutil_version": "test"},
    }
    mesh = {
        "divisions_xyz": [4, 2, 2],
        "element_count": 16,
        "node_count": 45,
        "dof_count": 135,
        "fixed_dof_count": 27,
        "free_dof_count": 108,
    }
    budget = {
        **MODULE._hex8sri_convergence24_budget(target),
        "attempts_per_nodeid": 1,
        "initial_campaign_max_attempts": 24,
        "blas_thread_environment": entry["blas_thread_environment"],
        "budget_semantics": {
            "captured_output": "controller-enforced byte caps",
            "rss_process_temporary_archive": "sampled soft observations, not OS quotas",
            "wall_timeout": "watchdog process-tree termination, best effort",
        },
    }
    manifest = {
        "schema": "qfsolver-hex8-sri-structural-case-v2",
        "campaign_id": MODULE.HEX8SRI_CONVERGENCE24_CAMPAIGN_ID,
        "case_id": "hex8_standard_nu_0p3_4x2x2",
        "common_problem": {"path": "common_problem.json", "sha256": MODULE._sha256(common_path)},
        "controller_registration_id": scope_id,
        "controller_campaign_scope_id": scope_id,
        "controller_identity_status": "FINAL_CONTROLLER_IDENTITY_BOUND",
        "controller_code_sha256": hashes,
        "controller_identity": {
            "branch": controller["identity"]["branch"],
            "head": controller["identity"]["head"],
            "runner_sha256": hashes["runner"],
            "pytest_plugin_sha256": hashes["pytest_plugin"],
            "policy_sha256": hashes["policy"],
        },
        "exact_nodeid": target,
        "science_branch": MODULE.HEX8SRI_CONVERGENCE24_SOURCE_IDENTITY["branch"],
        "source_fingerprint_sha256": MODULE.HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT,
        "execution_authorized": False,
        "do_not_execute": True,
        "execution_state": "PREPARED_NOT_AUTHORIZED",
        "formulation": {"id": "hex8_standard"},
        "poisson_ratio": 0.3,
        "mesh": mesh,
        "budgets": budget,
    }
    manifest_path = manifest_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    entry["root"] = str(repository)
    entry["git_root"] = str(repository)
    entry["case_manifests"] = {
        target: {
            "path": "registered_manifests/manifest.json",
            "sha256": MODULE._hex8sri_manifest_registration_sha256(manifest),
        }
    }
    identity = {
        "root": str(repository),
        "branch": entry["branch"],
        "head": "a" * 40,
        "tree": "b" * 40,
        "status_short": "",
    }
    store = tmp_path / "run-store"
    monkeypatch.setattr(MODULE, "resolve_targets", lambda *_args, **_kwargs: [target])
    monkeypatch.setattr(
        MODULE,
        "_registered_worktree",
        lambda *_args, **_kwargs: (
            entry,
            repository,
            source_root,
            identity,
            MODULE.HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT,
        ),
    )
    monkeypatch.setattr(
        MODULE, "_worktree_source_fingerprint", lambda *_args: MODULE.HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT
    )
    monkeypatch.setattr(MODULE, "_controller_provenance", lambda: controller)
    monkeypatch.setattr(MODULE, "_run_root", lambda *_args: store)
    monkeypatch.setattr(MODULE.shutil, "disk_usage", lambda _path: SimpleNamespace(free=8 * 1024**3))

    def fake_supervised_command(_command, *, output_dir, environment, **_kwargs):
        stdout = f"QF_DEV_SOLVER_ORIGIN={solver_file.resolve()}\n{target}\n"
        (output_dir / "stdout.log").write_text(stdout, encoding="utf-8")
        (output_dir / "stderr.log").write_text("", encoding="utf-8")
        report = {
            "schema": "qfsolver-hex8sri-convergence24-collection-v1",
            "scope_id": scope_id,
            "target": target,
            "collected_nodeids": [target],
            "skip_markers": [],
            "bodies_executed": False,
            "exitstatus": 0,
        }
        Path(environment["QF_DEV_PREFLIGHT_COLLECTION_REPORT"]).write_text(
            json.dumps(report, sort_keys=True) + "\n", encoding="utf-8"
        )
        return SimpleNamespace(
            status="PASS",
            return_code=0,
            elapsed_seconds=0.01,
            peak_rss_bytes=1024,
            peak_process_count=1,
            stdout_bytes=len(stdout.encode()),
            stderr_bytes=0,
            archive_bytes=0,
            temporary_bytes=0,
            stop_reason=None,
        )

    monkeypatch.setattr(MODULE, "run_supervised_command", fake_supervised_command)
    result = MODULE.preflight_hex8sri_convergence24_pytest(target, "pf-24fedcba9876", policy=policy)
    assert result["state"] == "PREFLIGHT_PASS"
    assert result["receipt_validated"] is True
    assert result["bodies_executed"] is False
    assert not (store / MODULE.HEX8SRI_CONVERGENCE24_LEDGER).exists()


def test_hex8sri_convergence24_execution_refuses_before_ledger_or_launcher(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    worktree_id = MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID
    target = MODULE._hex8sri_convergence24_nodeids()[0]
    policy = _policy()
    entry = policy["worktrees"][worktree_id]
    identity = {
        "root": entry["root"],
        "branch": entry["branch"],
        "head": "a" * 40,
        "tree": "b" * 40,
        "status_short": "",
    }
    monkeypatch.setattr(MODULE, "load_policy", lambda: policy)
    monkeypatch.setattr(MODULE, "resolve_targets", lambda *_args, **_kwargs: [target])
    monkeypatch.setattr(
        MODULE,
        "_registered_worktree",
        lambda *_args, **_kwargs: (
            entry,
            tmp_path / "science",
            tmp_path / "science" / "src",
            identity,
            MODULE.HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT,
        ),
    )
    monkeypatch.setattr(MODULE, "_run_root", lambda *_args: tmp_path / "run-store")
    monkeypatch.setattr(
        MODULE,
        "_node_ledger_context",
        lambda *_args, **_kwargs: pytest.fail("unauthorized HEX8-SRI execution reached ledger setup"),
    )
    monkeypatch.setattr(
        MODULE, "run_supervised_command", lambda *_args, **_kwargs: pytest.fail("refusal must precede launch")
    )
    with pytest.raises(MODULE.PolicyError, match="requires one validated collect-only receipt"):
        MODULE.run_pytest(
            "fem_exploratory",
            target,
            "dev-hex8sri-convergence24-test",
            worktree_id=worktree_id,
            reason="synthetic refusal test",
        )
    assert list(tmp_path.iterdir()) == []


def _synthetic_hex8sri_execution_authorization(
    tmp_path: Path,
    *,
    authorized_nodeids: list[str] | None = None,
    frozen_nodeids: list[str] | None = None,
) -> dict[str, Any]:
    scope_id = MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID
    entry = json.loads(json.dumps(_policy()["worktrees"][scope_id]))
    selected_nodeids = list(MODULE.HEX8SRI_FIRST6_NODEIDS) if authorized_nodeids is None else authorized_nodeids
    target = selected_nodeids[0] if selected_nodeids else MODULE.HEX8SRI_FIRST6_NODEIDS[0]
    scope = MODULE._hex8sri_criteria_scope_for_target(target)
    default_frozen_nodeids = list(scope[1]) if scope is not None else list(MODULE.HEX8SRI_FIRST6_NODEIDS)
    frozen_scope = default_frozen_nodeids if frozen_nodeids is None else frozen_nodeids
    identity = {
        "root": str(tmp_path / "synthetic-science-root"),
        "branch": entry["branch"],
        "head": MODULE.HEX8SRI_CONVERGENCE24_SOURCE_HEAD,
        "tree": MODULE.HEX8SRI_CONVERGENCE24_SOURCE_TREE,
        "status_short": "",
    }
    controller = {
        "identity": {"branch": "codex/hex8sri-convergence24-execution-gate", "head": "c" * 40},
        "sha256": {"runner": "1" * 64, "pytest_plugin": "2" * 64, "policy": "3" * 64},
        "runtime": {"python_version": "synthetic", "pytest_version": "synthetic", "psutil_version": "synthetic"},
    }
    case_manifest = {
        "criteria_status": "OWNER_FREEZE_REQUIRED",
        "criteria_contract": {
            "schema": MODULE.HEX8SRI_CRITERIA_CONTRACT_SCHEMA,
            "revision": scope[0] if scope is not None else MODULE.HEX8SRI_CRITERIA_CONTRACT_REVISION,
            "dispositions": MODULE.HEX8SRI_CRITERIA_PROPOSAL_DISPOSITIONS,
        },
        "proposed_criteria": MODULE.HEX8SRI_PROPOSED_CRITERIA,
        "frozen_criteria": None,
    }
    registration_sha256 = MODULE._hex8sri_manifest_registration_sha256(case_manifest)
    entry["case_manifests"][target]["sha256"] = registration_sha256
    selected_case = MODULE._hex8sri_convergence24_case(target)
    assert selected_case is not None
    binding = {
        "path": "registered/manifest.json",
        "sha256": "d" * 64,
        "registration_sha256": registration_sha256,
        "case_id": f"{selected_case[0]}_nu_{selected_case[1]}_{selected_case[2]}",
        "scope_id": scope_id,
    }
    source_fingerprint = MODULE.HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT
    store = tmp_path / "run-store"
    ledger = {
        "path": str(store / entry["node_attempt_ledger"]["path"]),
        "mandate_id": entry["development_mandate_id"],
        "attempts_reserved": False,
    }
    preflight_id, preflight_path, _ = _write_synthetic_hex8sri_convergence24_receipt(
        store,
        target=target,
        identity=identity,
        source_fingerprint=source_fingerprint,
        controller_provenance=controller,
        manifest_binding=binding,
        attempt_ledger=ledger,
    )
    preflight = (preflight_path, MODULE._sha256(preflight_path))
    authorization_id = "hex8sri-auth-0001"
    criteria_freeze = MODULE._hex8sri_expected_criteria_freeze(
        entry=entry,
        source_fingerprint=source_fingerprint,
        controller_provenance=controller,
        frozen_nodeids=frozen_scope,
    )
    freeze_decision = {
        "schema": MODULE.HEX8SRI_CRITERIA_FREEZE_DECISION_SCHEMA,
        "decision_type": "CRITERIA_FREEZE_ONLY",
        "decision_id": "owner-freeze-0001",
        "status": "CRITERIA_FROZEN_EXECUTION_NOT_AUTHORIZED",
        "execution_authorized": False,
        "do_not_execute": True,
        "approved_by": "Owner",
        "approved_at_utc": MODULE.datetime.now(MODULE.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "reason": "Synthetic criteria-only freeze; no FEM execution is authorized.",
        "scope_id": scope_id,
        "mandate_id": entry["development_mandate_id"],
        "campaign_id": entry["campaign_id"],
        "frozen_nodeids": list(frozen_scope),
        "source_fingerprint": source_fingerprint,
        "controller_fingerprint": MODULE._stable_fingerprint(controller),
        "controller_head": controller["identity"]["head"],
        "criteria_freeze": criteria_freeze,
    }
    freeze_path = store / "authorizations" / scope_id / "owner-decisions" / "criteria-freeze" / "owner-freeze-0001.json"
    freeze_path.parent.mkdir(parents=True)
    freeze_path.write_text(json.dumps(freeze_decision, sort_keys=True) + "\n", encoding="utf-8")
    freeze_ref = {
        "decision_id": freeze_decision["decision_id"],
        "path": str(freeze_path),
        "sha256": MODULE._sha256(freeze_path),
    }
    manifest_bindings = {}
    for index, nodeid in enumerate(frozen_scope):
        if nodeid == target:
            manifest_bindings[nodeid] = binding
            continue
        case = MODULE._hex8sri_convergence24_case(nodeid)
        assert case is not None
        manifest_bindings[nodeid] = {
            "path": str(tmp_path / "registered" / f"case-{index}.json"),
            "sha256": hashlib.sha256(f"manifest-{index}".encode()).hexdigest(),
            "registration_sha256": entry["case_manifests"][nodeid]["sha256"],
            "case_id": f"{case[0]}_nu_{case[1]}_{case[2]}",
            "scope_id": scope_id,
        }
    now = MODULE.datetime.now(MODULE.timezone.utc).replace(microsecond=0)
    selected_manifest_bindings = {
        nodeid: manifest_bindings[nodeid] for nodeid in selected_nodeids if nodeid in manifest_bindings
    }
    decision = {
        "schema": MODULE.HEX8SRI_EXECUTION_APPROVAL_SCHEMA,
        "decision_type": "EXECUTION_APPROVED",
        "decision_id": "owner-execution-0001",
        "status": "APPROVED",
        "execution_authorized": True,
        "do_not_execute": False,
        "approved_by": "Owner",
        "approved_at_utc": now.isoformat().replace("+00:00", "Z"),
        "expires_at_utc": (now + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
        "reason": "Synthetic exact-case authorization contract test.",
        "scope_id": scope_id,
        "mandate_id": entry["development_mandate_id"],
        "campaign_id": entry["campaign_id"],
        "authorized_nodeids": selected_nodeids,
        "source_fingerprint": source_fingerprint,
        "controller_fingerprint": MODULE._stable_fingerprint(controller),
        "controller_head": controller["identity"]["head"],
        "criteria_freeze_record": freeze_ref,
        "criteria_freeze": criteria_freeze,
        "case_manifests_by_nodeid": selected_manifest_bindings,
        "limits_by_nodeid": {
            nodeid: MODULE._hex8sri_execution_limits(entry, nodeid)
            for nodeid in selected_nodeids
            if nodeid in manifest_bindings
        },
    }
    decision_path = store / "authorizations" / scope_id / "owner-decisions" / "execution" / f"{decision['decision_id']}.json"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text(json.dumps(decision, sort_keys=True) + "\n", encoding="utf-8")
    payload = {
        "schema": MODULE.HEX8SRI_EXECUTION_MANIFEST_SCHEMA,
        "state": "OWNER_AUTHORIZED",
        "execution_authorized": True,
        "do_not_execute": False,
        "authorization_id": authorization_id,
        "worktree_id": scope_id,
        "mandate_id": entry["development_mandate_id"],
        "campaign_id": entry["campaign_id"],
        "target": target,
        "identity": identity,
        "source_fingerprint": source_fingerprint,
        "controller_provenance": controller,
        "controller_fingerprint": MODULE._stable_fingerprint(controller),
        "case_manifest": binding,
        "preflight": {
            "preflight_id": preflight_id,
            "receipt_path": str(preflight_path),
            "receipt_sha256": preflight[1],
        },
        "limits": MODULE._hex8sri_execution_limits(entry, target),
        "owner_decision": decision,
        "owner_decision_record": {
            "path": str(decision_path),
            "sha256": MODULE._sha256(decision_path),
        },
    }
    path = store / "authorizations" / scope_id / f"{authorization_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "entry": entry,
        "target": target,
        "identity": identity,
        "controller": controller,
        "source_fingerprint": source_fingerprint,
        "binding": binding,
        "case_manifest": case_manifest,
        "preflight_id": preflight_id,
        "preflight": preflight,
        "store": store,
        "freeze_decision": freeze_decision,
        "freeze_path": freeze_path,
        "freeze_ref": freeze_ref,
        "manifest_bindings": manifest_bindings,
        "selected_manifest_bindings": selected_manifest_bindings,
        "path": path,
        "payload": payload,
        "decision": decision,
    }


def _validate_synthetic_hex8sri_execution(fixture: dict[str, Any]) -> dict[str, Any]:
    return MODULE._validate_hex8sri_execution_manifest(
        fixture["path"],
        store=fixture["store"],
        target=fixture["target"],
        entry=fixture["entry"],
        identity=fixture["identity"],
        source_fingerprint=fixture["source_fingerprint"],
        controller_provenance=fixture["controller"],
        case_manifest_binding=fixture["binding"],
        case_manifest=fixture["case_manifest"],
        preflight_id=fixture["preflight_id"],
        preflight_receipt=fixture["preflight"],
    )


def _validate_synthetic_hex8sri_approval(fixture: dict[str, Any]) -> dict[str, Any]:
    return MODULE._validate_hex8sri_execution_approval(
        fixture["decision"],
        store=fixture["store"],
        entry=fixture["entry"],
        target=fixture["target"],
        source_fingerprint=fixture["source_fingerprint"],
        controller_provenance=fixture["controller"],
        case_manifest_binding=fixture["binding"],
    )


@pytest.mark.parametrize(
    "selected", [[nodeid] for nodeid in MODULE.HEX8SRI_FIRST6_NODEIDS] + [[MODULE.HEX8SRI_FIRST6_NODEIDS[0], MODULE.HEX8SRI_FIRST6_NODEIDS[-1]]],
    ids=[f"single-{index}" for index in range(6)] + ["two-nodeids"],
)
def test_hex8sri_execution_approval_accepts_explicit_registered_subset(
    tmp_path: Path, selected: list[str]
) -> None:
    fixture = _synthetic_hex8sri_execution_authorization(tmp_path, authorized_nodeids=selected)
    approved = _validate_synthetic_hex8sri_approval(fixture)
    assert approved["authorized_nodeids"] == selected
    assert set(approved["case_manifests_by_nodeid"]) == set(selected)
    assert set(approved["limits_by_nodeid"]) == set(selected)


@pytest.mark.parametrize(
    ("selection", "mutation", "message"),
    [
        ([], None, "reviewed criteria scope"),
        (["tests/verification/test_hex8_sri_convergence.py::test_not_registered"], None, "reviewed criteria scope"),
        ([MODULE.HEX8SRI_FIRST6_NODEIDS[0], MODULE.HEX8SRI_FIRST6_NODEIDS[0]], None, "reviewed criteria scope"),
        ([MODULE.HEX8SRI_FIRST6_NODEIDS[0]], "missing_manifest", "does not authorize this exact scope"),
        ([MODULE.HEX8SRI_FIRST6_NODEIDS[0]], "mismatched_manifest", "does not authorize this exact scope"),
        ([MODULE.HEX8SRI_FIRST6_NODEIDS[0]], "budget", "registered case budget"),
        ([MODULE.HEX8SRI_FIRST6_NODEIDS[0]], "fingerprint", "exact scope, source, controller or nodeid"),
    ],
    ids=["empty", "unknown-nodeid", "duplicate-nodeid", "missing-manifest", "mismatched-manifest", "changed-budget", "wrong-fingerprint"],
)
def test_hex8sri_execution_approval_rejects_invalid_partial_selection(
    tmp_path: Path, selection: list[str], mutation: str | None, message: str
) -> None:
    known = set(MODULE.HEX8SRI_FIRST6_NODEIDS)
    fixture_selection = selection if all(nodeid in known for nodeid in selection) else [MODULE.HEX8SRI_FIRST6_NODEIDS[0]]
    fixture = _synthetic_hex8sri_execution_authorization(tmp_path, authorized_nodeids=fixture_selection)
    decision = fixture["decision"]
    decision["authorized_nodeids"] = selection
    if mutation == "missing_manifest":
        decision["case_manifests_by_nodeid"] = {}
    elif mutation == "mismatched_manifest":
        decision["case_manifests_by_nodeid"][selection[0]] = {
            **decision["case_manifests_by_nodeid"][selection[0]],
            "sha256": "0" * 64,
        }
    elif mutation == "budget":
        decision["limits_by_nodeid"][selection[0]]["timeout_seconds"] += 1
    elif mutation == "fingerprint":
        decision["source_fingerprint"] = "f" * 64
    with pytest.raises(MODULE.PolicyError, match=message):
        _validate_synthetic_hex8sri_approval(fixture)


def test_hex8sri_execution_manifest_refuses_unselected_nodeid(tmp_path: Path) -> None:
    fixture = _synthetic_hex8sri_execution_authorization(
        tmp_path, authorized_nodeids=[MODULE.HEX8SRI_FIRST6_NODEIDS[0]]
    )
    fixture["payload"]["target"] = MODULE.HEX8SRI_FIRST6_NODEIDS[1]
    fixture["path"].write_text(json.dumps(fixture["payload"], sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(MODULE.PolicyError, match="does not bind this exact source"):
        _validate_synthetic_hex8sri_execution(fixture)


def test_hex8sri_owner_archive_binds_only_selected_current_manifests(tmp_path: Path) -> None:
    fixture = _synthetic_hex8sri_execution_authorization(
        tmp_path, authorized_nodeids=[MODULE.HEX8SRI_FIRST6_NODEIDS[1]]
    )
    current = {
        nodeid: dict(binding) for nodeid, binding in fixture["manifest_bindings"].items()
    }
    selected = MODULE._hex8sri_selected_current_case_manifest_bindings(fixture["decision"], current)
    assert list(selected) == [MODULE.HEX8SRI_FIRST6_NODEIDS[1]]
    assert selected == fixture["selected_manifest_bindings"]
    altered = json.loads(json.dumps(fixture["decision"]))
    altered["case_manifests_by_nodeid"][MODULE.HEX8SRI_FIRST6_NODEIDS[1]]["sha256"] = "0" * 64
    with pytest.raises(MODULE.PolicyError, match="does not match every current selected"):
        MODULE._hex8sri_selected_current_case_manifest_bindings(altered, current)
    altered = json.loads(json.dumps(fixture["decision"]))
    altered["case_manifests_by_nodeid"][MODULE.HEX8SRI_FIRST6_NODEIDS[0]] = current[MODULE.HEX8SRI_FIRST6_NODEIDS[0]]
    with pytest.raises(MODULE.PolicyError, match="does not match every current selected"):
        MODULE._hex8sri_selected_current_case_manifest_bindings(altered, current)


def test_hex8sri_execution_manifest_refuses_missing_owner_decision(tmp_path: Path) -> None:
    fixture = _synthetic_hex8sri_execution_authorization(
        tmp_path, authorized_nodeids=[MODULE.HEX8SRI_FIRST6_NODEIDS[0]]
    )
    fixture["payload"]["owner_decision"] = None
    fixture["path"].write_text(json.dumps(fixture["payload"], sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(MODULE.PolicyError, match="differs from its separately archived approval record"):
        _validate_synthetic_hex8sri_execution(fixture)


def test_hex8sri_execution_manifest_accepts_synthetic_owner_decision_and_exact_preflight(
    tmp_path: Path,
) -> None:
    fixture = _synthetic_hex8sri_execution_authorization(tmp_path)
    receipt = _validate_synthetic_hex8sri_execution(fixture)
    assert receipt["authorization_id"] == fixture["payload"]["authorization_id"]
    assert receipt["decision_id"] == fixture["decision"]["decision_id"]
    assert receipt["owner_decision"]["mandate_id"] == fixture["entry"]["development_mandate_id"]
    assert receipt["owner_decision_record"]["sha256"] == fixture["payload"]["owner_decision_record"]["sha256"]
    assert receipt["criteria_dispositions"] == MODULE.HEX8SRI_CRITERIA_DISPOSITIONS
    assert receipt["frozen_criteria"] == MODULE.HEX8SRI_FROZEN_CASE_GATE_CRITERIA
    assert receipt["preflight"]["receipt_sha256"] == fixture["preflight"][1]
    assert receipt["sha256"] == MODULE._sha256(fixture["path"])


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ("not_authorized", "does not bind this exact source, controller, case, preflight and budget"),
        ("mandate", "does not bind this exact source, controller, case, preflight and budget"),
        ("fingerprint", "does not bind this exact source, controller, case, preflight and budget"),
        ("nodeid", "nodeid is not registered"),
        ("budget", "does not bind this exact source, controller, case, preflight and budget"),
        ("decision_mandate", "does not authorize this exact scope, source, controller or nodeid"),
        ("criteria_freeze_stale", "does not match its separately frozen criteria record"),
    ],
    ids=(
        "not-authorized",
        "wrong-mandate",
        "wrong-source-fingerprint",
        "unregistered-nodeid",
        "over-budget",
        "wrong-owner-mandate",
        "obsolete-criteria-decision",
    ),
)
def test_hex8sri_execution_manifest_rejects_invalid_authorization(
    tmp_path: Path, mutation: str, expected_error: str
) -> None:
    fixture = _synthetic_hex8sri_execution_authorization(tmp_path)
    payload = fixture["payload"]
    if mutation == "not_authorized":
        payload.update(state="PREPARED_NOT_AUTHORIZED", execution_authorized=False, do_not_execute=True)
    elif mutation == "mandate":
        payload["mandate_id"] = "DEVELOPMENT_AUTONOMOUS-WRONG-MANDATE"
    elif mutation == "fingerprint":
        payload["source_fingerprint"] = "f" * 64
    elif mutation == "nodeid":
        payload["target"] = "tests/verification/test_hex8_sri_convergence.py::test_not_registered"
        fixture["target"] = payload["target"]
    elif mutation == "budget":
        payload["limits"]["timeout_seconds"] += 1
    elif mutation == "decision_mandate":
        payload["owner_decision"]["mandate_id"] = "DEVELOPMENT_AUTONOMOUS-WRONG-MANDATE"
        decision_path = Path(payload["owner_decision_record"]["path"])
        decision_path.write_text(json.dumps(payload["owner_decision"], sort_keys=True) + "\n", encoding="utf-8")
        payload["owner_decision_record"]["sha256"] = MODULE._sha256(decision_path)
    else:
        payload["owner_decision"]["criteria_freeze"]["revision"] = "obsolete-first-six-criteria"
        decision_path = Path(payload["owner_decision_record"]["path"])
        decision_path.write_text(json.dumps(payload["owner_decision"], sort_keys=True) + "\n", encoding="utf-8")
        payload["owner_decision_record"]["sha256"] = MODULE._sha256(decision_path)
    fixture["path"].write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(MODULE.PolicyError, match=expected_error):
        _validate_synthetic_hex8sri_execution(fixture)


def test_hex8sri_execution_ledger_refuses_cross_scope_and_malformed_entries(tmp_path: Path) -> None:
    entry = _policy()["worktrees"][MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID]
    target = entry["allowed_nodeids"][0]
    path = tmp_path / "ledger.json"
    path.write_text(
        json.dumps(
            {
                "schema": "qfsolver-development-node-ledger-v1",
                "mandate_id": entry["development_mandate_id"],
                "entries": {"other:scope:node": []},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(MODULE.PolicyError, match="another scope or mandate"):
        MODULE._validate_hex8sri_execution_ledger(path, entry=entry, target=target)


def test_hex8sri_execution_attempt_reservation_records_mandate_and_owner_decision(tmp_path: Path) -> None:
    entry = _policy()["worktrees"][MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID]
    target = entry["allowed_nodeids"][0]
    ledger_path = tmp_path / MODULE.HEX8SRI_CONVERGENCE24_LEDGER
    key, number = MODULE._reserve_node_attempt(
        ledger_path,
        ledger_path.with_suffix(".lock"),
        mandate_id=entry["development_mandate_id"],
        worktree_id=MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID,
        target=target,
        series_id="dev-hex8sri-synthetic",
        source_fingerprint=MODULE.HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT,
        reason="Synthetic isolated ledger writer contract test.",
        maximum=1,
        total_maximum=24,
        authorization_id="hex8sri-auth-0001",
        owner_decision_id="owner-decision-0001",
        controller_fingerprint="d" * 64,
    )
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert number == 1
    assert ledger["mandate_id"] == entry["development_mandate_id"]
    assert key == f"{entry['development_mandate_id']}:{MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID}:{target}"
    assert ledger["entries"][key][0]["authorization_id"] == "hex8sri-auth-0001"
    assert ledger["entries"][key][0]["owner_decision_id"] == "owner-decision-0001"
    MODULE._validate_hex8sri_execution_ledger(ledger_path, entry=entry, target=target)
    with pytest.raises(MODULE.PolicyError, match="exhausted 1 attempts"):
        MODULE._reserve_node_attempt(
            ledger_path,
            ledger_path.with_suffix(".lock"),
            mandate_id=entry["development_mandate_id"],
            worktree_id=MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID,
            target=target,
            series_id="dev-hex8sri-retry",
            source_fingerprint=MODULE.HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT,
            reason="Synthetic retry must be refused.",
            maximum=1,
            total_maximum=24,
            authorization_id="hex8sri-auth-0002",
            owner_decision_id="owner-decision-0001",
            controller_fingerprint="d" * 64,
        )


def test_hex8sri_owner_manifest_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    fixture = _synthetic_hex8sri_execution_authorization(tmp_path)
    fixture["path"].write_text('{"schema":"one","schema":"two"}\n', encoding="utf-8")
    with pytest.raises(MODULE.PolicyError, match="duplicate JSON key"):
        _validate_synthetic_hex8sri_execution(fixture)


def test_hex8sri_owner_manifest_rejects_tampered_approval_record(tmp_path: Path) -> None:
    fixture = _synthetic_hex8sri_execution_authorization(tmp_path)
    decision_path = Path(fixture["payload"]["owner_decision_record"]["path"])
    decision_path.write_text('{"decision_id":"altered"}\n', encoding="utf-8")
    with pytest.raises(MODULE.PolicyError, match="path or SHA-256 is invalid"):
        _validate_synthetic_hex8sri_execution(fixture)


def test_hex8sri_manifest_preparation_stays_unapproved_and_refuses_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from contextlib import nullcontext

    scope_id = MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID
    policy = _policy()
    entry = policy["worktrees"][scope_id]
    target = entry["allowed_nodeids"][0]
    science_root = tmp_path / "science"
    source_root = science_root / "src"
    identity = {
        "root": str(science_root),
        "branch": entry["branch"],
        "head": "a" * 40,
        "tree": "b" * 40,
        "status_short": "",
    }
    controller = {
        "identity": {"branch": "codex/hex8sri-convergence24-execution-gate", "head": "c" * 40},
        "sha256": {"runner": "1" * 64, "pytest_plugin": "2" * 64, "policy": "3" * 64},
    }
    case_path = science_root / "manifest.json"
    case_path.parent.mkdir(parents=True)
    case_path.write_text("{}\n", encoding="utf-8")
    case_manifest = {"case_id": "synthetic-case"}
    store = tmp_path / "controller-run-store"
    ledger_path = store / entry["node_attempt_ledger"]["path"]
    monkeypatch.setattr(MODULE, "load_policy", lambda *_args, **_kwargs: policy)
    monkeypatch.setattr(MODULE, "resolve_targets", lambda *_args, **_kwargs: [target])
    monkeypatch.setattr(
        MODULE,
        "_registered_worktree",
        lambda *_args, **_kwargs: (
            entry,
            science_root,
            source_root,
            identity,
            MODULE.HEX8SRI_CONVERGENCE24_SOURCE_FINGERPRINT,
        ),
    )
    monkeypatch.setattr(MODULE, "_run_root", lambda *_args, **_kwargs: store)
    monkeypatch.setattr(
        MODULE,
        "_node_ledger_context",
        lambda *_args, **_kwargs: (
            ledger_path,
            ledger_path.with_suffix(".lock"),
            entry["development_mandate_id"],
            None,
        ),
    )
    monkeypatch.setattr(MODULE, "_hex8sri_convergence24_manifest", lambda *_args: (case_path, case_manifest, "d" * 64))
    monkeypatch.setattr(MODULE, "_hex8sri_manifest_registration_sha256", lambda _manifest: "e" * 64)
    monkeypatch.setattr(MODULE, "_hex8sri_convergence24_case_contract", lambda _manifest: {"element_count": 16})
    monkeypatch.setattr(MODULE, "_controller_provenance", lambda: controller)
    monkeypatch.setattr(MODULE, "_verify_hex8sri_convergence24_controller_identity", lambda *_args: None)
    monkeypatch.setattr(
        MODULE,
        "_validate_hex8sri_convergence24_preflight_receipt",
        lambda *_args, **_kwargs: (tmp_path / "preflight.json", "f" * 64),
    )
    monkeypatch.setattr(MODULE, "_exclusive_file_lock", lambda _path: nullcontext())

    result = MODULE.prepare_hex8sri_execution_manifest(target, "pf-24abcdeffedc", "hex8sri-draft-001")
    draft_path = Path(result["path"])
    payload = json.loads(draft_path.read_text(encoding="utf-8"))
    assert result["state"] == payload["state"] == "PREPARED_NOT_AUTHORIZED"
    assert payload["execution_authorized"] is False
    assert payload["do_not_execute"] is True
    assert payload["owner_decision"] is None
    assert payload["owner_decision_record"] is None
    assert not ledger_path.exists()
    with pytest.raises(MODULE.PolicyError, match="refusing to overwrite"):
        MODULE.prepare_hex8sri_execution_manifest(target, "pf-24abcdeffedc", "hex8sri-draft-001")
    assert json.loads(draft_path.read_text(encoding="utf-8")) == payload


def test_hex8sri_criteria_freeze_only_does_not_authorize_execution(tmp_path: Path) -> None:
    fixture = _synthetic_hex8sri_execution_authorization(tmp_path)
    frozen = MODULE._validate_hex8sri_criteria_freeze_decision(
        fixture["freeze_decision"],
        entry=fixture["entry"],
        source_fingerprint=fixture["source_fingerprint"],
        controller_provenance=fixture["controller"],
    )
    assert frozen["status"] == "CRITERIA_FROZEN_EXECUTION_NOT_AUTHORIZED"
    assert frozen["execution_authorized"] is False
    assert frozen["do_not_execute"] is True
    assert "authorized_nodeids" not in frozen
    assert "limits_by_nodeid" not in frozen
    assert fixture["freeze_decision"]["criteria_freeze"]["criteria_definitions"] == (
        MODULE.HEX8SRI_CRITERIA_DEFINITIONS
    )
    deferred = {
        name: record
        for name, record in MODULE.HEX8SRI_CRITERIA_DISPOSITIONS.items()
        if record["classification"] == "CAMPAIGN_GATE_DEFERRED"
    }
    assert deferred
    assert all(record["status"] == "NOT_ASSESSED" for record in deferred.values())
    assert not set(deferred).intersection(frozen["criteria_freeze"]["frozen_case_gate_criteria"])

    payload = fixture["payload"]
    payload["owner_decision"] = fixture["freeze_decision"]
    payload["owner_decision_record"] = {
        "path": str(fixture["freeze_path"]),
        "sha256": MODULE._sha256(fixture["freeze_path"]),
    }
    fixture["path"].write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(MODULE.PolicyError, match="reviewed criteria scope"):
        _validate_synthetic_hex8sri_execution(fixture)


@pytest.mark.parametrize(
    "mutation",
    [
        "incomplete",
        "classification_change",
        "threshold_change",
        "boolean_threshold",
        "stale_fingerprint",
        "missing_nodeid",
    ],
)
def test_hex8sri_criteria_freeze_decision_rejects_incomplete_or_changed_contract(
    tmp_path: Path, mutation: str
) -> None:
    fixture = _synthetic_hex8sri_execution_authorization(tmp_path)
    decision = json.loads(json.dumps(fixture["freeze_decision"]))
    if mutation == "incomplete":
        del decision["criteria_freeze"]["criteria_definitions"]["finite_state"]
    elif mutation == "classification_change":
        decision["criteria_freeze"]["dispositions"]["negative_mean_loaded_face_uz"] = {
            "classification": "CASE_DIAGNOSTIC",
            "status": "DESCRIPTIVE_ONLY",
        }
    elif mutation == "threshold_change":
        decision["criteria_freeze"]["criteria_definitions"]["free_residual_relative_max"]["threshold"][
            "value"
        ] = 1e-6
    elif mutation == "boolean_threshold":
        decision["criteria_freeze"]["criteria_definitions"]["positive_sampled_jacobians_center_and_gauss"][
            "threshold"
        ]["value"] = False
    elif mutation == "stale_fingerprint":
        decision["source_fingerprint"] = "f" * 64
    else:
        decision["frozen_nodeids"].pop()
    with pytest.raises(MODULE.PolicyError, match="criteria-freeze decision is incomplete, stale or inconsistent"):
        MODULE._validate_hex8sri_criteria_freeze_decision(
            decision,
            entry=fixture["entry"],
            source_fingerprint=fixture["source_fingerprint"],
            controller_provenance=fixture["controller"],
        )


@pytest.mark.parametrize("mutation", ["unfrozen_gate", "threshold_drift", "classification_drift", "stale_owner_case"])
def test_hex8sri_criteria_freeze_refuses_unfrozen_or_incoherent_contracts(
    tmp_path: Path, mutation: str
) -> None:
    fixture = _synthetic_hex8sri_execution_authorization(tmp_path)
    case_manifest = fixture["case_manifest"]
    decision = fixture["decision"]
    binding_sha = fixture["binding"]["registration_sha256"]
    if mutation == "unfrozen_gate":
        case_manifest["criteria_status"] = "PROPOSED_REQUIRES_OWNER_FREEZE"
    elif mutation == "threshold_drift":
        decision["criteria_freeze"]["frozen_case_gate_criteria"] = {
            **decision["criteria_freeze"]["frozen_case_gate_criteria"],
            "free_residual_relative_max": 1e-6,
        }
    elif mutation == "classification_drift":
        dispositions = dict(decision["criteria_freeze"]["dispositions"])
        dispositions["single_case_convergence"] = {
            "classification": "CASE_DIAGNOSTIC",
            "status": "DESCRIPTIVE_ONLY",
        }
        decision["criteria_freeze"]["dispositions"] = dispositions
    else:
        decision["criteria_freeze"]["case_manifest_registration_sha256_by_nodeid"][fixture["target"]] = "f" * 64
    with pytest.raises(MODULE.PolicyError, match="does not freeze the exact registered criteria scope"):
        MODULE._validate_hex8sri_frozen_case_criteria(
            case_manifest,
            decision=decision,
            target=fixture["target"],
            case_registration_sha256=binding_sha,
        )


def test_hex8sri_refined_three_criteria_freeze_is_exact_and_execution_remains_per_case(
    tmp_path: Path,
) -> None:
    refined_nodeids = list(MODULE.HEX8SRI_REFINED3_NODEIDS)
    fixture = _synthetic_hex8sri_execution_authorization(
        tmp_path,
        authorized_nodeids=refined_nodeids,
        frozen_nodeids=refined_nodeids,
    )
    frozen = MODULE._validate_hex8sri_criteria_freeze_decision(
        fixture["freeze_decision"],
        entry=fixture["entry"],
        source_fingerprint=fixture["source_fingerprint"],
        controller_provenance=fixture["controller"],
    )
    assert frozen["criteria_freeze"]["revision"] == MODULE.HEX8SRI_REFINED3_CRITERIA_CONTRACT_REVISION
    assert frozen["frozen_nodeids"] == refined_nodeids
    assert frozen["execution_authorized"] is False
    approved = _validate_synthetic_hex8sri_approval(fixture)
    assert approved["authorized_nodeids"] == refined_nodeids
    assert set(approved["limits_by_nodeid"]) == set(refined_nodeids)
    assert all(limit["attempts_per_nodeid"] == 1 for limit in approved["limits_by_nodeid"].values())


def test_hex8sri_criteria_freeze_rejects_cross_scope_or_extra_nodeids() -> None:
    assert MODULE._hex8sri_criteria_scope_for_nodeids(list(MODULE.HEX8SRI_REFINED3_NODEIDS)) == (
        MODULE.HEX8SRI_REFINED3_CRITERIA_CONTRACT_REVISION,
        MODULE.HEX8SRI_REFINED3_NODEIDS,
    )
    assert MODULE._hex8sri_criteria_scope_for_nodeids(
        [*MODULE.HEX8SRI_REFINED3_NODEIDS, MODULE.HEX8SRI_FIRST6_NODEIDS[0]]
    ) is None
    assert MODULE._hex8sri_criteria_scope_for_nodeids(list(MODULE.HEX8SRI_REFINED3_NODEIDS)[:-1]) is None


def test_hex8sri_execution_approval_requires_the_archived_matching_freeze(tmp_path: Path) -> None:
    fixture = _synthetic_hex8sri_execution_authorization(tmp_path)
    payload = fixture["payload"]
    decision = payload["owner_decision"]
    decision["criteria_freeze_record"]["sha256"] = "0" * 64
    decision_path = Path(payload["owner_decision_record"]["path"])
    decision_path.write_text(json.dumps(decision, sort_keys=True) + "\n", encoding="utf-8")
    payload["owner_decision_record"]["sha256"] = MODULE._sha256(decision_path)
    fixture["path"].write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(MODULE.PolicyError, match="Owner decision record path or SHA-256 is invalid"):
        _validate_synthetic_hex8sri_execution(fixture)


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ("missing_freeze", "Owner decision record is missing"),
        ("expired", "execution approval is expired or has an invalid validity interval"),
        ("manifest_drift", "does not authorize this exact scope, source, controller or nodeid"),
    ],
)
def test_hex8sri_execution_approval_rejects_missing_freeze_expiry_or_manifest_drift(
    tmp_path: Path, mutation: str, expected_error: str
) -> None:
    fixture = _synthetic_hex8sri_execution_authorization(tmp_path)
    payload = fixture["payload"]
    # Keep the decision JSON detached from the expected current manifest binding;
    # otherwise mutating this nested dict would mutate both sides of the check.
    decision = json.loads(json.dumps(payload["owner_decision"]))
    if mutation == "missing_freeze":
        decision["criteria_freeze_record"].update(
            path=str(fixture["store"] / "authorizations" / MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID / "owner-decisions" / "criteria-freeze" / "missing.json"),
            sha256="0" * 64,
        )
    elif mutation == "expired":
        decision["expires_at_utc"] = "2026-10-26T00:00:00Z"
    else:
        decision["case_manifests_by_nodeid"][fixture["target"]]["sha256"] = "0" * 64
    payload["owner_decision"] = decision
    decision_path = Path(payload["owner_decision_record"]["path"])
    decision_path.write_text(json.dumps(decision, sort_keys=True) + "\n", encoding="utf-8")
    payload["owner_decision_record"]["sha256"] = MODULE._sha256(decision_path)
    fixture["path"].write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(MODULE.PolicyError, match=expected_error):
        _validate_synthetic_hex8sri_execution(fixture)


def test_hex8sri_freeze_archive_is_no_replace_and_preserves_evidence_and_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _synthetic_hex8sri_execution_authorization(tmp_path)
    entry = fixture["entry"]
    decision = json.loads(json.dumps(fixture["freeze_decision"]))
    decision["decision_id"] = "owner-freeze-archive-0001"
    decision_path = tmp_path / "submitted-freeze.json"
    decision_path.write_text(json.dumps(decision, sort_keys=True) + "\n", encoding="utf-8")
    store = fixture["store"]
    ledger_path = store / entry["node_attempt_ledger"]["path"]
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_bytes = b'{"schema":"synthetic-ledger","entries":{}}\n'
    ledger_path.write_bytes(ledger_bytes)
    preflight_path, preflight_sha = fixture["preflight"]
    preflight_bytes = preflight_path.read_bytes()
    scope_id = MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID
    monkeypatch.setattr(MODULE, "load_policy", lambda *_args: {"worktrees": {scope_id: entry}})
    monkeypatch.setattr(MODULE, "resolve_targets", lambda *_args, **_kwargs: [fixture["target"]])
    monkeypatch.setattr(
        MODULE,
        "_registered_worktree",
        lambda *_args: (entry, Path(fixture["identity"]["root"]), Path(fixture["identity"]["root"]) / "src", fixture["identity"], fixture["source_fingerprint"]),
    )
    monkeypatch.setattr(MODULE, "_controller_provenance", lambda: fixture["controller"])
    monkeypatch.setattr(MODULE, "_run_root", lambda *_args: store)
    monkeypatch.setattr(
        MODULE,
        "_hex8sri_current_case_manifest_bindings",
        lambda *_args: fixture["manifest_bindings"],
    )
    result = MODULE.archive_hex8sri_owner_decision(decision_path)
    archived = Path(result["path"])
    assert result["state"] == "CRITERIA_FROZEN_EXECUTION_NOT_AUTHORIZED"
    assert result["execution_manifest_created"] is False
    assert result["attempt_reserved"] is False
    assert MODULE._sha256(archived) == result["sha256"]
    assert ledger_path.read_bytes() == ledger_bytes
    assert preflight_path.read_bytes() == preflight_bytes
    assert preflight_sha == MODULE._sha256(preflight_path)
    with pytest.raises(MODULE.PolicyError, match="refusing to overwrite"):
        MODULE.archive_hex8sri_owner_decision(decision_path)


def test_hex8sri_scope_refresh_leaves_historical_scope_registrations_unchanged() -> None:
    baseline = json.loads(
        subprocess.run(
            ["git", "show", "e25b32272d974dd1f34c03617721f95befde87de:development_autonomous_policy.json"],
            cwd=MODULE.ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    current = _policy()
    hex20_scope_id = MODULE.WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID
    assert set(current["worktrees"]) == set(baseline["worktrees"]) | {
        hex20_scope_id, MODULE.WP12B_HEX20_R2_WORKTREE_ID, MODULE.VV3D_WORKTREE_ID,
        MODULE.VV3D_R2_WORKTREE_ID,
    }
    for worktree_id, baseline_entry in baseline["worktrees"].items():
        if worktree_id == MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID:
            _assert_hex8sri_source_refresh_only(
                current["worktrees"][worktree_id], _hex8sri_pre_refresh_baseline()
            )
        elif worktree_id != "wp12_dynamics":
            assert current["worktrees"][worktree_id] == baseline_entry
    current_dynamics = current["worktrees"]["wp12_dynamics"]
    baseline_dynamics = baseline["worktrees"]["wp12_dynamics"]
    _assert_wp12a_p0_registration_extension(current_dynamics, baseline_dynamics)
    assert (
        current_dynamics["nodeid_registration_records"][: len(baseline_dynamics["nodeid_registration_records"])]
        == (baseline_dynamics["nodeid_registration_records"])
    )
    assert any(
        record["target"]
        == "tests/unit/test_wp07_uniform_base_acceleration.py::"
        "test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames"
        and record["worktree_head"] == "630d22b7667a0d84dd7b136b9f8c7d89ae00fc66"
        for record in current_dynamics["nodeid_registration_records"]
    )
    assert current["worktrees"][MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID]["execution_authorized"] is False
    assert (
        current["worktrees"][MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID]["allowed_nodeids"]
        == (baseline["worktrees"][MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID]["allowed_nodeids"])
    )
    assert current["worktrees"][MODULE.HEX8SRI_CONVERGENCE24_WORKTREE_ID]["attempt_limit_per_nodeid"] == 1
    assert current["worktrees"][hex20_scope_id]["allowed_nodeids"] in ([], [WP12B_HEX20_DIAGNOSTIC_NODEID])


def test_hex8sri_execution_test_contract_rejects_legacy_and_accepts_declared_contract(tmp_path: Path) -> None:
    module = Path("tests/verification/test_hex8_sri_convergence.py")
    test_path = tmp_path / module
    test_path.parent.mkdir(parents=True)
    target = f"{module.as_posix()}::test_convergence_case[hex8_standard-nu_0p3-4x2x2]"
    test_path.write_text(
        'def _authorized_case():\n    """Legacy identity: hex8sri codex/hex8sri-controller-registration."""\n    return None\n',
        encoding="utf-8",
    )
    with pytest.raises(MODULE.PolicyError, match="dedicated Owner-manifest/preflight contract"):
        MODULE._validate_hex8sri_execution_test_contract(tmp_path, target)

    contract_strings = (
        "QF_DEV_EXECUTION_MANIFEST_PATH",
        "QF_DEV_EXECUTION_MANIFEST_SHA256",
        "QF_DEV_OWNER_DECISION_ID",
        "QF_DEV_CASE_MANIFEST_PATH",
        "QF_DEV_PREFLIGHT_ID",
        "QF_DEV_PREFLIGHT_SHA256",
        "QF_DEV_TARGET_NODEID",
        "QF_DEV_CONTROLLER_ROOT",
        "QF_DEV_CONTROLLER_BRANCH",
        "QF_DEV_CONTROLLER_HEAD",
        "QF_DEV_CONTROLLER_RUNNER_SHA256",
        "QF_DEV_CONTROLLER_POLICY_SHA256",
        "QF_DEV_CONTROLLER_PLUGIN_SHA256",
        "hex8sri-convergence24",
        "OWNER_AUTHORIZED",
        "criteria_contract",
        "criteria_freeze",
        "CASE_GATE",
        "CASE_DIAGNOSTIC",
        "CAMPAIGN_GATE_DEFERRED",
        "NOT_ASSESSED",
        "negative_mean_loaded_face_uz",
    )
    source = (
        f'def _authorized_case():\n    """{MODULE.HEX8SRI_EXECUTION_TEST_CONTRACT_MARKER}"""\n'
        + "\n".join(f"    _ = {value!r}" for value in contract_strings)
        + "\n    return None\n"
    )
    test_path.write_text(source, encoding="utf-8")
    MODULE._validate_hex8sri_execution_test_contract(tmp_path, target)


def _wp12_dynamics_attestation(**updates: Any) -> str:
    payload: dict[str, Any] = {
        "schema": "qfsolver-wp12-dynamics-collect-only-v1",
        "expected_nodeid": WP12_DYNAMICS_PREFLIGHT_NODEID,
        "collected_nodeids": [WP12_DYNAMICS_PREFLIGHT_NODEID],
        "skip_markers": [],
        "bodies_executed": False,
        "solver_origin": "C:/source/src/solveur/__init__.py",
        "worktree_id": "wp12_dynamics",
        "selected_dofs_expected": 1,
        "selected_dofs": "1",
        "max_dofs_expected": None,
        "max_dofs": None,
        "exitstatus": 0,
    }
    payload.update(updates)
    return MODULE.WP12_DYNAMICS_PREFLIGHT_ATTESTATION_PREFIX + json.dumps(payload)


def test_wp12_dynamics_collect_only_command_is_limited_to_reviewed_exact_nodes(tmp_path: Path) -> None:
    command = MODULE.build_pytest_command(
        "fem_exploratory",
        [WP12_DYNAMICS_PREFLIGHT_NODEID],
        tmp_path,
        repository_root=tmp_path,
        source_root=tmp_path / "src",
        wp12_dynamics_collect_only_attestation=True,
        collect_only=True,
    )
    assert "--collect-only" in command
    assert command[-1] == WP12_DYNAMICS_PREFLIGHT_NODEID
    assert "wp12-dynamics-preflight" in command[3]

    for target in MODULE.WP12_DYNAMICS_PREFLIGHT_NODEIDS:
        command = MODULE.build_pytest_command(
            "fem_exploratory",
            [target],
            tmp_path,
            repository_root=tmp_path,
            source_root=tmp_path / "src",
            wp12_dynamics_collect_only_attestation=True,
            collect_only=True,
        )
        assert command[-1] == target
        assert "--collect-only" in command

    policy_targets = set(MODULE.load_policy()["worktrees"]["wp12_dynamics"]["allowed_nodeids"])
    assert set(MODULE.WP12_DYNAMICS_PREFLIGHT_NODEIDS) <= policy_targets

    with pytest.raises(MODULE.PolicyError, match="reviewed exact collect-only nodeids"):
        MODULE.build_pytest_command(
            "fem_exploratory",
            ["tests/unit/test_other.py::test_unregistered"],
            tmp_path,
            repository_root=tmp_path,
            source_root=tmp_path / "src",
            wp12_dynamics_collect_only_attestation=True,
            collect_only=True,
        )
    with pytest.raises(MODULE.PolicyError, match="collect-only without any skip override"):
        MODULE.build_pytest_command(
            "fem_exploratory",
            [WP12_DYNAMICS_PREFLIGHT_NODEID],
            tmp_path,
            repository_root=tmp_path,
            source_root=tmp_path / "src",
            wp12_dynamics_collect_only_attestation=True,
            allow_native_skip_override=True,
            collect_only=True,
        )


@pytest.mark.parametrize("target", MODULE.WP12_DYNAMICS_PREFLIGHT_NODEIDS[4:])
def test_wp12a_p0_preflight_routes_exact_registered_node_without_reservation(
    target: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str | None]] = []

    def fake_collect(nodeid: str, preflight_id: str | None, **kwargs: Any) -> dict[str, Any]:
        calls.append((nodeid, preflight_id))
        assert kwargs["worktree_id"] == "wp12_dynamics"
        assert kwargs["attestation_mode"] == "wp12_dynamics_collect_only_attestation"
        return {"state": "PREFLIGHT_PASS", "bodies_executed": False, "attempt_reserved": False}

    monkeypatch.setattr(MODULE, "_preflight_wp12_attested_pytest", fake_collect)
    monkeypatch.setattr(MODULE, "_reserve_node_attempt", lambda *args, **kwargs: pytest.fail("reservation forbidden"))
    result = MODULE.preflight_wp12_dynamics_pytest(target, "pf-123456789abc")
    assert calls == [(target, "pf-123456789abc")]
    assert result == {"state": "PREFLIGHT_PASS", "bodies_executed": False, "attempt_reserved": False}


def _wp12b_hex20_diagnostic_attestation(**updates: Any) -> str:
    payload: dict[str, Any] = {
        "schema": MODULE.WP12B_HEX20_DIAGNOSTIC_PREFLIGHT_SCHEMA,
        "expected_nodeid": WP12B_HEX20_DIAGNOSTIC_NODEID,
        "collected_nodeids": [WP12B_HEX20_DIAGNOSTIC_NODEID],
        "skip_markers": [],
        "bodies_executed": False,
        "solver_origin": "C:/source/src/solveur/__init__.py",
        "worktree_id": MODULE.WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID,
        "selected_dofs_expected": 60,
        "selected_dofs": "60",
        "max_dofs_expected": 60,
        "max_dofs": "60",
        "exitstatus": 0,
    }
    payload.update(updates)
    return MODULE.WP12B_HEX20_DIAGNOSTIC_PREFLIGHT_MARKER + json.dumps(payload)


def test_wp12b_hex20_collect_only_command_is_limited_to_its_exact_nodeid(tmp_path: Path) -> None:
    command = MODULE.build_pytest_command(
        "fem_exploratory",
        [WP12B_HEX20_DIAGNOSTIC_NODEID],
        tmp_path,
        repository_root=tmp_path,
        source_root=tmp_path / "src",
        wp12b_hex20_diagnostic_collect_only_attestation=True,
        collect_only=True,
    )
    assert "--collect-only" in command
    assert command[-1] == WP12B_HEX20_DIAGNOSTIC_NODEID
    assert "wp12b-hex20-diagnostic-preflight" in command[3]

    with pytest.raises(MODULE.PolicyError, match="one exact nodeid"):
        MODULE.build_pytest_command(
            "fem_exploratory",
            ["tests/unit/test_other.py::test_unregistered"],
            tmp_path,
            repository_root=tmp_path,
            source_root=tmp_path / "src",
            wp12b_hex20_diagnostic_collect_only_attestation=True,
            collect_only=True,
        )
    with pytest.raises(MODULE.PolicyError, match="one exact nodeid"):
        MODULE.build_pytest_command(
            "fem_exploratory",
            [WP12B_HEX20_DIAGNOSTIC_NODEID, "tests/unit/test_other.py::test_unregistered"],
            tmp_path,
            repository_root=tmp_path,
            source_root=tmp_path / "src",
            wp12b_hex20_diagnostic_collect_only_attestation=True,
            collect_only=True,
        )
    with pytest.raises(MODULE.PolicyError, match="one exact nodeid"):
        MODULE.build_pytest_command(
            "fem_exploratory",
            [WP12B_HEX20_DIAGNOSTIC_NODEID],
            tmp_path,
            repository_root=tmp_path,
            source_root=tmp_path / "src",
            wp12b_hex20_diagnostic_collect_only_attestation=True,
            collect_only=False,
        )
    with pytest.raises(MODULE.PolicyError, match="collect-only for its one exact nodeid"):
        MODULE.build_pytest_command(
            "fem_exploratory",
            [WP12B_HEX20_DIAGNOSTIC_NODEID],
            tmp_path,
            repository_root=tmp_path,
            source_root=tmp_path / "src",
            wp12b_hex20_diagnostic_collect_only_attestation=True,
            allow_native_skip_override=True,
            collect_only=True,
        )


@pytest.mark.parametrize(
    ("updates", "expected"),
    [
        ({}, "PREFLIGHT_PASS"),
        ({"collected_nodeids": []}, "PREFLIGHT_NODEID_NOT_CONFIRMED"),
        (
            {"collected_nodeids": [WP12B_HEX20_DIAGNOSTIC_NODEID, WP12B_HEX20_DIAGNOSTIC_NODEID]},
            "PREFLIGHT_NODEID_NOT_CONFIRMED",
        ),
        ({"skip_markers": [{"marker": "skip"}]}, "PREFLIGHT_SKIPPED"),
        ({"bodies_executed": True}, "PREFLIGHT_BODY_EXECUTION_DETECTED"),
        ({"solver_origin": "C:/wrong/solveur/__init__.py"}, "PREFLIGHT_WRONG_SOLVER_ORIGIN"),
        ({"worktree_id": "wp12_elements_loads"}, "PREFLIGHT_SCOPE_MISMATCH"),
        ({"selected_dofs": "30"}, "PREFLIGHT_SCOPE_MISMATCH"),
        ({"max_dofs": "30000"}, "PREFLIGHT_SCOPE_MISMATCH"),
        ({"exitstatus": 1}, "PREFLIGHT_FAILED"),
    ],
)
def test_wp12b_hex20_collect_only_attestation_fails_closed(updates: dict[str, Any], expected: str) -> None:
    status, payload = MODULE._validate_wp12b_hex20_diagnostic_collect_attestation(
        _wp12b_hex20_diagnostic_attestation(**updates),
        target=WP12B_HEX20_DIAGNOSTIC_NODEID,
        solver_origin="C:/source/src/solveur/__init__.py",
        selected_dofs=60,
    )
    assert status == expected
    assert payload is not None


def test_wp12b_hex20_child_attestor_records_one_skip_free_node_without_body_execution(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setenv("QF_DEV_WORKTREE_ID", MODULE.WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID)
    monkeypatch.setenv("QF_DEV_SELECTED_DOFS", "60")
    monkeypatch.setenv("QF_DEV_MAX_DOFS", "60")
    expected_origin = "C:/source/src/solveur/__init__.py"
    attestor = PLUGIN.ExactCollectOnlyAttestor(
        WP12B_HEX20_DIAGNOSTIC_NODEID,
        solver_origin=expected_origin,
        selected_dofs=60,
        max_dofs=60,
        schema=MODULE.WP12B_HEX20_DIAGNOSTIC_PREFLIGHT_SCHEMA,
        marker=MODULE.WP12B_HEX20_DIAGNOSTIC_PREFLIGHT_MARKER,
    )
    item = SimpleNamespace(nodeid=WP12B_HEX20_DIAGNOSTIC_NODEID, iter_markers=lambda: [])
    attestor.pytest_collection_finish(SimpleNamespace(items=[item]))
    attestor.pytest_sessionfinish(SimpleNamespace(), 0)
    output = capsys.readouterr().out.strip()
    status, payload = MODULE._validate_wp12b_hex20_diagnostic_collect_attestation(
        output,
        target=WP12B_HEX20_DIAGNOSTIC_NODEID,
        solver_origin=expected_origin,
        selected_dofs=60,
    )
    assert status == "PREFLIGHT_PASS"
    assert payload is not None and payload["bodies_executed"] is False
    assert payload["collected_nodeids"] == [WP12B_HEX20_DIAGNOSTIC_NODEID]


def test_wp12b_hex20_preflight_records_exact_collect_only_without_attempt_reservation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = WP12B_HEX20_DIAGNOSTIC_NODEID
    worktree_id = MODULE.WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID
    source_root = tmp_path / "source" / "src"
    source_root.mkdir(parents=True)
    source_checkout = source_root.parent
    store = tmp_path / "evidence"
    entry = {
        "worktree_id": worktree_id,
        "development_mandate_id": MODULE.WP12_OWNER_ENVELOPES[worktree_id]["development_mandate_id"],
        "max_fem_cases_per_attempt": 1,
        "target_max_dofs": 60,
        "evidence_root": str(store),
        "budgets": {
            "timeout_seconds": 300,
            "rss_soft_limit_mib": 4096,
            "process_tree_limit": 4,
            "output_total_limit_mib": 2,
            "output_stream_limit_mib": 1,
            "temporary_limit_mib": 8,
            "archive_size_limit_mib": 8,
        },
    }
    identity = {
        "head": "a" * 40,
        "tree": "b" * 40,
        "branch": "emptiesvoids-cloud/wp12b-hex20-consolidation",
        "status_short": "",
    }
    fingerprint = "c" * 64
    selection = {"selected_dofs": 60, "selection_basis": "Synthetic exact 60-DOF contract", "timeout_seconds": 300}
    policy = {"minimum_free_disk_mib": 1, "poll_interval_seconds": 0.01}
    expected_origin = str((source_root / "solveur" / "__init__.py").resolve())

    monkeypatch.setattr(MODULE, "resolve_targets", lambda *_args, **_kwargs: [target])
    monkeypatch.setattr(
        MODULE,
        "_registered_worktree",
        lambda *_args, **_kwargs: (entry, source_checkout, source_root, identity, fingerprint),
    )
    monkeypatch.setattr(MODULE, "_wp12_active_registration", lambda *_args, **_kwargs: selection)
    monkeypatch.setattr(MODULE, "_run_root", lambda *_args: store)
    monkeypatch.setattr(MODULE, "load_policy", lambda *_args: policy)
    monkeypatch.setattr(MODULE, "_controller_provenance", lambda: {"fingerprint": "d" * 64})
    monkeypatch.setattr(MODULE, "psutil", object())
    monkeypatch.setattr(
        MODULE,
        "_node_ledger_context",
        lambda *_args, **_kwargs: pytest.fail("collect-only preflight must not reserve or touch the attempt ledger"),
    )
    monkeypatch.setattr(MODULE, "build_child_environment", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(MODULE.shutil, "disk_usage", lambda *_args: SimpleNamespace(free=10**12))

    def supervised(command, *, output_dir, limits, **_kwargs):
        assert "--collect-only" in command
        assert command[-1] == target
        assert limits["timeout_seconds"] == 300
        (output_dir / "stdout.log").write_text(
            "QF_DEV_SOLVER_ORIGIN="
            + expected_origin
            + "\n"
            + _wp12b_hex20_diagnostic_attestation(solver_origin=expected_origin),
            encoding="utf-8",
        )
        (output_dir / "stderr.log").write_text("", encoding="utf-8")
        return SimpleNamespace(
            status="PASS",
            return_code=0,
            elapsed_seconds=0.01,
            peak_rss_bytes=1024,
            peak_process_count=1,
            stdout_bytes=512,
            stderr_bytes=0,
        )

    monkeypatch.setattr(MODULE, "run_supervised_command", supervised)
    result = MODULE.preflight_wp12b_hex20_diagnostic_pytest(target, "pf-a1b2c3d4e5f6", policy=policy)
    assert result["state"] == "PREFLIGHT_PASS"
    assert result["attempt_reserved"] is False
    assert result["ledger_touched"] is False
    assert result["nodeid"] == target
    receipt_path = Path(result["receipt"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    checksum = json.loads((receipt_path.parent / "preflight.sha256.json").read_text(encoding="utf-8"))
    assert checksum["sha256"] == result["receipt_sha256"] == MODULE._sha256(receipt_path)
    assert receipt["worktree_id"] == worktree_id
    assert receipt["collected_nodeids"] == [target]
    assert receipt["bodies_executed"] is False
    assert receipt["attempt_reserved"] is False
    assert receipt["ledger_touched"] is False
    assert receipt["attempt_ledger"]["sha256_before"] is None
    assert receipt["attempt_ledger"]["sha256_after"] is None


@pytest.mark.parametrize(
    ("updates", "expected"),
    [
        ({}, "PREFLIGHT_PASS"),
        ({"collected_nodeids": []}, "PREFLIGHT_NODEID_NOT_CONFIRMED"),
        (
            {"collected_nodeids": [WP12_DYNAMICS_PREFLIGHT_NODEID, WP12_DYNAMICS_PREFLIGHT_NODEID]},
            "PREFLIGHT_NODEID_NOT_CONFIRMED",
        ),
        ({"skip_markers": [{"marker": "skip"}]}, "PREFLIGHT_SKIPPED"),
        ({"bodies_executed": True}, "PREFLIGHT_BODY_EXECUTION_DETECTED"),
        ({"solver_origin": "C:/wrong/solveur/__init__.py"}, "PREFLIGHT_WRONG_SOLVER_ORIGIN"),
        ({"worktree_id": "rotor"}, "PREFLIGHT_SCOPE_MISMATCH"),
        ({"exitstatus": 1}, "PREFLIGHT_FAILED"),
        ({"selected_dofs": "3"}, "PREFLIGHT_SCOPE_MISMATCH"),
    ],
)
def test_wp12_dynamics_collect_only_attestation_fails_closed(updates: dict[str, Any], expected: str) -> None:
    status, payload = MODULE._validate_wp12_dynamics_collect_attestation(
        _wp12_dynamics_attestation(**updates),
        target=WP12_DYNAMICS_PREFLIGHT_NODEID,
        solver_origin="C:/source/src/solveur/__init__.py",
        selected_dofs=1,
    )
    assert status == expected
    assert payload is not None


def test_wp12_dynamics_collect_only_attestation_rejects_missing_or_duplicate_receipts() -> None:
    validate = MODULE._validate_wp12_dynamics_collect_attestation
    expected = {
        "target": WP12_DYNAMICS_PREFLIGHT_NODEID,
        "solver_origin": "C:/source/src/solveur/__init__.py",
        "selected_dofs": 1,
    }
    assert validate("", **expected) == ("PREFLIGHT_ATTESTATION_INVALID", None)
    line = _wp12_dynamics_attestation()
    status, payload = validate(line + "\n" + line, **expected)
    assert status == "PREFLIGHT_ATTESTATION_INVALID"
    assert payload is None


def test_wp12_dynamics_child_attestor_reports_skip_and_body_tripwires(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setenv("QF_DEV_WORKTREE_ID", "wp12_dynamics")
    expected_origin = "C:/source/src/solveur/__init__.py"
    marker = MODULE.WP12_DYNAMICS_PREFLIGHT_ATTESTATION_PREFIX
    attestor = PLUGIN.ExactCollectOnlyAttestor(
        WP12_DYNAMICS_PREFLIGHT_NODEID,
        solver_origin=expected_origin,
        selected_dofs=1,
        max_dofs=None,
        schema="qfsolver-wp12-dynamics-collect-only-v1",
        marker=marker,
    )
    skip = SimpleNamespace(name="skip", kwargs={"reason": "synthetic skip"})
    item = SimpleNamespace(
        nodeid=WP12_DYNAMICS_PREFLIGHT_NODEID,
        iter_markers=lambda: [skip],
    )
    attestor.pytest_collection_finish(SimpleNamespace(items=[item]))
    attestor.pytest_runtest_call(item)
    attestor.pytest_sessionfinish(SimpleNamespace(), 0)
    output = capsys.readouterr().out.strip()
    status, payload = MODULE._validate_wp12_dynamics_collect_attestation(
        output,
        target=WP12_DYNAMICS_PREFLIGHT_NODEID,
        solver_origin=expected_origin,
        selected_dofs=1,
    )
    assert status == "PREFLIGHT_SKIPPED"
    assert payload is not None and payload["bodies_executed"] is True


def _synthetic_wp12_dynamics_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    from contextlib import nullcontext

    policy = _policy()
    entry = policy["worktrees"]["wp12_dynamics"]
    target = WP12_DYNAMICS_NODEIDS[10]
    registration = next(record for record in reversed(entry["nodeid_registration_records"]) if record["target"] == target)
    source_root = tmp_path / "science" / "src"
    source_root.mkdir(parents=True)
    science_root = source_root.parent
    identity = {
        "root": str(science_root),
        "branch": entry["branch"],
        "head": "a" * 40,
        "tree": "b" * 40,
        "status_short": "",
    }
    source_fingerprint = registration["source_fingerprint"]
    controller_provenance = {
        "identity": {"root": "synthetic-controller", "head": "c" * 40, "tree": "d" * 40},
        "sha256": {"runner": "e" * 64, "pytest_plugin": "f" * 64, "policy": "1" * 64},
        "runtime": {"python_version": "3.synthetic", "pytest_version": "synthetic"},
    }
    store = tmp_path / "evidence"
    entry["evidence_root"] = str(store)
    (store / "locks").mkdir(parents=True)
    predecessor_path = store / "node-attempt-ledger.json"
    predecessor_mandate = MODULE.WP12_DYNAMICS_LEGACY_MANDATE_ID
    predecessor_payload = {
        "schema": "qfsolver-development-node-ledger-v1",
        "mandate_id": predecessor_mandate,
        "entries": {
            f"{predecessor_mandate}:wp12_dynamics:{nodeid}": [
                {"attempt": index} for index in range(1, count + 1)
            ]
            for nodeid, count in zip(MODULE.WP12_DYNAMICS_PREFLIGHT_NODEIDS[:4], (3, 1, 1, 0), strict=True)
            if count
        },
    }
    predecessor_path.write_text(json.dumps(predecessor_payload, sort_keys=True) + "\n", encoding="utf-8")
    predecessor_sha = MODULE._sha256(predecessor_path)
    entry["node_attempt_ledger"]["predecessor"]["sha256"] = predecessor_sha
    ledger_path = store / entry["node_attempt_ledger"]["path"]
    preflight_id = "pf-123456789abc"
    receipt_dir = store / "worktrees" / "wp12_dynamics" / "preflight" / preflight_id
    (receipt_dir / "output").mkdir(parents=True)
    solver_origin = str(source_root / "solveur" / "__init__.py")
    receipt = {
        "schema": "qfsolver-development-wp12-dynamics-preflight-v2",
        "mode": "DEVELOPMENT_AUTONOMOUS",
        "mandate_id": entry["development_mandate_id"],
        "worktree_id": "wp12_dynamics",
        "target": target,
        "preflight_id": preflight_id,
        "phase": "PYTEST_COLLECT_ONLY",
        "state": "PREFLIGHT_PASS",
        "bodies_executed": False,
        "attempt_reserved": False,
        "ledger_touched": False,
        "identity": identity,
        "identity_after": identity,
        "source_fingerprint": source_fingerprint,
        "source_fingerprint_after": source_fingerprint,
        "registration": {**registration, "timeout_seconds": 300},
        "attempt_ledger": {
            "path": str(ledger_path),
            "sha256_before": None,
            "sha256_after": None,
            "touched": False,
            "predecessor": entry["node_attempt_ledger"]["predecessor"],
            "predecessor_sha256_before": predecessor_sha,
            "predecessor_sha256_after": predecessor_sha,
        },
        "solver_origin_expected": solver_origin,
        "solver_origin_observed": solver_origin,
        "controller_provenance": controller_provenance,
        "controller_provenance_after": controller_provenance,
        "collected_nodeids": [target],
        "skip_markers": [],
        "return_code": 0,
        "budgets": {"timeout_seconds": 300},
    }
    receipt_path = receipt_dir / "preflight.json"
    receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    receipt_sha = MODULE._sha256(receipt_path)
    (receipt_dir / "preflight.sha256.json").write_text(
        json.dumps({"sha256": receipt_sha}, sort_keys=True) + "\n", encoding="utf-8"
    )

    monkeypatch.setattr(MODULE, "load_policy", lambda *_args, **_kwargs: policy)
    monkeypatch.setattr(MODULE, "_registered_root", lambda *_args, **_kwargs: science_root)
    monkeypatch.setattr(
        MODULE,
        "resolve_targets",
        lambda scope, requested, current_policy, *, worktree_id=None: [requested]
        if scope == "fem_exploratory"
        and worktree_id == "wp12_dynamics"
        and requested in current_policy["worktrees"][worktree_id]["allowed_nodeids"]
        else pytest.fail("synthetic dynamics fixture must resolve only its exact registered nodeid"),
    )
    monkeypatch.setattr(
        MODULE,
        "_test_source_dependency_inventory",
        lambda *_args: registration.get("test_source_dependencies", {}),
    )
    monkeypatch.setattr(
        MODULE,
        "_registered_worktree",
        lambda *_args, **_kwargs: (entry, science_root, source_root, identity, source_fingerprint),
    )
    monkeypatch.setattr(MODULE, "_run_root", lambda *_args, **_kwargs: store)
    monkeypatch.setattr(MODULE, "_controller_provenance", lambda: controller_provenance)
    monkeypatch.setattr(MODULE, "_wp12_resource_lock", lambda *_args, **_kwargs: nullcontext())
    monkeypatch.setattr(MODULE, "psutil", object())
    monkeypatch.setattr(MODULE.shutil, "disk_usage", lambda _path: SimpleNamespace(free=2 * 1024**3))
    monkeypatch.setattr(MODULE, "_worktree_source_fingerprint", lambda *_args, **_kwargs: source_fingerprint)
    return {
        "policy": policy,
        "entry": entry,
        "target": target,
        "identity": identity,
        "source_root": source_root,
        "science_root": science_root,
        "source_fingerprint": source_fingerprint,
        "controller_provenance": controller_provenance,
        "store": store,
        "ledger_path": ledger_path,
        "predecessor_path": predecessor_path,
        "predecessor_sha256": predecessor_sha,
        "preflight_id": preflight_id,
        "preflight_path": receipt_path,
        "preflight_sha256": receipt_sha,
    }


def test_wp12_dynamics_uses_empty_scope_ledger_and_preserves_legacy_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _synthetic_wp12_dynamics_context(tmp_path, monkeypatch)
    legacy_before = fixture["predecessor_path"].read_bytes()
    legacy_hash = MODULE._sha256(fixture["predecessor_path"])

    ledger_path, lock_path, mandate_id, predecessor = MODULE._node_ledger_context(
        fixture["policy"], fixture["store"], "wp12_dynamics"
    )

    assert ledger_path == fixture["ledger_path"]
    assert lock_path == ledger_path.with_suffix(".lock")
    assert mandate_id == fixture["entry"]["development_mandate_id"]
    assert predecessor == fixture["entry"]["node_attempt_ledger"]["predecessor"]
    assert not ledger_path.exists()
    assert MODULE._sha256(fixture["predecessor_path"]) == legacy_hash
    assert fixture["predecessor_path"].read_bytes() == legacy_before


def test_wp12_dynamics_refuses_changed_legacy_ledger_without_creating_scope_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _synthetic_wp12_dynamics_context(tmp_path, monkeypatch)
    fixture["predecessor_path"].write_bytes(fixture["predecessor_path"].read_bytes() + b" ")

    with pytest.raises(MODULE.PolicyError, match="historical WP12-A dynamics ledger changed"):
        MODULE._node_ledger_context(fixture["policy"], fixture["store"], "wp12_dynamics")

    assert not fixture["ledger_path"].exists()


@pytest.mark.parametrize(
    ("schema", "mandate_id"),
    [
        ("qfsolver-development-node-ledger-v1", "DEVELOPMENT_AUTONOMOUS-WP12-DYNAMICS-2026-10-26-v1"),
        ("qfsolver-development-node-ledger-v2", "DEVELOPMENT_AUTONOMOUS-FEM-2026-10-24-v1"),
    ],
    ids=["wrong-schema", "wrong-mandate"],
)
def test_wp12_dynamics_refuses_incompatible_ledger_before_reservation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    schema: str,
    mandate_id: str,
) -> None:
    fixture = _synthetic_wp12_dynamics_context(tmp_path, monkeypatch)
    bad_payload = {
        "schema": schema,
        "mandate_id": mandate_id,
        "predecessor": fixture["entry"]["node_attempt_ledger"]["predecessor"],
        "entries": {},
    }
    fixture["ledger_path"].write_text(json.dumps(bad_payload, sort_keys=True) + "\n", encoding="utf-8")
    bad_bytes = fixture["ledger_path"].read_bytes()
    old_bytes = fixture["predecessor_path"].read_bytes()

    with pytest.raises(MODULE.PolicyError, match="identity/schema mismatch"):
        MODULE._node_ledger_context(fixture["policy"], fixture["store"], "wp12_dynamics")
    with pytest.raises(MODULE.PolicyError, match="identity/schema mismatch"):
        MODULE._reserve_node_attempt(
            fixture["ledger_path"],
            fixture["ledger_path"].with_suffix(".lock"),
            mandate_id=fixture["entry"]["development_mandate_id"],
            worktree_id="wp12_dynamics",
            target=fixture["target"],
            series_id="dev-wp12-invalid-ledger-0001",
            source_fingerprint=fixture["source_fingerprint"],
            reason="Synthetic invalid-ledger reservation must be refused.",
            maximum=10,
            total_maximum=130,
            predecessor=fixture["entry"]["node_attempt_ledger"]["predecessor"],
        )

    assert fixture["ledger_path"].read_bytes() == bad_bytes
    assert fixture["predecessor_path"].read_bytes() == old_bytes


def test_wp12_dynamics_preflight_receipt_validation_binds_exact_identities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _synthetic_wp12_dynamics_context(tmp_path, monkeypatch)
    receipt_path, receipt_sha = MODULE._validate_wp12_dynamics_preflight_receipt(
        fixture["store"],
        fixture["preflight_id"],
        target=fixture["target"],
        identity=fixture["identity"],
        source_fingerprint=fixture["source_fingerprint"],
        controller_provenance=fixture["controller_provenance"],
        policy=fixture["policy"],
    )
    assert receipt_path == fixture["preflight_path"]
    assert receipt_sha == fixture["preflight_sha256"]


def test_wp12_dynamics_campaign_refreshes_preflight_and_manifest_after_prior_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _synthetic_wp12_dynamics_context(tmp_path, monkeypatch)
    entry = fixture["entry"]
    old_preflight_bytes = fixture["preflight_path"].read_bytes()

    MODULE._reserve_node_attempt(
        fixture["ledger_path"],
        fixture["ledger_path"].with_suffix(".lock"),
        mandate_id=entry["development_mandate_id"],
        worktree_id="wp12_dynamics",
        target=fixture["target"],
        series_id="dev-synthetic-prior-0001",
        source_fingerprint=fixture["source_fingerprint"],
        reason="Synthetic prior case used to advance the shared campaign ledger.",
        maximum=entry["attempt_limit_per_nodeid"],
        total_maximum=entry["max_total_attempts"],
        authorization_id="wp12-synthetic-prior-auth-001",
        owner_decision_id="owner-synthetic-prior-001",
        predecessor=entry["node_attempt_ledger"]["predecessor"],
        controller_fingerprint="2" * 64,
    )
    assert fixture["ledger_path"].is_file()
    assert fixture["preflight_path"].read_bytes() == old_preflight_bytes

    with pytest.raises(MODULE.PolicyError, match="does not match this exact source, controller, ledger and nodeid"):
        MODULE.prepare_wp12_execution_manifest(
            "wp12_dynamics", fixture["target"], "wp12-synth-stale-0001", preflight_id=fixture["preflight_id"]
        )
    assert not (fixture["store"] / "authorizations" / "wp12_dynamics" / "wp12-synth-stale-0001.json").exists()

    expected_origin = str((fixture["source_root"] / "solveur" / "__init__.py").resolve())

    def synthetic_collect_only(command, *, output_dir, **_kwargs):
        assert "--collect-only" in command
        assert command[-1] == fixture["target"]
        attestation = _wp12_dynamics_attestation(
            expected_nodeid=fixture["target"],
            collected_nodeids=[fixture["target"]],
            solver_origin=expected_origin,
        )
        (output_dir / "stdout.log").write_text(
            f"QF_DEV_SOLVER_ORIGIN={expected_origin}\n{attestation}", encoding="utf-8"
        )
        (output_dir / "stderr.log").write_text("", encoding="utf-8")
        return SimpleNamespace(
            status="PASS",
            return_code=0,
            elapsed_seconds=0.01,
            peak_rss_bytes=1024,
            peak_process_count=1,
            stdout_bytes=512,
            stderr_bytes=0,
        )

    monkeypatch.setattr(MODULE, "run_supervised_command", synthetic_collect_only)
    refreshed = MODULE.preflight_wp12_dynamics_pytest(
        fixture["target"], "pf-123456789abd", policy=fixture["policy"]
    )

    assert refreshed["state"] == "PREFLIGHT_PASS"
    assert refreshed["bodies_executed"] is False
    assert refreshed["attempt_reserved"] is False
    assert refreshed["ledger_touched"] is False
    refreshed_receipt, refreshed_sha = MODULE._validate_wp12_dynamics_preflight_receipt(
        fixture["store"],
        refreshed["preflight_id"],
        target=fixture["target"],
        identity=fixture["identity"],
        source_fingerprint=fixture["source_fingerprint"],
        controller_provenance=fixture["controller_provenance"],
        policy=fixture["policy"],
    )
    assert refreshed_receipt == Path(refreshed["receipt"])
    assert refreshed_sha == refreshed["receipt_sha256"]

    prepared = MODULE.prepare_wp12_execution_manifest(
        "wp12_dynamics",
        fixture["target"],
        "wp12-synth-refreshed-0001",
        preflight_id=refreshed["preflight_id"],
    )
    manifest = json.loads(Path(prepared["path"]).read_text(encoding="utf-8"))
    assert manifest["state"] == "PREPARED_NOT_AUTHORIZED"
    assert manifest["preflight"] == {
        "preflight_id": refreshed["preflight_id"],
        "receipt_path": str(refreshed_receipt),
        "receipt_sha256": refreshed_sha,
    }
    assert manifest["limits"]["timeout_seconds"] == 300


def test_wp12a_other_case_reservation_invalidates_prepared_case_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _synthetic_wp12_dynamics_context(tmp_path, monkeypatch)
    entry = fixture["entry"]
    other_target = MODULE.WP12_DYNAMICS_PREFLIGHT_NODEIDS[0]
    assert other_target != fixture["target"]
    original_preflight = fixture["preflight_path"].read_bytes()
    predecessor = fixture["predecessor_path"].read_bytes()

    MODULE._reserve_node_attempt(
        fixture["ledger_path"],
        fixture["ledger_path"].with_suffix(".lock"),
        mandate_id=entry["development_mandate_id"],
        worktree_id="wp12_dynamics",
        target=other_target,
        series_id="dev-synthetic-other-case-0001",
        source_fingerprint=fixture["source_fingerprint"],
        reason="Synthetic independent case advances only a temporary campaign ledger.",
        maximum=entry["attempt_limit_per_nodeid"],
        total_maximum=entry["max_total_attempts"],
        authorization_id="wp12-synthetic-other-auth-001",
        owner_decision_id="owner-synthetic-other-001",
        predecessor=entry["node_attempt_ledger"]["predecessor"],
        controller_fingerprint="2" * 64,
    )

    ledger_after_other_case = fixture["ledger_path"].read_bytes()
    with pytest.raises(MODULE.PolicyError, match="does not match this exact source, controller, ledger and nodeid"):
        MODULE.prepare_wp12_execution_manifest(
            "wp12_dynamics", fixture["target"], "wp12-synthetic-case-b-0001", preflight_id=fixture["preflight_id"]
        )
    assert fixture["ledger_path"].read_bytes() == ledger_after_other_case
    assert fixture["preflight_path"].read_bytes() == original_preflight
    assert fixture["predecessor_path"].read_bytes() == predecessor
    assert not (fixture["store"] / "authorizations" / "wp12_dynamics" / "wp12-synthetic-case-b-0001.json").exists()


def test_wp12a_ledger_change_between_preflight_and_reservation_is_refused_under_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _synthetic_wp12_dynamics_context(tmp_path, monkeypatch)
    entry = fixture["entry"]
    assert not fixture["ledger_path"].exists()
    fixture["ledger_path"].write_bytes(b'{"unexpected":"mutation"}\n')
    unexpected = fixture["ledger_path"].read_bytes()
    with pytest.raises(MODULE.PolicyError, match="ledger changed before reservation"):
        MODULE._reserve_node_attempt(
            fixture["ledger_path"],
            fixture["ledger_path"].with_suffix(".lock"),
            mandate_id=entry["development_mandate_id"],
            worktree_id="wp12_dynamics",
            target=fixture["target"],
            series_id="dev-synthetic-ledger-race-0001",
            source_fingerprint=fixture["source_fingerprint"],
            reason="Synthetic mutation between receipt validation and reservation.",
            maximum=entry["attempt_limit_per_nodeid"],
            total_maximum=entry["max_total_attempts"],
            predecessor=entry["node_attempt_ledger"]["predecessor"],
            expected_ledger_sha256=None,
            require_ledger_snapshot=True,
        )
    assert fixture["ledger_path"].read_bytes() == unexpected


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("bodies_executed", True),
        ("attempt_reserved", True),
        ("ledger_touched", True),
        ("skip_markers", [{"marker": "skip"}]),
        ("collected_nodeids", []),
        ("solver_origin_observed", "C:/wrong/solveur/__init__.py"),
        ("identity_after", {"head": "0" * 40}),
        ("source_fingerprint_after", "0" * 64),
        ("controller_provenance_after", {"changed": True}),
    ],
)
def test_wp12_dynamics_preflight_receipt_rejects_tampered_attestations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: Any
) -> None:
    fixture = _synthetic_wp12_dynamics_context(tmp_path, monkeypatch)
    path = fixture["preflight_path"]
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt[field] = value
    path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    (path.parent / "preflight.sha256.json").write_text(
        json.dumps({"sha256": MODULE._sha256(path)}, sort_keys=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(MODULE.PolicyError, match="does not match"):
        MODULE._validate_wp12_dynamics_preflight_receipt(
            fixture["store"],
            fixture["preflight_id"],
            target=fixture["target"],
            identity=fixture["identity"],
            source_fingerprint=fixture["source_fingerprint"],
            controller_provenance=fixture["controller_provenance"],
            policy=fixture["policy"],
        )


def test_wp12_dynamics_manifest_preparation_and_validation_bind_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _synthetic_wp12_dynamics_context(tmp_path, monkeypatch)
    prepared = MODULE.prepare_wp12_execution_manifest(
        "wp12_dynamics", fixture["target"], "wp12-synth-auth-0001", preflight_id=fixture["preflight_id"]
    )
    manifest_path = Path(prepared["path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["state"] == "PREPARED_NOT_AUTHORIZED"
    assert manifest["execution_authorized"] is False
    assert manifest["do_not_execute"] is True
    assert manifest["preflight"] == {
        "preflight_id": fixture["preflight_id"],
        "receipt_path": str(fixture["preflight_path"]),
        "receipt_sha256": fixture["preflight_sha256"],
    }
    with pytest.raises(MODULE.PolicyError, match="collect-only preflight"):
        MODULE.prepare_wp12_execution_manifest("wp12_dynamics", fixture["target"], "wp12-synth-auth-0002")

    manifest["state"] = "OWNER_AUTHORIZED"
    manifest["execution_authorized"] = True
    manifest["do_not_execute"] = False
    manifest["owner_decision"] = {
        "status": "APPROVED",
        "decision_id": "owner-wp12a-contract-0001",
        "approved_by": "Owner",
        "approved_at_utc": "2026-10-28T10:00:00Z",
        "reason": "Synthetic exact-case WP12-A execution authorization for contract test.",
    }
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    selection = MODULE._wp12_active_registration(
        "wp12_dynamics", fixture["target"], fixture["entry"], fixture["source_fingerprint"]
    )
    receipt = MODULE._validate_wp12_execution_manifest(
        manifest_path,
        worktree_id="wp12_dynamics",
        target=fixture["target"],
        entry=fixture["entry"],
        identity=fixture["identity"],
        source_fingerprint=fixture["source_fingerprint"],
        controller_fingerprint=MODULE._stable_fingerprint(fixture["controller_provenance"]),
        selection=selection,
        preflight_id=fixture["preflight_id"],
        preflight_receipt=(fixture["preflight_path"], fixture["preflight_sha256"]),
    )
    assert receipt["decision_id"] == "owner-wp12a-contract-0001"
    assert receipt["authorization_id"] == "wp12-synth-auth-0001"
    with pytest.raises(MODULE.PolicyError, match="does not bind its successful exact-node preflight"):
        MODULE._validate_wp12_execution_manifest(
            manifest_path,
            worktree_id="wp12_dynamics",
            target=fixture["target"],
            entry=fixture["entry"],
            identity=fixture["identity"],
            source_fingerprint=fixture["source_fingerprint"],
            controller_fingerprint=MODULE._stable_fingerprint(fixture["controller_provenance"]),
            selection=selection,
            preflight_id="pf-000000000000",
            preflight_receipt=(fixture["preflight_path"], fixture["preflight_sha256"]),
        )


def test_wp12a_batch_lock_serializes_dynamics_and_preserves_other_scope_lock_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from contextlib import contextmanager

    calls: list[Path] = []

    @contextmanager
    def synthetic_lock(path: Path):
        calls.append(Path(path))
        yield

    monkeypatch.setattr(MODULE, "_exclusive_file_lock", synthetic_lock)
    ledger_path = tmp_path / "node-attempt-ledger-wp12-dynamics-v2.json"
    ledger_lock = tmp_path / "node-attempt-ledger.lock"
    with MODULE._node_attempt_locks(ledger_path, ledger_lock, "wp12_dynamics"):
        assert calls == [ledger_path.with_suffix(".batch.lock"), ledger_lock]

    calls.clear()
    MODULE._WP12A_BATCH_LOCK_LOCAL.held = True
    try:
        with MODULE._node_attempt_locks(ledger_path, ledger_lock, "wp12_dynamics"):
            assert calls == [ledger_lock]
    finally:
        MODULE._WP12A_BATCH_LOCK_LOCAL.held = False

    calls.clear()
    with MODULE._node_attempt_locks(ledger_path, ledger_lock, MODULE.WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID):
        assert calls == [ledger_lock]


def _synthetic_wp12a_batch_manifest_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    fixture = _synthetic_wp12_dynamics_context(tmp_path, monkeypatch)
    target = fixture["target"]
    auth_id = "wp12-synth-batch-auth-01"
    prepared = MODULE.prepare_wp12_execution_manifest(
        "wp12_dynamics", target, auth_id, preflight_id=fixture["preflight_id"]
    )
    prepared_path = Path(prepared["path"]).resolve(strict=True)
    prepared_sha = MODULE._sha256(prepared_path)

    batch_root = fixture["store"] / "authorizations" / "wp12_dynamics" / "batches" / "wp12a-p0-synthetic-01"
    batch_root.mkdir(parents=True)
    contract_path = batch_root / "contract.json"
    decision_path = batch_root / "owner-decision.json"
    contract_path.write_text('{"schema":"synthetic-closed-contract"}\n', encoding="utf-8")
    decision_path.write_text('{"schema":"synthetic-owner-decision"}\n', encoding="utf-8")

    monkeypatch.setattr(MODULE, "ROOT", tmp_path / "controller-repository")
    # The case manifest is fully synthetic and stays below pytest's temp path.
    case_path = MODULE.ROOT / "qualification" / "0_2_12" / "wp12a_p0" / "case_manifests" / "case-01.json"
    case_path.parent.mkdir(parents=True)
    case_path.write_text(json.dumps({"nodeid": target}, sort_keys=True) + "\n", encoding="utf-8")
    case_sha = MODULE._sha256(case_path)

    decision_id = "owner-synthetic-p0-batch-01"
    binding = {
        "campaign_id": "wp12a-p0-synthetic-01",
        "contract_path": str(contract_path.resolve()),
        "contract_sha256": MODULE._sha256(contract_path),
        "decision_path": str(decision_path.resolve()),
        "decision_id": decision_id,
        "decision_sha256": MODULE._sha256(decision_path),
        "case_ordinal": 1,
        "nodeid": target,
        "case_manifest_path": str(case_path.resolve()),
        "case_manifest_sha256": case_sha,
        "preflight_id": fixture["preflight_id"],
        "preflight_receipt_sha256": fixture["preflight_sha256"],
        "authorization_id": auth_id,
        "prepared_manifest_path": str(prepared_path),
        "prepared_manifest_sha256": prepared_sha,
    }
    authorized_path = fixture["store"] / "authorizations" / "wp12_dynamics" / "owner-authorized" / f"{auth_id}.json"
    authorized_path.parent.mkdir(parents=True)
    authorized_manifest = json.loads(prepared_path.read_text(encoding="utf-8"))
    authorized_manifest.update(
        {
            "state": "OWNER_AUTHORIZED",
            "execution_authorized": True,
            "do_not_execute": False,
            "batch_authorization": binding,
            "owner_decision": {
                "status": "APPROVED",
                "decision_id": decision_id,
                "approved_by": "Owner",
                "approved_at_utc": "2026-10-29T10:00:00Z",
                "reason": "Synthetic batch contract validation; no scientific run is performed.",
            },
        }
    )
    authorized_path.write_text(json.dumps(authorized_manifest, sort_keys=True) + "\n", encoding="utf-8")
    selection = MODULE._wp12_active_registration(
        "wp12_dynamics", target, fixture["entry"], fixture["source_fingerprint"]
    )
    return {**fixture, "target": target, "binding": binding, "authorized_path": authorized_path, "selection": selection}


def test_wp12_dynamics_batch_manifest_requires_and_validates_all_bound_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _synthetic_wp12a_batch_manifest_context(tmp_path, monkeypatch)
    receipt = MODULE._validate_wp12_execution_manifest(
        fixture["authorized_path"],
        worktree_id="wp12_dynamics",
        target=fixture["target"],
        entry=fixture["entry"],
        identity=fixture["identity"],
        source_fingerprint=fixture["source_fingerprint"],
        controller_fingerprint=MODULE._stable_fingerprint(fixture["controller_provenance"]),
        selection=fixture["selection"],
        preflight_id=fixture["preflight_id"],
        preflight_receipt=(fixture["preflight_path"], fixture["preflight_sha256"]),
        batch_binding=fixture["binding"],
    )
    assert receipt["decision_id"] == fixture["binding"]["decision_id"]
    assert receipt["authorization_id"] == fixture["binding"]["authorization_id"]

    with pytest.raises(MODULE.PolicyError, match="official batch execution path"):
        MODULE._validate_wp12_execution_manifest(
            fixture["authorized_path"],
            worktree_id="wp12_dynamics",
            target=fixture["target"],
            entry=fixture["entry"],
            identity=fixture["identity"],
            source_fingerprint=fixture["source_fingerprint"],
            controller_fingerprint=MODULE._stable_fingerprint(fixture["controller_provenance"]),
            selection=fixture["selection"],
            preflight_id=fixture["preflight_id"],
            preflight_receipt=(fixture["preflight_path"], fixture["preflight_sha256"]),
        )


@pytest.mark.parametrize("bound_file", ["contract", "decision", "prepared", "case"])
def test_wp12_dynamics_batch_manifest_refuses_changed_bound_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bound_file: str
) -> None:
    fixture = _synthetic_wp12a_batch_manifest_context(tmp_path, monkeypatch)
    path = Path(fixture["binding"][{
        "contract": "contract_path",
        "decision": "decision_path",
        "prepared": "prepared_manifest_path",
        "case": "case_manifest_path",
    }[bound_file]])
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(MODULE.PolicyError, match="identity or SHA-256 changed"):
        MODULE._validate_wp12_execution_manifest(
            fixture["authorized_path"],
            worktree_id="wp12_dynamics",
            target=fixture["target"],
            entry=fixture["entry"],
            identity=fixture["identity"],
            source_fingerprint=fixture["source_fingerprint"],
            controller_fingerprint=MODULE._stable_fingerprint(fixture["controller_provenance"]),
            selection=fixture["selection"],
            preflight_id=fixture["preflight_id"],
            preflight_receipt=(fixture["preflight_path"], fixture["preflight_sha256"]),
            batch_binding=fixture["binding"],
        )


def test_wp12_dynamics_synthetic_end_to_end_reserves_and_archives_without_running_pytest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _synthetic_wp12_dynamics_context(tmp_path, monkeypatch)
    predecessor_before = fixture["predecessor_path"].read_bytes()
    predecessor_hash = MODULE._sha256(fixture["predecessor_path"])
    prepared = MODULE.prepare_wp12_execution_manifest(
        "wp12_dynamics", fixture["target"], "wp12-synth-e2e-0001", preflight_id=fixture["preflight_id"]
    )
    manifest_path = Path(prepared["path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["state"] = "OWNER_AUTHORIZED"
    manifest["execution_authorized"] = True
    manifest["do_not_execute"] = False
    manifest["owner_decision"] = {
        "status": "APPROVED",
        "decision_id": "owner-wp12a-e2e-0001",
        "approved_by": "Owner",
        "approved_at_utc": "2026-10-28T10:00:00Z",
        "reason": "Synthetic Owner authorization drives the bounded launcher contract test.",
    }
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    calls: list[dict[str, Any]] = []

    def fake_supervised(command, *, cwd, environment, output_dir, temporary_dir, limits, poll_interval):
        calls.append({"command": command, "cwd": cwd, "environment": environment, "limits": limits})
        assert command[-1] == fixture["target"]
        assert "--collect-only" not in command
        assert limits["timeout_seconds"] == 300
        (output_dir / "stdout.log").write_text("synthetic launch stub; pytest body deliberately not invoked\n", encoding="utf-8")
        (output_dir / "stderr.log").write_text("", encoding="utf-8")
        return SimpleNamespace(
            status="PASS",
            return_code=0,
            elapsed_seconds=0.01,
            peak_rss_bytes=1024,
            peak_process_count=1,
            stdout_bytes=64,
            stderr_bytes=0,
            archive_bytes=128,
            temporary_bytes=0,
            stop_reason=None,
        )

    monkeypatch.setattr(MODULE, "run_supervised_command", fake_supervised)
    result, exit_code = MODULE.run_pytest(
        "fem_exploratory",
        fixture["target"],
        "dev-synthetic-wp12a0001",
        worktree_id="wp12_dynamics",
        reason="Synthetic e2e launcher path; supervised child is stubbed and no mechanics run.",
        preflight_id=fixture["preflight_id"],
        execution_manifest=manifest_path,
    )
    assert exit_code == 0 and result["state"] == "PASS"
    assert len(calls) == 1
    assert calls[0]["environment"]["QF_DEV_SELECTED_DOFS"] == "1"
    assert calls[0]["environment"]["QF_DEV_EVIDENCE_ROOT"] == str(fixture["store"])
    run_record = json.loads(Path(result["record"]).read_text(encoding="utf-8"))
    assert run_record["preflight_receipt"] == {
        "path": str(fixture["preflight_path"]),
        "sha256": fixture["preflight_sha256"],
    }
    assert run_record["execution_manifest"]["authorization_id"] == "wp12-synth-e2e-0001"
    assert run_record["execution_manifest"]["decision_id"] == "owner-wp12a-e2e-0001"
    ledger = json.loads(fixture["ledger_path"].read_text(encoding="utf-8"))
    key = f"{fixture['entry']['development_mandate_id']}:wp12_dynamics:{fixture['target']}"
    attempt = ledger["entries"][key][0]
    assert ledger["schema"] == "qfsolver-development-node-ledger-v2"
    assert ledger["predecessor"] == fixture["entry"]["node_attempt_ledger"]["predecessor"]
    assert attempt["state"] == "PASS"
    assert attempt["authorization_id"] == "wp12-synth-e2e-0001"
    assert attempt["owner_decision_id"] == "owner-wp12a-e2e-0001"
    assert attempt["source_fingerprint"] == fixture["source_fingerprint"]
    assert attempt["predecessor_attempts_for_nodeid"] == 0
    assert fixture["predecessor_path"].read_bytes() == predecessor_before
    assert MODULE._sha256(fixture["predecessor_path"]) == predecessor_hash
    assert MODULE._node_ledger_context(fixture["policy"], fixture["store"], "wp12_dynamics")[0] == fixture[
        "ledger_path"
    ]

    current_ledger_bytes = fixture["ledger_path"].read_bytes()
    with pytest.raises(MODULE.PolicyError, match="authorization ID has already been consumed"):
        MODULE._reserve_node_attempt(
            fixture["ledger_path"],
            fixture["ledger_path"].with_suffix(".lock"),
            mandate_id=fixture["entry"]["development_mandate_id"],
            worktree_id="wp12_dynamics",
            target=fixture["target"],
            series_id="dev-wp12-e2e-duplicate-authorization",
            source_fingerprint=fixture["source_fingerprint"],
            reason="Synthetic duplicate authorization must not reserve again.",
            maximum=10,
            total_maximum=130,
            authorization_id="wp12-synth-e2e-0001",
            owner_decision_id="owner-wp12a-e2e-0001",
            predecessor=fixture["entry"]["node_attempt_ledger"]["predecessor"],
        )
    assert fixture["ledger_path"].read_bytes() == current_ledger_bytes


@pytest.mark.parametrize(
    "decision_id",
    [None, "bad id with spaces"],
    ids=["missing", "malformed"],
)
def test_wp12_dynamics_invalid_decision_id_refuses_before_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, decision_id: str | None
) -> None:
    fixture = _synthetic_wp12_dynamics_context(tmp_path, monkeypatch)
    prepared = MODULE.prepare_wp12_execution_manifest(
        "wp12_dynamics", fixture["target"], "wp12-synth-decision-id-0001", preflight_id=fixture["preflight_id"]
    )
    manifest_path = Path(prepared["path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["state"] = "OWNER_AUTHORIZED"
    manifest["execution_authorized"] = True
    manifest["do_not_execute"] = False
    manifest["owner_decision"] = {
        "status": "APPROVED",
        "approved_by": "Owner",
        "approved_at_utc": "2026-10-28T10:00:00Z",
        "reason": "Synthetic malformed Owner decision ID must refuse before reservation.",
    }
    if decision_id is not None:
        manifest["owner_decision"]["decision_id"] = decision_id
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    monkeypatch.setattr(MODULE, "_next_attempt", lambda *_args, **_kwargs: pytest.fail("must refuse before reservation"))
    with pytest.raises(MODULE.PolicyError, match="requires a valid decision_id"):
        MODULE.run_pytest(
            "fem_exploratory",
            fixture["target"],
            "dev-synthetic-wp12a-decision-id",
            worktree_id="wp12_dynamics",
            reason="Synthetic invalid Owner decision ID refusal test.",
            preflight_id=fixture["preflight_id"],
            execution_manifest=manifest_path,
        )
    assert not fixture["ledger_path"].exists()
    assert MODULE._sha256(fixture["predecessor_path"]) == fixture["predecessor_sha256"]


@pytest.mark.parametrize(
    ("execution_authorized", "do_not_execute"),
    [(False, True), (True, True), (False, False), (None, None)],
)
def test_wp12_dynamics_inconsistent_execution_flags_refuse_before_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, execution_authorized: bool | None, do_not_execute: bool | None
) -> None:
    fixture = _synthetic_wp12_dynamics_context(tmp_path, monkeypatch)
    prepared = MODULE.prepare_wp12_execution_manifest(
        "wp12_dynamics", fixture["target"], "wp12-synth-flags-0001", preflight_id=fixture["preflight_id"]
    )
    manifest_path = Path(prepared["path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "state": "OWNER_AUTHORIZED",
        "execution_authorized": execution_authorized,
        "do_not_execute": do_not_execute,
        "owner_decision": {
            "status": "APPROVED", "decision_id": "owner-synthetic-flags-0001", "approved_by": "Owner",
            "approved_at_utc": "2026-10-28T10:00:00Z", "reason": "Synthetic refusal of inconsistent execution flags.",
        },
    })
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(MODULE, "_next_attempt", lambda *_args, **_kwargs: pytest.fail("must refuse before reservation"))
    with pytest.raises(MODULE.PolicyError, match="inconsistent explicit authorization flags"):
        MODULE.run_pytest(
            "fem_exploratory", fixture["target"], "dev-synthetic-wp12a-flags", worktree_id="wp12_dynamics",
            reason="Synthetic refusal before reservation for inconsistent execution flags.",
            preflight_id=fixture["preflight_id"], execution_manifest=manifest_path,
        )
    assert not fixture["ledger_path"].exists()


def test_wp12_dynamics_cli_routes_preflight_ids_for_manifest_and_execution(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    target = WP12_DYNAMICS_NODEIDS[10]
    observed: dict[str, Any] = {}

    def prepare(worktree_id, nodeid, authorization_id, *, preflight_id=None):
        observed["prepare"] = (worktree_id, nodeid, authorization_id, preflight_id)
        return {"state": "PREPARED_NOT_AUTHORIZED", "path": "synthetic.json"}

    monkeypatch.setattr(MODULE, "prepare_wp12_execution_manifest", prepare)
    assert MODULE.main(
        [
            "prepare-manifest",
            "--worktree",
            "wp12_dynamics",
            "--target",
            target,
            "--authorization-id",
            "wp12-cli-synthetic-001",
            "--preflight-id",
            "pf-123456789abc",
        ]
    ) == 0
    assert observed["prepare"] == (
        "wp12_dynamics",
        target,
        "wp12-cli-synthetic-001",
        "pf-123456789abc",
    )
    capsys.readouterr()

    def run(scope, nodeid, series_id, **kwargs):
        observed["run"] = (scope, nodeid, series_id, kwargs)
        return {"state": "SYNTHETIC_LAUNCH_ACCEPTED"}, 0

    monkeypatch.setattr(MODULE, "run_pytest", run)
    assert MODULE.main(
        [
            "test",
            "--scope",
            "fem_exploratory",
            "--worktree",
            "wp12_dynamics",
            "--target",
            target,
            "--reason",
            "Synthetic CLI wiring contract; test runner is stubbed.",
            "--preflight-id",
            "pf-123456789abc",
            "--execution-manifest",
            "synthetic.json",
        ]
    ) == 0
    assert observed["run"][3]["preflight_id"] == "pf-123456789abc"
    assert observed["run"][3]["execution_manifest"] == Path("synthetic.json")


def test_wp12_dynamics_run_requires_preflight_before_attempt_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _synthetic_wp12_dynamics_context(tmp_path, monkeypatch)
    prepared = MODULE.prepare_wp12_execution_manifest(
        "wp12_dynamics", fixture["target"], "wp12-synth-gate-0001", preflight_id=fixture["preflight_id"]
    )
    manifest_path = Path(prepared["path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["state"] = "OWNER_AUTHORIZED"
    manifest["execution_authorized"] = True
    manifest["do_not_execute"] = False
    manifest["owner_decision"] = {
        "status": "APPROVED",
        "approved_by": "Owner",
        "approved_at_utc": "2026-10-28T10:00:00Z",
        "reason": "Synthetic Owner decision for missing-preflight refusal contract.",
    }
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    monkeypatch.setattr(MODULE, "_next_attempt", lambda *_args, **_kwargs: pytest.fail("must refuse before creating attempt"))
    with pytest.raises(MODULE.PolicyError, match="require a successful exact-node collect-only preflight"):
        MODULE.run_pytest(
            "fem_exploratory",
            fixture["target"],
            "dev-synthetic-wp12a-gate01",
            worktree_id="wp12_dynamics",
            reason="Synthetic missing collect-only receipt refusal contract.",
            execution_manifest=manifest_path,
        )
    assert not fixture["ledger_path"].exists()
    assert MODULE._sha256(fixture["predecessor_path"]) == fixture["predecessor_sha256"]


@pytest.mark.parametrize(
    "reason",
    ["registered worktree branch mismatch", "WP12 source fingerprint changed; inspected registration required"],
)
def test_wp12_dynamics_preflight_propagates_source_identity_refusals_before_launch(
    monkeypatch: pytest.MonkeyPatch, reason: str
) -> None:
    monkeypatch.setattr(MODULE, "resolve_targets", lambda *_args, **_kwargs: [WP12_DYNAMICS_PREFLIGHT_NODEID])
    monkeypatch.setattr(
        MODULE,
        "_registered_worktree",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(MODULE.PolicyError(reason)),
    )
    monkeypatch.setattr(
        MODULE,
        "run_supervised_command",
        lambda *_args, **_kwargs: pytest.fail("identity refusal must precede child collection"),
    )
    with pytest.raises(MODULE.PolicyError, match="branch mismatch|fingerprint changed"):
        MODULE.preflight_wp12_dynamics_pytest(
            WP12_DYNAMICS_PREFLIGHT_NODEID,
            policy={"worktrees": {}},
        )


@pytest.mark.parametrize(
    ("mutate_ledger_during_collection", "change_controller_during_collection", "mutate_predecessor_during_collection"),
    [(False, False, False), (True, False, False), (False, True, False), (False, False, True)],
)
def test_wp12_dynamics_preflight_detects_identity_changes_and_never_reserves(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutate_ledger_during_collection: bool,
    change_controller_during_collection: bool,
    mutate_predecessor_during_collection: bool,
) -> None:
    # This synthetic preflight tests provenance transitions, not host free-disk
    # availability. Keep the environment guard deterministic and side-effect free.
    monkeypatch.setattr(MODULE.shutil, "disk_usage", lambda _path: SimpleNamespace(free=2 * 1024**3))
    target = WP12_DYNAMICS_PREFLIGHT_NODEID
    source_root = tmp_path / "source" / "src"
    source_root.mkdir(parents=True)
    source_checkout = source_root.parent
    store = tmp_path / "evidence"
    (store / "locks").mkdir(parents=True)
    entry = {
        "worktree_id": "wp12_dynamics",
        "development_mandate_id": MODULE.WP12_OWNER_ENVELOPES["wp12_dynamics"]["development_mandate_id"],
        "allowed_nodeids": [target],
        "attempt_limit_per_nodeid": 10,
        "max_total_attempts": 130,
        "node_attempt_ledger": {
            "path": MODULE.WP12_DYNAMICS_LEDGER,
            "predecessor": {
                "path": "node-attempt-ledger.json",
                "sha256": "0" * 64,
                "mandate_id": MODULE.WP12_DYNAMICS_LEGACY_MANDATE_ID,
            },
        },
        "max_fem_cases_per_attempt": 1,
        "target_max_dofs": None,
        "evidence_root": str(store),
        "budgets": {
            "timeout_seconds": 300,
            "rss_soft_limit_mib": 128,
            "process_tree_limit": 4,
            "output_total_limit_mib": 2,
            "output_stream_limit_mib": 1,
            "temporary_limit_mib": 8,
            "archive_size_limit_mib": 8,
        },
    }
    predecessor_path = store / "node-attempt-ledger.json"
    predecessor_payload = {
        "schema": "qfsolver-development-node-ledger-v1",
        "mandate_id": MODULE.WP12_DYNAMICS_LEGACY_MANDATE_ID,
        "entries": {},
    }
    predecessor_path.write_text(json.dumps(predecessor_payload, sort_keys=True) + "\n", encoding="utf-8")
    entry["node_attempt_ledger"]["predecessor"]["sha256"] = MODULE._sha256(predecessor_path)
    ledger_path = store / MODULE.WP12_DYNAMICS_LEDGER
    identity = {
        "head": "a" * 40,
        "tree": "b" * 40,
        "branch": "codex/wp12-dynamic-harmonic-verification",
        "status_short": "",
    }
    fingerprint = "c" * 64
    selection = {
        "selected_dofs": 1,
        "selection_basis": "One synthetic registered DDL for collect-only validation",
        "timeout_seconds": 300,
    }
    policy = {
        "minimum_free_disk_mib": 1,
        "poll_interval_seconds": 0.01,
        "worktrees": {"wp12_dynamics": entry},
    }
    expected_origin = str((source_root / "solveur" / "__init__.py").resolve())

    monkeypatch.setattr(MODULE, "resolve_targets", lambda *_args, **_kwargs: [target])
    monkeypatch.setattr(
        MODULE,
        "_registered_worktree",
        lambda *_args, **_kwargs: (entry, source_checkout, source_root, identity, fingerprint),
    )
    monkeypatch.setattr(MODULE, "_wp12_active_registration", lambda *_args, **_kwargs: selection)
    monkeypatch.setattr(MODULE, "_run_root", lambda *_args, **_kwargs: store)
    monkeypatch.setattr(MODULE, "load_policy", lambda: policy)
    controller_provenances = iter(
        [
            {"fingerprint": "d" * 64},
            {"fingerprint": ("e" if change_controller_during_collection else "d") * 64},
        ]
    )
    monkeypatch.setattr(MODULE, "_controller_provenance", lambda: next(controller_provenances))
    monkeypatch.setattr(MODULE, "psutil", object())
    def supervised(command, *, output_dir, **_kwargs):
        assert "--collect-only" in command
        if mutate_ledger_during_collection:
            ledger_path.write_text('{"synthetic": true}\n', encoding="utf-8")
        if mutate_predecessor_during_collection:
            predecessor_path.write_text('{"synthetic": "historical edit"}\n', encoding="utf-8")
        (output_dir / "stdout.log").write_text(
            "QF_DEV_SOLVER_ORIGIN=" + expected_origin + "\n" + _wp12_dynamics_attestation(solver_origin=expected_origin),
            encoding="utf-8",
        )
        (output_dir / "stderr.log").write_text("", encoding="utf-8")
        return SimpleNamespace(
            status="PASS",
            return_code=0,
            elapsed_seconds=0.01,
            peak_rss_bytes=1024,
            peak_process_count=1,
            stdout_bytes=512,
            stderr_bytes=0,
        )

    monkeypatch.setattr(MODULE, "run_supervised_command", supervised)
    result = MODULE.preflight_wp12_dynamics_pytest(
        target,
        "pf-000000000003"
        if change_controller_during_collection
        else ("pf-000000000002" if mutate_ledger_during_collection else "pf-000000000001"),
        policy=policy,
    )
    expected_state = (
        "PREFLIGHT_CONTROLLER_CHANGED"
        if change_controller_during_collection
        else (
            "PREFLIGHT_LEDGER_CHANGED"
            if mutate_ledger_during_collection or mutate_predecessor_during_collection
            else "PREFLIGHT_PASS"
        )
    )
    assert result["state"] == expected_state
    assert result["attempt_reserved"] is False
    assert result["ledger_touched"] is (mutate_ledger_during_collection or mutate_predecessor_during_collection)
    assert result["bodies_executed"] is False
    receipt = json.loads(Path(result["receipt"]).read_text(encoding="utf-8"))
    receipt_path = Path(result["receipt"])
    checksum = json.loads((receipt_path.parent / "preflight.sha256.json").read_text(encoding="utf-8"))
    assert checksum["sha256"] == result["receipt_sha256"] == MODULE._sha256(receipt_path)
    assert receipt["attempt_reserved"] is False
    assert receipt["ledger_touched"] is (mutate_ledger_during_collection or mutate_predecessor_during_collection)
    assert receipt["bodies_executed"] is False
    assert receipt["attempt_ledger"]["touched"] is (
        mutate_ledger_during_collection or mutate_predecessor_during_collection
    )
    if not mutate_ledger_during_collection and not mutate_predecessor_during_collection:
        assert receipt["attempt_ledger"]["path"] == str(ledger_path)
        assert receipt["attempt_ledger"]["sha256_before"] is None
        assert receipt["attempt_ledger"]["sha256_after"] is None
        assert receipt["attempt_ledger"]["predecessor"] == entry["node_attempt_ledger"]["predecessor"]
        assert receipt["attempt_ledger"]["predecessor_sha256_before"] == MODULE._sha256(predecessor_path)
        assert receipt["attempt_ledger"]["predecessor_sha256_after"] == MODULE._sha256(predecessor_path)
    assert receipt["controller_provenance_after"]["fingerprint"] == (
        "e" if change_controller_during_collection else "d"
    ) * 64
