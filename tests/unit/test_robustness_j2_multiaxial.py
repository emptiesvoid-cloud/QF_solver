from solveur.verification.robustness_nonlinear_solids import run_constitutive_paths


def test_j2_multiaxial_paths_cover_unload_reload_and_nonproportional_loading() -> None:
    result = run_constitutive_paths()

    assert result["status"] == "PASS"
    assert {item["id"] for item in result["checks"]} == {
        "traction_unload_reload",
        "pure_shear",
        "non_proportional",
    }
    assert all(item["plastic_max"] > 0.0 for item in result["checks"])
