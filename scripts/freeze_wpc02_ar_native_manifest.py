"""Bind an external WP-C02-AR run manifest to an already committed source tree."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
from io import BytesIO
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED = ROOT / "qualification/0_2_12/wp_c02_ar_native_execution_manifest.json"


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _aggregate(files: dict[str, str]) -> str:
    records = "\n".join(f"{path}  {files[path]}" for path in sorted(files))
    return _sha256(records.encode("utf-8"))


def _assert_external(path: Path) -> None:
    try:
        relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return
    if _git("ls-tree", "--name-only", "HEAD", "--", relative):
        raise RuntimeError("The execution manifest must remain outside the committed source tree.")


def bind_manifest(
    seed_path: Path,
    output_path: Path,
    *,
    campaign: str = "WP-C02-AR native one-shot campaign N03 M4/M5",
    campaign_id: str = "wpc02-ar-native-n03-m4m5-20261023-01",
    archive_relative_path: str = "qualification/0_2_12/wpc02_ar_native_campaign_n03_20261023_01",
) -> dict[str, Any]:
    _assert_external(output_path)
    manifest = json.loads(seed_path.read_text(encoding="utf-8"))
    head = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", "HEAD^{tree}")
    source_map = manifest.get("source_files_sha256")
    if not isinstance(source_map, dict) or not source_map:
        raise RuntimeError("Seed manifest has no source path set.")

    paths = list(source_map)
    for path in paths:
        item = PurePosixPath(path)
        if item.is_absolute() or ".." in item.parts or "\\" in path:
            raise RuntimeError(f"Invalid repository-relative POSIX source path: {path}.")

    archive = subprocess.run(
        ["git", "archive", "--format=tar", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout
    with tarfile.open(fileobj=BytesIO(archive), mode="r:") as tar:
        committed = {}
        for path in paths:
            member = tar.getmember(path)
            stream = tar.extractfile(member)
            if stream is None:
                raise RuntimeError(f"Commit path is not a regular file: {path}.")
            committed[path] = _sha256(stream.read())

    for path, expected in committed.items():
        working = ROOT / path
        if not working.is_file() or _sha256(working.read_bytes()) != expected:
            raise RuntimeError(f"Working source differs from exact HEAD content: {path}.")

    manifest["source_files_sha256"] = committed
    manifest["source_file_count"] = len(committed)
    manifest["source_set_sha256"] = _aggregate(committed)
    manifest["schema"] = "wpc02-ar-native-execution-manifest-v3"
    manifest["campaign"] = campaign
    manifest["campaign_id"] = campaign_id
    manifest["identity"] = {
        "git_head": head,
        "git_tree_oid": tree,
        "branch": _git("branch", "--show-current") or "detached",
        "source_commit_only": True,
        "manifest_external_to_tree": True,
    }
    manifest["execution"]["archive_relative_path"] = archive_relative_path
    manifest["execution"]["manifest_external_path"] = str(output_path.resolve())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--campaign", default="WP-C02-AR native one-shot campaign N03 M4/M5")
    parser.add_argument("--campaign-id", default="wpc02-ar-native-n03-m4m5-20261023-01")
    parser.add_argument(
        "--archive-relative-path",
        default="qualification/0_2_12/wpc02_ar_native_campaign_n03_20261023_01",
    )
    args = parser.parse_args()
    manifest = bind_manifest(
        args.seed,
        args.output,
        campaign=args.campaign,
        campaign_id=args.campaign_id,
        archive_relative_path=args.archive_relative_path,
    )
    print(json.dumps({
        "campaign_id": manifest["campaign_id"],
        "git_head": manifest["identity"]["git_head"],
        "git_tree_oid": manifest["identity"]["git_tree_oid"],
        "source_file_count": manifest["source_file_count"],
        "source_set_sha256": manifest["source_set_sha256"],
        "manifest_sha256": _sha256(args.output.read_bytes()),
        "manifest_path": str(args.output.resolve()),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
