"""Run the corrected, module-invoked J10 pairwise mesh post-processing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.j11_transient.j10_spatial_pairwise import analyze_archived_j10


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "research/j11_transient/contracts/j10_spatial_sensitivity_postprocess_contract_v3.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = analyze_archived_j10(contract_path=CONTRACT_PATH)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
