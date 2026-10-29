"""Read the immutable R1 sidecar and perform matrix-only diagnostics; no FEM solve."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix

EXPECTED_SHA = "dee3c6976929954b7f4c5a678d474b3a151f7821db9c334f0f01d22320d2133e"
FACES = (
    (0, 3, 2, 1, 9, 13, 11, 8),
    (4, 5, 6, 7, 16, 18, 19, 17),
    (0, 1, 5, 4, 8, 12, 16, 10),
    (1, 2, 6, 5, 11, 14, 18, 12),
    (2, 3, 7, 6, 13, 15, 19, 14),
    (3, 0, 4, 7, 9, 10, 17, 15),
)


def analyze(path: Path) -> dict:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
        raise ValueError("INTEGRITY_MISMATCH: R1 sidecar")
    x = json.loads(raw)
    c = x["assembly"]["K_csr"]
    k = csr_matrix((c["data"], c["indices"], c["indptr"]), shape=c["shape"])
    f = np.asarray(x["assembly"]["F_N"])
    u = np.asarray(x["result"]["displacements_m"])
    ua = np.asarray(x["affine_oracle"]["u_affine_m"])
    free = np.asarray(x["residuals"]["free_indices"], dtype=int)
    fixed = np.asarray(x["residuals"]["fixed_indices"], dtype=int)
    nodes = np.asarray(x["model"]["nodes_m"])
    faces = x["assembly"]["face_contributions"]
    oracle = sum((np.asarray(row["independent_oracle"]["vector_N"]) for row in faces), np.zeros(60))
    delta_f = f - oracle
    ra = np.asarray(k[free][:, free] @ ua[free] - (f[free] - k[free][:, fixed] @ ua[fixed])).ravel()
    rn = np.asarray(k[free][:, free] @ u[free] - (f[free] - k[free][:, fixed] @ u[fixed])).ravel()
    kd = np.asarray(k[free][:, free] @ (u[free] - ua[free])).ravel()
    rows = []
    for row in faces:
        prod = np.asarray(row["production_dense_N"]).reshape(-1, 3)
        ref = np.asarray(row["independent_oracle"]["vector_N"]).reshape(-1, 3)
        diff = prod - ref
        rows.append(
            {
                "face": row["face"],
                "normal": row["independent_oracle"]["normal"],
                "production_resultant_N": prod.sum(axis=0).tolist(),
                "oracle_resultant_N": ref.sum(axis=0).tolist(),
                "production_moment_Nm": np.cross(nodes, prod).sum(axis=0).tolist(),
                "oracle_moment_Nm": np.cross(nodes, ref).sum(axis=0).tolist(),
                "nodes": [
                    {
                        "node": i,
                        "production_N": prod[i].tolist(),
                        "oracle_N": ref[i].tolist(),
                        "difference_N": diff[i].tolist(),
                    }
                    for i in FACES[row["face"]]
                ],
                "difference_inf_N": float(np.max(np.abs(diff))),
            }
        )
    geometry = []
    for i, face in enumerate(FACES):
        pts = nodes[list(face)]
        corners = pts[:4]
        midpoint_error = max(
            float(np.linalg.norm(pts[4 + j] - (corners[j] + corners[(j + 1) % 4]) / 2)) for j in range(4)
        )
        normal = np.cross(corners[1] - corners[0], corners[3] - corners[0])
        normal /= np.linalg.norm(normal)
        geometry.append(
            {
                "face": i,
                "loop": list(face),
                "midpoint_error_m": midpoint_error,
                "normal": normal.tolist(),
                "oracle_normal": x["affine_oracle"]["analytic_face_oracles"][i]["normal"],
                "surface_jacobian_m2": float(
                    np.linalg.norm(np.cross(corners[1] - corners[0], corners[3] - corners[0])) / 4
                ),
            }
        )

    def norm(v: object) -> float:
        return float(np.linalg.norm(v))

    eq = x["result"]["equilibrium"]
    moment = np.asarray(eq["moment_imbalance_about_origin"])
    moment_scale = max(norm(eq["external_moment_about_origin"]), norm(eq["reaction_moment_about_origin"]), 1.0)
    load_scale = norm(eq["external_resultant"])
    return {
        "input_sha256": EXPECTED_SHA,
        "face_comparison": rows,
        "geometry": geometry,
        "affine_fixed_displacement_max_m": float(np.max(np.abs(ua[fixed]))),
        "r_affine_free_inf_N": float(np.max(np.abs(ra))),
        "r_affine_free_2_N": norm(ra),
        "r_numeric_free_inf_N": float(np.max(np.abs(rn))),
        "r_numeric_free_2_N": norm(rn),
        "load_difference_free_inf_N": float(np.max(np.abs(delta_f[free]))),
        "affine_residual_plus_load_difference_inf_N": float(np.max(np.abs(ra + delta_f[free]))),
        "K_delta_minus_load_difference_inf_N": float(np.max(np.abs(kd - delta_f[free]))),
        "identity_residual_inf_N": float(np.max(np.abs(ra + kd - rn))),
        "Kua_minus_full_six_face_oracle_inf_N": float(
            np.max(np.abs(k @ ua - np.asarray(x["affine_oracle"]["all_six_analytic_boundary_loads_N"])))
        ),
        "moment_imbalance_norm_Nm": norm(moment),
        "moment_scale_Nm": moment_scale,
        "moment_relative_recomputed": norm(moment) / moment_scale,
        "moment_force_length_scale_1m": norm(moment) / load_scale,
        "energy_actual_J": x["result"]["energy"]["strain_energy_J"],
        "energy_reference_J": x["result"]["historical_r4_energy_reference_J"],
        "energy_difference_from_uKu_J": float(0.5 * (u @ (k @ u) - ua @ (k @ ua))),
        "numerical_uKu_J": float(0.5 * u @ (k @ u)),
        "affine_uKu_J": float(0.5 * ua @ (k @ ua)),
    }


if __name__ == "__main__":
    print(json.dumps(analyze(Path(sys.argv[1])), indent=2, allow_nan=False))
