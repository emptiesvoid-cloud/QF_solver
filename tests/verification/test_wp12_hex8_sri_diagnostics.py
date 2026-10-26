"""Bounded WP12 HEX8-SRI diagnostics; execution requires a registered runner attempt.

Each test performs one linear solve and archives its raw numerical state under
the active development attempt's ``output`` directory before evaluating the
frozen historical tolerances. The evidence is therefore independent of
pytest's stdout capture.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from solveur.elements.solid.hex8 import Hex8Element  # noqa: E402
from solveur.elements.solid.hex8_sri import Hex8SRIElement  # noqa: E402
from solveur.materials.solid import SolidMaterial  # noqa: E402


CONTRACT_PATH = ROOT / "qualification/0_2_8/wp13_12_hex8_sri_maturation_contract.json"
CONTRACT_SHA256 = "f1df42b4dc74704097ce30705d7f3b69f2b9272a745f71c2e7f08c7c38ae9d51"
SRI_SOURCE = ROOT / "src/solveur/elements/solid/hex8_sri.py"
STANDARD_HEX8_SOURCE = ROOT / "src/solveur/elements/solid/hex8.py"
YOUNG_MODULUS_PA = 1.0e6
LENGTH_M = 20.0
WIDTH_M = 1.0
HEIGHT_M = 1.0
TOTAL_LOAD_N = 1.0
MAX_REGISTERED_DOFS = 30_000


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256(path.read_bytes())


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _preselect_total_dofs(nx: int, expected_total_dofs: int) -> int:
    """Reject a model outside its declared size before mesh or FEM work."""
    selected_dofs = 27 * (nx + 1)  # 3 DOFs/node; 3 x 3 nodes per x station.
    if selected_dofs != expected_total_dofs:
        raise RuntimeError(
            f"preselection mismatch: nx={nx} selects {selected_dofs} total DDL, "
            f"expected exactly {expected_total_dofs}"
        )
    if selected_dofs > MAX_REGISTERED_DOFS:
        raise RuntimeError(
            f"preselection refused {selected_dofs} total DDL above the registered "
            f"{MAX_REGISTERED_DOFS} DDL ceiling"
        )
    return selected_dofs


def _active_attempt_output_dir(expected_total_dofs: int) -> Path:
    """Resolve the controller-owned durable output beside its temporary dir."""
    if os.environ.get("QF_DEVELOPMENT_AUTONOMOUS") != "1":
        pytest.fail(
            "FEM diagnostic refused: invoke only as an exact nodeid in an active "
            "registered DEVELOPMENT_AUTONOMOUS attempt",
            pytrace=False,
        )

    if os.environ.get("QF_DEV_WORKTREE_ID") != "wp12_elements":
        pytest.fail("FEM diagnostic refused: controller selected a different worktree", pytrace=False)
    if os.environ.get("QF_DEV_SELECTED_DOFS") != str(expected_total_dofs):
        pytest.fail("FEM diagnostic refused: controller DDL selection does not match this case", pytrace=False)
    if os.environ.get("QF_DEV_MAX_DOFS") != str(MAX_REGISTERED_DOFS):
        pytest.fail("FEM diagnostic refused: controller DDL ceiling is missing or changed", pytrace=False)
    if os.environ.get("QF_DEV_MAX_FEM_CASES") != "1":
        pytest.fail("FEM diagnostic refused: controller case-count limit is missing or changed", pytrace=False)

    temporary_value = os.environ.get("TEMP") or os.environ.get("TMPDIR") or os.environ.get("TMP")
    if not temporary_value:
        pytest.fail("FEM diagnostic refused: controller temporary directory is missing", pytrace=False)
    evidence_root_value = os.environ.get("QF_DEV_EVIDENCE_ROOT")
    if not evidence_root_value:
        pytest.fail("FEM diagnostic refused: controller evidence root is missing", pytrace=False)

    temporary_dir = Path(temporary_value).resolve()
    attempt_dir = temporary_dir.parent
    output_dir = attempt_dir / "output"
    evidence_root = Path(evidence_root_value).resolve()
    worktree_output_root = (evidence_root / "worktrees" / "wp12_elements").resolve()
    if (
        temporary_dir.name.casefold() != "tmp"
        or not re.fullmatch(r"attempt-[0-9]{4}", attempt_dir.name)
        or not _is_within(attempt_dir, worktree_output_root)
    ):
        pytest.fail(
            "FEM diagnostic refused: TEMP is not inside this worktree's durable "
            "controller evidence attempt",
            pytrace=False,
        )
    if not output_dir.is_dir():
        pytest.fail("FEM diagnostic refused: attempt output directory is missing", pytrace=False)
    return output_dir


def _load_frozen_contract() -> dict[str, Any]:
    payload = CONTRACT_PATH.read_bytes()
    if _sha256(payload) != CONTRACT_SHA256:
        raise RuntimeError("frozen HEX8-SRI contract hash changed; diagnostic stopped")
    contract = json.loads(payload.decode("utf-8"))
    if contract.get("contract_id") != "WP13-12-HEX8-SRI-MATURATION-001":
        raise RuntimeError("unexpected frozen HEX8-SRI contract")
    return contract


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else repr(number)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, Path):
        return str(value)
    return value


def _write_attempt_evidence(
    output_dir: Path,
    case_id: str,
    record: dict[str, Any],
    arrays: dict[str, np.ndarray],
) -> tuple[Path, Path]:
    """Write immutable NPZ and JSON sidecars into controller-inventoried output."""
    case_dir = output_dir / f"wp12-elements-{case_id}"
    case_dir.mkdir(exist_ok=False)

    array_stream = io.BytesIO()
    np.savez_compressed(array_stream, **arrays)
    archive_bytes = array_stream.getvalue()
    archive_path = case_dir / "numerical-state.npz"
    with archive_path.open("xb") as stream:
        stream.write(archive_bytes)

    manifest = {
        "archive_file": archive_path.name,
        "archive_sha256": _sha256(archive_bytes),
        "archive_bytes": len(archive_bytes),
        "arrays": {
            name: {"shape": list(value.shape), "dtype": str(value.dtype)}
            for name, value in sorted(arrays.items())
        },
        "stdout_capture_independent": True,
    }
    record["archive"] = manifest
    record_path = case_dir / "result.json"
    with record_path.open("xb") as stream:
        stream.write(
            json.dumps(_json_ready(record), sort_keys=True, indent=2, allow_nan=False).encode("utf-8")
        )
    return archive_path, record_path


def _mesh(nx: int, *, distortion: str) -> tuple[np.ndarray, list[list[int]]]:
    ny = nz = 2
    nodes: list[list[float]] = []
    node_ids: dict[tuple[int, int, int], int] = {}
    for k in range(nz + 1):
        for j in range(ny + 1):
            for i in range(nx + 1):
                x = LENGTH_M * i / nx
                y = WIDTH_M * j / ny
                z = HEIGHT_M * k / nz
                x_ratio = x / LENGTH_M
                if distortion == "near_degenerate_valid":
                    z = 0.04 * z + 0.006 * x_ratio * (y - 0.5 * WIDTH_M)
                elif distortion != "regular":
                    raise ValueError(f"unsupported diagnostic geometry {distortion!r}")
                node_ids[i, j, k] = len(nodes)
                nodes.append([x, y, z])

    elements: list[list[int]] = []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                elements.append(
                    [
                        node_ids[i, j, k],
                        node_ids[i + 1, j, k],
                        node_ids[i + 1, j + 1, k],
                        node_ids[i, j + 1, k],
                        node_ids[i, j, k + 1],
                        node_ids[i + 1, j, k + 1],
                        node_ids[i + 1, j + 1, k + 1],
                        node_ids[i, j + 1, k + 1],
                    ]
                )
    return np.asarray(nodes, dtype=float), elements


def _local_dofs(connectivity: list[int]) -> np.ndarray:
    return np.asarray(
        [[3 * node, 3 * node + 1, 3 * node + 2] for node in connectivity], dtype=int
    ).ravel()


def _run_sri_diagnostic(
    request: pytest.FixtureRequest,
    *,
    case_id: str,
    nx: int,
    nu: float,
    distortion: str,
    expected_total_dofs: int,
) -> None:
    # DDL selection and controller evidence location are checked before mesh
    # construction, element assembly, or any other FEM operation.
    selected_dofs = _preselect_total_dofs(nx, expected_total_dofs)
    output_dir = _active_attempt_output_dir(selected_dofs)
    solver_root = (ROOT / "src/solveur").resolve()
    for solver_class in (Hex8SRIElement, Hex8Element):
        solver_module = sys.modules[solver_class.__module__]
        solver_origin = Path(str(solver_module.__file__)).resolve()
        if not _is_within(solver_origin, solver_root):
            pytest.fail(
                f"FEM diagnostic refused: {solver_class.__name__} imported "
                f"outside this worktree: {solver_origin}",
                pytrace=False,
            )
    contract = _load_frozen_contract()
    attempt_dir = output_dir.parent
    record: dict[str, Any] = {
        "schema": "wp12-hex8-sri-diagnostic-v1",
        "status": "started",
        "case_id": case_id,
        "nodeid": request.node.nodeid,
        "worktree_id": "wp12_elements",
        "selected_total_dofs": selected_dofs,
        "selection_basis": "27 * (nx + 1), total model DOFs before supports",
        "registered_maximum_total_dofs": MAX_REGISTERED_DOFS,
        "inputs": {
            "formulation": "HEX8-SRI",
            "E_Pa": YOUNG_MODULUS_PA,
            "nu": nu,
            "nx": nx,
            "ny": 2,
            "nz": 2,
            "distortion": distortion,
            "length_m": LENGTH_M,
            "width_m": WIDTH_M,
            "height_m": HEIGHT_M,
            "total_end_load_N": TOTAL_LOAD_N,
            "load_direction_global": [0.0, 0.0, -1.0],
            "end_face_nodes": 9,
        },
        "frozen_contract": {
            "path": "qualification/0_2_8/wp13_12_hex8_sri_maturation_contract.json",
            "sha256": CONTRACT_SHA256,
            "gates": contract["gates"],
        },
        "attempt_directory": str(attempt_dir),
        "runtime": {
            "python": sys.version,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "git_head": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "hex8_sri_source_sha256": _sha256_file(SRI_SOURCE),
            "standard_hex8_source_sha256": _sha256_file(STANDARD_HEX8_SOURCE),
        },
    }
    arrays: dict[str, np.ndarray] = {}

    try:
        nodes, elements = _mesh(nx, distortion=distortion)
        dof_count = 3 * len(nodes)
        if dof_count != selected_dofs:
            raise RuntimeError(f"mesh generated {dof_count} DDL after preselecting {selected_dofs}")
        stiffness = np.zeros((dof_count, dof_count), dtype=float)
        arrays["coordinates_m"] = nodes
        arrays["connectivity"] = np.asarray(elements, dtype=np.int64)
        arrays["K_N_per_m"] = stiffness

        element = Hex8SRIElement(SolidMaterial(E=YOUNG_MODULUS_PA, nu=nu))
        determinants: list[float] = []
        for connectivity in elements:
            coordinates = nodes[connectivity]
            local_dofs = _local_dofs(connectivity)
            stiffness[np.ix_(local_dofs, local_dofs)] += element.stiffness(coordinates)
            determinants.extend(
                element.jacobian_determinant(coordinates, point)
                for point in Hex8Element.integration_points
            )
        arrays["K_N_per_m"] = stiffness
        arrays["gauss_determinants_m3"] = np.asarray(determinants, dtype=float)

        force = np.zeros(dof_count, dtype=float)
        free_end_nodes = np.flatnonzero(np.isclose(nodes[:, 0], LENGTH_M))
        force[3 * free_end_nodes + 2] = -TOTAL_LOAD_N / float(free_end_nodes.size)
        fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
        fixed_dofs = (3 * fixed_nodes[:, None] + np.arange(3)).reshape(-1)
        fixed_mask = np.zeros(dof_count, dtype=bool)
        fixed_mask[fixed_dofs] = True
        free_dofs = np.flatnonzero(~fixed_mask)
        displacement = np.zeros(dof_count, dtype=float)
        reactions = np.zeros(dof_count, dtype=float)
        arrays.update(
            {
                "F_N": force,
                "fixed_dof_mask": fixed_mask,
                "free_dof_indices": free_dofs,
                "u_m": displacement,
                "R_N": reactions,
            }
        )
        displacement[free_dofs] = np.linalg.solve(
            stiffness[np.ix_(free_dofs, free_dofs)], force[free_dofs]
        )

        raw_residual = stiffness @ displacement - force
        reactions[fixed_dofs] = raw_residual[fixed_dofs]
        dof_equilibrium_residual = raw_residual - reactions
        arrays["Ku_minus_F_N"] = raw_residual
        arrays["Ku_minus_F_minus_R_N"] = dof_equilibrium_residual
        force_rows = force.reshape((-1, 3))
        reaction_rows = reactions.reshape((-1, 3))
        applied_force_resultant = force_rows.sum(axis=0)
        reaction_force_resultant = reaction_rows.sum(axis=0)
        force_closure = applied_force_resultant + reaction_force_resultant
        applied_moment_terms = np.cross(nodes, force_rows)
        reaction_moment_terms = np.cross(nodes, reaction_rows)
        applied_moment = applied_moment_terms.sum(axis=0)
        reaction_moment = reaction_moment_terms.sum(axis=0)
        moment_closure = applied_moment + reaction_moment
        strain_energy = float(0.5 * displacement @ stiffness @ displacement)
        external_work = float(0.5 * displacement @ force)
        energy_difference = abs(strain_energy - external_work)
        legacy_energy_error = energy_difference / max(abs(external_work), 1.0)
        scale_free_energy_error = energy_difference / max(
            abs(strain_energy), abs(external_work), np.finfo(float).tiny
        )
        force_norm = max(float(np.linalg.norm(force)), 1.0)
        dof_equilibrium_relative = float(np.linalg.norm(dof_equilibrium_residual) / force_norm)
        free_residual_relative = float(np.linalg.norm(dof_equilibrium_residual[free_dofs]) / force_norm)
        force_closure_relative = float(np.linalg.norm(force_closure) / force_norm)
        moment_closure_relative = float(
            np.linalg.norm(moment_closure) / max(float(np.linalg.norm(force)) * LENGTH_M, 1.0)
        )

        arrays.update(
            {
                "u_m": displacement,
                "F_N": force,
                "fixed_dof_mask": fixed_mask,
                "free_dof_indices": free_dofs,
                "R_N": reactions,
                "applied_moment_contributions_Nm": applied_moment_terms,
                "reaction_moment_contributions_Nm": reaction_moment_terms,
            }
        )
        metrics: dict[str, Any] = {
            "node_count": int(nodes.shape[0]),
            "element_count": len(elements),
            "total_dofs": dof_count,
            "free_dofs": int(free_dofs.size),
            "applied_force_resultant_N": applied_force_resultant.tolist(),
            "reaction_force_resultant_N": reaction_force_resultant.tolist(),
            "force_closure_components_N": force_closure.tolist(),
            "dof_equilibrium_residual_relative": dof_equilibrium_relative,
            "free_residual_relative": free_residual_relative,
            "external_resultant_force_balance_relative": force_closure_relative,
            "applied_moment_about_origin_Nm": applied_moment.tolist(),
            "reaction_moment_about_origin_Nm": reaction_moment.tolist(),
            "moment_closure_components_Nm": moment_closure.tolist(),
            "moment_balance_relative": moment_closure_relative,
            "strain_energy_U_J": strain_energy,
            "ramped_external_work_W_J": external_work,
            "energy_difference_abs_J": energy_difference,
            "energy_identity_relative_legacy": legacy_energy_error,
            "energy_identity_relative_scale_free": scale_free_energy_error,
            "gauss_determinant_min_m3": float(np.min(determinants)),
            "gauss_determinant_max_m3": float(np.max(determinants)),
            "finite": bool(
                np.all(np.isfinite(stiffness))
                and np.all(np.isfinite(displacement))
                and np.all(np.isfinite(force))
                and np.all(np.isfinite(reactions))
            ),
        }
        record["status"] = "completed"
        record["metrics"] = metrics
        record["gate_evaluation"] = {
            "energy_identity_relative": legacy_energy_error
            <= float(contract["gates"]["energy_identity_relative"]),
            "dof_equilibrium_residual_relative": dof_equilibrium_relative
            <= float(contract["gates"]["force_balance_relative"]),
            # The historical WP13 runner used this resultant closure for its
            # force_balance_relative field. Keep it visible and gated at the
            # same frozen value without conflating it with the contract formula.
            "external_resultant_force_balance_relative": force_closure_relative
            <= float(contract["gates"]["force_balance_relative"]),
            "moment_balance_relative": moment_closure_relative
            <= float(contract["gates"]["moment_balance_relative"]),
        }
        archive_path, record_path = _write_attempt_evidence(output_dir, case_id, record, arrays)
    except Exception as exc:
        record["status"] = "calculation_or_archive_error"
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        partial_determinants = locals().get("determinants")
        if (
            partial_determinants is not None
            and "gauss_determinants_m3" not in arrays
        ):
            arrays["gauss_determinants_m3"] = np.asarray(partial_determinants, dtype=float)
        if arrays and not (output_dir / f"wp12-elements-{case_id}").exists():
            _write_attempt_evidence(output_dir, case_id, record, arrays)
        raise

    failed_gates = [name for name, passed in record["gate_evaluation"].items() if not passed]
    assert not failed_gates, (
        f"{case_id} failed frozen HEX8-SRI gates {failed_gates}; "
        f"metrics={json.dumps(_json_ready(record['metrics']), sort_keys=True)}; "
        f"archives={archive_path} and {record_path}"
    )


def test_wp12_hex8_sri_near_incompressible_nu04999_nx16(
    request: pytest.FixtureRequest,
) -> None:
    """Reproduce the regular nu=0.4999 SRI cantilever failure at 459 total DDL."""
    _run_sri_diagnostic(
        request,
        case_id="sri-regular-nu04999-nx16",
        nx=16,
        nu=0.4999,
        distortion="regular",
        expected_total_dofs=459,
    )


def test_wp12_hex8_sri_near_degenerate_nu0495_nx4(
    request: pytest.FixtureRequest,
) -> None:
    """Reproduce the nu=0.495 near-degenerate SRI case at 135 total DDL."""
    _run_sri_diagnostic(
        request,
        case_id="sri-near-degenerate-nu0495-nx4",
        nx=4,
        nu=0.495,
        distortion="near_degenerate_valid",
        expected_total_dofs=135,
    )
