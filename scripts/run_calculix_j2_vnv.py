"""Execute and normalize the CalculiX isotropic J2 correlation."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from solveur.verification.calculix_j2 import (  # noqa: E402
    evaluate_calculix_j2_correlation,
    parse_calculix_j2_dat,
    write_calculix_j2_figure,
    write_calculix_j2_report,
)

IMAGE = "qf-solver/calculix-nafems13h:2.20"
SOURCE = PROJECT_ROOT / "qualification" / "vnv" / "external" / "calculix_j2" / "j2_uniaxial_isotropic.inp"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the CalculiX 2.20 isotropic J2 correlation.")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "results" / "VNV-J2-CALCULIX-ISOTROPIC-002")
    parser.add_argument("--image", default=IMAGE)
    args = parser.parse_args()
    output = args.output.resolve()
    work = output / "calculix"
    work.mkdir(parents=True, exist_ok=True)
    input_path = work / SOURCE.name
    shutil.copy2(SOURCE, input_path)
    command = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{work}:/work",
        "-w",
        "/work",
        args.image,
        input_path.stem,
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    (output / "calculix.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"CalculiX failed with exit code {completed.returncode}; see calculix.log")
    dat_path = work / f"{input_path.stem}.dat"
    if not dat_path.is_file():
        raise RuntimeError("CalculiX completed without a .dat result file.")
    state = parse_calculix_j2_dat(dat_path.read_text(encoding="utf-8", errors="replace"))
    summary = evaluate_calculix_j2_correlation(state)
    summary["external_solver"] = {"name": "CalculiX", "version": "2.20", "image": args.image}
    summary["input_sha256"] = hashlib.sha256(input_path.read_bytes()).hexdigest()
    summary["command"] = command
    write_calculix_j2_report(summary, output)
    write_calculix_j2_figure(summary, output)
    print(f"CalculiX J2 V&V: {summary['status']}")
    print(json.dumps({check["id"]: check["value"] for check in summary["checks"]}, indent=2))
    print(f"output: {output}")
    return 0 if summary["status"] == "PASS_INTERNAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
