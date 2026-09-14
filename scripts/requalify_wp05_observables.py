"""Re-extract the frozen WP05 observables from completed solver artifacts.

This is a qualification-only repair for the first WP05 runner.  It reuses the
completed displacement/state outputs and recomputes only the observable
extraction with production integration-point fields.  Original result and raw
files are never overwritten.
"""

# This script prepends the checkout's src tree before importing the package.
# ruff: noqa: E402

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
for import_root in (str(ROOT), str(SOURCE_ROOT)):
    if import_root in sys.path:
        sys.path.remove(import_root)
    sys.path.insert(0, import_root)

from scripts.run_wp05_structural_qualification import _model, _observables
from scripts.wp05_cd_structural_harness import StructuralBenchmarkContract, build_mesh


DEFAULT_INPUT = ROOT / "qualification" / "0_2_9" / "overnight_r2" / "wp05_runs"
DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_9" / "overnight_r2_corrected" / "wp05_runs"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _verify_mesh(raw: np.lib.npyio.NpzFile, mesh: Any) -> None:
    coordinates = np.asarray(raw["coordinates"], dtype=np.float64)
    connectivity = np.asarray(raw["connectivity"], dtype=np.int64)
    expected_coordinates = np.asarray(mesh.coordinates, dtype=np.float64)
    expected_connectivity = np.asarray(mesh.connectivity, dtype=np.int64)
    if not np.array_equal(coordinates, expected_coordinates):
        raise ValueError("Completed artifact coordinates differ from frozen mesh construction.")
    if not np.array_equal(connectivity, expected_connectivity):
        raise ValueError("Completed artifact connectivity differs from frozen mesh construction.")


def requalify_result(input_result: Path, output_root: Path) -> dict[str, Any]:
    original = json.loads(input_result.read_text(encoding="utf-8"))
    if original.get("status") != "PASS":
        raise ValueError(f"Only completed PASS artifacts can be re-extracted: {input_result}")
    family = str(original["family"])
    level = str(original["mesh_level"])
    contract = StructuralBenchmarkContract()
    input_raw = ROOT / str(original["raw_npz"])
    if not input_raw.is_file():
        raise FileNotFoundError(input_raw)
    with np.load(input_raw, allow_pickle=False) as raw:
        mesh = build_mesh(family, level, contract)
        _verify_mesh(raw, mesh)
        model, model_mesh, loads, fixed_nodes = _model(family, level, contract)
        if not np.array_equal(np.asarray(raw["loads"], dtype=np.float64), loads):
            raise ValueError("Completed artifact loads differ from the frozen load vector.")
        displacement = np.asarray(raw["displacement"], dtype=np.float64)
        observed, arrays = _observables(model, model_mesh, loads, fixed_nodes, displacement)

    output_dir = output_root / family / level
    output_dir.mkdir(parents=True, exist_ok=True)
    output_raw = output_dir / "raw.npz"
    output_result = output_dir / "result.json"
    np.savez_compressed(output_raw, **arrays)  # type: ignore[arg-type]

    payload = deepcopy(original)
    payload.update(
        {
            "evidence_schema_version": 3,
            "status": "PASS",
            "observables": observed,
            "raw_npz": _relative(output_raw),
            "raw_sha256": _sha256(output_raw),
            "observable_extraction_status": "CORRECTED_FROZEN_INTEGRATION_POINT_REFERENCE_VOLUME",
            "observable_extraction_source": "scripts/run_wp05_structural_qualification.py:_integration_records",
            "supersedes_result": _relative(input_result),
            "supersedes_raw_sha256": str(original.get("raw_sha256", _sha256(input_raw))),
            "postprocessed_at": datetime.now(timezone.utc).isoformat(),
            "postprocessing_git_sha": _git_sha(),
            "postprocessing_preserves_solver_output": True,
            "postprocessing_changes_mechanics": False,
        }
    )
    _write_json(output_result, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--family", choices=("TET10", "HEX20"))
    parser.add_argument("--mesh", choices=("H1", "H2", "H3"))
    args = parser.parse_args()
    input_root = args.input.resolve()
    output_root = args.output.resolve()
    selected = []
    for path in sorted(input_root.glob("*/H*/result.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "PASS":
            continue
        if args.family and payload.get("family") != args.family:
            continue
        if args.mesh and payload.get("mesh_level") != args.mesh:
            continue
        selected.append(path)
    if not selected:
        raise SystemExit("No completed WP05 artifacts selected.")
    results = [requalify_result(path, output_root) for path in selected]
    print(json.dumps({"count": len(results), "results": results}, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
