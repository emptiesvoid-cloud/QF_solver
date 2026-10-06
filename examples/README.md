# QF Solver examples

These maintained inputs illustrate solver routes and mechanical problems.
They are organized by capability rather than release number. An executable
input is not, by itself, a qualification or a physical-validation claim; check
the [capability index](https://emptiesvoid-cloud.github.io/QF_solver/capabilities/)
and the applicable evidence before generalizing a result.

## Start with a linear static case

From the repository root after installing QF Solver:

```bash
qf-solver check-mesh --input examples/tet4_static.json
qf-solver solve --input examples/tet4_static.json --output results/tet4.json
qf-solver inspect --input examples/tet4_static.json --markdown results/tet4_audit.md
```

The [first-calculation guide](https://emptiesvoid-cloud.github.io/QF_solver/getting-started/quickstart/)
covers the CLI and public Python API. For a small nonlinear illustration,
follow the separate [Total-Lagrangian TET4 example](https://emptiesvoid-cloud.github.io/QF_solver/getting-started/nonlinear-example/);
its engineering-profile `WARNING` is part of the documented outcome.

## Find an example by problem

| Problem family | Example inputs | Scope notes |
| --- | --- | --- |
| Linear solid statics | `tet4_static.json`, `tet10_static.json`, `tet4_compression.json`, `tet4_body_force.json`, `tet4_pressure.json`, `tet4_orthotropic_static.json`, `tet10_orthotropic_static.json` | Check the element, material, loading and result scope in the capability records. |
| Modal analysis | `tet4_modal_unit.json`, `tet4_orthotropic_modal.json`, `mitc3_modal_cantilever.json`, `mitc4_modal_cantilever.json` | Family and mass-formulation maturity vary; the MITC4 modal historical issue remains documented. |
| Transient and harmonic dynamics | `tet4_transient_dynamic.json`, `tet4_dynamic_free_vibration.json`, `tet4_dynamic_sdof_free_vibration.json`, `tet4_dynamic_tabulated_load.json`, `tet4_harmonic_response.json`, `tet4_harmonic_sdof_response.json`, `mitc3_newmark_cantilever.json`, `mitc3_laminate_harmonic.json`, `mitc4_newmark_cantilever.json`, `mitc4_harmonic_cantilever.json` | Linear dynamics, timestep, mass, damping and mixed-family limitations apply. |
| Beams, shells and laminates | `beam2_cantilever.json`, `mitc3_shell_static.json`, `mitc3_laminate_harmonic.json`, `mitc4_shell_static.json`, `mitc4_laminate_static.json`, `mitc4_dynamic_multicomponent.json` | Element routes do not have identical analysis maturity. |
| Material and geometric nonlinearity | `tet4_elastoplastic_static.json`, `tet4_nonlinear_static.json`, `tet4_geometric_nonlinear_static.json`, `hex8_g06_j2.json`, `hex20_g06_j2.json` | These cases do not establish arbitrary J2, coupled, finite-strain or high-order nonlinear behavior. |
| Constraints and contact | `rbe2_rigid_arm.json`, `frictionless_contact_plane.json`, `frictionless_contact_surface.json`, `frictional_contact_plane.json` | Contact is bounded; frictional current-source formal requalification and general finite sliding are not claimed. |
| Linear buckling | `tet4_linear_buckling.json` | Linearized buckling is not postbuckling analysis. |
| Rotating modal and Campbell | See the [rotating-modal guide](https://emptiesvoid-cloud.github.io/QF_solver/mechanics/rotating-modal/), [Campbell guide](https://emptiesvoid-cloud.github.io/QF_solver/mechanics/campbell/) and [0.2.11 verification summary](https://emptiesvoid-cloud.github.io/QF_solver/verification/0_2_11/). | Experimental bounded BEAM2/disk route. The repository currently has no curated standalone JSON input for this API workflow. |
| Controlled verification fixtures | `tet4_g06_analytic.json`, `tet10_g06_analytic.json`, `hex8_g06_analytic.json`, `hex20_g06_analytic.json` | Read the associated contract and provenance; a fixture is not a general user benchmark. |
| Input rejection | `invalid_inverted_tet4.json` | Intentionally invalid; use it to inspect mesh-validation diagnostics, not to solve. |

Other inputs cover orthotropy, laminate response, springs, tabulated loads and
additional controlled cases. The [elements map](https://emptiesvoid-cloud.github.io/QF_solver/elements/),
[analysis index](https://emptiesvoid-cloud.github.io/QF_solver/analyses/) and
[technical limitations](https://emptiesvoid-cloud.github.io/QF_solver/etat/limites/)
explain how to select and interpret a route.

## Inspect a result

The public Python workflow uses the `qf_solver` namespace:

```python
from qf_solver import check_mesh, load_model, solve_model

model = load_model("examples/tet4_static.json")
report = check_mesh(model)
if report.status == "FAIL":
    raise RuntimeError(report.errors)
result = solve_model(model)
print(result.to_dict()["status"])
```

Inspect residuals, reactions and route-specific diagnostics in addition to
the solve status. The integration suite exercises a maintained subset of
these inputs; it does not qualify every example or every possible model:

```bash
python -m pytest tests/integration/test_examples.py
```

Larger documentation models are generated by the controlled documentation
workflow rather than maintained as a second hand-edited example collection.
Their manifests and applicable evidence are linked from the
[documentation site](https://emptiesvoid-cloud.github.io/QF_solver/).
