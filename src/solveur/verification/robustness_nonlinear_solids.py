"""Bounded robustness qualification for the common J2 solid path.

The campaign deliberately separates internal verification from external
correlation.  It exercises the same constitutive contract and element
assembly used by the solver; it does not promote a scope by itself.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from solveur.api import solve_model
from solveur.core.material_state import MaterialStateSession
from solveur.core.model import FiniteElementModel
from solveur.elements.solid.hex20 import Hex20Element
from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.tet10 import Tet10Element
from solveur.elements.solid.tet4 import Tet4Element
from solveur.io.manifest import write_json_file
from solveur.materials.solid import VonMisesElastoplasticMaterial


ELEMENT_TYPES = ("TET4", "TET10", "HEX8", "HEX20")
CAMPAIGN_ID = "VNV-ROBUSTNESS-NONLINEAR-SOLIDS-024"


def _archived_external_correlation() -> dict[str, Any]:
    """Read the bounded RQ-G08 archive when it is present in the checkout."""

    root = Path(__file__).resolve().parents[3]
    tracked_path = root / "qualification" / "external_reference_digests" / "rqg08_j2_common_024.json"
    raw_path = root / "qualification" / "vnv" / "external" / "rqg08_j2_common_024" / "reference" / "summary.json"
    path = tracked_path if tracked_path.is_file() else raw_path
    if not path.is_file():
        return {
            "status": "PENDING_EXTERNAL",
            "solvers": ["Code_Aster", "CalculiX"],
            "note": "The bounded RQ-G08 archive is not present in this checkout.",
        }
    evidence = json.loads(path.read_text(encoding="utf-8"))
    status = evidence["status"]
    if path == raw_path:
        status = "PASS_EXTERNAL_CORRELATION_BOUNDED" if status == "PASS_EXTERNAL_CORRELATION" else status
        reference = "qualification/vnv/external/rqg08_j2_common_024/reference/summary.json"
        checks = len(evidence["checks"])
        solver = evidence["external_solver"]
    else:
        checks = evidence["checks"]["total"]
        solver = evidence["external_solver"]
        reference = "qualification/external_reference_digests/rqg08_j2_common_024.json"
    return {
        "status": status,
        "solver": solver,
        "reference": reference,
        "checks": checks,
        "scope": "One affine displacement-controlled element per family; no physical validation claim.",
    }


def j2_material() -> VonMisesElastoplasticMaterial:
    """Return the deterministic material used by the bounded campaign."""

    return VonMisesElastoplasticMaterial(E=1000.0, nu=0.3, yield_stress=0.02, hardening_modulus=10.0, density=1.0)


def element_coordinates(element_type: str, *, distorted: bool = False) -> np.ndarray:
    """Return canonical unit-volume coordinates for one supported element."""

    corners = np.asarray(
        [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]],
        dtype=float,
    )
    family = str(element_type).upper()
    if family == "TET4":
        result = corners[[0, 1, 3, 4]]
    elif family == "TET10":
        base = corners[[0, 1, 3, 4]]
        edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
        result = np.vstack([base, [(base[first] + base[second]) / 2.0 for first, second in edges]])
    elif family == "HEX8":
        result = corners.copy()
    elif family == "HEX20":
        edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
        result = np.vstack([corners, [(corners[first] + corners[second]) / 2.0 for first, second in edges]])
    else:
        raise ValueError(f"Unsupported robustness element {element_type!r}.")

    if distorted and family in {"HEX8", "HEX20"}:
        result = result.copy()
        result[6] += np.asarray([0.12, -0.07, 0.08])
        if family == "HEX20":
            edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
            for index, (first, second) in enumerate(edges, start=8):
                result[index] = 0.5 * (result[first] + result[second])
    return result


def material_paths() -> dict[str, list[np.ndarray]]:
    """Return deterministic multiaxial strain histories."""

    zero = np.zeros(6)

    def vector(ex: float = 0.0, ey: float = 0.0, ez: float = 0.0, gxy: float = 0.0, gyz: float = 0.0, gxz: float = 0.0) -> np.ndarray:
        return np.asarray([ex, ey, ez, gxy, gyz, gxz], dtype=float)

    return {
        "traction_unload_reload": [
            zero,
            vector(ex=0.01),
            vector(ex=0.04),
            vector(ex=0.01),
            zero,
            vector(ex=-0.025),
            zero,
            vector(ex=0.03),
        ],
        "pure_shear": [zero, vector(gxy=0.01), vector(gxy=0.05), vector(gxy=0.01), zero, vector(gxy=-0.04)],
        "non_proportional": [
            zero,
            vector(ex=0.025),
            vector(ex=0.025, gxy=0.02),
            vector(ex=0.01, gxy=0.04),
            vector(ex=-0.015, gxy=0.02),
            vector(ex=-0.015, gxy=-0.03),
        ],
    }


def run_constitutive_paths() -> dict[str, Any]:
    """Evaluate all material paths and verify finite, transactional responses."""

    material = j2_material()
    histories: dict[str, Any] = {}
    checks: list[dict[str, Any]] = []
    for name, path in material_paths().items():
        committed = material.initial_state()
        rows = []
        for strain in path:
            response = material.evaluate(strain, committed)
            committed = deepcopy(response.trial_state)
            rows.append(
                {
                    "strain": strain.tolist(),
                    "stress": response.stress.tolist(),
                    "von_mises": float(response.trial_state["equivalent_stress"]),
                    "equivalent_plastic_strain": float(response.trial_state["equivalent_plastic_strain"]),
                    "yield_function": float(response.trial_state["yield_function"]),
                }
            )
        finite = all(np.all(np.isfinite(row["stress"])) for row in rows)
        plastic = max(row["equivalent_plastic_strain"] for row in rows)
        checks.append({"id": name, "status": "PASS" if finite and plastic > 0.0 else "FAIL", "plastic_max": plastic})
        histories[name] = rows
    return {"status": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL", "checks": checks, "histories": histories}


def tangent_finite_difference() -> dict[str, Any]:
    """Compare the algorithmic tangent with central differences."""

    material = j2_material()
    strain = np.asarray([0.08, 0.005, -0.002, 0.01, -0.004, 0.006])
    committed = material.initial_state()
    response = material.evaluate(strain, committed)
    errors: list[float] = []
    steps = (1.0e-5, 1.0e-6, 1.0e-7)
    for step in steps:
        numerical = np.column_stack(
            [
                (material.evaluate(strain + step * np.eye(6)[column], committed).stress - material.evaluate(strain - step * np.eye(6)[column], committed).stress)
                / (2.0 * step)
                for column in range(6)
            ]
        )
        errors.append(float(np.linalg.norm(response.tangent - numerical) / max(np.linalg.norm(numerical), 1.0)))
    return {
        "status": "PASS" if max(errors) < 1.0e-6 else "FAIL",
        "steps": list(steps),
        "relative_errors": errors,
        "maximum_relative_error": max(errors),
        "limit": 1.0e-6,
    }


def transaction_check() -> dict[str, Any]:
    """Prove that failed trial work does not alter committed integration states."""

    material = j2_material()
    committed = {0: [material.initial_state(), material.initial_state()]}
    before = deepcopy(committed)
    session = MaterialStateSession(committed)
    trial = session.begin_trial()
    response = material.evaluate(np.asarray([0.08, 0.01, 0.0, 0.02, 0.0, 0.0]), trial[0][0])
    trial[0][0] = response.trial_state
    session.rollback()
    rollback_untouched = committed == before
    trial = session.begin_trial()
    trial[0][0] = response.trial_state
    session.commit()
    commit_changed = committed != before
    return {"status": "PASS" if rollback_untouched and commit_changed else "FAIL", "rollback_untouched": rollback_untouched, "commit_changed": commit_changed}


def _element_class(element_type: str) -> type:
    return {"TET4": Tet4Element, "TET10": Tet10Element, "HEX8": Hex8Element, "HEX20": Hex20Element}[element_type]


def run_element_matrix() -> dict[str, Any]:
    """Run the common affine history on all four element contracts."""

    gradient = np.asarray([[0.08, 0.015, -0.01], [0.005, -0.015, 0.01], [0.0, 0.008, 0.02]])
    factors = (0.25, 0.5, 0.75, 1.0, 0.5, 0.0, -0.5)
    rows = []
    for family in ELEMENT_TYPES:
        coords = element_coordinates(family, distorted=family in {"HEX8", "HEX20"})
        element = _element_class(family)(j2_material())
        committed: list[dict[str, object]] | None = None
        force_rows = []
        for factor in factors:
            displacement = np.concatenate([factor * gradient @ point for point in coords])
            internal, tangent, trial = element.internal_force_tangent_state(coords, displacement, committed)
            committed = deepcopy(trial)
            peeq = max(float(item.get("equivalent_plastic_strain", 0.0)) for item in committed)
            vm = max(float(item.get("equivalent_stress", 0.0)) for item in committed)
            force_rows.append({"factor": factor, "reaction_norm": float(np.linalg.norm(internal)), "energy": float(0.5 * displacement @ internal), "von_mises_max": vm, "peeq_max": peeq, "tangent_norm": float(np.linalg.norm(tangent))})
        rows.append({"element": family, "distorted": family in {"HEX8", "HEX20"}, "integration_points": len(committed or []), "dof_count": int(coords.size), "history": force_rows, "status": "PASS" if all(np.isfinite(row["energy"]) for row in force_rows) else "FAIL"})
    return {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "rows": rows, "factors": list(factors)}


def _global_model(element_type: str) -> FiniteElementModel:
    coords = element_coordinates(element_type)
    fixed = [{"node": 0, "dofs": ["UX", "UY", "UZ"]}, {"node": 1, "dofs": ["UY", "UZ"]}, {"node": 2, "dofs": ["UZ"]}]
    return FiniteElementModel.from_raw(
        nodes=coords.tolist(),
        elements=[{"type": element_type, "nodes": list(range(len(coords))), "material": "j2"}],
        materials={"j2": {"type": "von_mises_elastoplastic_3d", "E": 1000.0, "nu": 0.3, "density": 1.0, "yield_stress": 0.02, "hardening_modulus": 10.0}},
        fixed_dofs=fixed,
        loads=[{"node": 1, "dof": "UX", "value": 5.0}],
        analysis={"type": "nonlinear_static", "method": "newton_raphson", "load_path": [0.25, 0.5, 0.75, 1.0], "max_iterations": 30, "tolerance": 1.0e-7},
    )


def run_common_global_benchmark() -> dict[str, Any]:
    """Run the same bounded nonlinear load history through the global driver."""

    rows = []
    for family in ELEMENT_TYPES:
        started = perf_counter()
        result = solve_model(_global_model(family))
        data = result.to_dict()
        steps = data["solver"]["steps"]
        reaction_norm = 0.0
        if result.audit is not None:
            for vector in result.audit.vectors:
                name = vector.get("name", "") if isinstance(vector, dict) else getattr(vector, "name", "")
                if name == "reactions":
                    reaction_norm = float(vector.get("norm", 0.0) if isinstance(vector, dict) else vector.norm)
                    break
        rows.append({"element": family, "status": "PASS" if result.status == "PASS" else "FAIL", "dof_count": int(result.displacements.size), "newton_iterations": int(sum(step["iterations"] for step in steps)), "maximum_relative_residual": float(max(step["relative_residual"] for step in steps)), "final_displacement_norm": float(np.linalg.norm(result.displacements)), "final_peeq": float(steps[-1]["equivalent_plastic_strain_max"]), "elapsed_seconds": float(perf_counter() - started), "reaction_norm": reaction_norm})
    rate = run_newton_rate_study(rows)
    return {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "rows": rows, "load_path": [0.25, 0.5, 0.75, 1.0], "newton_rate_study": rate}


def run_newton_rate_study(reference_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Characterize full Newton against modified Newton without hiding failure."""

    rows = []
    reference_by_family = {row["element"]: row for row in (reference_rows or [])}
    for family in ELEMENT_TYPES:
        exact_row = reference_by_family.get(family)
        exact = None if exact_row is not None else solve_model(_global_model(family)).to_dict()
        modified_model = _global_model(family)
        modified_model.analysis = replace(modified_model.analysis, method="modified_newton")
        try:
            modified = solve_model(modified_model).to_dict()
            modified_row = {"status": modified["status"], "iterations": int(sum(step["iterations"] for step in modified["solver"]["steps"])), "maximum_relative_residual": float(max(step["relative_residual"] for step in modified["solver"]["steps"]))}
        except Exception as error:
            modified_row = {"status": "NON_CONVERGED", "iterations": 30 * 4, "maximum_relative_residual": None, "failure_reason": type(error).__name__}
        full_row = {"status": exact_row["status"], "iterations": exact_row["newton_iterations"], "maximum_relative_residual": exact_row["maximum_relative_residual"]} if exact_row is not None else {"status": exact["status"], "iterations": int(sum(step["iterations"] for step in exact["solver"]["steps"])), "maximum_relative_residual": float(max(step["relative_residual"] for step in exact["solver"]["steps"]))}
        rows.append({"element": family, "full_newton": full_row, "modified_newton": modified_row})
    return {"status": "PASS_CHARACTERIZED" if all(row["full_newton"]["status"] == "PASS" and row["modified_newton"]["status"] in {"PASS", "NON_CONVERGED"} for row in rows) else "FAIL", "rows": rows, "interpretation": "Full Newton is the qualified path; modified Newton is characterized and any non-convergence is explicit."}


class RobustnessQualificationCampaign:
    """Produce the internal evidence package for the robustness work packages."""

    campaign_id = CAMPAIGN_ID

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        constitutive = run_constitutive_paths()
        tangent = tangent_finite_difference()
        transactions = transaction_check()
        elements = run_element_matrix()
        benchmark = run_common_global_benchmark()
        external = _archived_external_correlation()
        summary: dict[str, Any] = {
            "campaign_id": self.campaign_id,
            "status": "PASS_INTERNAL" if all(item["status"] == "PASS" for item in (constitutive, tangent, transactions, elements, benchmark)) else "FAIL",
            "maturity": "experimental",
            "scope": {"elements": list(ELEMENT_TYPES), "material": "small-strain J2 isotropic hardening", "external_correlation": external["status"], "large_scale_claim": False},
            "constitutive_paths": constitutive,
            "consistent_tangent": tangent,
            "transactions": transactions,
            "element_matrix": elements,
            "common_global_benchmark": benchmark,
            "external_correlations": external,
            "limitations": ["Small-strain J2 only.", "Canonical one-element benchmark; no multi-million-DOF claim.", "Multi-element, cyclic and physical validation remain outside the bounded RQ-G08 scope.", "No physical validation claim is made."],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._write_report(summary)
        self._write_plots(summary)
        return summary

    def _write_report(self, summary: dict[str, Any]) -> None:
        lines = [f"# {self.campaign_id}", "", f"Statut interne : **{summary['status']}**", "", "## Matrice elementaire", "", "| Element | Points Gauss | Distordu | Statut |", "| --- | ---: | --- | --- |"]
        for row in summary["element_matrix"]["rows"]:
            lines.append(f"| {row['element']} | {row['integration_points']} | {row['distorted']} | {row['status']} |")
        lines.extend(["", "## Benchmark global", "", "| Element | Iterations Newton | Residu max | PEEQ final | Reaction | Temps (s) |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
        for row in summary["common_global_benchmark"]["rows"]:
            lines.append(f"| {row['element']} | {row['newton_iterations']} | {row['maximum_relative_residual']:.3e} | {row['final_peeq']:.3e} | {row['reaction_norm']:.3e} | {row['elapsed_seconds']:.3f} |")
        lines.extend(["", "## Robustesse", "", f"Tangent FD max : `{summary['consistent_tangent']['maximum_relative_error']:.3e}`", f"Transactions : **{summary['transactions']['status']}**", "", "![Force displacement](force_displacement.png)", "", "![Newton rate](newton_rate.png)", "", f"Correlation externe : **{summary['external_correlations']['status']}**", ""])
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")

    def _write_plots(self, summary: dict[str, Any]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        figure, axes = plt.subplots(1, 2, figsize=(10.0, 4.2), constrained_layout=True)
        for row in summary["element_matrix"]["rows"]:
            factors = [item["factor"] for item in row["history"]]
            axes[0].plot(factors, [item["reaction_norm"] for item in row["history"]], marker="o", label=row["element"])
        axes[0].set(xlabel="Facteur de charge", ylabel="Norme force interne", title="Force-deplacement borne")
        for row in summary["common_global_benchmark"]["rows"]:
            axes[1].bar(row["element"], row["newton_iterations"])
        axes[1].set(ylabel="Iterations Newton", title="Cout Newton par element")
        axes[0].legend()
        for axis in axes:
            axis.grid(alpha=0.25)
        figure.savefig(self.output_dir / "force_displacement.png", dpi=160)
        plt.close(figure)
        figure, axis = plt.subplots(figsize=(6.4, 4.0))
        for row in summary["common_global_benchmark"]["rows"]:
            axis.plot([row["maximum_relative_residual"]], [row["newton_iterations"]], "o", label=row["element"])
        axis.set(xscale="log", xlabel="Residus relatifs maximum", ylabel="Iterations Newton", title="Indicateur de convergence")
        axis.grid(alpha=0.25)
        axis.legend()
        figure.savefig(self.output_dir / "newton_rate.png", dpi=160)
        plt.close(figure)
