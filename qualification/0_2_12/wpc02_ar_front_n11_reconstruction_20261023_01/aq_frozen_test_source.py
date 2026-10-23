"""Manufactured partially-active frozen-face TET4 contact verification.

The exact elastic field defines a zero-gap/contact-pressure patch on x<a and
a positive gap/zero pressure region on x>a. Loads follow from the continuum
stress. The test independently assembles B.T D B and a KKT reference; it does
not seed the production active set. This is a bounded manufactured benchmark,
not a natural-load or general surface-contact qualification.
"""
from __future__ import annotations

import json
from collections import Counter
from itertools import combinations

import numpy as np
from scipy.optimize import nnls

from solveur.contact.experimental_distributed_frozen import (
    DistributedContactControls,
    DistributedTet4Case,
    DistributedContactStepper,
    SlaveContactPoint,
    assemble_tet4_distributed_contact,
)
from solveur.contact.experimental_regular_face import (
    RegularFaceTolerances,
    RegularPlanarFace,
)


E = 3.0e6
MU = E / 2.0
H = 1.0
WIDTH_Y_M = 1.0
GAP = 1.0e-3
AMP = 1.0e-5
GAP_CURVATURE_M = 1.0e-3
PRESSURE_CURVATURE_PA_PER_M2 = 4.0e3
FRONT_X_M = 0.5
# The front aligns with every x-cell boundary. These anisotropic levels keep
# the manufactured positive-part fields polynomial within each integration
# cell while staying inside the adapter's 384-DOF/32-row limits.
LEVELS = ((2, 1, 1), (4, 2, 2), (6, 3, 3))
GEOM = RegularFaceTolerances(
    length_abs_m=1.0e-10,
    length_rel=1.0e-10,
    tie_abs_m=1.0e-10,
    normal_alignment=1.0e-10,
)
CTRL = DistributedContactControls(
    length_scale_m=1.0,
    force_scale_n=1.0e3,
    gap_tolerance_m=1.0e-10,
    force_tolerance_n=1.0e-7,
    complementarity_tolerance_nm=1.0e-10,
    maximum_condition_number=1.0e12,
    maximum_pivots=128,
)


def _node(i: int, j: int, k: int, nx: int, ny: int) -> int:
    return (k * (ny + 1) + j) * (nx + 1) + i


def _mesh(level):
    nx, ny, nz = level
    xyz = np.asarray([
        (i / nx, j / ny, GAP + H * k / nz)
        for k in range(nz + 1)
        for j in range(ny + 1)
        for i in range(nx + 1)
    ], dtype=float)
    local_tets = (
        (0, 1, 3, 7), (0, 3, 2, 7), (0, 2, 6, 7),
        (0, 6, 4, 7), (0, 4, 5, 7), (0, 5, 1, 7),
    )
    bits = (
        (0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0),
        (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1),
    )
    tets = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                corners = [_node(i + di, j + dj, k + dk, nx, ny) for di, dj, dk in bits]
                for local in local_tets:
                    tet = [corners[q] for q in local]
                    det = float(np.linalg.det((xyz[tet[1:]] - xyz[tet[0]]).T))
                    if det < 0.0:
                        tet[2], tet[3] = tet[3], tet[2]
                    if det == 0.0:
                        raise AssertionError("zero-volume structured TET4")
                    tets.append(tet)
    bottom = tuple(_node(i, j, 0, nx, ny) for j in range(ny + 1) for i in range(nx + 1))
    top = tuple(_node(i, j, nz, nx, ny) for j in range(ny + 1) for i in range(nx + 1))
    areas = {node: 0.0 for node in bottom}
    for j in range(ny):
        for i in range(nx):
            a, b = _node(i, j, 0, nx, ny), _node(i + 1, j, 0, nx, ny)
            c, d = _node(i + 1, j + 1, 0, nx, ny), _node(i, j + 1, 0, nx, ny)
            for tri in ((a, b, c), (a, c, d)):
                for node in tri:
                    areas[node] += 0.5 / (nx * ny * 3.0)
    counts = Counter()
    for tet in tets:
        for face in combinations(tet, 3):
            counts[tuple(sorted(face))] += 1
    boundary = tuple(face for face, count in counts.items() if count == 1)
    bottom_triangles = tuple(
        tri
        for j in range(ny)
        for i in range(nx)
        for tri in (
            (_node(i, j, 0, nx, ny), _node(i + 1, j, 0, nx, ny), _node(i + 1, j + 1, 0, nx, ny)),
            (_node(i, j, 0, nx, ny), _node(i + 1, j + 1, 0, nx, ny), _node(i, j + 1, 0, nx, ny)),
        )
    )
    return xyz, np.asarray(tets, dtype=np.int64), bottom, top, areas, boundary, bottom_triangles


def _q(x, y):
    return 1.0 + 0.4 * x - 0.25 * y + 0.3 * x * y + 0.15 * x * x


def _qx(x, y):
    return 0.4 + 0.3 * y + 0.3 * x


def _qy(x, y):
    return -0.25 + 0.3 * x


def _phi(s):
    return s * (1.0 - s) ** 2


def _phip(s):
    return 1.0 - 4.0 * s + 3.0 * s * s


def _phipp(s):
    return -4.0 + 6.0 * s


def _positive_part_gap(x: float, front: float) -> tuple[float, float, float]:
    r = max(float(x) - front, 0.0)
    return GAP_CURVATURE_M * r**4, 4.0 * GAP_CURVATURE_M * r**3, 12.0 * GAP_CURVATURE_M * r**2


def _lambda_exact(x: float, front: float) -> float:
    r = max(front - float(x), 0.0)
    return PRESSURE_CURVATURE_PA_PER_M2 * r**2


def _u_exact(point, front):
    x, y, z = map(float, point)
    s = (z - GAP) / H
    gap, _gx, _gxx = _positive_part_gap(x, front)
    return np.array((0.0, 0.0, -(GAP - gap) * (1.0 - s) + AMP * _q(x, y) * _phi(s)))


def _stress(point, front):
    x, y, z = map(float, point)
    s = (z - GAP) / H
    _gap, gx, _gxx = _positive_part_gap(x, front)
    sig = np.zeros((3, 3))
    sig[2, 2] = E / H * (GAP - _positive_part_gap(x, front)[0] + AMP * _q(x, y) * _phip(s))
    sig[0, 2] = sig[2, 0] = MU * (gx * (1.0 - s) + AMP * _qx(x, y) * _phi(s))
    sig[1, 2] = sig[2, 1] = MU * AMP * _qy(x, y) * _phi(s)
    return sig


def _body(point, front):
    x, y, z = map(float, point)
    s = (z - GAP) / H
    _gap, gx, gxx = _positive_part_gap(x, front)
    q = _q(x, y)
    return -np.array((
        MU / H * (-gx + AMP * _qx(x, y) * _phip(s)),
        MU * AMP * _qy(x, y) * _phip(s) / H,
        MU * (gxx * (1.0 - s) + AMP * 0.3 * _phi(s))
        + E * AMP * q * _phipp(s) / (H * H),
    ))


def _gauss01(order=6):
    x, w = np.polynomial.legendre.leggauss(order)
    return 0.5 * (x + 1.0), 0.5 * w


def _tet_rule(xyz, order=6):
    x, w = _gauss01(order)
    jac = abs(float(np.linalg.det((xyz[1:] - xyz[0]).T)))
    for i, r in enumerate(x):
        for j, s in enumerate(x):
            for k, t in enumerate(x):
                N = np.array(((1-r)*(1-s)*(1-t), r, (1-r)*s, (1-r)*(1-s)*t))
                dv = jac * (1-r)**2 * (1-s) * w[i] * w[j] * w[k]
                yield N, N @ xyz, float(dv)


def _tri_rule(xyz):
    x, w = _gauss01()
    jac = float(np.linalg.norm(np.cross(xyz[1] - xyz[0], xyz[2] - xyz[0])))
    for i, r in enumerate(x):
        for j, s in enumerate(x):
            xi, eta = r, (1-r) * s
            N = np.array((1-xi-eta, xi, eta))
            da = jac * (1-r) * w[i] * w[j]
            yield N, N @ xyz, float(da)


def _load(mesh, front):
    xyz, tets, _bottom, top, _areas, boundary, _bottom_triangles = mesh
    force = np.zeros((len(xyz), 3))
    for tet in tets:
        for N, point, dv in _tet_rule(xyz[tet], order=6):
            body = _body(point, front)
            for a, node in enumerate(tet):
                force[node] += N[a] * body * dv
    top_set = set(top)
    center = np.array((0.5, 0.5, GAP + 0.5 * H))
    for face0 in boundary:
        face = tuple(face0)
        if all(i in top_set for i in face):
            continue
        tri = xyz[np.asarray(face)]
        normal = np.cross(tri[1] - tri[0], tri[2] - tri[0])
        normal /= np.linalg.norm(normal)
        if normal @ (tri.mean(axis=0) - center) < 0.0:
            face = (face[0], face[2], face[1])
            tri = xyz[np.asarray(face)]
            normal = np.cross(tri[1] - tri[0], tri[2] - tri[0])
            normal /= np.linalg.norm(normal)
        is_bottom = all(abs(float(xyz[i, 2] - GAP)) < 1.0e-14 for i in face)
        for N, point, da in _tri_rule(tri):
            traction = _stress(point, front) @ normal
            if is_bottom:
                # Exterior normal is -ez. Contact force on the body is +lambda ez.
                traction[2] -= _lambda_exact(point[0], front)
            for a, node in enumerate(face):
                force[node] += N[a] * traction * da
    return force


def _case(mesh, front):
    xyz, tets, bottom, top, areas, _boundary, _bottom_triangles = mesh
    face = RegularPlanarFace(
        vertices_m=((-2.0, -1.0, 0.0), (3.0, -1.0, 0.0), (0.5, 4.0, 0.0)),
        free_side_normal=(0.0, 0.0, 1.0),
        face_id="aj-flat-rigid-master",
    )
    return DistributedTet4Case(
        nodes_m=xyz,
        tetrahedra=tets,
        young_modulus_pa=E,
        poisson_ratio=0.0,
        master_faces=(face,),
        slave_points=tuple(SlaveContactPoint(i, areas[i], face.face_id) for i in bottom),
        external_nodal_forces_n=_load(mesh, front),
        prescribed_displacements_m={(i, d): 0.0 for i in top for d in ("UX", "UY", "UZ")},
        controls=CTRL,
        geometry_tolerances=GEOM,
    )


def _tet_stiffness(xyz):
    coef = np.linalg.solve(np.column_stack((np.ones(4), xyz)), np.eye(4))
    grad = coef[1:, :].T
    B = np.zeros((6, 12))
    for i, (dx, dy, dz) in enumerate(grad):
        c = 3 * i
        B[0, c] = dx; B[1, c + 1] = dy; B[2, c + 2] = dz
        B[3, c] = dy; B[3, c + 1] = dx
        B[4, c + 1] = dz; B[4, c + 2] = dy
        B[5, c] = dz; B[5, c + 2] = dx
    D = np.diag((E, E, E, MU, MU, MU))
    vol = abs(float(np.linalg.det((xyz[1:] - xyz[0]).T))) / 6.0
    return vol * (B.T @ D @ B), B, D


def _independent_stiffness(xyz, tets):
    K = np.zeros((3 * len(xyz), 3 * len(xyz)))
    for tet in tets:
        local, _B, _D = _tet_stiffness(xyz[tet])
        dofs = np.asarray([3 * int(i) + c for i in tet for c in range(3)])
        K[np.ix_(dofs, dofs)] += local
    return K


def _exact_contact(front):
    x, w = _gauss01(12)
    force = 0.0
    moment = np.zeros(3)
    for i, xi in enumerate(x):
        xx = front * xi
        for j, yy in enumerate(x):
            lam = _lambda_exact(xx, front)
            f = np.array((0.0, 0.0, lam))
            weight = front * w[i] * w[j]
            force += weight * lam
            moment += weight * np.cross((xx, yy, GAP), f)
    return force, moment


def _exact_top(front):
    x, w = _gauss01(12)
    force = np.zeros(3)
    moment = np.zeros(3)
    z = GAP + H
    # Split at the positive-part front; every subintegrand is polynomial.
    for x0, x1 in ((0.0, front), (front, 1.0)):
        for i, xi in enumerate(x):
            xx = x0 + (x1 - x0) * xi
            for j, yy in enumerate(x):
                point = np.array((xx, yy, z))
                traction = _stress(point, front) @ np.array((0.0, 0.0, 1.0))
                weight = (x1 - x0) * w[i] * w[j]
                force += weight * traction
                moment += weight * np.cross(point, traction)
    return force, moment


def _field_metrics(mesh, displacement, front, K):
    xyz, tets, *_ = mesh
    un = displacement.reshape((-1, 3))
    l2 = exact_l2 = energy_error = exact_strain_energy = fe_integrated_strain_energy = 0.0
    D = np.diag((E, E, E, MU, MU, MU))
    for tet in tets:
        _local, B, _D = _tet_stiffness(xyz[tet])
        eps_fe = B @ un[tet].reshape(-1)
        for N, point, dv in _tet_rule(xyz[tet], order=8):
            fe_integrated_strain_energy += 0.5 * float(eps_fe @ D @ eps_fe) * dv
            delta = N @ un[tet] - _u_exact(point, front)
            l2 += float(delta @ delta) * dv
            exact = _u_exact(point, front)
            exact_l2 += float(exact @ exact) * dv
            x, y, z = map(float, point)
            s = (z - GAP) / H
            _gap, gx, _gxx = _positive_part_gap(x, front)
            strain = np.array((
                0.0, 0.0, (GAP - _positive_part_gap(x, front)[0] + AMP * _q(x, y) * _phip(s)) / H,
                0.0,
                # B uses engineering Voigt order [xx, yy, zz, xy, yz, xz].
                AMP * _qy(x, y) * _phi(s),
                (gx * (1.0 - s) + AMP * _qx(x, y) * _phi(s)),
            ))
            de = eps_fe - strain
            energy_error += float(de @ D @ de) * dv
            exact_strain_energy += 0.5 * float(strain @ D @ strain) * dv
    fe_strain_energy = 0.5 * float(displacement @ (K @ displacement))
    energy_error_norm = float(np.sqrt(energy_error))
    exact_energy_norm = float(np.sqrt(2.0 * exact_strain_energy))
    return {
        "relative_l2_displacement_error": float(np.sqrt(l2 / exact_l2)),
        "strain_energy_error_norm_j_sqrt": energy_error_norm,
        "relative_energy_norm_error": energy_error_norm / max(exact_energy_norm, np.finfo(float).tiny),
        "strain_energy_j": fe_strain_energy,
        "fe_integrated_strain_energy_j": fe_integrated_strain_energy,
        "exact_strain_energy_j": exact_strain_energy,
        "absolute_strain_energy_difference_j": abs(fe_strain_energy - exact_strain_energy),
        "fe_energy_matrix_vs_quadrature_error_j": abs(fe_strain_energy - fe_integrated_strain_energy),
        "energy_definition": "engineering-Voigt [xx,yy,zz,xy,yz,xz]; D shear entries=mu; U=0.5*integral(epsilon.T D epsilon)dV; error norm=sqrt(integral(delta_epsilon.T D delta_epsilon)dV)",
    }


def _independent_discrete_kkt(K, external_force, contact_nodes, prescribed_dofs):
    """Solve the complete discrete contact QP with an independent NNLS method.

    The dual quadratic is derived from the independently assembled elastic
    matrix. All bottom constraints participate; no continuum active set is
    supplied. Positive-definite free stiffness and independent constraint
    rows make the dual Hessian positive definite for these fixtures.
    """
    free = np.setdiff1d(np.arange(K.shape[0], dtype=int), prescribed_dofs)
    lookup = {int(dof): column for column, dof in enumerate(free)}
    Kff = K[np.ix_(free, free)]
    f = external_force[free]
    G = np.zeros((len(contact_nodes), len(free)))
    for row, node in enumerate(contact_nodes):
        G[row, lookup[3 * int(node) + 2]] = 1.0

    u0 = np.linalg.solve(Kff, f)
    compliance = np.linalg.solve(Kff, G.T)
    W = G @ compliance
    q = np.full(len(contact_nodes), GAP) + G @ u0
    # Scale the dual QP to dimensionless displacement/force variables.
    W_scaled = (CTRL.force_scale_n / CTRL.length_scale_m) * 0.5 * (W + W.T)
    q_scaled = q / CTRL.length_scale_m
    chol = np.linalg.cholesky(W_scaled)
    target = np.linalg.solve(chol, -q_scaled)
    x, nnls_residual = nnls(chol.T, target, maxiter=max(50, 20 * len(contact_nodes)))
    multipliers = CTRL.force_scale_n * x
    u_free = u0 + compliance @ multipliers
    displacement = np.zeros(K.shape[0])
    displacement[free] = u_free
    gaps = np.full(len(contact_nodes), GAP) + G @ u_free
    stationarity = Kff @ u_free - f - G.T @ multipliers
    return {
        "free_dofs": free,
        "G": G,
        "displacement": displacement,
        "multipliers": multipliers,
        "gaps": gaps,
        "stationarity": stationarity,
        "nnls_residual_sqrt_j": float(nnls_residual),
        "dual_hessian_condition": float(np.linalg.cond(W_scaled)),
        "complementarity_inf_nm": float(np.max(np.abs(gaps * multipliers), initial=0.0)),
    }


def _front_diagnostics(contact_nodes, xyz, areas, front, hx, gaps, multipliers):
    """Measure the numerical free boundary without enforcing continuum labels."""
    points = xyz[np.asarray(contact_nodes, dtype=int)]
    pressure = multipliers / np.asarray([areas[int(node)] for node in contact_nodes])
    active = multipliers > CTRL.force_tolerance_n
    opened = gaps > CTRL.gap_tolerance_m
    biactive = (np.abs(gaps) <= CTRL.gap_tolerance_m) & (np.abs(multipliers) <= CTRL.force_tolerance_n)
    continuum_active = points[:, 0] < front - 1.0e-12
    continuum_open = points[:, 0] > front + 1.0e-12
    false_positive = np.flatnonzero(active & continuum_open)
    false_negative = np.flatnonzero(opened & continuum_active)
    trace = []
    for y in np.unique(points[:, 1]):
        rows = np.flatnonzero(np.isclose(points[:, 1], y, rtol=0.0, atol=1.0e-14))
        active_x = points[rows[active[rows]], 0]
        open_x = points[rows[opened[rows]], 0]
        last_active = float(np.max(active_x)) if len(active_x) else None
        first_open = float(np.min(open_x)) if len(open_x) else None
        bracketed = last_active is not None and first_open is not None
        trace.append({
            "y_m": float(y), "last_active_x_m": last_active, "first_open_x_m": first_open,
            "front_bracketed_by_observed_states": bracketed,
            "signed_front_error_m": last_active - front if last_active is not None else None,
            "absolute_front_error_m": abs(last_active - front) if last_active is not None else None,
            "first_open_signed_offset_m": first_open - front if first_open is not None else None,
            "active_x_m": sorted(map(float, active_x)), "open_x_m": sorted(map(float, open_x)),
        })
    offsets = [
        row["signed_front_error_m"] for row in trace
        if row["front_bracketed_by_observed_states"] and row["signed_front_error_m"] is not None
    ]
    fp_area = float(sum(areas[int(contact_nodes[row])] for row in false_positive))
    fn_area = float(sum(areas[int(contact_nodes[row])] for row in false_negative))
    contact_area = float(sum(areas[int(node)] for node in contact_nodes))

    def row_values(indices):
        return [
            {
                "node": int(contact_nodes[row]), "x_m": float(points[row, 0]), "y_m": float(points[row, 1]),
                "distance_to_front_m": abs(float(points[row, 0]) - front),
                "distance_to_front_over_hx": abs(float(points[row, 0]) - front) / hx,
                "gap_m": float(gaps[row]), "lambda_n": float(multipliers[row]), "pressure_pa": float(pressure[row]),
            }
            for row in indices
        ]

    return {
        "front_definition": "per y-row: greatest x with lambda above frozen force tolerance; descriptive, not a label-equality gate",
        "front_exact_x_m": float(front), "front_trace_by_y": trace,
        "front_unbracketed_y_m": [row["y_m"] for row in trace if not row["front_bracketed_by_observed_states"]],
        "front_bracketed_row_count": int(sum(row["front_bracketed_by_observed_states"] for row in trace)),
        "front_row_count": int(len(trace)),
        "front_error_max_abs_m": max((abs(value) for value in offsets), default=None),
        "front_error_rms_m": float(np.sqrt(np.mean(np.square(offsets)))) if offsets else None,
        "front_error_max_over_hx": max((abs(value) / hx for value in offsets), default=None),
        "front_error_rms_over_hx": float(np.sqrt(np.mean(np.square(np.asarray(offsets) / hx)))) if offsets else None,
        "false_positive_count": int(len(false_positive)), "false_negative_count": int(len(false_negative)),
        "false_positive_tributary_area_m2": fp_area, "false_negative_tributary_area_m2": fn_area,
        "mismatch_tributary_area_fraction": (fp_area + fn_area) / contact_area if contact_area else None,
        "false_positives": row_values(false_positive), "false_negatives": row_values(false_negative),
        "biactive_count": int(np.count_nonzero(biactive)),
        "strict_active_max_gap_m": float(np.max(gaps[active], initial=-np.inf)) if np.any(active) else None,
        "strict_active_min_lambda_n": float(np.min(multipliers[active])) if np.any(active) else None,
        "strict_open_min_gap_m": float(np.min(gaps[opened])) if np.any(opened) else None,
        "strict_open_max_lambda_n": float(np.max(multipliers[opened], initial=0.0)) if np.any(opened) else None,
        "area_metric_note": "Nodal tributary areas define a lumped mismatch measure, not an exact active-area integral or Hausdorff distance.",
    }


def _solve_level(level, front: float = FRONT_X_M):
    nx, ny, nz = level
    mesh = _mesh(level)
    xyz, tets, bottom, top, areas, _boundary, bottom_triangles = mesh
    case = _case(mesh, front)
    assembled = assemble_tet4_distributed_contact(case)
    result = assembled.solve()
    K = _independent_stiffness(xyz, tets)
    prescribed = np.asarray([3 * int(node) + axis for node in top for axis in range(3)], dtype=int)
    contact_nodes = np.asarray(bottom, dtype=int)
    independent = _independent_discrete_kkt(
        K, case.external_nodal_forces_n.reshape(-1), contact_nodes, prescribed
    )
    free = independent["free_dofs"]
    uref = independent["displacement"]
    lamref = independent["multipliers"]
    gap_ref = independent["gaps"]
    observed_u = result.displacement_m.reshape(-1)
    observed_lambda = np.asarray(result.multipliers_n, dtype=float)
    gap = GAP + observed_u[3 * contact_nodes + 2]
    reported_gap_error = float(np.max(np.abs(np.asarray(result.gaps_m) - gap), initial=0.0))
    front_metrics = _front_diagnostics(contact_nodes, xyz, areas, front, 1.0 / nx, gap, observed_lambda)
    pressure = result.multipliers_n / np.asarray([areas[i] for i in bottom])
    exact_pressure = np.asarray([_lambda_exact(xyz[i, 0], front) for i in bottom])
    pressure_error_sq = exact_pressure_sq = 0.0
    for triangle in bottom_triangles:
        tri_nodes = np.asarray(triangle, dtype=int)
        tri_xyz = xyz[tri_nodes]
        tri_pressure = pressure[tri_nodes]
        for N, point, da in _tri_rule(tri_xyz):
            exact_p = _lambda_exact(float(point[0]), front)
            pressure_error_sq += float((N @ tri_pressure - exact_p) ** 2) * da
            exact_pressure_sq += exact_p**2 * da
    pressure_error = float(np.sqrt(pressure_error_sq / exact_pressure_sq))
    exact_force, exact_moment = _exact_contact(front)
    contact_force = np.zeros((len(xyz), 3))
    contact_force[contact_nodes, 2] = observed_lambda
    external_force = case.external_nodal_forces_n
    support = result.support_reaction_n.reshape((-1, 3))
    force_balance = external_force.sum(axis=0) + support.sum(axis=0) + contact_force.sum(axis=0)
    moment_balance = (np.cross(xyz, external_force).sum(axis=0)
                     + np.cross(xyz, support).sum(axis=0)
                     + np.cross(xyz, contact_force).sum(axis=0))
    exact_support, exact_support_moment = _exact_top(front)
    support_force = support.sum(axis=0)
    support_moment = np.cross(xyz, support).sum(axis=0)
    reference_contact = np.zeros((len(xyz), 3))
    reference_contact[contact_nodes, 2] = lamref
    reference_internal = K @ uref
    reference_support = np.zeros_like(reference_contact)
    prescribed_mask = np.zeros(3 * len(xyz), dtype=bool)
    prescribed_mask[prescribed] = True
    reference_residual_at_support = reference_internal - case.external_nodal_forces_n.reshape(-1) - reference_contact.reshape(-1)
    reference_support.reshape(-1)[prescribed_mask] = reference_residual_at_support[prescribed_mask]
    reference_support_force = reference_support.sum(axis=0)
    reference_support_moment = np.cross(xyz, reference_support).sum(axis=0)
    reference_force_balance = case.external_nodal_forces_n.sum(axis=0) + reference_support_force + reference_contact.sum(axis=0)
    reference_moment_balance = (np.cross(xyz, case.external_nodal_forces_n).sum(axis=0)
                                + reference_support_moment + np.cross(xyz, reference_contact).sum(axis=0))
    h = max(float(np.linalg.norm(xyz[a] - xyz[b]))
            for tet in tets for a, b in combinations(tet, 2))
    force_scale = max(abs(float(exact_force)), 1.0)
    moment_scale = force_scale * 1.0  # fixed 1 m characteristic arm, N*m
    contact_work = float(observed_lambda @ observed_u.reshape((-1, 3))[contact_nodes, 2])
    observed_stationarity = K[np.ix_(free, np.arange(K.shape[0]))] @ observed_u
    observed_stationarity -= case.external_nodal_forces_n.reshape(-1)[free]
    observed_stationarity -= independent["G"].T @ observed_lambda
    ref_stationarity_inf = float(np.linalg.norm(independent["stationarity"], ord=np.inf))
    ref_complementarity_inf = independent["complementarity_inf_nm"]
    diagnostic = {
        "level_nx_ny_nz": [nx, ny, nz], "nodes": len(xyz), "tet4": len(tets), "total_dofs": 3 * len(xyz),
        "free_dofs": len(free), "contact_rows": len(bottom), "active_count": int(np.count_nonzero(observed_lambda > CTRL.force_tolerance_n)),
        "open_count": int(np.count_nonzero(gap > CTRL.gap_tolerance_m)),
        "h_max_m": h, "h_x_m": 1.0 / nx, "active_set_solver_indices": list(map(int, result.active_set)),
        "active_set_history": [list(map(int, row)) for row in result.active_set_history],
        "maximum_penetration_m": max(0.0, -float(np.min(gap))),
        "production_gap_reconstruction_error_m": reported_gap_error,
        "complementarity_inf_nm": float(result.complementarity_inf_nm),
        "production_independent_stationarity_inf_n": float(np.linalg.norm(observed_stationarity, ord=np.inf)),
        "independent_kkt_stationarity_inf_n": ref_stationarity_inf,
        "independent_kkt_primal_gap_min_m": float(np.min(gap_ref)),
        "independent_kkt_dual_multiplier_min_n": float(np.min(lamref)),
        "independent_kkt_complementarity_inf_nm": ref_complementarity_inf,
        "independent_kkt_normalized_residual_max": max(
            ref_stationarity_inf / CTRL.force_scale_n,
            max(0.0, -float(np.min(gap_ref))) / CTRL.length_scale_m,
            max(0.0, -float(np.min(lamref))) / CTRL.force_scale_n,
            ref_complementarity_inf / CTRL.complementarity_tolerance_nm,
        ),
        "independent_kkt_nnls_residual_sqrt_j": independent["nnls_residual_sqrt_j"],
        "independent_kkt_dual_condition": independent["dual_hessian_condition"],
        "independent_kkt_displacement_error_m": float(np.max(np.abs(result.displacement_m.reshape(-1) - uref))),
        "independent_kkt_multiplier_error_n": float(np.max(np.abs(result.multipliers_n - lamref))),
        "independent_kkt_reference_active_count": int(np.count_nonzero(lamref > CTRL.force_tolerance_n)),
        "contact_force_n": float(observed_lambda.sum()),
        "contact_force_exact_n": exact_force,
        "contact_force_error_n": abs(float(observed_lambda.sum()) - exact_force),
        "contact_force_relative_error": abs(float(observed_lambda.sum()) - exact_force) / max(abs(exact_force), 1.0),
        "contact_moment_exact_nm": _exact_contact(front)[1].tolist(),
        "contact_moment_error_nm": float(np.linalg.norm(np.cross(xyz[contact_nodes], contact_force[contact_nodes]).sum(axis=0) - exact_moment)),
        "contact_moment_relative_error": float(np.linalg.norm(np.cross(xyz[contact_nodes], contact_force[contact_nodes]).sum(axis=0) - exact_moment) / moment_scale),
        "force_balance_relative": float(np.linalg.norm(force_balance) / force_scale),
        "moment_balance_relative": float(np.linalg.norm(moment_balance) / moment_scale),
        "support_resultant_n": support_force.tolist(),
        "support_resultant_exact_n": exact_support.tolist(),
        "support_resultant_error_n": float(np.linalg.norm(support_force - exact_support)),
        "support_moment_nm": support_moment.tolist(),
        "support_moment_exact_nm": exact_support_moment.tolist(),
        "support_moment_error_nm": float(np.linalg.norm(support_moment - exact_support_moment)),
        "independent_kkt_contact_force_n": float(lamref.sum()),
        "independent_kkt_contact_force_error_n": abs(float(lamref.sum()) - exact_force),
        "independent_kkt_contact_moment_nm": np.cross(xyz[contact_nodes], reference_contact[contact_nodes]).sum(axis=0).tolist(),
        "independent_kkt_contact_moment_error_nm": float(np.linalg.norm(np.cross(xyz[contact_nodes], reference_contact[contact_nodes]).sum(axis=0) - exact_moment)),
        "independent_kkt_support_resultant_n": reference_support_force.tolist(),
        "independent_kkt_support_resultant_error_n": float(np.linalg.norm(reference_support_force - exact_support)),
        "independent_kkt_support_moment_nm": reference_support_moment.tolist(),
        "independent_kkt_support_moment_error_nm": float(np.linalg.norm(reference_support_moment - exact_support_moment)),
        "independent_kkt_force_balance_n": reference_force_balance.tolist(),
        "independent_kkt_moment_balance_nm": reference_moment_balance.tolist(),
        "independent_kkt_contact_work_j": float(lamref @ uref.reshape((-1, 3))[contact_nodes, 2]),
        "independent_kkt_contact_work_identity_error_j": abs(
            float(lamref @ uref.reshape((-1, 3))[contact_nodes, 2]) + GAP * float(lamref.sum())
        ),
        "independent_kkt_force_balance_relative": float(np.linalg.norm(reference_force_balance) / force_scale),
        "independent_kkt_moment_balance_relative": float(np.linalg.norm(reference_moment_balance) / moment_scale),
        "pressure_relative_l2_error": pressure_error,
        "contact_pressures_pa": pressure.tolist(),
        "gap_m": gap.tolist(),
        "contact_work_j": contact_work,
        "contact_work_identity_error_j": abs(contact_work + GAP * float(observed_lambda.sum())),
        "force_scale_n": force_scale,
        "force_scale_definition": "max(abs(analytic contact resultant), 1 N); fixed across mesh levels",
        "moment_scale_nm": moment_scale,
        "units": {"length": "m", "force": "N", "pressure": "Pa", "moment": "N*m", "energy": "J"},
        **front_metrics,
        **_field_metrics(mesh, result.displacement_m.reshape(-1), front, K),
    }
    return diagnostic


def test_aj_partial_active_contact_refinement():
    rows = []
    for level in LEVELS:
        row = _solve_level(level)
        rows.append(row)
        # Persist each completed level before attempting a finer solve, so a
        # later resource or numerical failure cannot erase earlier evidence.
        print(json.dumps({"aj_partial_mesh_diagnostic": row}, sort_keys=True))
    # Log all observations before assertions so failures remain diagnosable.
    assert all(0 < row["active_count"] < row["contact_rows"] for row in rows)
    assert all(row["open_count"] > 0 for row in rows)
    assert all(row["maximum_penetration_m"] <= CTRL.gap_tolerance_m for row in rows)
    assert all(row["production_gap_reconstruction_error_m"] <= CTRL.gap_tolerance_m for row in rows)
    assert all(row["complementarity_inf_nm"] <= CTRL.complementarity_tolerance_nm for row in rows)
    assert all(row["independent_kkt_dual_multiplier_min_n"] >= -CTRL.force_tolerance_n for row in rows)
    assert all(row["strict_active_max_gap_m"] <= CTRL.gap_tolerance_m for row in rows)
    assert all(row["strict_open_max_lambda_n"] <= CTRL.force_tolerance_n for row in rows)
    assert all(row["contact_work_identity_error_j"] <= 1.0e-9 for row in rows)
    assert all(row["production_independent_stationarity_inf_n"] <= 1.0e-6 for row in rows)
    assert all(row["independent_kkt_stationarity_inf_n"] <= 1.0e-6 for row in rows)
    assert all(row["independent_kkt_primal_gap_min_m"] >= -CTRL.gap_tolerance_m for row in rows)
    assert all(row["independent_kkt_dual_multiplier_min_n"] >= -CTRL.force_tolerance_n for row in rows)
    assert all(row["independent_kkt_complementarity_inf_nm"] <= CTRL.complementarity_tolerance_nm for row in rows)
    assert all(row["independent_kkt_contact_work_identity_error_j"] <= 1.0e-9 for row in rows)
    assert all(row["independent_kkt_force_balance_relative"] <= 1.0e-9 for row in rows)
    assert all(row["independent_kkt_moment_balance_relative"] <= 1.0e-9 for row in rows)
    assert all(row["independent_kkt_displacement_error_m"] <= 1.0e-9 for row in rows)
    assert all(row["independent_kkt_multiplier_error_n"] <= 1.0e-6 for row in rows)
    # Continuum force/moment discrepancies are reported as refinement
    # observables; they are not forced to a discretization-independent bound.
    assert all(np.isfinite(row["contact_force_relative_error"]) for row in rows)
    assert all(np.isfinite(row["contact_moment_relative_error"]) for row in rows)
    assert all(row["force_balance_relative"] <= 1.0e-9 for row in rows)
    assert all(row["moment_balance_relative"] <= 1.0e-9 for row in rows)
    assert all(np.isfinite(row["front_error_max_abs_m"]) for row in rows)
    assert all(np.isfinite(row["front_error_rms_over_hx"]) for row in rows)
    assert all(row["fe_energy_matrix_vs_quadrature_error_j"] <= 1.0e-10 for row in rows)
    assert rows[-1]["relative_l2_displacement_error"] < 0.9 * rows[0]["relative_l2_displacement_error"]
    assert rows[-1]["pressure_relative_l2_error"] < 0.9 * rows[0]["pressure_relative_l2_error"]
    assert rows[-1]["strain_energy_error_norm_j_sqrt"] < rows[0]["strain_energy_error_norm_j_sqrt"]


def test_aj_analytic_partial_contact_contract():
    # Continuous references: active patch [0,a] x [0,1], open patch x>a.
    exact_force, exact_moment = _exact_contact(FRONT_X_M)
    analytic_force = WIDTH_Y_M * PRESSURE_CURVATURE_PA_PER_M2 * FRONT_X_M**3 / 3.0
    analytic_mx = 0.5 * analytic_force * WIDTH_Y_M
    analytic_my = -WIDTH_Y_M * PRESSURE_CURVATURE_PA_PER_M2 * FRONT_X_M**4 / 12.0
    active_probe = _positive_part_gap(FRONT_X_M, FRONT_X_M)[0]
    open_probe = _positive_part_gap(1.0, FRONT_X_M)[0]
    open_shear = MU * 4.0 * GAP_CURVATURE_M * (1.0 - FRONT_X_M) ** 3
    data = {
        "active_domain": "0<=x<0.5 m, 0<=y<=1 m",
        "open_domain": "0.5<x<=1 m, 0<=y<=1 m",
        "interface_width_y_m": WIDTH_Y_M,
        "active_front_x_m": FRONT_X_M,
        "analytic_contact_force_n": analytic_force,
        "quadrature_contact_force_n": exact_force,
        "analytic_contact_moment_nm": [analytic_mx, analytic_my, 0.0],
        "quadrature_contact_moment_nm": exact_moment.tolist(),
        "active_front_gap_m": active_probe,
        "open_edge_gap_m": open_probe,
        "open_edge_bottom_tangential_traction_magnitude_pa": open_shear,
        "all_open_state_parameter_front_x_m": -0.1,
        "units": {"length": "m", "force": "N", "pressure": "Pa", "moment": "N*m"},
    }
    print(json.dumps({"aj_analytic_contract": data}, sort_keys=True))
    assert abs(exact_force - analytic_force) <= 1.0e-10
    assert np.linalg.norm(exact_moment - np.array((analytic_mx, analytic_my, 0.0))) <= 1.0e-10
    assert active_probe == 0.0 and open_probe > CTRL.gap_tolerance_m
    assert open_shear > 0.0


def test_aj_accepted_open_partial_extension_release_sequence():
    # A single mesh and frozen geometry are retained. The load patterns are
    # manufactured from successively changing exact fronts; this is an
    # accepted-state sequence for linear path-independent elasticity, not a
    # scalar-amplitude or nonlinear material-history claim.
    mesh = _mesh((6, 3, 3))
    assembled = assemble_tet4_distributed_contact(_case(mesh, -0.1))
    initial = assembled.solve()
    stepper = DistributedContactStepper(assembled, initial, _load(mesh, -0.1))
    history = [{
        "label": "OPEN",
        "front_parameter_m": -0.1,
        "active_count": len(initial.active_set),
        "minimum_gap_m": float(np.min(initial.gaps_m)),
        "multiplier_sum_n": float(np.sum(initial.multipliers_n)),
        "accepted_revision": stepper.accepted.revision,
    }]
    print(json.dumps({"aj_contact_state": history[-1]}, sort_keys=True))
    for label, front in (("FIRST_CONTACT", 1.0 / 6.0), ("PARTIAL", 1.0 / 3.0), ("EXTENDED", 2.0 / 3.0), ("RELEASE", -0.1)):
        trial = stepper.propose(_load(mesh, front))
        history.append({
            "label": label,
            "front_parameter_m": front,
            "active_count": len(trial.active_set),
            "minimum_gap_m": float(np.min(trial.gaps_m)),
            "multiplier_sum_n": float(np.sum(trial.multipliers_n)),
            "accepted_revision_before_commit": stepper.accepted.revision,
        })
        # Emit the solved trial values before commit. If commit refuses, the
        # trial result remains available and is not mislabeled as accepted.
        print(json.dumps({"aj_contact_state_trial": history[-1]}, sort_keys=True))
        stepper.accept()
        history[-1]["accepted_revision_after_commit"] = stepper.accepted.revision
        print(json.dumps({"aj_contact_state_accepted": history[-1]}, sort_keys=True))
    counts = [record["active_count"] for record in history]
    assert counts[0] == 0
    assert 0 < counts[1] < counts[2] < counts[3] < len(assembled.contact_node_ids)
    assert counts[4] == 0
    assert history[0]["minimum_gap_m"] > CTRL.gap_tolerance_m
    assert history[4]["minimum_gap_m"] > CTRL.gap_tolerance_m
    assert history[1]["multiplier_sum_n"] > 0.0
    assert history[2]["multiplier_sum_n"] > history[1]["multiplier_sum_n"]
    assert history[3]["multiplier_sum_n"] > history[2]["multiplier_sum_n"]
    assert history[4]["multiplier_sum_n"] == 0.0
    assert [stepper.accepted.revision] == [4]
