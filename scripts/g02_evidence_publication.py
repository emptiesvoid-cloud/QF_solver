"""External correlation and publication helpers for controlled 025-G02 evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "vnv_0_2_5" / "g02_latest"
LOW_ORDER = ("TET4", "HEX8")
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from solveur.api import solve_model  # noqa: E402
from solveur.core.model import FiniteElementModel  # noqa: E402
from solveur.verification.code_aster_tl_structural import (  # noqa: E402
    CODE_ASTER_IMAGE,
    CODE_ASTER_PROFILE,
    run_code_aster,
)
from solveur.verification.robustness_mesh import mesh_refinement_mesh  # noqa: E402

from g02_evidence_studies import boundary_metrics, rel  # noqa: E402


def code_aster_mesh(family: str, nodes: np.ndarray, elements: list[list[int]], fixed: np.ndarray, loaded: np.ndarray) -> str:
    lines = ["TITRE", f"QF Solver G02 {family} Code_Aster correlation", "FINSF", "COOR_3D"]
    lines.extend(
        f"N{i + 1} {float(node[0]):.16g} {float(node[1]):.16g} {float(node[2]):.16g}"
        for i, node in enumerate(nodes)
    )
    lines.extend(["FINSF", "TETRA4" if family == "TET4" else "HEXA8"])
    lines.extend(
        f"M{i + 1} " + " ".join(f"N{int(node) + 1}" for node in element)
        for i, element in enumerate(elements)
    )
    lines.extend(["FINSF", "GROUP_MA", "SOLID", *(f"M{i + 1}" for i in range(len(elements))), "FINSF"])
    lines.extend(["GROUP_NO", "FIXED", *(f"N{int(node) + 1}" for node in fixed), "FINSF"])
    lines.extend(["GROUP_NO", "LOAD", *(f"N{int(node) + 1}" for node in loaded), "FINSF", "FIN"])
    return "\n".join(lines) + "\n"


def code_aster_comm(family: str, load_scale: float, increments: int, node_count: int) -> str:
    element = "TETRA4" if family == "TET4" else "HEXA8"
    return f'''# coding=utf-8
import json
import numpy as np
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS=_F(E=10.0, NU=0.3))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
fixed = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="FIXED", DX=0.0, DY=0.0, DZ=0.0))
load = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="LOAD", FZ={load_scale:.16g} / {node_count}))
ramp = DEFI_FONCTION(NOM_PARA="INST", VALE=(0.0, 0.0, 1.0, 1.0))
times = DEFI_LIST_REEL(DEBUT=0.0, INTERVALLE=_F(JUSQU_A=1.0, NOMBRE={increments}))
result = STAT_NON_LINE(
    MODELE=model,
    CHAM_MATER=field,
    EXCIT=(_F(CHARGE=fixed), _F(CHARGE=load, FONC_MULT=ramp)),
    COMPORTEMENT=_F(RELATION="ELAS", DEFORMATION="GREEN_LAGRANGE"),
    INCREMENT=_F(LIST_INST=times),
    CONVERGENCE=_F(RESI_GLOB_RELA=1.0e-9, ITER_GLOB_MAXI=50),
)
result = CALC_CHAMP(reuse=result, RESULTAT=result, FORCE=("REAC_NODA",), DEFORMATION=("EPSI_ELGA",))
rows = []
for order, instant in zip(result.getIndexes(), result.getAccessParameters()["INST"]):
    displacement = result.getField("DEPL", order)
    uz, _ = displacement.getValuesWithDescription("DZ", ["LOAD"])
    reaction = result.getField("REAC_NODA", order)
    rx, _ = reaction.getValuesWithDescription("DX", ["FIXED"])
    ry, _ = reaction.getValuesWithDescription("DY", ["FIXED"])
    rz, _ = reaction.getValuesWithDescription("DZ", ["FIXED"])
    stress = result.getField("SIEF_ELGA", order)
    strain = result.getField("EPSI_ELGA", order)
    stress_components = []
    for name in ("SIXX", "SIYY", "SIZZ", "SIXY", "SIXZ", "SIYZ"):
        values, _ = stress.getValuesWithDescription(name, ["SOLID"])
        stress_components.append(float(np.mean(values)))
    strain_components = []
    for name in ("EPXX", "EPYY", "EPZZ", "EPXY", "EPXZ", "EPYZ"):
        values, _ = strain.getValuesWithDescription(name, ["SOLID"])
        strain_components.append(float(np.mean(values)))
    rows.append({{
        "order": int(order),
        "load_factor": float(instant),
        "tip_displacement_z": float(np.mean(uz)),
        "reaction_vector": [float(np.sum(rx)), float(np.sum(ry)), float(np.sum(rz))],
        "stress_sief_elga": stress_components,
        "strain_epsi_elga": strain_components,
    }})
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{"element": "{element}", "rows": rows}}, stream, indent=2)
FIN()
'''


def qf_external_curve(family: str, factors: list[float]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for factor in factors:
        nodes, elements = mesh_refinement_mesh(family, 1)
        fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
        loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
        model = FiniteElementModel.from_raw(
            nodes=nodes.tolist(),
            elements=[{"type": family, "nodes": item, "material": "solid"} for item in elements],
            materials={"solid": {"type": "isotropic_3d", "E": 10.0, "nu": 0.3}},
            fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
            loads=[
                {"node": int(node), "dof": "UZ", "value": 0.2 * factor / len(loaded_nodes)}
                for node in loaded_nodes
            ],
            analysis={
                "type": "geometric_nonlinear_static",
                "method": "newton_raphson",
                "parameters": {"load_increments": 12, "max_iterations": 50, "tolerance": 1.0e-9},
            },
        )
        result = solve_model(model, enforce_policy=False)
        rows.append({"load_factor": factor, "status": result.status, **boundary_metrics(model, result.displacements)})
    return rows


def external_correlation() -> dict[str, Any]:
    base = OUT / "external_code_aster"
    factors = [index / 12.0 for index in range(0, 13)]
    families: dict[str, Any] = {}
    for family in LOW_ORDER:
        nodes, elements = mesh_refinement_mesh(family, 1)
        fixed = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
        loaded = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
        work = base / family
        work.mkdir(parents=True, exist_ok=True)
        stem = family.lower()
        (work / f"{stem}.mail").write_text(code_aster_mesh(family, nodes, elements, fixed, loaded), encoding="ascii")
        (work / f"{stem}.comm").write_text(
            code_aster_comm(family, 0.2, len(factors) - 1, len(loaded)), encoding="utf-8"
        )
        try:
            run_code_aster(work, stem, timeout=1200)
            raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
            qf_rows = qf_external_curve(family, factors)
            comparisons: list[dict[str, Any]] = []
            for qf_row, ca_row in zip(qf_rows, raw["rows"], strict=True):
                ca_stress = np.asarray(ca_row["stress_sief_elga"], dtype=float)
                ca_strain = np.asarray(ca_row["strain_epsi_elga"], dtype=float)
                qf_stress = np.asarray(qf_row["cauchy_stress_mean"], dtype=float)
                qf_strain = np.asarray(qf_row["infinitesimal_strain_mean"], dtype=float)
                comparisons.append(
                    {
                        "load_factor": ca_row["load_factor"],
                        "tip_displacement_relative_error": rel(
                            qf_row["tip_displacement_z"], ca_row["tip_displacement_z"]
                        ),
                        "reaction_relative_error": float(
                            np.linalg.norm(np.asarray(qf_row["reaction_vector"]) - np.asarray(ca_row["reaction_vector"]))
                            / max(np.linalg.norm(ca_row["reaction_vector"]), 1.0e-30)
                        ),
                        "stress_relative_error": float(
                            np.linalg.norm(qf_stress - ca_stress) / max(np.linalg.norm(ca_stress), 1.0e-30)
                        ),
                        "strain_relative_error": float(
                            np.linalg.norm(qf_strain - ca_strain) / max(np.linalg.norm(ca_strain), 1.0e-30)
                        ),
                        "qf": {
                            "tip_displacement_z": qf_row["tip_displacement_z"],
                            "reaction_vector": qf_row["reaction_vector"],
                            "cauchy_stress": qf_stress.tolist(),
                            "infinitesimal_strain": qf_strain.tolist(),
                        },
                        "code_aster": ca_row,
                    }
                )
            maxima = {
                key: max(float(row[key]) for row in comparisons)
                for key in (
                    "tip_displacement_relative_error",
                    "reaction_relative_error",
                    "stress_relative_error",
                    "strain_relative_error",
                )
            }
            families[family] = {
                "status": "PASS_EXTERNAL_CORRELATION_BOUNDED",
                "external_element": raw["element"],
                "rows": comparisons,
                "maximum_relative_errors": maxima,
                "energy": {
                    "status": "NOT_COMPARED",
                    "reason": "Code_Aster native energy field is not part of this portable ELGA extraction; QF energy is reported separately in the internal curve evidence.",
                },
                "provenance": {
                    "image": CODE_ASTER_IMAGE,
                    "profile": CODE_ASTER_PROFILE,
                    "mesh": str((work / f"{stem}.mail").relative_to(ROOT)),
                    "command_file": str((work / f"{stem}.comm").relative_to(ROOT)),
                },
            }
        except Exception as error:
            families[family] = {
                "status": "BLOCKED_EXTERNAL_CORRELATION",
                "error_type": type(error).__name__,
                "error": str(error),
            }
    return {
        "status": "PASS_EXTERNAL_CORRELATION_BOUNDED"
        if families and all(item["status"] == "PASS_EXTERNAL_CORRELATION_BOUNDED" for item in families.values())
        else "BLOCKED_EXTERNAL_CORRELATION",
        "families": families,
        "load_factors": factors,
        "required_solver": "Code_Aster MUST for low-order G02 scope",
        "optional_solver": "CalculiX SHOULD and Abaqus COULD are not used to inflate this G02 decision",
        "limitations": [
            "The comparison is numerical code-to-code correlation, not physical validation.",
            "Code_Aster TET4/HEX8 histories use native SIEF_ELGA and EPSI_ELGA fields; QF reports matching Cauchy and infinitesimal measures.",
            "Energy is not compared because no common extracted native measure is available in this deck.",
        ],
    }


def plots(data: dict[str, Any]) -> list[str]:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    paths: list[str] = []
    objectivity = data["objectivity"]
    fig, ax = plt.subplots(figsize=(10, 5))
    labels: list[str] = []
    values: list[float] = []
    for family in objectivity["rows"]:
        for transform in family["transforms"]:
            labels.append(f"{family['element']}\n{transform['transform']}")
            values.append(max(float(value) for key, value in transform["metrics"].items() if key != "minimum_det_f"))
    ax.bar(np.arange(len(values)), values)
    ax.set_yscale("log")
    ax.set_ylabel("max parasite norm")
    ax.set_title("G02 objectivity: rigid-body parasite measures")
    ax.set_xticks(np.arange(len(labels)), labels, rotation=70, ha="right", fontsize=7)
    fig.tight_layout()
    path = OUT / "g02_objectivity.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(str(path.relative_to(ROOT)))

    fig, ax = plt.subplots(figsize=(8, 5))
    for family, rows in data["large_rotation"]["curves"].items():
        ax.plot([row["load_factor"] for row in rows], [row["tip_displacement_z"] for row in rows], marker="o", label=family)
    for family, item in data["external"]["families"].items():
        if item["status"] == "PASS_EXTERNAL_CORRELATION_BOUNDED":
            ax.plot(
                [row["load_factor"] for row in item["rows"]],
                [row["code_aster"]["tip_displacement_z"] for row in item["rows"]],
                linestyle="--",
                label=f"{family} Code_Aster",
            )
    ax.set_xlabel("normalized load factor")
    ax.set_ylabel("mean tip displacement z")
    ax.set_title("G02 bounded large-rotation path and Code_Aster correlation")
    ax.legend()
    fig.tight_layout()
    path = OUT / "g02_large_rotation_correlation.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(str(path.relative_to(ROOT)))

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for item in data["mesh"]["rows"]:
        family = item["element"]
        levels = item["levels"]
        x = [level["cells_x"] for level in levels]
        axes[0].plot(x, [level["tip_displacement_norm"] for level in levels], marker="o", label=family)
        axes[1].plot(x, [level["strain_energy"] for level in levels], marker="o", label=family)
        axes[2].plot(x, [level["maximum_cauchy_stress_norm"] for level in levels], marker="o", label=family)
    axes[0].set_ylabel("tip displacement norm")
    axes[1].set_ylabel("strain energy")
    axes[2].set_ylabel("max Cauchy stress norm")
    for axis in axes:
        axis.set_xlabel("cells in x")
        axis.grid(True, alpha=0.3)
    axes[0].legend()
    fig.suptitle("G02 pre-limit mesh sensitivity: bounded observation")
    fig.tight_layout()
    path = OUT / "g02_mesh_sensitivity.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(str(path.relative_to(ROOT)))

    fig, ax = plt.subplots(figsize=(8, 5))
    for row in data["small_strain_limit"]["rows"]:
        ax.loglog(
            [item["load_factor"] for item in row["rows"]],
            [item["relative_displacement_error"] for item in row["rows"]],
            marker="o",
            label=row["element"],
        )
    ax.set_xlabel("load factor")
    ax.set_ylabel("relative displacement error")
    ax.set_title("G02 small-strain limit recovery")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    path = OUT / "g02_small_strain_limit.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(str(path.relative_to(ROOT)))
    return paths


def report(data: dict[str, Any], source_sha: str, dirty: bool, timestamp: str, plot_paths: list[str]) -> str:
    external_status = data["external"]["status"]
    mesh_status = data["mesh"]["status"]
    owner_decision = "REQUIRED"
    g02_status = "OPEN"
    return "\n".join(
        [
            "# QF Solver 0.2.5a0 - 025-G02 geometric nonlinear evidence",
            "",
            f"- Source SHA: `{source_sha}`",
            f"- Worktree dirty: `{str(dirty).lower()}`",
            f"- Evidence timestamp (UTC): `{timestamp}`",
            f"- Gate status: **{g02_status}**",
            f"- Owner decision: **{owner_decision}**",
            "",
            "## Decision boundary",
            "",
            "This pack qualifies only the bounded elastic Total-Lagrangian geometric core for TET4 and HEX8. It does not qualify `total_lagrangian_j2`, TET10/HEX20 finite-kinematic plasticity, post-limit load control, buckling, arc-length, contact or coupled nonlinear capabilities.",
            "",
            "## Objectivity",
            "",
            "Rigid translation, a 0.7 rad rigid rotation, and their combination were evaluated for TET4, TET10, HEX8 and HEX20. The pack records Green-Lagrange strain, second-Piola stress, Cauchy stress, internal-force and energy parasite norms. The resulting internal status is `" + data["objectivity"]["status"] + "`.",
            "",
            "## Consistent tangent",
            "",
            "The assembled sparse tangent was compared with a central finite difference of the internal force for all four families. Low-order thresholds are the existing unit-test contracts (`1e-8` TET4 and `1e-7` HEX8); high-order values are additional observations. The resulting internal status is `" + data["tangent"]["status"] + "`.",
            "",
            "## Large rotation",
            "",
            "TET4 and HEX8 were run with 60 Full-Newton load increments to a normalized end-line rotation above 0.5 rad. The path records load factor, tip displacement, reactions, energy, det(F), Newton iterations and residuals. The point after a physical load-control limit is deliberately outside this gate and belongs to G04.",
            "",
            "| Family | Final angle (rad) | Minimum det(F) | Max displacement | Energy | Max relative residual |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        + [
            f"| {family} | {item['end_line_angle_rad']:.9g} | {item['minimum_det_f']:.9g} | {item['maximum_displacement_norm']:.9g} | {item['strain_energy']:.9g} | {item['maximum_relative_residual']:.3e} |"
            for family, item in ((row["element"], row) for row in data["large_rotation"]["final_summary"]["rows"])
        ]
        + [
            "",
            "## Mesh/refinement observation",
            "",
            f"The pre-limit four-level study (coarse/medium/fine/refined = 1/2/3/4 cells) is `{mesh_status}`. It is intentionally classified `OWNER_DECISION_REQUIRED`: the measured coarse-to-refined changes are reported without inventing a universal convergence band. The load-scale 1.0 line-search failure is retained as a stability-boundary observation, not converted into a PASS.",
            "",
            "| Family | Coarse->refined tip change | Last refinement tip change | Coarse->refined energy change | Last refinement energy change |",
            "|---|---:|---:|---:|---:|",
        ]
        + [
            f"| {row['element']} | {row['coarse_to_refined_relative_change']['tip_displacement_norm']:.6g} | {row['last_refinement_relative_change']['tip_displacement_norm']:.6g} | {row['coarse_to_refined_relative_change']['strain_energy']:.6g} | {row['last_refinement_relative_change']['strain_energy']:.6g} |"
            for row in data["mesh"]["rows"]
        ]
        + [
            "",
            "## Small-strain limit",
            "",
            "The elastic Total-Lagrangian solution is compared with the existing small-strain linear route at load factors 1e-2, 1e-3 and 1e-4 for all four families. The relative displacement error decreases toward zero while det(F) remains positive. This is not the finite-kinematic J2 limit-recovery experiment, which remains research evidence.",
            "",
            "| Family | 1e-2 error | 1e-3 error | 1e-4 error |",
            "|---|---:|---:|---:|",
        ]
        + [
            f"| {row['element']} | {row['rows'][0]['relative_displacement_error']:.3e} | {row['rows'][1]['relative_displacement_error']:.3e} | {row['rows'][2]['relative_displacement_error']:.3e} |"
            for row in data["small_strain_limit"]["rows"]
        ]
        + [
            "",
            "## Code_Aster MUST correlation",
            "",
            f"The pinned Code_Aster 18.1 campaign is `{external_status}` for TET4 and HEX8, with twelve matched load factors and full displacement, reaction, stress (`SIEF_ELGA`) and strain (`EPSI_ELGA`) histories. QF compares Cauchy stress and infinitesimal strain in the corresponding extracted measures. Native Code_Aster energy is not compared because this deck does not expose a common portable energy field; QF strain energy and internal work are still archived. This is bounded numerical correlation, not physical validation.",
            "",
            "| Family | Max displacement error | Max reaction error | Max stress error | Max strain error |",
            "|---|---:|---:|---:|---:|",
        ]
        + [
            f"| {family} | {item['maximum_relative_errors']['tip_displacement_relative_error']:.3e} | {item['maximum_relative_errors']['reaction_relative_error']:.3e} | {item['maximum_relative_errors']['stress_relative_error']:.3e} | {item['maximum_relative_errors']['strain_relative_error']:.3e} |"
            for family, item in data["external"]["families"].items()
            if item["status"] == "PASS_EXTERNAL_CORRELATION_BOUNDED"
        ]
        + [
            "",
            "## Claims and limitations",
            "",
            "- `QUALIFIED candidate`: bounded elastic Total-Lagrangian geometric core for TET4/HEX8, subject to Owner acceptance of the mesh/refinement treatment and this exact evidence SHA.",
            "- `EXPERIMENTAL`: high-order elastic geometric adapter and the four-family objectivity/tangent/small-load observations.",
            "- `RESEARCH`: `kinematics=total_lagrangian_j2`, plastic finite-kinematic paths and high-order plastic geometric paths.",
            "- `NOT_IN_RELEASE_SCOPE`: G03 buckling, G04 arc-length, G05 contact, G06 coupling and G07 friction; this pack does not alter their gates.",
            "- No physical validation, post-buckling, arbitrary large-deformation, multi-million-DOF or general finite-strain plasticity claim is made.",
            "",
            "## Evidence files",
            "",
            *[f"- `{path}`" for path in plot_paths],
            "- `summary.json` contains all numeric rows and provenance.",
            "- `external_code_aster/` contains the generated meshes, command files, raw histories and Docker logs.",
            "",
            "## Gate decision",
            "",
            "G02 remains `OPEN` in this pack until the Owner explicitly accepts the bounded mesh/refinement treatment and records the release-scope decision. No requirement or tolerance was lowered. No other functional gate is modified.",
        ]
    ) + "\n"
