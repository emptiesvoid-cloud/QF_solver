"""Verify evidence bundle manifests and file fingerprints."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from solveur.io.manifest import is_relative_to, sha256


@dataclass(frozen=True)
class EvidenceFileCheck:
    """Verification outcome for one file declared by an evidence manifest."""

    role: str
    path: str
    status: str
    expected_size_bytes: int | None = None
    actual_size_bytes: int | None = None
    expected_sha256: str = ""
    actual_sha256: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "path": self.path,
            "status": self.status,
            "expected_size_bytes": self.expected_size_bytes,
            "actual_size_bytes": self.actual_size_bytes,
            "expected_sha256": self.expected_sha256,
            "actual_sha256": self.actual_sha256,
            "message": self.message,
        }


@dataclass(frozen=True)
class EvidenceVerificationReport:
    """Machine-readable verdict for an evidence bundle integrity check."""

    status: str
    manifest_path: str
    checked_file_count: int
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    files: tuple[EvidenceFileCheck, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "manifest_path": self.manifest_path,
            "checked_file_count": self.checked_file_count,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "files": [item.to_dict() for item in self.files],
        }


class EvidenceBundleVerifier:
    """Check that an evidence bundle still matches its manifest."""

    def verify(self, path: str | Path) -> EvidenceVerificationReport:
        manifest_path = _manifest_path(path)
        errors: list[str] = []
        warnings: list[str] = []
        if not manifest_path.exists():
            return _failed_report(manifest_path, [f"Missing evidence manifest: {manifest_path}"])
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return _failed_report(manifest_path, [f"Invalid evidence manifest JSON: {exc}"])

        files_data = manifest.get("files", [])
        manifest_version = manifest.get("manifest_schema_version")
        if manifest_version not in {1, 2}:
            errors.append("Unsupported or missing manifest_schema_version.")
        if manifest_version == 2:
            self._verify_v2_metadata(manifest, errors)
        if not isinstance(files_data, list):
            return _failed_report(manifest_path, errors + ["Manifest field 'files' must be a list."])
        expected_count = manifest.get("file_count")
        if expected_count != len(files_data):
            errors.append(f"Manifest file_count={expected_count!r} does not match files length={len(files_data)}.")

        file_checks = self._verify_files(manifest_path.parent, files_data, errors)
        status = "FAIL" if errors or any(item.status == "FAIL" for item in file_checks) else "PASS"
        return EvidenceVerificationReport(
            status=status,
            manifest_path=str(manifest_path),
            checked_file_count=len(file_checks),
            errors=tuple(errors),
            warnings=tuple(warnings),
            files=tuple(file_checks),
        )

    @staticmethod
    def _verify_v2_metadata(manifest: dict[str, Any], errors: list[str]) -> None:
        for field in ("source", "runtime", "locked_environments", "command_line", "input_sha256", "traceability"):
            if not manifest.get(field):
                errors.append(f"Manifest v2 field {field!r} is required.")

    @staticmethod
    def _verify_files(root: Path, files_data: list[Any], errors: list[str]) -> list[EvidenceFileCheck]:
        checks: list[EvidenceFileCheck] = []
        seen_paths: set[str] = set()
        for index, raw in enumerate(files_data):
            if not isinstance(raw, dict):
                errors.append(f"Manifest file entry {index} must be an object.")
                continue
            check = _verify_file_entry(root, raw)
            if check.path in seen_paths:
                check = EvidenceFileCheck(
                    role=check.role,
                    path=check.path,
                    status="FAIL",
                    expected_size_bytes=check.expected_size_bytes,
                    actual_size_bytes=check.actual_size_bytes,
                    expected_sha256=check.expected_sha256,
                    actual_sha256=check.actual_sha256,
                    message="Duplicate file path in manifest.",
                )
            seen_paths.add(check.path)
            if check.status == "FAIL":
                errors.append(f"{check.path}: {check.message}")
            checks.append(check)
        return checks


def _verify_file_entry(root: Path, raw: dict[str, Any]) -> EvidenceFileCheck:
    role = str(raw.get("role", ""))
    relative = str(raw.get("path", ""))
    expected_size = _optional_int(raw.get("size_bytes"))
    expected_hash = str(raw.get("sha256", "")).lower()
    base = root.resolve()
    candidate = (base / relative).resolve()
    if not is_relative_to(candidate, base):
        return EvidenceFileCheck(role=role, path=relative, status="FAIL", message="File path escapes evidence root.")
    if not candidate.is_file():
        return EvidenceFileCheck(
            role=role,
            path=relative,
            status="FAIL",
            expected_size_bytes=expected_size,
            expected_sha256=expected_hash,
            message="File is missing.",
        )
    actual_size = candidate.stat().st_size
    actual_hash = sha256(candidate)
    errors: list[str] = []
    if expected_size is None:
        errors.append("missing expected size")
    elif actual_size != expected_size:
        errors.append(f"size mismatch expected={expected_size} actual={actual_size}")
    if not expected_hash:
        errors.append("missing expected sha256")
    elif actual_hash != expected_hash:
        errors.append("sha256 mismatch")
    return EvidenceFileCheck(
        role=role,
        path=relative,
        status="FAIL" if errors else "PASS",
        expected_size_bytes=expected_size,
        actual_size_bytes=actual_size,
        expected_sha256=expected_hash,
        actual_sha256=actual_hash,
        message="; ".join(errors),
    )


def _manifest_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_dir():
        return candidate / "evidence_manifest.json"
    return candidate


def _failed_report(manifest_path: Path, errors: list[str]) -> EvidenceVerificationReport:
    return EvidenceVerificationReport(
        status="FAIL",
        manifest_path=str(manifest_path),
        checked_file_count=0,
        errors=tuple(errors),
        warnings=(),
        files=(),
    )


def _optional_int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
