"""Controlled Code_Aster comparison for the regularized Coulomb contact law."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


class CodeAsterFrictionContactCampaign:
    """Compare a three-node regularized Coulomb problem with Code_Aster.

    Code_Aster uses its documented ``CONTINUE`` Coulomb contact with normal and
    tangential penalties. QF_solver retains its exact normal multiplier and
    regularized tangential return mapping. Consequently, this campaign checks
    branch selection and engineering observables with a declared penalty
    tolerance; it is not a claim of identical contact discretizations.
    """

    study_id = "VNV-CONTACT-FRICTION-CODEASTER-CONTINUE-003"
    _gap = 0.1
    _normal_load = -200.0
    _normal_stiffness = 1.0e8
    _structural_stiffness = 1000.0
    _tangential_stiffness = 10000.0
    _friction = 0.5

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        """Run the saturated sliding case through the pinned Docker image."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = [
            self._run_case(identifier, load_x, self._tangential_stiffness, "slip")
            for identifier, load_x in (
                ("slip_200", 200.0),
                ("slip_250", 250.0),
                ("slip_300", 300.0),
            )
        ]
        checks = self._checks(rows)
        summary: dict[str, Any] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if all(row["status"] == "PASS" for row in checks) else "FAIL",
            "maturity": "experimental",
            "scope": "linear_static_regularized_coulomb_saturated_sliding",
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "formulation": "DEFI_CONTACT / CONTINUE / COULOMB",
                "normal_penalty_n_per_m": self._normal_stiffness,
                "tangential_penalty_n_per_m": self._tangential_stiffness,
            },
            "model": {
                "initial_normal_gap_m": self._gap,
                "normal_load_n": self._normal_load,
                "structural_spring_n_per_m": self._structural_stiffness,
                "friction_coefficient": self._friction,
                "same_loads_and_units": True,
            },
            "load_level_count": len(rows),
            "cases": rows,
            "checks": checks,
            "limitations": [
                "QF_solver uses an exact normal multiplier; Code_Aster CONTINUE uses declared penalties.",
                "The comparison is a controlled point/contact-law correlation, not a surface-to-surface validation.",
                "The elastic stick branch is not compared because Code_Aster's tangential penalty is not identical to QF_solver's return-map regularization.",
                "Large sliding, updated normals, multiple contacts and dynamic contact are outside this study.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(rows)
        (self.output_dir / "report.md").write_text(self._markdown(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _run_case(
        self,
        identifier: str,
        load_x: float,
        tangential_penalty: float,
        expected_state: str,
    ) -> dict[str, Any]:
        work = self.output_dir / identifier
        work.mkdir(exist_ok=True)
        qf = LinearStaticSolver().solve(JsonModelReader().from_dict(_qf_model(load_x)))
        qf_contacts = qf.solver["contact"]["contacts"]
        qf_ux = float(np.mean([qf.displacements[qf.dofs.index(node, "UX")] for node in (3, 4, 5)]))
        qf_uz = float(np.mean([qf.displacements[qf.dofs.index(node, "UZ")] for node in (3, 4, 5)]))
        (work / f"{identifier}.mail").write_text(surface_pair_mesh(), encoding="ascii")
        (work / f"{identifier}.comm").write_text(
            friction_contact_comm(load_x, tangential_penalty), encoding="utf-8"
        )
        run_code_aster(work, identifier)
        raw = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
        aster_ux = float(raw["ux_m"])
        aster_uz = float(raw["uz_m"])
        return {
            "id": identifier,
            "load_x_n": load_x,
            "load_z_n": self._normal_load,
            "code_aster_tangential_penalty_n_per_m": tangential_penalty,
            "expected_state": expected_state,
            "qf_state": _common_state(qf_contacts),
            "qf_ux_m": qf_ux,
            "qf_uz_m": qf_uz,
            "qf_tangential_force_n": float(sum(float(row["tangential_force_norm"]) for row in qf_contacts)),
            "qf_friction_limit_n": float(sum(float(row["friction_limit"]) for row in qf_contacts)),
            "code_aster_ux_m": aster_ux,
            "code_aster_uz_m": aster_uz,
            "qf_code_aster_ux_difference": _relative(qf_ux, aster_ux),
            "qf_code_aster_uz_difference": _relative(qf_uz, aster_uz),
        }

    @staticmethod
    def _checks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []
        for slip in rows:
            identifier = str(slip["id"])
            checks.extend(
                [
                    _upper(f"{identifier}_qf_code_aster_ux", float(slip["qf_code_aster_ux_difference"]), 0.02),
                    _upper(f"{identifier}_normal_penalty_displacement", abs(float(slip["qf_code_aster_uz_difference"])), 1.0e-3),
                    {
                        "id": f"{identifier}_qf_slip_branch",
                        "value": float(int(slip["qf_state"] != "slip")),
                        "limit": 0.0,
                        "status": "PASS" if slip["qf_state"] == "slip" else "FAIL",
                    },
                    _upper(
                        f"{identifier}_qf_slip_coulomb_limit",
                        abs(float(slip["qf_tangential_force_n"]) - float(slip["qf_friction_limit_n"])),
                        1.0e-8,
                    ),
                ]
            )
        return checks

    def _plot(self, rows: list[dict[str, Any]]) -> None:
        labels = [str(row["id"]) for row in rows]
        x: np.ndarray = np.arange(len(rows), dtype=float)
        figure, axis = plt.subplots(figsize=(7.2, 4.2), constrained_layout=True)
        axis.bar(x - 0.17, [float(row["qf_ux_m"]) for row in rows], 0.34, label="QF_solver")
        axis.bar(x + 0.17, [float(row["code_aster_ux_m"]) for row in rows], 0.34, label="Code_Aster")
        axis.set(xticks=x, xticklabels=labels, ylabel="UX esclave [m]")
        axis.grid(True, axis="y", alpha=0.3)
        axis.legend()
        figure.savefig(self.output_dir / "code_aster_friction_comparison.png", dpi=180)
        plt.close(figure)

    def _markdown(self, summary: dict[str, Any]) -> str:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut automatise : **{summary['status']}**.",
            "",
            "Code_Aster est execute avec l'image Docker epinglee, son contact "
            "continu de Coulomb et les penalites declarees dans `summary.json`. "
            "QF_solver conserve sa contrainte normale exacte : les ecarts attendus "
            "en `UZ` sont donc controles separement.",
            "",
            "| Cas | Etat QF | UX QF [m] | UX Aster [m] | Ecart UX | UZ QF [m] | UZ Aster [m] |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in summary["cases"]:
            lines.append(
                f"| {row['id']} | {row['qf_state']} | {float(row['qf_ux_m']):.10g} | "
                f"{float(row['code_aster_ux_m']):.10g} | {100 * float(row['qf_code_aster_ux_difference']):.4g} % | "
                f"{float(row['qf_uz_m']):.10g} | {float(row['code_aster_uz_m']):.10g} |"
            )
        lines.extend([
            "",
            "![Comparaison de glissement](code_aster_friction_comparison.png)",
            "",
            "## Limites",
            "",
            "Cette correlation ne couvre que le glissement sature. La branche d'adhesion "
            "n'est pas comparable par simple calibration de penalite : les essais Code_Aster "
            "montrent aussi un decalage de branche. Elle ne valide pas des surfaces deformables "
            "ni le grand glissement.",
            "",
        ])
        return "\n".join(lines)


def surface_pair_mesh() -> str:
    """Return coincidently oriented master/slave triangular surface groups."""
    return """TITRE\nQF_solver regularized Coulomb external correlation\nFINSF\nCOOR_3D\nM1 -1.0 -1.0 0.0\nM2 1.0 -1.0 0.0\nM3 -1.0 1.0 0.0\nS1 -0.3 -0.3 0.1\nS2 -0.1 -0.3 0.1\nS3 -0.1 -0.1 0.1\nG1 -0.3 -0.3 1.0\nG2 -0.1 -0.3 1.0\nG3 -0.1 -0.1 1.0\nFINSF\nTRIA3\nE1 M1 M2 M3\nE2 S1 S2 S3\nFINSF\nSEG2\nR1 S1 G1\nR2 S2 G2\nR3 S3 G3\nFINSF\nGROUP_MA\nMASTER_SURFACE\nE1\nFINSF\nGROUP_MA\nSLAVE_SURFACE\nE2\nFINSF\nGROUP_MA\nSLAVE_SPRINGS\nR1 R2 R3\nFINSF\nGROUP_NO\nMASTER_NO\nM1 M2 M3\nFINSF\nGROUP_NO\nSLAVE_NO\nS1 S2 S3\nFINSF\nGROUP_NO\nGROUND_NO\nG1 G2 G3\nFINSF\nFIN\n"""


def friction_contact_comm(load_x_n: float, tangential_penalty: float = 10000.0) -> str:
    """Return the pinned Code_Aster discrete Coulomb deck for one load level."""
    return f'''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=(
    _F(GROUP_MA=("MASTER_SURFACE", "SLAVE_SURFACE"), PHENOMENE="MECANIQUE", MODELISATION="DKT"),
    _F(GROUP_MA="SLAVE_SPRINGS", PHENOMENE="MECANIQUE", MODELISATION="DIS_TR"),
))
material = DEFI_MATERIAU(ELAS=_F(E=1.0e-3, NU=0.3))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA=("MASTER_SURFACE", "SLAVE_SURFACE"), MATER=material))
stiffness = AFFE_CARA_ELEM(
    MODELE=model,
    COQUE=_F(GROUP_MA=("MASTER_SURFACE", "SLAVE_SURFACE"), EPAIS=1.0),
    DISCRET=_F(GROUP_MA="SLAVE_SPRINGS", REPERE="GLOBAL", CARA="K_TR_D_L", VALE=(1000.0 / 3.0, 0.0, 1000.0 / 3.0, 0.0, 0.0, 0.0)),
)
fixed = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=(
    _F(GROUP_NO="MASTER_NO", DX=0.0, DY=0.0, DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0),
    _F(GROUP_NO="SLAVE_NO", DY=0.0, DRX=0.0, DRY=0.0, DRZ=0.0),
    _F(GROUP_NO="GROUND_NO", DX=0.0, DY=0.0, DZ=0.0, DRX=0.0, DRY=0.0, DRZ=0.0),
))
load = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=_F(GROUP_NO="SLAVE_NO", FX={load_x_n / 3.0:.16g}, FZ=-200.0 / 3.0))
contact = DEFI_CONTACT(
    MODELE=model,
    FORMULATION="CONTINUE",
    FROTTEMENT="COULOMB",
    ALGO_RESO_GEOM="POINT_FIXE", REAC_GEOM="SANS",
    ALGO_RESO_CONT="NEWTON", ALGO_RESO_FROT="NEWTON",
    ZONE=_F(
        GROUP_MA_MAIT="MASTER_SURFACE", GROUP_MA_ESCL="SLAVE_SURFACE",
        VECT_MAIT="FIXE", MAIT_FIXE=(0.0, 0.0, 1.0), CONTACT_INIT="NON",
        ALGO_CONT="PENALISATION", ALGO_FROT="PENALISATION", ADAPTATION="NON",
        COEF_PENA_CONT=1.0e8, COEF_PENA_FROT={tangential_penalty:.16g}, COULOMB=0.5,
    ),
)
times = DEFI_LIST_REEL(DEBUT=0.0, INTERVALLE=_F(JUSQU_A=1.0, NOMBRE=10))
result = STAT_NON_LINE(
    MODELE=model, CHAM_MATER=field, CARA_ELEM=stiffness,
    EXCIT=(_F(CHARGE=fixed), _F(CHARGE=load)), CONTACT=contact,
    COMPORTEMENT=_F(RELATION="ELAS"), INCREMENT=_F(LIST_INST=times),
    NEWTON=_F(MATRICE="TANGENTE", REAC_ITER=1),
    CONVERGENCE=_F(RESI_GLOB_RELA=1.0e-10, ITER_GLOB_MAXI=50),
)
order = result.getIndexes()[-1]
displacement = result.getField("DEPL", order)
ux, _ = displacement.getValuesWithDescription("DX", ["SLAVE_NO"])
uz, _ = displacement.getValuesWithDescription("DZ", ["SLAVE_NO"])
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{"ux_m": float(sum(ux) / len(ux)), "uz_m": float(sum(uz) / len(uz))}}, stream, indent=2)
FIN()
'''


def _qf_model(load_x_n: float) -> dict[str, object]:
    return {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 30},
        "nodes": [[-1.0, -1.0, 0.0], [1.0, -1.0, 0.0], [-1.0, 1.0, 0.0], [-0.3, -0.3, 0.1], [-0.1, -0.3, 0.1], [-0.1, -0.1, 0.1]],
        "elements": [], "materials": {},
        "fixed_dofs": [
            {"node": 0, "dofs": ["UX", "UY", "UZ"]}, {"node": 1, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]}, {"node": 3, "dofs": ["UY"]},
            {"node": 4, "dofs": ["UY"]}, {"node": 5, "dofs": ["UY"]},
        ],
        "springs": [{"node_a": node, "dofs": ["UX", "UZ"], "stiffness": [1000.0 / 3.0, 1000.0 / 3.0]} for node in (3, 4, 5)],
        "loads": [item for node in (3, 4, 5) for item in (
            {"node": node, "dof": "UX", "value": load_x_n / 3.0}, {"node": node, "dof": "UZ", "value": -200.0 / 3.0},
        )],
        "contacts": [{
            "name": f"rough_plane_{node}", "slave_node": node, "master_nodes": [0, 1, 2],
            "friction_coefficient": 0.5, "tangential_stiffness": 10000.0 / 3.0,
        } for node in (3, 4, 5)],
    }


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), 1.0e-12)


def _common_state(rows: object) -> str:
    """Return the common QF contact state, rejecting nonuniform branches."""
    if not isinstance(rows, list) or not rows:
        return "invalid"
    states = {str(row.get("tangential_state", "invalid")) for row in rows if isinstance(row, dict)}
    return states.pop() if len(states) == 1 else "mixed"


def _upper(identifier: str, value: float, limit: float) -> dict[str, Any]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL"}
