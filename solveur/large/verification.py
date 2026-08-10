"""Post-run verification for large-scale qualification evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from solveur.io.evidence_verifier import EvidenceBundleVerifier


@dataclass(frozen=True)
class LargeQualificationVerification:
    """Machine-readable verification report for a large qualification directory."""

    status: str
    root: str
    checks: tuple[dict[str, Any], ...]
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "root": self.root,
            "checks": list(self.checks),
            "details": self.details,
        }


def verify_large_qualification(
    path: str | Path,
    *,
    target_dofs: int = 1_000_000,
    max_solver_residual: float = 1.0e-6,
) -> LargeQualificationVerification:
    """Verify that a large qualification run has complete, consistent evidence."""
    root = Path(path)
    benchmark_dir = root / "benchmark" if (root / "benchmark").is_dir() else root
    checks: list[dict[str, Any]] = []
    summary = _read_json(root / "large_qualification_summary.json", checks, "qualification_summary")
    benchmark = _read_json(benchmark_dir / "benchmark_large.json", checks, "benchmark")
    solver_summary = _read_json(benchmark_dir / "summary.json", checks, "solver_summary")
    audit = _read_json(benchmark_dir / "audit_large.json", checks, "audit_large")
    root_runtime = _read_json(root / "runtime_environment.json", checks, "runtime_root")
    benchmark_runtime = _read_json(benchmark_dir / "runtime_environment.json", checks, "runtime_benchmark")
    _check_manifests(root, benchmark_dir, checks)
    _check_counts(summary, benchmark, target_dofs, checks)
    _check_statuses(summary, benchmark, audit, checks)
    _check_displacements(benchmark_dir, benchmark, checks)
    _check_artifacts(benchmark, checks)
    _check_runtime(root_runtime, benchmark_runtime, benchmark, checks)
    _check_residual(benchmark, solver_summary, max_solver_residual, checks)
    _check_readiness(summary, checks)
    status = "FAIL" if any(item["status"] == "FAIL" for item in checks) else "PASS"
    details = {
        "target_dofs": int(target_dofs),
        "benchmark_dir": str(benchmark_dir),
        "max_solver_residual": float(max_solver_residual),
        "summary_status": summary.get("status"),
        "benchmark_status": benchmark.get("status"),
        "ndof": benchmark.get("ndof", summary.get("actual_dofs")),
        "python": benchmark_runtime.get("python", {}).get("version"),
    }
    return LargeQualificationVerification(status=status, root=str(root), checks=tuple(checks), details=details)


def save_large_verification_report(
    report: LargeQualificationVerification,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Path]:
    """Write JSON and/or Markdown reports for a large qualification verification."""
    paths: dict[str, Path] = {}
    if json_path is not None:
        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        paths["json"] = target
    if markdown_path is not None:
        target = Path(markdown_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_markdown(report), encoding="utf-8")
        paths["markdown"] = target
    return paths


def _read_json(path: Path, checks: list[dict[str, Any]], label: str) -> dict[str, Any]:
    if not path.is_file():
        checks.append(_check(f"{label.upper()}-EXISTS", False, f"missing {path}"))
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        checks.append(_check(f"{label.upper()}-JSON", False, str(exc)))
        return {}
    checks.append(_check(f"{label.upper()}-EXISTS", True, str(path)))
    return data if isinstance(data, dict) else {}


def _check_manifests(root: Path, benchmark_dir: Path, checks: list[dict[str, Any]]) -> None:
    verifier = EvidenceBundleVerifier()
    for label, directory in (("QUALIFICATION", root), ("BENCHMARK", benchmark_dir)):
        report = verifier.verify(directory)
        checks.append(_check(f"{label}-MANIFEST", report.status == "PASS", report.manifest_path))


def _check_counts(
    summary: dict[str, Any],
    benchmark: dict[str, Any],
    target_dofs: int,
    checks: list[dict[str, Any]],
) -> None:
    actual = int(benchmark.get("ndof", summary.get("actual_dofs", 0)) or 0)
    checks.append(_check("TARGET-DOFS", actual >= target_dofs, f"actual={actual}, target={target_dofs}"))
    for key in ("node_count", "element_count"):
        left = int(summary.get(key, 0) or 0)
        right = int(benchmark.get(key, left) or 0)
        checks.append(_check(f"{key.upper()}-CONSISTENT", left == right and left > 0, f"summary={left}, benchmark={right}"))


def _check_statuses(
    summary: dict[str, Any],
    benchmark: dict[str, Any],
    audit: dict[str, Any],
    checks: list[dict[str, Any]],
) -> None:
    checks.append(_check("QUALIFICATION-STATUS", summary.get("status") == "PASS", str(summary.get("status"))))
    checks.append(_check("BENCHMARK-STATUS", benchmark.get("status") == "PASS", str(benchmark.get("status"))))
    checks.append(_check("AUDIT-STATUS", benchmark.get("audit_status") == "PASS", str(benchmark.get("audit_status"))))
    checks.append(_check("AUDIT-FILE-STATUS", audit.get("status") == "PASS", str(audit.get("status"))))


def _check_displacements(benchmark_dir: Path, benchmark: dict[str, Any], checks: list[dict[str, Any]]) -> None:
    output_files = dict(benchmark.get("output_files", {}))
    displacement = Path(str(output_files.get("displacements", "")))
    if not displacement.is_absolute():
        displacement = benchmark_dir / displacement
    exists = displacement.is_file()
    checks.append(_check("DISPLACEMENTS-FILE", exists, str(displacement)))
    if not exists:
        return
    shape = _displacement_shape(displacement)
    expected_nodes = int(benchmark.get("node_count", 0) or 0)
    checks.append(_check("DISPLACEMENTS-SHAPE", shape == (expected_nodes, 3), f"shape={shape}, expected=({expected_nodes}, 3)"))


def _displacement_shape(path: Path) -> tuple[int, int] | None:
    suffix = path.suffix.lower()
    if suffix == ".bin":
        metadata_path = path.with_name("displacements_metadata.json")
        if not metadata_path.is_file():
            return None
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            shape = tuple(int(value) for value in metadata["shape"])
            flat_size = int(metadata["flat_size"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None
        if len(shape) != 2 or flat_size != shape[0] * shape[1]:
            return None
        expected_bytes = flat_size * 8
        if metadata.get("dtype") != "float64" or path.stat().st_size != expected_bytes:
            return None
        return shape  # type: ignore[return-value]
    if suffix in {".h5", ".hdf5"}:
        import h5py

        with h5py.File(path, "r") as handle:
            return tuple(handle["displacements"].shape)  # type: ignore[return-value]
    if suffix == ".npz":
        import numpy as np

        with np.load(path, allow_pickle=False) as data:
            return tuple(data["displacements"].shape)  # type: ignore[return-value]
    return None


def _check_artifacts(benchmark: dict[str, Any], checks: list[dict[str, Any]]) -> None:
    policy = dict(benchmark.get("artifact_policy", {}))
    checks.append(
        _check("FILE-BACKED-DISPLACEMENTS", bool(policy.get("file_backed_displacements")), str(policy.get("displacement_output", "")))
    )
    checks.append(
        _check(
            "NO-MONOLITHIC-DISPLACEMENT-JSON",
            not bool(policy.get("monolithic_displacements_in_json")),
            f"offenders={policy.get('offending_json_files', [])}",
        )
    )
    fingerprint = dict(benchmark.get("input_fingerprint", {}))
    checks.append(_check("INPUT-FINGERPRINT", bool(fingerprint.get("sha256")), str(fingerprint.get("path", ""))))
    checks.append(
        _check("RUNTIME-PATH-RECORDED", bool(benchmark.get("runtime_environment")), str(benchmark.get("runtime_environment", "")))
    )


def _check_runtime(
    root_runtime: dict[str, Any],
    benchmark_runtime: dict[str, Any],
    benchmark: dict[str, Any],
    checks: list[dict[str, Any]],
) -> None:
    root_solver = dict(root_runtime.get("solver", {}))
    benchmark_solver = dict(benchmark_runtime.get("solver", {}))
    checks.append(_check("RUNTIME-ROOT-SOLVER", bool(root_solver.get("version")), str(root_solver.get("version", ""))))
    checks.append(
        _check("RUNTIME-BENCHMARK-SOLVER", bool(benchmark_solver.get("version")), str(benchmark_solver.get("version", "")))
    )
    checks.append(
        _check(
            "RUNTIME-BENCHMARK-PYTHON",
            bool(benchmark_runtime.get("python", {}).get("version")),
            str(benchmark_runtime.get("python", {}).get("executable", "")),
        )
    )
    packages = dict(benchmark_runtime.get("packages", {}))
    required = ["numpy", "scipy"]
    displacement = str(dict(benchmark.get("output_files", {})).get("displacements", ""))
    if Path(displacement).suffix.lower() in {".h5", ".hdf5"}:
        required.append("h5py")
    if str(benchmark.get("backend", "")).lower() == "petsc":
        required.extend(["mpi4py", "petsc4py"])
    for name in required:
        record = dict(packages.get(name, {}))
        detail = str(record.get("version", ""))
        checks.append(_check(f"RUNTIME-PACKAGE-{name.upper()}", bool(record.get("available")), detail))


def _check_residual(
    benchmark: dict[str, Any],
    solver_summary: dict[str, Any],
    max_solver_residual: float,
    checks: list[dict[str, Any]],
) -> None:
    solver = dict(benchmark.get("solver", solver_summary.get("solver", {})))
    residual = solver.get("residual_norm")
    try:
        residual_value = float(residual)
    except (TypeError, ValueError):
        checks.append(_check("SOLVER-RESIDUAL", False, f"missing residual_norm={residual!r}"))
        return
    checks.append(_check("SOLVER-RESIDUAL", residual_value <= max_solver_residual, f"{residual_value:.6e}"))


def _check_readiness(summary: dict[str, Any], checks: list[dict[str, Any]]) -> None:
    readiness = dict(summary.get("readiness", {}))
    if not readiness:
        checks.append(_check("READINESS-RECORDED", False, "missing readiness section"))
        return
    checks.append(_check("READINESS-STATUS", readiness.get("status") != "FAIL", str(readiness.get("status"))))


def _check(identifier: str, condition: bool, detail: str) -> dict[str, Any]:
    return {"id": identifier, "status": "PASS" if condition else "FAIL", "detail": detail}


def _markdown(report: LargeQualificationVerification) -> str:
    lines = [
        "# Verification qualification grand modele",
        "",
        f"Statut: **{report.status}**",
        "",
        f"- Racine: `{report.root}`",
        f"- DDL: {report.details.get('ndof', '')}",
        f"- Cible DDL: {report.details.get('target_dofs', '')}",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- {item['id']}: **{item['status']}** - {item['detail']}" for item in report.checks)
    lines.append("")
    return "\n".join(lines)
