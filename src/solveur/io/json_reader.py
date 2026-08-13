"""Read solver JSON input files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.io.schema import JsonSchemaValidator


class JsonModelReader:
    """Convert a JSON model file into a FiniteElementModel."""

    def read(self, path: str | Path) -> FiniteElementModel:
        source = Path(path)
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except OSError as exc:
            raise InputValidationError(f"Cannot read model input {source}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise InputValidationError(
                f"Malformed JSON in {source} at line {exc.lineno}, column {exc.colno}: {exc.msg}."
            ) from exc
        return self.from_dict(data)

    def from_dict(self, data: dict[str, Any]) -> FiniteElementModel:
        JsonSchemaValidator().validate(data)
        return FiniteElementModel.from_raw(
            analysis=data.get("analysis", "linear_static"),
            nodes=data["nodes"],
            elements=data.get("elements", []),
            materials=data.get("materials", {}),
            fixed_dofs=data.get("fixed_dofs", []),
            loads=data.get("loads", []),
            distributed_loads=data.get("distributed_loads", []),
            springs=data.get("springs", []),
            concentrated_masses=data.get("concentrated_masses", []),
            multipoint_constraints=data.get("multipoint_constraints", []),
            rbe2=data.get("rbe2", []),
            rbe3=data.get("rbe3", []),
            contacts=data.get("contacts", []),
            schema_version=int(data.get("schema_version", 1)),
            units=dict(data.get("units", {"system": "SI"})),
            verification_profile=str(data.get("verification_profile", "engineering")),
        )
