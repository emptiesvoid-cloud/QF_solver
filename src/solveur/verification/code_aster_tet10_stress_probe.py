"""Distance-controlled TET10 stress-field correlation against Code_Aster."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.io.manifest import write_json_file
from solveur.verification.code_aster_tet10_block_dynamic import (
    CodeAsterTet10BlockDynamicsCampaign,
)
from solveur.verification.code_aster_tet10_dynamic import CodeAsterTet10DynamicsCampaign
from solveur.verification.code_aster_tet10_cylinder_dynamic import (
    CodeAsterTet10CylinderDynamicsCampaign,
)
from solveur.verification.code_aster_tet10_dynamic import (
    _code_aster_tet_mesh,
)
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


class CodeAsterTet10StressProbeCampaign:
    """Compare interior TET10 stress averages, excluding singular boundaries."""

    study_id = "VNV-TET10-STRESS-PROBE-CODEASTER-TETRA10-BLOCK-026"
    mesh_size = 0.32
    probe_margin = 0.20
    relative_limit = 0.10

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        campaign = self._build_campaign()
        model, root, tip = campaign._model(
            self.mesh_size, "linear_static", total_load=-1.0
        )
        qf = solve_model(model, enforce_policy=False)
        probe = self._select_probes(model)
        qf_stress = np.mean(
            [np.asarray(qf.element_results[index]["stress"], dtype=float) for index in probe],
            axis=0,
        )
        mesh_text = _probe_mesh(model, root, tip, probe)
        (self.output_dir / "tet10_stress_probe.mail").write_text(mesh_text, encoding="ascii")
        (self.output_dir / "tet10_stress_probe.comm").write_text(
            _stress_comm(tip, campaign._tip_load_weights), encoding="utf-8"
        )
        self._run_code_aster()
        raw = json.loads(
            (self.output_dir / "code_aster_stress_probe_raw.json").read_text(
                encoding="utf-8"
            )
        )
        aster_stress = np.asarray(raw["stress_pa"], dtype=float)
        error = _relative_norm(qf_stress, aster_stress)
        summary = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if error <= self.relative_limit else "WARNING",
            "maturity": "experimental",
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "element": "3D/TETRA10",
            },
            "model": {
                "nodes": model.node_count,
                "elements": len(model.elements),
                "mesh_size": self.mesh_size,
                "load": "top-face resultant FZ=-1 N",
                "fixed_boundary": "bottom face",
            },
            "observable": {
                "type": "mean_element_stress_vector",
                "components": ["SIXX", "SIYY", "SIZZ", "SIXY", "SIYZ", "SIXZ"],
                "probe_margin_fraction": self.probe_margin,
                "probe_element_indices": probe,
                "singular_boundaries_excluded": True,
                "qf_solver_pa": qf_stress.tolist(),
                "code_aster_pa": aster_stress.tolist(),
                "relative_l2_difference": error,
            },
            "criteria": {
                "relative_l2_difference_max": self.relative_limit,
                "status": "PASS" if error <= self.relative_limit else "WARNING",
            },
            "limitations": [
                "The scalar is an interior-element average, not a pointwise peak stress.",
                "The current proof is isotropic, small-strain and linear static.",
                "Surface singularities at the bottom clamp and top load are excluded by construction.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        _plot(self.output_dir, qf_stress, aster_stress)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _select_probes(self, model: Any) -> list[int]:
        centers = np.asarray(
            [np.mean(model.nodes[list(element.nodes)], axis=0) for element in model.elements]
        )
        lower = centers.min(axis=0) + self.probe_margin * (centers.max(axis=0) - centers.min(axis=0))
        upper = centers.max(axis=0) - self.probe_margin * (centers.max(axis=0) - centers.min(axis=0))
        selected = np.flatnonzero(np.all((centers >= lower) & (centers <= upper), axis=1))
        if selected.size < 3:
            distances = np.linalg.norm(centers - 0.5, axis=1)
            selected = np.argsort(distances)[:3]
        return [int(index) for index in selected]

    def _build_campaign(self) -> Any:
        return CodeAsterTet10BlockDynamicsCampaign(
            self.output_dir / "model", mesh_size=self.mesh_size
        )

    def _run_code_aster(self) -> None:
        run_code_aster(self.output_dir, "tet10_stress_probe", timeout=900)


def _probe_mesh(model: Any, root: np.ndarray, tip: np.ndarray, probe: list[int]) -> str:
    text = _code_aster_tet_mesh(
        model.nodes,
        model.elements,
        root,
        tip,
        "TETRA10",
        "TET10",
    )
    names = "\n".join(f"M{index + 1}" for index in probe)
    return text.replace(
        "\nGROUP_NO\nROOT",
        f"\nGROUP_MA\nPROBE\n{names}\nFINSF\nGROUP_NO\nROOT",
        1,
    )


def _stress_comm(tip: np.ndarray, weights: np.ndarray | None) -> str:
    load_weights = np.full(tip.size, 1.0 / tip.size) if weights is None else weights
    load_rows = ",\n    ".join(
        f'_F(NOEUD="N{int(node) + 1}", FZ={-float(weight):.16g})'
        for node, weight in zip(tip, load_weights, strict=True)
    )
    return '''# coding=utf-8
import json
import numpy as np
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS=_F(E=7.0e10, NU=0.3, RHO=2700.0))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="ROOT", DX=0.0, DY=0.0, DZ=0.0))
force = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=(
    __LOAD_ROWS__
))
result = MECA_STATIQUE(MODELE=model, CHAM_MATER=field, EXCIT=(
    _F(CHARGE=boundary), _F(CHARGE=force)
))
order = result.getIndexes()[-1]
stress = result.getField("SIEF_ELGA", order)
components = []
for name in ("SIXX", "SIYY", "SIZZ", "SIXY", "SIYZ", "SIXZ"):
    values, _ = stress.getValuesWithDescription(name, ["PROBE"])
    components.append(float(np.mean(values)))
with open("/work/code_aster_stress_probe_raw.json", "w", encoding="utf-8") as stream:
    json.dump({"stress_pa": components}, stream, indent=2)
FIN()
'''.replace("__LOAD_ROWS__", load_rows)


class CodeAsterTet10CantileverStressProbeCampaign(CodeAsterTet10StressProbeCampaign):
    """Run the same interior stress observable on a rectangular cantilever."""

    study_id = "VNV-TET10-STRESS-PROBE-CODEASTER-TETRA10-CANTILEVER-027"
    mesh_size = 0.60

    def _build_campaign(self) -> Any:
        return CodeAsterTet10DynamicsCampaign(
            self.output_dir / "model",
            mesh_size=self.mesh_size,
            length=4.0,
            width=0.4,
            height=0.4,
        )


class CodeAsterTet10CylinderStressProbeCampaign(CodeAsterTet10StressProbeCampaign):
    """Run the same interior stress observable on a faceted circular shaft."""

    study_id = "VNV-TET10-STRESS-PROBE-CODEASTER-TETRA10-CYLINDER-028"
    mesh_size = 0.32

    def _build_campaign(self) -> Any:
        return CodeAsterTet10CylinderDynamicsCampaign(
            self.output_dir / "model", mesh_size=self.mesh_size
        )


def _relative_norm(first: np.ndarray, second: np.ndarray) -> float:
    return float(np.linalg.norm(first - second) / max(np.linalg.norm(second), 1.0e-30))


def _plot(output: Path, qf: np.ndarray, aster: np.ndarray) -> None:
    labels = ["SIXX", "SIYY", "SIZZ", "SIXY", "SIYZ", "SIXZ"]
    figure, axis = plt.subplots(figsize=(10.0, 5.5))
    positions = np.arange(len(labels))
    axis.bar(positions - 0.18, qf / 1.0e6, width=0.36, label="QF_solver")
    axis.bar(positions + 0.18, aster / 1.0e6, width=0.36, label="Code_Aster")
    axis.set_xticks(positions, labels)
    axis.set_ylabel("Contrainte moyenne [MPa]")
    axis.set_title("TET10 : contraintes sur elements interieurs")
    axis.grid(axis="y", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output / "stress_probe_comparison.png", dpi=180)
    plt.close(figure)


def _report(summary: dict[str, Any]) -> str:
    observable = summary["observable"]
    return "\n".join(
        [
            f"# {summary['study_id']}",
            "",
            f"Statut : **{summary['status']}**.",
            "",
            f"Ecart L2 relatif sur la moyenne des elements interieurs : `{100.0 * observable['relative_l2_difference']:.5g} %`.",
            "Les elements proches du blocage et du chargement sont exclus de l'observable.",
            "",
            "| Composante | QF_solver [MPa] | Code_Aster [MPa] |",
            "| --- | ---: | ---: |",
            *[
                f"| {label} | {float(first) / 1e6:.6g} | {float(second) / 1e6:.6g} |"
                for label, first, second in zip(
                    observable["components"], observable["qf_solver_pa"], observable["code_aster_pa"], strict=True
                )
            ],
            "",
            "![Comparaison des contraintes](stress_probe_comparison.png)",
        ]
    )
