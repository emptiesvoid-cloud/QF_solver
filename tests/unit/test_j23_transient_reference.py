import csv
from pathlib import Path

import numpy as np
import pytest

from research.j23.transient_flexure_reference.compare_external_history import compare_histories, read_rows
from research.j23.transient_flexure_reference.prepare_abaqus_case import (
    DATA_DIR,
    MODEL_INPUTS,
    QF_HISTORY,
    build_package,
    integrate_uniform_tip_load,
    load_model_inputs,
    render_abaqus_input,
    validate_archived_load,
)


def test_archived_tet10_mesh_and_load_match() -> None:
    arrays = load_model_inputs(MODEL_INPUTS)
    recomputed, audit = validate_archived_load(arrays)

    assert arrays["coordinates"].shape == (1377, 3)
    assert arrays["connectivity"].shape == (768, 10)
    assert audit["face_triangle_count"] == 32
    assert audit["face_area_m2"] == pytest.approx(0.01, abs=1e-12)
    assert audit["recomputed_resultant_n"] == pytest.approx([0.0, 0.0, 100.0], abs=1e-12)
    assert np.max(np.abs(recomputed - arrays["archived_nodal_force"])) < 1e-13
    assert np.linalg.norm(audit["moment_about_loaded_face_centroid_nm"]) < 1e-12


def test_generated_deck_model_and_time_contract(tmp_path: Path) -> None:
    arrays = load_model_inputs(MODEL_INPUTS)
    load, _audit = validate_archived_load(arrays)
    deck = render_abaqus_input(arrays, load)

    assert deck.count("*ELEMENT, TYPE=C3D10") == 1
    assert deck.count("*NODE\n") == 1
    assert "*MATERIAL, NAME=ELASTIC_SOLID\n*DENSITY\n7800." in deck
    assert "210000000000., 0.3" in deck
    assert "*DYNAMIC, DIRECT, ALPHA=0.0, BETA=0.25, GAMMA=0.5\n0.0001, 0.080000000000000002, 0.0001, 0.0001" in deck
    assert "*BOUNDARY\nFIXED_NODES, 1, 3, 0.0" in deck
    assert "*OUTPUT, FIELD, NUMBER INTERVAL=800, TIME MARKS=YES" in deck
    assert "0, 0\n0.01, 1\n0.02, 0\n0.080000000000000002, 0" in deck
    cload_section = deck.split("*CLOAD, AMPLITUDE=TIP_PULSE\n", 1)[1].split("*OUTPUT, FIELD", 1)[0]
    load_lines = [line for line in cload_section.splitlines() if line.strip()]
    assert load_lines
    assert all(line.startswith("BEAM-1.") and ", 3, " in line for line in load_lines)
    assert sum(float(line.rsplit(",", 1)[1]) for line in load_lines) == pytest.approx(100.0, abs=1e-12)
    assert len(deck.splitlines()) < 10000
    assert DATA_DIR.is_dir()
    assert QF_HISTORY.is_file()


def test_qf_reference_export_is_physical_time_aligned(tmp_path: Path) -> None:
    package = tmp_path / "generated"
    result = build_package(DATA_DIR, package)
    csv_path = package / "site_assets" / "qf_euler_bernoulli_probe_histories.csv"
    plot_path = package / "site_assets" / "qf_euler_bernoulli_histories.png"
    with csv_path.open(encoding="utf-8") as stream:
        rows = stream.readlines()

    assert len(rows) == 802  # header, initial state, and 800 archived increments
    assert rows[1].startswith("0,")
    assert rows[-1].startswith("0.080000000000000002,")
    assert result["load_audit"]["archive_load_max_abs_difference_n"] < 1e-13
    assert result["qf_equilibrium"]["checkpoint_count"] == 101
    assert result["qf_equilibrium"]["unique_checkpoint_count"] == 100
    assert result["qf_equilibrium"]["duplicate_terminal_checkpoint_identical"] is True
    assert result["qf_eb_metrics"]["status"] == "DESCRIPTIVE_ARCHIVED_QF_VS_EULER_BERNOULLI"
    assert result["qf_eb_metrics"]["probes"]["tip"]["max_difference_normalized_to_eb_peak"] == pytest.approx(0.10488028029920096)
    assert plot_path.is_file()
    assert (package / "j23_tet10_transient_flexure.inp").is_file()


def test_external_history_comparison_accepts_synthetic_identical_curves(tmp_path: Path) -> None:
    package = tmp_path / "generated"
    build_package(DATA_DIR, package)
    qf_csv = package / "site_assets" / "qf_euler_bernoulli_probe_histories.csv"
    with qf_csv.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    external_csv = tmp_path / "synthetic_external_history.csv"
    qf_reactions = read_rows(package / "site_assets" / "qf_support_reaction_checkpoints.csv")
    reaction_columns = (
        "qf_reaction_fx_n", "qf_reaction_fy_n", "qf_reaction_fz_n",
        "qf_reaction_mx_nm", "qf_reaction_my_nm", "qf_reaction_mz_nm",
    )
    external_columns = (
        "reaction_fx_n", "reaction_fy_n", "reaction_fz_n",
        "reaction_mx_nm", "reaction_my_nm", "reaction_mz_nm",
    )
    external_times = np.asarray([float(row["time_s"]) for row in rows])
    with external_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("time_s", "midspan_uz_m", "tip_uz_m") + external_columns)
        for index, row in enumerate(rows):
            reaction_values = [
                np.interp(external_times[index], qf_reactions["time_s"], qf_reactions[column])
                for column in reaction_columns
            ]
            writer.writerow((row["time_s"], row["qf_midspan_uz_m"], row["qf_tip_uz_m"], *reaction_values))

    metrics = compare_histories(
        qf_csv,
        external_csv,
        tmp_path / "synthetic_metrics.json",
        tmp_path / "synthetic_comparison.png",
        package / "site_assets" / "qf_support_reaction_checkpoints.csv",
    )

    assert metrics["status"] == "DESCRIPTIVE_EXTERNAL_COMPARISON"
    assert metrics["sample_count"] == 801
    assert metrics["probes"]["tip"]["max_difference_normalized_to_qf_peak"] == pytest.approx(0.0, abs=1e-14)
    assert metrics["support_reactions"]["sample_count"] == 100
    assert metrics["support_reactions"]["components"]["force"]["max_difference_normalized_to_qf_peak"] == pytest.approx(0.0, abs=1e-14)
    assert (tmp_path / "synthetic_comparison.png").is_file()
