# Testing and verification navigation

**Scope:** how to find relevant checks; no claim that listed tests have run on the current checkout.
**Revision:** 2026-10-25.

## Repository layout

- [tests/unit/](../../tests/unit/) contains focused component and route tests.
- [tests/integration/](../../tests/integration/) exercises public API, CLI, IO, and selected composed workflows.
- [tests/verification/](../../tests/verification/) contains higher-level verification and convergence checks.
- [src/solveur/verification/](../../src/solveur/verification/) contains reusable verification/campaign code; its presence does not mean a campaign was executed.
- [qualification/](../../qualification/) contains release-specific contracts, manifests, decisions, reports, and preserved evidence.
- [scripts/](../../scripts/) and [.github/workflows/](../../.github/workflows/) contain controlled runners and CI workflows.

The test configuration and markers are in pyproject.toml. Tests may be expensive, environment-dependent, externally backed, or evidence-producing. Follow [AGENTS.md](../../AGENTS.md), qualification runner rules, and the applicable Owner authorization. This navigation page does not authorize execution.

## Find tests by domain

| Domain | First test files to inspect |
|---|---|
| Elements | [TET4](../../tests/unit/test_tet4_element.py), [TET10](../../tests/unit/test_tet10_element.py), [HEX8](../../tests/unit/test_hex8_element.py), [HEX20](../../tests/unit/test_hex20_element.py), [WEDGE6](../../tests/unit/test_wedge6_kernel.py), [BEAM2](../../tests/unit/test_beam2_element.py), [MITC3](../../tests/unit/test_mitc3_element.py), [MITC4 dynamics](../../tests/unit/test_mitc4_dynamics.py) |
| Modal basis and dynamic system | [prepared system](../../tests/unit/test_prepared_dynamic_system.py), [excitation channels](../../tests/unit/test_excitation_channels.py), [modal basis/damping](../../tests/unit/test_modal_basis_damping.py) |
| Reduced harmonic / modal Newmark / base acceleration | [reduced harmonic](../../tests/unit/test_reduced_harmonic.py), [modal Newmark](../../tests/unit/test_modal_newmark.py), [base acceleration](../../tests/unit/test_wp07_uniform_base_acceleration.py) |
| D01/D02 | [D01 residual flexibility](../../tests/unit/test_wp_d01_residual_flexibility.py), [D02 stress recovery](../../tests/unit/test_wp_d02_dynamic_stress.py) |
| J2 and nonlinear state | [corrected corotational J2](../../tests/unit/test_corotational_j2_corrected.py), [corotational J2](../../tests/unit/test_corotational_j2.py), [total-Lagrangian J2](../../tests/unit/test_total_lagrangian_j2.py), [state transactions](../../tests/unit/test_nonlinear_state_transaction_contract.py), [nonlinear checkpoints](../../tests/unit/test_nonlinear_checkpoint.py) |
| Contact | [frictionless](../../tests/unit/test_frictionless_contact.py), [frictional](../../tests/unit/test_frictional_contact.py), WPC01/WPC02 tests and [C02 convergence](../../tests/verification/test_wpc02_ar_native_contact_convergence.py) |
| Rotordynamics | [disk gyro](../../tests/unit/test_rotating_disk_gyro.py), [rotating cases](../../tests/unit/test_rotating_modal_cases.py), [QEP](../../tests/unit/test_rotating_qep.py), [preflight](../../tests/unit/test_rotating_modal_preflight.py), [Campbell](../../tests/unit/test_campbell.py), [public API](../../tests/integration/test_rotating_modal_public_api.py) |
| Public API, serialization, CLI and exports | [API contract](../../tests/unit/test_public_api_contract.py), [serialization](../../tests/unit/test_result_serialization_contracts.py), [JSON IO](../../tests/unit/test_json_io.py), [overwrite CLI](../../tests/unit/test_save_result_cli_overwrite.py), [public facade](../../tests/integration/test_public_qf_solver_api.py), [API/CLI](../../tests/integration/test_api_and_cli.py), [exports](../../tests/integration/test_export_formats.py) |
| Constraints / RBE | [RBE links](../../tests/unit/test_rbe_links.py), [Code_Aster RBE comparison](../../tests/unit/test_code_aster_rbe.py) |

Paths above are repository-relative. Confirm current file contents and exact nodeids before selecting any execution.

## Evidence types

- **Unit test:** may check a local formula, invariant, refusal, or implementation behavior; it is not automatically a physical oracle.
- **Analytical reference:** compares selected observables against an independent closed-form result under stated assumptions.
- **Algebraic/invariant check:** checks properties such as symmetry, residuals, energy, or identities; it does not necessarily validate physical modeling.
- **Convergence study:** establishes behavior under a stated mesh/time refinement and observable; one mesh is not convergence evidence.
- **External comparison:** establishes scoped correlation to another implementation, subject to model and observable equivalence; not automatically physical validation.
- **Contract/API test:** checks schema, compatibility, serialization, or refusal behavior, not the science of the result.
- **Campaign/benchmark:** records execution and resources under a manifest; it is not general performance evidence beyond its workload/environment.
- **Historical evidence:** applies to the frozen identity and scope recorded by its manifest/report; it is not a pass on current HEAD.

## Efficient selection

Start from the changed module. Trace callers via [DEPENDENCIES.md](DEPENDENCIES.md), read the relevant contract, and choose the smallest tests that cover the changed component, a consumer boundary, and an independent oracle where the contract requires one. Consult qualification manifests for exact nodes and execution controls. Do not use the number of passing tests as a maturity metric.
