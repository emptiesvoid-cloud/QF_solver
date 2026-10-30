# Dependency and change-impact map

**Scope:** source-supported relationships useful for review planning, not a guarantee that every listed change alters every consumer.
**Revision:** 2026-10-25.

“Direct” means the consumer calls or receives the component in the checked source route. “Potential” means a shared representation or dispatch boundary could affect it and needs a targeted review. Import relationships alone do not prove a mechanical effect.

| Changed component | Relationship | Consumers to inspect | Relevant test/evidence entry points |
|---|---|---|---|
| [modal_basis_numerics.py](../../src/solveur/core/analyses/modal_basis_numerics.py) | Direct | [modal_basis.py](../../src/solveur/core/analyses/modal_basis.py); basis projection and normalization | [modal basis test](../../tests/unit/test_modal_basis_damping.py), WP04 contract/report |
| Modal basis | Direct | [reduced harmonic](../../src/solveur/core/analyses/reduced_harmonic.py) and [modal Newmark](../../src/solveur/core/analyses/modal_newmark.py) consume prepared basis/operators | [reduced harmonic test](../../tests/unit/test_reduced_harmonic.py), [modal Newmark test](../../tests/unit/test_modal_newmark.py); WP05/WP06 contracts |
| Prepared dynamic system | Direct | Excitation binding, modal basis, reduced harmonic, modal Newmark | [prepared system test](../../tests/unit/test_prepared_dynamic_system.py), [excitation test](../../tests/unit/test_excitation_channels.py); WP02/WP03 |
| Excitation and phase channels | Direct | Reduced harmonic, modal Newmark, base acceleration preparation | [excitation test](../../tests/unit/test_excitation_channels.py), [base acceleration test](../../tests/unit/test_wp07_uniform_base_acceleration.py) |
| Uniform base acceleration | Direct | Router-approved modal-superposition harmonic and modal-Newmark routes | [router](../../src/solveur/core/router.py), WP07 contract/report and route tests |
| Dynamic stress recovery | Direct | Modal transient post-processing and supported solid stress outputs | [D02 test](../../tests/unit/test_wp_d02_dynamic_stress.py); D02 bounded closure record |
| Constitutive state/tangent | Direct | Nonlinear element response, global residual/tangent, state transactions | J2, nonlinear transaction/checkpoint and route tests; WP08–WP10/E01 records |
| Shared [assembly](../../src/solveur/core/assembly/assembler.py) or [DOF map](../../src/solveur/core/dofs.py) | Potential, often direct within a selected solver | Static/modal/dynamic/nonlinear routes; contact; constraints and RBE | Element, assembly, RBE, and route tests selected by modified assembly path |
| [MaterialFactory](../../src/solveur/materials/factory.py), [ElementRegistry](../../src/solveur/elements/registry.py), and [compatibility preflight](../../src/solveur/compatibility/preflight.py) | Direct | JSON/API material construction, element assembly, load integration, nonlinear state creation, and post-processing | Material/element tests, compatibility matrix and route-specific tests; descriptor declarations alone do not establish that a material can be assembled |
| Laminate material axes and ply data | Direct | MITC3/MITC4 shell operators, shell stress recovery, and first-ply failure indicators | [laminate tests](../../tests/unit/test_mitc4_laminate.py), [failure-indicator tests](../../tests/unit/test_composite_failure.py); these do not demonstrate progressive damage |
| [Constraints](../../src/solveur/core/constraints.py) and [RBE transforms](../../src/solveur/core/rbe.py) | Direct where enabled by route | DOF reduction, assembly, solution reconstruction, reactions/output logic | [RBE links](../../tests/unit/test_rbe_links.py), [Code_Aster RBE](../../tests/unit/test_code_aster_rbe.py) and applicable route tests |
| Contact search/contribution | Direct | Contact residual/tangent assembly and contact analysis routes | frictionless/frictional contact tests; C01/C02 contracts and reports |
| [Disk gyro assembly](../../src/solveur/core/assembly/rotating_disk_gyro.py) | Direct | [rotating_modal](../../src/solveur/core/analyses/rotating_modal.py), then Campbell speed sweep | [gyro assembly test](../../tests/unit/test_rotating_disk_gyro.py), [rotating cases](../../tests/unit/test_rotating_modal_cases.py), GYRO contracts |
| [QEP solver](../../src/solveur/core/analyses/qep.py) | Direct | Rotating-modal eigenpairs; Campbell samples through rotating modal | [QEP test](../../tests/unit/test_rotating_qep.py), rotor route tests |
| [Campbell tracking/MAC](../../src/solveur/core/analyses/modal_tracking.py) | Direct | Branch association, lineage, gaps and ambiguity reporting | [Campbell test](../../tests/unit/test_campbell.py); v0.2.11 WP06 records |
| [AnalysisRouter](../../src/solveur/core/router.py) / compatibility preflight | Direct | Analysis selection and refusals; all route entry points | [analysis matrix](../../tests/unit/test_element_analysis_matrix.py), public API and route refusal tests |
| Result DTO or [serialization](../../src/solveur/core/result_serialization.py) | Direct | API consumers, CLI/export, post-processing and saved results | [result serialization](../../tests/unit/test_result_serialization_contracts.py), [public API contract](../../tests/unit/test_public_api_contract.py), overwrite CLI tests |
| Linear solver/backend policy | Potential or direct per route | Applicable static, modal, harmonic, nonlinear and large-model routes | Route-specific backend tests and contracts; do not assume one backend serves every path |
| Optional PETSc/SLEPc backend selection | Direct only on selected routes | Static/modal/transient and specialized large-TET4 paths; direct complex harmonic and inherited rotor QEP have explicit backend restrictions | [modal backend edge tests](../../tests/unit/test_modal_backend_edges.py), backend/large-model contracts; optional dependency presence is not evidence of general MPI scaling |

## Review procedure

1. Trace the concrete call path from the edited module to its consumers in source.
2. Identify shared state or operator identities, not only import edges.
3. Read each consumer’s contract and refusal behavior.
4. Select tests that exercise the edited component and at least one user-facing route where the change crosses a boundary.
5. Determine whether a test is an algebraic check, numerical oracle, integration check, or historical campaign record.
6. Recheck evidence provenance before claiming current-HEAD coverage.

See [ARCHITECTURE.md](ARCHITECTURE.md) for layer locations, [DEVELOPMENT.md](DEVELOPMENT.md) for task entry points, and [TESTING.md](TESTING.md) for test navigation.
