"""Run the bounded experimental B* contact fixture only with explicit --run."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPOSITORY_ROOT = HERE.parents[2]
FIXTURE = HERE / "model_r14_bstar_slip.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        action="store_true",
        help="explicitly run the FEM example (otherwise no calculation is launched)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/bstar_small_rotation_result.json"),
        help="result JSON path (default: output/bstar_small_rotation_result.json)",
    )
    args = parser.parse_args()
    if not args.run:
        print("No calculation launched. Pass --run to explicitly start this FEM example.")
        return 0

    output = args.output.resolve()
    if output.exists():
        parser.error(f"refusing to overwrite existing result file: {output}")

    source_root = REPOSITORY_ROOT / "src"
    if source_root.is_dir():
        sys.path.insert(0, str(source_root))

    from qf_solver import load_model, save_result, solve_model

    model = load_model(FIXTURE)
    result = solve_model(model)
    output.parent.mkdir(parents=True, exist_ok=True)
    save_result(result, output)
    print(f"Saved B* result to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
