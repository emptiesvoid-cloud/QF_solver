"""Selected release validation is contract-driven and fails closed."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.verify_authorized_release_artifacts import (
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
