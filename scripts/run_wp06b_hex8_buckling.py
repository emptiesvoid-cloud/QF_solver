"""Run the WP06B HEX8 buckling remediation campaign without rewriting WP06 evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_wp06_hex8_buckling import _json_default, run_campaign  # noqa: E402


BASELINE_SHA = "be8fbd99d8a3d3b8e4ee3b8d867842389b063061"
CONTRACT = ROOT / "qualification/0_2_8/wp06b_hex8_buckling_contract.json"
EVIDENCE = ROOT / "qualification/0_2_8/wp06b_hex8_buckling_vnv.json"


def main() -> None:
    result = run_campaign()
    result.update(
        {
            "record_id": "QF-028-WP06B-HEX8-BUCKLING-VNV",
            "work_package": "WP06B",
            "baseline_sha": BASELINE_SHA,
            "source_sha": BASELINE_SHA,
            "contract": str(CONTRACT.relative_to(ROOT)).replace("\\", "/"),
            "status": "CAMPAIGN_COMPLETE_NO_PROMOTION",
            "public_maturity": "NOT_QUALIFIED",
        }
    )
    result["root_cause_audit"] = json.loads(CONTRACT.read_text(encoding="utf-8"))["root_cause_audit"]
    result["minimal_remediation"] = json.loads(CONTRACT.read_text(encoding="utf-8"))["minimal_remediation"]
    result["fixes_applied"] = {
        "deterministic_arpack_start": True,
        "invalid_orientation_regression_case": True,
        "euler_oracle_changed": False,
        "mesh_or_boundary_scope_changed": False,
        "tolerances_changed": False,
    }
    result["numerical_source_changed"] = True
    result["historical_0_2_7_evidence_changed"] = False
    EVIDENCE.write_text(
        json.dumps(result, indent=2, sort_keys=True, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": result["status"], "technical_decision": result["technical_decision"], "replays": result["replays"], "external": result["external_oracle"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
