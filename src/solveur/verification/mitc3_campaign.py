"""Executable qualification-candidate campaign for the MITC3+ shell."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
from solveur.elements.shell.mitc4 import ShellMaterial

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.core.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel
from solveur.elements.shell.mitc3 import EXPANDED_DOF_COUNT, Mitc3ShellElement
from solveur.io.manifest import write_json_file
from solveur.verification.mitc3_models import (
    cantilever_model,
    cook_model,
    pinched_cylinder_model,
    rectangular_tri_mesh,
    scordelis_model,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


class Mitc3ValidationCampaign:
    """Generate deterministic MITC3+ static and dynamic engineering evidence."""

    STUDY_IDS = (
        "VNV-MITC3-PATCH-001",
        "VNV-MITC3-SHEAR-LOCKING-002",
        "VNV-MITC3-DISTORTION-003",
        "VNV-MITC3-COOK-004",
        "VNV-MITC3-SCORDELIS-005",
        "VNV-MITC3-PINCHED-006",
        "VNV-MITC3-MIXED-MESH-007",
        "VNV-MITC3-LOADS-008",
        "VNV-MITC3-MODAL-009",
        "VNV-MITC3-NEWMARK-010",
        "VNV-MITC3-HARMONIC-011",
        "VNV-MITC3-LAMINATE-012",
    )

    def __init__(self, output: str | Path, *, quick: bool = False) -> None:
        self.output = Path(output)
        self.quick = bool(quick)

    def run(self) -> dict[str, Any]:
        self.output.mkdir(parents=True, exist_ok=True)
        studies = {
            "patch": self._patch(),
            "shear_locking": self._locking(),
            "distortion": self._distortion(),
            "cook": self._cook(),
            "scordelis": self._scordelis(),
            "pinched": self._pinched(),
            "mixed_mesh": self._mixed_mesh(),
            "loads": self._loads(),
        }
        modal, modal_model = self._modal()
        studies["modal"] = modal
        studies["newmark"] = self._newmark(modal, modal_model)
        studies["harmonic"] = self._harmonic(modal, modal_model)
        studies["laminate"] = self._laminate()
        failures = [name for name, study in studies.items() if study["status"] == "FAIL"]
        warnings = [name for name, study in studies.items() if study["status"] == "WARNING"]
        summary = {
            "schema_version": 1,
            "campaign": "MITC3-PLUS-V1",
            "profile": "engineering",
            "quick": self.quick,
            "maturity": "experimental",
            "status": "FAIL" if failures else "PASS_WITH_WARNINGS" if warnings else "PASS",
            "failed_studies": failures,
            "warning_studies": warnings,
            "studies": studies,
        }
        write_json_file(self.output / "summary.json", summary)
        self._write_reports(studies)
        self._plot_series(studies["shear_locking"]["points"], "mesh_nx", "tip_ratio", "locking.png")
        self._plot_series(studies["cook"]["points"], "element_count", "relative_error", "cook.png")
        self._plot_series(studies["scordelis"]["points"], "element_count", "relative_error", "scordelis.png")
        self._plot_series(studies["pinched"]["points"], "element_count", "relative_error", "pinched.png")
        write_vnv_manifest(self.output, "VNV-MITC3-CAMPAIGN-V1")
        return summary

    @staticmethod
    def _patch() -> dict[str, Any]:
        strain = 1.0e-4
        poisson = 0.3
        nodes, triangles, _ = rectangular_tri_mesh(1.0, 1.0, 2, 2)
        element = Mitc3ShellElement(ShellMaterial(E=70.0e9, nu=poisson, t=0.01))
        global_tensor = np.diag([strain, -poisson * strain, 0.0])
        maximum_error = 0.0
        maximum_shear_error = 0.0
        for triangle in triangles:
            coords = nodes[triangle]
            displacement = np.zeros(18)
            for local, node in enumerate(triangle):
                x, y, _ = nodes[node]
                displacement[6 * local] = strain * x
                displacement[6 * local + 1] = -poisson * strain * y
            actual = element.generalized_strains(coords, displacement)["membrane"]
            frame = element.local_frame(coords)
            local_tensor = frame @ global_tensor @ frame.T
            expected = np.array(
                [local_tensor[0, 0], local_tensor[1, 1], 2.0 * local_tensor[0, 1]]
            )
            maximum_error = max(
                maximum_error,
                float(np.linalg.norm(actual - expected) / np.linalg.norm(expected)),
            )
            _, local = element.project_to_local_midplane(coords)
            for expected_shear in (
                np.array([2.0e-4, 0.0]),
                np.array([0.0, -3.0e-4]),
                np.array([2.0e-4, -3.0e-4]),
            ):
                expanded = np.zeros(EXPANDED_DOF_COUNT)
                for local_node, (x, y) in enumerate(local):
                    expanded[6 * local_node + 2] = expected_shear @ np.array([x, y])
                for r, s in ((1.0 / 3.0, 1.0 / 3.0), (0.1, 0.2), (0.6, 0.1)):
                    actual_shear = element.strain_matrices_local(local, r, s).shear @ expanded
                    maximum_shear_error = max(
                        maximum_shear_error,
                        float(
                            np.linalg.norm(actual_shear - expected_shear)
                            / np.linalg.norm(expected_shear)
                        ),
                    )
        passed = maximum_error <= 1.0e-10 and maximum_shear_error <= 1.0e-10
        return _study(
            passed,
            affine_strain_error=maximum_error,
            constant_shear_interpolation_error=maximum_shear_error,
        )

    def _locking(self) -> dict[str, Any]:
        levels = (4, 8, 16) if self.quick else (4, 8, 16, 24, 32, 48, 64)
        points = []
        thickness = 1.0e-4
        young, poisson, width = 70.0e9, 0.3, 0.2
        shear = young / (2.0 * (1.0 + poisson))
        reference = 1.0 / (3.0 * young * width * thickness**3 / 12.0)
        reference += 1.0 / ((5.0 / 6.0) * shear * width * thickness)
        for nx in levels:
            model = cantilever_model(nx, max(1, nx // 4), thickness=thickness)
            result = solve_model(model, enforce_policy=False)
            edge = np.where(np.isclose(model.nodes[:, 0], 1.0))[0]
            tip = abs(float(np.mean([result.displacements[result.dofs.index(int(n), "UZ")] for n in edge])))
            points.append({"mesh_nx": nx, "element_count": len(model.elements), "tip_ratio": tip / reference})
        fine = float(points[-1]["tip_ratio"])
        increment = abs(fine - float(points[-2]["tip_ratio"])) / max(abs(fine), 1.0e-30)
        passed = fine >= 0.89 and increment <= 0.02
        return _study(
            passed,
            warning=not passed and fine >= 0.85,
            points=points,
            fine_tip_ratio=fine,
            final_increment=increment,
            reference="Timoshenko beam",
        )

    @staticmethod
    def _distortion() -> dict[str, Any]:
        values = []
        for distortion in (0.0, 0.1, 0.2, 0.3):
            result = solve_model(
                cantilever_model(12, 3, distortion=distortion),
                enforce_policy=False,
            )
            values.append(float(result.max_displacement))
        spread = (max(values) - min(values)) / max(abs(values[0]), 1.0e-30)
        return _study(spread <= 0.10, displacement_spread=spread, displacements=values)

    def _cook(self) -> dict[str, Any]:
        levels = (4, 8) if self.quick else (4, 8, 16, 24, 32)
        points = []
        reference = 23.96 * 100.0 / (1.0e6 * 0.01)
        for level in levels:
            model, tip = cook_model(level)
            result = solve_model(model, enforce_policy=False)
            value = float(result.displacements[result.dofs.index(tip, "UY")])
            points.append(_point(level, len(model.elements), value, reference))
        return _study(points[-1]["relative_error"] <= 0.12, warning=True, points=points)

    def _scordelis(self) -> dict[str, Any]:
        levels = (4, 8) if self.quick else (4, 8, 12, 16, 24, 32)
        points = []
        reference = -0.3024
        for level in levels:
            model, edge = scordelis_model(level, level)
            result = solve_model(model, enforce_policy=False)
            value = 0.5 * sum(
                float(result.displacements[result.dofs.index(node, "UZ")]) for node in edge
            )
            points.append(_point(level, len(model.elements), value, reference))
        return _study(points[-1]["relative_error"] <= 0.15, warning=True, points=points)

    def _pinched(self) -> dict[str, Any]:
        levels = (
            ((4, 8), (8, 16))
            if self.quick
            else ((4, 8), (8, 16), (12, 24), (16, 32), (24, 48), (32, 64))
        )
        points = []
        reference = 1.8248e-5
        for nx, nt in levels:
            model, load_node = pinched_cylinder_model(nx, nt)
            result = solve_model(model, enforce_policy=False)
            value = abs(float(result.displacements[result.dofs.index(load_node, "UY")]))
            points.append(_point(nx, len(model.elements), value, reference))
        return _study(points[-1]["relative_error"] <= 0.25, warning=True, points=points)

    @staticmethod
    def _mixed_mesh() -> dict[str, Any]:
        model = _mixed_patch_model()
        result = solve_model(model, enforce_policy=False)
        expected = 1.0e6 / (70.0e9 * 0.01)
        value = float(result.displacements[result.dofs.index(5, "UX")])
        error = abs(value - 2.0 * expected) / (2.0 * expected)
        return _study(error <= 1.0e-10, relative_error=error)

    @staticmethod
    def _loads() -> dict[str, Any]:
        model = cantilever_model(2, 1, transverse_force=-12.0)
        dofs = model.dof_manager()
        vector = GlobalAssembler().assemble_loads(model, dofs)
        total = sum(vector[dofs.index(node, "UZ")] for node in range(model.node_count))
        error = abs(total + 12.0) / 12.0
        return _study(error <= 1.0e-14, resultant_error=error, resultant=total)

    @staticmethod
    def _modal() -> tuple[dict[str, Any], FiniteElementModel]:
        model = cantilever_model(
            8,
            2,
            transverse_force=0.0,
            analysis={"type": "modal", "method": "eigh", "parameters": {"mode_count": 6}},
        )
        result = solve_model(model, enforce_policy=False)
        solver = result.solver
        passed = (
            solver["max_relative_residual"] <= 1.0e-8
            and solver["mass_orthogonality_error"] <= 1.0e-8
        )
        return (
            _study(
                passed,
                frequencies_hz=np.asarray(result.frequencies_hz).tolist(),
                max_relative_residual=float(solver["max_relative_residual"]),
                mass_orthogonality_error=float(solver["mass_orthogonality_error"]),
                first_mode=np.asarray(result.modes[:, 0]).tolist(),
            ),
            model,
        )

    @staticmethod
    def _newmark(modal: dict[str, Any], modal_model: FiniteElementModel) -> dict[str, Any]:
        frequency = float(modal["frequencies_hz"][0])
        mode = np.asarray(modal["first_mode"], dtype=float)
        mode *= 1.0e-4 / np.max(np.abs(mode))
        modal_dofs = modal_model.dof_manager()
        initial = [
            {"node": node, "dof": name, "value": float(mode[modal_dofs.index(node, name)])}
            for node, names in modal_dofs.node_dofs.items()
            for name in names
            if abs(mode[modal_dofs.index(node, name)]) > 1.0e-18
        ]
        period = 1.0 / frequency
        model = cantilever_model(
            8,
            2,
            transverse_force=0.0,
            analysis={
                "type": "transient_dynamic",
                "method": "newmark",
                "parameters": {
                    "time_step": period / 80.0,
                    "steps": 80,
                    "load_factors": [0.0],
                    "initial_displacements": initial,
                },
            },
        )
        result = solve_model(model, enforce_policy=False)
        drift = max(abs(float(row["relative_energy_drift"])) for row in result.solver["time_history"])
        return _study(drift <= 1.0e-4, maximum_energy_drift=drift, period=period)

    @staticmethod
    def _harmonic(modal: dict[str, Any], modal_model: FiniteElementModel) -> dict[str, Any]:
        frequency = float(modal["frequencies_hz"][0])
        model = cantilever_model(
            8,
            2,
            analysis={
                "type": "harmonic_response",
                "method": "direct_frequency",
                "parameters": {
                    "frequencies_hz": [
                        0.0,
                        0.8 * frequency,
                        0.95 * frequency,
                        1.05 * frequency,
                        1.2 * frequency,
                    ]
                },
            },
        )
        result = solve_model(model, enforce_policy=False)
        static_model = cantilever_model(8, 2)
        static = solve_model(static_model, enforce_policy=False)
        zero = np.asarray(result.responses[0])
        error = np.linalg.norm(zero.real - static.displacements) / np.linalg.norm(static.displacements)
        finite = bool(np.all(np.isfinite(np.asarray(result.responses))))
        return _study(
            finite and error <= 1.0e-8,
            zero_frequency_static_error=float(error),
            frequencies_hz=np.asarray(result.frequencies_hz).tolist(),
            peak_stress_amplitude=float(
                max(row["peak_component"]["amplitude"] for row in result.shell_stress_response)
            ),
        )

    @staticmethod
    def _laminate() -> dict[str, Any]:
        model = cantilever_model(8, 2, laminate=True)
        result = solve_model(model, enforce_policy=False)
        plies = result.element_results[0]["ply_results"]
        finite = all(np.all(np.isfinite(point["stress"])) for point in plies)
        return _study(finite and len(plies) == 12, recovered_ply_points=len(plies))

    def _write_reports(self, studies: dict[str, dict[str, Any]]) -> None:
        for identifier, (name, study) in zip(self.STUDY_IDS, studies.items(), strict=True):
            lines = [
                "---",
                f"doc_id: {identifier}",
                "revision: 0.1",
                "status: generated_engineering_evidence",
                "---",
                "",
                f"# {identifier}",
                "",
                f"Etude: `{name}`. Verdict automatique: **{study['status']}**.",
                "",
                "| Metrique | Valeur |",
                "| --- | --- |",
            ]
            lines.extend(
                f"| `{key}` | `{_compact(value)}` |"
                for key, value in study.items()
                if key not in {"status", "points", "first_mode"}
            )
            if "points" in study:
                lines.extend(("", "Les points complets sont traces dans `summary.json`."))
            (self.output / f"{identifier}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _plot_series(
        self,
        points: list[dict[str, Any]],
        x_key: str,
        y_key: str,
        filename: str,
    ) -> None:
        figure, axis = plt.subplots(figsize=(7.0, 4.2))
        axis.plot([row[x_key] for row in points], [row[y_key] for row in points], "o-")
        axis.set_xlabel(x_key)
        axis.set_ylabel(y_key)
        axis.grid(True, alpha=0.3)
        figure.tight_layout()
        figure.savefig(self.output / filename, dpi=160)
        plt.close(figure)


def _study(passed: bool, *, warning: bool = False, **values: Any) -> dict[str, Any]:
    return {"status": "PASS" if passed else "WARNING" if warning else "FAIL", **values}


def _point(level: int, count: int, value: float, reference: float) -> dict[str, Any]:
    return {
        "mesh_level": level,
        "element_count": count,
        "value": value,
        "reference": reference,
        "relative_error": abs(value - reference) / abs(reference),
    }


def _mixed_patch_model() -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [2, 0, 0], [2, 1, 0]],
        elements=[
            {"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "skin"},
            {"type": "MITC3", "nodes": [1, 4, 2], "material": "skin"},
            {"type": "MITC3", "nodes": [4, 5, 2], "material": "skin"},
        ],
        materials={"skin": {"type": "shell_isotropic", "E": 70.0e9, "nu": 0.3, "t": 0.01}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]},
            {"node": 3, "dofs": ["UX", "UZ", "RX", "RY"]},
            *[{"node": node, "dofs": ["UZ", "RX", "RY"]} for node in (1, 2, 4, 5)],
        ],
        distributed_loads=[
            {"type": "edge_traction", "element": 2, "edge": 0, "value": [1.0e6, 0.0, 0.0]}
        ],
        verification_profile="quick",
    )


def _compact(value: Any) -> str:
    text = str(value)
    return text if len(text) <= 180 else text[:177] + "..."
