import numpy as np

from solveur.core.model import FiniteElementModel
from solveur.post.audit import PostProcessingAuditor
from solveur.post.stress import StressPostProcessor


def shell_patch_model():
    return FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]],
        elements=[{"type": "MITC4", "nodes": [0, 1, 2, 3], "material": "skin"}],
        materials={"skin": {"type": "shell_isotropic", "E": 1000.0, "nu": 0.25, "t": 0.1}},
    )


def test_mitc4_shell_resultants_for_affine_membrane_field():
    model = shell_patch_model()
    dofs = model.dof_manager()
    displacement = np.zeros(dofs.ndof)
    exx = 1.0e-3
    eyy = -2.0e-3
    gxy = 5.0e-4
    for node, (x, y, _) in enumerate(model.nodes):
        displacement[dofs.index(node, "UX")] = exx * x + 0.5 * gxy * y
        displacement[dofs.index(node, "UY")] = 0.5 * gxy * x + eyy * y
    result = StressPostProcessor().element_results(model, dofs, displacement)[0]
    assert result["type"] == "MITC4"
    assert np.allclose(result["membrane_strain"], [exx, eyy, gxy])
    assert np.allclose(result["curvature"], [0.0, 0.0, 0.0])
    assert np.allclose(result["shear_strain"], [0.0, 0.0])
    assert np.linalg.norm(result["membrane_force"]) > 0.0
    assert len(result["shell_faces"]) == 2
    assert len(result["integration_points"]) == 1
    assert len(result["nodal_results"]) == 4
    assert result["nodal_results"][0]["shell_top_von_mises"] >= 0.0
    assert np.allclose(result["shell_faces"][0]["stress"], result["shell_faces"][1]["stress"])
    audit = PostProcessingAuditor().element_audits(model, dofs, displacement, [result])[0]
    assert audit["calculation_frame"] == "mitc4_midplane_local"
    assert len(audit["global_dof_displacement"]) == 24
    assert len(audit["calculation_displacement"]) == 24
    assert np.allclose(audit["membrane_strain"], [exx, eyy, gxy])
    assert "membrane_force" in audit


def test_mitc4_shell_face_results_for_bending_field():
    model = shell_patch_model()
    dofs = model.dof_manager()
    displacement = np.zeros(dofs.ndof)
    for node, (x, _, _) in enumerate(model.nodes):
        displacement[dofs.index(node, "RY")] = 1.0e-3 * x
    result = StressPostProcessor().element_results(model, dofs, displacement)[0]
    bottom, top = result["shell_faces"]
    assert bottom["face"] == "bottom"
    assert top["face"] == "top"
    assert bottom["von_mises"] >= 0.0
    assert top["von_mises"] >= 0.0
    assert not np.allclose(bottom["stress"], top["stress"])
