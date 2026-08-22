"""Same-mesh Code_Aster TETRA10 static correlation for a supplied model."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from solveur.api import solve_model
from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.paths import project_root
from solveur.verification.code_aster_tet10_dynamic import _code_aster_tet_mesh
from solveur.verification.code_aster_tl_structural import CODE_ASTER_IMAGE, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


class CodeAsterTet10StaticCampaign:
    """Compare QF_solver TET10 and Code_Aster TETRA10 on the same JSON model."""

    study_id = "VNV-TET10-STATIC-CODEASTER-TETRA10-029"
    relative_limit = 0.01

    def __init__(
        self,
        model_path: str | Path,
        output_dir: str | Path,
        *,
        tet4_summary_path: str | Path | None = None,
        publish_reference: bool = True,
    ) -> None:
        self.model_path = Path(model_path).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.tet4_summary_path = (
            Path(tet4_summary_path).resolve() if tet4_summary_path is not None else None
        )
        self.publish_reference = bool(publish_reference)

    def run(self) -> dict[str, Any]:
        raw = json.loads(self.model_path.read_text(encoding="utf-8"))
        model = JsonModelReader().from_dict(raw)
        if {str(element.type).upper() for element in model.elements} != {"TET10"}:
            raise ValueError("The supplied static correlation model must contain TET10 elements only.")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        root = _root_nodes(raw)
        tip = _tip_nodes(model.nodes, model.nodes[:, 0].max())
        if root.size == 0 or tip.size == 0:
            raise ValueError("The model must provide a detectable clamped root and loaded tip.")

        qf_result = solve_model(model, enforce_policy=False)
        qf_tip = _mean_tip_displacement(qf_result, model, tip)
        work = self.output_dir / "code_aster"
        work.mkdir(parents=True, exist_ok=True)
        (work / "tet10_static.mail").write_text(
            _code_aster_tet_mesh(model.nodes, model.elements, root, tip, "TETRA10", "TET10"),
            encoding="ascii",
        )
        material = _material_parameters(raw, model.elements[0].material)
        (work / "tet10_static.comm").write_text(
            _static_comm(material[0], material[1], raw.get("loads", []), tip),
            encoding="utf-8",
        )
        run_code_aster(work, "tet10_static", timeout=1800)
        raw_external = json.loads((work / "code_aster_raw.json").read_text(encoding="utf-8"))
        aster_tip = float(raw_external["tip_uz_m"])
        relative_difference = _relative(qf_tip, aster_tip)
        tet4_reference = self._tet4_reference(len(model.elements), qf_tip, aster_tip)
        checks = [
            _check("same_mesh", True, True),
            _check("finite_results", np.isfinite(qf_tip) and np.isfinite(aster_tip), True),
            _check("relative_difference", relative_difference, self.relative_limit),
        ]
        summary: dict[str, Any] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION"
            if all(item["status"] == "PASS" for item in checks)
            else "WARNING",
            "maturity": "stable_candidate",
            "scope": "isotropic small-strain TET10/TETRA10 linear static same-mesh correlation",
            "input_model": str(self.model_path.relative_to(project_root())),
            "external_solver": {
                "name": "Code_Aster",
                "version": "18.1.0",
                "image": CODE_ASTER_IMAGE,
                "element": "3D/TETRA10",
            },
            "model": {
                "node_count": model.node_count,
                "element_count": len(model.elements),
                "root_node_count": int(root.size),
                "tip_node_count": int(tip.size),
                "same_mesh": True,
                "observable": "mean UZ over loaded end-face nodes",
            },
            "qf_tip_uz_m": qf_tip,
            "code_aster_tip_uz_m": aster_tip,
            "relative_difference": relative_difference,
            "tet4_reference": tet4_reference,
            "checks": checks,
            "limitations": [
                "The comparison covers only isotropic small-strain TET10/TETRA10 linear statics.",
                "The supplied load and boundary groups are part of the model-specific evidence contract.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        if self.publish_reference:
            self._publish_reference()
        return summary

    def _tet4_reference(
        self, element_count: int, qf_tet10_tip: float, aster_tet10_tip: float
    ) -> dict[str, Any] | None:
        if self.tet4_summary_path is None:
            return None
        source = json.loads(self.tet4_summary_path.read_text(encoding="utf-8"))
        rows = [row for row in source.get("rows", []) if int(row.get("tet4_elements", -1)) == element_count]
        if not rows:
            raise ValueError(f"No TET4 row with {element_count} elements in {self.tet4_summary_path}.")
        qf_tet4_tip = float(rows[-1]["tet4_tip_uz_m"])
        try:
            source_name = str(self.tet4_summary_path.relative_to(project_root()))
        except ValueError:
            source_name = str(self.tet4_summary_path)
        return {
            "source": source_name,
            "qf_tet4_tip_uz_m": qf_tet4_tip,
            "qf_tet10_tip_uz_m": qf_tet10_tip,
            "code_aster_tet10_tip_uz_m": aster_tet10_tip,
            "qf_tet4_to_code_aster_tetra10_difference": _relative(qf_tet4_tip, aster_tet10_tip),
        }

    def _publish_reference(self) -> None:
        target = project_root() / "qualification" / "vnv" / "external" / "code_aster_tet10_static" / "reference"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(self.output_dir, target)


def _root_nodes(raw: dict[str, Any]) -> np.ndarray:
    components = {"UX", "UY", "UZ"}
    by_node: dict[int, set[str]] = {}
    for item in raw.get("fixed_dofs", []):
        by_node.setdefault(int(item["node"]), set()).update(
            str(dof).upper() for dof in item.get("dofs", [])
        )
    return np.asarray(
        sorted(node for node, node_components in by_node.items() if components.issubset(node_components)),
        dtype=int,
    )


def _tip_nodes(nodes: np.ndarray, maximum_x: float) -> np.ndarray:
    return np.flatnonzero(np.isclose(nodes[:, 0], maximum_x, atol=1.0e-10)).astype(int)


def _material_parameters(raw: dict[str, Any], name: str) -> tuple[float, float]:
    material = raw.get("materials", {}).get(name, {})
    return float(material["E"]), float(material["nu"])


def _mean_tip_displacement(result: Any, model: Any, tip: np.ndarray) -> float:
    dofs = model.dof_manager()
    values = np.asarray(result.displacements, dtype=float)
    return float(np.mean([values[dofs.index(int(node), "UZ")] for node in tip]))


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), 1.0e-30)


def _check(identifier: str, value: object, limit: object) -> dict[str, object]:
    if isinstance(limit, bool):
        normalized_value = bool(value)
        passed = normalized_value == limit
    else:
        normalized_value = float(value)
        passed = bool(normalized_value <= float(limit))
    return {"id": identifier, "value": normalized_value, "limit": limit, "status": "PASS" if passed else "FAIL"}


def _static_comm(young: float, poisson: float, loads: list[dict[str, Any]], tip: np.ndarray) -> str:
    terms = []
    for load in loads:
        component = str(load["dof"]).upper()
        force_name = {"UX": "FX", "UY": "FY", "UZ": "FZ"}.get(component)
        if force_name is None:
            raise ValueError(f"Unsupported static TET10 load component: {component}")
        terms.append(f'_F(NOEUD="N{int(load["node"]) + 1}", {force_name}={float(load["value"]):.16g})')
    if not terms:
        raise ValueError("The TET10 static correlation model has no nodal loads.")
    load_text = ",\n    ".join(terms)
    return f'''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS=_F(E={young:.16g}, NU={poisson:.16g}))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="ROOT", DX=0.0, DY=0.0, DZ=0.0))
force = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=(
    {load_text}
))
static = MECA_STATIQUE(MODELE=model, CHAM_MATER=field, EXCIT=(_F(CHARGE=boundary), _F(CHARGE=force)))
values, _ = static.getField("DEPL", 1).getValuesWithDescription("DZ", ["TIP"])
with open("/work/code_aster_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{"tip_uz_m": float(sum(values) / len(values))}}, stream, indent=2)
FIN()
'''


def _report(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut automatise : **{summary['status']}**.",
        "",
        "| Observable | QF_solver TET10 | Code_Aster TETRA10 | Ecart relatif |",
        "| --- | ---: | ---: | ---: |",
        f"| UZ pointe [m] | {summary['qf_tip_uz_m']:.9e} | {summary['code_aster_tip_uz_m']:.9e} | {100.0 * summary['relative_difference']:.6g} % |",
        "",
        "La comparaison est realisee sur la connectivite, les coordonnees, les blocages et les charges identiques.",
        "",
    ]
    return "\n".join(lines)
