"""Validate and install WP05 execution records generated from an exact source SHA."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
QUALIFICATION = ROOT / "qualification" / "0_2_11"
CONTRACT = QUALIFICATION / "wp05_gyroscopic_contract.json"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_hash(value: dict[str, Any]) -> str:
    return _sha(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"))


def _load_record(path: Path, expected_sha: str, key: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("source_sha") != expected_sha:
        raise ValueError(f"Evidence record {path.name} is bound to a different source SHA.")
    if value.get(key) != "PASS":
        raise ValueError(f"Evidence record {path.name} does not pass {key}.")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--gyro-record", type=Path, required=True)
    parser.add_argument("--dense-record", type=Path, required=True)
    args = parser.parse_args()
    if len(args.source_sha) != 40 or any(char not in "0123456789abcdef" for char in args.source_sha):
        parser.error("--source-sha must be a lowercase full Git SHA")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if head != args.source_sha or status:
        parser.error(f"evidence finalization requires clean HEAD={args.source_sha}; found HEAD={head}, dirty={bool(status)}")

    gyro = _load_record(args.gyro_record, args.source_sha, "overall_status")
    dense = _load_record(args.dense_record, args.source_sha, "overall_status")
    contract_hash = _sha(CONTRACT.read_bytes())
    if gyro.get("contract_sha256") != contract_hash or dense.get("contract_sha256") != contract_hash:
        parser.error("Evidence records do not match the current frozen WP05 contract bytes.")
    if gyro.get("g04_formulation_status") != "PASS" or gyro.get("g05_qep_result_status") != "PASS":
        parser.error("GYRO execution record does not pass both frozen gates.")

    stored_gyro = QUALIFICATION / "wp05_gyro_verification_records.json"
    stored_dense = QUALIFICATION / "wp05_dense_characterization.json"
    stored_gyro.write_text(json.dumps(gyro, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    stored_dense.write_text(json.dumps(dense, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")

    sizes = [
        {
            "physical_dofs": run["physical_dofs"],
            "status": run["result_status"],
            "median_seconds": run["summary"]["wall_seconds_median"],
            "peak_rss_bytes": run["summary"]["peak_rss_bytes_max"],
            "maximum_qep_residual": run["summary"]["maximum_qep_residual"],
        }
        for run in dense["executions"]
    ]
    summary = {
        "record_schema": "qf.wp05.gate-summary.v1",
        "schema_version": 2,
        "work_package": "WP05",
        "source_sha": args.source_sha,
        "contract_path": "qualification/0_2_11/wp05_gyroscopic_contract.json",
        "contract_sha256": contract_hash,
        "gyro_record_path": "qualification/0_2_11/wp05_gyro_verification_records.json",
        "gyro_record_sha256": _sha(stored_gyro.read_bytes()),
        "dense_record_path": "qualification/0_2_11/wp05_dense_characterization.json",
        "dense_record_sha256": _sha(stored_dense.read_bytes()),
        "qf0211_g04": gyro["g04_formulation_status"],
        "qf0211_g05": gyro["g05_qep_result_status"] if dense["overall_status"] == "PASS" else "FAIL",
        "gyro_case_statuses": {case["case_id"]: case["numerical_status"] for case in gyro["cases"]},
        "dense_characterization": sizes,
        "supported_physical_dof_bound": dense["supported_physical_dof_bound"],
        "evidence_availability": "AVAILABLE_AND_REPRODUCIBLE",
        "maturity": "EXPERIMENTAL",
        "maturity_promotion": "NONE",
        "g03": "FAIL_PRESERVED",
        "whole_repository_archive_cleared": False,
        "wp14": "HOLD_NOT_PROMOTED",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    summary["record_sha256"] = _canonical_hash(summary)
    summary_path = QUALIFICATION / "wp05_gate_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "qf0211_g04": summary["qf0211_g04"],
                "qf0211_g05": summary["qf0211_g05"],
                "supported_physical_dof_bound": summary["supported_physical_dof_bound"],
                "gate_summary_sha256": _sha(summary_path.read_bytes()),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
