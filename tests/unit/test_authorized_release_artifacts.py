"""Release-asset verification accepts only exact Owner-authorized selected bytes."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.verify_authorized_release_artifacts import verify_artifact_set, validate_owner_artifact_scope


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    dist = tmp_path / "dist"
    dist.mkdir()
    wheel = b"audited wheel bytes"
    sdist = b"audited source bytes"
    wheel_name = "qf_solver-0.2.10-py3-none-any.whl"
    sdist_name = "qf_solver-0.2.10.tar.gz"
    manifest_name = "qf_solver-0.2.10-SHA256SUMS.txt"
    (dist / wheel_name).write_bytes(wheel)
    (dist / sdist_name).write_bytes(sdist)
    manifest = f"{_sha(wheel)}  {wheel_name}\n{_sha(sdist)}  {sdist_name}\n".encode("ascii")
    (dist / manifest_name).write_bytes(manifest)
    contract: dict[str, object] = {
        "audited_artifacts": {
            "wheel": {"filename": wheel_name, "bytes": len(wheel), "sha256": _sha(wheel)},
            "sdist": {"filename": sdist_name, "bytes": len(sdist), "sha256": _sha(sdist)},
        },
        "sha256_manifest": {
            "filename": manifest_name, "bytes": len(manifest), "sha256": _sha(manifest),
        },
    }
    return dist, contract


def test_only_exact_packages_and_checksum_manifest_are_accepted(tmp_path: Path) -> None:
    dist, contract = _fixture(tmp_path)
    result = verify_artifact_set(dist, contract)
    assert result["status"] == "PASS_EXACT_RELEASE_ASSETS"
    assert len(result["files"]) == 3


def test_changed_package_bytes_and_manifest_are_rejected(tmp_path: Path) -> None:
    dist, contract = _fixture(tmp_path)
    (dist / "qf_solver-0.2.10.tar.gz").write_bytes(b"changed bytes")
    with pytest.raises(ValueError, match="differs from the authorized contract"):
        verify_artifact_set(dist, contract)

    dist, contract = _fixture(tmp_path / "second")
    (dist / "qf_solver-0.2.10-SHA256SUMS.txt").write_text("0" * 64, encoding="ascii")
    with pytest.raises(ValueError, match="differs from the authorized contract"):
        verify_artifact_set(dist, contract)


def test_extra_assets_are_not_silently_published(tmp_path: Path) -> None:
    dist, contract = _fixture(tmp_path)
    (dist / "repository-source.zip").write_bytes(b"uncleared source archive")
    with pytest.raises(ValueError, match="only the two selected packages"):
        verify_artifact_set(dist, contract)


def test_owner_authorization_pins_exact_source_and_package_hashes() -> None:
    source = "b453265d5e61acd5f91cfc3aa236ee8b85344033"
    contract: dict[str, object] = {
        "source_sha": source,
        "tag_target_sha": source,
        "release_tag": "v0.2.10",
        "audited_artifacts": {
            "wheel": {"filename": "qf_solver-0.2.10-py3-none-any.whl", "bytes": 1509431, "sha256": "5c97d11cdc199512658ca3067b16beb7d72a2f6a183a171db5e921884709ca10"},
            "sdist": {"filename": "qf_solver-0.2.10.tar.gz", "bytes": 1114202, "sha256": "35ce10458e84425558396f1246b55e217734e0fa0189df242fbc2242bca9099d"},
        },
        "sha256_manifest": {"filename": "qf_solver-0.2.10-SHA256SUMS.txt", "bytes": 190, "sha256": "fbe097e7d785d9d0c63cc16f562a32166da3aca300fc0693ef1777ba3bd85d7a"},
    }
    owner = {
        "record_id": "QF-0210-OWNER-PUBLICATION-REAUTHORIZATION-B453265D",
        "decision": "AUTHORIZE_V0_2_10_PUBLICATION",
        "version": "0.2.10",
        "authorized_source_sha": source,
        "authorized_tag": "v0.2.10",
        "authorized_tag_target_sha": source,
        "authorized_wheel_sha256": "5c97d11cdc199512658ca3067b16beb7d72a2f6a183a171db5e921884709ca10",
        "authorized_sdist_sha256": "35ce10458e84425558396f1246b55e217734e0fa0189df242fbc2242bca9099d",
        "authorized_manifest_sha256": "fbe097e7d785d9d0c63cc16f562a32166da3aca300fc0693ef1777ba3bd85d7a",
        "authorized_artifacts": {
            "wheel": {"filename": "qf_solver-0.2.10-py3-none-any.whl", "bytes": 1509431, "sha256": "5c97d11cdc199512658ca3067b16beb7d72a2f6a183a171db5e921884709ca10"},
            "sdist": {"filename": "qf_solver-0.2.10.tar.gz", "bytes": 1114202, "sha256": "35ce10458e84425558396f1246b55e217734e0fa0189df242fbc2242bca9099d"},
            "manifest": {"filename": "qf_solver-0.2.10-SHA256SUMS.txt", "bytes": 190, "sha256": "fbe097e7d785d9d0c63cc16f562a32166da3aca300fc0693ef1777ba3bd85d7a"},
        },
        "authorization": {
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
        },
        "selected_package_publication_allowed": True,
        "tag_creation_allowed": True,
        "pypi_publication_allowed": True,
        "github_release_allowed": True,
        "zenodo_selected_artifact_publication_allowed": True,
        "g03_status": "FAIL_PRESERVED",
        "whole_repository_archive_cleared": False,
        "whole_repository_archive_publication_allowed": False,
        "wp14_status": "HOLD_NOT_PROMOTED",
        "wp14_promotion_allowed": False,
        "numeric_maturity_promotion_allowed": False,
        "historical_result_reclassification_allowed": False,
        "ledger_update_allowed": False,
        "certification_or_universal_validation_claims_allowed": False,
        "preserved_gates": {
            "g03_status": "FAIL_PRESERVED",
            "whole_repository_archive_cleared": False,
            "wp14_status": "HOLD_NOT_PROMOTED",
        },
    }
    validate_owner_artifact_scope(contract, owner)

    changed_source = {**contract, "source_sha": "c" * 40}
    with pytest.raises(ValueError, match="exact source accepted by the Owner"):
        validate_owner_artifact_scope(changed_source, owner)

    changed_artifacts = {**contract, "audited_artifacts": {
        **contract["audited_artifacts"],
        "wheel": {"filename": "qf_solver-0.2.10-py3-none-any.whl", "bytes": 1509431, "sha256": "3" * 64},
    }}
    with pytest.raises(ValueError, match="exact artifact accepted by the Owner"):
        validate_owner_artifact_scope(changed_artifacts, owner)

    changed_manifest = {**contract, "sha256_manifest": {
        **contract["sha256_manifest"], "sha256": "4" * 64,
    }}
    with pytest.raises(ValueError, match="exact artifact accepted by the Owner"):
        validate_owner_artifact_scope(changed_manifest, owner)

    changed_flat_hash = {**owner, "authorized_wheel_sha256": "4" * 64}
    with pytest.raises(ValueError, match="direct artifact hashes"):
        validate_owner_artifact_scope(contract, changed_flat_hash)

    revoked_authorization = {**owner, "authorization": {
        **owner["authorization"], "pypi_publication_allowed": False,
    }}
    with pytest.raises(ValueError, match="permissions broaden or weaken"):
        validate_owner_artifact_scope(contract, revoked_authorization)

    cleared_g03 = {**owner, "g03_status": "PASS"}
    with pytest.raises(ValueError, match="preserved release boundary"):
        validate_owner_artifact_scope(contract, cleared_g03)
