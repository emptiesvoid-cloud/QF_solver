"""Build reproducible documentation assets and the offline MkDocs site."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
for candidate in (SOURCE_ROOT, PROJECT_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from scripts.docs_assets import DocumentationAssetBuilder  # noqa: E402
from solveur.io.manifest import git_source_state  # noqa: E402


class DocumentationBuildError(RuntimeError):
    """Base error for an explicit documentation build refusal."""


class DocumentationQualificationGateError(DocumentationBuildError):
    """Raised when controlled publication prerequisites are incomplete."""


class DocumentationInfrastructureError(DocumentationBuildError):
    """Raised when optional site dependencies are unavailable."""


class DocumentationSiteBuilder:
    """Orchestrate evidence generation, qualification gates and MkDocs."""

    def __init__(self, project_root: str | Path = PROJECT_ROOT) -> None:
        self.root = Path(project_root).resolve()

    def build(self, *, profile: str, output: str | Path | None = None, assets_only: bool = False) -> dict[str, object]:
        normalized = profile.lower()
        if normalized not in {"engineering", "qualification"}:
            raise ValueError("Documentation profile must be 'engineering' or 'qualification'.")
        if normalized == "qualification":
            self._enforce_qualification_gate()
        manifest = DocumentationAssetBuilder(self.root, profile=normalized).build()
        if manifest["qualification_campaign"]["status"] != "PASS":
            raise DocumentationBuildError("The executable qualification campaign did not pass.")
        if not assets_only:
            self._build_mkdocs(output)
        return manifest

    def _enforce_qualification_gate(self) -> None:
        source = git_source_state(self.root)
        blockers = []
        if source["revision"] == "uncommitted":
            blockers.append("no committed source revision")
        if source["dirty"]:
            blockers.append("working tree is dirty")
        registry = json.loads((self.root / "docs" / "document_registry.json").read_text(encoding="utf-8"))
        accepted_states = {"controlled", "approved", "superseded"}
        draft = [item["id"] for item in registry["documents"] if item.get("status") not in accepted_states]
        if draft:
            blockers.append("documents without controlled review: " + ", ".join(draft))
        if blockers:
            raise DocumentationQualificationGateError("Qualification documentation build refused: " + "; ".join(blockers))

    def _build_mkdocs(self, output: str | Path | None) -> None:
        if importlib.util.find_spec("mkdocs") is None or importlib.util.find_spec("material") is None:
            raise DocumentationInfrastructureError("MkDocs Material is unavailable; install the optional dependency with 'python -m pip install -e .[docs]'.")
        command = [sys.executable, "-m", "mkdocs", "build", "--strict", "--clean"]
        if output is not None:
            command.extend(("--site-dir", str(Path(output).resolve())))
        completed = subprocess.run(command, cwd=self.root, text=True, check=False)
        if completed.returncode != 0:
            raise DocumentationBuildError(f"MkDocs strict build failed with exit code {completed.returncode}.")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Regenerate and build the offline FEM technical documentation.")
    result.add_argument("--profile", choices=("engineering", "qualification"), default="engineering")
    result.add_argument("--output", type=Path, default=None, help="Override the MkDocs site output directory.")
    result.add_argument("--assets-only", action="store_true", help="Regenerate evidence without building HTML.")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        manifest = DocumentationSiteBuilder().build(
            profile=args.profile,
            output=args.output,
            assets_only=args.assets_only,
        )
    except DocumentationQualificationGateError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    except DocumentationInfrastructureError as exc:
        print(str(exc), file=sys.stderr)
        return 5
    except (DocumentationBuildError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        f"Documentation {manifest['profile']} generated: "
        f"{len(manifest['files'])} artifacts, campaign={manifest['qualification_campaign']['status']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
