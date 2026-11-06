"""Bounded stress recovery for linear solid modal responses.

The recovery uses the existing solid-element strain-displacement operators and
the existing isotropic linear-elastic constitutive matrix.  It does not alter
or re-solve WP04-WP07 response equations.
"""

from __future__ import annotations

from copy import deepcopy
import math
from collections.abc import Sequence
from decimal import Decimal, localcontext
from typing import Any

import numpy as np

from solveur.core.analyses.modal_basis import ModalBasis
from solveur.core.analyses.modal_newmark import ModalNewmarkResult
from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem
from solveur.core.dofs import SOLID_DOFS, DofManager
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.core.results import ReducedHarmonicResult
from solveur.elements.solid.common import von_mises_3d
from solveur.elements.solid.hex20 import Hex20Element
from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.tet10 import Tet10Element
from solveur.elements.solid.tet4 import Tet4Element
from solveur.materials.factory import MaterialFactory
from solveur.materials.solid import SolidMaterial


DYNAMIC_STRESS_CONTRACT = "qf-dynamic-solid-stress/v1"
STRESS_CONVENTION = "GLOBAL_SMALL_STRAIN_CAUCHY_VOIGT_XX_YY_ZZ_XY_YZ_ZX"
STRESS_COMPONENT_ORDER = ("XX", "YY", "ZZ", "XY", "YZ", "ZX")
HARMONIC_PHASE_CONVENTION = "u(t) = Re[U(omega) exp(+i*omega*t)]"
SUPPORTED_SOLID_TYPES = frozenset({"TET4", "TET10", "HEX8", "HEX20"})

_VON_MISES_METRIC = np.asarray(
    [
        [1.0, -0.5, -0.5, 0.0, 0.0, 0.0],
        [-0.5, 1.0, -0.5, 0.0, 0.0, 0.0],
        [-0.5, -0.5, 1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 3.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 3.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, 0.0, 3.0],
    ],
    dtype=np.float64,
)


def recover_solid_stress_field(
    model: FiniteElementModel,
    displacement: np.ndarray | Sequence[float] | Sequence[complex],
    *,
    stress_convention: str = STRESS_CONVENTION,
) -> dict[str, Any]:
    """Recover a full-order displacement field at supported solid integration points.

    A real vector produces signed real stress tensors and conventional von
    Mises stress.  A complex vector is interpreted as a harmonic amplitude;
    its real and imaginary tensor components are kept separate and its scalar
    equivalent is the exact maximum instantaneous von Mises value over phase.
    """
    _validate_stress_convention(stress_convention)
    dofs, materials = _recovery_inputs(model)
    values, is_complex = _displacement_vector(displacement, dofs.ndof)
    elements = _recover_elements(model, dofs, materials, values, is_complex=is_complex)
    return {
        "schema": DYNAMIC_STRESS_CONTRACT,
        "status": "COMPLETED_POSTPROCESSING",
        "analysis": "full_order_displacement_field",
        "stress_convention": STRESS_CONVENTION,
        "stress_component_order": list(STRESS_COMPONENT_ORDER),
        "shear_components": "tensor shear stress; the input strain operator uses engineering shear strain",
        "coordinate_frame": "GLOBAL_CARTESIAN",
        "field_kind": "COMPLEX_HARMONIC_AMPLITUDE" if is_complex else "REAL_DISPLACEMENT_FIELD",
        "phase_convention": HARMONIC_PHASE_CONVENTION if is_complex else None,
        "units": _units_payload(model),
        "element_coverage": _model_element_coverage(model),
        "elements": elements,
        "qualification_decision": "NOT_ASSESSED",
        "maturity": "EXPERIMENTAL",
    }


def recover_harmonic_stress(
    model: FiniteElementModel,
    result: ReducedHarmonicResult,
    *,
    prepared: PreparedDynamicSystem,
    basis: ModalBasis,
    selected_frequencies_hz: Sequence[float],
    stress_convention: str = STRESS_CONVENTION,
) -> dict[str, Any]:
    """Recover stress amplitudes at explicitly selected WP05 frequencies."""
    dofs, materials = _validate_dynamic_context(
        model,
        result,
        prepared=prepared,
        basis=basis,
        analysis="harmonic_response",
        method="modal_superposition",
        stress_convention=stress_convention,
    )
    signature = _canonical_dof_signature(dofs)
    if result.dof_signature != signature or result.full_dof_count != dofs.ndof:
        raise InputValidationError(
            "Harmonic stress recovery requires a complete displacement field on the model's full DOF map; probe-only results are unsupported."
        )
    if result.solver.get("phase_convention") != HARMONIC_PHASE_CONVENTION:
        raise InputValidationError(
            "Harmonic response phase convention is missing or incompatible with stress recovery."
        )
    frequencies = _select_exact_values(
        selected_frequencies_hz,
        result.frequencies_hz,
        "selected frequency",
    )
    output_rows = []
    for frequency in frequencies:
        index = next(i for i, value in enumerate(result.frequencies_hz) if float(value) == frequency)
        response, is_complex = _displacement_vector(result.responses[index], dofs.ndof)
        if not is_complex:
            raise InputValidationError("Harmonic stress recovery requires complex displacement amplitudes.")
        output_rows.append(
            {
                "frequency_hz": frequency,
                "omega_rad_s": float(2.0 * math.pi * frequency),
                "response_frame": _displacement_frame(result.solver),
                "elements": _recover_elements(model, dofs, materials, response, is_complex=True),
            }
        )
    return _dynamic_envelope(
        model,
        result,
        basis,
        analysis="harmonic_response",
        response_frame=_displacement_frame(result.solver),
        records=output_rows,
        selection_name="frequency_responses",
        stress_convention=stress_convention,
        phase_convention=HARMONIC_PHASE_CONVENTION,
    )


def recover_modal_transient_stress(
    model: FiniteElementModel,
    result: ModalNewmarkResult,
    *,
    prepared: PreparedDynamicSystem,
    basis: ModalBasis,
    selected_times_s: Sequence[float],
    stress_convention: str = STRESS_CONVENTION,
) -> dict[str, Any]:
    """Recover transient stress at selected stored WP06 modal states.

    The caller must have run WP06 with ``store_modal_history=true`` and retain
    the exact ``PreparedDynamicSystem`` and ``ModalBasis`` used by that run.
    Selection is by stored time; interpolation is not performed.
    """
    dofs, materials = _validate_dynamic_context(
        model,
        result,
        prepared=prepared,
        basis=basis,
        analysis="transient_dynamic",
        method="modal_newmark",
        stress_convention=stress_convention,
    )
    if (
        not result.modal_history
        or result.result_availability.get("modal_state_history", {}).get("status") != "AVAILABLE"
    ):
        raise InputValidationError(
            "Transient stress recovery requires retained modal_history; run WP06 with store_modal_history=true."
        )
    available_times = [float(row.get("time_s", float("nan"))) for row in result.modal_history]
    selected_times = _select_exact_values(selected_times_s, available_times, "selected time")
    output_rows = []
    for time_s in selected_times:
        row = next(item for item in result.modal_history if float(item["time_s"]) == time_s)
        coordinates = np.asarray(row.get("q"), dtype=np.float64)
        if coordinates.shape != (basis.mode_count,) or not np.all(np.isfinite(coordinates)):
            raise InputValidationError("Stored transient modal coordinates are incomplete or non-finite.")
        try:
            displacement = prepared.expand_state(basis.modes @ coordinates)
        except (TypeError, ValueError, FloatingPointError) as exc:
            raise InputValidationError("Could not reconstruct the selected transient displacement field.") from exc
        values, is_complex = _displacement_vector(displacement, dofs.ndof)
        if is_complex:
            raise InputValidationError("Modal Newmark transient displacement must be real-valued.")
        output_rows.append(
            {
                "time_s": time_s,
                "step": int(row.get("step", -1)),
                "response_frame": _displacement_frame(result.solver),
                "elements": _recover_elements(model, dofs, materials, values, is_complex=False),
            }
        )
    return _dynamic_envelope(
        model,
        result,
        basis,
        analysis="transient_dynamic",
        response_frame=_displacement_frame(result.solver),
        records=output_rows,
        selection_name="time_responses",
        stress_convention=stress_convention,
        phase_convention=None,
    )


def _validate_dynamic_context(
    model: FiniteElementModel,
    result: ReducedHarmonicResult | ModalNewmarkResult,
    *,
    prepared: PreparedDynamicSystem,
    basis: ModalBasis,
    analysis: str,
    method: str,
    stress_convention: str,
) -> tuple[DofManager, dict[str, SolidMaterial]]:
    _validate_stress_convention(stress_convention)
    dofs, materials = _recovery_inputs(model)
    expected_signature = _canonical_dof_signature(dofs)
    if not isinstance(prepared, PreparedDynamicSystem) or not isinstance(basis, ModalBasis):
        raise InputValidationError(
            "Dynamic stress recovery requires the exact prepared system and modal basis objects."
        )
    if not isinstance(result, (ReducedHarmonicResult, ModalNewmarkResult)):
        raise InputValidationError("Dynamic stress recovery received an unsupported result type.")
    if (
        result.analysis != analysis
        or result.method != method
        or model.analysis.type != analysis
        or model.analysis.method != method
    ):
        raise InputValidationError(
            f"Dynamic stress recovery requires analysis={analysis!r}, method={method!r} for both model and result."
        )
    if result.numerical_status != "PASS":
        raise InputValidationError("Dynamic stress recovery requires a numerically successful response result.")
    prepared.require_compatible(model)
    basis.assert_compatible(prepared)
    if expected_signature != prepared.dof_signature:
        raise InputValidationError("Prepared system DOFs do not match the model's complete response DOF map.")
    result_signature = (
        result.dof_signature if isinstance(result, ReducedHarmonicResult) else _canonical_dof_signature(result.dofs)
    )
    if result_signature != expected_signature:
        raise InputValidationError("Response result does not contain the complete model displacement field.")
    provenance = result.provenance
    expected_provenance = {
        "source_sha": prepared.source_sha,
        "physical_identity": prepared.physical_identity,
        "operator_identity": prepared.operator_identity,
        "basis_identity": basis.basis_identity,
    }
    if any(provenance.get(key) != value for key, value in expected_provenance.items()):
        raise InputValidationError("Response provenance does not match the supplied model, operators and modal basis.")
    if result.node_count != model.node_count or result.element_count != len(model.elements):
        raise InputValidationError("Response result mesh counts do not match the supplied source model.")
    return dofs, materials


def _recovery_inputs(model: FiniteElementModel) -> tuple[DofManager, dict[str, SolidMaterial]]:
    if not isinstance(model, FiniteElementModel):
        raise InputValidationError("Dynamic stress recovery requires a FiniteElementModel.")
    if model.analysis.type not in {"linear_static", "modal", "transient_dynamic", "harmonic_response"}:
        raise InputValidationError("Stress recovery is limited to linear static and linear dynamic analysis routes.")
    if model.contacts:
        raise InputValidationError("Contact configurations are outside bounded dynamic stress recovery.")
    if not model.elements:
        raise InputValidationError("Stress recovery requires at least one supported solid element.")
    unsupported = sorted({str(element.type).upper() for element in model.elements} - SUPPORTED_SOLID_TYPES)
    if unsupported:
        raise InputValidationError(
            "Stress recovery supports only TET4, TET10, HEX8 and HEX20 solid elements; "
            f"unsupported element families: {unsupported}."
        )
    families = {str(element.type).upper() for element in model.elements}
    if len(families) != 1:
        raise InputValidationError("Mixed solid-family stress recovery is not included in the bounded WP-D02 scope.")
    dofs = model.dof_manager()
    materials: dict[str, SolidMaterial] = {}
    for definition in model.elements:
        if definition.material in materials:
            continue
        raw = model.materials.get(definition.material)
        if not isinstance(raw, dict) or str(raw.get("type", "")).lower() != "isotropic_3d":
            raise InputValidationError(
                f"Stress recovery requires linear isotropic_3d material; material {definition.material!r} is unsupported."
            )
        try:
            material = MaterialFactory.create(raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise InputValidationError(f"Could not construct supported material {definition.material!r}.") from exc
        if type(material) is not SolidMaterial:
            raise InputValidationError(
                f"Stress recovery requires linear isotropic_3d material; material {definition.material!r} is unsupported."
            )
        materials[definition.material] = material
    return dofs, materials


def _recover_elements(
    model: FiniteElementModel,
    dofs: DofManager,
    materials: dict[str, SolidMaterial],
    displacement: np.ndarray,
    *,
    is_complex: bool,
) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    for element_index, definition in enumerate(model.elements):
        local_indices: list[int] = []
        for node in definition.nodes:
            try:
                local_indices.extend(dofs.node_indices(node, SOLID_DOFS))
            except ValueError as exc:
                raise InputValidationError(
                    f"Element {element_index} does not have a complete UX/UY/UZ displacement field."
                ) from exc
        local_displacement = displacement[np.asarray(local_indices, dtype=np.int64)]
        coords = np.asarray(model.nodes[list(definition.nodes)], dtype=np.float64)
        material = materials[definition.material]
        expected_local_size = 3 * coords.shape[0]
        if local_displacement.shape != (expected_local_size,):
            raise InputValidationError(
                f"Element {element_index} displacement vector must have shape ({expected_local_size},)."
            )
        if material.elasticity_matrix.shape != (6, 6):
            raise InputValidationError(f"Element {element_index} constitutive matrix must have shape (6, 6).")
        integration_points = []
        for point in _element_points(definition.type.upper(), coords):
            # Remove the element's rigid translation before applying B.  The
            # partition-of-unity identity makes this algebraically equivalent
            # to B @ u, while avoiding cancellation of large constant terms
            # when the expected strain is zero.
            nodal_displacement = local_displacement.reshape((-1, 3))
            relative_displacement = nodal_displacement - nodal_displacement[0]
            b_matrix = np.asarray(point["b_matrix"])
            if b_matrix.shape != (6, expected_local_size):
                raise InputValidationError(
                    f"Element {element_index} strain-displacement matrix must have shape (6, {expected_local_size})."
                )
            relative_vector = relative_displacement.reshape(-1)
            strain = b_matrix @ relative_vector
            elasticity = material.elasticity_matrix
            stress = elasticity @ strain
            if _matvec_roundoff_limited(b_matrix, relative_vector, strain) or _matvec_roundoff_limited(
                elasticity, strain, stress
            ):
                # A nearly cancelled strain or constitutive component can be
                # smaller than the rounding bound of the binary64 dot product.
                # Rebuild the entire B·u and D·strain chain from the exact
                # stored binary64 operands at higher precision; do not adjust
                # stress values or their tolerances.
                strain = _decimal_matvec(b_matrix, relative_vector)
                stress = _decimal_matvec(elasticity, strain)
            if not np.all(np.isfinite(strain)) or not np.all(np.isfinite(stress)):
                raise InputValidationError(f"Element {element_index} produced non-finite stress recovery values.")
            integration_points.append(_point_result(point, strain, stress, is_complex=is_complex))
        elements.append(
            {
                "element_index": element_index,
                "element_id_basis": "zero_based_model_element_order",
                "element_type": definition.type.upper(),
                "material_id": definition.material,
                "integration_points": integration_points,
            }
        )
    return elements


def _matvec_roundoff_limited(matrix: np.ndarray, vector: np.ndarray, result: np.ndarray) -> bool:
    """Detect matrix-vector rows whose cancellation exceeds binary64 resolution."""
    epsilon = np.finfo(np.float64).eps
    entries = np.asarray(vector)
    for row, value in zip(matrix, result):
        components = (
            ((entries.real, float(np.real(value))), (entries.imag, float(np.imag(value))))
            if np.iscomplexobj(entries) or np.iscomplexobj(result)
            else ((entries, float(value)),)
        )
        for component, component_value in components:
            products = np.asarray(row, dtype=np.float64) * np.asarray(component, dtype=np.float64)
            if not np.all(np.isfinite(products)) or not math.isfinite(component_value):
                continue
            try:
                absolute_sum = math.fsum(abs(float(product)) for product in products)
            except OverflowError:
                return True
            if absolute_sum == 0.0:
                continue
            rounding_bound = 8.0 * epsilon * len(row) * absolute_sum
            if abs(component_value) <= rounding_bound:
                return True
    return False


def _decimal_matvec(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
    """Evaluate a small matrix-vector product with high-precision accumulation."""
    values = np.asarray(matrix, dtype=np.float64)
    entries = np.asarray(vector)
    if np.iscomplexobj(entries):
        return _decimal_matvec(values, entries.real) + 1j * _decimal_matvec(values, entries.imag)
    entries = np.asarray(entries, dtype=np.float64)
    with localcontext() as context:
        context.prec = 80
        return np.asarray(
            [
                float(
                    sum(
                        (
                            Decimal.from_float(float(coefficient)) * Decimal.from_float(float(entry))
                            for coefficient, entry in zip(row, entries)
                        ),
                        Decimal(0),
                    )
                )
                for row in values
            ],
            dtype=np.float64,
        )


def _element_points(element_type: str, coords: np.ndarray) -> list[dict[str, Any]]:
    try:
        if element_type == "TET4":
            volume = Tet4Element.signed_volume(coords)
            if volume <= 1.0e-14:
                raise ValueError("Invalid or inverted TET4 volume.")
            return [
                {
                    "integration_point_index": 0,
                    "location": "centroid",
                    "natural_coordinates": [0.25, 0.25, 0.25, 0.25],
                    "coordinates": np.mean(coords, axis=0),
                    "weight": volume,
                    "b_matrix": Tet4Element.strain_displacement_matrix(coords),
                }
            ]
        if element_type == "TET10":
            output = []
            for index, (point, reference_weight) in enumerate(Tet10Element.stiffness_integration_rule(coords)):
                b_matrix, determinant = Tet10Element.b_matrix(coords, point)
                weight = float(reference_weight * determinant)
                if determinant <= 0.0 or not math.isfinite(weight) or weight <= 0.0:
                    raise ValueError("Invalid TET10 integration-point Jacobian or weight.")
                output.append(
                    {
                        "integration_point_index": index,
                        "location": "gauss",
                        "natural_coordinates": list(point),
                        "coordinates": Tet10Element.shape_functions(point) @ coords,
                        "weight": weight,
                        "b_matrix": b_matrix,
                    }
                )
            return output
        element_class = Hex8Element if element_type == "HEX8" else Hex20Element
        output = []
        for index, (point, reference_weight, b_matrix, determinant) in enumerate(element_class.integration_data(coords)):
            shape = element_class.shape_functions(point)
            if shape.shape != (coords.shape[0],) or b_matrix.shape != (6, 3 * coords.shape[0]):
                raise ValueError(
                    f"Invalid {element_type} integration data dimensions: shape={shape.shape}, "
                    f"B={b_matrix.shape}, nodes={coords.shape[0]}."
                )
            weight = float(reference_weight * determinant)
            if determinant <= 0.0 or not math.isfinite(weight) or weight <= 0.0:
                raise ValueError(f"Invalid {element_type} integration-point Jacobian or weight.")
            output.append(
                {
                    "integration_point_index": index,
                    "location": "gauss",
                    "natural_coordinates": list(point),
                    "coordinates": shape @ coords,
                    "weight": weight,
                    "b_matrix": b_matrix,
                }
            )
        return output
    except (IndexError, TypeError, ValueError, np.linalg.LinAlgError) as exc:
        raise InputValidationError(f"Could not evaluate {element_type} stress integration points: {exc}") from exc


def _point_result(
    point: dict[str, Any],
    strain: np.ndarray,
    stress: np.ndarray,
    *,
    is_complex: bool,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "integration_point_index": int(point["integration_point_index"]),
        "integration_point_id_basis": "zero_based_element_rule_order",
        "location": str(point["location"]),
        "natural_coordinates": [float(value) for value in point["natural_coordinates"]],
        "coordinates": [float(value) for value in point["coordinates"]],
        "weight": float(point["weight"]),
        "weight_measure": "physical_volume_in_model_length_units_cubed",
        "coordinate_frame": "GLOBAL_CARTESIAN",
        "strain_components": _component_payload(strain, is_complex=is_complex),
        "stress_components": _component_payload(stress, is_complex=is_complex),
    }
    if is_complex:
        base["stress_tensor"] = {
            "real": _voigt_tensor(stress.real).tolist(),
            "imag": _voigt_tensor(stress.imag).tolist(),
        }
        base["von_mises_phase_peak"] = _harmonic_von_mises_peak(stress)
        base["von_mises_convention"] = (
            "max over phase of VM(Re[Sigma exp(+i*phase)]); exact for the retained complex tensor amplitude"
        )
    else:
        real_stress = np.asarray(stress, dtype=np.float64)
        base["stress_tensor"] = _voigt_tensor(real_stress).tolist()
        base["von_mises"] = float(von_mises_3d(real_stress))
        base["von_mises_convention"] = "standard 3D von Mises stress of the signed real Cauchy tensor"
    return base


def _component_payload(values: np.ndarray, *, is_complex: bool) -> dict[str, Any]:
    if is_complex:
        return {
            "component_order": list(STRESS_COMPONENT_ORDER),
            "real": np.asarray(values.real, dtype=np.float64).tolist(),
            "imag": np.asarray(values.imag, dtype=np.float64).tolist(),
        }
    return {
        "component_order": list(STRESS_COMPONENT_ORDER),
        "values": np.asarray(values, dtype=np.float64).tolist(),
    }


def _voigt_tensor(values: np.ndarray) -> np.ndarray:
    xx, yy, zz, xy, yz, zx = values
    return np.asarray([[xx, xy, zx], [xy, yy, yz], [zx, yz, zz]])


def _harmonic_von_mises_peak(stress: np.ndarray) -> float:
    """Return max_theta VM(Re[stress exp(+i theta)]) for a complex amplitude."""
    values = np.asarray(stress, dtype=np.complex128)
    real = values.real
    imag = values.imag
    a = float(real @ (_VON_MISES_METRIC @ real))
    b = float(real @ (_VON_MISES_METRIC @ imag))
    c = float(imag @ (_VON_MISES_METRIC @ imag))
    maximum_squared = 0.5 * (a + c + math.sqrt(max(0.0, (a - c) ** 2 + 4.0 * b * b)))
    return math.sqrt(max(0.0, maximum_squared))


def _validate_stress_convention(value: str) -> None:
    if value != STRESS_CONVENTION:
        raise InputValidationError(
            f"Unsupported stress convention {value!r}; only {STRESS_CONVENTION!r} is implemented."
        )


def _displacement_vector(values: Any, expected_size: int) -> tuple[np.ndarray, bool]:
    try:
        raw = np.asarray(values)
        if raw.ndim != 1 or raw.size != expected_size or raw.dtype.kind not in "iufc":
            raise ValueError
        is_complex = np.iscomplexobj(raw)
        vector = np.asarray(raw, dtype=np.complex128 if is_complex else np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise InputValidationError("Displacement field must be a complete one-dimensional numeric DOF vector.") from exc
    if not np.all(np.isfinite(vector)):
        raise InputValidationError("Displacement field must contain only finite values.")
    return vector, is_complex


def _select_exact_values(requested: Sequence[float], available: Sequence[float], label: str) -> list[float]:
    if isinstance(requested, (str, bytes)):
        raise InputValidationError(f"At least one finite {label} must be selected explicitly.")
    try:
        requested_values = list(requested)
        available_values = [float(value) for value in available]
    except (TypeError, ValueError, OverflowError) as exc:
        raise InputValidationError(f"Selected {label} values must be finite numeric scalars.") from exc
    if not requested_values:
        raise InputValidationError(f"At least one {label} must be selected explicitly.")
    selected: list[float] = []
    for value in requested_values:
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.number)):
            raise InputValidationError(f"Selected {label} values must be finite numeric scalars.")
        number = float(value)
        if not math.isfinite(number) or number not in available_values:
            raise InputValidationError(f"Selected {label} {number!r} is not present in the response result.")
        if number in selected:
            raise InputValidationError(f"Selected {label} values must not contain duplicates.")
        selected.append(number)
    return selected


def _canonical_dof_signature(dofs: DofManager) -> tuple[tuple[int, tuple[str, ...]], ...]:
    return tuple(sorted((int(node), tuple(names)) for node, names in dofs.node_dofs.items()))


def _displacement_frame(solver: dict[str, Any]) -> str:
    return "RELATIVE_RESPONSE" if "uniform_base_acceleration" in solver else "STRUCTURAL_RESPONSE"


def _dynamic_envelope(
    model: FiniteElementModel,
    result: ReducedHarmonicResult | ModalNewmarkResult,
    basis: ModalBasis,
    *,
    analysis: str,
    response_frame: str,
    records: list[dict[str, Any]],
    selection_name: str,
    stress_convention: str,
    phase_convention: str | None,
) -> dict[str, Any]:
    return {
        "schema": DYNAMIC_STRESS_CONTRACT,
        "status": "COMPLETED_POSTPROCESSING",
        "analysis": analysis,
        "method": result.method,
        "stress_convention": stress_convention,
        "stress_component_order": list(STRESS_COMPONENT_ORDER),
        "shear_components": "tensor shear stress; the input strain operator uses engineering shear strain",
        "coordinate_frame": "GLOBAL_CARTESIAN",
        "response_frame": response_frame,
        "phase_convention": phase_convention,
        "units": _units_payload(model),
        "element_coverage": _model_element_coverage(model),
        "source_model": {
            "source_sha": result.provenance["source_sha"],
            "physical_identity": result.provenance["physical_identity"],
            "operator_identity": result.provenance["operator_identity"],
            "execution_key": result.execution_key,
        },
        "modal_basis": {
            "basis_identity": basis.basis_identity,
            "operator_identity": basis.operator_identity,
            "mode_count": basis.mode_count,
            "system_size": basis.system_size,
            "is_full_basis": basis.is_full_basis,
            "extraction": basis.extraction,
            "truncation": deepcopy(basis.diagnostics.get("truncation", {})),
        },
        "accuracy_statement": (
            "Recovered stress belongs to the supplied modal response. A truncated basis can omit local stress contributions; "
            "no stress error bound or full-order accuracy is inferred."
        ),
        "result_provenance": {
            "result_schema": (
                ReducedHarmonicResult.CONTRACT
                if isinstance(result, ReducedHarmonicResult)
                else ModalNewmarkResult.CONTRACT
            ),
            "numerical_status": result.numerical_status,
            "qualification_decision": "NOT_ASSESSED",
            "maturity": "EXPERIMENTAL",
        },
        "qualification_decision": "NOT_ASSESSED",
        "maturity": "EXPERIMENTAL",
        selection_name: records,
    }


def _units_payload(model: FiniteElementModel) -> dict[str, Any]:
    units = deepcopy(model.units)
    return {
        "model_units": units,
        "coordinate_and_displacement": units.get("length", "same as model coordinates; not explicitly declared"),
        "time": units.get("time", "s (WP06 time field convention)"),
        "harmonic_frequency": "Hz (WP05 result field convention)",
        "strain": "dimensionless",
        "stress": units.get("stress", "same unit as material Young's modulus; not explicitly declared"),
        "integration_point_weight": "coordinate unit cubed",
        "conversion_applied": False,
    }


def _model_element_coverage(model: FiniteElementModel) -> list[str]:
    return sorted({str(element.type).upper() for element in model.elements})
