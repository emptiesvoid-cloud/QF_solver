from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import scripts.run_wp12_code_aster_multifamily as wp12_runner
from scripts.run_wp12_code_aster_multifamily import (
    ASTER_NODE_ORDER,
    FAMILIES,
    aster_comm_text,
    aster_export_text,
    aster_mesh_text,
    relative_l2,
    relative_linf,
)
from scripts.audit_wp12_code_aster_multifamily import _validate_manifest, recompute_metrics


@pytest.mark.parametrize("family", FAMILIES)
def test_aster_mesh_text_preserves_node_count_and_canonical_groups(family: str) -> None:
    node_count = len(ASTER_NODE_ORDER[family])
    coordinates = np.zeros((node_count, 3), dtype=float)
    coordinates[:, 0] = np.linspace(0.0, 1.0, node_count)
    connectivity = np.arange(node_count, dtype=np.int64)

    text = aster_mesh_text(family, coordinates, connectivity)

    assert f"{family if family.startswith('TET') else family}" in text
    assert "GROUP_MA\nSOLID\nM1\nFINSF" in text
    assert "GROUP_NO\nROOT\n" in text
    assert "GROUP_NO\nLOAD\n" in text
    assert text.count("GROUP_NO\nQF") == node_count


def test_hex20_aster_connectivity_uses_code_aster_edge_order() -> None:
    coordinates = np.zeros((20, 3), dtype=float)
    coordinates[1::2, 0] = 1.0
    connectivity = np.arange(20, dtype=np.int64)

    text = aster_mesh_text("HEX20", coordinates, connectivity)

    element_line = next(line for line in text.splitlines() if line.startswith("M1 "))
    assert element_line == "M1 N1 N2 N3 N4 N5 N6 N7 N8 N9 N12 N14 N10 N11 N13 N15 N16 N17 N19 N20 N18"


def test_frozen_contract_provenance_runtime_and_family_order_are_coherent() -> None:
    contract_path = Path(__file__).resolve().parents[2] / "qualification/0_2_9/wp12_external_vv_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    external = contract["external_solver"]
    reference = contract["qf_reference"]

    assert tuple(contract["families"]) == FAMILIES
    assert contract["code_aster_action"] == external["action"] == "make_etude"
    assert contract["code_aster_image"] == external["image"]
    assert contract["code_aster_image_id"] == external["image_id"]
    assert contract["timeout_seconds"] == external["timeout_seconds"]
    assert contract["memory_limit_mb"] == external["memory_limit_mb"]
    assert contract["wp11_source_sha"] == reference["source_sha"]
    assert contract["wp11_owner_acceptance_sha256"] == reference["owner_acceptance_sha256"]
    assert contract["wp11_owner_manifest_sha256"] == reference["owner_manifest_sha256"]
    assert contract["wp11_contract_sha256"] == reference["contract_sha256"]
    for family in FAMILIES:
        spec = contract["families"][family]
        assert tuple(spec["aster_local_node_order"]) == ASTER_NODE_ORDER[family]
        assert spec["dofs"] == 3 * spec["nodes"]


def test_aster_comm_preserves_total_nodal_load_without_equal_share_redefinition() -> None:
    loads = np.zeros(24, dtype=float)
    loads[2] = -1000.0
    material = {"E": 210.0e9, "nu": 0.3}

    text = aster_comm_text("TET4", 8, material, loads)

    assert 'FZ=-1000' in text
    assert "E=210000000000" in text
    assert "NU=0.29999999999999999" in text
    assert "MECA_STATIQUE" in text
    assert "REAC_NODA" in text


def test_generated_code_aster_deck_is_valid_python_syntax() -> None:
    loads = np.zeros(12, dtype=float)
    loads[2] = -1000.0
    deck = aster_comm_text("TET4", 4, {"E": 210.0e9, "nu": 0.3}, loads)

    compile(deck, "WP12_TET4.comm", "exec")


def test_run_aster_export_binds_mesh_and_single_cpu_without_mpi() -> None:
    export = aster_export_text("HEX8", timeout_seconds=900, memory_limit_mb=4096)

    assert "P actions make_etude" in export
    assert "P ncpus 1" in export
    assert "P mpi_nbcpu 1" in export
    assert "P mpi_nbnoeud 1" in export
    assert "F comm /work/HEX8.comm D 1" in export
    assert "F mail /work/HEX8.mail D 20" in export
    assert "F mess /work/HEX8.mess R 6" in export
    assert "F resu /work/HEX8.resu R 8" in export
    assert "F result " not in export
    assert "P no-mpi" not in export


def test_manifest_rejects_unlisted_or_stale_files(tmp_path) -> None:
    from scripts.run_wp12_code_aster_multifamily import write_json

    listed = tmp_path / "listed.txt"
    listed.write_text("frozen\n", encoding="utf-8")
    digest = wp12_runner.sha256_file(listed)
    write_json(
        tmp_path / "manifest.json",
        {"files": {"listed.txt": {"sha256": digest, "size_bytes": listed.stat().st_size}}},
    )
    assert _validate_manifest(tmp_path) == []

    (tmp_path / "unlisted.txt").write_text("extra\n", encoding="utf-8")
    errors = _validate_manifest(tmp_path)
    assert len(errors) == 1
    assert "unlisted=['unlisted.txt']" in errors[0]


def test_external_execution_uses_official_run_aster_entrypoint_and_records_fresh_process(
    tmp_path, monkeypatch
) -> None:
    class CompletedProcess:
        pid = 48152
        returncode = 0

        def poll(self):
            return self.returncode

    captured: dict[str, object] = {}

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["cwd"] = kwargs["cwd"]
        cid = Path(command[command.index("--cidfile") + 1])
        cid.write_text("a" * 64, encoding="ascii")
        return CompletedProcess()

    monkeypatch.setattr(wp12_runner.shutil, "which", lambda name: "docker.exe")
    monkeypatch.setattr(wp12_runner.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        wp12_runner.subprocess,
        "run",
        lambda *args, **kwargs: wp12_runner.subprocess.CompletedProcess(
            args[0], 0, "code_aster 18.1.0 (spack-local)\n", ""
        ),
    )

    result = wp12_runner._run_aster(tmp_path, "TET4", 900, "sha256:" + "b" * 64)
    command = captured["command"]

    assert command[command.index("--entrypoint") + 1] == wp12_runner.CODE_ASTER_RUNNER
    assert command[command.index(wp12_runner.CODE_ASTER_IMAGE) + 1] == "TET4.export"
    assert "--cpus=1" in command
    assert "--no-mpi" in command
    assert "python3" not in command
    assert result["fresh_container_process"] is True
    assert result["container_id"] == "a" * 64
    assert result["image_id"] == "sha256:" + "b" * 64
    telemetry = [json.loads(line) for line in (tmp_path / "telemetry.jsonl").read_text(encoding="utf-8").splitlines()]
    process_record = json.loads((tmp_path / "process.json").read_text(encoding="utf-8"))
    assert telemetry[0]["event"] == "RUN_START"
    assert telemetry[-1]["event"] == "RUN_END"
    assert process_record["telemetry_events"] == len(telemetry)


def test_independent_recomputation_uses_all_fixed_nodes_and_checks_full_fields() -> None:
    qf_u = np.zeros(12)
    qf_u[5] = -1000.0
    stiffness = np.eye(12)
    stiffness[2, 2] = 2.0
    stiffness[5, 5] = 1.0
    stiffness[2, 5] = -1.0
    stiffness[5, 2] = -1.0
    loads = np.zeros(12)
    loads[5] = -1000.0
    fixed = np.array([0, 1, 2, 6, 7, 8, 9, 10, 11], dtype=np.int64)
    qf_reaction = (stiffness @ qf_u - loads).reshape(4, 3)
    aster_displacement = qf_u.reshape(4, 3).copy()
    aster_displacement[2, 0] = 2.0e-9
    aster_reaction = qf_reaction.copy()

    metrics = recompute_metrics(
        qf_displacement=qf_u,
        qf_fixed=fixed,
        qf_loads=loads,
        qf_stiffness=stiffness,
        aster_displacement=aster_displacement,
        aster_reaction=aster_reaction,
        coordinates=np.zeros((4, 3)),
    )

    assert metrics["displacement_relative_l2"] > 0.0
    assert metrics["reaction_relative_l2"] == pytest.approx(0.0)
    assert metrics["strain_energy_from_external_work_relative"] == pytest.approx(0.0)
    assert metrics["qf_force_equilibrium_relative"] == pytest.approx(0.0)
    assert metrics["aster_force_equilibrium_relative"] == pytest.approx(0.0)
    assert metrics["fixed_displacement_abs_max"] == pytest.approx(2.0e-9)


def test_independent_recomputation_fails_closed_on_nonfinite_raw_values() -> None:
    with pytest.raises(ValueError, match="Non-finite"):
        recompute_metrics(
            qf_displacement=np.array([np.nan, 0.0, 0.0]),
            qf_fixed=np.array([0]),
            qf_loads=np.zeros(3),
            qf_stiffness=np.eye(3),
            aster_displacement=np.zeros((1, 3)),
            aster_reaction=np.zeros((1, 3)),
            coordinates=np.zeros((1, 3)),
        )


def test_relative_comparison_metrics_are_finite_and_scale_aware() -> None:
    expected = np.array([1.0e-8, -2.0e-8, 3.0e-8])
    actual = expected * (1.0 + 1.0e-10)

    assert relative_l2(actual, expected) == pytest.approx(1.0e-10)
    assert relative_linf(actual, expected) == pytest.approx(1.0e-10)
