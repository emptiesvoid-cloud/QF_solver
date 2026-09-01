"""Controlled WEDGE6 consistent-mass and modal evidence for WP10."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
import shutil
import subprocess
from typing import Any

import numpy as np

from solveur.core.model import FiniteElementModel
from solveur.core.router import AnalysisRouter
from solveur.core.errors import InfrastructureError
from solveur.elements.solid.wedge6 import Wedge6Element
from solveur.materials.factory import MaterialFactory
from solveur.verification.code_aster_tl_structural import (
    CODE_ASTER_IMAGE,
    run_code_aster,
)
from solveur.verification.v2 import (
    ExternalUnavailableError,
    ExecutionOutput,
    VnvRunner,
    load_cases,
    replay_case,
)


ROOT = Path(__file__).resolve().parents[3]
CATALOG = ROOT / "qualification" / "0_2_7" / "vnv_v2" / "wp10_cases.json"
CODE_ASTER_MODAL_DECK_DIR = ROOT / "qualification" / "0_2_7" / "external_oracles" / "wedge6" / "decks" / "code_aster"
CODE_ASTER_MODAL_COMM = CODE_ASTER_MODAL_DECK_DIR / "WP10-A-penta6-modal.comm"
CODE_ASTER_MODAL_MAIL = CODE_ASTER_MODAL_DECK_DIR / "WP10-A-penta6-modal.mail"
MATERIAL_DATA = {
    "steel": {
        "type": "isotropic_3d",
        "E": 210.0e9,
        "nu": 0.3,
        "density": 7800.0,
    }
}
BASE_LAYER = np.asarray(
    ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    dtype=float,
)
TOTAL_LENGTH = 3.0


def source_sha() -> str:
    """Return the exact QF revision used to produce the campaign."""

    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prism_chain(
    segments: int = 1,
    *,
    length: float = TOTAL_LENGTH,
    transform: np.ndarray | None = None,
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> tuple[np.ndarray, list[list[int]]]:
    """Build a conforming chain of affine WEDGE6 prisms."""

    if not isinstance(segments, int) or segments <= 0:
        raise ValueError("segments must be a positive integer.")
    layers = [BASE_LAYER.copy() for _ in range(segments + 1)]
    for index, layer in enumerate(layers):
        layer[:, 2] = length * index / segments
    nodes = np.vstack(layers)
    if transform is not None:
        matrix = np.asarray(transform, dtype=float)
        if matrix.shape != (3, 3):
            raise ValueError("WEDGE6 modal transform must have shape (3, 3).")
        nodes = nodes @ matrix.T
    nodes += np.asarray(translation, dtype=float)
    elements = [
        [3 * index, 3 * index + 1, 3 * index + 2,
         3 * (index + 1), 3 * (index + 1) + 1, 3 * (index + 1) + 2]
        for index in range(segments)
    ]
    return nodes, elements


def modal_model(
    segments: int = 1,
    *,
    transform: np.ndarray | None = None,
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    density: float = 7800.0,
    modes: int = 6,
) -> FiniteElementModel:
    """Return a fixed-bottom WEDGE6 modal model for a declared case."""

    nodes, elements = prism_chain(segments, transform=transform, translation=translation)
    material = {"steel": {**MATERIAL_DATA["steel"], "density": density}}
    fixed = [{"node": index, "dofs": ["UX", "UY", "UZ"]} for index in range(3)]
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "WEDGE6", "nodes": item, "material": "steel"} for item in elements],
        materials=material,
        fixed_dofs=fixed,
        analysis={"type": "modal", "method": "eigh", "modes": modes},
        units={"system": "SI"},
        verification_profile="engineering",
    )


def _solve(model: FiniteElementModel) -> Any:
    return AnalysisRouter().solve(model)


def _element(model: FiniteElementModel, index: int = 0) -> Wedge6Element:
    definition = model.elements[index]
    material = MaterialFactory.create(model.materials[definition.material])
    return Wedge6Element(material)


def mass_metrics() -> dict[str, Any]:
    """Evaluate fixed mass properties before the modal cases are run."""

    model = modal_model()
    element = _element(model)
    coords = model.nodes[list(model.elements[0].nodes)]
    mass = element.mass(coords)
    reference = element.reference_mass(coords)
    scale = max(float(np.linalg.norm(mass)), 1.0)
    eigens = np.linalg.eigvalsh(mass)
    density = float(model.materials["steel"]["density"])
    expected_mass = density * element.volume(coords)
    direction_masses = []
    for component in range(3):
        translation = np.zeros(18)
        translation[component::3] = 1.0
        direction_masses.append(float(translation @ mass @ translation))
    doubled = modal_model(density=2.0 * density)
    doubled_mass = _element(doubled).mass(doubled.nodes[list(doubled.elements[0].nodes)])
    scaled = modal_model()
    scaled.nodes = scaled.nodes * 2.0
    scaled_mass = _element(scaled).mass(scaled.nodes[list(scaled.elements[0].nodes)])
    skew = np.asarray(((1.0, 0.12, 0.0), (0.0, 1.0, 0.08), (0.0, 0.0, 1.0)))
    distorted = modal_model(transform=skew, translation=(4.0, -2.0, 1.0))
    distorted_mass = _element(distorted).mass(distorted.nodes[list(distorted.elements[0].nodes)])
    return {
        "mass_shape": list(mass.shape),
        "symmetry_error": float(np.linalg.norm(mass - mass.T) / scale),
        "minimum_eigenvalue": float(np.min(eigens)),
        "positive_definite": bool(np.all(eigens > 0.0)),
        "expected_total_mass": expected_mass,
        "direction_masses": direction_masses,
        "mass_conservation_error": float(max(abs(value - expected_mass) for value in direction_masses)),
        "reference_mass_relative_difference": float(np.linalg.norm(mass - reference) / scale),
        "density_scaling_error": float(np.linalg.norm(doubled_mass - 2.0 * mass) / scale),
        "density_scaling_pass": bool(np.allclose(doubled_mass, 2.0 * mass, rtol=1.0e-12, atol=1.0e-12)),
        "geometry_scaling_ratio": float(np.sum(scaled_mass) / np.sum(mass)),
        "geometry_scaling_pass": bool(np.isclose(np.sum(scaled_mass) / np.sum(mass), 8.0, rtol=1.0e-12)),
        "distorted_positive": bool(np.all(np.linalg.eigvalsh(distorted_mass) > 0.0)),
        "distorted_total_mass": float(np.sum(distorted_mass[0::3, 0::3])),
    }


def modal_metrics(segments: int = 1, *, transform: np.ndarray | None = None) -> dict[str, Any]:
    """Solve one common-route model and return stable modal observables."""

    result = _solve(modal_model(segments, transform=transform))
    frequencies = np.asarray(result.frequencies_hz, dtype=float)
    modes = np.asarray(result.modes, dtype=float)
    replay = _solve(modal_model(segments, transform=transform))
    return {
        "status": result.status,
        "frequency_count": int(frequencies.size),
        "frequencies_hz": frequencies.tolist(),
        "finite_frequencies": bool(np.isfinite(frequencies).all()),
        "positive_frequencies": bool(np.all(frequencies > 0.0)),
        "finite_modes": bool(np.isfinite(modes).all()),
        "mode_norms_finite": bool(np.isfinite(np.linalg.norm(modes, axis=0)).all()),
        "max_relative_residual": float(result.solver["max_relative_residual"]),
        "mass_orthogonality_error": float(result.solver["mass_orthogonality_error"]),
        "stiffness_diagonal_error": float(result.solver["stiffness_diagonal_error"]),
        "assembly_route": result.solver["assembly"]["stiffness"].get("paired_assembly", False),
        "deterministic_frequencies": bool(np.array_equal(frequencies, np.asarray(replay.frequencies_hz))),
        "deterministic_modes": bool(np.array_equal(modes, np.asarray(replay.modes))),
    }


def refinement_metrics() -> dict[str, Any]:
    rows = []
    for segments in (1, 2, 3, 4):
        metrics = modal_metrics(segments)
        rows.append({"segments": segments, "first_frequency_hz": metrics["frequencies_hz"][0]})
    frequencies = np.asarray([row["first_frequency_hz"] for row in rows], dtype=float)
    return {
        "levels": rows,
        "finite": bool(np.isfinite(frequencies).all()),
        "final_relative_change": float(abs(frequencies[-1] - frequencies[-2]) / frequencies[-1]),
        "trend_reported_without_monotonicity_claim": True,
    }


def _aster_mesh(nodes: np.ndarray, elements: list[list[int]]) -> str:
    lines = ["TITRE", "QF_solver WEDGE6 modal Code_Aster correlation", "FINSF", "COOR_3D"]
    lines.extend(
        f"N{index + 1} {node[0]:.16g} {node[1]:.16g} {node[2]:.16g}"
        for index, node in enumerate(nodes)
    )
    lines.extend(["FINSF", "PENTA6"])
    lines.extend(
        f"E{index + 1} " + " ".join(f"N{node + 1}" for node in element)
        for index, element in enumerate(elements)
    )
    lines.extend(["FINSF", "GROUP_MA", "SOLID"])
    lines.extend(f"E{index + 1}" for index in range(len(elements)))
    lines.extend(["FINSF", "GROUP_NO", "FIXED", "N1", "N2", "N3", "FINSF", "FIN"])
    return "\n".join(lines) + "\n"


def _aster_comm() -> str:
    return '''# coding=utf-8
import json
from code_aster.Commands import *

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))
mesh = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=20)
model = AFFE_MODELE(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", PHENOMENE="MECANIQUE", MODELISATION="3D"))
material = DEFI_MATERIAU(ELAS=_F(E=210.0e9, NU=0.3, RHO=7800.0))
field = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA="SOLID", MATER=material))
boundary = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_NO="FIXED", DX=0.0, DY=0.0, DZ=0.0))
rigidity_e = CALC_MATR_ELEM(OPTION="RIGI_MECA", MODELE=model, CHAM_MATER=field, CHARGE=boundary)
mass_e = CALC_MATR_ELEM(OPTION="MASS_MECA", MODELE=model, CHAM_MATER=field, CHARGE=boundary)
numbering = NUME_DDL(MATR_RIGI=rigidity_e)
rigidity = ASSE_MATRICE(MATR_ELEM=rigidity_e, NUME_DDL=numbering)
mass = ASSE_MATRICE(MATR_ELEM=mass_e, NUME_DDL=numbering)
modes = CALC_MODES(
    OPTION="PLUS_PETITE", MATR_RIGI=rigidity, MATR_MASS=mass,
    CALC_FREQ=_F(NMAX_FREQ=6), VERI_MODE=_F(STOP_ERREUR="OUI", SEUIL=1.0e-7),
)
with open("/work/code_aster_modal_raw.json", "w", encoding="utf-8") as stream:
    json.dump({"frequencies_hz": [float(value) for value in modes.getAccessParameters()["FREQ"]]}, stream, indent=2)
FIN()
'''


def run_code_aster_modal(output_dir: Path) -> dict[str, Any]:
    """Run the comparable one-prism PENTA6 oracle in the pinned headless image."""

    external_dir = output_dir / "code_aster_modal"
    external_dir.mkdir(parents=True, exist_ok=True)
    if not CODE_ASTER_MODAL_COMM.is_file() or not CODE_ASTER_MODAL_MAIL.is_file():
        raise ExternalUnavailableError("The committed Code_Aster WP10 modal deck is missing.")
    shutil.copyfile(CODE_ASTER_MODAL_MAIL, external_dir / "wedge6_modal.mail")
    shutil.copyfile(CODE_ASTER_MODAL_COMM, external_dir / "wedge6_modal.comm")
    try:
        run_code_aster(external_dir, "wedge6_modal")
    except InfrastructureError as exc:
        raise ExternalUnavailableError(str(exc)) from exc
    raw_path = external_dir / "code_aster_modal_raw.json"
    if not raw_path.is_file():
        raise ExternalUnavailableError("Code_Aster completed without a modal result artifact.")
    external = json.loads(raw_path.read_text(encoding="utf-8"))
    qf = modal_metrics()
    qf_frequencies = np.asarray(qf["frequencies_hz"], dtype=float)
    external_frequencies = np.asarray(external["frequencies_hz"], dtype=float)
    count = min(qf_frequencies.size, external_frequencies.size)
    differences = np.abs(qf_frequencies[:count] - external_frequencies[:count]) / np.maximum(
        np.abs(external_frequencies[:count]), 1.0e-12
    )
    tolerance = 1.0e-2
    return {
        "state": "PASS_EXTERNAL_CORRELATION_BOUNDED" if np.all(differences <= tolerance) else "FAIL_EXTERNAL",
        "solver": "Code_Aster 18.1.0 / PENTA6",
        "image": CODE_ASTER_IMAGE,
        "qf_frequencies_hz": qf_frequencies[:count].tolist(),
        "code_aster_frequencies_hz": external_frequencies[:count].tolist(),
        "relative_errors": differences.tolist(),
        "tolerance": tolerance,
        "tolerance_source": "WP10 predeclared same-mesh modal candidate; OWNER_REVIEW_REQUIRED",
        "formulation_compatible": True,
        "primary_observable": "frequency_hz",
        "mode_shape_comparison": "NOT_RUN; PENTA6/QF displacement mapping not required for this frequency-only bounded check",
        "deck": "qualification/0_2_7/external_oracles/wedge6/decks/code_aster/WP10-A-penta6-modal",
        "deck_digests": {
            "comm": _file_sha256(CODE_ASTER_MODAL_COMM),
            "mail": _file_sha256(CODE_ASTER_MODAL_MAIL),
        },
    }


def _case_observables(case_id: str) -> dict[str, Any]:
    if case_id == "WP10-MASS-SYMMETRY":
        metrics = mass_metrics()
        return {"pass": metrics["symmetry_error"] <= 1.0e-14, **metrics}
    if case_id == "WP10-MASS-POSITIVITY":
        metrics = mass_metrics()
        return {"pass": metrics["positive_definite"], **metrics}
    if case_id == "WP10-MASS-CONSERVATION":
        metrics = mass_metrics()
        return {"pass": metrics["mass_conservation_error"] <= 1.0e-10, **metrics}
    if case_id == "WP10-MASS-DENSITY-SCALING":
        metrics = mass_metrics()
        return {"pass": metrics["density_scaling_pass"], **metrics}
    if case_id == "WP10-MASS-GEOMETRY-SCALING":
        metrics = mass_metrics()
        return {"pass": metrics["geometry_scaling_pass"], **metrics}
    if case_id == "WP10-MASS-DISTORTED":
        metrics = mass_metrics()
        return {"pass": metrics["distorted_positive"], **metrics}
    if case_id in {"WP10-MODAL-SINGLE", "WP10-MODAL-AXIAL", "WP10-MODAL-BENDING", "WP10-MODAL-SHEAR"}:
        metrics = modal_metrics(1 if case_id != "WP10-MODAL-BENDING" else 3)
        return {"pass": metrics["status"] == "PASS" and metrics["positive_frequencies"], **metrics}
    if case_id == "WP10-MODAL-MULTI":
        metrics = modal_metrics(3)
        return {"pass": metrics["status"] == "PASS", **metrics}
    if case_id == "WP10-MODAL-DISTORTED":
        transform = np.asarray(((1.0, 0.12, 0.0), (0.0, 1.0, 0.08), (0.0, 0.0, 1.0)))
        metrics = modal_metrics(3, transform=transform)
        return {"pass": metrics["status"] == "PASS", **metrics}
    if case_id == "WP10-MODAL-REFINEMENT":
        return refinement_metrics()
    if case_id == "WP10-MODAL-REPLAY":
        metrics = modal_metrics(3)
        return {"pass": metrics["deterministic_frequencies"] and metrics["deterministic_modes"], **metrics}
    raise ValueError(f"Unknown WP10 internal case {case_id!r}.")


def run(output: Path, *, run_external: bool = True) -> dict[str, Any]:
    """Execute and persist the WP10 catalog plus the optional external oracle."""

    output = Path(output).resolve()
    source = source_sha()
    cases = load_cases(CATALOG)
    runner = VnvRunner(source_sha=source, environment={"runner": "run_wp10_wedge6_modal", "catalog": CATALOG.name})
    evidence = []
    for case in cases:
        if case.case_id == "WP10-MODAL-NO-DENSITY":
            def execute_invalid(_case: Any) -> ExecutionOutput:
                _solve(modal_model(density=0.0))
                return ExecutionOutput({"pass": False})
            current = runner.run(case, execute_invalid)
        elif case.case_id == "WP10-MODAL-CODE-ASTER":
            def execute_external(_case: Any) -> ExecutionOutput:
                if not run_external:
                    raise ExternalUnavailableError("External execution disabled by policy.")
                external = run_code_aster_modal(output.parent)
                return ExecutionOutput({"pass": external["state"] == "PASS_EXTERNAL_CORRELATION_BOUNDED", "external": external})
            current = runner.run(case, execute_external)
        else:
            current = runner.run(case, lambda item: ExecutionOutput(_case_observables(item.case_id)))
        evidence.append(current.to_dict())
    replay_case_id = "WP10-MODAL-REPLAY"
    replay_target = next(item for item in cases if item.case_id == replay_case_id)
    replay_evidence = next(item for item in evidence if item["case_id"] == replay_case_id)
    replay_ok, replay_reason, _ = replay_case(
        replay_target,
        lambda item: ExecutionOutput(_case_observables(item.case_id)),
        replay_evidence,
        source_sha=source,
        environment={"runner": "run_wp10_wedge6_modal", "catalog": CATALOG.name},
    )
    summary = {
        "schema_version": 1,
        "work_package": "WP10",
        "gate": "027-G10",
        "source_sha": source,
        "catalog": str(CATALOG.relative_to(ROOT)).replace("\\", "/"),
        "evidence": evidence,
        "replay": {"case_id": replay_case_id, "ok": replay_ok, "reason": replay_reason},
        "external": next(
            (item["observables"].get("external") for item in evidence if item["case_id"] == "WP10-MODAL-CODE-ASTER" and item["observables"].get("external")),
            {"state": "SKIPPED_EXTERNAL_UNAVAILABLE"},
        ),
        "policy": {
            "mass_formulation": "consistent",
            "production_quadrature": "TRI3_X_GAUSS2",
            "reference_quadrature": "DUFFY_GAUSS5_X_GAUSS4",
            "residual_pass": 1.0e-7,
            "mass_positive": "all eigenvalues > 0 for admissible full-rank element mass",
            "external_frequency_relative": 1.0e-2,
            "external_tolerance_status": "OWNER_REVIEW_REQUIRED",
            "static_evidence_transfer": False,
        },
        "summary": {
            "case_count": len(evidence),
            "pass": sum(item["verdict"] == "PASS" for item in evidence),
            "expected_failure_pass": sum(item["verdict"] == "EXPECTED_FAILURE_PASS" for item in evidence),
            "fail": sum(item["verdict"] == "FAIL" for item in evidence),
            "skipped_external_unavailable": sum(item["verdict"] == "SKIPPED_EXTERNAL_UNAVAILABLE" for item in evidence),
        },
        "maturity": "EXPERIMENTAL",
        "scope": {
            "element": "WEDGE6",
            "analysis": "modal",
            "material": "homogeneous_isotropic_small_strain",
            "backend": "common SciPy modal route",
            "mass": "consistent translational mass",
            "modes": "first six requested where available; first-mode evidence is bounded",
        },
        "limitations": [
            "WEDGE6 modal evidence is separate from static WP07-WP09 evidence and does not promote the public capability.",
            "No lumped-mass route is qualified.",
            "The mesh series reports first-frequency evolution; no universal convergence threshold is inferred from four levels.",
            "Mode-shape MAC is not claimed without an independently mapped external displacement field.",
            "External modal tolerance remains OWNER_REVIEW_REQUIRED and Code_Aster availability is environment-dependent.",
            "Newmark, harmonic, nonlinear, J2, TL and contact WEDGE6 routes remain outside WP10.",
        ],
        "artifact_classification": "CONTROLLED_PROOF",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return summary


__all__ = [
    "CATALOG",
    "MATERIAL_DATA",
    "modal_model",
    "mass_metrics",
    "modal_metrics",
    "refinement_metrics",
    "run_code_aster_modal",
    "run",
]
