from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "qualification" / "0_2_9" / "wp11_multifamily_extension_contract.json"
FAMILIES = ("TET4", "HEX8", "TET10", "HEX20")


@pytest.mark.parametrize("family", FAMILIES)
def test_wp11_multifamily_scipy_runner_writes_contract_bound_result(tmp_path: Path, family: str) -> None:
    output = tmp_path / family
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_wp11_multifamily.py",
            "--family",
            family,
            "--backend",
            "scipy",
            "--output",
            str(output),
            "--contract",
            str(CONTRACT),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads((output / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "PASS"
    assert result["element_family"] == family
    assert result["actual_elements"] == 1
    assert result["fallback_count"] == 0
    assert result["observables"]["finite"] is True
    assert (output / "displacement.npy").is_file()
