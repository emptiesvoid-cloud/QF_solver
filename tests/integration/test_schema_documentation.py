from pathlib import Path

from solveur.api import load_model


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DOC = PROJECT_ROOT / "docs" / "schema_json.md"
DOCUMENTED_EXAMPLES = [
    "examples/tet4_static.json",
    "examples/tet4_compression.json",
    "examples/tet4_body_force.json",
    "examples/tet4_pressure.json",
    "examples/tet10_static.json",
    "examples/mitc4_shell_static.json",
    "examples/tet4_modal_unit.json",
    "examples/tet4_nonlinear_static.json",
    "examples/tet4_elastoplastic_static.json",
    "examples/tet4_transient_dynamic.json",
    "examples/tet4_dynamic_free_vibration.json",
    "examples/tet4_dynamic_sdof_free_vibration.json",
    "examples/tet4_dynamic_tabulated_load.json",
    "examples/tet4_harmonic_response.json",
    "examples/tet4_harmonic_sdof_response.json",
    "examples/mitc4_harmonic_cantilever.json",
]


def test_schema_doc_references_loadable_official_examples():
    text = SCHEMA_DOC.read_text(encoding="utf-8")
    for relative in DOCUMENTED_EXAMPLES:
        assert relative in text
        model = load_model(PROJECT_ROOT / relative)
        assert model.node_count > 0
        assert model.elements
