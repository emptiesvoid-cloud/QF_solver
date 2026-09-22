"""Run a non-formal lower-load HEX20 sensitivity study.

The original HEX20 extension contract remains immutable at load scale 0.25.
This diagnostic records whether the same HEX20 hierarchy is numerically viable
inside a smaller bounded load window; it cannot award WP09 points.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.run_wp09_hex20_extension import (  # noqa: E402
    CONTRACT_PATH,
    FAMILY,
    LOAD_PATH,
    STAGES,
    _finite,
    _git,
    _json_default,
    _metrics,
    _model,
    _relative,
    _sha256,
)
from solveur.api import solve_model  # noqa: E402
from solveur.mesh.validation import MeshValidator  # noqa: E402


DEFAULT_OUTPUT = ROOT / "qualification" / "0_2_9" / "wp09_hex20_extension" / "load_window_020"
LOAD_SCALE = 0.20
STRAIN_LIMIT = 0.05


def _run(stage: str, cells: int, output: Path) -> dict[str, Any]:
    started = time.perf_counter()
    model = _model(cells, load_scale=LOAD_SCALE)
    quality = MeshValidator().validate(model)
    try:
        result = solve_model(model, enforce_policy=True)
        metrics = _metrics(result, time.perf_counter() - started)
        raw = {
            "study": "WP09 HEX20 lower-load sensitivity",
            "family": FAMILY,
            "stage": stage,
            "cells": cells,
            "load_scale": LOAD_SCALE,
            "load_path": list(LOAD_PATH),
            "source_sha": _git("rev-parse", "HEAD"),
            "contract_sha256": _sha256(CONTRACT_PATH),
            "diagnostic_only": True,
            "mesh_quality": quality.to_dict(),
            "metrics": metrics,
            "result": result.to_dict(),
        }
        path = output / f"{stage.lower()}_hex20_load020.json"
        path.write_text(json.dumps(raw, indent=2, default=_json_default, allow_nan=False), encoding="utf-8")
        return {"stage": stage, "cells": cells, **metrics, "raw_path": str(path)}
    except Exception as exc:  # noqa: BLE001 - preserve diagnostic failures.
        return {
            "stage": stage,
            "cells": cells,
            "status": "FAIL_EXCEPTION",
            "exception_type": type(exc).__name__,
            "exception": str(exc),
            "elapsed_seconds": time.perf_counter() - started,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty output: {output}")
    output.mkdir(parents=True, exist_ok=True)
    rows = [_run(stage, cells, output) for stage, cells in STAGES]
    gates = {
        "H1": rows[0].get("status") == "PASS",
        "H2": rows[1].get("status") == "PASS",
        "H3": rows[2].get("status") == "PASS",
    }
    finite = all(_finite(row.get("max_local_strain_norm")) for row in rows)
    envelope = all(float(row.get("max_local_strain_norm", np.inf)) <= STRAIN_LIMIT for row in rows)
    mesh_deltas = {
        name: _relative(rows[1][name], rows[2][name])
        for name in ("selected_displacement", "reaction_norm", "energy", "von_mises_max")
    } if all(gates.values()) else {}
    mesh_gate = {
        "status": "FAIL_CLOSED" if mesh_deltas.get("selected_displacement", float("inf")) > 0.05 else "PASS",
        "thresholds": {
            "selected_displacement": 0.05,
            "reaction_norm": 0.05,
            "energy": 0.05,
            "von_mises_max": 0.10,
        },
    }
    mesh_gate["status"] = "PASS" if mesh_deltas and all(
        mesh_deltas[name] <= limit for name, limit in mesh_gate["thresholds"].items()
    ) else "FAIL_CLOSED"
    summary = {
        "status": "PASS_DIAGNOSTIC_WITH_MESH_LIMITATION" if all(gates.values()) and finite and envelope else "FAIL_CLOSED",
        "diagnostic_only": True,
        "load_scale": LOAD_SCALE,
        "original_contract_load_scale": 0.25,
        "source_sha": _git("rev-parse", "HEAD"),
        "contract_sha256": _sha256(CONTRACT_PATH),
        "rows": rows,
        "gates": gates,
        "strain_envelope": {"status": "PASS" if finite and envelope else "FAIL", "limit": STRAIN_LIMIT},
        "mesh_gate": mesh_gate,
        "mesh_h2_to_h3_deltas": mesh_deltas,
        "formal_points": "0/pending",
        "limitations": [
            "not the frozen load scale 0.25 contract",
            "no formal WP09 points",
            "no independent global FEM solve",
            "same x-only hierarchy as the extension study",
        ],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, default=_json_default, allow_nan=False), encoding="utf-8")
    lines = [
        "# WP09 HEX20 lower-load sensitivity diagnostic",
        "",
        f"Status: `{summary['status']}`",
        "",
        "This diagnostic is separate from the frozen HEX20 load-scale 0.25 contract.",
        "",
        "| Stage | Cells | Status | max ||U-I||F |",
        "|---|---:|---|---:|",
    ]
    for row in rows:
        lines.append(f"| {row['stage']} | {row['cells']} | {row.get('status', 'UNKNOWN')} | {float(row.get('max_local_strain_norm', float('nan'))):.6e} |")
    lines.extend([
        "",
        f"H2→H3 mesh deltas: `{json.dumps(mesh_deltas, sort_keys=True)}`",
        "",
        "This evidence is diagnostic only and does not modify the accepted HEX8 score or WP09 official ledger.",
    ])
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, default=_json_default))
    return 0 if summary["status"].startswith("PASS_DIAGNOSTIC") else 2


if __name__ == "__main__":
    raise SystemExit(main())
