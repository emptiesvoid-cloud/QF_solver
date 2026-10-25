# Capability map

**Scope:** capability families present in the repository as inspected 2026-10-25.
**Status warning:** implementation presence, tests, and scientific qualification are separate facts. Exact support is model-, route-, backend-, and release-dependent.

For a current maturity index consult [docs/capabilities/index.md](../capabilities/index.md), then verify the applicable source and release-specific contract. Do not infer a Cartesian product of element, material, and analysis support.

## Elements, constraints, and materials

| Group | Repository map | Tests and evidence entry points | Scope notes |
|---|---|---|---|
| Solid elements | TET4, TET10, HEX8, HEX20, WEDGE6 in [elements](../../src/solveur/elements/) | [TET4](../../tests/unit/test_tet4_element.py), [TET10](../../tests/unit/test_tet10_element.py), [HEX8](../../tests/unit/test_hex8_element.py), [HEX20](../../tests/unit/test_hex20_element.py), [WEDGE6](../../tests/unit/test_wedge6_kernel.py) | Supported combinations vary by formulation and route. Do not infer support for WEDGE15 or other absent families. |
| Beam and shells | BEAM2, MITC3, MITC4 in [elements](../../src/solveur/elements/) | [BEAM2](../../tests/unit/test_beam2_element.py), [MITC3](../../tests/unit/test_mitc3_element.py), [MITC4 dynamics](../../tests/unit/test_mitc4_dynamics.py); shell verification under [verification](../../src/solveur/verification/) | Shell material, dynamics, and stress recovery are separately bounded by their contracts. |
| Discrete entities | Masses, springs, and rotating disk entities under [elements](../../src/solveur/elements/) | [disk gyro test](../../tests/unit/test_rotating_disk_gyro.py) and route-specific tests | Rotating disks are accepted only on rotating-modal/Campbell routes by the [router](../../src/solveur/core/router.py). |
| DOFs and rigid constraints | [dofs.py](../../src/solveur/core/dofs.py), [constraints.py](../../src/solveur/core/constraints.py), [rbe.py](../../src/solveur/core/rbe.py) | [RBE links](../../tests/unit/test_rbe_links.py) and route tests | MPC/RBE behavior is a cross-cutting dependency; inspect constraint transformation and selected solver route. |
| Materials | [materials](../../src/solveur/materials/) and element constitutive interfaces | [solid material](../../tests/unit/test_solid_material.py), [composite material](../../tests/unit/test_composite_material.py), orthotropic/J2 tests | Isotropic, orthotropic, and composite/laminate models exist. Constitutive availability does not imply support for all elements or nonlinear routes. |

## Linear and dynamic analysis

| Capability | Main implementation | Evidence navigation | Boundary |
|---|---|---|---|
| Linear static | [static solver](../../src/solveur/core/solvers/static.py), assembly and linear solver layers | Static element tests and release-specific contracts | Results depend on mesh, constraints, material, and backend compatibility. |
| Classical modal | [modal.py](../../src/solveur/core/analyses/modal.py) | Modal tests and relevant release records | Generalized eigenproblem route; distinguish its mass normalization and solver settings from reduced-dynamic basis contracts. |
| Direct harmonic | [harmonic.py](../../src/solveur/core/analyses/harmonic.py) | Harmonic unit/verification tests | Complex frequency response using assembled K, M, and Rayleigh C on the supported route; exact sign, phase and damping conventions are contract-controlled. |
| Direct transient | [dynamic.py](../../src/solveur/core/analyses/dynamic.py) | Dynamic tests and transient contracts | Classical transient route using shared Newmark implementation; not interchangeable with modal Newmark. |
| Linear buckling | [buckling.py](../../src/solveur/core/analyses/buckling.py) | [linear buckling test](../../tests/unit/test_linear_buckling.py) and buckling records | Linearized eigenvalue buckling has its own assumptions and is not general post-buckling. |
| Prepared dynamic system | [prepared_dynamic_system.py](../../src/solveur/core/analyses/prepared_dynamic_system.py) | [WP02 contract](../../qualification/0_2_12/wp02_prepared_dynamic_system_contract.json), [report](../../qualification/0_2_12/wp02_prepared_dynamic_system_report.md), [test](../../tests/unit/test_prepared_dynamic_system.py) | v0.2.12 basis for subsequent dynamic routes; operator identities matter. |
| Excitation channels | [excitation_channels.py](../../src/solveur/core/analyses/excitation_channels.py) | [WP03 contract](../../qualification/0_2_12/wp03_excitation_channels_contract.json), [report](../../qualification/0_2_12/wp03_excitation_channels_report.md), [test](../../tests/unit/test_excitation_channels.py) | Typed excitation preparation with contract-defined units, phase and binding. |
| Modal basis and damping | [modal_basis.py](../../src/solveur/core/analyses/modal_basis.py) | [WP04 contract](../../qualification/0_2_12/wp04_modal_basis_damping_contract.json), [report](../../qualification/0_2_12/wp04_modal_basis_damping_report.md), [test](../../tests/unit/test_modal_basis_damping.py) | Reusable mass-normalized basis; identity binding and normalization are part of its contract. |
| Reduced harmonic | [reduced_harmonic.py](../../src/solveur/core/analyses/reduced_harmonic.py) | [WP05 contract](../../qualification/0_2_12/wp05_reduced_harmonic_contract.json), [report](../../qualification/0_2_12/wp05_reduced_harmonic_report.md), [test](../../tests/unit/test_reduced_harmonic.py) | Explicit modal-superposition route; separate result schema. |
| Modal Newmark | [modal_newmark.py](../../src/solveur/core/analyses/modal_newmark.py) | [WP06 contract](../../qualification/0_2_12/wp06_modal_newmark_contract.json), [report](../../qualification/0_2_12/wp06_modal_newmark_report.md), [test](../../tests/unit/test_modal_newmark.py) | Explicit transient modal route, reusing Newmark core; separate from direct Newmark. |
| Uniform base acceleration | [uniform_base_acceleration.py](../../src/solveur/core/analyses/uniform_base_acceleration.py) | [WP07 contract](../../qualification/0_2_12/wp07_uniform_base_acceleration_contract.json), [report](../../qualification/0_2_12/wp07_uniform_base_acceleration_report.md), [test](../../tests/unit/test_wp07_uniform_base_acceleration.py) | Router currently permits this input only on harmonic modal-superposition and transient modal-Newmark routes. |
| Residual flexibility | [residual_flexibility.py](../../src/solveur/core/analyses/residual_flexibility.py) | [D01 integration report](../../qualification/0_2_12/wp_d01_stable_projection_integration_report.md), [test](../../tests/unit/test_wp_d01_residual_flexibility.py) | WP-D01 is INCONCLUSIVE; do not claim general residual correction verification. |
| Dynamic stress recovery | [dynamic_stress.py](../../src/solveur/post/dynamic_stress.py) | [D02 closure report](../../qualification/0_2_12/wp_d02_bounded_closure_report.md), [test](../../tests/unit/test_wp_d02_dynamic_stress.py) | WP-D02 is CLOSED_BOUNDED within its recorded model/material scope. |

## Nonlinear and contact

| Group | Main implementation / tests | Current evidence boundary |
|---|---|---|
| J2 plasticity | [nonlinear core](../../src/solveur/core/nonlinear/); [corotational J2](../../tests/unit/test_corotational_j2.py), [corrected corotational J2](../../tests/unit/test_corotational_j2_corrected.py), [total-Lagrangian J2](../../tests/unit/test_total_lagrangian_j2.py) | [WP08 constitutive-state contract](../../qualification/0_2_12/wp08_r1_constitutive_state_contract.json) and nonlinear reports define the current scope. Small-strain, total-Lagrangian, and corotational implementations have distinct assumptions. Pointwise checks do not prove a complete FEM chain. |
| Geometric nonlinear routes | [nonlinear core](../../src/solveur/core/nonlinear/) and [geometric nonlinear analysis](../../src/solveur/core/analyses/geometric_nonlinear.py) | Total-Lagrangian and corotational methods are not interchangeable. Deformation, element, and state restrictions are contract-specific. |
| Newton and state | Nonlinear solver, iteration/line-search controls, state transaction and checkpoint modules; test_nonlinear_state_transaction_contract.py, test_nonlinear_checkpoint.py | Iteration controls do not guarantee convergence for arbitrary problems. Checkpoint and rollback behavior have separate contracts. |
| Experimental finite-strain foundations | WP-E01 material and integration work | [WP-E01 integration report](../../qualification/0_2_12/wp_e01_bc_integration_report.md) records OPEN_WITH_BOUNDED_CERTIFICATES; bounded certificates do not qualify a general finite-strain FEM workflow. |
| Contact | [contact implementation](../../src/solveur/contact/); [frictionless test](../../tests/unit/test_frictionless_contact.py), [frictional test](../../tests/unit/test_frictional_contact.py) | [C01 status register](../../qualification/0_2_12/wp_c01_r19_status_register.json) records CLOSED_NEGATIVE with remediation open. [C02 Owner decision](../../qualification/0_2_12/wp_c02_n13_owner_bounded_closure_decision.md) bounds CLOSED_BOUNDED to AR/N03 only. Search, slip, mesh, and route limitations remain explicit. |

## Rotating machinery

| Route | Main implementation | Evidence and maturity |
|---|---|---|
| Rotating modal | [rotating_modal.py](../../src/solveur/core/analyses/rotating_modal.py), [qep.py](../../src/solveur/core/analyses/qep.py), [rotating_disk_gyro.py](../../src/solveur/core/assembly/rotating_disk_gyro.py) | [v0.2.11 WP05 contract](../../qualification/0_2_11/wp05_gyroscopic_contract.json) and [report](../../qualification/0_2_11/wp05_gyroscopic_report.md) record historical GYRO-01–04 evidence; maturity EXPERIMENTAL. |
| Campbell | [campbell.py](../../src/solveur/core/analyses/campbell.py), [modal_tracking.py](../../src/solveur/core/analyses/modal_tracking.py), [Campbell post-processing](../../src/solveur/post/campbell.py) | [v0.2.11 WP06 contract](../../qualification/0_2_11/wp06_campbell_contract.json) and [report](../../qualification/0_2_11/wp06_campbell_report.md) record historical GYRO-05/06 evidence. The 100 rad/s association ambiguity remains; maturity EXPERIMENTAL. |

The bounded model uses straight collinear BEAM2 shafts and centered rigid axisymmetric disks, a dense serial QEP, and explicit signed speed samples. Exclusions include distributed shaft gyros, unbalance forced response, speed-dependent bearings, general rotor damping, centrifugal prestress, sparse QEP, and general rotating-machinery qualification. See [rotating-modal](../mechanics/rotating-modal.md), [Campbell](../mechanics/campbell.md), and the original [WP05 contract](../../qualification/0_2_11/wp05_gyroscopic_contract.json) and [WP06 contract](../../qualification/0_2_11/wp06_campbell_contract.json).

## Interfaces and infrastructure

- **Python API:** [public facade](../../src/qf_solver/__init__.py) and [API implementation](../../src/solveur/api/public.py).
- **CLI:** entry points in [pyproject.toml](../../pyproject.toml); see [API reference](../reference/qf_solver_api.md) and [interfaces](../reference/interfaces.md).
- **Input/output:** JSON model IO, bounded .inp import, Gmsh MSH 4.1 import, CSV/VTU output, and route-specific result serialization. Optional mixed HDF5 is provisional.
- **Results:** route-specific result DTOs and versioned contracts; no universal result schema or generic loader.
- **Sparse and distributed routes:** SciPy sparse/direct/iterative paths are available where routed; PETSc/MPI is limited to selected configurations. Do not generalize its qualification or scaling.
- **Qualification:** contracts, manifests, evidence registries, and controlled runners live in qualification/, src/solveur/verification/, and scripts/.
