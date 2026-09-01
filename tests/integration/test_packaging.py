import os
import subprocess
import sys
from pathlib import Path

from solveur.version import __version__

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 compatibility; tomllib is built in from Python 3.11.
    import tomli as tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _source_environment() -> dict[str, str]:
    environment = os.environ.copy()
    source = str(PROJECT_ROOT / "src")
    environment["PYTHONPATH"] = os.pathsep.join(
        value for value in (source, environment.get("PYTHONPATH", "")) if value
    )
    return environment


def _maintained_text_files() -> list[Path]:
    roots = [
        PROJECT_ROOT / "src" / "qf_solver",
        PROJECT_ROOT / "src" / "solveur",
        PROJECT_ROOT / "scripts",
        PROJECT_ROOT / "tests",
        PROJECT_ROOT / "docs",
        PROJECT_ROOT / "qualification",
        PROJECT_ROOT / ".github",
    ]
    suffixes = {".css", ".html", ".js", ".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}
    files = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "DEVELOPER_GUIDE.md",
        PROJECT_ROOT / "CHANGELOG.md",
        PROJECT_ROOT / "prochaines_etapes.md",
        PROJECT_ROOT / "pyproject.toml",
        PROJECT_ROOT / "qf_solver.py",
        PROJECT_ROOT / "main_solveur.py",
    ]
    for root in roots:
        files.extend(
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in suffixes and "generated" not in path.parts
        )
    return files


def test_pyproject_declares_installable_solver_package():
    data = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    assert project["name"] == "qf-solver"
    assert project["version"] == __version__
    assert project["requires-python"] == ">=3.10"
    assert {"numpy>=1.24", "scipy>=1.10", "matplotlib>=3.7"} <= set(project["dependencies"])
    assert "ruff>=0.6" in project["optional-dependencies"]["dev"]
    assert {"h5py>=3.10", "mpi4py>=3.1", "petsc4py>=3.20"} <= set(project["optional-dependencies"]["large"])
    assert "pypdf==6.10.0" in project["optional-dependencies"]["docs"]
    assert "platformdirs==4.9.4" in project["optional-dependencies"]["docs"]
    assert not any(
        dependency.startswith(("mkdocs", "playwright"))
        for dependency in project["optional-dependencies"]["docs"]
    )
    assert project["scripts"]["qf-solver"] == "solveur.cli.main:main"
    assert "qf-solver-docs" not in project["scripts"]
    assert project["scripts"]["solveur-ef"] == "solveur.cli.main:legacy_main"
    assert project["scripts"]["mitc4-solver"] == "solveur.compat.mitc4.cli:main"
    assert data["tool"]["ruff"]["line-length"] == 120
    assert "F" in data["tool"]["ruff"]["lint"]["select"]


def test_locked_documentation_baseline_contains_pdf_runtime():
    requirements = {
        line.strip()
        for line in (PROJECT_ROOT / "requirements/baseline-docs.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert "pypdf==6.10.0" in requirements


def test_pyproject_packages_include_public_and_internal_namespaces():
    data = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_finder = data["tool"]["setuptools"]["packages"]["find"]
    assert package_finder["where"] == ["src"]
    assert package_finder["include"] == ["qf_solver*", "solveur*"]


def test_runtime_distribution_excludes_repository_only_trees():
    data = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    data_files = data["tool"]["setuptools"]["data-files"]
    assert set(data_files) == {"examples", "qualification", "requirements"}
    serialized = repr(data_files)
    assert "tests/" not in serialized
    assert "docs/" not in serialized
    assert "qualification/reviews" not in serialized
    assert "qualification/vnv" not in serialized


def test_large_container_is_optional_tooling_not_a_root_runtime_file():
    assert not (PROJECT_ROOT / "Dockerfile").exists()
    assert not (PROJECT_ROOT / "docker").joinpath("large", "Dockerfile").exists()
    assert (PROJECT_ROOT / "tools" / "containers" / "large" / "Dockerfile").is_file()


def test_maintained_sources_use_only_qf_solver_brand():
    old_brand = "SAF" + "RAN"
    old_names = (old_brand, f"{old_brand.lower()}-solveur", f"{old_brand.lower()}_solveur")
    offenders: list[str] = []
    for path in _maintained_text_files():
        content = path.read_text(encoding="utf-8", errors="replace")
        if any(old_name.lower() in content.lower() for old_name in old_names):
            offenders.append(path.relative_to(PROJECT_ROOT).as_posix())
    assert offenders == []


def test_solver_cli_module_entry_point_runs():
    completed = subprocess.run(
        [sys.executable, "-m", "solveur.cli.main", "methods"],
        cwd=PROJECT_ROOT,
        env=_source_environment(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "linear_static:" in completed.stdout
    assert "nonlinear_static:" in completed.stdout


def test_solver_cli_module_help_runs():
    completed = subprocess.run(
        [sys.executable, "-m", "solveur.cli.main", "--help"],
        cwd=PROJECT_ROOT,
        env=_source_environment(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "check-mesh" in completed.stdout
    assert "convert-model" in completed.stdout
    assert "generate-large-tet4-block" in completed.stdout
    assert "inspect-large" in completed.stdout
    assert "benchmark-large" in completed.stdout
    assert "large-readiness" in completed.stdout
    assert "qualify-large" in completed.stdout
    assert "verify-large" in completed.stdout
    assert "solve-large" in completed.stdout
    assert "verify-evidence" in completed.stdout
    assert "solve" in completed.stdout


def test_solver_cli_module_check_mesh_and_solve_run(tmp_path: Path):
    example = PROJECT_ROOT / "examples" / "tet4_static.json"
    mesh_report = tmp_path / "mesh_report.json"
    result_path = tmp_path / "result.json"
    check = subprocess.run(
        [
            sys.executable,
            "-m",
            "solveur.cli.main",
            "check-mesh",
            "--input",
            str(example),
            "--json-report",
            str(mesh_report),
        ],
        cwd=PROJECT_ROOT,
        env=_source_environment(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0, check.stdout + check.stderr
    assert mesh_report.exists()
    solve = subprocess.run(
        [
            sys.executable,
            "-m",
            "solveur.cli.main",
            "solve",
            "--input",
            str(example),
            "--output",
            str(result_path),
            "--audit-gate",
            "fail",
        ],
        cwd=PROJECT_ROOT,
        env=_source_environment(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert solve.returncode == 0, solve.stdout + solve.stderr
    assert result_path.exists()


def test_solver_cli_version_runs():
    completed = subprocess.run(
        [sys.executable, "-m", "solveur.cli.main", "--version"],
        cwd=PROJECT_ROOT,
        env=_source_environment(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.strip() == f"QF_solver {__version__}"


def test_portable_and_legacy_launchers_expose_qf_solver_identity():
    portable = subprocess.run(
        [sys.executable, "qf_solver.py", "--version"],
        cwd=PROJECT_ROOT,
        env=_source_environment(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert portable.returncode == 0, portable.stdout + portable.stderr
    assert portable.stdout.strip() == f"QF_solver {__version__}"
    legacy = subprocess.run(
        [sys.executable, "main_solveur.py", "--version"],
        cwd=PROJECT_ROOT,
        env=_source_environment(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert legacy.returncode == 0, legacy.stdout + legacy.stderr
    assert legacy.stdout.strip() == f"QF_solver {__version__}"
    assert "deprecated" in legacy.stderr


def test_mitc4_cli_module_entry_point_runs():
    completed = subprocess.run(
        [sys.executable, "-m", "solveur.compat.mitc4.cli", "--help"],
        cwd=PROJECT_ROOT,
        env=_source_environment(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "verify" in completed.stdout
    assert "scordelis" in completed.stdout


def test_mitc4_cli_version_runs():
    completed = subprocess.run(
        [sys.executable, "-m", "solveur.compat.mitc4.cli", "--version"],
        cwd=PROJECT_ROOT,
        env=_source_environment(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert __version__ in completed.stdout
