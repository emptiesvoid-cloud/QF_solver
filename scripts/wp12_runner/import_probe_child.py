"""Non-numerical child process used to verify the candidate source import."""

from __future__ import annotations

import importlib.metadata
import importlib
import json
from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"state": "INVALID_ARGUMENTS"}))
        return 2
    source_root = Path(sys.argv[1]).resolve(strict=True)
    package_root = source_root / "src" / "solveur"
    if not package_root.is_dir():
        print(json.dumps({"state": "SOURCE_PACKAGE_MISSING"}))
        return 2

    # Insert only the pinned scientific checkout. The -I launcher ignores user
    # site-packages and ambient PYTHONPATH; no FEM or analysis API is imported.
    sys.path.insert(0, str(source_root / "src"))
    try:
        solveur = importlib.import_module("solveur")
        version = importlib.import_module("solveur.version")
    except Exception as exc:  # diagnostic must report an import failure cleanly
        print(json.dumps({"state": "IMPORT_FAILED", "error_type": type(exc).__name__}))
        return 2

    package_file = Path(solveur.__file__).resolve(strict=True)
    version_file = Path(version.__file__).resolve(strict=True)
    try:
        package_file.relative_to(package_root)
        version_file.relative_to(package_root)
    except ValueError:
        state = "WRONG_IMPORT_ORIGIN"
        return_code = 3
    else:
        state = "SOURCE_IMPORT_VERIFIED"
        return_code = 0
    try:
        distribution = importlib.metadata.distribution("qf-solver")
        installed_distribution = {
            "version": distribution.version,
            "metadata_path": str(getattr(distribution, "_path", "")),
        }
    except importlib.metadata.PackageNotFoundError:
        installed_distribution = None
    print(
        json.dumps(
            {
                "state": state,
                "python_executable": str(Path(sys.executable).resolve()),
                "python_version": sys.version.split()[0],
                "virtual_environment": sys.prefix != sys.base_prefix,
                "sys_prefix": sys.prefix,
                "base_prefix": sys.base_prefix,
                "scientific_source_root": str(source_root),
                "solveur_file": str(package_file),
                "version_file": str(version_file),
                "version": getattr(version, "__version__", None),
                "installed_qf_solver_distribution": installed_distribution,
                "fem_or_analysis_api_called": False,
            },
            sort_keys=True,
        )
    )
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
