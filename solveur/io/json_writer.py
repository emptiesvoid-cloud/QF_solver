"""Write solver result JSON files."""

from __future__ import annotations

import json
from pathlib import Path


class JsonResultWriter:
    """Serialize solve results with stable formatting."""

    def write(self, result: object, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
