"""Check runner import identity without launching any qualification campaign."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("module", [
    "scripts.run_wp06d_low_strain_exploratory",
    "scripts.run_wp10_hex8_coupled",
    "scripts.run_wp10_tet4_coupled",
    "scripts.run_wp10_hex20_coupled",
    "scripts.run_wp10_tet10_surface_r2",
])
def test_runner_import_uses_the_same_source_root_from_an_unrelated_cwd(tmp_path: Path, module: str) -> None:
    # A fresh import per runner avoids mutating another test's cached base module.
    code = (
        "import importlib,json,sys; from pathlib import Path; "
        "m=importlib.import_module(sys.argv[1]); expected=Path(sys.argv[2]).resolve(); "
        "assert m.ROOT == expected; "
        "assert not hasattr(m,'LOCAL_SOURCE') or m.LOCAL_SOURCE == expected/'src'; "
        "print(json.dumps({'root':str(m.ROOT),'imported':m.__name__}))"
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(ROOT / "src")])
    completed = subprocess.run(
        [sys.executable, "-c", code, module, str(ROOT)],
        cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["imported"] == module
    assert Path(report["root"]) == ROOT
