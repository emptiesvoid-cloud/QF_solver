"""Small reproducible harmonic and modal-transient stress-recovery examples.

Run from the repository root after setting ``QF_SOURCE_SHA`` to the exact
40-character source commit SHA for the checkout. The example intentionally
uses one linear TET4 and stores modal coordinates rather than full stress
histories.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

from solveur.core.analyses.modal_basis import ModalBasis
from solveur.core.analyses.modal_newmark import ModalNewmarkTransientSolver
from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem
from solveur.core.analyses.reduced_harmonic import ReducedHarmonicResponseSolver
from solveur.core.model import FiniteElementModel
from solveur.post.dynamic_stress import recover_harmonic_stress, recover_modal_transient_stress


NODES = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.2, 1.1, 0.0], [0.25, 0.3, 1.4]]
MATERIALS = {"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}}
FIXED_DOFS = [{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (0, 2, 3)]


def _model(analysis: str) -> FiniteElementModel:
    common = {
        "modal_mode_count": 3,
        "modal_extraction_method": "dense",
        "modal_dense_limit": 64,
        "rayleigh_alpha": 0.02,
        "rayleigh_beta": 0.0001,
    }
    if analysis == "harmonic":
        settings: dict[str, Any] = {
            "type": "harmonic_response",
            "method": "modal_superposition",
            **common,
            "frequencies_hz": [5.0],
        }
        loads = [{"node": 1, "dof": "UX", "value": 1.0}]
    elif analysis == "transient":
        settings = {
            "type": "transient_dynamic",
            "method": "modal_newmark",
            **common,
            "time_step": 0.00005,
            "steps": 20,
            "newmark_beta": 0.25,
            "newmark_gamma": 0.5,
            "record_time_history": False,
            "store_modal_history": True,
            "initial_displacements": [{"node": 1, "dof": "UX", "value": 2.0e-6}],
            "initial_velocities": [{"node": 1, "dof": "UX", "value": 0.0}],
        }
        loads = []
    else:
        raise ValueError("analysis must be 'harmonic' or 'transient'.")
    return FiniteElementModel.from_raw(
        analysis=settings,
        nodes=NODES,
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
        materials=MATERIALS,
        fixed_dofs=FIXED_DOFS,
        loads=loads,
        units={"system": "SI", "length": "m", "time": "s", "stress": "Pa"},
    )


def _prepared_basis(model: FiniteElementModel, source_sha: str) -> tuple[PreparedDynamicSystem, ModalBasis]:
    prepared = PreparedDynamicSystem.prepare(model, source_sha=source_sha)
    basis = ModalBasis.from_prepared(
        prepared,
        mode_count=prepared.reduced_size,
        method="dense",
        dense_limit=64,
    )
    return prepared, basis


def harmonic_example(source_sha: str) -> dict[str, object]:
    model = _model("harmonic")
    prepared, basis = _prepared_basis(model, source_sha)
    result = ReducedHarmonicResponseSolver().solve(
        model,
        source_sha=source_sha,
        prepared=prepared,
        basis=basis,
    )
    return recover_harmonic_stress(
        model,
        result,
        prepared=prepared,
        basis=basis,
        selected_frequencies_hz=[5.0],
    )


def transient_example(source_sha: str) -> dict[str, object]:
    model = _model("transient")
    prepared, basis = _prepared_basis(model, source_sha)
    result = ModalNewmarkTransientSolver().solve(
        model,
        source_sha=source_sha,
        prepared=prepared,
        basis=basis,
    )
    middle = len(result.times) // 2
    selected_times = sorted({float(result.times[0]), float(result.times[middle]), float(result.times[-1])})
    return recover_modal_transient_stress(
        model,
        result,
        prepared=prepared,
        basis=basis,
        selected_times_s=selected_times,
    )


def main() -> None:
    source_sha = os.environ.get("QF_SOURCE_SHA", "").lower()
    if re.fullmatch(r"[0-9a-f]{40}", source_sha) is None:
        raise SystemExit("Set QF_SOURCE_SHA to the exact 40-character source commit SHA.")
    if len(sys.argv) != 2 or sys.argv[1] not in {"harmonic", "transient"}:
        raise SystemExit("Usage: python examples/wp_d02_dynamic_stress.py harmonic|transient")
    result = harmonic_example(source_sha) if sys.argv[1] == "harmonic" else transient_example(source_sha)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
