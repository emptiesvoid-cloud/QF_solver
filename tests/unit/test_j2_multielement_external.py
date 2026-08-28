from __future__ import annotations

import numpy as np

import solveur.verification.j2_multielement_external as campaign
from solveur.verification.j2_multielement_external import code_aster_mesh, code_aster_commands


def test_multielement_external_decks_cover_all_solid_families() -> None:
    expected = {
        "TET4": "TETRA4",
        "TET10": "TETRA10",
        "HEX8": "HEXA8",
        "HEX20": "HEXA20",
    }
    for family, keyword in expected.items():
        nodes, elements, mesh = code_aster_mesh(family, cells=2)
        assert nodes.shape[1] == 3
        assert len(elements) == (10 if family in {"TET4", "TET10"} else 2)
        assert keyword in mesh
        assert "GROUP_MA" in mesh
        assert "FIXED" in mesh
        assert "LOAD" in mesh
        load_node_count = int(np.count_nonzero(np.isclose(nodes[:, 0], 1.0)))
        commands = code_aster_commands(family, load_node_count)
        assert 'RELATION="VMIS_ISOT_LINE"' in commands
        assert 'DEFORMATION="PETIT"' in commands
        assert '"equivalent_plastic_strain"' in commands


def test_hex20_external_mesh_uses_code_aster_edge_order() -> None:
    _, _, mesh = code_aster_mesh("HEX20", cells=2)
    assert mesh.count("M1") == 2
    assert mesh.count("M2") == 2
    assert "N9\nN12\nN14\nN10" in mesh


def test_external_correlation_keeps_tet10_point_convention_open(monkeypatch) -> None:
    def fake_qf_history(element_type: str) -> list[dict[str, object]]:
        return [
            {
                "time": 0.25,
                "ux_load": 1.0,
                "reaction_x": 1.0,
                "stress_xx": 1.0,
                "equivalent_plastic_strain": 1.0,
                "integration_point_count": 4,
                "stress_xx_values": [1.0] * 4,
                "equivalent_plastic_strain_values": [1.0] * 4,
            }
        ]

    monkeypatch.setattr(campaign, "_qf_history", fake_qf_history)
    raw = {
        "elements": [
            {
                "element": element,
                "steps": [
                    {
                        "time": 0.25,
                        "ux_load": 1.0,
                        "reaction_x": 1.0,
                        "stress_xx": 1.0,
                        "equivalent_plastic_strain": 1.0,
                        "stress_xx_values": [1.0] * (5 if element == "TET10" else 4),
                        "equivalent_plastic_strain_values": [1.0] * (5 if element == "TET10" else 4),
                    }
                ],
            }
            for element in campaign.ELEMENT_TYPES
        ]
    }

    summary = campaign.evaluate_external_correlation(raw)

    assert summary["status"] == "FAIL"
    tet10 = next(row for row in summary["rows"] if row["element"] == "TET10")
    assert tet10["comparability_status"] == "OPEN_INTEGRATION_CONVENTION"
    assert tet10["integration_point_counts"]["qf"] == [4]
    assert tet10["integration_point_counts"]["code_aster_peeq"] == [5]
    assert all(item["status"] == "OPEN_COMPARABILITY" for item in summary["open_findings"])
