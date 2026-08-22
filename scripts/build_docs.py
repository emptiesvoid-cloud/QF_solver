"""Build reproducible Markdown/PDF documentation evidence assets."""

from __future__ import annotations

import argparse
import json
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


class DocumentationEvidenceBuilder:
    """Orchestrate reproducible documentation evidence and qualification gates."""

    def __init__(self, project_root: str | Path = PROJECT_ROOT) -> None:
        self.root = Path(project_root).resolve()

    def build(self, *, profile: str) -> dict[str, object]:
        normalized = profile.lower()
        if normalized not in {"engineering", "qualification"}:
            raise ValueError("Documentation profile must be 'engineering' or 'qualification'.")
        if normalized == "qualification":
            self._enforce_qualification_gate()
        manifest = DocumentationAssetBuilder(self.root, profile=normalized).build()
        if manifest["qualification_campaign"]["status"] != "PASS":
            raise DocumentationBuildError("The executable qualification campaign did not pass.")
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

def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Regenerate reproducible FEM documentation evidence.")
    result.add_argument("--profile", choices=("engineering", "qualification"), default="engineering")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        manifest = DocumentationEvidenceBuilder().build(profile=args.profile)
    except DocumentationQualificationGateError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    except (DocumentationBuildError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        f"Documentation evidence {manifest['profile']} generated: "
        f"{len(manifest['files'])} artifacts, campaign={manifest['qualification_campaign']['status']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
