"""Independent CalculiX probe for the additional deformable contact model."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import cast

import numpy as np

from solveur.verification.calculix_total_lagrangian import (
    parse_last_frd_displacement,
)


CALCULIX_IMAGE = "qf-solver/calculix-nafems13h:2.20"


def run_calculix_precontact_probe(
    work: Path,
    data: dict[str, object],
) -> list[float]:
    """Return the two free-surface displacements at 10 percent load."""
    target = work / "calculix_precontact.inp"
    target.write_text(calculix_probe_deck(data), encoding="ascii")
    completed = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{work}:/work",
            "-w",
            "/work",
            CALCULIX_IMAGE,
            target.stem,
        ],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    (work / "calculix_precontact.log").write_text(
        completed.stdout + completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "CalculiX pre-contact probe failed:\n"
            + "\n".join((completed.stdout + completed.stderr).splitlines()[-30:])
        )
    elements = cast(list[dict[str, object]], data["elements"])
    node_count = 1 + max(
        int(node)
        for element in elements
        for node in cast(list[int], element["nodes"])
    )
    displacement = parse_last_frd_displacement(
        work / "calculix_precontact.frd",
        node_count,
    )
    slaves = cast(list[int], data["_plot"]["slaves"])
    return [float(displacement[node, 0]) for node in slaves]


def calculix_probe_deck(data: dict[str, object]) -> str:
    """Build the same TET4 block without contact at 10 percent load."""
    elements = cast(list[dict[str, object]], data["elements"])
    node_count = 1 + max(
        int(node)
        for element in elements
        for node in cast(list[int], element["nodes"])
    )
    nodes = cast(list[list[float]], data["nodes"])[:node_count]
    fixed = [
        index + 1
        for index, point in enumerate(nodes)
        if np.isclose(float(point[0]), 1.1)
    ]
    slaves = [node + 1 for node in cast(list[int], data["_plot"]["slaves"])]
    lines = ["*HEADING", "QF contact block pre-contact probe", "*NODE"]
    lines.extend(
        f"{index + 1},{point[0]:.16g},{point[1]:.16g},{point[2]:.16g}"
        for index, point in enumerate(nodes)
    )
    lines.append("*ELEMENT,TYPE=C3D4,ELSET=EALL")
    lines.extend(
        f"{index + 1},"
        + ",".join(
            str(int(node) + 1)
            for node in cast(list[int], element["nodes"])
        )
        for index, element in enumerate(elements)
    )
    lines.extend(["*NSET,NSET=FIXED", *_chunks(fixed)])
    for index, slave in enumerate(slaves, start=1):
        lines.extend([f"*NSET,NSET=SLAVE_{index}", str(slave)])
    lines.extend(
        [
            "*MATERIAL,NAME=ISO",
            "*ELASTIC",
            "10000.,0.3",
            "*SOLID SECTION,ELSET=EALL,MATERIAL=ISO",
            "*BOUNDARY",
            "FIXED,1,3,0.",
            "*STEP",
            "*STATIC",
            "*CLOAD",
            "SLAVE_1,1,-200.",
            "SLAVE_2,1,-200.",
            "*NODE FILE",
            "U",
            "*END STEP",
        ]
    )
    return "\n".join(lines) + "\n"


def _chunks(values: list[int]) -> list[str]:
    return [
        ",".join(str(value) for value in values[start : start + 16])
        for start in range(0, len(values), 16)
    ]
