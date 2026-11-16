"""Independent Reissner-Mindlin continuum Ritz calculation and figures."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

MODE_ORDERS = ((1, 1), (1, 2), (2, 1), (2, 2))


def _weighted_mac(first: np.ndarray, second: np.ndarray, weights: np.ndarray) -> float:
    first = np.asarray(first, dtype=float).reshape(-1)
    second = np.asarray(second, dtype=float).reshape(-1)
    weights = np.asarray(weights, dtype=float).reshape(-1)
    numerator = float(np.sum(weights * first * second)) ** 2
    denominator = float(np.sum(weights * first * first) * np.sum(weights * second * second))
    if denominator <= np.finfo(float).tiny:
        raise ValueError("weighted MAC is undefined for a zero field")
    return numerator / denominator


def _weighted_subspace_mac_min(first: np.ndarray, second: np.ndarray, weights: np.ndarray) -> float:
    root_weights = np.sqrt(np.asarray(weights, dtype=float))[:, None]
    first_q, _ = np.linalg.qr(np.asarray(first, dtype=float) * root_weights)
    second_q, _ = np.linalg.qr(np.asarray(second, dtype=float) * root_weights)
    singular_values = np.linalg.svd(first_q.T @ second_q, compute_uv=False)
    return float(np.min(singular_values) ** 2)


def _legendre_tensor_basis(
    x: np.ndarray, y: np.ndarray, degree: int, length: float, width: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    from numpy.polynomial.legendre import legder, legval

    xi = 2.0 * np.asarray(x) / length - 1.0
    eta = 2.0 * (np.asarray(y) + 0.5 * width) / width - 1.0
    lx = np.polynomial.legendre.legvander(xi, degree)
    ly = np.polynomial.legendre.legvander(eta, degree)
    dlx = np.zeros_like(lx)
    dly = np.zeros_like(ly)
    for order in range(1, degree + 1):
        coeff = np.zeros(order + 1)
        coeff[order] = 1.0
        dlx[:, order] = legval(xi, legder(coeff)) * (2.0 / length)
        dly[:, order] = legval(eta, legder(coeff)) * (2.0 / width)
    pairs = [(i, j) for i in range(degree + 1) for j in range(degree + 1)]
    values = np.column_stack([lx[:, i] * ly[:, j] for i, j in pairs])
    dx = np.column_stack([dlx[:, i] * ly[:, j] for i, j in pairs])
    dy = np.column_stack([lx[:, i] * dly[:, j] for i, j in pairs])
    return values, dx, dy


def _sine_tensor_basis(
    x: np.ndarray, y: np.ndarray, order: int, length: float, width: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=float)
    y_positive = np.asarray(y, dtype=float) + 0.5 * width
    modes = [(m, n) for m in range(1, order + 1) for n in range(1, order + 1)]
    value_columns = []
    dx_columns = []
    dy_columns = []
    for m, n in modes:
        sx = np.sin(m * math.pi * x / length)
        sy = np.sin(n * math.pi * y_positive / width)
        value_columns.append(sx * sy)
        dx_columns.append((m * math.pi / length) * np.cos(m * math.pi * x / length) * sy)
        dy_columns.append(sx * (n * math.pi / width) * np.cos(n * math.pi * y_positive / width))
    return np.column_stack(value_columns), np.column_stack(dx_columns), np.column_stack(dy_columns)


def _gram(first: np.ndarray, second: np.ndarray, weights: np.ndarray) -> np.ndarray:
    return first.T @ (second * weights[:, None])


@dataclass(frozen=True)
class RitzResult:
    frequencies_hz: np.ndarray
    eigenvectors: np.ndarray
    transverse_basis_count: int
    rotation_basis_count: int
    system_dimension: int
    quadrature_order: int
    rotation_degree: int
    transverse_order: int


def _mindlin_ritz(
    model: dict[str, Any],
    transverse_order: int,
    rotation_degree: int,
    quadrature_order: int,
) -> RitzResult:
    """Solve a soft-support Reissner--Mindlin Ritz problem, independent of QF."""
    from scipy.linalg import eigh

    geometry = model["geometry"]
    material = model["material"]
    length = float(geometry["length_m"])
    width = float(geometry["width_m"])
    thickness = float(geometry["thickness_m"])
    young = float(material["young_modulus_pa"])
    poisson = float(material["poisson_ratio"])
    density = float(material["density_kg_m3"])
    shear_factor = float(material["transverse_shear_factor"])
    shear_modulus = young / (2.0 * (1.0 + poisson))
    rigidity = young * thickness**3 / (12.0 * (1.0 - poisson**2))
    shear_rigidity = shear_factor * shear_modulus * thickness

    gauss_x, gauss_w = np.polynomial.legendre.leggauss(quadrature_order)
    x1 = 0.5 * length * (gauss_x + 1.0)
    y1 = 0.5 * width * (gauss_x + 1.0) - 0.5 * width
    qx, qy = np.meshgrid(x1, y1, indexing="ij")
    weights = (0.25 * length * width * np.outer(gauss_w, gauss_w)).reshape(-1)
    qx = qx.reshape(-1)
    qy = qy.reshape(-1)

    w, wx, wy = _sine_tensor_basis(qx, qy, transverse_order, length, width)
    rotation, rotation_x, rotation_y = _legendre_tensor_basis(qx, qy, rotation_degree, length, width)
    nw = w.shape[1]
    nr = rotation.shape[1]
    dimension = nw + 2 * nr
    stiffness = np.zeros((dimension, dimension), dtype=float)
    mass = np.zeros_like(stiffness)
    w_slice = slice(0, nw)
    rx_slice = slice(nw, nw + nr)
    ry_slice = slice(nw + nr, dimension)

    kww = shear_rigidity * (_gram(wx, wx, weights) + _gram(wy, wy, weights))
    kwx = shear_rigidity * _gram(wx, rotation, weights)
    kwy = shear_rigidity * _gram(wy, rotation, weights)
    kxx = rigidity * (
        _gram(rotation_x, rotation_x, weights) + 0.5 * (1.0 - poisson) * _gram(rotation_y, rotation_y, weights)
    ) + shear_rigidity * _gram(rotation, rotation, weights)
    kyy = rigidity * (
        _gram(rotation_y, rotation_y, weights) + 0.5 * (1.0 - poisson) * _gram(rotation_x, rotation_x, weights)
    ) + shear_rigidity * _gram(rotation, rotation, weights)
    kxy = rigidity * (
        poisson * _gram(rotation_x, rotation_y, weights)
        + 0.5 * (1.0 - poisson) * _gram(rotation_y, rotation_x, weights)
    )

    stiffness[w_slice, w_slice] = kww
    stiffness[w_slice, rx_slice] = kwx
    stiffness[rx_slice, w_slice] = kwx.T
    stiffness[w_slice, ry_slice] = kwy
    stiffness[ry_slice, w_slice] = kwy.T
    stiffness[rx_slice, rx_slice] = kxx
    stiffness[ry_slice, ry_slice] = kyy
    stiffness[rx_slice, ry_slice] = kxy
    stiffness[ry_slice, rx_slice] = kxy.T

    areal_mass = density * thickness
    rotary_mass = density * thickness**3 / 12.0
    mass[w_slice, w_slice] = areal_mass * _gram(w, w, weights)
    mass[rx_slice, rx_slice] = rotary_mass * _gram(rotation, rotation, weights)
    mass[ry_slice, ry_slice] = rotary_mass * _gram(rotation, rotation, weights)

    eigenvalues, eigenvectors = eigh(stiffness, mass, subset_by_index=(0, 5), driver="gvx", check_finite=True)
    if not np.all(np.isfinite(eigenvalues)) or np.min(eigenvalues) <= 0.0:
        raise ValueError("independent Ritz eigenproblem returned nonpositive eigenvalues")
    frequencies = np.sqrt(eigenvalues) / (2.0 * math.pi)
    return RitzResult(
        frequencies_hz=frequencies,
        eigenvectors=eigenvectors,
        transverse_basis_count=nw,
        rotation_basis_count=nr,
        system_dimension=dimension,
        quadrature_order=quadrature_order,
        rotation_degree=rotation_degree,
        transverse_order=transverse_order,
    )


def _build_ritz_sweep(model: dict[str, Any], contract: dict[str, Any]) -> tuple[list[dict[str, Any]], RitzResult]:
    bounds = contract["bounded_run"]
    quadrature = int(bounds["max_quadrature_points_per_axis"])
    pmax = int(bounds["max_rotation_polynomial_degree"])
    nwmax = int(bounds["max_transverse_harmonic_order"])
    sweep: list[tuple[int, int, str]] = [(5, degree, "rotation_degree_refinement") for degree in (4, 8, 12, 16, pmax)]
    sweep.extend((order, pmax, "transverse_harmonic_refinement") for order in (3, nwmax))
    results: list[dict[str, Any]] = []
    cache: dict[tuple[int, int], RitzResult] = {}
    for nw, degree, sequence in sweep:
        key = (nw, degree)
        if key not in cache:
            result = _mindlin_ritz(model, nw, degree, quadrature)
            if result.system_dimension > int(bounds["max_dense_generalized_system_dimension"]):
                raise ValueError("Ritz system dimension exceeds the predeclared bound")
            cache[key] = result
        result = cache[key]
        results.append(
            {
                "sequence": sequence,
                "transverse_order": nw,
                "rotation_degree": degree,
                "quadrature_order_per_axis": quadrature,
                "system_dimension": result.system_dimension,
                "frequencies_hz": [float(value) for value in result.frequencies_hz[:4]],
                "is_highest_basis_reference": nw == nwmax and degree == pmax,
            }
        )
    _check_nested_ritz_monotonicity(results)
    return results, cache[(nwmax, pmax)]


def _check_nested_ritz_monotonicity(rows: list[dict[str, Any]]) -> None:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row["sequence"]), []).append(row)
    for name, sequence in groups.items():
        for previous, current in zip(sequence, sequence[1:]):
            old = np.asarray(previous["frequencies_hz"])
            new = np.asarray(current["frequencies_hz"])
            relative_increase = (new - old) / np.maximum(np.abs(old), np.finfo(float).tiny)
            if np.any(relative_increase > 1.0e-8):
                raise ValueError(f"nested Ritz sequence {name} increased beyond 1e-8")


def _quad_gauss_samples(
    arrays: dict[str, np.ndarray], qf_modes: np.ndarray, model: dict[str, Any], order: int = 4
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    nodes = arrays["nodes"]
    quads = arrays["quads"]
    xi, wi = np.polynomial.legendre.leggauss(order)
    local_points = [(a, b, wa * wb) for a, wa in zip(xi, wi) for b, wb in zip(xi, wi)]
    points: list[tuple[float, float]] = []
    weights: list[float] = []
    values: list[np.ndarray] = []
    for quad in quads:
        xy = nodes[quad, :2]
        for xip, etap, weight in local_points:
            shape = np.asarray(
                [
                    0.25 * (1.0 - xip) * (1.0 - etap),
                    0.25 * (1.0 + xip) * (1.0 - etap),
                    0.25 * (1.0 + xip) * (1.0 + etap),
                    0.25 * (1.0 - xip) * (1.0 + etap),
                ]
            )
            dxi = np.asarray([-(1.0 - etap), (1.0 - etap), (1.0 + etap), -(1.0 + etap)]) * 0.25
            deta = np.asarray([-(1.0 - xip), -(1.0 + xip), (1.0 + xip), (1.0 - xip)]) * 0.25
            jacobian = np.asarray([dxi @ xy, deta @ xy]).T
            determinant = float(np.linalg.det(jacobian))
            if determinant <= 0.0:
                raise ValueError("bilinear QF shape interpolation encountered nonpositive Jacobian")
            point = shape @ xy
            points.append((float(point[0]), float(point[1])))
            weights.append(weight * determinant)
            values.append(shape @ qf_modes[quad, :])
    return np.asarray(points), np.asarray(weights), np.asarray(values)


def _reference_fields_at(points: np.ndarray, result: RitzResult, model: dict[str, Any]) -> np.ndarray:
    width = float(model["geometry"]["width_m"])
    length = float(model["geometry"]["length_m"])
    basis, _, _ = _sine_tensor_basis(points[:, 0], points[:, 1], result.transverse_order, length, width)
    return basis @ result.eigenvectors[: result.transverse_basis_count, :4]


def _write_frequency_figure(path: Path, mesh_rows: list[dict[str, Any]], ritz: RitzResult, navier: np.ndarray) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
    sizes = [row["mesh_size"] for row in mesh_rows]
    for mode_index, axis in enumerate(axes.flat):
        values = [row["candidate_frequencies_hz"][mode_index] for row in mesh_rows]
        axis.plot(sizes, values, "o-", label="QF Solver J5B candidate")
        axis.axhline(
            ritz.frequencies_hz[mode_index],
            color="tab:green",
            linestyle="--",
            label="Soft-support Mindlin Ritz (largest basis)",
        )
        axis.axhline(navier[mode_index], color="tab:gray", linestyle=":", label="Kirchhoff/Navier")
        axis.set_title(f"Mode order {MODE_ORDERS[mode_index]}")
        axis.set_xlabel("MITC4 mesh divisions per edge")
        axis.set_ylabel("Frequency (Hz)")
        axis.grid(True, alpha=0.25)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="outside lower center", ncol=3, fontsize=8)
    figure.suptitle("J5B candidates and independent plate references (diagnostic)")
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _grid_from_nodes(nodes: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x_levels = np.unique(nodes[:, 0])
    y_levels = np.unique(nodes[:, 1])
    field = np.empty((len(y_levels), len(x_levels)), dtype=float)
    for index, (x, y) in enumerate(nodes[:, :2]):
        ix = int(np.argmin(np.abs(x_levels - x)))
        iy = int(np.argmin(np.abs(y_levels - y)))
        field[iy, ix] = values[index]
    return x_levels, y_levels, field


def _write_shape_figure(
    path: Path,
    arrays: dict[str, np.ndarray],
    result: RitzResult,
    model: dict[str, Any],
) -> None:
    nodes = arrays["nodes"]
    qf_modes = arrays["translations"][:, 2, :4]
    x = np.linspace(0.0, float(model["geometry"]["length_m"]), 121)
    y = np.linspace(-0.5 * float(model["geometry"]["width_m"]), 0.5 * float(model["geometry"]["width_m"]), 121)
    xx, yy = np.meshgrid(x, y)
    points = np.column_stack((xx.reshape(-1), yy.reshape(-1)))
    ref_all = _reference_fields_at(points, result, model)
    qf_points, weights, qf_quadrature = _quad_gauss_samples(arrays, qf_modes, model)
    qf_pair = qf_quadrature[:, 1:3]
    qf_pair_gram = qf_pair.T @ (qf_pair * weights[:, None])
    # Use the reference's transverse field at the integration points for a
    # stable visualization within the nearly repeated QF two-mode subspace.
    reference_at_quadrature = _reference_fields_at(qf_points, result, model)[:, 1]
    qf_pair_cross = qf_pair.T @ (reference_at_quadrature * weights)
    alignment_coefficients = np.linalg.solve(qf_pair_gram, qf_pair_cross)
    aligned_nodes = qf_modes[:, 1:3] @ alignment_coefficients
    display_modes = np.column_stack((qf_modes[:, 0], aligned_nodes))
    mode_labels = ("(1,1) first mode", "repeated subspace aligned to Ritz (1,2); not one raw eigenvector")
    fig, axes = plt.subplots(2, 2, figsize=(10, 8), constrained_layout=True)
    for mode_index, mode_label in enumerate(mode_labels):
        gx, gy, qf_grid = _grid_from_nodes(nodes, display_modes[:, mode_index])
        qf_norm = qf_grid / max(float(np.max(np.abs(qf_grid))), np.finfo(float).tiny)
        ritz_grid = ref_all[:, mode_index].reshape(yy.shape)
        ritz_grid = ritz_grid / max(float(np.max(np.abs(ritz_grid))), np.finfo(float).tiny)
        for column, (axis, field, title) in enumerate(
            (
                (axes[0, mode_index], qf_norm, "J5B QF candidate"),
                (axes[1, mode_index], ritz_grid, "Mindlin soft-support Ritz"),
            )
        ):
            if column == 0:
                contour = axis.contourf(gx, gy, field, levels=21, cmap="coolwarm", vmin=-1.0, vmax=1.0)
            else:
                contour = axis.contourf(x, y, field, levels=21, cmap="coolwarm", vmin=-1.0, vmax=1.0)
            axis.set_aspect("equal")
            axis.set_xlabel("x (m)")
            axis.set_ylabel("y (m)")
            axis.set_title(f"{title}\n{mode_label}")
            fig.colorbar(contour, ax=axis, shrink=0.82, label="Normalized transverse displacement")
    fig.suptitle("Mode-shape comparison; amplitudes normalized independently")
    fig.savefig(path, dpi=160)
    plt.close(fig)
