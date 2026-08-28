# ruff: noqa: F401, F403, F405

"""Implementation group for the nonlinear robustness campaign: robustness_foundations."""

from __future__ import annotations

from solveur.verification.robustness_support import *  # noqa: F401,F403



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
    """Compare the algorithmic tangent with central differences over states."""

    material = j2_material()
    limit = 1.0e-6
    common_steps = (1.0e-5, 1.0e-6, 1.0e-7)

    def vector(ex: float = 0.0, ey: float = 0.0, ez: float = 0.0, gxy: float = 0.0, gyz: float = 0.0, gxz: float = 0.0) -> np.ndarray:
        return np.asarray([ex, ey, ez, gxy, gyz, gxz], dtype=float)

    def committed_before(path: list[np.ndarray], index: int) -> dict[str, object]:
        state = material.initial_state()
        for strain in path[:index]:
            state = deepcopy(material.evaluate(strain, state).trial_state)
        return state

    traction_path = material_paths()["traction_unload_reload"]
    non_proportional_path = material_paths()["non_proportional"]
    shear_path = material_paths()["pure_shear"]
    cases = [
        ("elastic", vector(ex=1.0e-5), material.initial_state(), common_steps),
        ("near_yield_elastic", vector(ex=2.5e-5), material.initial_state(), (1.0e-7, 1.0e-8, 1.0e-9)),
        ("plastic_traction", vector(ex=0.08, ey=0.005, ez=-0.002, gxy=0.01, gyz=-0.004, gxz=0.006), material.initial_state(), common_steps),
        ("plastic_compression", vector(ex=-0.08), material.initial_state(), common_steps),
        ("plastic_shear", vector(gxy=0.05), material.initial_state(), common_steps),
        ("plastic_non_proportional", non_proportional_path[-1], committed_before(non_proportional_path, len(non_proportional_path) - 1), (1.0e-6, 1.0e-7, 1.0e-8)),
        ("plastic_reload", traction_path[-1], committed_before(traction_path, len(traction_path) - 1), (1.0e-6, 1.0e-7, 1.0e-8)),
        ("plastic_shear_cycle", shear_path[-1], committed_before(shear_path, len(shear_path) - 1), (1.0e-6, 1.0e-7, 1.0e-8)),
    ]
    case_rows: list[dict[str, Any]] = []
    for name, strain, committed, steps in cases:
        response = material.evaluate(strain, committed)
        errors: list[float] = []
        for step in steps:
            numerical = np.column_stack(
                [
                    (
                        material.evaluate(strain + step * np.eye(6)[column], committed).stress
                        - material.evaluate(strain - step * np.eye(6)[column], committed).stress
                    )
                    / (2.0 * step)
                    for column in range(6)
                ]
            )
            errors.append(float(np.linalg.norm(response.tangent - numerical) / max(np.linalg.norm(numerical), 1.0)))
        case_rows.append(
            {
                "name": name,
                "steps": list(steps),
                "relative_errors": errors,
                "maximum_relative_error": max(errors),
                "elastic": bool(response.trial_state.get("elastic", False)),
                "yield_function": float(response.trial_state.get("yield_function", 0.0)),
                "equivalent_plastic_strain": float(response.trial_state.get("equivalent_plastic_strain", 0.0)),
                "status": "PASS" if max(errors) < limit and all(np.isfinite(errors)) else "FAIL",
            }
        )
    primary = next(row for row in case_rows if row["name"] == "plastic_traction")
    maximum_error = max(row["maximum_relative_error"] for row in case_rows)
    return {
        "status": "PASS" if all(row["status"] == "PASS" for row in case_rows) else "FAIL",
        "steps": list(common_steps),
        "relative_errors": primary["relative_errors"],
        "maximum_relative_error": maximum_error,
        "limit": limit,
        "cases": case_rows,
        "scope": "elastic, near-yield, traction, compression, shear, reload and non-proportional committed states",
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


def _newton_rate_metrics(residual_histories: list[list[float]]) -> dict[str, Any]:
    """Summarize observed Newton residual reduction without claiming a rate.

    The histories are evidence emitted by the solver.  This helper only
    describes the observed sequence; it deliberately does not classify a
    method as quadratic or convergent and therefore cannot hide a failed
    increment behind a scalar score.
    """

    reduction_ratios: list[list[float]] = []
    observed_orders: list[list[float]] = []
    monotone_histories: list[bool] = []
    finite_histories: list[bool] = []
    for history in residual_histories:
        values = [float(value) for value in history]
        finite = bool(values) and bool(np.all(np.isfinite(values)))
        finite_histories.append(finite)
        monotone_histories.append(
            finite
            and all(next_value <= current * (1.0 + 1.0e-12) for current, next_value in zip(values, values[1:]))
        )

        ratios: list[float] = []
        for current, next_value in zip(values, values[1:]):
            if current > 0.0 and np.isfinite(current) and np.isfinite(next_value):
                ratio = next_value / current
                if np.isfinite(ratio):
                    ratios.append(float(ratio))
        reduction_ratios.append(ratios)

        orders: list[float] = []
        for previous, current, next_value in zip(values, values[1:], values[2:]):
            if min(previous, current, next_value) <= 0.0 or not np.all(np.isfinite([previous, current, next_value])):
                continue
            denominator = float(np.log(current / previous))
            numerator = float(np.log(next_value / current))
            if abs(denominator) <= 1.0e-14:
                continue
            order = numerator / denominator
            if np.isfinite(order):
                orders.append(float(order))
        observed_orders.append(orders)

    flat_ratios = [ratio for history in reduction_ratios for ratio in history]
    return {
        "history_count": len(residual_histories),
        "finite_histories": bool(finite_histories) and all(finite_histories),
        "monotone_nonincreasing": bool(monotone_histories) and all(monotone_histories),
        "residual_reduction_ratios": reduction_ratios,
        "observed_order_estimates": observed_orders,
        "final_reduction_ratios": [history[-1] if history else None for history in reduction_ratios],
        "maximum_reduction_ratio": max(flat_ratios, default=None),
        "minimum_reduction_ratio": min(flat_ratios, default=None),
    }


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
            modified_histories = [list(map(float, step.get("residual_history", []))) for step in modified["solver"]["steps"]]
            modified_row = {"status": modified["status"], "iterations": int(sum(step["iterations"] for step in modified["solver"]["steps"])), "maximum_relative_residual": float(max(step["relative_residual"] for step in modified["solver"]["steps"])), "residual_histories": modified_histories, "rate_metrics": _newton_rate_metrics(modified_histories)}
        except Exception as error:
            modified_row = {"status": "NON_CONVERGED", "iterations": 30 * 4, "maximum_relative_residual": None, "failure_reason": type(error).__name__, "residual_histories": [], "rate_metrics": _newton_rate_metrics([])}
        if exact_row is not None:
            full_histories = exact_row.get("residual_histories", [])
            full_row = {"status": exact_row["status"], "iterations": exact_row["newton_iterations"], "maximum_relative_residual": exact_row["maximum_relative_residual"], "residual_histories": full_histories, "rate_metrics": exact_row.get("rate_metrics", _newton_rate_metrics(full_histories))}
        else:
            full_histories = [list(map(float, step.get("residual_history", []))) for step in exact["solver"]["steps"]]
            full_row = {"status": exact["status"], "iterations": int(sum(step["iterations"] for step in exact["solver"]["steps"])), "maximum_relative_residual": float(max(step["relative_residual"] for step in exact["solver"]["steps"])), "residual_histories": full_histories, "rate_metrics": _newton_rate_metrics(full_histories)}
        rows.append({"element": family, "full_newton": full_row, "modified_newton": modified_row})
    return {"status": "PASS_CHARACTERIZED" if all(row["full_newton"]["status"] == "PASS" and row["modified_newton"]["status"] in {"PASS", "NON_CONVERGED"} for row in rows) else "FAIL", "rows": rows, "interpretation": "Full Newton is the qualified path; modified Newton is characterized and any non-convergence is explicit."}


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
        residual_histories = [list(map(float, step.get("residual_history", []))) for step in steps]
        rows.append({"element": family, "status": "PASS" if result.status == "PASS" else "FAIL", "dof_count": int(result.displacements.size), "newton_iterations": int(sum(step["iterations"] for step in steps)), "maximum_relative_residual": float(max(step["relative_residual"] for step in steps)), "final_displacement_norm": float(np.linalg.norm(result.displacements)), "final_peeq": float(steps[-1]["equivalent_plastic_strain_max"]), "elapsed_seconds": float(perf_counter() - started), "reaction_norm": reaction_norm, "residual_histories": residual_histories, "rate_metrics": _newton_rate_metrics(residual_histories)})
    rate = run_newton_rate_study(rows)
    return {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "rows": rows, "load_path": [0.25, 0.5, 0.75, 1.0], "newton_rate_study": rate}


__all__ = [name for name in globals() if not name.startswith("__")]
