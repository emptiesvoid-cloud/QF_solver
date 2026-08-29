"""Run the dedicated 0.2.6 G05-B modal/dynamic/harmonic evidence batch."""

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


REGISTRY = ROOT / "qualification" / "0_2_6" / "g05_deep_case_registry.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "vnv_026" / "g05b")
    parser.add_argument("--family", choices=("MOD", "DYN", "HAR"))
    arguments = parser.parse_args()
    registry = VnvRegistry.from_file(REGISTRY)
    tags = (arguments.family.lower(),) if arguments.family else ()
    summary = VnvRunner(ROOT).run(registry, arguments.output, profile="G05B", tags=tags)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
