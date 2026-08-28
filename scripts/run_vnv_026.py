"""Run registered QF Solver 0.2.6 V&V cases without arbitrary shell execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from solveur.verification.framework import VnvRegistry, VnvRunner  # noqa: E402


REGISTRY = ROOT / "qualification" / "0_2_6" / "case_registry.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="SMOKE", choices=("SMOKE", "G05", "G06", "STANDARD", "FULL", "EXTERNAL", "ADVERSARIAL", "SCALING", "RELEASE"))
    parser.add_argument("--case", dest="case_ids", action="append", default=[])
    parser.add_argument("--tag", dest="tags", action="append", default=[])
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "vnv_026")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--list", action="store_true", help="List selected definitions without running them.")
    arguments = parser.parse_args()
    registry = VnvRegistry.from_file(REGISTRY)
    selected = registry.select(case_ids=arguments.case_ids, profile=arguments.profile, tags=arguments.tags)
    if arguments.list:
        print(json.dumps([case.to_mapping() for case in selected], indent=2, sort_keys=True))
        return 0
    summary = VnvRunner(ROOT).run(
        registry,
        arguments.output / arguments.profile.lower(),
        profile=arguments.profile,
        case_ids=arguments.case_ids,
        tags=arguments.tags,
        resume=arguments.resume,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
