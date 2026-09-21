"""WP10 HEX20 extension wrapper around the validated bounded runner."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_wp10_tet4_coupled as base

base.ELEMENT_TYPE = "HEX20"
base.CONTRACT = ROOT / "qualification" / "0_2_9" / "wp10_hex20_extension_contract.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=("m1", "m2"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    record = base.run_case(args.case, args.output)
    if args.reference is not None:
        reference = base.independent_reference(args.output, args.reference)
        if reference["status"] != "PASS_INDEPENDENT_OBSERVABLE_RECOMPUTATION":
            return 2
    return 0 if record["status"] == "PASS_CANDIDATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
