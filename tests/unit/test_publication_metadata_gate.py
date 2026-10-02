"""Publication must reject a tagged source with stale public-facing metadata."""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.check_publication_metadata import check_publication_metadata


ROOT = Path(__file__).resolve().parents[2]


def test_v0210_candidate_is_not_a_publishable_metadata_state() -> None:
    failures = check_publication_metadata(ROOT, "v0.2.10")
    assert "CITATION.cff does not identify this version" in failures
    assert "README.md release line does not identify this version" in failures
    assert "README.md still denies publication of this version" in failures
    assert "CHANGELOG.md has no released entry for this version" in failures
    assert "docs/index.md still advertises a different current release" in failures


def test_metadata_gate_rejects_nonstable_or_mismatched_tag() -> None:
    assert check_publication_metadata(ROOT, "../../v0.2.9") == [
        "release tag must be a stable vMAJOR.MINOR.PATCH tag"
    ]
    assert "pyproject.toml version differs from release tag" in check_publication_metadata(ROOT, "v0.2.9")
    assert "pyproject.toml version differs from release tag" in check_publication_metadata(ROOT, "v0.2.11")


def test_metadata_gate_accepts_consistent_release_copy(tmp_path: Path) -> None:
    version, tag = "0.2.10", "v0.2.10"
    files = {
        "pyproject.toml": f'[project]\nversion = "{version}"\n',
        "CITATION.cff": f'version: "{version}"\ndate-released: 2026-10-02\ndoi: "10.5281/zenodo.99999999"\n',
        "README.md": f"| Release line | `{version}` |\n",
        "CHANGELOG.md": f"## {version} - Released\n",
        "docs/index.md": f"**Current release:** [`{version}`]\n",
        "docs/getting-started/installation.md": f"QF Solver `{version}` is published on PyPI.\n",
        "docs/capabilities/index.md": f"**Current release:** `{version}` / `{tag}`\n",
        "docs/reference/feuille_de_route.md": f"QF Solver {version} is the current published release.\n",
        "CONTRIBUTING.md": f"QF Solver `{version}` (`{tag}`)\n",
        "SUPPORT.md": f"currently `{version}`\n",
        "SECURITY.md": f"Current release: `{version}` / `{tag}`\n",
    }
    for relative, content in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    assert check_publication_metadata(tmp_path, tag) == []
    (tmp_path / "README.md").write_text(
        f"| Release line | `{version}` |\nNo {version} package has been published.\n", encoding="utf-8"
    )
    assert "README.md still denies publication of this version" in check_publication_metadata(tmp_path, tag)
    (tmp_path / "README.md").write_text(
        f"| Release line | `{version}` |\nThe `{version}` candidate is not yet published.\n", encoding="utf-8"
    )
    assert "README.md still denies publication of this version" in check_publication_metadata(tmp_path, tag)


def test_pypi_workflow_publishes_only_audited_selected_archives() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/publish-pypi.yml").read_text(encoding="utf-8"))
    assert set(workflow["jobs"]) == {"preflight", "quality", "docs", "build", "publish"}
    assert workflow["jobs"]["publish"]["needs"] == ["preflight", "quality", "docs", "build"]
    assert "inputs.confirm_publish == true" in workflow["jobs"]["publish"]["if"]
    assert workflow["jobs"]["publish"]["environment"]["name"] == "pypi"
    preflight = str(workflow["jobs"]["preflight"])
    build = str(workflow["jobs"]["build"])
    assert "check_publication_metadata.py" in preflight
    assert "git merge-base --is-ancestor" in preflight
    assert "prepare_wp14_recovered_evidence.py" in str(workflow["jobs"]["quality"])
    assert "mkdocs build --strict" in str(workflow["jobs"]["docs"])
    events = workflow.get("on", workflow.get(True))
    assert "default" not in events["workflow_dispatch"]["inputs"]["release_tag"]
    assert "default" not in events["workflow_dispatch"]["inputs"]["contract_path"]
    assert "audit_wp14_public_scope.py" in build
    assert "verify_public_package.py" in build
    assert "qf-package-candidate/dist" in build
    assert "python -m build" not in build
