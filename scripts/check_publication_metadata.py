"""Fail closed if a tagged PyPI candidate still describes another release."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 compatibility.
    import tomli as tomllib


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


def check_publication_metadata(root: Path, tag: str) -> list[str]:
    """Check release-facing metadata; this is not a content or mechanics audit."""
    failures: list[str] = []
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        return ["release tag must be a stable vMAJOR.MINOR.PATCH tag"]
    version = tag[1:]
    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    except (OSError, KeyError, ValueError) as exc:
        return [f"project metadata is unreadable: {type(exc).__name__}"]
    if project.get("version") != version:
        failures.append("pyproject.toml version differs from release tag")

    contents: dict[str, str] = {}
    for relative in (*PUBLIC_PAGES, "CITATION.cff"):
        try:
            contents[relative] = (root / relative).read_text(encoding="utf-8")
        except OSError:
            failures.append(f"missing public metadata: {relative}")
    if failures:
        return failures

    citation = contents["CITATION.cff"]
    if not re.search(rf'(?m)^version:\s*["\']?{re.escape(version)}["\']?\s*$', citation):
        failures.append("CITATION.cff does not identify this version")
    if not re.search(r'(?m)^date-released:\s*\d{4}-\d{2}-\d{2}\s*$', citation):
        failures.append("CITATION.cff needs a release date")
    doi = re.search(r'(?m)^doi:\s*["\']?(10\.5281/zenodo\.\d+)["\']?\s*$', citation)
    if doi is None or doi.group(1) == "10.5281/zenodo.22697898":
        failures.append("CITATION.cff needs an assigned version DOI")

    readme = contents["README.md"]
    if f"| Release line | `{version}` |" not in readme:
        failures.append("README.md release line does not identify this version")
    if f"## {version} - Released" not in contents["CHANGELOG.md"]:
        failures.append("CHANGELOG.md has no released entry for this version")
    if f"**Current release:** [`{version}`]" not in contents["docs/index.md"]:
        failures.append("docs/index.md still advertises a different current release")
    if f"QF Solver `{version}` is published" not in contents["docs/getting-started/installation.md"]:
        failures.append("installation guide does not identify this published version")
    if f"**Current release:** `{version}` / `{tag}`" not in contents["docs/capabilities/index.md"]:
        failures.append("capability index still advertises a different release")
    if f"QF Solver {version} is the current published release." not in contents["docs/reference/feuille_de_route.md"]:
        failures.append("public roadmap still advertises a different release")
    if f"QF Solver `{version}` (`{tag}`)" not in contents["CONTRIBUTING.md"]:
        failures.append("contribution guide still advertises a different release")
    if f"currently `{version}`" not in contents["SUPPORT.md"]:
        failures.append("support guide still advertises a different release")
    if f"Current release: `{version}` / `{tag}`" not in contents["SECURITY.md"]:
        failures.append("security policy still advertises a different release")

    for relative, body in contents.items():
        denial_before_version = re.search(
            rf"(?is)(?:no|not|pas de|non)\s+[^.\n]{{0,90}}{re.escape(version)}[^.\n]{{0,90}}(?:publish|publi)",
            body,
        )
        denial_after_version = re.search(
            rf"(?is){re.escape(version)}[^.]{{0,160}}\b(?:not\s+(?:yet\s+)?(?:a\s+)?(?:tagged|published|publishable)|no\s+[^.]{{0,30}}(?:publication|version\s+DOI))\b",
            body,
        )
        if denial_before_version or denial_after_version:
            failures.append(f"{relative} still denies publication of this version")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    failures = check_publication_metadata(args.root, args.tag)
    for failure in failures:
        print(f"PUBLICATION METADATA FAIL: {failure}", file=sys.stderr)
    if failures:
        return 1
    print(f"PUBLICATION METADATA: PASS for {args.tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
