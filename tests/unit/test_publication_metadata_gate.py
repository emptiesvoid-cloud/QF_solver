"""Publication metadata must match the current release phase and evidence."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.check_publication_metadata import check_publication_metadata


ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.2.11"
TAG = "v0.2.11"
VERSION_DOI = "10.5281/zenodo.23214487"
RELEASE_DATE = "2026-10-07"
PUBLICATION_RECORD = ROOT / "qualification/0_2_11/publication_verification_0_2_11.json"
RELEASE_CONTRACT = ROOT / "qualification/0_2_11/authorized_selected_package_release_contract_afd2efa.json"


def _write_release_copy(root: Path, phase: str, *, doi: str | None = None, released: bool = False) -> None:
    root.mkdir(parents=True, exist_ok=True)
    citation_fields = [
        "cff-version: 1.2.0",
        f'message: "Use concept DOI 10.5281/zenodo.22697897. {"Published version DOI is available." if doi else "This metadata identifies version 0.2.11 without asserting a release date or version DOI."}"',
        "type: software",
        f'version: "{VERSION}"',
    ]
    if released:
        citation_fields.extend([f'date-released: "{RELEASE_DATE}"', f'doi: "{doi}"'])
    citation_fields.extend([
        'title: "QF Solver"',
        'license: "Apache-2.0"',
        'authors: [{family-names: "Farinazzo", given-names: "Quentin"}]',
    ])
    changelog_heading = f"## {VERSION} - Released" if released else f"## {VERSION} - Release candidate; not published"
    old_version = "0.2.10"
    files = {
        "pyproject.toml": f'[project]\nname = "qf-solver"\nversion = "{VERSION}"\n',
        "CITATION.cff": "\n".join(citation_fields) + "\n",
        "README.md": (
            f"The current QF Solver release is `{VERSION}`. Rotating_modal and Campbell remain EXPERIMENTAL.\n"
            "At 100 rad/s the high-frequency pair is ambiguous. GYRO-06 provides internal mesh-convergence "
            "evidence, not independent physical validation.\n"
            "Historical G03 remains FAIL_PRESERVED; the full-repository archive is not cleared and WP14 remains "
            "HOLD_NOT_PROMOTED.\n"
            + (f"Version DOI: https://doi.org/{doi}\n" if released else "")
        ),
        "CHANGELOG.md": (
            f"{changelog_heading}\n\n"
            + ("QF Solver 0.2.11 release.\n" if released else "This release candidate is not published.\n")
            + f"\n## {old_version} - Released\n"
        ),
        "docs/index.md": (
            f"**Current release documentation:** `{VERSION}`\n"
            + (f"Version DOI: https://doi.org/{doi}\n" if released else "")
            + ("This metadata identifies version 0.2.11 without asserting a publication date or version DOI.\n" if not released else "")
        ),
        "docs/getting-started/installation.md": (
            f"This guide applies to QF Solver `{VERSION}`.\n"
            + (f"The selected QF Solver `{VERSION}` wheel and sdist are the audited PyPI release artifacts.\n"
               if released else "Install after its release upload.\n")
        ),
        "docs/capabilities/index.md": (
            f"**Current release documentation:** `{VERSION}`\n"
            "rotating_modal and Campbell remain EXPERIMENTAL.\n"
        ),
        "docs/reference/feuille_de_route.md": (
            f"Version {VERSION} is the current documentation baseline.\n"
            + (f"QF Solver {VERSION} is the current published release.\n" if released else "")
        ),
        "CONTRIBUTING.md": (
            f"QF Solver `{VERSION}` (`{TAG}`) is the current published release.\n"
            if released else f"QF Solver `{old_version}` (`v{old_version}`) is the current published release.\n"
        ),
        "SUPPORT.md": (
            f"latest published release, currently `{VERSION}`\n"
            if released else f"latest published release, currently `{old_version}`\n"
        ),
        "SECURITY.md": (
            f"Current release: `{VERSION}` / `{TAG}`\n"
            if released else f"Current release: `{old_version}` / `v{old_version}`\n"
        ),
        "docs/whats-new/0.2.11.md": (
            "At 100 rad/s, the high-frequency pair remains ambiguous. GYRO-06 is internal mesh-convergence evidence, "
            "not independent physical validation. Both routes remain EXPERIMENTAL.\n"
        ),
        "docs/verification/0_2_11/README.md": (
            "The complete repository archive is not cleared. Historical G03 is FAIL_PRESERVED and WP14 is "
            "HOLD_NOT_PROMOTED.\n"
        ),
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _write_postpublication_evidence(root: Path, *, doi: str = VERSION_DOI) -> tuple[Path, Path]:
    wheel_name = f"qf_solver-{VERSION}-py3-none-any.whl"
    sdist_name = f"qf_solver-{VERSION}.tar.gz"
    manifest_name = f"qf_solver-{VERSION}-afd2efa4-SHA256SUMS.txt"
    wheel_hash = "a" * 64
    sdist_hash = "b" * 64
    manifest_hash = "c" * 64
    source_sha = "d" * 40
    contract = {
        "status": "OWNER_AUTHORIZED_SELECTED_PACKAGE_RELEASE",
        "package_version": VERSION,
        "release_tag": TAG,
        "source_sha": source_sha,
        "tag_target_sha": source_sha,
        "publication_scope": "SELECTED_DISTRIBUTION",
        "audited_artifacts": {
            "wheel": {"filename": wheel_name, "sha256": wheel_hash},
            "sdist": {"filename": sdist_name, "sha256": sdist_hash},
        },
        "sha256_manifest": {"filename": manifest_name, "sha256": manifest_hash},
        "g03_status": "FAIL_PRESERVED",
        "whole_repository_archive_cleared": False,
        "wp14_status": "HOLD_NOT_PROMOTED",
        "authorization": {
            "selected_package_publication_allowed": True,
            "github_release_allowed": True,
            "pypi_publication_allowed": True,
            "zenodo_selected_artifact_publication_allowed": True,
            "whole_repository_archive_cleared": False,
            "whole_repository_archive_publication_allowed": False,
        },
    }
    contract_path = root / "release-contract.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    all_files = [
        {"filename": wheel_name, "sha256": wheel_hash},
        {"filename": sdist_name, "sha256": sdist_hash},
        {"filename": manifest_name, "sha256": manifest_hash},
    ]
    record = {
        "schema_version": 1,
        "status": "PUBLICATION_VERIFIED",
        "publication_phase": "POST_PUBLICATION",
        "version": VERSION,
        "tag": TAG,
        "source_sha": source_sha,
        "version_doi": doi,
        "release_date": RELEASE_DATE,
        "concept_doi": "10.5281/zenodo.22697897",
        "tag_exists": True,
        "main_contains_tag_target": True,
        "tag_verification": {"target_sha": source_sha, "annotated": True},
        "github_release": {"published": True, "tag": TAG, "selected_assets": all_files},
        "pypi": {
            "published": True,
            "version": VERSION,
            "install_probe": "PASS",
            "files": all_files[:2],
        },
        "zenodo": {
            "published": True,
            "doi_resolves": True,
            "version_doi": doi,
            "concept_doi": "10.5281/zenodo.22697897",
            "release_date": RELEASE_DATE,
            "whole_repository_archive_present": False,
            "files": all_files,
        },
    }
    record_path = root / "publication-record.json"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    return contract_path, record_path


def test_current_postpublication_metadata_matches_public_evidence() -> None:
    failures = check_publication_metadata(
        ROOT,
        TAG,
        "POST_PUBLICATION",
        version_doi=VERSION_DOI,
        release_date=RELEASE_DATE,
        publication_record=PUBLICATION_RECORD,
        release_contract=RELEASE_CONTRACT,
    )
    assert failures == []


def test_prepublication_rejects_a_doi_or_date_claim(tmp_path: Path) -> None:
    _write_release_copy(tmp_path, "PRE_PUBLICATION", doi=VERSION_DOI, released=True)
    failures = check_publication_metadata(tmp_path, TAG, "PRE_PUBLICATION")
    assert "CITATION.cff version differs from the release" not in failures
    assert "PRE_PUBLICATION CITATION.cff must not assert a version DOI" in failures
    assert "PRE_PUBLICATION CITATION.cff must not assert a release date" in failures

    assert "PRE_PUBLICATION must not claim a version DOI" in check_publication_metadata(
        tmp_path, TAG, "PRE_PUBLICATION", version_doi=VERSION_DOI
    )


def test_postpublication_requires_doi_and_date_and_accepts_captured_values(tmp_path: Path) -> None:
    _write_release_copy(tmp_path, "POST_PUBLICATION", released=False)
    missing = check_publication_metadata(tmp_path, TAG, "POST_PUBLICATION")
    assert "POST_PUBLICATION needs a captured Zenodo version DOI" in missing
    assert "POST_PUBLICATION needs the factual ISO release date" in missing

    _write_release_copy(tmp_path, "POST_PUBLICATION", doi=VERSION_DOI, released=True)
    contract_path, record_path = _write_postpublication_evidence(tmp_path)
    assert check_publication_metadata(
        tmp_path,
        TAG,
        "POST_PUBLICATION",
        version_doi=VERSION_DOI,
        release_date=RELEASE_DATE,
        publication_record=record_path,
        release_contract=contract_path,
    ) == []


def test_postpublication_rejects_concept_doi_and_mismatched_citation(tmp_path: Path) -> None:
    _write_release_copy(tmp_path, "POST_PUBLICATION", doi=VERSION_DOI, released=True)
    contract_path, record_path = _write_postpublication_evidence(tmp_path)
    citation = tmp_path / "CITATION.cff"
    citation.write_text(citation.read_text(encoding="utf-8").replace(VERSION_DOI, "10.5281/zenodo.22697897"), encoding="utf-8")
    failures = check_publication_metadata(
        tmp_path,
        TAG,
        "POST_PUBLICATION",
        version_doi=VERSION_DOI,
        release_date=RELEASE_DATE,
        publication_record=record_path,
        release_contract=contract_path,
    )
    assert "CITATION.cff DOI differs from the captured version DOI" in failures

    concept_doi = check_publication_metadata(
        tmp_path,
        TAG,
        "POST_PUBLICATION",
        version_doi="10.5281/zenodo.22697897",
        release_date=RELEASE_DATE,
        publication_record=record_path,
        release_contract=contract_path,
    )
    assert "the project concept DOI cannot be used as a version DOI" in concept_doi


def test_postpublication_requires_all_channels_and_exact_public_hashes(tmp_path: Path) -> None:
    _write_release_copy(tmp_path, "POST_PUBLICATION", doi=VERSION_DOI, released=True)
    contract_path, record_path = _write_postpublication_evidence(tmp_path)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["zenodo"]["whole_repository_archive_present"] = True
    record["github_release"]["selected_assets"].pop()
    record_path.write_text(json.dumps(record), encoding="utf-8")
    failures = check_publication_metadata(
        tmp_path,
        TAG,
        "POST_PUBLICATION",
        version_doi=VERSION_DOI,
        release_date=RELEASE_DATE,
        publication_record=record_path,
        release_contract=contract_path,
    )
    assert "GitHub Release or its selected asset hashes do not match the contract" in failures
    assert "Zenodo record, DOI, selected files or archive boundary do not match the contract" in failures


def test_unstable_or_mismatched_tag_is_rejected() -> None:
    assert check_publication_metadata(ROOT, "../../v0.2.9", "PRE_PUBLICATION") == [
        "release tag must be a stable vMAJOR.MINOR.PATCH tag"
    ]
    assert "pyproject.toml version differs from release tag" in check_publication_metadata(
        ROOT, "v0.2.10", "PRE_PUBLICATION"
    )


def test_public_claim_gate_rejects_forbidden_rotordynamics_claims(tmp_path: Path) -> None:
    claims = (
        "This is qualified rotordynamics.",
        "This is a validated general critical-speed prediction.",
        "This is an industrial rotor solver.",
        "The whole-repository archive is cleared.",
    )
    for index, claim in enumerate(claims):
        root = tmp_path / str(index)
        _write_release_copy(root, "PRE_PUBLICATION")
        readme = root / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + claim + "\n", encoding="utf-8")
        failures = check_publication_metadata(root, TAG, "PRE_PUBLICATION")
        assert any("prohibited public claim detected" in failure for failure in failures), claim


def test_public_claim_gate_rejects_whole_archive_clearance_claim(tmp_path: Path) -> None:
    _write_release_copy(tmp_path, "PRE_PUBLICATION")
    readme = tmp_path / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "The whole-repository archive is cleared.\n", encoding="utf-8")
    failures = check_publication_metadata(tmp_path, TAG, "PRE_PUBLICATION")
    assert any("whole|full" in failure and "cleared" in failure for failure in failures)


def test_selected_release_scope_is_distinct_from_repository_archive_policy() -> None:
    from scripts.public_release_scope import publication_scope_decision

    assert publication_scope_decision("SELECTED_DISTRIBUTION", "FAIL_PRESERVED", False) == "ALLOWED"
    assert publication_scope_decision("WHOLE_REPOSITORY_ARCHIVE", "FAIL_PRESERVED", False) == "DENIED"
    assert publication_scope_decision("SELECTED_DISTRIBUTION", "FAIL_PRESERVED", True) == "DENIED"
    assert publication_scope_decision("SELECTED_DISTRIBUTION", "PASS", True) == "ALLOWED"
    assert publication_scope_decision("WHOLE_REPOSITORY_ARCHIVE", "PASS", True) == "ALLOWED"
    assert publication_scope_decision("WHOLE_REPOSITORY_ARCHIVE", "PASS", False) == "DENIED"
    assert publication_scope_decision("unknown", "FAIL_PRESERVED", False) == "DENIED"


def test_public_release_policy_keeps_channel_and_archive_clearance_separate() -> None:
    policy = " ".join((ROOT / "PUBLIC_RELEASE_POLICY.md").read_text(encoding="utf-8").split())
    assert "SELECTED_DISTRIBUTION_CLEARANCE" in policy
    assert "WHOLE_REPOSITORY_ARCHIVE_CLEARANCE" in policy
    assert "automatically generated `Source code (zip)`" in policy
    assert "version DOI absent" in policy
    assert "fails the `POST_PUBLICATION` gate" in policy


def test_pypi_workflow_uses_prepublication_phase_and_selected_artifact_gates() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/publish-pypi.yml").read_text(encoding="utf-8"))
    assert set(workflow["jobs"]) == {"preflight", "quality", "docs", "build", "publish"}
    assert workflow["jobs"]["publish"]["needs"] == ["preflight", "quality", "docs", "build"]
    assert "inputs.confirm_publish == true" in workflow["jobs"]["publish"]["if"]
    assert workflow["jobs"]["publish"]["environment"]["name"] == "pypi"
    preflight = str(workflow["jobs"]["preflight"])
    build = str(workflow["jobs"]["build"])
    assert "check_publication_metadata.py" in preflight
    assert "PRE_PUBLICATION" in preflight
    assert "git merge-base --is-ancestor" in preflight
    assert "prepare_wp14_recovered_evidence.py" in str(workflow["jobs"]["quality"])
    assert "mkdocs build --strict" in str(workflow["jobs"]["docs"])
    events = workflow.get("on", workflow.get(True))
    assert "default" not in events["workflow_dispatch"]["inputs"]["release_tag"]
    assert "default" not in events["workflow_dispatch"]["inputs"]["contract_path"]
    assert "publication_scope" in preflight
    assert "audit_wp14_public_scope.py" in build
    assert "verify_authorized_release_artifacts.py" in build
    assert "gh release download" in build
    assert "qf-package-candidate/dist" in build
    assert "python -m build" not in build
    assert "verify_public_package.py" not in build
    assert "PASS_AUTHORIZED_SELECTED_ARTIFACTS_ONLY" in build
