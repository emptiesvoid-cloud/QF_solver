"""Generate small reproducible HEX8 mesh inputs for the 0.2.6 V&V corpus."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "examples" / "vnv_026_g06"


def build_hex8_mesh(nx: int) -> dict[str, object]:
    if nx < 1:
        raise ValueError("nx must be positive")
    nodes = []
    index: dict[tuple[int, int, int], int] = {}
    for i in range(nx + 1):
        for j in range(2):
            for k in range(2):
                index[(i, j, k)] = len(nodes)
                nodes.append([i / nx, float(j), float(k)])
    elements = []
    for i in range(nx):
        elements.append({
            "type": "HEX8",
            "nodes": [
                index[(i, 0, 0)], index[(i + 1, 0, 0)], index[(i + 1, 1, 0)], index[(i, 1, 0)],
                index[(i, 0, 1)], index[(i + 1, 0, 1)], index[(i + 1, 1, 1)], index[(i, 1, 1)],
            ],
            "material": "solid",
        })
    fixed = [{"node": index[(0, j, k)], "dofs": ["UX", "UY", "UZ"]} for j in range(2) for k in range(2)]
    loaded = [index[(nx, j, k)] for j in range(2) for k in range(2)]
    loads = [{"node": node, "dof": "UX", "value": 1.0 / len(loaded)} for node in loaded]
    return {
        "analysis": {"type": "linear_static", "method": "direct"},
        "nodes": nodes,
        "elements": elements,
        "materials": {"solid": {"type": "isotropic_3d", "E": 210000000000.0, "nu": 0.3, "density": 7800.0}},
        "fixed_dofs": fixed,
        "loads": loads,
    }


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for nx in (1, 2, 4, 8):
        path = OUTPUT / f"hex8_mesh_{nx:02d}.json"
        path.write_text(json.dumps(build_hex8_mesh(nx), indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len((1, 2, 4, 8))} G06 HEX8 mesh models in {OUTPUT}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
