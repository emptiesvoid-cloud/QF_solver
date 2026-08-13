"""CSV exports for solved finite element results."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from solveur.core.dofs import DOF_ORDER, TRANSLATION_DOFS
from solveur.core.model import FiniteElementModel


class CsvResultWriter:
    """Write tabular result and audit data for spreadsheets or scripts."""

    def write(self, result: object, directory: str | Path, model: FiniteElementModel | None = None) -> dict[str, Path]:
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        written = {"element_results": target / "element_results.csv"}
        if hasattr(result, "displacements"):
            written["nodal_displacements"] = target / "nodal_displacements.csv"
            self._write_nodal_displacements(result, written["nodal_displacements"], model)
        self._write_table(getattr(result, "element_results", []), written["element_results"])
        time_history = getattr(result, "solver", {}).get("time_history", [])
        if time_history:
            written["time_history"] = target / "time_history.csv"
            self._write_table(time_history, written["time_history"])
        if hasattr(result, "to_dict"):
            frequency_response = result.to_dict().get("frequency_response", [])
            if frequency_response:
                written["frequency_response"] = target / "frequency_response.csv"
                self._write_table(_frequency_rows(frequency_response), written["frequency_response"])
        nodal_results = getattr(result, "nodal_results", [])
        if nodal_results:
            written["nodal_results"] = target / "nodal_results.csv"
            self._write_table(nodal_results, written["nodal_results"])
        audit = getattr(result, "audit", None)
        if audit is not None:
            audit_data = audit.to_dict()
            written["audit_checks"] = target / "audit_checks.csv"
            self._write_table(audit_data.get("checks", []), written["audit_checks"])
            if audit_data.get("post_results"):
                written["post_results"] = target / "post_results.csv"
                self._write_table(audit_data["post_results"], written["post_results"])
        return written

    @staticmethod
    def _write_nodal_displacements(result: object, path: Path, model: FiniteElementModel | None) -> None:
        dofs = getattr(result, "dofs", None)
        displacements = getattr(result, "displacements", None)
        if dofs is None or displacements is None:
            raise ValueError("CSV displacement export requires a static displacement result.")
        values = np.asarray(displacements, dtype=float)
        rows: list[dict[str, Any]] = []
        for node, names in sorted(dofs.node_dofs.items()):
            row: dict[str, Any] = {"node": int(node)}
            if model is not None:
                x, y, z = model.nodes[int(node)]
                row.update({"x": float(x), "y": float(y), "z": float(z)})
            for dof in DOF_ORDER:
                row[dof] = float(values[dofs.index(node, dof)]) if dof in names else ""
            translation = [float(row[dof]) for dof in TRANSLATION_DOFS if row.get(dof) != ""]
            row["translation_magnitude"] = float(np.linalg.norm(translation)) if translation else 0.0
            rows.append(row)
        CsvResultWriter._write_table(rows, path)

    @staticmethod
    def _write_table(rows: list[dict[str, Any]], path: Path) -> None:
        flattened = [_flatten_row(row) for row in rows]
        columns: list[str] = []
        for row in flattened:
            for key in row:
                if key not in columns:
                    columns.append(key)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(flattened)


def _flatten_row(row: dict[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in row.items():
        _flatten_value(str(key), value, flattened)
    return flattened


def _flatten_value(prefix: str, value: Any, output: dict[str, Any]) -> None:
    if isinstance(value, dict):
        for subkey, subvalue in value.items():
            _flatten_value(f"{prefix}_{subkey}", subvalue, output)
        return
    if isinstance(value, (list, tuple)):
        if all(isinstance(item, (int, float, str, bool)) or item is None for item in value):
            for index, item in enumerate(value):
                output[f"{prefix}_{index}"] = item
        else:
            output[prefix] = json.dumps(value)
        return
    output[prefix] = value


def _frequency_rows(response: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in response:
        base = {
            "index": item["index"],
            "frequency_hz": item["frequency_hz"],
            "omega_rad_s": item["omega_rad_s"],
            "max_displacement_amplitude": item["max_displacement_amplitude"],
        }
        for node in item.get("displacements", []):
            for dof, values in node.get("dofs", {}).items():
                rows.append({"node": node["node"], "dof": dof, **base, **values})
    return rows
