# ruff: noqa: F401, F403, F405

"""Implementation group for the nonlinear robustness campaign: robustness_mesh."""

from __future__ import annotations

from solveur.verification.robustness_support import *  # noqa: F401,F403



def multi_element_mesh(element_type: str) -> tuple[np.ndarray, list[list[int]]]:
    """Build two connected elements for the common global J2 benchmark."""
    family = str(element_type).upper()
    if family in {"HEX8", "HEX20"}:
        node_ids: dict[tuple[float, float, float], int] = {}
        elements: list[list[int]] = []

        def node_id(point: np.ndarray | tuple[float, float, float]) -> int:
            key = tuple(float(value) for value in point)
            if key not in node_ids:
                node_ids[key] = len(node_ids)
            return node_ids[key]

        edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
        for x0 in (0.0, 1.0):
            corners = np.asarray(
                [[x0, 0, 0], [x0 + 1, 0, 0], [x0 + 1, 1, 0], [x0, 1, 0], [x0, 0, 1], [x0 + 1, 0, 1], [x0 + 1, 1, 1], [x0, 1, 1]],
                dtype=float,
            )
            corner_ids = [node_id(point) for point in corners]
            if family == "HEX8":
                elements.append(corner_ids)
            else:
                midpoint_ids = [node_id(0.5 * (corners[first] + corners[second])) for first, second in edges]
                elements.append(corner_ids + midpoint_ids)
        nodes = np.zeros((len(node_ids), 3), dtype=float)
        for point, index in node_ids.items():
            nodes[index] = point
        return nodes, elements
    if family in {"TET4", "TET10"}:
        corners = np.asarray([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 1]], dtype=float)
        base_elements = ((0, 1, 2, 3), (1, 2, 3, 4))
        if family == "TET4":
            return corners, [list(item) for item in base_elements]
        node_ids = {tuple(point): index for index, point in enumerate(corners)}
        edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
        elements = []
        for element in base_elements:
            midpoint_ids = []
            for first, second in edges:
                point = tuple(0.5 * (corners[element[first]] + corners[element[second]]))
                node_ids.setdefault(point, len(node_ids))
                midpoint_ids.append(node_ids[point])
            elements.append(list(element) + midpoint_ids)
        nodes = np.zeros((len(node_ids), 3), dtype=float)
        for point, index in node_ids.items():
            nodes[index] = point
        return nodes, elements
    raise ValueError(f"Unsupported robustness element {element_type!r}.")


def mesh_refinement_mesh(element_type: str, cells: int) -> tuple[np.ndarray, list[list[int]]]:
    """Build a regular unit-block mesh at one refinement level.

    The topology is shared by all four families: HEX families use the block
    directly, while TET families split each block into five tetrahedra. Higher
    order nodes are generated from globally shared edge midpoints, so the
    comparison exercises the same assembled interface rather than independent
    element samples.
    """
    family = str(element_type).upper()
    if family not in ELEMENT_TYPES:
        raise ValueError(f"Unsupported robustness element {element_type!r}.")
    if isinstance(cells, bool) or not isinstance(cells, int) or cells < 1:
        raise ValueError("Mesh refinement cells must be a positive integer.")

    coordinates: list[tuple[float, float, float]] = []
    node_ids: dict[tuple[float, float, float], int] = {}

    def node_id(point: np.ndarray | tuple[float, float, float]) -> int:
        key = tuple(round(float(value), 14) for value in point)
        if key not in node_ids:
            node_ids[key] = len(coordinates)
            coordinates.append(key)
        return node_ids[key]

    def block_corners(index: int) -> list[int]:
        x0 = index / cells
        x1 = (index + 1) / cells
        points = (
            (x0, 0.0, 0.0),
            (x1, 0.0, 0.0),
            (x1, 1.0, 0.0),
            (x0, 1.0, 0.0),
            (x0, 0.0, 1.0),
            (x1, 0.0, 1.0),
            (x1, 1.0, 1.0),
            (x0, 1.0, 1.0),
        )
        return [node_id(point) for point in points]

    edge_order = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
    tet_corner_templates = ((0, 1, 3, 4), (1, 2, 3, 6), (1, 3, 4, 6), (1, 4, 5, 6), (3, 4, 6, 7))
    elements: list[list[int]] = []
    for index in range(cells):
        corners = block_corners(index)
        if family in {"HEX8", "HEX20"}:
            if family == "HEX8":
                elements.append(corners)
            else:
                mids = [node_id(0.5 * (np.asarray(coordinates[corners[first]]) + np.asarray(coordinates[corners[second]]))) for first, second in edge_order]
                elements.append(corners + mids)
            continue
        for template in tet_corner_templates:
            tet = [corners[position] for position in template]
            signed_volume = Tet4Element.signed_volume(np.asarray([coordinates[item] for item in tet]))
            if signed_volume < 0.0:
                tet[2], tet[3] = tet[3], tet[2]
            if family == "TET4":
                elements.append(tet)
                continue
            mids = [
                node_id(
                    0.5
                    * (
                        np.asarray(coordinates[tet[first]])
                        + np.asarray(coordinates[tet[second]])
                    )
                )
                for first, second in ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
            ]
            elements.append(tet + mids)
    return np.asarray(coordinates, dtype=float), elements


def _refinement_model(element_type: str, cells: int) -> FiniteElementModel:
    nodes, elements = mesh_refinement_mesh(element_type, cells)
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": element_type, "nodes": item, "material": "j2"} for item in elements],
        materials={"j2": {"type": "von_mises_elastoplastic_3d", "E": 1000.0, "nu": 0.3, "yield_stress": 0.02, "hardening_modulus": 10.0}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=[{"node": int(node), "dof": "UX", "value": 1.0 / len(loaded_nodes)} for node in loaded_nodes],
        analysis={"type": "nonlinear_static", "method": "newton_raphson", "load_path": [0.25, 0.5, 0.75, 1.0], "max_iterations": 40, "tolerance": 1.0e-7},
    )


def _reaction_norm(result: Any) -> float:
    """Extract the reaction norm without coupling the campaign to an audit type."""
    if result.audit is None:
        return 0.0
    for vector in result.audit.vectors:
        name = vector.get("name", "") if isinstance(vector, dict) else getattr(vector, "name", "")
        if name == "reactions":
            return float(vector.get("norm", 0.0) if isinstance(vector, dict) else vector.norm)
    return 0.0


def run_mesh_refinement_benchmark(
    element_types: tuple[str, ...] = ELEMENT_TYPES,
    levels: tuple[int, ...] = (1, 2, 4),
) -> dict[str, Any]:
    """Record assembled J2 response trends across regular mesh refinements."""
    if not levels or any(level < 1 for level in levels) or tuple(sorted(set(levels))) != levels:
        raise ValueError("Mesh refinement levels must be a non-empty increasing tuple of positive integers.")
    rows: list[dict[str, Any]] = []
    for family in element_types:
        family_rows: list[dict[str, Any]] = []
        for cells in levels:
            started = perf_counter()
            result = solve_model(_refinement_model(family, cells), enforce_policy=False)
            steps = result.to_dict()["solver"]["steps"]
            final = steps[-1]
            von_mises_max = max(
                (float(row.get("von_mises", 0.0)) for row in result.element_results),
                default=0.0,
            )
            family_rows.append(
                {
                    "element": family,
                    "cells_x": cells,
                    "node_count": int(result.node_count),
                    "element_count": int(result.element_count),
                    "dof_count": int(result.displacements.size),
                    "tip_displacement_norm": float(np.linalg.norm(result.displacements)),
                    "reaction_norm": _reaction_norm(result),
                    "von_mises_max": von_mises_max,
                    "peeq_max": float(final["equivalent_plastic_strain_max"]),
                    "plastic_dissipation": float(final["plastic_dissipation_max"]),
                    "energy": float(sum(step["incremental_internal_work"] for step in steps)),
                    "newton_iterations": int(sum(step["iterations"] for step in steps)),
                    "maximum_relative_residual": float(max(step["relative_residual"] for step in steps)),
                    "elapsed_seconds": float(perf_counter() - started),
                    "status": "PASS" if result.status == "PASS" else "FAIL",
                }
            )
        coarse = family_rows[0]
        fine = family_rows[-1]
        fine["change_from_coarse"] = {
            key: abs(float(fine[key]) - float(coarse[key])) / max(abs(float(fine[key])), 1.0e-15)
            for key in ("tip_displacement_norm", "reaction_norm", "von_mises_max", "peeq_max", "energy")
        }
        rows.append({"element": family, "levels": family_rows, "status": "PASS" if all(row["status"] == "PASS" for row in family_rows) else "FAIL"})
    return {
        "status": "PASS_INTERNAL_MESH_REFINEMENT" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "levels": list(levels),
        "rows": rows,
        "owner_acceptance_band_required": True,
        "limitations": [
            "Regular unit-block mesh with a single x refinement direction.",
            "The recorded trends are internal evidence; no convergence threshold is invented.",
            "External solver correlation and physical validation remain separate gates.",
        ],
    }


def _multi_element_model(element_type: str) -> FiniteElementModel:
    nodes, elements = multi_element_mesh(element_type)
    fixed = [
        {"node": index, "dofs": ["UX", "UY", "UZ"]}
        for index, point in enumerate(nodes)
        if point[0] <= 1.0e-12
    ]
    anchor = next(index for index, point in enumerate(nodes) if np.allclose(point, [1.0, 0.0, 0.0]))
    fixed.append({"node": anchor, "dofs": ["UY", "UZ"]})
    load_node = max(range(len(nodes)), key=lambda index: float(nodes[index, 0]))
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": element_type, "nodes": item, "material": "j2"} for item in elements],
        materials={"j2": {"type": "von_mises_elastoplastic_3d", "E": 1000.0, "nu": 0.3, "yield_stress": 0.02, "hardening_modulus": 10.0}},
        fixed_dofs=fixed,
        loads=[{"node": load_node, "dof": "UX", "value": 1.0}],
        analysis={"type": "nonlinear_static", "method": "newton_raphson", "load_path": [0.25, 0.5, 0.75, 1.0], "max_iterations": 40, "tolerance": 1.0e-7},
    )


def run_cyclic_load_benchmark(element_types: tuple[str, ...] = ELEMENT_TYPES) -> dict[str, Any]:
    """Exercise global loading, unloading, reversal and reloading paths."""
    path = [
        0.1,
        0.2,
        0.3,
        0.4,
        0.5,
        0.6,
        0.7,
        0.8,
        0.9,
        1.0,
        0.8,
        0.6,
        0.4,
        0.2,
        0.0,
        -0.1,
        -0.2,
        -0.3,
        -0.4,
        -0.5,
        -0.4,
        -0.3,
        -0.2,
        -0.1,
        0.0,
        0.1,
        0.2,
        0.3,
        0.4,
        0.5,
        0.6,
        0.7,
        0.8,
        0.9,
        1.0,
    ]
    load_scale = 0.2
    rows: list[dict[str, Any]] = []
    for family in element_types:
        model = _multi_element_model(family)
        model.loads = [replace(load, value=load.value * load_scale) for load in model.loads]
        model.analysis = replace(
            model.analysis,
            parameters={**model.analysis.parameters, "load_path": path, "max_iterations": 80},
        )
        result = solve_model(model, enforce_policy=False)
        steps = result.to_dict()["solver"]["steps"]
        peeq_history = [float(step["equivalent_plastic_strain_max"]) for step in steps]
        dissipation_history = [float(step["plastic_dissipation_max"]) for step in steps]
        rows.append(
            {
                "element": family,
                "status": "PASS" if result.status == "PASS" and all(np.isfinite(peeq_history)) else "FAIL",
                "load_path": path,
                "load_scale": load_scale,
                "newton_iterations": int(sum(step["iterations"] for step in steps)),
                "peeq_history": peeq_history,
                "plastic_dissipation_history": dissipation_history,
                "final_peeq": peeq_history[-1],
                "final_plastic_dissipation": dissipation_history[-1],
                "maximum_relative_residual": float(max(step["relative_residual"] for step in steps)),
                "monotonic_peeq": bool(np.all(np.diff(peeq_history) >= -1.0e-12)),
                "monotonic_dissipation": bool(np.all(np.diff(dissipation_history) >= -1.0e-12)),
            }
        )
    return {
        "status": "PASS_INTERNAL_CYCLIC" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "rows": rows,
        "owner_acceptance_band_required": True,
        "limitations": [
            "The current isotropic hardening law is not a cyclic calibration claim.",
            "Bauschinger effects and experimental validation are outside this campaign.",
        ],
    }


def run_multi_element_benchmark() -> dict[str, Any]:
    """Run a connected two-element J2 history through the global solver."""
    rows: list[dict[str, Any]] = []
    for family in ELEMENT_TYPES:
        started = perf_counter()
        result = solve_model(_multi_element_model(family), enforce_policy=False)
        data = result.to_dict()
        steps = data["solver"]["steps"]
        rows.append(
            {
                "element": family,
                "status": "PASS" if result.status == "PASS" else "FAIL",
                "node_count": int(result.node_count),
                "element_count": int(result.element_count),
                "dof_count": int(result.displacements.size),
                "newton_iterations": int(sum(step["iterations"] for step in steps)),
                "maximum_relative_residual": float(max(step["relative_residual"] for step in steps)),
                "final_displacement_norm": float(np.linalg.norm(result.displacements)),
                "final_peeq": float(steps[-1]["equivalent_plastic_strain_max"]),
                "final_plastic_dissipation": float(steps[-1]["plastic_dissipation_max"]),
                "external_work": float(sum(step["incremental_external_work"] for step in steps)),
                "internal_work": float(sum(step["incremental_internal_work"] for step in steps)),
                "maximum_work_imbalance": float(max(step["relative_work_imbalance"] for step in steps)),
                "elapsed_seconds": float(perf_counter() - started),
            }
        )
    return {
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "rows": rows,
        "mesh": "two connected elements with shared interface nodes",
        "limitations": ["This is an internal V&V benchmark; it is not an external correlation or physical validation."],
    }


def _energy_balance_for_result(result: Any) -> dict[str, Any]:
    """Recover global energy terms from one converged nonlinear result.

    The solver already records incremental external and internal work. The
    elastic and plastic terms are reconstructed from committed integration
    point states so this check stays independent of the Newton implementation.
    """

    steps = result.to_dict()["solver"]["steps"]
    external_work = float(sum(float(step["incremental_external_work"]) for step in steps))
    internal_work = float(sum(float(step["incremental_internal_work"]) for step in steps))
    elastic_energy = 0.0
    plastic_dissipation = 0.0
    minimum_point_dissipation = float("inf")
    state_count = 0

    for element_index, element_result in enumerate(result.element_results):
        states = result.material_states.get(element_index, [])
        points = element_result.get("integration_points", [])
        if len(states) != len(points):
            return {
                "status": "FAIL",
                "reason": "integration_point_state_cardinality_mismatch",
                "element": element_index,
                "state_count": len(states),
                "point_count": len(points),
            }
        for point_index, point in enumerate(points):
            state = states[point_index]
            weight = float(point["weight"])
            strain = np.asarray(point["strain"], dtype=float)
            stress = np.asarray(state["stress"], dtype=float)
            plastic_strain = np.asarray(state.get("plastic_strain", np.zeros(6)), dtype=float)
            point_dissipation = float(state.get("plastic_dissipation", 0.0))
            elastic_energy += weight * 0.5 * float((strain - plastic_strain) @ stress)
            plastic_dissipation += weight * point_dissipation
            minimum_point_dissipation = min(minimum_point_dissipation, point_dissipation)
            state_count += 1

    balance_error = external_work - elastic_energy - plastic_dissipation
    relative_balance_error = abs(balance_error) / max(abs(external_work), 1.0e-15)
    finite = all(
        np.isfinite(value)
        for value in (
            external_work,
            internal_work,
            elastic_energy,
            plastic_dissipation,
            balance_error,
            relative_balance_error,
        )
    )
    nonnegative_dissipation = minimum_point_dissipation >= -1.0e-12
    return {
        "status": "PASS_INTERNAL_ENERGY" if finite and nonnegative_dissipation else "FAIL",
        "total_external_work": external_work,
        "total_internal_work": internal_work,
        "elastic_strain_energy": float(elastic_energy),
        "plastic_dissipation": float(plastic_dissipation),
        "absolute_balance_error": float(abs(balance_error)),
        "signed_balance_error": float(balance_error),
        "relative_balance_error": float(relative_balance_error),
        "minimum_point_dissipation": float(minimum_point_dissipation if state_count else 0.0),
        "nonnegative_dissipation": nonnegative_dissipation,
        "integration_point_state_count": state_count,
        "owner_acceptance_band_required": True,
        "limitations": [
            "This is an internal energy-consistency check, not physical validation.",
            "The release acceptance band remains an Owner decision; no release threshold is invented here.",
        ],
    }


def run_energy_balance_benchmark(
    element_types: tuple[str, ...] = ELEMENT_TYPES,
    load_path: tuple[float, ...] = tuple(index / 10.0 for index in range(1, 11)),
) -> dict[str, Any]:
    """Check work, elastic energy and plastic dissipation on all four families."""

    rows: list[dict[str, Any]] = []
    for family in element_types:
        model = _multi_element_model(family)
        model.analysis = replace(
            model.analysis,
            parameters={**model.analysis.parameters, "load_path": list(load_path)},
        )
        result = solve_model(model, enforce_policy=False)
        balance = _energy_balance_for_result(result)
        rows.append(
            {
                "element": family,
                "solver_status": result.status,
                **balance,
                "maximum_relative_residual": float(
                    max(step["relative_residual"] for step in result.to_dict()["solver"]["steps"])
                ),
            }
        )
    return {
        "status": "PASS_INTERNAL_ENERGY" if all(row["status"] == "PASS_INTERNAL_ENERGY" for row in rows) else "FAIL",
        "load_path": list(load_path),
        "rows": rows,
        "owner_acceptance_band_required": True,
    }


def run_adversarial_rollback_benchmark(element_type: str = "TET4") -> dict[str, Any]:
    """Reject one trial increment and verify clean cutback/retry semantics."""

    family = str(element_type).upper()
    if family not in ELEMENT_TYPES:
        raise ValueError(f"Unsupported rollback benchmark element {element_type!r}.")
    model = _multi_element_model(family)
    parameters = dict(model.analysis.parameters)
    parameters.pop("load_path", None)
    parameters.update(
        {
            "adaptive_load_steps": True,
            "initial_load_increment": 1.0,
            "min_load_increment": 0.25,
            "max_load_increment": 1.0,
            "cutback_factor": 0.5,
            "growth_factor": 1.0,
        }
    )
    model.analysis = replace(model.analysis, parameters=parameters)

    class RejectFirstTrialSolver(NonlinearStaticSolver):
        """Inject one failure after mutating only the detached trial objects."""

        attempts = 0
        first_displacement_norm = float("nan")
        committed_digest_before_failure = ""
        retry_state_digest = ""
        retry_displacement_norm = float("nan")
        clean_retry = False

        def _solve_load_step(
            self,
            model: FiniteElementModel,
            dofs: Any,
            displacement: np.ndarray,
            free: np.ndarray,
            target_load: np.ndarray,
            material_states: Any,
            step: int,
            load_factor: float,
            load_increment: float,
            cached_tangent: Any,
            max_iterations: int,
            tolerance: float,
            linear_method: str,
            min_alpha: float,
            max_reductions: int,
            armijo: float,
            previous_load: np.ndarray | None = None,
            reference_force_norm: float | None = None,
        ):
            self.attempts += 1
            if self.attempts == 1:
                self.first_displacement_norm = float(np.linalg.norm(displacement))
                self.committed_digest_before_failure = state_digest(material_states)
                displacement[:] = 123.0
                material_states[0][0]["equivalent_plastic_strain"] = 999.0
                raise NumericalConvergenceError("controlled adversarial increment rejection")
            if self.attempts == 2:
                self.retry_state_digest = state_digest(material_states)
                self.retry_displacement_norm = float(np.linalg.norm(displacement))
                self.clean_retry = bool(
                    self.retry_displacement_norm == 0.0
                    and self.retry_state_digest == self.committed_digest_before_failure
                )
            return super()._solve_load_step(
                model,
                dofs,
                displacement,
                free,
                target_load,
                material_states,
                step,
                load_factor,
                load_increment,
                cached_tangent,
                max_iterations,
                tolerance,
                linear_method,
                min_alpha,
                max_reductions,
                armijo,
                previous_load,
                reference_force_norm,
            )

    solver = RejectFirstTrialSolver()
    result = solver.solve(model)

    reference_model = _multi_element_model(family)
    reference_model.analysis = replace(
        reference_model.analysis,
        parameters={
            **reference_model.analysis.parameters,
            "load_path": [0.25, 0.5, 0.75, 1.0],
        },
    )
    reference = solve_model(reference_model, enforce_policy=False)
    displacement_error = float(
        np.linalg.norm(result.displacements - reference.displacements)
        / max(np.linalg.norm(reference.displacements), 1.0e-15)
    )
    result_steps = result.to_dict()["solver"]["steps"]
    reference_steps = reference.to_dict()["solver"]["steps"]
    peeq_error = float(
        abs(
            float(result_steps[-1]["equivalent_plastic_strain_max"])
            - float(reference_steps[-1]["equivalent_plastic_strain_max"])
        )
    )
    data = result.to_dict()["solver"]
    return {
        "element": family,
        "status": "PASS_INTERNAL_ROLLBACK" if result.status == "PASS" and solver.clean_retry and data["rejected_increments"] == 1 else "FAIL",
        "solver_status": result.status,
        "clean_retry": solver.clean_retry,
        "first_displacement_norm": solver.first_displacement_norm,
        "retry_displacement_norm": solver.retry_displacement_norm,
        "committed_digest_before_failure": solver.committed_digest_before_failure,
        "retry_state_digest": solver.retry_state_digest,
        "rejected_increments": data["rejected_increments"],
        "rejection_log": data["rejection_log"],
        "adaptive_load_path": data["load_path"],
        "reference_load_path": reference.to_dict()["solver"]["load_path"],
        "final_displacement_relative_error": displacement_error,
        "final_peeq_absolute_error": peeq_error,
        "owner_acceptance_band_required": True,
        "limitations": [
            "The first rejection is deterministic fault injection; it is not a material instability claim.",
            "The reference comparison is internal and does not close external correlation gates.",
        ],
    }


__all__ = [name for name in globals() if not name.startswith("__")]
