"""Targeted WP09-R headless Code_Aster remediation checks."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "qualification/0_2_7/external_oracles/wedge6/docker/headless_contract.json"
DOCKERFILE = ROOT / "qualification/0_2_7/external_oracles/wedge6/docker/Dockerfile"
EVIDENCE = ROOT / "qualification/0_2_7/vnv_v2/wp09r_code_aster_evidence.json"


def test_headless_contract_is_pinned_and_sequential() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["status"] == "CONTROLLED_REPRODUCIBLE"
    assert contract["base_image"] == "simvia/code_aster:18.1.0"
    assert contract["base_image_digest"].startswith("sha256:")
    assert contract["code_aster_version"] == "18.1.0"
    assert contract["execution_model"] == {
        "headless": True,
        "launcher_processes": 1,
        "no_mpi_relaunch": True,
        "mpi4py_import_required": True,
        "mpi4py_comm_world_size": 1,
    }
    assert "PYTHONPATH" in contract["environment"]
    assert "LD_LIBRARY_PATH" in contract["environment"]


def test_dockerfile_exposes_existing_spack_view_without_host_install() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    assert "FROM simvia/code_aster@sha256:" in dockerfile
    assert "ENV PYTHONPATH=" in dockerfile
    assert "ENV LD_LIBRARY_PATH=" in dockerfile
    assert "ENTRYPOINT" in dockerfile
    assert "apt-get" not in dockerfile


def test_code_aster_evidence_is_external_bounded_and_not_a_promotion() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    oracle = evidence["oracle"]
    assert oracle["state"] == "PASS"
    assert oracle["solver"] == "Code_Aster 18.1.0 / PENTA6"
    assert oracle["formulation_compatible"] is True
    assert oracle["verdict"] == "PASS_EXTERNAL_CORRELATION_BOUNDED"
    assert oracle["tolerance_approval_state"] == "OWNER_REVIEW_REQUIRED"
    assert oracle["relative_error"]["displacement"] < 1.0e-6
    assert oracle["relative_error"]["total_reaction"] < 1.0e-6
    assert oracle["relative_error"]["strain_energy"] < 1.0e-6
    assert evidence["artifact_classification"] == "CONTROLLED_PROOF"
