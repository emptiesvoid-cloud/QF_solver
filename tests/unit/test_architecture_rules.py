import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAX_SOURCE_LINES = 700

# The 700-line guard is a product-code maintainability control.  These
# explicitly named files are frozen V&V campaign runners or the two bounded
# distributed/dynamic integration modules.  Their exact budgets prevent new
# growth while keeping historical campaign evidence from being mistaken for
# ordinary library source.  They remain refactoring debt rather than a new
# project-wide line-limit baseline.
FROZEN_SOURCE_LINE_BUDGETS = {
    "scripts/run_wp13_01c_final_runtime.py": 1512,
    "scripts/wp13_02b9_harness.py": 1003,
    "scripts/run_wp13_07_contact_bounded.py": 886,
    "scripts/run_wp13_02c_harmonic_mixed.py": 830,
    "scripts/run_wp13_03b_v2_mpc_rbe2.py": 801,
    "scripts/run_wp13_02c2_harmonic_harness.py": 789,
    "scripts/wp13_02b12_contract_compliance.py": 754,
    "src/solveur/large/generic_distributed.py": 1160,
    "src/solveur/core/analyses/dynamic.py": 723,
}


def test_python_source_files_stay_within_product_or_frozen_evidence_budgets():
    roots = [PROJECT_ROOT / "src" / "solveur"]
    roots.extend(PROJECT_ROOT / name for name in ("scripts", "tests"))
    oversized: list[str] = []
    for root in roots:
        for path in root.rglob("*.py"):
            line_count = sum(1 for _ in path.open(encoding="utf-8"))
            relative = path.relative_to(PROJECT_ROOT).as_posix()
            limit = FROZEN_SOURCE_LINE_BUDGETS.get(relative, MAX_SOURCE_LINES)
            if line_count > limit:
                oversized.append(f"{relative}: {line_count} (limit {limit})")
    assert oversized == []


def test_solver_layers_do_not_import_forbidden_upper_layers():
    rules = {
        PROJECT_ROOT / "src" / "solveur" / "elements": ("solveur.io", "solveur.cli", "solveur.api"),
        PROJECT_ROOT / "src" / "solveur" / "loads": ("solveur.io", "solveur.cli", "solveur.api"),
        PROJECT_ROOT / "src" / "solveur" / "core": ("solveur.cli", "solveur.api"),
    }
    violations: list[str] = []
    for root, forbidden_prefixes in rules.items():
        for path in root.rglob("*.py"):
            for imported in _solveur_imports(path):
                if imported.startswith(forbidden_prefixes):
                    relative = path.relative_to(PROJECT_ROOT)
                    violations.append(f"{relative}: imports {imported}")
    assert violations == []


def test_product_code_keeps_mitc4_compatibility_inside_solver_namespace():
    violations: list[str] = []
    product_root = PROJECT_ROOT / "src" / "solveur"
    for path in product_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = [node.module]
            else:
                continue
            if any(name == "mitc4" or name.startswith("mitc4.") for name in imported):
                violations.append(f"{path.relative_to(PROJECT_ROOT)}: imports removed top-level mitc4 package")
    assert violations == []


def test_core_implementation_has_explicit_domain_packages_and_compatibility_facades():
    core = PROJECT_ROOT / "src" / "solveur" / "core"
    for package in ("assembly", "solvers", "analyses", "nonlinear"):
        package_path = core / package
        assert (package_path / "__init__.py").is_file()

    ownership = {
        "assembly": ("assembler.py", "plan.py", "sparse.py", "geometric.py", "nonlinear.py"),
        "solvers": ("linear.py", "policy.py", "backend.py", "static.py"),
        "analyses": ("settings.py", "buckling.py", "dynamic.py", "modal.py", "harmonic.py"),
        "nonlinear": ("solver.py", "contracts.py", "controls.py", "iteration.py", "material_state.py"),
    }
    for package, modules in ownership.items():
        for module in modules:
            assert (core / package / module).is_file()

    for facade in ("assembler.py", "solver.py", "analysis.py", "modal.py", "nonlinear_iteration.py"):
        content = (core / facade).read_text(encoding="utf-8")
        assert "Compatibility alias" in content

    assert not (core / "nonlinear.py").is_file()


def test_sha256_helper_is_centralized_outside_tests():
    definitions: list[str] = []
    for path in (PROJECT_ROOT / "src" / "solveur").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and "sha256" in node.name.lower():
                    definitions.append(f"{path.relative_to(PROJECT_ROOT).as_posix()}:{node.name}")
    assert definitions == ["src/solveur/io/manifest.py:sha256"]


def _solveur_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names if alias.name.startswith("solveur."))
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("solveur."):
            imports.append(node.module)
    return imports
