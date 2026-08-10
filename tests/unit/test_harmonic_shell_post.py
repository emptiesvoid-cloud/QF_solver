import numpy as np

from solveur.core.model import FiniteElementModel
from solveur.post.harmonic_shell import HarmonicShellStressPostProcessor


def _shell_patch_model() -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]],
        elements=[{"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "skin"}],
        materials={"skin": {"type": "shell_isotropic", "E": 1000.0, "nu": 0.25, "t": 0.1}},
    )


def test_harmonic_shell_stress_preserves_complex_amplitude_and_phase() -> None:
    model = _shell_patch_model()
    dofs = model.dof_manager()
    response = np.zeros(dofs.ndof, dtype=complex)
    curvature = 1.0e-3 * (1.0 + 1.0j)
    for node, (x, _, _) in enumerate(model.nodes):
        response[dofs.index(node, "RY")] = curvature * x

    processor = HarmonicShellStressPostProcessor()
    result = processor.frequency_results(model, dofs, np.asarray([2.0]), [response])[0]
    top = result["element_results"][0]["shell_faces"][1]["stress"]
    expected_s11 = 1000.0 / (1.0 - 0.25**2) * 0.05 * curvature

    assert np.isclose(top["real"][0], np.real(expected_s11))
    assert np.isclose(top["imag"][0], np.imag(expected_s11))
    assert np.isclose(top["amplitude"][0], np.abs(expected_s11))
    assert np.isclose(top["phase_degrees"][0], 45.0)
    assert result["peak_component"]["component"] == "S11"

    nodal = processor.averaged_nodal_stress(model, dofs, response, 2, face="top")
    np.testing.assert_allclose(nodal[0], expected_s11)


def test_harmonic_shell_stress_rejects_unknown_face() -> None:
    model = _shell_patch_model()
    dofs = model.dof_manager()
    response = np.zeros(dofs.ndof, dtype=complex)

    with np.testing.assert_raises_regex(ValueError, "top.*bottom"):
        HarmonicShellStressPostProcessor().averaged_nodal_stress(
            model,
            dofs,
            response,
            0,
            face="middle",
        )
