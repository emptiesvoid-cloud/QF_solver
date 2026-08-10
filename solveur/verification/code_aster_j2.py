"""Code_Aster VMIS_ISOT_LINE correlation for the isotropic J2 material law."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import numpy as np

from solveur.io.manifest import write_json_file
from solveur.materials.solid import VonMisesElastoplasticMaterial
from solveur.verification.code_aster_tl_structural import code_aster_mesh, run_code_aster
from solveur.verification.vnv_manifest import write_vnv_manifest


class CodeAsterJ2Campaign:
    """Compare one affine uniaxial plastic state with Code_Aster 18.1.0."""

    study_id = "VNV-J2-CODEASTER-VMIS-ISOT-LINE-004"
    young_mpa = 210_000.0
    poisson = 0.3
    yield_stress_mpa = 250.0
    hardening_mpa = 50_000.0
    target_stress_mpa = 300.0

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        nodes, elements = unit_cube_tet4_mesh()
        axial_strain, lateral_strain = self._theoretical_strains()
        displacements = nodes * np.array([axial_strain, lateral_strain, lateral_strain])
        work = self.output_dir / "code_aster"
        work.mkdir(exist_ok=True)
        (work / "j2_patch.mail").write_text(
            code_aster_mesh(nodes, elements, list(range(1, nodes.shape[0] + 1))),
            encoding="ascii",
        )
        (work / "j2_patch.comm").write_text(
            code_aster_j2_commands(displacements, self),
            encoding="utf-8",
        )
        run_code_aster(work, "j2_patch")
        raw = json.loads((work / "code_aster_j2_raw.json").read_text(encoding="utf-8"))
        summary = evaluate_code_aster_j2(raw, self)
        write_json_file(self.output_dir / "summary.json", summary)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _theoretical_strains(self) -> tuple[float, float]:
        plastic = (self.target_stress_mpa - self.yield_stress_mpa) / self.hardening_mpa
        axial = self.target_stress_mpa / self.young_mpa + plastic
        lateral = -self.poisson * self.target_stress_mpa / self.young_mpa - 0.5 * plastic
        return axial, lateral

    @property
    def code_aster_tangent_mpa(self) -> float:
        """Convert plastic hardening H to Code_Aster's total uniaxial tangent."""
        return self.young_mpa * self.hardening_mpa / (self.young_mpa + self.hardening_mpa)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "Patch affine TET4 impose comparant QF_solver, la solution bilineaire "
            "uniaxiale et Code_Aster 18.1.0 `VMIS_ISOT_LINE`.",
            "",
            "| Verification | Valeur | Limite | Statut |",
            "| --- | ---: | ---: | --- |",
        ]
        checks = cast(list[dict[str, Any]], summary["checks"])
        for check in checks:
            lines.append(
                f"| {check['id']} | {check['value']:.6e} | "
                f"{check['limit']:.6e} | {check['status']} |"
            )
        lines.extend(
            [
                "",
                "## Domaine couvert",
                "",
                "- petites deformations et chargement monotone proportionnel;",
                "- plasticite J2 isotrope avec ecrouissage lineaire;",
                "- comparaison au point d'integration sur un champ affine;",
                "- aucune revendication sur les inversions cycliques ou les grandes deformations.",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def unit_cube_tet4_mesh() -> tuple[np.ndarray, np.ndarray]:
    """Return a conforming five-tetrahedron unit cube."""
    nodes = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
        ],
        dtype=float,
    )
    elements = np.array(
        [
            [0, 1, 3, 4],
            [1, 2, 3, 6],
            [1, 3, 4, 6],
            [1, 4, 5, 6],
            [3, 4, 6, 7],
        ],
        dtype=np.int64,
    )
    return nodes, elements


def code_aster_j2_commands(
    displacements: np.ndarray,
    campaign: CodeAsterJ2Campaign | None = None,
) -> str:
    """Return the controlled Code_Aster command file for the affine J2 patch."""
    settings = campaign or CodeAsterJ2Campaign(".")
    imposed = ",\n        ".join(
        f'_F(NOEUD="N{index + 1}", DX={value[0]:.16g}, '
        f"DY={value[1]:.16g}, DZ={value[2]:.16g})"
        for index, value in enumerate(np.asarray(displacements, dtype=float))
    )
    return f'''# coding=utf-8
import json
import numpy as np
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(
    MAILLAGE=mesh,
    AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"),
)
material = DEFI_MATERIAU(
    ELAS=_F(E={settings.young_mpa:.16g}, NU={settings.poisson:.16g}),
    ECRO_LINE=_F(
        SY={settings.yield_stress_mpa:.16g},
        D_SIGM_EPSI={settings.code_aster_tangent_mpa:.16g},
    ),
)
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
boundary = AFFE_CHAR_MECA(
    MODELE=model,
    DDL_IMPO=(
        {imposed}
    ),
)
ramp = DEFI_FONCTION(NOM_PARA="INST", VALE=(0.0, 0.0, 1.0, 1.0))
times = DEFI_LIST_REEL(DEBUT=0.0, INTERVALLE=_F(JUSQU_A=1.0, NOMBRE=10))
result = STAT_NON_LINE(
    MODELE=model,
    CHAM_MATER=field,
    EXCIT=_F(CHARGE=boundary, FONC_MULT=ramp),
    COMPORTEMENT=_F(RELATION="VMIS_ISOT_LINE", DEFORMATION="PETIT"),
    INCREMENT=_F(LIST_INST=times),
    CONVERGENCE=_F(RESI_GLOB_RELA=1.0e-10, ITER_GLOB_MAXI=30),
)
order = result.getIndexes()[-1]
stress = result.getField("SIEF_ELGA", order)
components = []
ranges = []
for name in ("SIXX", "SIYY", "SIZZ", "SIXY", "SIXZ", "SIYZ"):
    values, _ = stress.getValuesWithDescription(name, ["SOLID"])
    components.append(float(np.mean(values)))
    ranges.append([float(np.min(values)), float(np.max(values))])
internal = result.getField("VARI_ELGA", order)
plastic, _ = internal.getValuesWithDescription("V1", ["SOLID"])
with open("/work/code_aster_j2_raw.json", "w", encoding="utf-8") as stream:
    json.dump({{
        "stress_mpa": components,
        "stress_ranges_mpa": ranges,
        "equivalent_plastic_strain": float(np.mean(plastic)),
        "plastic_strain_range": [float(np.min(plastic)), float(np.max(plastic))],
    }}, stream, indent=2)
FIN()
'''


def evaluate_code_aster_j2(
    raw: dict[str, object],
    campaign: CodeAsterJ2Campaign | None = None,
) -> dict[str, object]:
    """Compare normalized Code_Aster values with theory and the QF material point."""
    settings = campaign or CodeAsterJ2Campaign(".")
    axial_strain, lateral_strain = settings._theoretical_strains()
    strain = np.array([axial_strain, lateral_strain, lateral_strain, 0.0, 0.0, 0.0])
    material = VonMisesElastoplasticMaterial(
        E=settings.young_mpa,
        nu=settings.poisson,
        yield_stress=settings.yield_stress_mpa,
        hardening_modulus=settings.hardening_mpa,
    )
    qf_stress, _, qf_state = material.stress_tangent_state(strain, material.initial_state())
    expected_plastic = (
        settings.target_stress_mpa - settings.yield_stress_mpa
    ) / settings.hardening_mpa
    code_stress = np.asarray(raw["stress_mpa"], dtype=float)
    code_plastic = float(cast(Any, raw["equivalent_plastic_strain"]))
    checks = [
        _relative_check(
            "code_aster_axial_stress_vs_theory",
            code_stress[0],
            settings.target_stress_mpa,
            2.0e-5,
        ),
        _relative_check(
            "qf_solver_axial_stress_vs_theory",
            float(qf_stress[0]),
            settings.target_stress_mpa,
            2.0e-5,
        ),
        _relative_check(
            "code_aster_equivalent_plastic_strain_vs_theory",
            code_plastic,
            expected_plastic,
            2.0e-5,
        ),
        _relative_check(
            "qf_solver_equivalent_plastic_strain_vs_theory",
            float(qf_state["equivalent_plastic_strain"]),
            expected_plastic,
            2.0e-5,
        ),
        _absolute_check(
            "code_aster_lateral_stress_ratio",
            float(np.max(np.abs(code_stress[1:3]))) / settings.target_stress_mpa,
            2.0e-5,
        ),
        _absolute_check(
            "code_aster_homogeneous_stress_range",
            _maximum_range(raw["stress_ranges_mpa"]) / settings.target_stress_mpa,
            2.0e-5,
        ),
    ]
    return {
        "study_id": settings.study_id,
        "status": "PASS_EXTERNAL_CORRELATION"
        if all(check["status"] == "PASS" for check in checks)
        else "FAIL",
        "maturity": "experimental",
        "external_solver": {
            "name": "Code_Aster",
            "version": "18.1.0",
            "relation": "VMIS_ISOT_LINE",
            "deformation": "PETIT",
        },
        "code_aster": raw,
        "qf_solver": {
            "stress_mpa": qf_stress.tolist(),
            "equivalent_plastic_strain": float(qf_state["equivalent_plastic_strain"]),
        },
        "theory": {
            "axial_stress_mpa": settings.target_stress_mpa,
            "equivalent_plastic_strain": expected_plastic,
            "axial_strain": axial_strain,
            "lateral_strain": lateral_strain,
            "plastic_hardening_modulus_mpa": settings.hardening_mpa,
            "code_aster_total_tangent_mpa": settings.code_aster_tangent_mpa,
        },
        "checks": checks,
        "limitations": [
            "Affine monotonic small-strain material correlation.",
            "No cyclic reversal or structural localization comparison.",
            "Code_Aster TETRA4 and QF_solver use independent constitutive implementations.",
        ],
    }


def _relative_check(identifier: str, value: float, reference: float, limit: float) -> dict[str, Any]:
    denominator = max(abs(reference), float(np.finfo(float).tiny))
    error = abs(value - reference) / denominator
    return _absolute_check(identifier, error, limit)


def _absolute_check(identifier: str, value: float, limit: float) -> dict[str, Any]:
    return {
        "id": identifier,
        "value": float(value),
        "limit": float(limit),
        "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL",
    }


def _maximum_range(raw_ranges: object) -> float:
    ranges = np.asarray(raw_ranges, dtype=float)
    return float(np.max(np.abs(ranges[:, 1] - ranges[:, 0])))
