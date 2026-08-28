"""Capture a compact 0.2.5 numerical baseline used only as a refactor guard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from solveur.core.router import AnalysisRouter  # noqa: E402
from solveur.cli.main import SolverCli  # noqa: E402
from solveur.io.json_reader import JsonModelReader  # noqa: E402
from solveur.version import __version__  # noqa: E402
from solveur.verification.framework.environment import capture_environment  # noqa: E402


BASE_RELEASE_HEAD = "1e6c3e96d1e1366c4cc790546e82769cd9227902"
MODELS = (
    "tet4_static.json", "mitc3_shell_static.json", "tet4_modal_unit.json", "tet4_transient_dynamic.json",
    "tet4_elastoplastic_static.json", "tet4_geometric_nonlinear_static.json", "tet4_linear_buckling.json",
    "frictionless_contact_plane.json",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "qualification" / "0_2_6" / "baseline_snapshot.json")
    arguments = parser.parse_args()
    rows = [_solve(name) for name in MODELS]
    report = {
        "schema_version": 1,
        "purpose": "refactoring_guard_not_new_025_qualification",
        "baseline_release": "v0.2.5a0",
        "baseline_release_head": BASE_RELEASE_HEAD,
        "historical_qualified_numerical_source": "8047fb63c420609b510beaa1e30aa3ab31d9ad87",
        "historical_release_evidence": {
            "source_document": "docs/verification/0_2_5/0_2_5_release_readiness.md",
            "qualification_regression": "1719 passed, 0 failed, 183 skipped",
            "reference_coverage_percent": 88.37,
            "external_correlation": "64/64 PASS",
            "replay_status": "NOT_REPLAYED_IN_FOUNDATION",
        },
        "capture_environment": capture_environment(ROOT),
        "solver_version_at_capture": __version__,
        "public_api_symbols": _public_symbols(),
        "cli_entrypoint": "qf-solver",
        "cli_commands": _cli_commands(),
        "comparison_policy": {"exact": ["analysis", "status", "n_dof"], "relative_tolerance": 1e-12, "rationale": "small deterministic maintained examples"},
        "representative_results": rows,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"baseline capture: {len(rows)} representative routes -> {arguments.output}")
    return 0


def _solve(name: str) -> dict[str, Any]:
    result = AnalysisRouter().solve(JsonModelReader().read(ROOT / "examples" / name)).to_dict()
    solver = result.get("solver") if isinstance(result.get("solver"), dict) else {}
    return {"model": name, "status": result.get("status"), "analysis": result.get("analysis"), "n_dof": result.get("ndof"), "max_displacement": result.get("max_displacement"), "iterations": solver.get("iterations"), "residual_norm": solver.get("residual_norm")}


def _public_symbols() -> list[str]:
    import qf_solver

    return sorted(qf_solver.__all__)


def _cli_commands() -> list[str]:
    """Capture the public command names from the same parser users invoke."""

    parser = SolverCli().build_parser()
    for action in parser._actions:  # argparse exposes subcommands through this action.
        choices = getattr(action, "choices", None)
        if isinstance(choices, dict):
            return sorted(choices)
    raise RuntimeError("QF Solver CLI parser has no subcommand registry.")


if __name__ == "__main__":
    raise SystemExit(main())
