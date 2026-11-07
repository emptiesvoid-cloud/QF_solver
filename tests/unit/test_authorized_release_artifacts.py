"""Selected release validation is contract-driven and fails closed."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from scripts import verify_authorized_release_artifacts as release_verifier, verify_release_engineering_0212
from scripts.verify_authorized_release_artifacts import (
    _validate_candidate_audit,
    validate_owner_artifact_scope,
    verify_artifact_set,
)


ROOT = Path(__file__).resolve().parents[2]
AUTHORIZATION = {
    "selected_package_publication_allowed": True,
    "tag_creation_allowed": True,
    "pypi_publication_allowed": True,
    "github_release_allowed": True,
    "zenodo_selected_artifact_publication_allowed": True,
    "whole_repository_archive_cleared": False,
    "whole_repository_archive_publication_allowed": False,
    "ledger_update_allowed": False,
    "wp14_promotion_allowed": False,
    "numeric_maturity_promotion_allowed": False,
    "historical_result_reclassification_allowed": False,
    "certification_or_universal_validation_claims_allowed": False,
}


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fixture(tmp_path: Path, version: str = "0.2.11", schema_version: int = 2):
    dist = tmp_path / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    source = ("a" if version == "0.2.10" else "b") * 40
    wheel_name = f"qf_solver-{version}-py3-none-any.whl"
    sdist_name = f"qf_solver-{version}.tar.gz"
    manifest_name = f"qf_solver-{version}-test-SHA256SUMS.txt"
    wheel = b"exact selected wheel fixture"
    sdist = b"exact selected source fixture"
    (dist / wheel_name).write_bytes(wheel)
    (dist / sdist_name).write_bytes(sdist)
    manifest = f"{_sha(wheel)}  {wheel_name}\n{_sha(sdist)}  {sdist_name}\n".encode("ascii")
    (dist / manifest_name).write_bytes(manifest)
    artifacts = {
        "wheel": {"filename": wheel_name, "bytes": len(wheel), "sha256": _sha(wheel)},
        "sdist": {"filename": sdist_name, "bytes": len(sdist), "sha256": _sha(sdist)},
    }
    manifest_binding = {"filename": manifest_name, "bytes": len(manifest), "sha256": _sha(manifest)}
    record_id = f"QF-TEST-OWNER-{version}"
    gates = {f"QF0211_G0{number}": "PASS" if number > 6 else "INHERITED_PASS" for number in range(1, 9)}
    contract = {
        "schema_version": schema_version,
        "status": "OWNER_AUTHORIZED_SELECTED_PACKAGE_RELEASE",
        "package_version": version,
        "release_tag": f"v{version}",
        "source_sha": source,
        "tag_target_sha": source,
        "publication_scope": "SELECTED_DISTRIBUTION" if schema_version == 2 else None,
        "audited_artifacts": artifacts,
        "sha256_manifest": manifest_binding,
        "g03_status": "FAIL_PRESERVED",
        "whole_repository_archive_cleared": False,
        "whole_repository_archive_publication_allowed": False,
        "wp14_status": "HOLD_NOT_PROMOTED",
        "authorization": AUTHORIZATION.copy(),
    }
    owner = {
        "record_id": record_id,
        "decision": "AUTHORIZE_SELECTED_PACKAGE_RELEASE",
        "status": "OWNER_AUTHORIZED_SELECTED_PACKAGE_RELEASE",
        "version": version,
        "authorized_source_sha": source,
        "authorized_tag": f"v{version}",
        "authorized_tag_target_sha": source,
        "authorized_artifacts": {**artifacts, "manifest": manifest_binding},
        "authorized_wheel_sha256": artifacts["wheel"]["sha256"],
        "authorized_sdist_sha256": artifacts["sdist"]["sha256"],
        "authorized_manifest_sha256": manifest_binding["sha256"],
        "authorization": AUTHORIZATION.copy(),
        "selected_package_publication_allowed": True,
        "tag_creation_allowed": True,
        "pypi_publication_allowed": True,
        "github_release_allowed": True,
        "zenodo_selected_artifact_publication_allowed": True,
        "whole_repository_archive_cleared": False,
        "whole_repository_archive_publication_allowed": False,
        "wp14_promotion_allowed": False,
        "numeric_maturity_promotion_allowed": False,
        "historical_result_reclassification_allowed": False,
        "ledger_update_allowed": False,
        "certification_or_universal_validation_claims_allowed": False,
        "g03_status": "FAIL_PRESERVED",
        "wp14_status": "HOLD_NOT_PROMOTED",
        "preserved_gates": {
            "g03_status": "FAIL_PRESERVED",
            "whole_repository_archive_cleared": False,
            "wp14_status": "HOLD_NOT_PROMOTED",
        },
    }
    if version == "0.2.11":
        maturities = {
            "rotating_modal": "EXPERIMENTAL",
            "campbell": "EXPERIMENTAL",
            "campbell_100_rad_s_ambiguity": "PRESERVED",
            "gyro_06_evidence": "INTERNAL_MESH_CONVERGENCE_ONLY",
        }
        contract["maturities"] = maturities
        contract["release_gates"] = gates
        contract["publication_phase"] = {
            "current_phase": "PRE_PUBLICATION",
            "version_doi": "NOT_ASSIGNED",
            "release_date": "NOT_SET",
            "concept_doi": "10.5281/zenodo.22697897",
        }
        owner["publication_scope"] = "SELECTED_DISTRIBUTION"
        owner["publication_phase"] = contract["publication_phase"]
        owner["maturities"] = maturities
        owner["release_gates"] = gates
    return dist, contract, owner


def test_exact_selected_assets_and_manifest_are_accepted(tmp_path: Path) -> None:
    dist, contract, _ = _fixture(tmp_path)
    result = verify_artifact_set(dist, contract)
    assert result["status"] == "PASS_EXACT_RELEASE_ASSETS"
    assert len(result["files"]) == 3


def test_changed_bytes_missing_artifact_or_extra_archive_are_rejected(tmp_path: Path) -> None:
    dist, contract, _ = _fixture(tmp_path)
    (dist / "qf_solver-0.2.11.tar.gz").write_bytes(b"changed source bytes")
    with pytest.raises(ValueError, match="differs from the authorized contract"):
        verify_artifact_set(dist, contract)

    dist, contract, _ = _fixture(tmp_path / "missing")
    (dist / "qf_solver-0.2.11.tar.gz").unlink()
    with pytest.raises(ValueError, match="only the two selected packages"):
        verify_artifact_set(dist, contract)

    dist, contract, _ = _fixture(tmp_path / "extra")
    (dist / "repository-source.zip").write_bytes(b"uncleared repository archive")
    with pytest.raises(ValueError, match="only the two selected packages"):
        verify_artifact_set(dist, contract)


@pytest.mark.parametrize("version,schema_version", [("0.2.10", 1), ("0.2.11", 2)])
def test_versioned_owner_contracts_authorize_exact_selected_bytes(
    tmp_path: Path, version: str, schema_version: int,
) -> None:
    _, contract, owner = _fixture(tmp_path, version, schema_version)
    validate_owner_artifact_scope(contract, owner)


def test_historical_0210_contract_remains_readable_without_rewriting_it() -> None:
    contract_path = ROOT / "qualification/0_2_10/authorized_selected_package_release_contract_e535ff.json"
    owner_path = ROOT / "qualification/0_2_10/owner_publication_reauthorization_e535ff.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    validate_owner_artifact_scope(contract, owner)
    assert contract["source_sha"] == "e535ff63464ddd7d76c2898df25470350b5154f1"
    assert owner["authorized_source_sha"] == contract["source_sha"]


def test_actual_0211_owner_authorization_matches_the_frozen_candidate() -> None:
    owner_path = ROOT / "qualification/0_2_11/owner_publication_authorization_afd2efa4.json"
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    contract = {
        "schema_version": 2,
        "status": owner["status"],
        "package_version": owner["version"],
        "release_tag": owner["authorized_tag"],
        "source_sha": owner["authorized_source_sha"],
        "tag_target_sha": owner["authorized_tag_target_sha"],
        "publication_scope": owner["publication_scope"],
        "audited_artifacts": {kind: owner["authorized_artifacts"][kind] for kind in ("wheel", "sdist")},
        "sha256_manifest": owner["authorized_artifacts"]["manifest"],
        "authorization": owner["authorization"],
        "g03_status": owner["g03_status"],
        "whole_repository_archive_cleared": owner["whole_repository_archive_cleared"],
        "whole_repository_archive_publication_allowed": owner["whole_repository_archive_publication_allowed"],
        "wp14_status": owner["wp14_status"],
        "release_gates": owner["release_gates"],
        "maturities": owner["maturities"],
        "publication_phase": owner["publication_phase"],
    }
    validate_owner_artifact_scope(contract, owner)
    assert owner["authorized_source_sha"] == "afd2efa469a18e66581720ff4801f50de7d29eb4"
    assert owner["g03_status"] == "FAIL_PRESERVED"
    assert owner["whole_repository_archive_cleared"] is False
    assert owner["wp14_status"] == "HOLD_NOT_PROMOTED"


def test_actual_0211_release_contract_binds_only_the_authorized_distribution() -> None:
    contract_path = ROOT / "qualification/0_2_11/authorized_selected_package_release_contract_afd2efa.json"
    owner_path = ROOT / "qualification/0_2_11/owner_publication_authorization_afd2efa4.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    validate_owner_artifact_scope(contract, owner)
    assert contract["source_sha"] == "afd2efa469a18e66581720ff4801f50de7d29eb4"
    assert contract["publication_scope"] == "SELECTED_DISTRIBUTION"
    assert contract["g03_status"] == "FAIL_PRESERVED"
    assert contract["whole_repository_archive_cleared"] is False
    assert contract["wp14_status"] == "HOLD_NOT_PROMOTED"
    assert contract["authorization"]["whole_repository_archive_publication_allowed"] is False


def test_changed_source_version_or_hash_fails_closed(tmp_path: Path) -> None:
    _, contract, owner = _fixture(tmp_path)
    changed_source = {**contract, "source_sha": "c" * 40}
    with pytest.raises(ValueError, match="exact source accepted by the Owner"):
        validate_owner_artifact_scope(changed_source, owner)

    wrong_version = {**contract, "package_version": "0.2.12"}
    with pytest.raises(ValueError, match="exact source accepted by the Owner"):
        validate_owner_artifact_scope(wrong_version, owner)

    changed_artifacts = {**contract, "audited_artifacts": {
        **contract["audited_artifacts"],
        "wheel": {**contract["audited_artifacts"]["wheel"], "sha256": "3" * 64},
    }}
    with pytest.raises(ValueError, match="exact artifact accepted by the Owner"):
        validate_owner_artifact_scope(changed_artifacts, owner)


def test_unknown_contract_schema_owner_or_archive_scope_is_rejected(tmp_path: Path) -> None:
    _, contract, owner = _fixture(tmp_path)
    with pytest.raises(ValueError, match="Unknown selected-release contract schema"):
        validate_owner_artifact_scope({**contract, "schema_version": 99}, owner)

    with pytest.raises(ValueError, match="only an explicit selected-distribution scope"):
        validate_owner_artifact_scope({**contract, "publication_scope": "WHOLE_REPOSITORY_ARCHIVE"}, owner)

    g03_cleared = {**contract, "g03_status": "PASS", "whole_repository_archive_cleared": True}
    with pytest.raises(ValueError, match="release contract does not preserve G03"):
        validate_owner_artifact_scope(g03_cleared, owner)


def test_owner_permissions_cannot_promote_wp14_or_maturity(tmp_path: Path) -> None:
    _, contract, owner = _fixture(tmp_path)
    denied = {**owner, "authorization": {**owner["authorization"], "whole_repository_archive_publication_allowed": True}}
    with pytest.raises(ValueError, match="permissions broaden or weaken"):
        validate_owner_artifact_scope(contract, denied)

    promoted = {**owner, "wp14_status": "PASS"}
    with pytest.raises(ValueError, match="preserved release boundary"):
        validate_owner_artifact_scope(contract, promoted)


def test_explicit_pypi_only_channels_require_exactly_narrowed_permissions(tmp_path: Path) -> None:
    _, contract, owner = _fixture(tmp_path)
    pypi_only = {**AUTHORIZATION, "github_release_allowed": False,
                 "zenodo_selected_artifact_publication_allowed": False}
    contract = {**contract, "release_channels": ["pypi"], "authorization": pypi_only.copy()}
    owner = {
        **owner,
        "release_channels": ["pypi"],
        "authorization": pypi_only.copy(),
        "github_release_allowed": False,
        "zenodo_selected_artifact_publication_allowed": False,
    }
    validate_owner_artifact_scope(contract, owner)

    with pytest.raises(ValueError, match="permissions broaden or weaken"):
        validate_owner_artifact_scope(contract, {
            **owner,
            "authorization": AUTHORIZATION.copy(),
            "github_release_allowed": True,
            "zenodo_selected_artifact_publication_allowed": True,
        })

    with pytest.raises(ValueError, match="same release channels"):
        validate_owner_artifact_scope(contract, {**owner, "release_channels": []})


def test_explicit_pypi_only_contract_rejects_missing_channel_permissions(tmp_path: Path) -> None:
    _, contract, owner = _fixture(tmp_path)
    contract = {**contract, "release_channels": ["pypi"]}
    pypi_only = {**AUTHORIZATION, "github_release_allowed": False,
                 "zenodo_selected_artifact_publication_allowed": False}
    owner = {
        **owner,
        "release_channels": ["pypi"],
        "authorization": pypi_only,
        "github_release_allowed": False,
        "zenodo_selected_artifact_publication_allowed": False,
    }
    with pytest.raises(ValueError, match="release contract permissions"):
        validate_owner_artifact_scope(contract, owner)


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def _candidate_audit_repo(root: Path, *, annotated: bool = True, candidate_value=None):
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "tests@example.invalid")
    _git(root, "config", "user.name", "Release Validator Test")
    (root / "source.txt").write_text("source\n", encoding="utf-8")
    _git(root, "add", "source.txt")
    _git(root, "commit", "-m", "source")
    source_sha = _git(root, "rev-parse", "HEAD")
    if annotated:
        _git(root, "tag", "-a", "v0.2.12", "-m", "release", source_sha)
    else:
        _git(root, "tag", "v0.2.12", source_sha)
    tag_object = _git(root, "rev-parse", "refs/tags/v0.2.12")
    audit = {
        "record_id": "QF-TEST-CANDIDATE",
        "status": "READY_FOR_OWNER_RELEASE_AUTHORIZATION",
        "candidate": candidate_value if candidate_value is not None else {
            "package_version": "0.2.12",
            "package_source_sha": source_sha,
            "expected_tag": "v0.2.12",
            "expected_tag_target_sha": source_sha,
            "tag_created": True,
            "tag_object_sha": tag_object,
        },
        "release_gates": {"ready_for_owner_release_authorization": True},
    }
    audit_bytes = json.dumps(audit, sort_keys=True).encode("utf-8")
    audit_path = "candidate-audit.json"
    (root / audit_path).write_bytes(audit_bytes)
    _git(root, "add", audit_path)
    _git(root, "commit", "-m", "candidate audit")
    audit_commit = _git(root, "rev-parse", "HEAD")
    (root / "head.txt").write_text("head\n", encoding="utf-8")
    _git(root, "add", "head.txt")
    _git(root, "commit", "-m", "release contract")
    head = _git(root, "rev-parse", "HEAD")
    contract = {
        "release_channels": ["pypi"],
        "tag_object_sha": tag_object,
        "release_tag": "v0.2.12",
        "package_version": "0.2.12",
        "candidate_audit": {
            "path": audit_path,
            "commit_sha": audit_commit,
            "sha256": _sha(audit_bytes),
            "record_id": "QF-TEST-CANDIDATE",
        },
        "release_gates": {},
    }
    return source_sha, head, contract, tag_object


def test_pypi_only_candidate_audit_requires_exact_annotated_tag_before_ci_gate(tmp_path: Path) -> None:
    root = tmp_path / "annotated"
    source, head, contract, _ = _candidate_audit_repo(root)
    with pytest.raises(ValueError, match="successful exact-source Quality and Documentation CI"):
        _validate_candidate_audit(root, head, source, contract)

    lightweight = tmp_path / "lightweight"
    source, head, contract, _ = _candidate_audit_repo(lightweight, annotated=False)
    with pytest.raises(ValueError, match="exact annotated tag object"):
        _validate_candidate_audit(lightweight, head, source, contract)

    wrong_hash = tmp_path / "wrong-hash"
    source, head, contract, _ = _candidate_audit_repo(wrong_hash)
    contract["tag_object_sha"] = "0" * 40
    with pytest.raises(ValueError, match="exact annotated tag object"):
        _validate_candidate_audit(wrong_hash, head, source, contract)

    malformed = tmp_path / "malformed"
    source, head, contract, _ = _candidate_audit_repo(malformed, candidate_value=[])
    with pytest.raises(ValueError, match="candidate audit record is malformed"):
        _validate_candidate_audit(malformed, head, source, contract)


def test_tagged_engineering_ci_requires_matching_lineage_and_authenticated_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    source, _, contract, _ = _candidate_audit_repo(root)
    workflow = root / ".github/workflows/release-engineering-0212.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_bytes(b"name: test workflow\n")
    _git(root, "add", workflow.relative_to(root).as_posix())
    _git(root, "commit", "-m", "engineering workflow")
    workflow_sha = _git(root, "rev-parse", "HEAD")
    evidence = {
        "workflow_sha": workflow_sha,
        "workflow_sha256": _sha(workflow.read_bytes()),
        "scope_manifest_sha256": _sha(b"approved scope"),
        "run_id": 11,
        "run_attempt": 1,
        "artifact_id": 12,
        "artifact_sha256": _sha(b"approved archive"),
    }
    contract["tagged_engineering_ci"] = evidence
    calls = []
    responses = {
        "actions/runs/11": b"{}",
        "actions/runs/11/attempts/1/jobs?per_page=100": b'{"total_count": 0, "jobs": []}',
        "actions/artifacts/12": b'{"id": 12, "size_in_bytes": 16}',
        "actions/artifacts/12/zip": b"different archive",
    }

    def fetch(endpoint: str) -> bytes:
        calls.append(endpoint)
        return responses[endpoint]

    monkeypatch.setattr(release_verifier, "_github_release_evidence", fetch)
    validate = release_verifier._validate_tagged_engineering_ci
    with pytest.raises(ValueError, match="must bind the same tagged engineering run"):
        validate(root, workflow_sha, source, contract, {})
    with pytest.raises(ValueError, match="must belong to the release lineage"):
        validate(root, source, source, contract, {"tagged_engineering_ci": evidence})
    assert calls == []
    with pytest.raises(ValueError, match="differs from the exact authorized bytes"):
        validate(root, workflow_sha, source, contract, {"tagged_engineering_ci": evidence})
    assert calls == list(responses)

    checked = {}

    def verify_attestation(**kwargs):
        checked.update(kwargs)

    monkeypatch.setattr(verify_release_engineering_0212, "validate_release_engineering_attestation", verify_attestation)
    responses["actions/artifacts/12/zip"] = b"approved archive"
    validate(root, workflow_sha, source, contract, {"tagged_engineering_ci": evidence})
    assert checked["expected_workflow_sha"] == workflow_sha
    assert checked["expected_source_sha"] == source
    assert checked["expected_source_tree_sha"] == _git(root, "rev-parse", f"{source}^{{tree}}")
    assert checked["expected_scope_manifest_sha256"] == evidence["scope_manifest_sha256"]
    assert checked["artifact_bytes"] == b"approved archive"


def test_0211_owner_contract_requires_matching_scope_gates_and_prepublication_state(tmp_path: Path) -> None:
    _, contract, owner = _fixture(tmp_path)
    with pytest.raises(ValueError, match="gate decisions differ"):
        validate_owner_artifact_scope({**contract, "release_gates": None}, owner)

    with pytest.raises(ValueError, match="same selected scope"):
        validate_owner_artifact_scope(contract, {**owner, "publication_scope": "WHOLE_REPOSITORY_ARCHIVE"})

    fake_doi = {**owner, "publication_phase": {
        **owner["publication_phase"], "version_doi": "10.5281/zenodo.12345678"
    }}
    with pytest.raises(ValueError, match="no-DOI prepublication phase"):
        validate_owner_artifact_scope(contract, fake_doi)
