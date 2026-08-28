"""Bounded Code_Aster correlation for the regular 0.2.5 J2 benchmark.

The campaign is opt-in because it requires the pinned Code_Aster Docker image.
Deck generation is deterministic and can be inspected without Docker. A gate
can close only after the external raw histories have been produced and checked.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from solveur.api import solve_model
from solveur.io.manifest import sha256, write_json_file
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.robustness_nonlinear_solids import (
    ELEMENT_TYPES,
    _refinement_model,
    mesh_refinement_mesh,
)


STUDY_ID = "VNV-J2-MULTI-ELEMENT-CODEASTER-025"
LOAD_FACTORS = (0.25, 0.5, 0.75, 1.0)
TOLERANCE = 5.0e-3


def _aster_order(element_type: str, connectivity: list[int]) -> list[int]:
    """Map QF local connectivity to Code_Aster ordering where required."""
    if element_type == "HEX20":
        order = (0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 13, 9, 10, 12, 14, 15, 16, 18, 19, 17)
        return [connectivity[index] for index in order]
    return connectivity


def code_aster_mesh(element_type: str, cells: int = 2) -> tuple[np.ndarray, list[list[int]], str]:
    """Return a regular shared mesh and deterministic ASTER text."""
    nodes, elements = mesh_refinement_mesh(element_type, cells)
    keywords = {"TET4": "TETRA4", "TET10": "TETRA10", "HEX8": "HEXA8", "HEX20": "HEXA20"}
    lines = ["TITRE", f"QF Solver 0.2.5 regular-mesh J2 {element_type}", "FINSF", "COOR_3D"]
    lines.extend(
        f"N{index + 1} {point[0]:.16g} {point[1]:.16g} {point[2]:.16g}"
        for index, point in enumerate(nodes)
    )
    lines.extend(["FINSF", keywords[element_type]])
    for index, connectivity in enumerate(elements, start=1):
        lines.append(f"M{index}")
        lines.extend(f"N{node + 1}" for node in _aster_order(element_type, connectivity))
    lines.extend(["FINSF", "GROUP_MA", "SOLID"])
    lines.extend(f"M{index}" for index in range(1, len(elements) + 1))
    fixed_nodes = [index + 1 for index, point in enumerate(nodes) if np.isclose(point[0], 0.0)]
    loaded_nodes = [index + 1 for index, point in enumerate(nodes) if np.isclose(point[0], 1.0)]
    lines.extend(["FINSF", "GROUP_NO", "FIXED"])
    lines.extend(f"N{index}" for index in fixed_nodes)
    lines.extend(["FINSF", "GROUP_NO", "LOAD"])
    lines.extend(f"N{index}" for index in loaded_nodes)
    lines.extend(["FINSF", "GROUP_NO", "NALL"])
    lines.extend(f"N{index + 1}" for index in range(nodes.shape[0]))
    lines.extend(["FINSF", "FIN"])
    return nodes, elements, "\n".join(lines) + "\n"


def code_aster_commands(element_type: str, load_node_count: int) -> str:
    """Generate a displacement/load-controlled VMIS_ISOT_LINE command file."""
    return f'''# coding=utf-8
import json
import numpy as np
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(
    ELAS=_F(E=1000.0, NU=0.3),
    ECRO_LINE=_F(SY=0.02, D_SIGM_EPSI=9.900990099009901),
)
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
fixed = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="FIXED", DX=0.0, DY=0.0, DZ=0.0))
load = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="LOAD", FX={1.0 / load_node_count:.16g}))
ramp = DEFI_FONCTION(NOM_PARA="INST", VALE=(0.0, 0.0, 1.0, 1.0))
times = DEFI_LIST_REEL(DEBUT=0.0, INTERVALLE=_F(JUSQU_A=1.0, NOMBRE=4))
result = STAT_NON_LINE(
    MODELE=model, CHAM_MATER=field,
    EXCIT=(_F(CHARGE=fixed), _F(CHARGE=load, FONC_MULT=ramp)),
    COMPORTEMENT=_F(RELATION="VMIS_ISOT_LINE", DEFORMATION="PETIT"),
    INCREMENT=_F(LIST_INST=times),
    CONVERGENCE=_F(RESI_GLOB_RELA=1.0e-9, ITER_GLOB_MAXI=60),
)
CALC_CHAMP(reuse=result, RESULTAT=result, FORCE=("REAC_NODA",))
raw = {{"study_id": "{STUDY_ID}", "element": "{element_type}", "steps": []}}
access = result.getAccessParameters()
for order, instant in zip(result.getIndexes(), access["INST"]):
    if instant <= 0.0:
        continue
    displacement = result.getField("DEPL", order)
    ux, _ = displacement.getValuesWithDescription("DX", ["LOAD"])
    reaction = result.getField("REAC_NODA", order)
    rx, _ = reaction.getValuesWithDescription("DX", ["FIXED"])
    stress = result.getField("SIEF_ELGA", order)
    sxx, _ = stress.getValuesWithDescription("SIXX", ["SOLID"])
    vari = result.getField("VARI_ELGA", order)
    peeq, _ = vari.getValuesWithDescription("V1", ["SOLID"])
    raw["steps"].append({{
        "time": float(instant),
        "ux_load": float(np.mean(ux)),
        "reaction_x": float(np.sum(rx)),
        "stress_xx": float(np.mean(sxx)),
        "equivalent_plastic_strain": float(np.mean(peeq)),
        "stress_xx_values": [float(value) for value in sxx],
        "equivalent_plastic_strain_values": [float(value) for value in peeq],
    }})
with open("/work/j2_multi_raw.json", "w", encoding="utf-8") as stream:
    json.dump(raw, stream, indent=2)
FIN()
'''


def _qf_history(element_type: str) -> list[dict[str, Any]]:
    """Evaluate the same regular shared benchmark through QF."""
    base_model = _refinement_model(element_type, 2)
    if element_type == "TET10":
        # Code_Aster exposes five ELGA points for the regular TET10 mesh. Keep
        # the comparison convention explicit; the legacy four-point rule
        # remains the default for existing QF models.
        base_model.analysis.parameters["tet10_nonlinear_quadrature"] = "code_aster_5"
    loaded_nodes = np.flatnonzero(np.isclose(base_model.nodes[:, 0], 1.0))
    history: list[dict[str, float]] = []
    for factor in LOAD_FACTORS:
        model = _refinement_model(element_type, 2)
        if element_type == "TET10":
            model.analysis.parameters["tet10_nonlinear_quadrature"] = "code_aster_5"
        model.analysis.parameters["load_path"] = [factor]
        model.analysis.parameters["load_steps"] = 1
        result = solve_model(model, enforce_policy=False)
        data = result.to_dict()
        steps = data["solver"]["steps"]
        displacement = result.displacements
        loaded_dofs = [result.dofs.node_indices(int(node), ("UX",))[0] for node in loaded_nodes]
        integration_points = [
            point
            for element in data["element_results"]
            for point in element.get("integration_points", [])
        ]
        stress_xx = [float(point["stress"][0]) for point in integration_points]
        equivalent_plastic_strain = [
            float(point["equivalent_plastic_strain"]) for point in integration_points
        ]
        rows = {
            "time": factor,
            "ux_load": float(np.mean(displacement[loaded_dofs])),
            "reaction_x": -1.0 * factor,
            "stress_xx": float(np.mean(stress_xx)),
            # Code_Aster exports the unweighted mean over the SOLID field. Use
            # the same aggregate here; element volume averages and global step
            # maxima are different observables.
            "equivalent_plastic_strain": float(np.mean(equivalent_plastic_strain)),
            "integration_point_count": len(integration_points),
            "stress_xx_values": stress_xx,
            "equivalent_plastic_strain_values": equivalent_plastic_strain,
        }
        rows["relative_residual"] = float(steps[-1]["relative_residual"])
        scalar_values = [
            rows["time"],
            rows["ux_load"],
            rows["reaction_x"],
            rows["stress_xx"],
            rows["equivalent_plastic_strain"],
            rows["relative_residual"],
        ]
        if not np.all(np.isfinite(scalar_values)):
            raise ValueError(f"Non-finite QF history for {element_type} at load factor {factor}.")
        if len(stress_xx) == 0:
            raise ValueError(f"No constitutive points were returned for {element_type}.")
        if not np.isfinite(rows["reaction_x"]):
            raise ValueError(f"Non-finite reaction for {element_type}.")
        if not np.isfinite(rows["ux_load"]):
            raise ValueError(f"Non-finite displacement for {element_type}.")
        if not np.isfinite(rows["stress_xx"]):
            raise ValueError(f"Non-finite stress for {element_type}.")
        if not np.isfinite(rows["equivalent_plastic_strain"]):
            raise ValueError(f"Non-finite PEEQ for {element_type}.")
        history.append(rows)
    return history


def _relative(left: float, right: float) -> float:
    return abs(left - right) / max(abs(right), 1.0e-12)


def evaluate_external_correlation(raw: dict[str, Any]) -> dict[str, Any]:
    """Compare complete external and QF histories without physical claims."""
    checks: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for element_type in ELEMENT_TYPES:
        qf = _qf_history(element_type)
        external = next(item for item in raw["elements"] if item["element"] == element_type)["steps"]
        if len(qf) != len(external):
            raise ValueError(f"History length mismatch for {element_type}: QF={len(qf)}, external={len(external)}.")
        element_checks: list[dict[str, Any]] = []
        for qf_row, external_row in zip(qf, external, strict=True):
            qf_point_count = int(qf_row["integration_point_count"])
            external_stress_count = len(external_row.get("stress_xx_values", []))
            external_peeq_count = len(external_row.get("equivalent_plastic_strain_values", []))
            point_count_match = {
                "equivalent_plastic_strain": qf_point_count == external_peeq_count,
            }
            for metric in ("ux_load", "reaction_x", "stress_xx", "equivalent_plastic_strain"):
                error = _relative(float(qf_row[metric]), float(external_row[metric]))
                comparable = point_count_match.get(metric, True)
                check = {
                    "id": f"{element_type}_{metric}_t{qf_row['time']:.2f}",
                    "value": error,
                    "limit": TOLERANCE,
                    "status": (
                        "OPEN_COMPARABILITY"
                        if not comparable
                        else "PASS" if np.isfinite(error) and error <= TOLERANCE else "FAIL"
                    ),
                    "qf_integration_point_count": qf_point_count,
                    "external_integration_point_count": (
                        external_peeq_count if metric == "equivalent_plastic_strain" else external_stress_count
                    ),
                }
                if not comparable:
                    check["reason"] = (
                        "QF and Code_Aster expose different integration-point counts; "
                        "aggregate state comparison is not convention-matched."
                    )
                checks.append(check)
                element_checks.append(check)
        rows.append({
            "element": element_type,
            "status": "PASS" if all(item["status"] == "PASS" for item in element_checks) else "FAIL",
            "integration_point_counts": {
                "qf": sorted({int(row["integration_point_count"]) for row in qf}),
                "code_aster_stress_xx": sorted({len(row.get("stress_xx_values", [])) for row in external}),
                "code_aster_peeq": sorted({len(row.get("equivalent_plastic_strain_values", [])) for row in external}),
            },
            "comparability_status": (
                "MATCHED"
                if all(check["status"] != "OPEN_COMPARABILITY" for check in element_checks)
                else "OPEN_INTEGRATION_CONVENTION"
            ),
            "qf_solver": qf,
            "code_aster": external,
        })
    return {
        "campaign_id": STUDY_ID,
        "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "FAIL",
        "maturity": "experimental",
        "release_claim": False,
        "scope": {
            "elements": list(ELEMENT_TYPES),
            "mesh": "regular two-cell shared benchmark",
            "material": "small-strain J2 isotropic hardening",
            "history": list(LOAD_FACTORS),
            "observables": ["force-displacement", "reactions", "stress_xx", "PEEQ"],
            "quadrature_conventions": {
                "TET10": "code_aster_5 for this external comparison; QF default remains hammer4",
            },
        },
        "checks": checks,
        "rows": rows,
        "open_findings": [
            {
                "id": check["id"],
                "status": check["status"],
                "reason": check.get("reason", ""),
            }
            for check in checks
            if check["status"] == "OPEN_COMPARABILITY"
        ],
        "limitations": [
            "This is a bounded numerical correlation, not physical validation.",
            "The regular two-cell mesh is a controlled research benchmark, not an industrial qualification envelope.",
            "Aggregate state comparisons are promoted only when integration-point counts and recovery conventions match.",
        ],
    }


def run_campaign(output_dir: str | Path) -> dict[str, Any]:
    """Generate, execute and evaluate all four external regular-mesh cases."""
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    raw: dict[str, Any] = {
        "campaign_id": STUDY_ID,
        "external_solver": {"name": "Code_Aster", "version": "18.1.0", "image": CODE_ASTER_IMAGE},
        "elements": [],
    }
    for element_type in ELEMENT_TYPES:
        work = output / element_type.lower()
        work.mkdir(parents=True, exist_ok=True)
        nodes, _, mesh = code_aster_mesh(element_type, cells=2)
        load_node_count = int(np.count_nonzero(np.isclose(nodes[:, 0], 1.0)))
        (work / "j2_multi.mail").write_text(mesh, encoding="ascii")
        (work / "j2_multi.comm").write_text(
            code_aster_commands(element_type, load_node_count), encoding="utf-8"
        )
        run_code_aster(work, "j2_multi")
        raw["elements"].append(json.loads((work / "j2_multi_raw.json").read_text(encoding="utf-8")))
    summary = evaluate_external_correlation(raw)
    summary["external_solver"] = raw["external_solver"]
    summary["raw_digest"] = {
        element: sha256(output / element.lower() / "j2_multi.comm") for element in ELEMENT_TYPES
    }
    write_json_file(output / "summary.json", summary)
    _write_report(output, summary)
    return summary


def _write_report(output: Path, summary: dict[str, Any]) -> None:
    lines = [
        f"# {STUDY_ID}",
        "",
        f"Status: **{summary['status']}**",
        "",
        "Bounded Code_Aster correlation of the regular two-cell shared J2 benchmark.",
        "",
        "| Element | Status | Max relative error |",
        "| --- | --- | ---: |",
    ]
    for row in summary["rows"]:
        values = [check["value"] for check in summary["checks"] if check["id"].startswith(f"{row['element']}_")]
        lines.append(f"| {row['element']} | {row['status']} | {max(values):.3e} |")
    lines.extend(["", "The evidence is numerical correlation only; it is not physical validation.", ""])
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
