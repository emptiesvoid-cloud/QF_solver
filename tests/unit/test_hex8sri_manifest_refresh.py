"""Synthetic checks for the preparation-only HEX8-SRI manifest refresher."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import development_autonomous as controller
from scripts import refresh_hex8sri_case_manifests as refresh


SOURCE_HEAD = "a" * 40
SOURCE_FINGERPRINT = "b" * 64
OLD_HASH = "c" * 64
NEW_HASH = "d" * 64
SOURCE_FILE = "tests/verification/test_hex8_sri_convergence.py"
OLD_FINGERPRINT = controller._source_inventory_fingerprint({SOURCE_FILE: OLD_HASH})


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _synthetic_case_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    science_root = tmp_path / "science"
    science_root.mkdir()
    manifests = science_root / "registered_manifests_execution_gate"
    manifests.mkdir()
    common = {
        "schema": "synthetic-common-v1",
        "source_identity": {
            "branch": "research/hex8-sri-equilibrium",
            "source_commit": "7" * 40,
            "source_files_sha256": {SOURCE_FILE: OLD_HASH},
            "source_fingerprint_sha256": OLD_FINGERPRINT,
        },
        "controller_identity": {"branch": "old-controller", "head": "8" * 40},
        "preflight_status": "NOT_RUN",
        **refresh.EXPECTED_COMMON_PHYSICS,
        "criteria_status": "OWNER_FREEZE_REQUIRED_BEFORE_EXECUTION",
        "independent_3d_reference": {
            "environment": "backend absent from current interpreter; source/version/container not frozen",
            "proposed_family": "mixed displacement-pressure P2/P1 tetrahedral linear elasticity in an independent FEM code",
            "status": "NOT_IMPLEMENTED_OR_QUALIFIED",
            "uncertainty_target_relative": 0.005,
        },
        "timoshenko_reference": {
            "cowper_rectangular_factor_abs_tip_deflection_mm": {"0.3": 32.0612, "0.4999": 32.0699956},
            "shear_factor_5_over_6_abs_tip_deflection_mm": {"0.3": 32.0624, "0.4999": 32.0719952},
            "use": "scale/sign/trend only; not a 3-D error gate",
        },
        "retry_allowed": False,
        "status": "PREPARED_NOT_AUTHORIZED",
        "total_cases": 24,
        "attempts_per_case": 1,
        "campaign_id": controller.HEX8SRI_CONVERGENCE24_CAMPAIGN_ID,
        "formulations": ["hex8_standard", "sri_historical", "sri_corrected"],
        "meshes_xyz": [[4, 2, 2], [8, 4, 4], [16, 8, 8], [32, 16, 16]],
    }
    common_bytes = _json_bytes(common)
    (manifests / "common_problem.json").write_bytes(common_bytes)
    common_sha = hashlib.sha256(common_bytes).hexdigest()
    thread_environment = {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}

    for nodeid in controller._hex8sri_convergence24_nodeids():
        formulation, nu_token, mesh_token = controller._hex8sri_convergence24_case(nodeid)  # type: ignore[misc]
        case_id = f"{formulation}_nu_{nu_token}_{mesh_token}"
        budget = {
            **controller._hex8sri_convergence24_budget(nodeid),
            "attempts_per_nodeid": 1,
            "initial_campaign_max_attempts": 24,
            "blas_thread_environment": thread_environment,
            "budget_semantics": refresh.BUDGET_SEMANTICS,
        }
        manifest = {
            "schema": "qfsolver-hex8-sri-structural-case-v2",
            "campaign_id": controller.HEX8SRI_CONVERGENCE24_CAMPAIGN_ID,
            "case_id": case_id,
            "exact_nodeid": nodeid,
            "controller_registration_id": controller.HEX8SRI_CONVERGENCE24_WORKTREE_ID,
            "controller_campaign_scope_id": controller.HEX8SRI_CONVERGENCE24_WORKTREE_ID,
            "controller_identity_status": "FINAL_CONTROLLER_IDENTITY_BOUND",
            "controller_identity": {"branch": "old-controller", "head": "8" * 40},
            "controller_code_sha256": {"runner": OLD_HASH, "policy": OLD_HASH, "pytest_plugin": OLD_HASH},
            "source_fingerprint_sha256": OLD_FINGERPRINT,
            "science_source_commit": "7" * 40,
            "source_files_sha256": {SOURCE_FILE: OLD_HASH},
            "science_branch": "research/hex8-sri-equilibrium",
            "execution_state": "PREPARED_NOT_AUTHORIZED",
            "execution_authorized": False,
            "do_not_execute": True,
            "frozen_criteria": None,
            "preflight_status": "NOT_RUN",
            "formulation": refresh.EXPECTED_FORMULATIONS[formulation],
            "poisson_ratio": controller.HEX8SRI_CONVERGENCE24_NU_TOKENS[nu_token],
            "material": {
                "young_modulus_pa": 1.0e6,
                "poisson_ratio": controller.HEX8SRI_CONVERGENCE24_NU_TOKENS[nu_token],
            },
            "mesh": {
                **refresh._expected_case_mesh(mesh_token),
            },
            "boundary_conditions": refresh.EXPECTED_BOUNDARY_CONDITIONS,
            "loading": refresh.EXPECTED_CASE_LOADING,
            "oracle": refresh.EXPECTED_CASE_ORACLE,
            "proposed_criteria": refresh.EXPECTED_COMMON_PHYSICS["proposed_criteria"],
            "common_problem": {"path": "common_problem.json", "sha256": common_sha},
            "budgets": budget,
        }
        (manifests / f"manifest_{case_id}.json").write_bytes(_json_bytes(manifest))
    _write_inventory(manifests)
    return science_root, manifests, common_bytes


def _write_inventory(directory: Path) -> None:
    bindings = {}
    for path in directory.glob("manifest_*_*.json"):
        if path.name == "manifest_bindings.json":
            continue
        manifest = json.loads(path.read_text(encoding="utf-8"))
        bindings[manifest["exact_nodeid"]] = {
            "path": str(path), "case_id": manifest["case_id"],
            "raw_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "sha256": refresh._registration_sha256(manifest),
        }
    index = {"schema": "qfsolver-hex8sri-convergence24-manifest-bindings-v1", "bindings": bindings}
    (directory / "manifest_bindings.json").write_bytes(_json_bytes(index))
    paths = sorted([directory / "common_problem.json", directory / "manifest_bindings.json", *directory.glob("manifest_hex8_*.json"), *directory.glob("manifest_sri_*.json")])
    (directory / "SHA256SUMS.txt").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in paths), encoding="ascii")


def _mock_science_identity(monkeypatch: pytest.MonkeyPatch, science_root: Path) -> None:
    def fake_git(root: Path, *args: str) -> str:
        if args == ("rev-parse", "--show-toplevel"):
            return str(science_root)
        if args == ("branch", "--show-current"):
            return "research/hex8-sri-equilibrium"
        if args == ("rev-parse", "HEAD"):
            return SOURCE_HEAD
        if args == ("status", "--porcelain", "--untracked-files=all"):
            return ""
        raise AssertionError(args)

    monkeypatch.setattr(refresh, "_git", fake_git)
    monkeypatch.setattr(refresh.controller, "_worktree_source_fingerprint", lambda *_args: SOURCE_FINGERPRINT)
    monkeypatch.setattr(refresh, "_source_file_hashes", lambda *_args: {SOURCE_FILE: NEW_HASH})
    monkeypatch.setattr(refresh, "HISTORICAL_SOURCE_HEAD", "7" * 40)
    monkeypatch.setattr(refresh, "HISTORICAL_SOURCE_FINGERPRINT", OLD_FINGERPRINT)
    monkeypatch.setattr(refresh, "HISTORICAL_SUMS_SHA256", hashlib.sha256((science_root / "registered_manifests_execution_gate" / "SHA256SUMS.txt").read_bytes()).hexdigest())
    monkeypatch.setattr(controller, "_git_identity", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(controller, "_validate_hex8sri_registered_source_identity", lambda *_args: None)


def test_refresh_plan_rebinds_all_24_without_changing_case_physics_or_gates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    science_root, source_dir, _ = _synthetic_case_files(tmp_path)
    _mock_science_identity(monkeypatch, science_root)
    plan = refresh.build_refresh_plan(
        science_root,
        source_dir,
        science_root / "refreshed",
        expected_science_head=SOURCE_HEAD,
        expected_source_fingerprint=SOURCE_FINGERPRINT,
    )
    assert plan["manifest_count"] == 24
    assert len(plan["bindings"]) == 24
    assert plan["controller_identity_status"] == "PENDING"
    assert plan["source_fingerprint_sha256"] == SOURCE_FINGERPRINT

    target = controller._hex8sri_convergence24_nodeids()[0]
    old = json.loads((source_dir / "manifest_hex8_standard_nu_0p3_16x8x8.json").read_text(encoding="utf-8"))
    new = json.loads(plan["payloads"]["manifest_hex8_standard_nu_0p3_16x8x8.json"])
    for key in (
        "formulation",
        "material",
        "mesh",
        "boundary_conditions",
        "loading",
        "oracle",
        "proposed_criteria",
        "budgets",
    ):
        assert new[key] == old[key]
    assert new["criteria_contract"] == refresh.EXPECTED_CRITERIA_CONTRACT_PROPOSAL
    assert new["criteria_status"] == "OWNER_FREEZE_REQUIRED"
    assert new["exact_nodeid"] == target
    assert new["execution_authorized"] is False
    assert new["do_not_execute"] is True
    assert new["execution_state"] == "PREPARED_NOT_AUTHORIZED"
    assert new["frozen_criteria"] is None
    assert new["science_source_commit"] == SOURCE_HEAD
    assert new["source_files_sha256"] == {SOURCE_FILE: NEW_HASH}


def test_criteria_contract_keeps_campaign_gates_not_assessed_until_multimesh_oracle_exists() -> None:
    dispositions = refresh.EXPECTED_CRITERIA_CONTRACT_PROPOSAL["dispositions"]
    assert dispositions["free_residual_relative_max"] == {
        "classification": "CASE_GATE",
        "status": "OWNER_FREEZE_REQUIRED",
    }
    assert dispositions["last_two_levels_mean_UZ_relative_change_max"] == {
        "classification": "CAMPAIGN_GATE_DEFERRED",
        "status": "NOT_ASSESSED",
    }
    assert dispositions["finest_level_independent_3d_energy_relative_error_max"] == {
        "classification": "CAMPAIGN_GATE_DEFERRED",
        "status": "NOT_ASSESSED",
    }
    assert refresh.EXPECTED_COMMON_PHYSICS["proposed_criteria"] == controller.HEX8SRI_PROPOSED_CRITERIA


@pytest.mark.parametrize("mutation", ["missing", "extra", "duplicate", "bad_schema", "tampered"])
def test_typed_manifest_inventory_refuses_ambiguity_or_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    science_root, directory, _ = _synthetic_case_files(tmp_path)
    paths = sorted(directory.glob("manifest_hex8_*.json"))
    if mutation == "missing":
        paths[0].unlink()
    elif mutation == "extra":
        (directory / "manifest_unexpected.json").write_text("{}", encoding="utf-8")
    elif mutation in {"duplicate", "bad_schema"}:
        payload = json.loads(paths[0].read_text(encoding="utf-8"))
        if mutation == "duplicate":
            payload["exact_nodeid"] = json.loads(paths[1].read_text(encoding="utf-8"))["exact_nodeid"]
        else:
            payload["schema"] = "incorrect"
        paths[0].write_bytes(_json_bytes(payload))
        _write_inventory(directory)
    else:
        paths[0].write_text("{}", encoding="utf-8")
    monkeypatch.setattr(refresh, "HISTORICAL_SUMS_SHA256", hashlib.sha256((directory / "SHA256SUMS.txt").read_bytes()).hexdigest())
    with pytest.raises(ValueError):
        refresh._read_case_inventory(directory, controller._hex8sri_convergence24_nodeids())


def test_typed_manifest_inventory_accepts_24_and_excludes_bindings_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    science_root, directory, _ = _synthetic_case_files(tmp_path)
    _mock_science_identity(monkeypatch, science_root)
    assert len(refresh._read_case_inventory(directory, controller._hex8sri_convergence24_nodeids())) == 24
    assert (directory / "manifest_bindings.json").is_file()


def test_old_controller_identity_is_refused(tmp_path: Path) -> None:
    _, directory, _ = _synthetic_case_files(tmp_path)
    manifest = json.loads((directory / "manifest_hex8_standard_nu_0p3_4x2x2.json").read_text(encoding="utf-8"))
    current = {"identity": {"branch": "new-controller", "head": "9" * 40}, "sha256": {"runner": "a" * 64, "policy": "b" * 64, "pytest_plugin": "c" * 64}}
    with pytest.raises(controller.PolicyError, match="not bound to the final controller identity"):
        controller._verify_hex8sri_convergence24_controller_identity(manifest, current)


def test_versioned_case_manifest_is_bound_to_clean_controller_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    science_root, source, _ = _synthetic_case_files(tmp_path)
    target = "tests/verification/test_hex8_sri_convergence.py::test_convergence_case[hex8_standard-nu_0p3-4x2x2]"
    name = "manifest_hex8_standard_nu_0p3_4x2x2.json"
    head = "a" * 40
    campaign = science_root / "campaign"
    template = (Path("campaign") / "results" / "hex8sri-registry-v4" / "{controller_head}" / name).as_posix()
    directory = campaign / "results" / "hex8sri-registry-v4" / head
    directory.mkdir(parents=True)
    (directory / name).write_bytes((source / name).read_bytes())
    (directory / "common_problem.json").write_bytes((source / "common_problem.json").read_bytes())
    manifest = json.loads((directory / name).read_text(encoding="utf-8"))
    entry = controller.load_policy()["worktrees"][controller.HEX8SRI_CONVERGENCE24_WORKTREE_ID]
    entry["case_manifests"][target] = {"path": template, "sha256": refresh._registration_sha256(manifest)}
    entry["source_fingerprint_sha256"] = OLD_FINGERPRINT
    monkeypatch.setattr(controller, "_worktree_source_fingerprint", lambda *_args: OLD_FINGERPRINT)
    monkeypatch.setattr(controller, "_git_identity", lambda *_args, **_kwargs: {"head": head, "status_short": ""})
    path, _, _ = controller._hex8sri_convergence24_manifest(entry, science_root, target)
    assert path == (directory / name).resolve()
    assert path.is_relative_to(campaign.resolve())
    monkeypatch.setattr(controller, "_git_identity", lambda *_args, **_kwargs: {"head": head, "status_short": " M policy"})
    with pytest.raises(controller.PolicyError, match="requires a clean controller HEAD"):
        controller._hex8sri_convergence24_manifest(entry, science_root, target)
    monkeypatch.setattr(controller, "_git_identity", lambda *_args, **_kwargs: {"head": "b" * 40, "status_short": ""})
    with pytest.raises(controller.PolicyError, match="missing or outside"):
        controller._hex8sri_convergence24_manifest(entry, science_root, target)


def test_refresh_refuses_fingerprint_or_authorization_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    science_root, source_dir, _ = _synthetic_case_files(tmp_path)
    _mock_science_identity(monkeypatch, science_root)
    with pytest.raises(ValueError, match="live source fingerprint differs"):
        refresh.build_refresh_plan(
            science_root,
            source_dir,
            science_root / "wrong-fingerprint",
            expected_science_head=SOURCE_HEAD,
            expected_source_fingerprint="f" * 64,
        )

    path = source_dir / "manifest_hex8_standard_nu_0p3_16x8x8.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["execution_authorized"] = True
    path.write_bytes(_json_bytes(manifest))
    _write_inventory(source_dir)
    monkeypatch.setattr(refresh, "HISTORICAL_SUMS_SHA256", hashlib.sha256((source_dir / "SHA256SUMS.txt").read_bytes()).hexdigest())
    with pytest.raises(ValueError, match="source case is not execution-locked"):
        refresh.build_refresh_plan(
            science_root,
            source_dir,
            science_root / "authorized-input",
            expected_science_head=SOURCE_HEAD,
            expected_source_fingerprint=SOURCE_FINGERPRINT,
        )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("material", {"young_modulus_pa": 2.0e6, "poisson_ratio": 0.3}),
        ("loading", {**refresh.EXPECTED_CASE_LOADING, "resultant_force_n": [0.0, 0.0, -2.0]}),
        ("formulation", {**refresh.EXPECTED_FORMULATIONS["hex8_standard"], "operator": "altered"}),
    ],
)
def test_refresh_refuses_physical_drift_in_case_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    replacement: dict[str, object],
) -> None:
    science_root, source_dir, _ = _synthetic_case_files(tmp_path)
    _mock_science_identity(monkeypatch, science_root)
    path = source_dir / "manifest_hex8_standard_nu_0p3_16x8x8.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest[field] = replacement
    path.write_bytes(_json_bytes(manifest))
    _write_inventory(source_dir)
    monkeypatch.setattr(refresh, "HISTORICAL_SUMS_SHA256", hashlib.sha256((source_dir / "SHA256SUMS.txt").read_bytes()).hexdigest())

    with pytest.raises(ValueError, match="case identity differs"):
        refresh.build_refresh_plan(
            science_root,
            source_dir,
            science_root / "physical-drift",
            expected_science_head=SOURCE_HEAD,
            expected_source_fingerprint=SOURCE_FINGERPRINT,
        )


def test_refresh_refuses_common_problem_physics_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    science_root, source_dir, _ = _synthetic_case_files(tmp_path)
    _mock_science_identity(monkeypatch, science_root)
    path = source_dir / "common_problem.json"
    common = json.loads(path.read_text(encoding="utf-8"))
    common["model"]["young_modulus_pa"] = 2.0e6
    common_bytes = _json_bytes(common)
    path.write_bytes(common_bytes)
    common_sha = hashlib.sha256(common_bytes).hexdigest()
    for manifest_path in source_dir.glob("manifest_*.json"):
        if manifest_path.name in {"manifest_index.json", "manifest_bindings.json"}:
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["common_problem"]["sha256"] = common_sha
        manifest_path.write_bytes(_json_bytes(manifest))
    _write_inventory(source_dir)
    monkeypatch.setattr(refresh, "HISTORICAL_SUMS_SHA256", hashlib.sha256((source_dir / "SHA256SUMS.txt").read_bytes()).hexdigest())

    with pytest.raises(ValueError, match="common-problem model"):
        refresh.build_refresh_plan(
            science_root,
            source_dir,
            science_root / "common-physics-drift",
            expected_science_head=SOURCE_HEAD,
            expected_source_fingerprint=SOURCE_FINGERPRINT,
        )
