"""Reproducible analytical benchmark for the BEAM2 element."""

from __future__ import annotations

import numpy as np

from solveur.benchmarks.support import BenchmarkContext, free_residual, run_status, upper_check
from solveur.benchmarks.types import BenchmarkRun
from solveur.core.model import FiniteElementModel


def run_beam2_cantilever(context: BenchmarkContext) -> BenchmarkRun:
    """Check static compliance and modal convergence of a slender cantilever."""
    length = 2.0
    young = 210.0e9
    poisson = 0.3
    shear = young / (2.0 * (1.0 + poisson))
    area = 0.01
    iy = 2.0e-6
    iz = 3.0e-6
    polar = 5.0e-6
    density = 7800.0
    shear_factor = 5.0 / 6.0
    line_load = 750.0
    static_reference = line_load * length**4 / (8.0 * young * iz)
    static_reference += line_load * length**2 / (2.0 * shear_factor * shear * area)
    modal_inertia = min(iy, iz)
    modal_reference = (1.875104068711961**2 / (2.0 * np.pi * length**2)) * np.sqrt(
        young * modal_inertia / (density * area)
    )
    rows: list[dict[str, float | int]] = []
    files: dict[str, str] = {}
    for element_count in (1, 2, 4, 8, 16):
        static_model = _cantilever_model(
            element_count,
            "linear_static",
            length=length,
            young=young,
            poisson=poisson,
            area=area,
            iy=iy,
            iz=iz,
            polar=polar,
            density=density,
            line_load=line_load,
        )
        static_result, static_files = context.solve_model(static_model, prefix=f"static_n{element_count}")
        modal_model = _cantilever_model(
            element_count,
            "modal",
            length=length,
            young=young,
            poisson=poisson,
            area=area,
            iy=iy,
            iz=iz,
            polar=polar,
            density=density,
            line_load=0.0,
        )
        modal_result, modal_files = context.solve_model(modal_model, prefix=f"modal_n{element_count}")
        tip = float(static_result.displacements[static_result.dofs.index(element_count, "UY")])
        frequency = float(modal_result.frequencies_hz[0])
        rows.append(
            {
                "element_count": element_count,
                "static_tip_displacement": tip,
                "static_reference": static_reference,
                "static_relative_error": abs((tip - static_reference) / static_reference),
                "first_frequency_hz": frequency,
                "euler_bernoulli_frequency_hz": modal_reference,
                "modal_relative_error": abs((frequency - modal_reference) / modal_reference),
                "modal_residual": float(modal_result.solver["relative_residuals"][0]),
                "free_relative_residual": free_residual(static_result),
            }
        )
        files.update(static_files)
        files.update(modal_files)
    criteria = context.descriptor.criteria
    modal_increment = abs(float(rows[-1]["first_frequency_hz"]) - float(rows[-2]["first_frequency_hz"]))
    modal_increment /= float(rows[-1]["first_frequency_hz"])
    checks = [
        upper_check(
            "beam2-static-compliance",
            max(float(row["static_relative_error"]) for row in rows),
            criteria["static_relative_error_max"],
        ),
        upper_check(
            "beam2-modal-reference",
            float(rows[-1]["modal_relative_error"]),
            criteria["modal_relative_error_max"],
        ),
        upper_check("beam2-modal-increment", modal_increment, criteria["modal_increment_max"]),
        upper_check(
            "beam2-modal-residual",
            max(float(row["modal_residual"]) for row in rows),
            criteria["modal_residual_max"],
        ),
        upper_check(
            "beam2-static-residual",
            max(float(row["free_relative_residual"]) for row in rows),
            criteria["free_residual_max"],
        ),
    ]
    return context.finalize(
        BenchmarkRun(
            context.descriptor,
            run_status(checks, expected_warning=True),
            {
                "convergence": rows,
                "static_reference": static_reference,
                "euler_bernoulli_frequency_hz": modal_reference,
                "final_modal_increment": modal_increment,
            },
            checks,
            files,
            "Experimental until an external same-model correlation and Owner review are complete.",
        )
    )


def _cantilever_model(
    element_count: int,
    analysis: str,
    *,
    length: float,
    young: float,
    poisson: float,
    area: float,
    iy: float,
    iz: float,
    polar: float,
    density: float,
    line_load: float,
) -> FiniteElementModel:
    nodes = [[length * index / element_count, 0.0, 0.0] for index in range(element_count + 1)]
    elements = [
        {"type": "BEAM2", "nodes": [index, index + 1], "material": "beam"}
        for index in range(element_count)
    ]
    distributed = [
        {"type": "line_load", "element": index, "value": [0.0, line_load, 0.0], "coordinate_system": "local"}
        for index in range(element_count)
        if line_load
    ]
    settings: str | dict[str, object] = analysis
    if analysis == "modal":
        settings = {"type": "modal", "parameters": {"modes": 1}}
    return FiniteElementModel.from_raw(
        nodes=nodes,
        elements=elements,
        materials={
            "beam": {
                "type": "beam_isotropic",
                "E": young,
                "nu": poisson,
                "A": area,
                "Iy": iy,
                "Iz": iz,
                "J": polar,
                "density": density,
                "reference_vector": [0.0, 1.0, 0.0],
            }
        },
        fixed_dofs=[{"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}],
        distributed_loads=distributed,
        analysis=settings,
        verification_profile="engineering",
    )
