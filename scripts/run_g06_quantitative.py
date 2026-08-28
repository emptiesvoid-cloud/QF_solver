"""Run quantitative analytical and mesh studies for the 0.2.6 G06 corpus."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from solveur.api import solve_model  # noqa: E402
from solveur.io.json_reader import JsonModelReader  # noqa: E402
from solveur.verification.framework import VnvRegistry, VnvRunner  # noqa: E402
from solveur.verification.framework.environment import capture_environment  # noqa: E402


REGISTRY = ROOT / "qualification" / "0_2_6" / "case_registry.json"
MESH_MODELS = tuple(ROOT / "examples" / "vnv_026_g06" / f"hex8_mesh_{nx:02d}.json" for nx in (1, 2, 4, 8))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "vnv_026_g06_quantitative")
    arguments = parser.parse_args()
    target = arguments.output.resolve()
    target.mkdir(parents=True, exist_ok=True)
    environment = capture_environment(ROOT)
    registry = VnvRegistry.from_file(REGISTRY)
    analytical = _run_analytical(registry, target / "analytical", environment)
    mesh = _run_mesh(target / "mesh", environment)
    summary = {
        "schema_version": 1,
        "study_id": "VNV026-G06-QUANTITATIVE-001",
        "status": "PASS" if analytical["status"] == "PASS" and mesh["status"] == "PASS" else "FAIL",
        "source": environment["source"],
        "captured_at_utc": environment["captured_at_utc"],
        "solver_version": environment["solver_version"],
        "registry_digest": registry.digest,
        "analytical": analytical,
        "mesh": mesh,
    }
    summary_path = target / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = _write_manifest(target, environment, registry.digest)
    print(json.dumps({"status": summary["status"], "manifest": str(manifest), "source": environment["source"]}, indent=2))
    return 0 if summary["status"] == "PASS" else 1


def _run_analytical(registry: VnvRegistry, output: Path, environment: dict[str, Any]) -> dict[str, Any]:
    summary = VnvRunner(ROOT).run(registry, output, profile="G06", tags=("analytical",))
    result_rows = []
    for path in sorted(output.glob("*.json")):
        if path.name in {"summary.json", "manifest.json"}:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        oracle = data.get("diagnostics", {}).get("oracle", {})
        result_rows.append(
            {
                "case_id": data["case_id"],
                "element_family": oracle.get("element_family"),
                "relative_error": oracle.get("relative_error"),
                "relative_tolerance": oracle.get("relative_tolerance"),
                "status": data["status"],
                "source_sha": data["source_sha"],
                "dirty": data["environment"]["source"]["dirty"],
            }
        )
    errors = [float(row["relative_error"]) for row in result_rows]
    return {
        "status": "PASS" if summary["status"] == "PASS" and result_rows and max(errors) <= max(float(row["relative_tolerance"]) for row in result_rows) else "FAIL",
        "case_count": len(result_rows),
        "pass_count": summary["pass_count"],
        "max_relative_error": max(errors) if errors else None,
        "rows": result_rows,
        "reference": "Independent constrained free-DOF stiffness integration for TET4/TET10/HEX8/HEX20.",
        "environment_source": environment["source"],
    }


def _run_mesh(output: Path, environment: dict[str, Any]) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for model_path in MESH_MODELS:
        model = JsonModelReader().read(model_path)
        before = _rss_bytes()
        started = perf_counter()
        result = solve_model(model)
        elapsed = perf_counter() - started
        after = _rss_bytes()
        tip_nodes = np.flatnonzero(np.isclose(model.nodes[:, 0], 1.0, atol=1.0e-12))
        tip_values = [result.displacements[result.dofs.index(int(node), "UX")] for node in tip_nodes]
        tip_displacement = float(np.mean(tip_values))
        material = model.materials[model.elements[0].material]
        length = float(np.max(model.nodes[:, 0]) - np.min(model.nodes[:, 0]))
        area = float(np.ptp(model.nodes[:, 1]) * np.ptp(model.nodes[:, 2]))
        total_force = float(sum(load.value for load in model.loads if load.dof == "UX"))
        reference = total_force * length / (float(material["E"]) * area)
        residual = float(result.audit.equilibrium.get("free_relative_residual", np.inf)) if result.audit else np.inf
        nx = int(model_path.stem.rsplit("_", 1)[-1])
        rows.append(
            {
                "level": f"nx={nx}",
                "nx": nx,
                "model": model_path.relative_to(ROOT).as_posix(),
                "node_count": model.node_count,
                "element_count": len(model.elements),
                "dof_count": result.dofs.ndof,
                "tip_ux": tip_displacement,
                "reference_tip_ux": reference,
                "relative_error": abs(tip_displacement - reference) / abs(reference),
                "residual": residual,
                "wall_time_seconds": elapsed,
                "rss_delta_bytes": max(0, after - before),
                "status": result.status,
                "source_sha": environment["source"]["sha"],
                "dirty": environment["source"]["dirty"],
            }
        )
    rows.sort(key=lambda row: row["nx"])
    for previous, current in zip(rows, rows[1:]):
        previous_error = float(previous["relative_error"])
        current_error = float(current["relative_error"])
        current["successive_error_reduction"] = previous_error - current_error
        current["observed_order"] = (
            float(np.log(previous_error / current_error) / np.log(current["nx"] / previous["nx"]))
            if previous_error > 0.0 and current_error > 0.0 else None
        )
    _plot_mesh(output / "mesh_convergence.png", rows)
    errors = [float(row["relative_error"]) for row in rows]
    return {
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) and all(current <= previous for previous, current in zip(errors, errors[1:])) else "FAIL",
        "level_count": len(rows),
        "rows": rows,
        "reference": "Uniform axial bar response: u_tip = F L / (E A).",
        "trend": "non-increasing relative error across nx=1,2,4,8" if all(current <= previous for previous, current in zip(errors, errors[1:])) else "non-monotone",
        "plot": "mesh/mesh_convergence.png",
        "environment_source": environment["source"],
    }


def _rss_bytes() -> int:
    try:
        import psutil
    except ModuleNotFoundError:
        return 0
    return int(psutil.Process().memory_info().rss)


def _plot_mesh(path: Path, rows: list[dict[str, Any]]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(7.2, 4.2))
    axis.loglog([row["nx"] for row in rows], [row["relative_error"] for row in rows], "o-")
    axis.set(xlabel="Elements along length (nx)", ylabel="Relative tip displacement error", title="G06 HEX8 mesh study")
    axis.grid(True, which="both", alpha=0.25)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _write_manifest(output: Path, environment: dict[str, Any], registry_digest: str) -> Path:
    files = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            files.append({"path": path.relative_to(output).as_posix(), "sha256": _sha256(path)})
    payload = {
        "schema_version": 1,
        "study_id": "VNV026-G06-QUANTITATIVE-001",
        "source": environment["source"],
        "captured_at_utc": environment["captured_at_utc"],
        "solver_version": environment["solver_version"],
        "registry_digest": registry_digest,
        "threshold_source": "qualification/0_2_6/tolerance_policy.json",
        "files": files,
    }
    path = output / "manifest.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
