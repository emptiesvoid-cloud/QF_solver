"""Comparable-degree-of-freedom TET10 versus HEX8 benchmark."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

import matplotlib
import numpy as np
import psutil

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file


STUDY_ID = "VNV-HEX8-TET10-COMPARABLE-DOF-001"
MULTI_MODEL_STUDY_ID = "VNV-HEX8-TET-FAMILY-MULTI-MODEL-001"
HEX20_MULTI_MODEL_STUDY_ID = "VNV-HEX20-TET-FAMILY-MULTI-MODEL-001"


def run_tet10_hex8_benchmark(output_dir: str | Path | None = None) -> dict[str, object]:
    cases = {"HEX8": _hex8_model(), "TET4": _tet4_model(), "TET10": _tet10_model()}
    rows = []
    process = psutil.Process()
    for name, model in cases.items():
        rss_before = process.memory_info().rss
        started = perf_counter()
        result = solve_model(model)
        elapsed = perf_counter() - started
        rss_after = process.memory_info().rss
        audit_matrices = result.audit.to_dict().get("matrices", []) if result.audit is not None else []
        stiffness = next((matrix for matrix in audit_matrices if matrix.get("name") == "stiffness"), None)
        rows.append(
            {
                "element": name,
                "status": result.status,
                "dofs": result.dofs.ndof,
                "elements": len(model.elements),
                "solve_seconds": elapsed,
                "nnz": int(stiffness.get("nnz", 0)) if stiffness is not None else None,
                "estimated_csr_bytes": int((int(stiffness.get("nnz", 0)) * 12) + (result.dofs.ndof + 1) * 4) if stiffness is not None else None,
                "rss_before_bytes": int(rss_before),
                "rss_after_bytes": int(rss_after),
                "rss_delta_bytes": int(max(0, rss_after - rss_before)),
                "max_displacement": float(np.max(np.abs(result.displacements))),
                "equilibrium_residual": float(result.audit.equilibrium.get("free_relative_residual", 0.0)),
            }
        )
    dofs_match = rows[0]["dofs"] == rows[1]["dofs"]
    summary = {
        "study_id": STUDY_ID,
        "status": "PASS_INTERNAL" if all(row["status"] == "PASS" for row in rows) and dofs_match else "FAIL",
        "comparison_basis": "same unit cube, boundary conditions, point load and 81 structural DOF",
        "rows": rows,
        "dofs_match": dofs_match,
        "external_accuracy_reference": "OPEN",
        "limitations": ["This is a performance and same-problem comparison, not an external certification."],
    }
    if output_dir is not None:
        target = Path(output_dir)
        target.mkdir(parents=True, exist_ok=True)
        write_json_file(target / "summary.json", summary)
    return summary


def run_multi_model_benchmark(output_dir: str | Path | None = None) -> dict[str, object]:
    """Compare TET4, TET10 and HEX8 on three distinct mechanical models."""
    rows: list[dict[str, object]] = []
    for case_name, dimensions, distortion in (
        ("unit_cube", (1.0, 1.0, 1.0), 0.0),
        ("slender_beam", (3.0, 0.5, 0.5), 0.0),
        ("distorted_cube", (1.0, 1.0, 1.0), 0.20),
    ):
        nodes = _structured_nodes(*dimensions, distortion=distortion)
        for family in ("HEX8", "TET4", "TET10"):
            model = _model_from_family(nodes, family, dimensions[0])
            rows.append(_benchmark_row(case_name, family, model))
    status = "PASS_INTERNAL" if all(row["status"] == "PASS" for row in rows) else "FAIL"
    summary: dict[str, object] = {
        "study_id": MULTI_MODEL_STUDY_ID,
        "status": status,
        "model_count": 3,
        "models": ["unit_cube", "slender_beam", "distorted_cube"],
        "element_families": ["TET4", "TET10", "HEX8"],
        "comparison_basis": "three same-geometry cases with common boundary/load convention per case",
        "rows": rows,
        "limitations": [
            "The three cases use a compact 2x2x2 structured partition; this is a robustness matrix, not a large-scale performance campaign.",
            "TET and HEX degrees of freedom are reported explicitly and are not asserted equal for every case.",
            "External certification remains covered by the separate CalculiX and Code_Aster same-mesh studies.",
        ],
    }
    if output_dir is not None:
        target = Path(output_dir)
        target.mkdir(parents=True, exist_ok=True)
        write_json_file(target / "summary.json", summary)
        (target / "report.md").write_text(_multi_model_report(summary), encoding="utf-8")
        _multi_model_plot(target, rows)
    return summary


def run_hex20_multi_model_benchmark(output_dir: str | Path | None = None) -> dict[str, object]:
    """Compare TET4, TET10, HEX8 and HEX20 on three common geometries."""
    rows: list[dict[str, object]] = []
    families = ("TET4", "TET10", "HEX8", "HEX20")
    cases = (
        ("unit_cube", (1.0, 1.0, 1.0), 0.0),
        ("slender_beam", (3.0, 0.5, 0.5), 0.0),
        ("distorted_cube", (1.0, 1.0, 1.0), 0.20),
    )
    for case_name, dimensions, distortion in cases:
        source_nodes = _structured_nodes(*dimensions, distortion=distortion)
        for family in families:
            nodes = [list(point) for point in source_nodes]
            if family == "HEX20":
                model = _hex20_model_from_nodes(nodes, dimensions[0])
            else:
                model = _model_from_family(nodes, family, dimensions[0])
            rows.append(_benchmark_row(case_name, family, model))
    summary: dict[str, object] = {
        "study_id": HEX20_MULTI_MODEL_STUDY_ID,
        "status": "PASS_INTERNAL" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "model_count": 3,
        "models": [case[0] for case in cases],
        "element_families": list(families),
        "comparison_basis": "three common structured 2x2x2 geometries with explicit DDL and common boundary/load convention",
        "rows": rows,
        "external_correlation": {
            "status": "OPEN",
            "required": True,
            "targets": ["CalculiX C3D20", "Code_Aster HEXA20"],
        },
        "limitations": [
            "The campaign is a compact internal robustness and scaling comparison, not a production-size benchmark.",
            "TET and HEX meshes have different interpolation orders and therefore their DDL counts are reported, not equalized.",
            "External correlation remains a separate gate and is not inferred from the internal PASS.",
        ],
    }
    if output_dir is not None:
        target = Path(output_dir)
        target.mkdir(parents=True, exist_ok=True)
        write_json_file(target / "summary.json", summary)
        (target / "report.md").write_text(_hex20_multi_model_report(summary), encoding="utf-8")
        _hex20_multi_model_plot(target, rows)
    return summary


def _benchmark_row(case_name: str, family: str, model: FiniteElementModel) -> dict[str, object]:
    process = psutil.Process()
    rss_before = process.memory_info().rss
    started = perf_counter()
    result = solve_model(model)
    elapsed = perf_counter() - started
    rss_after = process.memory_info().rss
    audit_matrices = result.audit.to_dict().get("matrices", []) if result.audit is not None else []
    stiffness = next((matrix for matrix in audit_matrices if matrix.get("name") == "stiffness"), None)
    residual = float(result.audit.equilibrium.get("free_relative_residual", np.inf)) if result.audit is not None else np.inf
    return {
        "model": case_name,
        "element": family,
        "status": result.status,
        "dofs": result.dofs.ndof,
        "elements": len(model.elements),
        "solve_seconds": elapsed,
        "nnz": int(stiffness.get("nnz", 0)) if stiffness is not None else None,
        "estimated_csr_bytes": int((int(stiffness.get("nnz", 0)) * 12) + (result.dofs.ndof + 1) * 4) if stiffness is not None else None,
        "rss_delta_bytes": int(max(0, rss_after - rss_before)),
        "max_displacement": float(np.max(np.abs(result.displacements))),
        "equilibrium_residual": residual,
    }


def _structured_nodes(length: float, width: float, height: float, *, distortion: float) -> list[list[float]]:
    nodes: list[list[float]] = []
    for k in range(3):
        for j in range(3):
            for i in range(3):
                sx, sy, sz = i / 2.0, j / 2.0, k / 2.0
                y = width * sy
                x = length * sx + distortion * length * sx * sy
                z = height * sz + 0.05 * distortion * height * sx * sy
                nodes.append([x, y, z])
    return nodes


def _model_from_family(nodes: list[list[float]], family: str, length: float) -> FiniteElementModel:
    def node(i: int, j: int, k: int) -> int:
        return i + 3 * j + 9 * k

    cells = []
    for k in range(2):
        for j in range(2):
            for i in range(2):
                cells.append((node(i, j, k), node(i + 1, j, k), node(i + 1, j + 1, k), node(i, j + 1, k), node(i, j, k + 1), node(i + 1, j, k + 1), node(i + 1, j + 1, k + 1), node(i, j + 1, k + 1)))
    if family == "HEX8":
        elements = [{"type": family, "nodes": list(cell), "material": "solid"} for cell in cells]
    else:
        patterns = ((0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6), (0, 7, 4, 6), (0, 4, 5, 6), (0, 5, 1, 6))
        if family == "TET4":
            elements = [{"type": family, "nodes": [cell[index] for index in pattern], "material": "solid"} for cell in cells for pattern in patterns]
        else:
            tet_edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
            edge_keys = sorted({
                tuple(sorted((cell[pattern[a]], cell[pattern[b]])))
                for cell in cells
                for pattern in patterns
                for a, b in tet_edges
            })
            edge_nodes = {edge: len(nodes) + index for index, edge in enumerate(edge_keys)}
            nodes.extend((0.5 * (np.asarray(nodes[a]) + np.asarray(nodes[b]))).tolist() for a, b in edge_keys)
            local_edges = tet_edges
            elements = []
            for cell in cells:
                for pattern in patterns:
                    tet = [cell[index] for index in pattern]
                    mids = [edge_nodes[tuple(sorted((tet[a], tet[b])))] for a, b in local_edges]
                    elements.append({"type": family, "nodes": tet + mids, "material": "solid"})
    fixed = [{"node": index, "dofs": ["UX", "UY", "UZ"]} for index, point in enumerate(nodes) if abs(float(point[0])) < 1.0e-12]
    load_node = next(index for index, point in enumerate(nodes) if np.allclose(point, [length, 0.0, 0.0]))
    return FiniteElementModel.from_raw(
        nodes=nodes,
        elements=elements,
        materials={"solid": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}},
        fixed_dofs=fixed,
        loads=[{"node": load_node, "dof": "UX", "value": 1.0}],
        analysis="linear_static",
    )


def _hex20_model_from_nodes(nodes: list[list[float]], length: float) -> FiniteElementModel:
    """Build a shared-edge HEX20 mesh over the same 2x2x2 corner partition."""
    def node(i: int, j: int, k: int) -> int:
        return i + 3 * j + 9 * k

    corner_cells = []
    for k in range(2):
        for j in range(2):
            for i in range(2):
                corner_cells.append(
                    (
                        node(i, j, k),
                        node(i + 1, j, k),
                        node(i + 1, j + 1, k),
                        node(i, j + 1, k),
                        node(i, j, k + 1),
                        node(i + 1, j, k + 1),
                        node(i + 1, j + 1, k + 1),
                        node(i, j + 1, k + 1),
                    )
                )
    local_edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
    edge_nodes: dict[tuple[int, int], int] = {}
    for corners in corner_cells:
        for first, second in local_edges:
            key = tuple(sorted((corners[first], corners[second])))
            if key not in edge_nodes:
                edge_nodes[key] = len(nodes)
                nodes.append((0.5 * (np.asarray(nodes[key[0]]) + np.asarray(nodes[key[1]]))).tolist())
    elements = []
    for corners in corner_cells:
        mids = [edge_nodes[tuple(sorted((corners[first], corners[second])))] for first, second in local_edges]
        elements.append({"type": "HEX20", "nodes": list(corners) + mids, "material": "solid"})
    fixed = [{"node": index, "dofs": ["UX", "UY", "UZ"]} for index, point in enumerate(nodes) if abs(float(point[0])) < 1.0e-12]
    load_node = next(index for index, point in enumerate(nodes) if np.allclose(point, [length, 0.0, 0.0]))
    return FiniteElementModel.from_raw(
        nodes=nodes,
        elements=elements,
        materials={"solid": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}},
        fixed_dofs=fixed,
        loads=[{"node": load_node, "dof": "UX", "value": 1.0}],
        analysis="linear_static",
    )


def _hex20_multi_model_report(summary: dict[str, object]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut interne : **{summary['status']}**",
        "",
        "La comparaison couvre trois modèles communs et les quatre familles TET4/TET10/HEX8/HEX20.",
        "",
        "| Modèle | Élément | DDL | Éléments | Temps (s) | nnz | CSR estimé (octets) | Delta RSS (octets) | Résidu |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["rows"]:
        lines.append(
            f"| {row['model']} | {row['element']} | {row['dofs']} | {row['elements']} | "
            f"{row['solve_seconds']:.6e} | {row['nnz']} | {row['estimated_csr_bytes']} | "
            f"{row['rss_delta_bytes']} | {row['equilibrium_residual']:.6e} |"
        )
    lines.extend(
        [
            "",
            "## Corrélation externe",
            "",
            "Statut : **OPEN**. Les decks CalculiX C3D20 et Code_Aster HEXA20 doivent être exécutés séparément.",
            "",
            "Une réussite interne ne vaut pas corrélation externe et ne ferme pas la gate Owner.",
            "",
        ]
    )
    return "\n".join(lines)


def _hex20_multi_model_plot(output: Path, rows: list[dict[str, object]]) -> None:
    models = ["unit_cube", "slender_beam", "distorted_cube"]
    families = ["TET4", "TET10", "HEX8", "HEX20"]
    figure, axes = plt.subplots(1, 3, figsize=(14.0, 4.2), constrained_layout=True)
    for axis, metric, title, ylabel in (
        (axes[0], "solve_seconds", "Temps de résolution", "secondes"),
        (axes[1], "nnz", "Sparsité", "nnz"),
        (axes[2], "equilibrium_residual", "Résidu d'équilibre", "résidu relatif"),
    ):
        positions = np.arange(len(models))
        width = 0.18
        for offset, family in enumerate(families):
            values = [
                next(float(row[metric]) for row in rows if row["model"] == model and row["element"] == family)
                for model in models
            ]
            axis.bar(positions + (offset - 1.5) * width, values, width, label=family)
        axis.set_xticks(positions, ["cube", "poutre", "distordu"])
        axis.set_title(title)
        axis.set_ylabel(ylabel)
        axis.grid(axis="y", alpha=0.25)
        if metric == "equilibrium_residual":
            axis.set_yscale("log")
    axes[0].legend(fontsize=8)
    figure.savefig(output / "tet_hex8_hex20_multi_model_comparison.png", dpi=180)
    plt.close(figure)


def _multi_model_report(summary: dict[str, object]) -> str:
    lines = [f"# {summary['study_id']}", "", f"Statut : **{summary['status']}**", "", "| Modèle | Élément | DDL | Eléments | Temps (s) | nnz | Résidu |", "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for row in summary["rows"]:
        lines.append(f"| {row['model']} | {row['element']} | {row['dofs']} | {row['elements']} | {row['solve_seconds']:.6e} | {row['nnz']} | {row['equilibrium_residual']:.6e} |")
    lines.extend(["", "![Comparaison TET/HEX](tet_hex_multi_model_comparison.png)", "", "Trois modèles distincts sont comparés; les limites sont celles du résumé JSON.", ""])
    return "\n".join(lines)


def _multi_model_plot(output: Path, rows: list[dict[str, object]]) -> None:
    models = ["unit_cube", "slender_beam", "distorted_cube"]
    families = ["TET4", "TET10", "HEX8"]
    figure, axes = plt.subplots(1, 3, figsize=(13.0, 4.2), constrained_layout=True)
    for axis, metric, title, ylabel in (
        (axes[0], "solve_seconds", "Temps de résolution", "secondes"),
        (axes[1], "nnz", "Sparsité", "nnz"),
        (axes[2], "equilibrium_residual", "Résidu d'équilibre", "résidu relatif"),
    ):
        positions = np.arange(len(models))
        width = 0.24
        for offset, family in enumerate(families):
            values = [next(float(row[metric]) for row in rows if row["model"] == model and row["element"] == family) for model in models]
            axis.bar(positions + (offset - 1) * width, values, width, label=family)
        axis.set_xticks(positions, ["cube", "poutre", "distordu"])
        axis.set_title(title)
        axis.set_ylabel(ylabel)
        axis.grid(axis="y", alpha=0.25)
        if metric == "equilibrium_residual":
            axis.set_yscale("log")
    axes[0].legend(fontsize=8)
    figure.savefig(output / "tet_hex_multi_model_comparison.png", dpi=180)
    plt.close(figure)


def _base_model(
    nodes: list[list[float]],
    elements: list[dict[str, object]],
    *,
    load_value: float = 1.0,
    young_modulus: float = 210.0e9,
) -> FiniteElementModel:
    fixed = [{"node": index, "dofs": ["UX", "UY", "UZ"]} for index, point in enumerate(nodes) if abs(point[0]) < 1.0e-12]
    load_node = next(index for index, point in enumerate(nodes) if np.allclose(point, [1.0, 0.0, 0.0]))
    return FiniteElementModel.from_raw(
        nodes=nodes,
        elements=elements,
        materials={"solid": {"type": "isotropic_3d", "E": young_modulus, "nu": 0.3, "density": 7800.0}},
        fixed_dofs=fixed,
        loads=[{"node": load_node, "dof": "UX", "value": load_value}],
        analysis="linear_static",
    )


def _hex8_model(*, load_value: float = 1.0, young_modulus: float = 210.0e9) -> FiniteElementModel:
    nodes = []
    for k in range(3):
        for j in range(3):
            for i in range(3):
                nodes.append([i / 2.0, j / 2.0, k / 2.0])
    def node(i: int, j: int, k: int) -> int:
        return i + 3 * j + 9 * k
    elements = []
    for k in range(2):
        for j in range(2):
            for i in range(2):
                elements.append({"type": "HEX8", "nodes": [node(i, j, k), node(i + 1, j, k), node(i + 1, j + 1, k), node(i, j + 1, k), node(i, j, k + 1), node(i + 1, j, k + 1), node(i + 1, j + 1, k + 1), node(i, j + 1, k + 1)], "material": "solid"})
    return _base_model(nodes, elements, load_value=load_value, young_modulus=young_modulus)


def _tet10_model() -> FiniteElementModel:
    corners = np.asarray([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]], dtype=float)
    tets = [(0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6), (0, 7, 4, 6), (0, 4, 5, 6), (0, 5, 1, 6)]
    edges = sorted({tuple(sorted((tet[i], tet[j]))) for tet in tets for i in range(4) for j in range(i + 1, 4)})
    edge_nodes = {edge: len(corners) + index for index, edge in enumerate(edges)}
    nodes = corners.tolist() + [(0.5 * (corners[a] + corners[b])).tolist() for a, b in edges]
    elements = []
    local_edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
    for tet in tets:
        mids = [edge_nodes[tuple(sorted((tet[a], tet[b])))] for a, b in local_edges]
        elements.append({"type": "TET10", "nodes": list(tet) + mids, "material": "solid"})
    return _base_model(nodes, elements)


def _tet4_model() -> FiniteElementModel:
    """Build the same 2x2x2 cube partition with linear tetrahedra."""
    nodes = []
    for k in range(3):
        for j in range(3):
            for i in range(3):
                nodes.append([i / 2.0, j / 2.0, k / 2.0])

    def node(i: int, j: int, k: int) -> int:
        return i + 3 * j + 9 * k

    patterns = ((0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6), (0, 7, 4, 6), (0, 4, 5, 6), (0, 5, 1, 6))
    elements = []
    for k in range(2):
        for j in range(2):
            for i in range(2):
                cube = (
                    node(i, j, k),
                    node(i + 1, j, k),
                    node(i + 1, j + 1, k),
                    node(i, j + 1, k),
                    node(i, j, k + 1),
                    node(i + 1, j, k + 1),
                    node(i + 1, j + 1, k + 1),
                    node(i, j + 1, k + 1),
                )
                elements.extend({"type": "TET4", "nodes": [cube[index] for index in pattern], "material": "solid"} for pattern in patterns)
    return _base_model(nodes, elements)
