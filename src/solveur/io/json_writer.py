"""Write solver result JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from solveur.core.errors import InputValidationError


class JsonResultWriter:
    """Serialize solve results with stable formatting."""

    def write(self, result: object, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            serialized = json.dumps(result.to_dict(), indent=2, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise InputValidationError(f"Cannot serialize solve result as finite JSON: {exc}") from exc
        try:
            with target.open("x", encoding="utf-8") as handle:
                handle.write(serialized)
        except FileExistsError as exc:
            raise InputValidationError(f"Refusing to overwrite existing solve result JSON: {target}") from exc
