import subprocess
import sys
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_public_facade_exports_documented_workflow() -> None:
    from qf_solver import check_mesh, load_model, save_result, solve_model

    assert all(callable(symbol) for symbol in (check_mesh, load_model, save_result, solve_model))


def test_public_facade_exports_documented_types() -> None:
    from qf_solver import MeshQualityThresholds, MeshValidator, OrthotropicLamina

    assert MeshQualityThresholds.__name__ == "MeshQualityThresholds"
    assert MeshValidator.__name__ == "MeshValidator"
    assert OrthotropicLamina.__name__ == "OrthotropicLamina"


def test_source_launcher_is_also_an_import_compatible_facade() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from qf_solver import load_model, __version__; print(__version__, load_model.__name__)",
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.strip() == "0.2.2a0 load_model"


def test_src_layout_package_exposes_the_same_facade(tmp_path: Path) -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from qf_solver import load_model, __version__; print(__version__, load_model.__name__)",
        ],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.strip() == "0.2.2a0 load_model"


def test_public_markdown_examples_do_not_import_internal_namespace() -> None:
    offenders: list[str] = []
    for path in [PROJECT_ROOT / "README.md", *(PROJECT_ROOT / "docs").rglob("*.md")]:
        text = path.read_text(encoding="utf-8")
        if "from solveur" in text or "import solveur" in text:
            offenders.append(path.relative_to(PROJECT_ROOT).as_posix())
    assert offenders == []
