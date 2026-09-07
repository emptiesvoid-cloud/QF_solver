from __future__ import annotations

import json
from pathlib import Path

from scripts.wp13_common import validate_vnv_contract


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "qualification/0_2_8/wp13_01a_mixed_petsc_contract.json"
EVIDENCE = ROOT / "qualification/0_2_8/wp13_01a_mixed_petsc_evidence.json"


def _read(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp13_01a_contract_is_predeclared_and_fail_closed() -> None:
    contract = _read(CONTRACT)
    assert contract["status"] == "PREDECLARED"
    assert contract["source_sha"] == "0c6204f398a8350c9e3fdb5e68f40708a5ca1750"
    assert validate_vnv_contract(contract) == []
    assert contract["tolerances"]["predeclared"] is True
    assert contract["tolerances"]["post_observation_retuning"] is False


def test_wp13_01a_evidence_preserves_no_go_and_tet4_boundary() -> None:
    evidence = _read(EVIDENCE)
    assert evidence["status"] == "NO_GO"
    assert evidence["owner_decision"]["status"] == "NO_GO"
    metrics = evidence["metrics"]
    assert metrics["petsc_backend_classification"] == "TET4_ONLY"
    assert metrics["architecture_extension_class"] == "MAJOR_REDESIGN"
    assert metrics["numerical_source_changed"] is False
    assert metrics["historical_0_2_7_evidence_changed"] is False


def test_wp13_01a_evidence_does_not_claim_distributed_runs() -> None:
    metrics = _read(EVIDENCE)["metrics"]
    assert metrics["petsc_1_rank"]["status"] == "BLOCKED_DEPENDENCY"
    assert metrics["mpi_2_ranks"]["status"] == "NOT_RUN"
    assert metrics["partition_invariance"].startswith("NOT_EVALUATED")
