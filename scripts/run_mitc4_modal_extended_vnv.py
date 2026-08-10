"""Run the extended free-free, curved-shell and sparse MITC4 modal studies."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from solveur.verification.mitc4_modal_extended import (
    CURVED_ID,
    FREE_FREE_ID,
    SPARSE_ID,
    write_extended_modal_evidence,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results" / "VNV-MITC4-MODAL-EXTENDED-005",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    summary = write_extended_modal_evidence(output)
    assets = ROOT / "docs" / "assets" / "reviews"
    assets.mkdir(parents=True, exist_ok=True)
    for identifier, name in (
        (FREE_FREE_ID, "mitc4_modal_free_free.png"),
        (CURVED_ID, "mitc4_modal_curved_distorted.png"),
        (SPARSE_ID, "mitc4_modal_eigsh_large.png"),
    ):
        shutil.copy2(output / f"{identifier}.png", assets / name)
    print(f"{summary['campaign']}: {summary['status']}")
    return 0 if summary["status"] == "PASS" else 4


if __name__ == "__main__":
    raise SystemExit(main())
