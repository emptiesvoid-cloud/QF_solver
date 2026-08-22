from solveur.verification.mitc3_curved_axial_audit import build_axial_audit


def _summary(external_name: str, rows: list[dict[str, float]]) -> dict:
    return {"external_solver": {"name": external_name}, "rows": rows}


def test_axial_audit_detects_reproducible_qf_and_external_spread() -> None:
    code_aster = _summary(
        "Code_Aster",
        [
            {
                "nx": 16,
                "ny": 8,
                "mitc3_elements": 256,
                "qf_ux": 1.0e-5,
                "qf_uz": 2.0e-6,
                "code_aster_ux": 1.01e-5,
                "code_aster_uz": 2.01e-6,
                "vector_difference": 0.01,
            }
        ],
    )
    calculix = _summary(
        "CalculiX",
        [
            {
                "nx": 16,
                "ny": 8,
                "mitc3_elements": 256,
                "qf_ux": 1.0e-5,
                "qf_uz": 2.0e-6,
                "calculix_ux": 1.02e-5,
                "calculix_uz": 2.5e-6,
                "vector_difference": 0.2,
            }
        ],
    )
    audit = build_axial_audit(code_aster, calculix)
    assert audit["checks"][0]["status"] == "PASS"
    assert audit["stable_gate_status"] == "BLOCKED_EXTERNAL_FORMULATION_COMPARABILITY"
    assert audit["rows"][0]["qf_cross_reference_relative_difference"] == 0.0


def test_axial_audit_requires_common_mesh() -> None:
    code_aster = _summary("Code_Aster", [{"nx": 8, "ny": 4}])
    calculix = _summary("CalculiX", [{"nx": 16, "ny": 8}])
    try:
        build_axial_audit(code_aster, calculix)
    except ValueError as error:
        assert "common mesh" in str(error)
    else:
        raise AssertionError("missing common mesh must be rejected")
