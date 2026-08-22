import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAX_SOURCE_LINES = 700


def test_python_source_files_stay_under_700_lines():
    roots = [PROJECT_ROOT / "src" / "solveur"]
    roots.extend(PROJECT_ROOT / name for name in ("scripts", "tests"))
    oversized: list[str] = []
    for root in roots:
        for path in root.rglob("*.py"):
            line_count = sum(1 for _ in path.open(encoding="utf-8"))
            if line_count > MAX_SOURCE_LINES:
                oversized.append(f"{path.relative_to(PROJECT_ROOT)}: {line_count}")
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
