"""Prospective, exact-H1 operator audit; gated for the local V&V runner only."""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest


CASE_ID = "TET4-H1-OPERATOR-AUDIT-002"
NODEID = "tests/unit/test_wp12_v2_tet4_operator_audit.py::test_tet4_h1_operator_audit_002"
RESULT_MARKER = "QF_VV_NUMERIC_RESULT="
H1_FIXTURE_SHA256 = "4807fea4cde876f57ef1e376f9b0791f5367526d182e236655b39e73e57baa7d"
U3_RECEIPT_SHA256 = "c47a566d97998746a58823ce3f88b5f4950b7cf597bf62129f72aa54c3956542"
U3_MANIFEST_SHA256 = "3f10c7156c6f4e5eaf07f0bf66a92fe3f7cc6ef9031c200c1e41ca1087bf2a1c"
U3_ARCHIVE_FIELDS_SHA256 = "a862bd016bb408566459491b3c726694e2cd408e084031b4f693223883429ba8"
ASSEMBLED_MATRIX_RELATIVE_LIMIT = 1.0e-12
OPERATOR_COLUMN_RELATIVE_LIMIT = 1.0e-12
MATRIX_FREE_RESIDUAL_LIMIT = 1.0e-8
DIRECT_RESIDUAL_LIMIT = 1.0e-7
CHUNK_SIZE = 8192


def _local_vv_environment_is_bound() -> bool:
    return (
        os.environ.get("QF_LOCAL_VV_EXPECTED_NODEID") == NODEID
        and bool(os.environ.get("QF_LOCAL_VV_SELECTION_PATH"))
        and bool(os.environ.get("QF_LOCAL_VV_EXPECTED_SOURCE_ROOT"))
    )


def _fraction(value: float) -> Fraction:
    return Fraction.from_float(float(value))


def _determinant(matrix: list[list[Fraction]]) -> Fraction:
    if len(matrix) == 1:
        return matrix[0][0]
    total = Fraction(0)
    for column, value in enumerate(matrix[0]):
        minor = [row[:column] + row[column + 1 :] for row in matrix[1:]]
        total += (-1 if column % 2 else 1) * value * _determinant(minor)
    return total


def _inverse(matrix: list[list[Fraction]]) -> list[list[Fraction]]:
    size = len(matrix)
    rows = [row.copy() + [Fraction(int(i == j)) for j in range(size)] for i, row in enumerate(matrix)]
    for column in range(size):
        pivot = next((row for row in range(column, size) if rows[row][column] != 0), None)
        if pivot is None:
            raise AssertionError("the exact H1 element geometry is singular")
        rows[column], rows[pivot] = rows[pivot], rows[column]
        scale = rows[column][column]
        rows[column] = [value / scale for value in rows[column]]
        for row in range(size):
            if row == column:
                continue
            factor = rows[row][column]
            rows[row] = [left - factor * right for left, right in zip(rows[row], rows[column], strict=True)]
    return [row[size:] for row in rows]


def _exact_constitutive(young: float, poisson: float) -> list[list[Fraction]]:
    e = _fraction(young)
    nu = _fraction(poisson)
    lame_lambda = e * nu / ((1 + nu) * (1 - 2 * nu))
    shear_mu = e / (2 * (1 + nu))
    matrix = [[Fraction(0) for _ in range(6)] for _ in range(6)]
    for i in range(3):
        for j in range(3):
            matrix[i][j] = lame_lambda
        matrix[i][i] += 2 * shear_mu
    for i in range(3, 6):
        matrix[i][i] = shear_mu
    return matrix


def _exact_element_stiffness(coordinates: list[list[float]], young: float, poisson: float) -> list[list[Fraction]]:
    points = [[_fraction(value) for value in row] for row in coordinates]
    edges = [[points[column + 1][row] - points[0][row] for column in range(3)] for row in range(3)]
    gradients = [[Fraction(0) for _ in range(3)] for _ in range(4)]
    inverse_edges = _inverse(edges)
    for node in range(1, 4):
        gradients[node] = inverse_edges[node - 1].copy()
    gradients[0] = [-sum(gradients[node][axis] for node in range(1, 4)) for axis in range(3)]
    b_matrix = [[Fraction(0) for _ in range(12)] for _ in range(6)]
    for node, (gx, gy, gz) in enumerate(gradients):
        column = 3 * node
        b_matrix[0][column] = gx
        b_matrix[1][column + 1] = gy
        b_matrix[2][column + 2] = gz
        b_matrix[3][column], b_matrix[3][column + 1] = gy, gx
        b_matrix[4][column + 1], b_matrix[4][column + 2] = gz, gy
        b_matrix[5][column], b_matrix[5][column + 2] = gz, gx
    constitutive = _exact_constitutive(young, poisson)
    volume = _determinant(edges) / 6
    return [
        [
            volume
            * sum(
                (
                    b_matrix[row][i] * constitutive[row][column] * b_matrix[column][j]
                    for row in range(6)
                    for column in range(6)
                ),
                Fraction(0),
            )
            for j in range(12)
        ]
        for i in range(12)
    ]


def _exact_global_stiffness(
    nodes: list[list[float]],
    connectivity: list[list[int]],
    young: float,
    poisson: float,
) -> tuple[list[list[Fraction]], list[list[list[Fraction]]]]:
    dof_count = 3 * len(nodes)
    global_matrix = [[Fraction(0) for _ in range(dof_count)] for _ in range(dof_count)]
    element_matrices: list[list[list[Fraction]]] = []
    for element_nodes in connectivity:
        local = _exact_element_stiffness([nodes[node] for node in element_nodes], young, poisson)
        element_matrices.append(local)
        dofs = [3 * node + component for node in element_nodes for component in range(3)]
        for local_row, global_row in enumerate(dofs):
            for local_column, global_column in enumerate(dofs):
                global_matrix[global_row][global_column] += local[local_row][local_column]
    return global_matrix, element_matrices


def _gamma(additions: int) -> Fraction:
    if additions <= 0:
        return Fraction(0)
    unit_roundoff = Fraction(1, 2**53)
    product = additions * unit_roundoff
    if product >= 1:
        raise AssertionError("gamma_p is undefined for p*u >= 1")
    return product / (1 - product)


def _relative_frobenius_error_to_exact(matrix: Any, exact: list[list[Fraction]]) -> float:
    numerator = Fraction(0)
    denominator = Fraction(0)
    for row in range(len(exact)):
        for column in range(len(exact[row])):
            value = _fraction(float(matrix[row, column]))
            numerator += (value - exact[row][column]) ** 2
            denominator += exact[row][column] ** 2
    if denominator == 0:
        raise AssertionError("the exact reference matrix must be nonzero")
    return math.sqrt(float(numerator / denominator))


def _matrix_symmetry_ratio(matrix: Any) -> float:
    numerator = Fraction(0)
    denominator = Fraction(0)
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            value = _fraction(float(matrix[row, column]))
            mirror = _fraction(float(matrix[column, row]))
            numerator += (value - mirror) ** 2
            denominator += value**2
    if denominator == 0:
        raise AssertionError("a zero stiffness matrix is not a valid H1 result")
    return math.sqrt(float(numerator / denominator))


def _assemble_local_float_matrices(local_matrices: list[Any], dof_maps: list[list[int]], dof_count: int) -> Any:
    import numpy as np

    result = np.zeros((dof_count, dof_count), dtype=np.float64)
    for local, dofs in zip(local_matrices, dof_maps, strict=True):
        result[np.ix_(dofs, dofs)] += local
    return result


def _global_contributions(
    local_matrices: list[Any], dof_maps: list[list[int]]
) -> dict[tuple[int, int], list[tuple[int, float]]]:
    contributions: dict[tuple[int, int], list[tuple[int, float]]] = {}
    for element_index, (local, dofs) in enumerate(zip(local_matrices, dof_maps, strict=True)):
        for local_row, global_row in enumerate(dofs):
            for local_column, global_column in enumerate(dofs):
                contributions.setdefault((global_row, global_column), []).append(
                    (element_index, float(local[local_row, local_column]))
                )
    return contributions


def _roundoff_checks(
    matrix: Any,
    local_matrices: list[Any],
    dof_maps: list[list[int]],
    exact_global: list[list[Fraction]],
) -> tuple[bool, list[dict[str, Any]], float]:
    contributions = _global_contributions(local_matrices, dof_maps)
    records: list[dict[str, Any]] = []
    maximum_bound_ratio: float | None = 0.0
    all_passed = True
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            terms = contributions.get((row, column), [])
            exact_sum_of_inputs = sum((_fraction(value) for _, value in terms), Fraction(0))
            stored = _fraction(float(matrix[row, column]))
            accumulation_error = abs(stored - exact_sum_of_inputs)
            absolute_sum = sum((abs(_fraction(value)) for _, value in terms), Fraction(0))
            bound = _gamma(len(terms) - 1) * absolute_sum
            passed = accumulation_error <= bound
            all_passed = all_passed and passed
            if bound and maximum_bound_ratio is not None:
                maximum_bound_ratio = max(maximum_bound_ratio, float(accumulation_error / bound))
            elif accumulation_error:
                maximum_bound_ratio = None
            if accumulation_error or bound:
                records.append(
                    {
                        "row": row,
                        "column": column,
                        "contribution_count": len(terms),
                        "exact_input_sum_fraction": str(exact_sum_of_inputs),
                        "stored_binary64_hex": float(matrix[row, column]).hex(),
                        "accumulation_error_fraction": str(accumulation_error),
                        "gamma_bound_fraction": str(bound),
                        "kernel_error_fraction": str(exact_sum_of_inputs - exact_global[row][column]),
                        "passed": passed,
                    }
                )
    return all_passed, records, maximum_bound_ratio


def _symmetry_checks(
    matrix: Any, local_matrices: list[Any], dof_maps: list[list[int]]
) -> tuple[bool, list[dict[str, Any]], float, int]:
    contributions = _global_contributions(local_matrices, dof_maps)
    records: list[dict[str, Any]] = []
    all_passed = True
    maximum_bound_ratio: float | None = 0.0
    nonzero_pairs = 0
    for row in range(matrix.shape[0]):
        for column in range(row + 1, matrix.shape[1]):
            left_terms = {element: value for element, value in contributions.get((row, column), [])}
            right_terms = {element: value for element, value in contributions.get((column, row), [])}
            same_contributors = left_terms.keys() == right_terms.keys()
            local_difference = sum(
                (
                    abs(_fraction(left_terms[element]) - _fraction(right_terms[element]))
                    for element in left_terms.keys() & right_terms.keys()
                ),
                Fraction(0),
            )
            left_sum_abs = sum((abs(_fraction(value)) for value in left_terms.values()), Fraction(0))
            right_sum_abs = sum((abs(_fraction(value)) for value in right_terms.values()), Fraction(0))
            left_count = len(left_terms)
            right_count = len(right_terms)
            left_bound = _gamma(left_count - 1) * left_sum_abs
            right_bound = _gamma(right_count - 1) * right_sum_abs
            bound = local_difference + left_bound + right_bound
            difference = abs(_fraction(float(matrix[row, column])) - _fraction(float(matrix[column, row])))
            passed = same_contributors and difference <= bound
            all_passed = all_passed and passed
            if difference:
                nonzero_pairs += 1
            if bound and maximum_bound_ratio is not None:
                maximum_bound_ratio = max(maximum_bound_ratio, float(difference / bound))
            elif difference:
                maximum_bound_ratio = None
            if difference or bound or not same_contributors:
                records.append(
                    {
                        "row": row,
                        "column": column,
                        "left_contributor_elements": sorted(left_terms),
                        "right_contributor_elements": sorted(right_terms),
                        "local_mirror_difference_sum_fraction": str(local_difference),
                        "left_sum_abs_fraction": str(left_sum_abs),
                        "right_sum_abs_fraction": str(right_sum_abs),
                        "left_additions": max(left_count - 1, 0),
                        "right_additions": max(right_count - 1, 0),
                        "stored_difference_fraction": str(difference),
                        "bound_fraction": str(bound),
                        "passed": passed,
                    }
                )
    return all_passed, records, maximum_bound_ratio, nonzero_pairs


def _exact_load_vector(model: Any) -> list[Fraction]:
    load = [Fraction(0) for _ in range(model.ndof)]
    for node, component, value in zip(model.load_nodes, model.load_components, model.load_values, strict=True):
        index = 3 * int(node) + int(component)
        load[index] += _fraction(float(value))
    return load


def _exact_residual(stiffness: list[list[Fraction]], displacement: list[float], load: list[Fraction]) -> list[Fraction]:
    exact_displacement = [_fraction(value) for value in displacement]
    return [
        sum(
            (stiffness[row][column] * exact_displacement[column] for column in range(len(load))),
            Fraction(0),
        )
        - load[row]
        for row in range(len(load))
    ]


def _norm2(values: list[Fraction]) -> float:
    return math.sqrt(float(sum((value * value for value in values), Fraction(0))))


def _all_finite(*arrays: Any) -> bool:
    import numpy as np

    return all(bool(np.isfinite(np.asarray(array)).all()) for array in arrays)


def _local_matrix_entry(local_matrices: Any, element: int, row: int, column: int) -> float:
    """Read one local entry from either a list of matrices or a 3-D array."""
    return float(local_matrices[element][row, column])


def _pair_contribution_records(
    local_matrices: Any, dof_maps: list[list[int]], row_dof: int, column_dof: int
) -> list[dict[str, Any]]:
    records = []
    for element, dofs in enumerate(dof_maps):
        if row_dof in dofs and column_dof in dofs:
            records.append(
                {
                    "element": element,
                    "binary64_hex": _local_matrix_entry(
                        local_matrices, element, dofs.index(row_dof), dofs.index(column_dof)
                    ).hex(),
                }
            )
    return records


def _canonical_operator_columns(operator: Any, size: int, np: Any) -> Any:
    columns = np.zeros((size, size), dtype=np.float64)
    for column, basis in enumerate(_canonical_basis_vectors(size, np)):
        columns[:, column] = np.asarray(operator @ basis, dtype=np.float64)
    return columns


def _canonical_basis_vectors(size: int, np: Any) -> Any:
    for index in range(size):
        basis = np.zeros(size, dtype=np.float64)
        basis[index] = 1.0
        yield basis


def _emit(payload: dict[str, Any]) -> None:
    print(RESULT_MARKER + json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False))


@pytest.mark.skipif(
    not _local_vv_environment_is_bound(),
    reason="WP12-V2 is gated to its exact QUALIFICATION_LOCAL_VV runner invocation",
)
def test_tet4_h1_operator_audit_002(monkeypatch: pytest.MonkeyPatch) -> None:
    import numpy as np

    import solveur.large.assembler as assembler_module
    from solveur.elements.solid.tet4 import Tet4Element
    from solveur.large.assembler import ChunkedScipyAssembler, fixed_dof_indices
    from solveur.large.io import load_large_model
    from solveur.large.matrix_free import StructuredBlockOperator
    from solveur.large.tet4_batch import element_dofs_batch
    from solveur.materials.solid import SolidMaterial

    test_root = Path(__file__).resolve().parents[1]
    h1_fixture = test_root / "fixtures" / "wp12_u" / "tet4_h1_level1_model.h5"
    archived_fields_path = test_root / "fixtures" / "wp12_v2" / "u3_archived_solution_fields.json"
    if hashlib.sha256(h1_fixture.read_bytes()).hexdigest() != H1_FIXTURE_SHA256:
        raise AssertionError("the H1 model fixture does not match the frozen WP12-S identity")
    archive_bytes = archived_fields_path.read_bytes()
    if hashlib.sha256(archive_bytes).hexdigest() != U3_ARCHIVE_FIELDS_SHA256:
        raise AssertionError("the derived U3 archive-fields fixture changed")
    archive = json.loads(archive_bytes.decode("utf-8"))
    historical = archive["historical"]
    source = archive["source"]
    if (
        archive.get("schema") != "qf-wp12-v2-u3-archived-fields-v1"
        or source.get("receipt_sha256") != U3_RECEIPT_SHA256
        or source.get("manifest_sha256") != U3_MANIFEST_SHA256
        or source.get("run_id") != "20261026T120509Z-3a69e91f9b42"
        or historical.get("fixture_sha256") != H1_FIXTURE_SHA256
    ):
        raise AssertionError("the derived U3 fields do not bind the verified historical receipt")

    model = load_large_model(h1_fixture)
    if (model.element_count, model.node_count, model.ndof) != (12, 12, 36):
        raise AssertionError("the archived H1 model identity changed")
    if model.units != {"system": "SI"} or len(set(int(x) for x in model.material_ids)) != 1:
        raise AssertionError("the H1 units or single-material scope changed")
    material_values = model.material_for_element(0)
    young = float(material_values["E"])
    poisson = float(material_values["nu"])
    material = SolidMaterial(E=young, nu=poisson)
    batch_chunks: list[tuple[int, int, Any]] = []
    sparse_inputs: list[tuple[Any, Any, Any]] = []
    original_batch_kernel = assembler_module._stiffness_batch
    original_csr_constructor = assembler_module.csr_matrix

    def capture_batch_kernel(current_model: Any, start: int, stop: int, materials: Any) -> Any:
        values = original_batch_kernel(current_model, start, stop, materials)
        batch_chunks.append((start, stop, np.asarray(values, dtype=np.float64).copy()))
        return values

    def capture_sparse_input(argument: Any, *args: Any, **kwargs: Any) -> Any:
        if (
            isinstance(argument, tuple)
            and len(argument) == 2
            and isinstance(argument[0], np.ndarray)
            and isinstance(argument[1], tuple)
            and len(argument[1]) == 2
        ):
            values = np.asarray(argument[0], dtype=np.float64).copy()
            rows = np.asarray(argument[1][0], dtype=np.int64).copy()
            columns = np.asarray(argument[1][1], dtype=np.int64).copy()
            sparse_inputs.append((values, rows, columns))
        return original_csr_constructor(argument, *args, **kwargs)

    monkeypatch.setattr(assembler_module, "_stiffness_batch", capture_batch_kernel)
    monkeypatch.setattr(assembler_module, "csr_matrix", capture_sparse_input)
    assembly = ChunkedScipyAssembler(chunk_size=CHUNK_SIZE).assemble(model)
    if len(batch_chunks) != 1 or batch_chunks[0][:2] != (0, model.element_count):
        raise AssertionError("H1 must use the declared one-chunk batch assembly path")
    if len(sparse_inputs) != 1:
        raise AssertionError("the production chunk must feed one observable CSR constructor input")
    batch_local = batch_chunks[0][2]
    if batch_local.shape != (model.element_count, 12, 12):
        raise AssertionError("the captured production batch matrices have an unexpected shape")

    dof_maps = [
        [3 * int(node) + component for node in connectivity for component in range(3)] for connectivity in model.tet4
    ]
    production_dof_maps = np.asarray(element_dofs_batch(model.tet4), dtype=np.int64)
    if not np.array_equal(production_dof_maps, np.asarray(dof_maps, dtype=np.int64)):
        raise AssertionError("the batch DDL map differs from the independently formed node/component map")
    emitted_values, emitted_rows, emitted_columns = sparse_inputs[0]
    expected_rows = np.repeat(production_dof_maps, 12, axis=1).ravel()
    expected_columns = np.tile(production_dof_maps, (1, 12)).ravel()
    if not np.array_equal(emitted_rows, expected_rows) or not np.array_equal(emitted_columns, expected_columns):
        raise AssertionError("the observed CSR row/column stream does not match the declared DDL scatter")
    if not np.array_equal(emitted_values, batch_local.ravel()):
        raise AssertionError("the observed CSR values differ from the captured kernel output")

    scalar_element = Tet4Element(material)
    scalar_local = [scalar_element.stiffness(model.nodes[connectivity]).copy() for connectivity in model.tet4]
    scalar_global = _assemble_local_float_matrices(scalar_local, dof_maps, model.ndof)
    batch_global = assembly.stiffness.toarray()
    exact_global, exact_local = _exact_global_stiffness(model.nodes.tolist(), model.tet4.tolist(), young, poisson)
    scalar_local_symmetric = bool(np.array_equal(np.asarray(scalar_local), np.asarray(scalar_local).transpose(0, 2, 1)))
    batch_local_symmetric = bool(np.array_equal(batch_local, batch_local.transpose(0, 2, 1)))
    exact_free_from_model = [
        [exact_global[int(row)][int(column)] for column in historical["free_dofs"]] for row in historical["free_dofs"]
    ]
    archived_exact_free = [[Fraction(value) for value in row] for row in historical["full_free_matrix_exact_fractions"]]
    if exact_free_from_model != archived_exact_free:
        raise AssertionError("the independently reconstructed exact H1 free matrix differs from U3")

    exact_global_symmetric = all(
        exact_global[row][column] == exact_global[column][row]
        for row in range(model.ndof)
        for column in range(model.ndof)
    )
    scalar_relative_error = _relative_frobenius_error_to_exact(scalar_global, exact_global)
    batch_relative_error = _relative_frobenius_error_to_exact(batch_global, exact_global)
    scalar_roundoff_ok, scalar_roundoff_records, scalar_roundoff_ratio = _roundoff_checks(
        scalar_global, scalar_local, dof_maps, exact_global
    )
    batch_roundoff_ok, batch_roundoff_records, batch_roundoff_ratio = _roundoff_checks(
        batch_global, list(batch_local), dof_maps, exact_global
    )
    scalar_symmetry_ok, scalar_symmetry_records, scalar_symmetry_ratio, scalar_asymmetric_pairs = _symmetry_checks(
        scalar_global, scalar_local, dof_maps
    )
    batch_symmetry_ok, batch_symmetry_records, batch_symmetry_ratio, batch_asymmetric_pairs = _symmetry_checks(
        batch_global, list(batch_local), dof_maps
    )
    pair_14_22_contributions = {
        "K_14_22": _pair_contribution_records(batch_local, dof_maps, 14, 22),
        "K_22_14": _pair_contribution_records(batch_local, dof_maps, 22, 14),
        "scalar_K_14_22": _pair_contribution_records(scalar_local, dof_maps, 14, 22),
        "scalar_K_22_14": _pair_contribution_records(scalar_local, dof_maps, 22, 14),
    }
    if [item["element"] for item in pair_14_22_contributions["K_14_22"]] != [0, 5, 8, 9]:
        raise AssertionError("the H1 element incidence for global pair (14,22) changed")

    fixed = np.asarray(assembly.fixed_dofs, dtype=np.int64)
    matrix_free_fixed = np.asarray(fixed_dof_indices(model), dtype=np.int64)
    free = np.setdiff1d(np.arange(model.ndof, dtype=np.int64), fixed)
    if not np.array_equal(fixed, matrix_free_fixed):
        raise AssertionError("assembled and matrix-free fixed DDL maps differ")
    if free.tolist() != historical["free_dofs"] or fixed.tolist() != historical["fixed_dofs"]:
        raise AssertionError("the H1 free/fixed DDL map differs from the U3 archive")

    operator = StructuredBlockOperator(model, free=free, chunk_size=CHUNK_SIZE)
    element_template: dict[int, int] = {}
    for template_index, element_indices in enumerate(operator.element_ids_by_template):
        for element_index in np.asarray(element_indices, dtype=np.int64):
            if int(element_index) in element_template:
                raise AssertionError("a matrix-free element was assigned to more than one template")
            element_template[int(element_index)] = template_index
    if set(element_template) != set(range(model.element_count)):
        raise AssertionError("matrix-free template groups do not cover the H1 elements exactly once")

    direct_free = assembly.stiffness[free, :][:, free].toarray()
    exact_free = [[exact_global[int(row)][int(column)] for column in free] for row in free]
    exact_free_float = np.asarray([[float(value) for value in row] for row in exact_free])
    free_count = int(free.size)
    matrix_free_columns = _canonical_operator_columns(operator, free_count, np)
    column_component_records: list[dict[str, Any]] = []
    column_bound_ok = True
    for column_index, global_column_value in enumerate(free):
        global_column = int(global_column_value)
        for row_index, global_row_value in enumerate(free):
            global_row = int(global_row_value)
            contribution_count = 0
            absolute_sum = Fraction(0)
            kernel_error_bound = Fraction(0)
            for element_index, dofs in enumerate(dof_maps):
                local_columns = [index for index, value in enumerate(dofs) if value == global_column]
                if not local_columns:
                    continue
                local_column = local_columns[0]
                for local_row, row_dof in enumerate(dofs):
                    if row_dof != global_row:
                        continue
                    template_value = float(operator.templates[element_template[element_index]][local_row, local_column])
                    exact_value = exact_local[element_index][local_row][local_column]
                    exact_template_value = _fraction(template_value)
                    contribution_count += 1
                    absolute_sum += abs(exact_template_value)
                    kernel_error_bound += abs(exact_template_value - exact_value)
            scatter_bound = _gamma(contribution_count - 1) * absolute_sum
            component_bound = kernel_error_bound + scatter_bound
            observed_error = abs(
                _fraction(float(matrix_free_columns[row_index, column_index])) - exact_global[global_row][global_column]
            )
            passed = observed_error <= component_bound
            column_bound_ok = column_bound_ok and passed
            if observed_error or component_bound:
                column_component_records.append(
                    {
                        "free_row_index": row_index,
                        "free_column_index": column_index,
                        "global_row_dof": global_row,
                        "global_column_dof": global_column,
                        "contribution_count": contribution_count,
                        "kernel_error_bound_fraction": str(kernel_error_bound),
                        "scatter_gamma_bound_fraction": str(scatter_bound),
                        "observed_error_fraction": str(observed_error),
                        "passed": passed,
                    }
                )

    matrix_free_relative_error = _relative_frobenius_error_to_exact(matrix_free_columns, exact_free)
    direct_free_relative_error = _relative_frobenius_error_to_exact(direct_free, exact_free)
    route_difference_exact = [
        [
            _fraction(float(matrix_free_columns[row, column])) - _fraction(float(direct_free[row, column]))
            for column in range(free_count)
        ]
        for row in range(free_count)
    ]
    route_difference_frobenius_squared = sum((value**2 for row in route_difference_exact for value in row), Fraction(0))
    exact_free_frobenius_squared = sum((value**2 for row in exact_free for value in row), Fraction(0))
    route_relative_difference = math.sqrt(float(route_difference_frobenius_squared / exact_free_frobenius_squared))
    route_difference_frobenius = math.sqrt(float(route_difference_frobenius_squared))
    route_difference_infinity = max(
        (sum((abs(value) for value in row), Fraction(0)) for row in route_difference_exact),
        default=Fraction(0),
    )
    exact_free_infinity = max(
        (sum((abs(value) for value in row), Fraction(0)) for row in exact_free),
        default=Fraction(0),
    )
    route_difference_maximum = max(
        (abs(value) for row in route_difference_exact for value in row),
        default=Fraction(0),
    )
    exact_free_maximum = max(
        (abs(value) for row in exact_free for value in row),
        default=Fraction(0),
    )
    route_difference_relative_infinity = float(route_difference_infinity / exact_free_infinity)
    route_difference_relative_maximum = float(route_difference_maximum / exact_free_maximum)
    column_relative_errors = []
    for column in range(free_count):
        error_squared = sum(
            (
                (_fraction(float(matrix_free_columns[row, column])) - exact_free[row][column]) ** 2
                for row in range(free_count)
            ),
            Fraction(0),
        )
        exact_matrix_squared = sum((value**2 for row in exact_free for value in row), Fraction(0))
        column_relative_errors.append(math.sqrt(float(error_squared / exact_matrix_squared)))

    archived_mf = [float(value) for value in historical["displacements_matrix_free_m"]]
    archived_direct = [float(value) for value in historical["displacements_assembled_direct_m"]]
    if len(archived_mf) != model.ndof or len(archived_direct) != model.ndof:
        raise AssertionError("the archived U3 solution fields are incomplete")
    if any(archived_mf[index] != 0.0 or archived_direct[index] != 0.0 for index in fixed):
        raise AssertionError("the archived U3 fields do not retain zero fixed translations")
    exact_load = _exact_load_vector(model)
    residual_mf = _exact_residual(exact_global, archived_mf, exact_load)
    residual_direct = _exact_residual(exact_global, archived_direct, exact_load)
    if [str(value) for value in residual_mf] != historical["matrix_free_full_exact_residual_fraction_strings"]:
        raise AssertionError("the recalculated matrix-free U3 residual differs from its archived exact residual")
    if [str(value) for value in residual_direct] != historical["direct_full_exact_residual_fraction_strings"]:
        raise AssertionError("the recalculated direct U3 residual differs from its archived exact residual")
    residual_mf_free = [residual_mf[int(index)] for index in free]
    residual_direct_free = [residual_direct[int(index)] for index in free]
    if [str(value) for value in residual_mf_free] != historical["matrix_free_free_exact_residual_fraction_strings"]:
        raise AssertionError("the recalculated matrix-free free residual differs from its archive")
    if [str(value) for value in residual_direct_free] != historical["direct_free_exact_residual_fraction_strings"]:
        raise AssertionError("the recalculated direct free residual differs from its archive")

    exact_u_mf = [_fraction(value) for value in archived_mf]
    exact_u_direct = [_fraction(value) for value in archived_direct]
    exact_ku_mf = [
        sum((exact_global[row][column] * exact_u_mf[column] for column in range(model.ndof)), Fraction(0))
        for row in range(model.ndof)
    ]
    exact_ku_direct = [
        sum((exact_global[row][column] * exact_u_direct[column] for column in range(model.ndof)), Fraction(0))
        for row in range(model.ndof)
    ]
    energy_work: dict[str, dict[str, str]] = {}
    for route_name, displacement, ku, residual in (
        ("matrix_free", exact_u_mf, exact_ku_mf, residual_mf),
        ("assembled_direct", exact_u_direct, exact_ku_direct, residual_direct),
    ):
        strain_energy = (
            sum(
                (displacement[index] * ku[index] for index in range(model.ndof)),
                Fraction(0),
            )
            / 2
        )
        external_work = sum(
            (displacement[index] * exact_load[index] for index in range(model.ndof)),
            Fraction(0),
        )
        residual_work = sum(
            (displacement[int(index)] * residual[int(index)] for index in free),
            Fraction(0),
        )
        identity_left = 2 * strain_energy - external_work
        if identity_left != residual_work:
            raise AssertionError("the exact discrete energy identity 2U-W=u_free.T r_free failed")
        energy_work[route_name] = {
            "strain_energy_J_exact_fraction": str(strain_energy),
            "external_work_J_exact_fraction": str(external_work),
            "twice_energy_minus_work_J_exact_fraction": str(identity_left),
            "free_residual_work_J_exact_fraction": str(residual_work),
        }

    reaction_records: dict[str, Any] = {}
    for route_name, _ku, residual in (
        ("matrix_free", exact_ku_mf, residual_mf),
        ("assembled_direct", exact_ku_direct, residual_direct),
    ):
        support_by_node: dict[int, list[Fraction]] = {}
        for dof in fixed:
            global_dof = int(dof)
            node = global_dof // 3
            component = global_dof % 3
            support_by_node.setdefault(node, [Fraction(0), Fraction(0), Fraction(0)])[component] += residual[global_dof]
        support_force = [
            sum((force[component] for force in support_by_node.values()), Fraction(0)) for component in range(3)
        ]
        support_moment = [Fraction(0), Fraction(0), Fraction(0)]
        for node, force in support_by_node.items():
            x, y, z = [_fraction(value) for value in model.nodes[node]]
            support_moment[0] += y * force[2] - z * force[1]
            support_moment[1] += z * force[0] - x * force[2]
            support_moment[2] += x * force[1] - y * force[0]
        external_force = [
            sum((exact_load[3 * node + component] for node in range(model.node_count)), Fraction(0))
            for component in range(3)
        ]
        external_moment = [Fraction(0), Fraction(0), Fraction(0)]
        for node in range(model.node_count):
            x, y, z = [_fraction(value) for value in model.nodes[node]]
            fx, fy, fz = (exact_load[3 * node + component] for component in range(3))
            external_moment[0] += y * fz - z * fy
            external_moment[1] += z * fx - x * fz
            external_moment[2] += x * fy - y * fx
        force_defect = [support_force[i] + external_force[i] for i in range(3)]
        moment_defect = [support_moment[i] + external_moment[i] for i in range(3)]
        force_identity = []
        force_cauchy_bound = []
        for component in range(3):
            free_component_residual = [residual[int(index)] for index in free if int(index) % 3 == component]
            projection = sum(free_component_residual, Fraction(0))
            identity_holds = force_defect[component] == -projection
            squared_bound_holds = projection**2 <= len(free_component_residual) * sum(
                (value**2 for value in free_component_residual), Fraction(0)
            )
            force_identity.append(identity_holds)
            force_cauchy_bound.append(squared_bound_holds)
            if not identity_holds or not squared_bound_holds:
                raise AssertionError("the exact force balance identity or residual Cauchy bound failed")
        moment_identity = []
        moment_cauchy_bound = []
        free_residual_norm_squared = sum((residual[int(index)] ** 2 for index in free), Fraction(0))
        for axis in range(3):
            rotation_projection = Fraction(0)
            rotation_norm_squared = Fraction(0)
            for index in free:
                global_dof = int(index)
                node = global_dof // 3
                component = global_dof % 3
                x, y, z = [_fraction(value) for value in model.nodes[node]]
                rotation_vector_component = (
                    (Fraction(0), -z, y)[component]
                    if axis == 0
                    else (z, Fraction(0), -x)[component]
                    if axis == 1
                    else (-y, x, Fraction(0))[component]
                )
                rotation_projection += rotation_vector_component * residual[global_dof]
                rotation_norm_squared += rotation_vector_component**2
            identity_holds = moment_defect[axis] == -rotation_projection
            squared_bound_holds = rotation_projection**2 <= rotation_norm_squared * free_residual_norm_squared
            moment_identity.append(identity_holds)
            moment_cauchy_bound.append(squared_bound_holds)
            if not identity_holds or not squared_bound_holds:
                raise AssertionError("the exact moment balance identity or residual Cauchy bound failed")
        archived_reaction_key = (
            "matrix_free_support_reaction_N" if route_name == "matrix_free" else "direct_support_reaction_N"
        )
        archived_moment_key = (
            "matrix_free_support_moment_Nm" if route_name == "matrix_free" else "direct_support_moment_Nm"
        )
        archived_reaction = historical[archived_reaction_key]
        archived_moment = historical[archived_moment_key]
        reaction_records[route_name] = {
            "support_reaction_N_exact_fraction": [str(value) for value in support_force],
            "external_force_N_exact_fraction": [str(value) for value in external_force],
            "force_balance_defect_N_exact_fraction": [str(value) for value in force_defect],
            "support_moment_Nm_exact_fraction": [str(value) for value in support_moment],
            "external_moment_Nm_exact_fraction": [str(value) for value in external_moment],
            "moment_balance_defect_Nm_exact_fraction": [str(value) for value in moment_defect],
            "force_identity_from_free_residual": force_identity,
            "force_cauchy_bound_from_free_residual": force_cauchy_bound,
            "moment_identity_from_free_residual": moment_identity,
            "moment_cauchy_bound_from_free_residual": moment_cauchy_bound,
            "archived_support_reaction_N": archived_reaction,
            "recomputed_minus_archived_support_reaction_N_exact_fraction": [
                str(support_force[axis] - _fraction(float(archived_reaction[axis]))) for axis in range(3)
            ],
            "archived_support_moment_Nm": archived_moment,
            "recomputed_minus_archived_support_moment_Nm_exact_fraction": [
                str(support_moment[axis] - _fraction(float(archived_moment[axis]))) for axis in range(3)
            ],
        }

    free_exact_matrix = [[exact_global[int(row)][int(column)] for column in free] for row in free]
    norm_rhs = _norm2([exact_load[int(index)] for index in free])
    residual_mf_norm = _norm2(residual_mf_free)
    residual_direct_norm = _norm2(residual_direct_free)
    exact_product_direct = [
        sum(
            (
                free_exact_matrix[row][column] * _fraction(archived_direct[int(free[column])])
                for column in range(free_count)
            ),
            Fraction(0),
        )
        for row in range(free_count)
    ]
    residual_mf_relative = residual_mf_norm / norm_rhs
    residual_direct_relative = residual_direct_norm / max(
        norm_rhs,
        _norm2(exact_product_direct),
        1.0,
    )

    terminal_nodes = [index for index, coordinate in enumerate(model.nodes) if float(coordinate[0]) == 4.0]
    terminal_mean = {}
    for route_name, displacement in (
        ("matrix_free", archived_mf),
        ("assembled_direct", archived_direct),
    ):
        terminal_mean[route_name] = sum(displacement[3 * node + 2] for node in terminal_nodes) / len(terminal_nodes)
    total_fz = float(sum(exact_load[2::3], Fraction(0)))
    work_conjugate = {
        name: float(
            sum(
                (exact_load[index] * _fraction(displacement[index]) for index in range(model.ndof)),
                Fraction(0),
            )
            / _fraction(total_fz)
        )
        for name, displacement in (
            ("matrix_free", archived_mf),
            ("assembled_direct", archived_direct),
        )
    }
    displacement_difference = [
        _fraction(archived_mf[int(index)]) - _fraction(archived_direct[int(index)]) for index in free
    ]
    solution_difference_relative_l2 = _norm2(displacement_difference) / _norm2(
        [_fraction(archived_mf[int(index)]) for index in free]
    )

    finite_values = _all_finite(
        batch_local,
        np.asarray(scalar_local),
        batch_global,
        scalar_global,
        matrix_free_columns,
        direct_free,
    )
    subnormal_values_present = any(
        value != 0.0 and abs(float(value)) < sys.float_info.min
        for array in (batch_local, np.asarray(scalar_local), matrix_free_columns, direct_free)
        for value in np.asarray(array).ravel()
    )

    omitted_element = max(
        range(len(scalar_local)),
        key=lambda index: float(np.linalg.norm(scalar_local[index], ord="fro")),
    )
    local_without_element = [local.copy() for index, local in enumerate(scalar_local) if index != omitted_element]
    dofs_without_element = [dofs for index, dofs in enumerate(dof_maps) if index != omitted_element]
    missing_contribution_error = _relative_frobenius_error_to_exact(
        _assemble_local_float_matrices(local_without_element, dofs_without_element, model.ndof),
        exact_global,
    )
    shifted_dofs = np.asarray(dof_maps, dtype=np.int64).copy()
    shifted_dofs[0, 0] = (shifted_dofs[0, 0] + 1) % model.ndof
    shifted_map_global = _assemble_local_float_matrices(list(scalar_local), shifted_dofs.tolist(), model.ndof)
    shifted_map_relative_error = _relative_frobenius_error_to_exact(shifted_map_global, exact_global)
    mirrored_copy = np.asarray(scalar_local, dtype=np.float64).copy()
    upper = np.triu(np.abs(mirrored_copy), k=1)
    mirror_element, mirror_row, mirror_column = np.unravel_index(int(np.argmax(upper)), upper.shape)
    mirrored_copy[mirror_element, mirror_row, mirror_column] += (
        max(1.0, abs(float(mirrored_copy[mirror_element, mirror_row, mirror_column]))) * 1.0e-3
    )
    mirrored_global = _assemble_local_float_matrices(list(mirrored_copy), dof_maps, model.ndof)
    mirrored_global_relative_error = _relative_frobenius_error_to_exact(mirrored_global, exact_global)
    wrong_symmetric = exact_free_float.copy()
    wrong_symmetric[0, 0] += abs(wrong_symmetric[0, 0])
    wrong_column = exact_free_float.copy()
    wrong_column[0, 0] += 4.0 * OPERATOR_COLUMN_RELATIVE_LIMIT * float(np.linalg.norm(exact_free_float, ord="fro"))
    zero_solution = [0.0 for _ in archived_mf]
    zero_solution_residual = _exact_residual(exact_global, zero_solution, exact_load)
    zero_solution_relative_residual = _norm2([zero_solution_residual[int(index)] for index in free]) / norm_rhs
    negative_controls = {
        "missing_element_contribution_rejected": missing_contribution_error > ASSEMBLED_MATRIX_RELATIVE_LIMIT,
        "shifted_dof_map_rejected": (
            not np.array_equal(shifted_dofs, np.asarray(dof_maps))
            and shifted_map_relative_error > ASSEMBLED_MATRIX_RELATIVE_LIMIT
        ),
        "mirrored_local_perturbation_rejected": (
            not np.array_equal(mirrored_copy, mirrored_copy.transpose(0, 2, 1))
            and mirrored_global_relative_error > ASSEMBLED_MATRIX_RELATIVE_LIMIT
        ),
        "symmetric_but_wrong_matrix_rejected": (
            _relative_frobenius_error_to_exact(wrong_symmetric, exact_free) > ASSEMBLED_MATRIX_RELATIVE_LIMIT
        ),
        "matrix_free_column_perturbation_rejected": (
            _relative_frobenius_error_to_exact(wrong_column, exact_free) > OPERATOR_COLUMN_RELATIVE_LIMIT
        ),
        "inconsistent_archived_residual_rejected": zero_solution_relative_residual > MATRIX_FREE_RESIDUAL_LIMIT,
        "nonfinite_result_rejected": not _all_finite(np.asarray([[math.nan]])),
    }

    result = {
        "schema": "qf-wp12-v2-r1-h1-operator-audit-v1",
        "case_id": CASE_ID,
        "nodeid": NODEID,
        "execution_state": "RESULT_EMITTED_DURING_NODE_EXECUTION",
        "interpretation": "A pytest result is not general FEM qualification or continuum validation.",
        "identities": {
            "science_commit": "00428adf38e9397340ac136f6f503a268eb671da",
            "science_tree": "df4ec667bf746b042c900fad1f86bf542e1a437b",
            "historical_u3_receipt_sha256": U3_RECEIPT_SHA256,
            "historical_u3_manifest_sha256": U3_MANIFEST_SHA256,
            "h1_fixture_sha256": H1_FIXTURE_SHA256,
            "u3_archive_fields_fixture_sha256": U3_ARCHIVE_FIELDS_SHA256,
        },
        "scope": {
            "elements": model.element_count,
            "nodes": model.node_count,
            "total_dofs": model.ndof,
            "free_dofs": free.tolist(),
            "fixed_dofs": fixed.tolist(),
            "units": model.units,
            "loads": "archived H1 four equal terminal-node Fz loads; no new solve",
            "new_linear_solve_performed": False,
        },
        "assembly_capture": {
            "chunk_size": CHUNK_SIZE,
            "chunk_count": assembly.diagnostics["chunk_count"],
            "csr_constructor_input_count": len(sparse_inputs),
            "element_dof_maps_global": dof_maps,
            "emitted_rows": emitted_rows.tolist(),
            "emitted_columns": emitted_columns.tolist(),
            "emitted_values_binary64_hex": [float(value).hex() for value in emitted_values],
            "batch_local_matrices_binary64_hex": [
                [[float(value).hex() for value in row] for row in element] for element in batch_local
            ],
            "batch_local_matrices_exactly_symmetric": batch_local_symmetric,
            "scalar_local_matrices_exactly_symmetric": scalar_local_symmetric,
            "scalar_local_matrices_binary64_hex": [
                [[float(value).hex() for value in row] for row in element] for element in scalar_local
            ],
            "global_scalar_matrix_binary64_hex": [[float(value).hex() for value in row] for row in scalar_global],
            "global_batch_matrix_binary64_hex": [[float(value).hex() for value in row] for row in batch_global],
            "sparse_duplicate_reduction_order": "not observed inside SciPy; bound is order-independent under the declared binary64 addition model",
        },
        "exact_reference": {
            "origin": "exact Fraction arithmetic over the H1 binary64 input coordinates, E and nu",
            "global_stiffness_fraction_strings": [[str(value) for value in row] for row in exact_global],
            "global_stiffness_exactly_symmetric": exact_global_symmetric,
            "scalar_global_relative_frobenius_error": scalar_relative_error,
            "batch_global_relative_frobenius_error": batch_relative_error,
            "scalar_global_acceptance_limit": ASSEMBLED_MATRIX_RELATIVE_LIMIT,
            "batch_global_acceptance_limit": ASSEMBLED_MATRIX_RELATIVE_LIMIT,
        },
        "roundoff_and_symmetry": {
            "unit_roundoff": "2^-53",
            "gamma_definition": "gamma_p = p*u/(1-p*u), p=m-1",
            "rounding_assumption": "IEEE binary64 round-to-nearest; runtime rounding mode is not independently read by this test",
            "subnormal_intermediates_present": subnormal_values_present,
            "all_values_finite": bool(finite_values),
            "scalar_accumulation_bound_passed": scalar_roundoff_ok,
            "batch_accumulation_bound_passed": batch_roundoff_ok,
            "scalar_max_error_to_bound_ratio": scalar_roundoff_ratio,
            "batch_max_error_to_bound_ratio": batch_roundoff_ratio,
            "scalar_accumulation_component_records": scalar_roundoff_records,
            "batch_accumulation_component_records": batch_roundoff_records,
            "scalar_global_symmetry_relative_frobenius_error": _matrix_symmetry_ratio(scalar_global),
            "batch_global_symmetry_relative_frobenius_error": _matrix_symmetry_ratio(batch_global),
            "scalar_componentwise_symmetry_bound_passed": scalar_symmetry_ok,
            "batch_componentwise_symmetry_bound_passed": batch_symmetry_ok,
            "scalar_max_symmetry_to_bound_ratio": scalar_symmetry_ratio,
            "batch_max_symmetry_to_bound_ratio": batch_symmetry_ratio,
            "scalar_nonzero_asymmetric_pairs": scalar_asymmetric_pairs,
            "batch_nonzero_asymmetric_pairs": batch_asymmetric_pairs,
            "scalar_componentwise_symmetry_records": scalar_symmetry_records,
            "batch_componentwise_symmetry_records": batch_symmetry_records,
            "h1_pair_14_22_contributors_batch": [
                element for element, dofs in enumerate(dof_maps) if 14 in dofs and 22 in dofs
            ],
            "h1_pair_14_22_element_contributions": pair_14_22_contributions,
        },
        "matrix_free_full_free_operator": {
            "canonical_basis_count": free_count,
            "matrix_free_columns_binary64_hex": [[float(value).hex() for value in row] for row in matrix_free_columns],
            "assembled_direct_columns_binary64_hex": [[float(value).hex() for value in row] for row in direct_free],
            "matrix_free_minus_assembled_difference_exact_fraction_strings": [
                [str(value) for value in row] for row in route_difference_exact
            ],
            "matrix_free_minus_assembled_difference_frobenius": route_difference_frobenius,
            "matrix_free_minus_assembled_difference_infinity": float(route_difference_infinity),
            "matrix_free_minus_assembled_max_absolute_entry": float(route_difference_maximum),
            "matrix_free_minus_assembled_relative_frobenius_to_exact": route_relative_difference,
            "matrix_free_minus_assembled_relative_infinity_to_exact": route_difference_relative_infinity,
            "matrix_free_minus_assembled_relative_maximum_to_exact": route_difference_relative_maximum,
            "matrix_free_relative_frobenius_error_to_exact": matrix_free_relative_error,
            "assembled_relative_frobenius_error_to_exact": direct_free_relative_error,
            "matrix_free_vs_direct_relative_frobenius_difference": route_relative_difference,
            "per_column_relative_errors_normalized_by_exact_matrix_frobenius": column_relative_errors,
            "componentwise_kernel_plus_scatter_bounds_passed": column_bound_ok,
            "componentwise_error_bound_records": column_component_records,
            "acceptance_limit_reused_from_wp12_u": OPERATOR_COLUMN_RELATIVE_LIMIT,
        },
        "archived_solution_recalculation": {
            "archived_solution_fields_used": True,
            "historical_u3_source_receipt_sha256": U3_RECEIPT_SHA256,
            "exact_matrix_free_residual_full_fraction_strings": [str(value) for value in residual_mf],
            "exact_direct_residual_full_fraction_strings": [str(value) for value in residual_direct],
            "matrix_free_relative_free_residual_to_rhs": residual_mf_relative,
            "direct_relative_free_residual_to_max_rhs_product_one": residual_direct_relative,
            "matrix_free_residual_limit_reused_from_u3": MATRIX_FREE_RESIDUAL_LIMIT,
            "direct_residual_limit_reused_from_u3": DIRECT_RESIDUAL_LIMIT,
            "reactions_and_balance": reaction_records,
            "energy_and_work_exact": energy_work,
            "mean_terminal_face_uz_m": terminal_mean,
            "work_conjugate_displacement_m": work_conjugate,
            "relative_l2_difference_between_archived_fields": solution_difference_relative_l2,
            "limits": "Same discrete H1 model only; identities do not validate continuum accuracy.",
        },
        "synthetic_negative_controls": negative_controls,
        "synthetic_negative_control_metrics": {
            "shifted_dof_map_relative_error_to_exact": shifted_map_relative_error,
            "mirrored_local_perturbation_relative_error_to_exact": mirrored_global_relative_error,
        },
        "criteria": {
            "all_finite": bool(finite_values),
            "no_subnormal_values_for_gamma_profile": not subnormal_values_present,
            "exact_reference_is_symmetric": exact_global_symmetric,
            "local_exact_symmetry_observed": {
                "scalar": scalar_local_symmetric,
                "batch": batch_local_symmetric,
                "acceptance_role": "diagnostic_only; componentwise global symmetry and exact-reference checks are the criteria",
            },
            "scalar_global_accuracy": scalar_relative_error <= ASSEMBLED_MATRIX_RELATIVE_LIMIT,
            "batch_global_accuracy": batch_relative_error <= ASSEMBLED_MATRIX_RELATIVE_LIMIT,
            "scalar_accumulation_error_bound": scalar_roundoff_ok,
            "batch_accumulation_error_bound": batch_roundoff_ok,
            "scalar_componentwise_symmetry_bound": scalar_symmetry_ok,
            "batch_componentwise_symmetry_bound": batch_symmetry_ok,
            "matrix_free_all_columns_against_exact": (
                matrix_free_relative_error <= OPERATOR_COLUMN_RELATIVE_LIMIT
                and max(column_relative_errors, default=0.0) <= OPERATOR_COLUMN_RELATIVE_LIMIT
            ),
            "direct_all_columns_against_exact": direct_free_relative_error <= OPERATOR_COLUMN_RELATIVE_LIMIT,
            "matrix_free_componentwise_error_bound": column_bound_ok,
            "matrix_free_vs_direct_all_columns": route_relative_difference <= OPERATOR_COLUMN_RELATIVE_LIMIT,
            "recalculated_archived_residuals": residual_mf_relative <= MATRIX_FREE_RESIDUAL_LIMIT
            and residual_direct_relative <= DIRECT_RESIDUAL_LIMIT,
            "archived_energy_identity": all(
                value["twice_energy_minus_work_J_exact_fraction"] == value["free_residual_work_J_exact_fraction"]
                for value in energy_work.values()
            ),
            "negative_controls_detected": all(negative_controls.values()),
            "rounding_mode_runtime_verified": False,
            "rounding_assumptions_verified": False,
            "rounding_assumption_reasons": [
                "runtime floating-point rounding mode is not independently read by this test",
                "internal intermediate operations are not fully observed or independently verified",
            ],
            "gamma_bound_evaluated": True,
            "gamma_bound_evaluation_scope": (
                "scalar and batch accumulation, scalar and batch componentwise symmetry, and matrix-free "
                + "componentwise bounds were computed; their booleans are diagnostics and do not establish "
                + "the unverified rounding assumptions"
            ),
            "gamma_bound_satisfied": bool(
                scalar_roundoff_ok
                and batch_roundoff_ok
                and scalar_symmetry_ok
                and batch_symmetry_ok
                and column_bound_ok
            ),
            "owner_decision_required": True,
            "test_self_authorizes_execution": False,
        },
        "rounding_assumptions_verified": False,
        "gamma_bound_evaluated": True,
        "gamma_bound_satisfied": bool(
            scalar_roundoff_ok and batch_roundoff_ok and scalar_symmetry_ok and batch_symmetry_ok and column_bound_ok
        ),
        "gamma_bound_semantics": (
            "evaluated means scalar and batch accumulation, scalar and batch componentwise symmetry, and "
            + "matrix-free componentwise bounds were computed; satisfied is diagnostic only unless rounding "
            + "assumptions are verified"
        ),
        "gamma_scientific_status": "INCONCLUSIVE",
        "pytest_execution_status": "FAIL",
        "overall_scientific_status": "INCONCLUSIVE",
        "assertion_records": [],
    }
    checks = [
        ("all_finite", finite_values),
        ("exact_reference_symmetric", exact_global_symmetric),
        ("scalar_global_accuracy", scalar_relative_error <= ASSEMBLED_MATRIX_RELATIVE_LIMIT),
        ("batch_global_accuracy", batch_relative_error <= ASSEMBLED_MATRIX_RELATIVE_LIMIT),
        ("matrix_free_relative_accuracy", matrix_free_relative_error <= OPERATOR_COLUMN_RELATIVE_LIMIT),
        ("direct_relative_accuracy", direct_free_relative_error <= OPERATOR_COLUMN_RELATIVE_LIMIT),
        ("matrix_free_per_column_accuracy", max(column_relative_errors, default=0.0) <= OPERATOR_COLUMN_RELATIVE_LIMIT),
        ("matrix_free_vs_direct_accuracy", route_relative_difference <= OPERATOR_COLUMN_RELATIVE_LIMIT),
        ("matrix_free_archived_residual", residual_mf_relative <= MATRIX_FREE_RESIDUAL_LIMIT),
        ("direct_archived_residual", residual_direct_relative <= DIRECT_RESIDUAL_LIMIT),
        (
            "archived_energy_identity",
            all(
                value["twice_energy_minus_work_J_exact_fraction"] == value["free_residual_work_J_exact_fraction"]
                for value in energy_work.values()
            ),
        ),
        ("synthetic_negative_controls", all(negative_controls.values())),
    ]
    result["assertion_records"] = [
        {"name": name, "status": "NOT_REACHED", "acceptance_role": "mandatory"} for name, _condition in checks
    ]
    gamma_checks = [
        ("no_subnormal_values_for_gamma_profile", not subnormal_values_present),
        ("scalar_and_batch_accumulation_bounds", scalar_roundoff_ok and batch_roundoff_ok),
        ("scalar_and_batch_componentwise_symmetry_bounds", scalar_symmetry_ok and batch_symmetry_ok),
        ("matrix_free_componentwise_error_bound", column_bound_ok),
    ]
    result["assertion_records"].extend(
        {
            "name": name,
            "status": "NOT_REACHED",
            "acceptance_role": "gamma_conditional",
            "reason": "rounding assumptions are not verified; diagnostic is not established as an acceptance criterion",
        }
        for name, _condition in gamma_checks
    )
    try:
        for record, (_name, condition) in zip(result["assertion_records"][: len(checks)], checks, strict=True):
            record["status"] = "PASS" if condition else "FAIL"
            assert condition, record["name"]
        if result["rounding_assumptions_verified"]:
            for record, (_name, condition) in zip(
                result["assertion_records"][len(checks) :], gamma_checks, strict=True
            ):
                record["status"] = "PASS" if condition else "FAIL"
                assert condition, record["name"]
    finally:
        mandatory_records = [
            record for record in result["assertion_records"] if record["acceptance_role"] == "mandatory"
        ]
        gamma_records = [
            record for record in result["assertion_records"] if record["acceptance_role"] == "gamma_conditional"
        ]
        failed = any(record["status"] == "FAIL" for record in mandatory_records)
        all_reached = all(record["status"] != "NOT_REACHED" for record in mandatory_records)
        gamma_reached = not result["rounding_assumptions_verified"] or all(
            record["status"] != "NOT_REACHED" for record in gamma_records
        )
        any_assertion_failed = any(record["status"] == "FAIL" for record in result["assertion_records"])
        result["pytest_execution_status"] = (
            "PASS" if all_reached and gamma_reached and not any_assertion_failed else "FAIL"
        )
        gamma_satisfied = result["gamma_bound_satisfied"]
        if result["rounding_assumptions_verified"]:
            result["gamma_scientific_status"] = "PASS" if gamma_satisfied else "FAIL"
        else:
            result["gamma_scientific_status"] = "INCONCLUSIVE"
        if failed:
            result["overall_scientific_status"] = "FAIL"
        else:
            result["overall_scientific_status"] = result["gamma_scientific_status"]
        _emit(result)
