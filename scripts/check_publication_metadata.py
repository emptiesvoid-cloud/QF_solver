"""Validate release-facing metadata in explicit pre- or post-publication phase."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 compatibility.
    import tomli as tomllib


CONCEPT_DOI = "10.5281/zenodo.22697897"
VERSION_RE = re.compile(r"\d+\.\d+\.\d+\Z")
DOI_RE = re.compile(r"10\.5281/zenodo\.(\d+)\Z")
PUBLIC_PAGES = (
    "README.md",
    "CHANGELOG.md",
    "docs/index.md",
    "docs/getting-started/installation.md",
    "docs/capabilities/index.md",
    "docs/reference/feuille_de_route.md",
    "CONTRIBUTING.md",
    "SUPPORT.md",
    "SECURITY.md",
)
ROTATING_PAGES = (
    "docs/whats-new/0.2.11.md",
    "docs/verification/0_2_11/README.md",
)
FORBIDDEN_PUBLIC_CLAIMS = (
    re.compile(r"\bqualified\s+rotordynamics\b", re.IGNORECASE),
    re.compile(r"\bvalidated\s+general\s+critical[- ]speed(?:\s+prediction)?\b", re.IGNORECASE),
    re.compile(r"\bindustrial\s+(?:rotor|rotordynamics)\s+solver\b", re.IGNORECASE),
    re.compile(r"\bgeneral\s+rotordynamics\s+(?:solver|support)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:whole|full)[- ]repository(?:\s+source)?\s+archive\s+(?:is\s+)?(?:cleared|audited|qualified)\b",
        re.IGNORECASE,
    ),
)


def _field(text: str, name: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(name)}:\s*(.*?)\s*$", text)
    if match is None:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"\"", "'"}:
        value = value[1:-1]
    return value


def _released_versions(changelog: str) -> list[str]:
    return re.findall(r"(?mi)^##\s+(\d+\.\d+\.\d+)\s+-\s+Released\b", changelog)


def _require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def _phase_inputs(
    phase: str, version_doi: str | None, release_date: str | None, failures: list[str]
) -> tuple[str | None, str | None]:
    phase = phase.upper()
    if phase not in {"PRE_PUBLICATION", "POST_PUBLICATION"}:
        failures.append("publication phase must be PRE_PUBLICATION or POST_PUBLICATION")
        return None, None
    if phase == "PRE_PUBLICATION":
        _require(version_doi is None, "PRE_PUBLICATION must not claim a version DOI", failures)
        _require(release_date is None, "PRE_PUBLICATION must not claim a release date", failures)
        return None, None

    valid_doi = version_doi is not None and DOI_RE.fullmatch(version_doi) is not None
    _require(valid_doi, "POST_PUBLICATION needs a captured Zenodo version DOI", failures)
    valid_date = False
    if release_date is not None:
        try:
            valid_date = date.fromisoformat(release_date).isoformat() == release_date
        except ValueError:
            valid_date = False
    _require(valid_date, "POST_PUBLICATION needs the factual ISO release date", failures)
    if version_doi == CONCEPT_DOI:
        failures.append("the project concept DOI cannot be used as a version DOI")
    return version_doi, release_date


def _check_citation(
    citation: str,
    version: str,
    phase: str,
    version_doi: str | None,
    release_date: str | None,
    failures: list[str],
) -> None:
    _require(_field(citation, "version") == version, "CITATION.cff version differs from the release", failures)
    _require(CONCEPT_DOI in citation, "CITATION.cff must preserve the project concept DOI", failures)
    citation_doi = _field(citation, "doi")
    citation_date = _field(citation, "date-released")
    if phase == "PRE_PUBLICATION":
        _require(citation_doi is None, "PRE_PUBLICATION CITATION.cff must not assert a version DOI", failures)
        _require(citation_date is None, "PRE_PUBLICATION CITATION.cff must not assert a release date", failures)
        _require(
            "without asserting a release date or version doi" in citation.lower(),
            "PRE_PUBLICATION CITATION.cff must state that release metadata is not yet asserted",
            failures,
        )
        return

    _require(citation_doi == version_doi, "CITATION.cff DOI differs from the captured version DOI", failures)
    _require(citation_date == release_date, "CITATION.cff date differs from the factual release date", failures)


def _check_current_publication_claims(contents: dict[str, str], version: str, tag: str, phase: str,
                                     failures: list[str]) -> None:
    readme = contents["README.md"]
    changelog = contents["CHANGELOG.md"]
    index = contents["docs/index.md"]
    install = " ".join(contents["docs/getting-started/installation.md"].split())
    capabilities = contents["docs/capabilities/index.md"]
    roadmap = " ".join(contents["docs/reference/feuille_de_route.md"].split())

    _require(
        re.search(rf"(?i)current QF Solver release is\s+`{re.escape(version)}`", readme) is not None,
        "README.md must identify the requested current release semantically",
        failures,
    )
    _require(
        re.search(rf"(?mi)^\*\*Current release documentation:\*\*\s*`{re.escape(version)}`", index)
        is not None,
        "docs/index.md must identify the current release documentation version",
        failures,
    )
    _require(
        f"This guide applies to QF Solver `{version}`" in install,
        "installation guide must identify the applicable package version",
        failures,
    )
    _require(
        re.search(rf"(?mi)^\*\*Current release documentation:\*\*\s*`{re.escape(version)}`", capabilities)
        is not None,
        "capability index must identify the current release documentation version",
        failures,
    )
    _require(
        re.search(
            rf"(?i)(?:version\s+|qf solver\s+){re.escape(version)}\s+is the current documentation baseline",
            roadmap,
        )
        is not None,
        "public roadmap must identify the current documentation baseline",
        failures,
    )

    if phase == "PRE_PUBLICATION":
        heading = re.search(rf"(?mi)^##\s+{re.escape(version)}\s+-\s+([^\n]+)", changelog)
        _require(heading is not None, "CHANGELOG.md must contain this version's entry", failures)
        if heading is not None:
            _require(
                "candidate" in heading.group(1).lower() and "not published" in heading.group(1).lower(),
                "PRE_PUBLICATION changelog entry must remain explicitly unpublished",
                failures,
            )
        released = _released_versions(changelog)
        _require(bool(released), "CHANGELOG.md must retain an explicit latest published entry", failures)
        latest_published = released[0] if released else None
        if latest_published is not None:
            _require(
                f"QF Solver `{latest_published}` (`v{latest_published}`) is the current published release"
                in contents["CONTRIBUTING.md"],
                "CONTRIBUTING.md must distinguish the latest published release from the candidate",
                failures,
            )
            _require(
                f"currently `{latest_published}`" in contents["SUPPORT.md"],
                "SUPPORT.md must retain the actual latest published release during prepublication",
                failures,
            )
            _require(
                f"Current release: `{latest_published}` / `v{latest_published}`" in contents["SECURITY.md"],
                "SECURITY.md must retain the actual latest published release during prepublication",
                failures,
            )
    else:
        _require(
            re.search(rf"(?mi)^##\s+{re.escape(version)}\s+-\s+Released\b", changelog) is not None,
            "POST_PUBLICATION changelog must mark this version released",
            failures,
        )
        _require(
            f"selected QF Solver `{version}` wheel and sdist are the audited PyPI release artifacts" in install,
            "POST_PUBLICATION installation guide must identify the audited release artifacts",
            failures,
        )
        _require(
            f"QF Solver {version} is the current published release" in roadmap,
            "POST_PUBLICATION roadmap must identify the current published release",
            failures,
        )
        _require(
            f"QF Solver `{version}` (`{tag}`) is the current published release" in contents["CONTRIBUTING.md"],
            "POST_PUBLICATION CONTRIBUTING.md must identify the current published release",
            failures,
        )
        _require(
            f"currently `{version}`" in contents["SUPPORT.md"],
            "POST_PUBLICATION SUPPORT.md must identify the current published release",
            failures,
        )
        _require(
            f"Current release: `{version}` / `{tag}`" in contents["SECURITY.md"],
            "POST_PUBLICATION SECURITY.md must identify the current published release",
            failures,
        )
        _require(
            not re.search(r"(?i)without asserting (?:a )?publication date or version DOI", readme + index),
            "POST_PUBLICATION public pages must not retain prepublication citation wording",
            failures,
        )


def _check_bounded_claims(contents: dict[str, str], failures: list[str]) -> None:
    combined = "\n".join(contents.values())
    for pattern in FORBIDDEN_PUBLIC_CLAIMS:
        _require(pattern.search(combined) is None, f"prohibited public claim detected: {pattern.pattern}", failures)

    readme = " ".join(contents["README.md"].lower().split())
    whats_new = " ".join(contents.get("docs/whats-new/0.2.11.md", "").lower().split())
    summary = " ".join(contents.get("docs/verification/0_2_11/README.md", "").lower().split())
    capabilities = contents["docs/capabilities/index.md"].lower()
    _require("rotating_modal" in readme and "experimental" in readme, "README must retain experimental rotating-modal status", failures)
    _require("campbell" in readme and "experimental" in readme, "README must retain experimental Campbell status", failures)
    _require("100 rad/s" in readme and "ambig" in readme, "README must retain the 100 rad/s ambiguity", failures)
    _require("internal mesh-convergence evidence" in readme, "README must limit GYRO-06 to internal mesh convergence", failures)
    _require("not independent physical validation" in readme,
             "README must state that internal convergence is not physical validation", failures)
    _require("100 rad/s" in whats_new and "ambiguous" in whats_new, "What's New must preserve the 100 rad/s ambiguity", failures)
    _require("internal mesh-convergence evidence" in whats_new, "What's New must identify GYRO-06 as internal convergence evidence", failures)
    _require("not independent physical validation" in whats_new,
             "What's New must state that GYRO-06 is not physical validation", failures)
    _require("experimental" in capabilities and "rotating_modal" in capabilities and "campbell" in capabilities,
             "capability index must retain experimental rotating-analysis maturity", failures)
    _require("fail_preserved" in summary and "hold_not_promoted" in summary,
             "V&V summary must preserve historical G03 and WP14 statuses", failures)
    _require(re.search(r"(?i)(?:whole|full|complete)[ -]repository archive is not cleared", summary) is not None,
             "V&V summary must state that the whole-repository archive is not cleared", failures)


def _artifact_hashes(items: object) -> dict[str, str] | None:
    if not isinstance(items, list):
        return None
    result: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            return None
        filename, sha256 = item.get("filename"), item.get("sha256")
        if (
            not isinstance(filename, str)
            or not isinstance(sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", sha256)
            or filename in result
        ):
            return None
        result[filename] = sha256
    return result


def _check_postpublication_record(
    record_path: Path | None,
    contract_path: Path | None,
    version: str,
    tag: str,
    version_doi: str | None,
    release_date: str | None,
    failures: list[str],
) -> None:
    if record_path is None or contract_path is None:
        failures.append("POST_PUBLICATION requires a captured publication record and selected-release contract")
        return
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"POST_PUBLICATION evidence is unreadable: {type(exc).__name__}")
        return

    _require(record.get("schema_version") == 1, "POST_PUBLICATION record schema is unsupported", failures)
    _require(record.get("status") == "PUBLICATION_VERIFIED", "POST_PUBLICATION record is not verified", failures)
    _require(record.get("publication_phase") == "POST_PUBLICATION", "publication record phase is not POST_PUBLICATION", failures)
    _require(record.get("version") == version, "publication record version differs from the release", failures)
    _require(record.get("tag") == tag, "publication record tag differs from the release", failures)
    _require(record.get("version_doi") == version_doi, "publication record DOI differs from the captured DOI", failures)
    _require(record.get("release_date") == release_date, "publication record date differs from the factual release date", failures)
    _require(record.get("concept_doi") == CONCEPT_DOI, "publication record must preserve the project concept DOI", failures)
    _require(record.get("tag_exists") is True, "POST_PUBLICATION must confirm the immutable tag exists", failures)
    _require(record.get("main_contains_tag_target") is True, "POST_PUBLICATION must confirm the tag target is in main history", failures)

    expected_source = contract.get("source_sha")
    _require(
        contract.get("status") == "OWNER_AUTHORIZED_SELECTED_PACKAGE_RELEASE"
        and contract.get("package_version") == version
        and contract.get("release_tag") == tag
        and contract.get("tag_target_sha") == expected_source
        and contract.get("publication_scope") == "SELECTED_DISTRIBUTION"
        and record.get("source_sha") == expected_source,
        "publication record and selected-release contract do not bind the same exact source",
        failures,
    )
    authorization = contract.get("authorization", {})
    _require(
        isinstance(authorization, dict)
        and authorization.get("selected_package_publication_allowed") is True
        and authorization.get("github_release_allowed") is True
        and authorization.get("pypi_publication_allowed") is True
        and authorization.get("zenodo_selected_artifact_publication_allowed") is True
        and authorization.get("whole_repository_archive_cleared") is False
        and authorization.get("whole_repository_archive_publication_allowed") is False,
        "postpublication contract does not preserve selected-only authorization",
        failures,
    )
    _require(
        contract.get("g03_status") == "FAIL_PRESERVED"
        and contract.get("whole_repository_archive_cleared") is False
        and contract.get("wp14_status") == "HOLD_NOT_PROMOTED",
        "postpublication contract must preserve G03, whole-repository and WP14 statuses",
        failures,
    )

    contract_artifacts = contract.get("audited_artifacts")
    manifest = contract.get("sha256_manifest")
    if not isinstance(contract_artifacts, dict) or not isinstance(manifest, dict):
        failures.append("selected-release contract has no exact artifact bindings")
        return
    expected_all = {
        contract_artifacts.get(kind, {}).get("filename"): contract_artifacts.get(kind, {}).get("sha256")
        for kind in ("wheel", "sdist")
    }
    expected_all[manifest.get("filename")] = manifest.get("sha256")
    if any(
        not isinstance(name, str) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
        for name, digest in expected_all.items()
    ):
        failures.append("selected-release contract artifact bindings are malformed")
        return
    expected_pypi = {name: digest for name, digest in expected_all.items() if name.endswith((".whl", ".tar.gz"))}

    tag_record = record.get("tag_verification", {})
    _require(
        isinstance(tag_record, dict)
        and tag_record.get("target_sha") == expected_source
        and tag_record.get("annotated") is True,
        "POST_PUBLICATION tag target does not match the audited source",
        failures,
    )
    github = record.get("github_release", {})
    _require(
        isinstance(github, dict)
        and github.get("published") is True
        and github.get("tag") == tag
        and _artifact_hashes(github.get("selected_assets")) == expected_all,
        "GitHub Release or its selected asset hashes do not match the contract",
        failures,
    )
    pypi = record.get("pypi", {})
    _require(
        isinstance(pypi, dict)
        and pypi.get("published") is True
        and pypi.get("version") == version
        and pypi.get("install_probe") == "PASS"
        and _artifact_hashes(pypi.get("files")) == expected_pypi,
        "PyPI publication, install probe or selected file hashes do not match the contract",
        failures,
    )
    zenodo = record.get("zenodo", {})
    _require(
        isinstance(zenodo, dict)
        and zenodo.get("published") is True
        and zenodo.get("doi_resolves") is True
        and zenodo.get("version_doi") == version_doi
        and zenodo.get("concept_doi") == CONCEPT_DOI
        and zenodo.get("release_date") == release_date
        and zenodo.get("whole_repository_archive_present") is False
        and _artifact_hashes(zenodo.get("files")) == expected_all,
        "Zenodo record, DOI, selected files or archive boundary do not match the contract",
        failures,
    )


def check_publication_metadata(
    root: Path,
    tag: str,
    phase: str = "PRE_PUBLICATION",
    version_doi: str | None = None,
    release_date: str | None = None,
    publication_record: Path | None = None,
    release_contract: Path | None = None,
) -> list[str]:
    """Validate release metadata against the explicitly selected publication phase."""
    failures: list[str] = []
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        return ["release tag must be a stable vMAJOR.MINOR.PATCH tag"]
    version = tag[1:]
    if not VERSION_RE.fullmatch(version):
        return ["release version must be a stable MAJOR.MINOR.PATCH version"]
    phase = phase.upper()
    version_doi, release_date = _phase_inputs(phase, version_doi, release_date, failures)
    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    except (OSError, KeyError, ValueError) as exc:
        return [f"project metadata is unreadable: {type(exc).__name__}"]
    _require(project.get("version") == version, "pyproject.toml version differs from release tag", failures)

    required_paths = (*PUBLIC_PAGES, "CITATION.cff")
    contents: dict[str, str] = {}
    for relative in required_paths:
        try:
            contents[relative] = (root / relative).read_text(encoding="utf-8")
        except OSError:
            failures.append(f"missing public metadata: {relative}")
    if version == "0.2.11":
        for relative in ROTATING_PAGES:
            try:
                contents[relative] = (root / relative).read_text(encoding="utf-8")
            except OSError:
                failures.append(f"missing bounded rotating-analysis evidence page: {relative}")
    if any(path not in contents for path in required_paths):
        return failures

    citation = contents["CITATION.cff"]
    _check_citation(citation, version, phase, version_doi, release_date, failures)
    _check_current_publication_claims(contents, version, tag, phase, failures)
    if version == "0.2.11":
        _check_bounded_claims(contents, failures)
    if phase == "POST_PUBLICATION":
        _check_postpublication_record(
            publication_record, release_contract, version, tag, version_doi, release_date, failures
        )
    _require(
        phase in {"PRE_PUBLICATION", "POST_PUBLICATION"},
        "publication phase is invalid",
        failures,
    )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--tag", required=True)
    parser.add_argument("--phase", choices=("PRE_PUBLICATION", "POST_PUBLICATION"), required=True)
    parser.add_argument("--version-doi")
    parser.add_argument("--release-date")
    parser.add_argument("--publication-record", type=Path)
    parser.add_argument("--release-contract", type=Path)
    args = parser.parse_args()
    failures = check_publication_metadata(
        args.root,
        args.tag,
        args.phase,
        version_doi=args.version_doi,
        release_date=args.release_date,
        publication_record=args.publication_record,
        release_contract=args.release_contract,
    )
    for failure in failures:
        print(f"PUBLICATION METADATA FAIL: {failure}", file=sys.stderr)
    if failures:
        return 1
    print(f"PUBLICATION METADATA: PASS for {args.tag} in {args.phase}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
