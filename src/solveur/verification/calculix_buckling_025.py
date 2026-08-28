"""Bounded CalculiX correlation for the 0.2.5 solid buckling path.

The campaign deliberately compares the same QF model, boundary conditions and
nodal load vector with CalculiX.  It is an external numerical correlation, not
a physical validation and not a post-buckling qualification.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from solveur.core.errors import InfrastructureError
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import sha256, write_json_file
from solveur.verification.calculix_tl_structural import parse_calculix_buckling_factors
from solveur.verification.robustness_nonlinear_solids import (
    ELEMENT_TYPES,
    _buckling_mesh_model,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-BUCKLING-CALCULIX-SOLID-FAMILIES-025"
DEFAULT_IMAGE = "qf-solver/calculix-nafems13h:2.20"
CORRELATION_TOLERANCE = 0.10
CALCULIX_TYPES = {
    "TET4": "C3D4",
    "TET10": "C3D10",
    "HEX8": "C3D8",
    "HEX20": "C3D20",
}

# QF uses the Gmsh-style HEX20 edge order. CalculiX follows the conventional
# C3D20 order: four bottom edges, four top edges, then four vertical edges.
_CALCULIX_LOCAL_ORDER = {
    "TET4": tuple(range(4)),
    "TET10": tuple(range(10)),
    "HEX8": tuple(range(8)),
    "HEX20": (0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 13, 9, 16, 18, 19, 17, 10, 12, 14, 15),
}
_DOF_INDEX = {"UX": 1, "UY": 2, "UZ": 3}


def write_buckling_input(
    path: str | Path,
    model: FiniteElementModel,
    element_type: str,
    *,
    modes: int = 1,
) -> Path:
    """Write a deterministic CalculiX linear-buckling deck for ``model``."""

    family = str(element_type).upper()
    if family not in CALCULIX_TYPES:
        raise ValueError(f"Unsupported CalculiX solid family: {element_type!r}.")
    if not model.elements or any(item.type != family for item in model.elements):
        raise ValueError("The CalculiX buckling deck requires one homogeneous solid family.")
    if not model.loads:
        raise ValueError("The CalculiX buckling deck requires at least one nodal load.")
    if isinstance(modes, bool) or not isinstance(modes, int) or modes < 1:
        raise ValueError("modes must be a positive integer.")
    fixed_nodes = _fully_fixed_nodes(model)
    free_equations = 3 * model.node_count - 3 * len(fixed_nodes)
    lanczos_vectors = _lanczos_vectors(modes, free_equations)
    load_rows = [(int(item.node) + 1, _DOF_INDEX[item.dof], float(item.value)) for item in model.loads]
    material_name = model.elements[0].material
    material = model.materials[material_name]
    young = float(material.get("E", material.get("young_modulus", 0.0)))
    poisson = float(material.get("nu", material.get("poisson_ratio", 0.0)))
    if not np.isfinite(young) or young <= 0.0 or not np.isfinite(poisson) or not -1.0 < poisson < 0.5:
        raise ValueError("CalculiX buckling material needs finite E and -1 < nu < 0.5.")

    lines = [
        "*HEADING",
        f"QF Solver 0.2.5 bounded buckling correlation {family}",
        "*NODE",
    ]
    lines.extend(
        f"{index},{point[0]:.16g},{point[1]:.16g},{point[2]:.16g}"
        for index, point in enumerate(np.asarray(model.nodes, dtype=float), start=1)
    )
    lines.extend([f"*ELEMENT,TYPE={CALCULIX_TYPES[family]},ELSET=EALL"])
    order = _CALCULIX_LOCAL_ORDER[family]
    for index, element in enumerate(model.elements, start=1):
        connectivity = tuple(int(node) + 1 for node in element.nodes)
        if len(connectivity) != len(order):
            raise ValueError(f"{family} connectivity has {len(connectivity)} nodes, expected {len(order)}.")
        ordered = [connectivity[position] for position in order]
        lines.append(f"{index}," + ",".join(str(node) for node in ordered[:15]))
        if len(ordered) > 15:
            lines.append("," + ",".join(str(node) for node in ordered[15:]))
    lines.extend(
        [
            "*SOLID SECTION,ELSET=EALL,MATERIAL=MAT",
            "*MATERIAL,NAME=MAT",
            "*ELASTIC",
            f"{young:.16g},{poisson:.16g}",
            "*NSET,NSET=FIXED",
            *_set_lines(fixed_nodes),
            "*BOUNDARY",
            "FIXED,1,3,0.",
            "*STEP",
            "*BUCKLE",
            f"{modes},0.001,{lanczos_vectors},1000",
            "*CLOAD",
        ]
    )
    lines.extend(f"{node},{dof},{value:.16g}" for node, dof, value in load_rows)
    lines.extend(["*NODE FILE", "U", "*END STEP"])
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="ascii")
    return target


def run_campaign(
    output_dir: str | Path,
    *,
    element_types: tuple[str, ...] = ELEMENT_TYPES,
    cells: int = 1,
    image: str = DEFAULT_IMAGE,
    modes: int = 1,
    execute: bool = True,
) -> dict[str, Any]:
    """Run bounded QF/CalculiX buckling correlation for selected families."""

    if isinstance(cells, bool) or not isinstance(cells, int) or cells < 1:
        raise ValueError("cells must be a positive integer.")
    if isinstance(modes, bool) or not isinstance(modes, int) or modes < 1:
        raise ValueError("modes must be a positive integer.")
    families = tuple(str(item).upper() for item in element_types)
    if not families or any(item not in CALCULIX_TYPES for item in families):
        raise ValueError("element_types must contain only TET4, TET10, HEX8 or HEX20.")
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for family in families:
        model = _buckling_mesh_model(family, cells)
        fixed_nodes = _fully_fixed_nodes(model)
        free_equations = 3 * model.node_count - 3 * len(fixed_nodes)
        qf_result = _solve_qf(model)
        work = output / family.lower()
        work.mkdir(parents=True, exist_ok=True)
        deck = write_buckling_input(work / "buckling.inp", model, family, modes=modes)
        row: dict[str, Any] = {
            "element": family,
            "calculix_element": CALCULIX_TYPES[family],
            "cells": cells,
            "node_count": model.node_count,
            "element_count": len(model.elements),
            "dof_count": int(model.dof_manager().ndof),
            "free_equation_count": int(free_equations),
            "lanczos_vectors": int(_lanczos_vectors(modes, free_equations)),
            "qf_critical_factor": float(qf_result.solver["critical_factor"]),
            "qf_mode_residual_relative": float(qf_result.solver["critical_mode_residual_relative"]),
            "deck_sha256": sha256(deck),
            "status": "PLANNED" if not execute else "FAIL_EXTERNAL_EXECUTION",
        }
        if execute:
            try:
                factors = _run_calculix(work, image=image)
                external = float(factors[0])
                qf_factor = float(row["qf_critical_factor"])
                difference = abs(external - qf_factor) / max(abs(qf_factor), 1.0e-12)
                row.update(
                    {
                        "calculix_factors": factors,
                        "calculix_critical_factor": external,
                        "relative_difference": difference,
                        "tolerance": CORRELATION_TOLERANCE,
                        "status": "PASS"
                        if np.isfinite(difference) and difference <= CORRELATION_TOLERANCE
                        else "FAIL",
                    }
                )
            except (InfrastructureError, OSError, RuntimeError, ValueError) as exc:
                row.update(
                    {
                        "status": "BLOCKED_EXTERNAL_TOOL",
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
        rows.append(row)
    statuses = {str(row["status"]) for row in rows}
    if not execute:
        status = "PLANNED"
    elif statuses == {"PASS"}:
        status = "PASS_EXTERNAL_CORRELATION_BOUNDED"
    elif "BLOCKED_EXTERNAL_TOOL" in statuses:
        status = "BLOCKED_EXTERNAL_TOOL"
    else:
        status = "FAIL_EXTERNAL_CORRELATION"
    summary: dict[str, Any] = {
        "study_id": STUDY_ID,
        "status": status,
        "maturity": "research",
        "release_claim": False,
        "provenance": _git_provenance(),
        "external_solver": {"name": "CalculiX", "version": "2.20", "image": image},
        "scope": {
            "elements": list(families),
            "mesh": f"regular shared mesh cells={cells}",
            "analysis": "linearized tangent buckling",
            "same_qf_model": True,
            "requested_modes": modes,
        },
        "rows": rows,
        "limitations": [
            "Numerical correlation only; no physical validation claim.",
            "First linearized tangent-instability factor only; no post-buckling path.",
            "The 10 percent band is a bounded correlation screen, not a release-wide tolerance.",
            "The campaign does not close the general external-correlation matrix by itself.",
            "A BLOCKED_EXTERNAL_TOOL row records an external executable or input failure; it is not a correlation pass.",
        ],
    }
    write_json_file(output / "summary.json", summary)
    _write_plot(output, rows)
    _write_report(output, summary)
    write_vnv_manifest(output, STUDY_ID)
    return summary


def _git_provenance() -> dict[str, str | bool | None]:
    """Record the source revision without making Git a runtime dependency."""

    root = _repository_root()
    if root is None:
        return {"sha": "unknown", "worktree_dirty": None}
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        fallback_sha = _read_git_head(root)
        return {"sha": fallback_sha or "unknown", "worktree_dirty": None}
    return {"sha": sha or "unknown", "worktree_dirty": dirty}


def _repository_root() -> Path | None:
    """Find the checkout owning the current execution, including installed runs."""

    candidates = [Path.cwd(), *Path.cwd().parents, *Path(__file__).resolve().parents]
    for candidate in candidates:
        if (candidate / ".git").exists():
            return candidate
    return None


def _read_git_head(root: Path) -> str | None:
    """Read a commit id directly when the Git subprocess is unavailable."""

    git_entry = root / ".git"
    if git_entry.is_dir():
        git_dir = git_entry
    elif git_entry.is_file():
        marker = git_entry.read_text(encoding="utf-8").strip()
        if not marker.startswith("gitdir:"):
            return None
        git_dir = (root / marker.partition(":")[2].strip()).resolve()
    else:
        return None
    common_dir = git_dir
    commondir = git_dir / "commondir"
    if commondir.is_file():
        common_dir = (git_dir / commondir.read_text(encoding="ascii").strip()).resolve()

    head = git_dir / "HEAD"
    if not head.is_file():
        return None
    value = head.read_text(encoding="ascii").strip()
    if value.startswith("ref: "):
        ref_name = value[5:]
        reference = git_dir / ref_name
        if not reference.is_file():
            reference = common_dir / ref_name
        if reference.is_file():
            value = reference.read_text(encoding="ascii").strip()
        else:
            packed_refs = common_dir / "packed-refs"
            if not packed_refs.is_file():
                return None
            value = next(
                (line.split(" ", maxsplit=1)[0] for line in packed_refs.read_text(encoding="ascii").splitlines() if line.endswith(f" {ref_name}")),
                "",
            )
    return value if len(value) == 40 and all(character in "0123456789abcdef" for character in value.lower()) else None


def _solve_qf(model: FiniteElementModel) -> Any:
    from solveur.api import solve_model

    return solve_model(model, enforce_policy=False)


def _run_calculix(work: Path, *, image: str) -> list[float]:
    docker = os.environ.get("QF_SOLVER_DOCKER") or shutil.which("docker")
    if not docker:
        raise InfrastructureError("CalculiX correlation requires the Docker CLI.")
    try:
        completed = subprocess.run(
            [docker, "run", "--rm", "-v", f"{work}:/work", "-w", "/work", image, "buckling"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1200,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise InfrastructureError("CalculiX buckling correlation exceeded 1200 seconds.") from exc
    (work / "calculix.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        tail = "\n".join((completed.stdout + completed.stderr).splitlines()[-40:])
        raise RuntimeError(f"CalculiX buckling failed:\n{tail}")
    return parse_calculix_buckling_factors(work / "buckling.dat")


def _fully_fixed_nodes(model: FiniteElementModel) -> list[int]:
    required = {"UX", "UY", "UZ"}
    fixed = [condition.node for condition in model.fixed_dofs if set(condition.dofs) >= required]
    if not fixed:
        raise ValueError("The CalculiX buckling deck requires at least one fully fixed node set.")
    return sorted(set(int(node) + 1 for node in fixed))


def _lanczos_vectors(modes: int, free_equations: int) -> int:
    """Choose a valid CalculiX Lanczos subspace for the reduced system.

    CalculiX requires the Lanczos subspace to be smaller than the number of
    unconstrained equations.  The historical fixed value of 30 therefore
    fails on the smallest TET4/HEX8 probes even though the model itself is
    valid.  Keep the usual bounded value for larger systems and shrink it for
    small external-correlation decks.
    """

    minimum_vectors = max(4 * modes, modes + 2)
    candidate = min(30, free_equations - 1)
    if candidate < minimum_vectors:
        raise ValueError(
            "CalculiX buckling needs more free equations than requested modes "
            "plus one Lanczos vector."
        )
    return candidate


def _set_lines(values: list[int]) -> list[str]:
    return [
        ",".join(str(value) for value in values[index : index + 16])
        for index in range(0, len(values), 16)
    ]


def _write_plot(output: Path, rows: list[dict[str, Any]]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [str(row["element"]) for row in rows]
    qf = [float(row["qf_critical_factor"]) for row in rows]
    external = [float(row.get("calculix_critical_factor", np.nan)) for row in rows]
    x = np.arange(len(labels))
    figure, axis = plt.subplots(figsize=(7.6, 4.5))
    axis.plot(x, qf, "o-", label="QF Solver")
    if np.any(np.isfinite(external)):
        axis.plot(x, external, "s--", label="CalculiX")
    axis.set_xticks(x, labels)
    axis.set_ylabel("Critical load factor")
    axis.grid(True, axis="y", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output / "buckling_external_comparison.png", dpi=180)
    plt.close(figure)


def _write_report(output: Path, summary: dict[str, Any]) -> None:
    lines = [
        f"# {STUDY_ID}",
        "",
        f"Status: **{summary['status']}**",
        "",
        "Bounded same-model linearized tangent-buckling correlation.",
        "",
        "| Element | QF factor | CalculiX factor | Relative difference | Status |",
        "|---|---:|---:|---:|---|",
    ]
    for row in summary["rows"]:
        external = row.get("calculix_critical_factor")
        difference = row.get("relative_difference")
        lines.append(
            f"| {row['element']} | {float(row['qf_critical_factor']):.8g} | "
            f"{float(external):.8g} | {float(difference):.3e} | {row['status']} |"
            if external is not None and difference is not None
            else f"| {row['element']} | {float(row['qf_critical_factor']):.8g} | - | - | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "![Buckling external comparison](buckling_external_comparison.png)",
            "",
            "## External diagnostics",
            "",
            "This is numerical correlation only. It does not claim physical validation, "
            "post-buckling, or general external qualification.",
            "",
        ]
    )
    blocked = [row for row in summary["rows"] if row["status"] == "BLOCKED_EXTERNAL_TOOL"]
    if blocked:
        diagnostic_lines = [
            f"- `{row['element']}`: `{row.get('error_type', 'ExternalError')}` - "
            f"{str(row.get('error', 'no diagnostic')).splitlines()[-1][:240]}"
            for row in blocked
        ]
        insert_at = len(lines) - 3
        lines[insert_at:insert_at] = diagnostic_lines + [""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")


__all__ = [
    "CALCULIX_TYPES",
    "CORRELATION_TOLERANCE",
    "DEFAULT_IMAGE",
    "STUDY_ID",
    "run_campaign",
    "write_buckling_input",
]
