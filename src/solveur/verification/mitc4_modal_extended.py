"""Extended MITC4 modal verification on assembled and curved shells."""

from __future__ import annotations

from solveur.paths import project_root

import time
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
from scipy.linalg import eigh

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.elements.shell.mitc4.mesh import MeshFactory
from solveur.api import solve_model
from solveur.core.analyses.settings import AnalysisSettings
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.analyses.dynamic_reduction import DynamicDofReducer
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.verification.mitc4_modal_external import build_modal_correlation_model


PROJECT_ROOT = project_root()
FREE_FREE_ID = "VNV-MITC4-MODAL-FREEFREE-FOLDED-005"
CURVED_ID = "VNV-MITC4-MODAL-CURVED-DISTORTED-006"
SPARSE_ID = "VNV-MITC4-MODAL-EIGSH-LARGE-007"


class FoldedShellFreeFreeStudy:
    """Correlate six numerical zero modes with analytical rigid motions."""

    rigid_gap_limit = 1.0e-8
    rigid_subspace_mac_limit = 0.999999
    rigid_residual_limit = 1.0e-12

    def run(self) -> dict[str, Any]:
        model, quads = _folded_shell_model()
        dofs = model.dof_manager()
        assembler = GlobalAssembler()
        stiffness = assembler.assemble_stiffness(model, dofs)
        mass = assembler.assemble_mass(model, dofs)
        reducer = DynamicDofReducer.from_system(
            model,
            dofs,
            mass,
            stiffness,
            np.array([], dtype=int),
        )
        reduced_k = reducer.stiffness.toarray()
        reduced_m = reducer.mass.toarray()
        eigenvalues, modes = eigh(reduced_k, reduced_m)
        first_elastic = float(eigenvalues[6])
        rigid_values = np.asarray(eigenvalues[:6], dtype=float)
        rigid_gap = float(np.max(np.abs(rigid_values)) / first_elastic)
        analytical = _analytical_rigid_modes(model, dofs, reducer)
        rigid_mac = _mass_subspace_mac(analytical, modes[:, :6], reducer.mass)
        stiffness_scale = max(float(np.linalg.norm(stiffness.data)), 1.0)
        rigid_residuals = [
            float(np.linalg.norm(reducer.stiffness @ analytical[:, index]))
            / max(stiffness_scale * float(np.linalg.norm(analytical[:, index])), 1.0)
            for index in range(6)
        ]
        elastic = np.sqrt(np.maximum(eigenvalues[6:16], 0.0)) / (2.0 * np.pi)
        checks = {
            "exactly_six_rigid_modes": int(np.count_nonzero(np.abs(eigenvalues) < first_elastic * 1.0e-8))
            == 6,
            "rigid_elastic_separation": rigid_gap <= self.rigid_gap_limit,
            "analytical_rigid_subspace": min(rigid_mac) >= self.rigid_subspace_mac_limit,
            "analytical_rigid_residuals": max(rigid_residuals) <= self.rigid_residual_limit,
            "positive_first_elastic_mode": first_elastic > 0.0,
        }
        return {
            "study_id": FREE_FREE_ID,
            "status": "PASS" if all(checks.values()) else "FAIL",
            "model": {
                "geometry": "two MITC4 panels assembled at a 90 degree fold",
                "mesh": [8, 4],
                "node_count": model.node_count,
                "element_count": len(model.elements),
                "full_dof_count": dofs.ndof,
                "retained_dof_count": reducer.stiffness.shape[0],
                "condensed_drilling_dof_count": reducer.diagnostics[
                    "condensed_drilling_dof_count"
                ],
                "boundary_conditions": "free-free",
            },
            "metrics": {
                "rigid_eigenvalues": rigid_values.tolist(),
                "rigid_to_first_elastic_ratio": rigid_gap,
                "rigid_subspace_principal_mac": rigid_mac,
                "maximum_rigid_residual": max(rigid_residuals),
                "first_ten_elastic_frequencies_hz": elastic.tolist(),
            },
            "acceptance": {
                "rigid_mode_count": 6,
                "rigid_to_first_elastic_ratio_max": self.rigid_gap_limit,
                "rigid_subspace_mac_min": self.rigid_subspace_mac_limit,
                "rigid_residual_max": self.rigid_residual_limit,
            },
            "checks": checks,
            "limitations": [
                "The external correlation is the analytical six-dimensional rigid-motion subspace.",
                "An independent commercial-code free-free correlation remains desirable.",
            ],
            "_plot": {"nodes": model.nodes, "quads": quads, "eigenvalues": eigenvalues[:16]},
        }


class CurvedDistortedShellStudy:
    """Check a cylindrical MITC4 panel under refinement and mesh distortion."""

    convergence_limit = 0.04
    distortion_limit = 0.01
    rotation_limit = 1.0e-8
    residual_limit = 1.0e-7

    def run(self) -> dict[str, Any]:
        points = [self._point(size, size // 2) for size in (8, 16, 24)]
        regular = np.asarray(points[-1]["frequencies_hz"], dtype=float)
        previous = np.asarray(points[-2]["frequencies_hz"], dtype=float)
        distorted = self._point(24, 12, distortion=0.20, include_plot=True)
        rotated = self._point(24, 12, rotated=True)
        regular_plot = points[-1].pop("_plot")
        distorted_plot = distorted.pop("_plot")
        distortion_error = _relative_errors(distorted["frequencies_hz"], regular)
        rotation_error = _relative_errors(rotated["frequencies_hz"], regular)
        convergence = _relative_errors(previous, regular)
        checks = {
            "ten_modes_computed": all(len(point["frequencies_hz"]) == 10 for point in points),
            "h_refinement_convergence": max(convergence) <= self.convergence_limit,
            "twenty_percent_distortion": max(distortion_error) <= self.distortion_limit,
            "rigid_rotation_objectivity": max(rotation_error) <= self.rotation_limit,
            "modal_residuals": max(
                point["maximum_relative_residual"] for point in (*points, distorted, rotated)
            )
            <= self.residual_limit,
        }
        return {
            "study_id": CURVED_ID,
            "status": "PASS" if all(checks.values()) else "FAIL",
            "model": {
                "geometry": "cylindrical cantilever panel, radius 1 m, angle 0.6 rad",
                "length_m": 1.0,
                "thickness_m": 0.01,
                "boundary_conditions": "six dofs clamped at x=0",
                "distortion": "deterministic interior-node perturbation, 20 percent of cell size",
            },
            "points": points,
            "metrics": {
                "last_mesh_increment": convergence,
                "distorted_frequency_differences": distortion_error,
                "rotated_frequency_differences": rotation_error,
            },
            "acceptance": {
                "last_mesh_increment_max": self.convergence_limit,
                "distorted_frequency_difference_max": self.distortion_limit,
                "rotation_frequency_difference_max": self.rotation_limit,
                "relative_residual_max": self.residual_limit,
            },
            "checks": checks,
            "limitations": [
                "This case supplies convergence and invariance evidence, not an analytical shell oracle.",
                "The geometry is faceted; no curved isoparametric MITC4 mapping is claimed.",
            ],
            "_plot": {
                "regular": regular_plot,
                "distorted": distorted_plot,
            },
        }

    @staticmethod
    def _point(
        nx: int,
        ny: int,
        *,
        distortion: float = 0.0,
        rotated: bool = False,
        include_plot: bool = False,
    ) -> dict[str, Any]:
        model, quads = _curved_shell_model(nx, ny, distortion=distortion, rotated=rotated)
        started = time.perf_counter()
        result = solve_model(model, enforce_policy=False)
        elapsed = time.perf_counter() - started
        point: dict[str, Any] = {
            "mesh": [nx, ny],
            "element_count": len(model.elements),
            "retained_dof_count": result.solver["dynamic_reduction"]["retained_dof_count"],
            "frequencies_hz": [float(value) for value in result.frequencies_hz[:10]],
            "maximum_relative_residual": float(result.solver["max_relative_residual"]),
            "mass_orthogonality_error": float(result.solver["mass_orthogonality_error"]),
            "method": result.method,
            "elapsed_seconds": elapsed,
            "distortion": distortion,
            "rotated": rotated,
        }
        if include_plot or (nx == 24 and ny == 12 and not rotated):
            point["_plot"] = _mode_plot_data(model, quads, result)
        return point


class SparseModalScalingStudy:
    """Cross-check eigsh against eigh, then exercise a larger sparse model."""

    method_difference_limit = 1.0e-8
    method_mac_limit = 0.99999999
    residual_limit = 1.0e-7
    minimum_large_dofs = 5000

    def run(self) -> dict[str, Any]:
        direct_model, _ = build_modal_correlation_model(16)
        started = time.perf_counter()
        direct = solve_model(direct_model, enforce_policy=False)
        direct_time = time.perf_counter() - started
        sparse_model, _ = build_modal_correlation_model(16)
        sparse_model.analysis = _sparse_settings()
        started = time.perf_counter()
        sparse = solve_model(sparse_model, enforce_policy=False)
        sparse_time = time.perf_counter() - started
        method_differences = _relative_errors(
            sparse.frequencies_hz[:10], direct.frequencies_hz[:10]
        )
        method_mac = _modal_group_macs(direct, sparse, direct_model.node_count)

        large_model, _ = build_modal_correlation_model(48)
        started = time.perf_counter()
        large = solve_model(large_model, enforce_policy=False)
        large_time = time.perf_counter() - started
        large_dofs = int(large.solver["dynamic_reduction"]["retained_dof_count"])
        checks = {
            "medium_eigh_eigsh_frequencies": max(method_differences)
            <= self.method_difference_limit,
            "medium_eigh_eigsh_shapes": min(method_mac) >= self.method_mac_limit,
            "large_problem_size": large_dofs >= self.minimum_large_dofs,
            "large_sparse_method": large.method == "eigsh"
            and not bool(large.solver["dense_conversion_used"]),
            "large_ten_modes": len(large.frequencies_hz[:10]) == 10,
            "large_modal_residual": float(large.solver["max_relative_residual"])
            <= self.residual_limit,
            "large_orthogonality": max(
                float(large.solver["mass_orthogonality_error"]),
                float(large.solver["stiffness_diagonal_error"]),
            )
            <= self.residual_limit,
        }
        return {
            "study_id": SPARSE_ID,
            "status": "PASS" if all(checks.values()) else "FAIL",
            "medium_crosscheck": {
                "mesh": [16, 16],
                "retained_dof_count": direct.solver["dynamic_reduction"]["retained_dof_count"],
                "eigh_seconds": direct_time,
                "eigsh_seconds": sparse_time,
                "relative_frequency_differences": method_differences,
                "principal_mac": method_mac,
            },
            "large_sparse": {
                "mesh": [48, 48],
                "element_count": len(large_model.elements),
                "node_count": large_model.node_count,
                "retained_dof_count": large_dofs,
                "method": large.method,
                "dense_conversion_used": large.solver["dense_conversion_used"],
                "elapsed_seconds": large_time,
                "frequencies_hz": [float(value) for value in large.frequencies_hz[:10]],
                "maximum_relative_residual": float(large.solver["max_relative_residual"]),
                "mass_orthogonality_error": float(large.solver["mass_orthogonality_error"]),
                "stiffness_diagonal_error": float(large.solver["stiffness_diagonal_error"]),
                "matrix_nnz": large.solver["dynamic_reduction"]["condensed_stiffness_nnz"],
            },
            "acceptance": {
                "method_frequency_difference_max": self.method_difference_limit,
                "method_subspace_mac_min": self.method_mac_limit,
                "minimum_large_retained_dofs": self.minimum_large_dofs,
                "relative_residual_max": self.residual_limit,
            },
            "checks": checks,
            "limitations": [
                "The large case validates sparse modal execution, not million-dof scalability.",
                "ARPACK eigsh remains a shared-library dependency and must be configuration-controlled.",
            ],
        }


def write_extended_modal_evidence(output: str | Path) -> dict[str, Any]:
    """Run all extended studies and write controlled evidence artifacts."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    free_free = FoldedShellFreeFreeStudy().run()
    curved = CurvedDistortedShellStudy().run()
    sparse = SparseModalScalingStudy().run()
    free_plot = free_free.pop("_plot")
    curved_plot = curved.pop("_plot")
    summary = {
        "campaign": "MITC4-MODAL-EXTENDED-V1",
        "status": "PASS"
        if all(item["status"] == "PASS" for item in (free_free, curved, sparse))
        else "FAIL",
        "studies": {"free_free": free_free, "curved_distorted": curved, "sparse": sparse},
        "source": git_source_state(PROJECT_ROOT),
    }
    write_json_file(target / "summary.json", summary)
    _plot_free_free(free_plot, target / f"{FREE_FREE_ID}.png")
    _plot_curved(curved_plot, target / f"{CURVED_ID}.png")
    _plot_sparse(sparse, target / f"{SPARSE_ID}.png")
    _write_free_free_report(target / f"{FREE_FREE_ID}.md", free_free)
    _write_curved_report(target / f"{CURVED_ID}.md", curved)
    _write_sparse_report(target / f"{SPARSE_ID}.md", sparse)
    write_json_file(
        target / "vnv_manifest.json",
        {
            "schema_version": 1,
            "campaign": summary["campaign"],
            "source": summary["source"],
            "files": discovered_file_entries(
                target,
                lambda _: "mitc4_modal_extended_vnv",
                exclude_names=("vnv_manifest.json",),
            ),
        },
    )
    return summary


def _folded_shell_model() -> tuple[FiniteElementModel, np.ndarray]:
    mesh = MeshFactory.rectangular_plate(8, 4, 1.0, 0.4)
    nodes = mesh.nodes.copy()
    upper = nodes[:, 1] > 1.0e-12
    nodes[upper, 2] = nodes[upper, 1]
    nodes[upper, 1] = 0.0
    return _shell_model(nodes, mesh.quads, fixed=[]), mesh.quads


def _curved_shell_model(
    nx: int,
    ny: int,
    *,
    distortion: float = 0.0,
    rotated: bool = False,
) -> tuple[FiniteElementModel, np.ndarray]:
    mesh = MeshFactory.rectangular_plate(nx, ny, 1.0, 0.6)
    parameters = mesh.nodes.copy()
    x0 = parameters[:, 0].copy()
    s0 = parameters[:, 1].copy()
    x = x0.copy()
    arc = s0.copy()
    if distortion:
        x += distortion / nx * np.sin(np.pi * x0) * np.sin(2.0 * np.pi * (s0 + 0.3) / 0.6)
        arc += (
            distortion
            * 0.6
            / ny
            * np.sin(2.0 * np.pi * x0)
            * np.sin(np.pi * (s0 + 0.3) / 0.6)
        )
    nodes = np.column_stack((x, np.sin(arc), 1.0 - np.cos(arc)))
    if rotated:
        nodes = nodes @ _rotation_matrix().T
    root = np.flatnonzero(np.isclose(x0, 0.0))
    fixed = [
        {"node": int(node), "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}
        for node in root
    ]
    return _shell_model(nodes, mesh.quads, fixed=fixed, sparse=True), mesh.quads


def _shell_model(
    nodes: np.ndarray,
    quads: np.ndarray,
    *,
    fixed: list[dict[str, object]],
    sparse: bool = False,
) -> FiniteElementModel:
    analysis: dict[str, object] = {
        "type": "modal",
        "method": "eigsh" if sparse else "eigh",
        "modes": 10,
        "dense_modal_max_dofs": 10000,
        "modal_residual_failure_tolerance": 1.0e-6,
    }
    if sparse:
        analysis.update(
            {
                "arpack_tolerance": 1.0e-10,
                "arpack_maxiter": 10000,
                "arpack_ncv": 30,
                "prefer_dense_modal": True,
            }
        )
    return FiniteElementModel.from_raw(
        analysis=analysis,
        nodes=nodes.tolist(),
        elements=[
            {"type": "MITC4", "nodes": quad.tolist(), "material": "skin"}
            for quad in quads
        ],
        materials={
            "skin": {
                "type": "shell_isotropic",
                "E": 70.0e9,
                "nu": 0.3,
                "t": 0.01,
                "density": 2700.0,
                "drilling_scale": 1.0e-4,
            }
        },
        fixed_dofs=fixed,
    )


def _analytical_rigid_modes(
    model: FiniteElementModel,
    dofs: object,
    reducer: DynamicDofReducer,
) -> np.ndarray:
    modes: list[np.ndarray] = []
    translations = ("UX", "UY", "UZ")
    rotations = ("RX", "RY", "RZ")
    for direction in translations:
        vector = np.zeros(dofs.ndof)
        for node in range(model.node_count):
            vector[dofs.index(node, direction)] = 1.0
        modes.append(reducer.reduce_state(vector))
    center = np.mean(model.nodes, axis=0)
    for axis in range(3):
        omega = np.zeros(3)
        omega[axis] = 1.0
        vector = np.zeros(dofs.ndof)
        for node, point in enumerate(model.nodes):
            displacement = np.cross(omega, point - center)
            for component, direction in enumerate(translations):
                vector[dofs.index(node, direction)] = displacement[component]
            for component, direction in enumerate(rotations):
                vector[dofs.index(node, direction)] = omega[component]
        modes.append(reducer.reduce_state(vector))
    return np.column_stack(modes)


def _mass_subspace_mac(
    analytical: np.ndarray,
    numerical: np.ndarray,
    mass: object,
) -> list[float]:
    gram = analytical.T @ (mass @ analytical)
    values, vectors = eigh(gram)
    orthonormal = analytical @ vectors @ np.diag(1.0 / np.sqrt(values))
    singular_values = np.linalg.svd(
        orthonormal.T @ (mass @ numerical), compute_uv=False
    )
    return (singular_values**2).tolist()


def _sparse_settings() -> AnalysisSettings:
    return AnalysisSettings.from_raw(
        {
            "type": "modal",
            "method": "eigsh",
            "modes": 12,
            "arpack_tolerance": 1.0e-11,
            "arpack_maxiter": 10000,
            "arpack_ncv": 36,
            "modal_residual_failure_tolerance": 1.0e-6,
        }
    )


def _modal_group_macs(first: object, second: object, node_count: int) -> list[float]:
    uz = np.asarray([first.dofs.index(node, "UZ") for node in range(node_count)])
    first_shapes = np.asarray(first.modes[uz, :10])
    second_shapes = np.asarray(second.modes[uz, :10])
    values = []
    for group in ((0,), (1, 2), (3,), (4, 5), (6, 7), (8, 9)):
        if len(group) == 1:
            a = first_shapes[:, group[0]]
            b = second_shapes[:, group[0]]
            values.append(float(abs(np.vdot(a, b)) ** 2 / (np.vdot(a, a) * np.vdot(b, b)).real))
        else:
            first_basis, _ = np.linalg.qr(first_shapes[:, group])
            second_basis, _ = np.linalg.qr(second_shapes[:, group])
            singular = np.linalg.svd(first_basis.T @ second_basis, compute_uv=False)
            values.append(float(np.min(singular) ** 2))
    return values


def _relative_errors(values: object, references: object) -> list[float]:
    values_array = np.asarray(values, dtype=float)
    references_array = np.asarray(references, dtype=float)
    return (
        np.abs(values_array - references_array)
        / np.maximum(np.abs(references_array), 1.0e-30)
    ).tolist()


def _rotation_matrix() -> np.ndarray:
    angle_z = 0.47
    angle_y = -0.31
    rz = np.array(
        [
            [np.cos(angle_z), -np.sin(angle_z), 0.0],
            [np.sin(angle_z), np.cos(angle_z), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    ry = np.array(
        [
            [np.cos(angle_y), 0.0, np.sin(angle_y)],
            [0.0, 1.0, 0.0],
            [-np.sin(angle_y), 0.0, np.cos(angle_y)],
        ]
    )
    return rz @ ry


def _mode_plot_data(model: FiniteElementModel, quads: np.ndarray, result: object) -> dict[str, Any]:
    translations = np.asarray(
        [
            [result.modes[result.dofs.index(node, name), 0] for name in ("UX", "UY", "UZ")]
            for node in range(model.node_count)
        ]
    )
    return {"nodes": model.nodes, "quads": quads, "translations": translations}


def _plot_free_free(data: dict[str, Any], path: Path) -> None:
    figure = plt.figure(figsize=(9.0, 4.4))
    geometry = figure.add_subplot(121, projection="3d")
    _draw_mesh(geometry, data["nodes"], data["quads"], color="#087f5b")
    geometry.view_init(elev=24.0, azim=-58.0)
    geometry.set_axis_off()
    geometry.set_title("Structure assemblee libre-libre")
    spectrum = figure.add_subplot(122)
    values = np.abs(np.asarray(data["eigenvalues"], dtype=float))
    spectrum.semilogy(np.arange(1, len(values) + 1), np.maximum(values, 1.0e-16), "o-")
    spectrum.axvline(6.5, color="#c92a2a", linestyle="--", label="6 modes rigides")
    spectrum.set(xlabel="numero de mode", ylabel="abs(lambda)", title="Separation rigide/elastique")
    spectrum.grid(True, which="both", alpha=0.25)
    spectrum.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _plot_curved(data: dict[str, Any], path: Path) -> None:
    figure = plt.figure(figsize=(10.0, 4.6))
    for index, (title, item) in enumerate(
        (("Maillage regulier", data["regular"]), ("Maillage distordu 20 %", data["distorted"])),
        start=1,
    ):
        axis = figure.add_subplot(1, 2, index, projection="3d")
        nodes = np.asarray(item["nodes"])
        translations = np.asarray(item["translations"])
        scale = 0.15 / max(float(np.max(np.linalg.norm(translations, axis=1))), 1.0e-30)
        _draw_mesh(axis, nodes, item["quads"], color="#adb5bd", linewidth=0.3)
        _draw_mesh(axis, nodes + scale * translations, item["quads"], color="#087f5b")
        axis.set_title(f"{title}\nmode 1, facteur {scale:.2e}")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _plot_sparse(summary: dict[str, Any], path: Path) -> None:
    medium = summary["medium_crosscheck"]
    large = summary["large_sparse"]
    figure, axes = plt.subplots(1, 2, figsize=(9.0, 4.2))
    axes[0].bar(["eigh 16x16", "eigsh 16x16", "eigsh 48x48"], [medium["eigh_seconds"], medium["eigsh_seconds"], large["elapsed_seconds"]], color=["#495057", "#087f5b", "#0b7285"])
    axes[0].set_ylabel("temps [s]")
    axes[0].tick_params(axis="x", rotation=20)
    axes[1].semilogy(range(1, 11), large["frequencies_hz"], "o-", color="#087f5b")
    axes[1].set(xlabel="mode", ylabel="frequence [Hz]", title=f"{large['retained_dof_count']} DDL actifs")
    axes[1].grid(True, which="both", alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _draw_mesh(axis: object, nodes: object, quads: object, *, color: str, linewidth: float = 0.55) -> None:
    points = np.asarray(nodes)
    for quad in np.asarray(quads, dtype=int):
        closed = np.append(quad, quad[0])
        axis.plot(*points[closed].T, color=color, linewidth=linewidth)
    axis.set_box_aspect(np.maximum(np.ptp(points, axis=0), 1.0e-3))


def _write_free_free_report(path: Path, summary: dict[str, Any]) -> None:
    metrics = summary["metrics"]
    path.write_text(
        f"""# {FREE_FREE_ID}

Statut: **{summary['status']}**.

Structure composee de deux panneaux MITC4 assembles a 90 degres, sans aucun
blocage. Le sous-espace numerique des six premieres valeurs propres est compare
aux trois translations et trois rotations rigides analytiques.

| Indicateur | Valeur | Critere |
| --- | ---: | ---: |
| Nombre de modes rigides | 6 | 6 |
| Ratio rigide / premier elastique | {metrics['rigid_to_first_elastic_ratio']:.3e} | <= 1e-8 |
| MAC principal minimal | {min(metrics['rigid_subspace_principal_mac']):.12f} | >= 0.999999 |
| Residu rigide maximal | {metrics['maximum_rigid_residual']:.3e} | <= 1e-12 |

![Structure et spectre]({FREE_FREE_ID}.png)

## Limites

{_limitations(summary)}
""",
        encoding="utf-8",
    )


def _write_curved_report(path: Path, summary: dict[str, Any]) -> None:
    metrics = summary["metrics"]
    rows = "\n".join(
        f"| {point['mesh'][0]}x{point['mesh'][1]} | {point['element_count']} | "
        + ", ".join(f"{value:.4f}" for value in point["frequencies_hz"])
        + " |"
        for point in summary["points"]
    )
    path.write_text(
        f"""# {CURVED_ID}

Statut: **{summary['status']}**.

| Maillage | Elements | Dix frequences [Hz] |
| --- | ---: | --- |
{rows}

| Indicateur | Maximum | Critere |
| --- | ---: | ---: |
| Increment du dernier raffinement | {100*max(metrics['last_mesh_increment']):.3f} % | <= 4 % |
| Sensibilite a 20 % de distorsion | {100*max(metrics['distorted_frequency_differences']):.3f} % | <= 1 % |
| Erreur apres rotation rigide | {max(metrics['rotated_frequency_differences']):.3e} | <= 1e-8 |

![Coque courbe]({CURVED_ID}.png)

## Limites

{_limitations(summary)}
""",
        encoding="utf-8",
    )


def _write_sparse_report(path: Path, summary: dict[str, Any]) -> None:
    medium = summary["medium_crosscheck"]
    large = summary["large_sparse"]
    frequencies = "\n".join(
        f"| {index} | {frequency:.6f} |"
        for index, frequency in enumerate(large["frequencies_hz"], start=1)
    )
    path.write_text(
        f"""# {SPARSE_ID}

Statut: **{summary['status']}**.

## Contre-calcul sur le modele moyen

| Indicateur | Valeur | Critere |
| --- | ---: | ---: |
| DDL actifs | {medium['retained_dof_count']} | information |
| Ecart maximal eigh/eigsh | {max(medium['relative_frequency_differences']):.3e} | <= 1e-8 |
| MAC principal minimal | {min(medium['principal_mac']):.12f} | >= 0.99999999 |

## Modele creux significatif

| Indicateur | Valeur |
| --- | ---: |
| Maillage | 48x48 |
| Elements | {large['element_count']} |
| DDL actifs | {large['retained_dof_count']} |
| Non-nuls K | {large['matrix_nnz']} |
| Methode | {large['method']} |
| Conversion dense | {large['dense_conversion_used']} |
| Temps | {large['elapsed_seconds']:.3f} s |
| Residu modal maximal | {large['maximum_relative_residual']:.3e} |

| Mode | Frequence [Hz] |
| ---: | ---: |
{frequencies}

![Verification eigsh]({SPARSE_ID}.png)

## Limites

{_limitations(summary)}
""",
        encoding="utf-8",
    )


def _limitations(summary: dict[str, Any]) -> str:
    return "\n".join(f"- {item}" for item in summary["limitations"])
