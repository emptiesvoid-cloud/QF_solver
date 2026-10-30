# Proposed benchmark and experiment catalog

**Status:** PREPARATION_ONLY — all cases NOT_RUN for this plan.
**Execution status:** NUMERICAL_EXECUTION_NOT_PERFORMED.
**WP12:** OPEN.

The cases below are a future V&V design, not recorded results. “Existing test” means a source node exists; its presence is not a claim of execution on the frozen candidate. A future policy and Owner decision must authorize an exact scope before the listed command is used.

Recommended first local sequence, matching the Owner decision proposal: (1) ALG-PROJ-001, (2) MODAL-DISCRETE-001, (3) MODAL-2DOF-001, (4) DYN-SDOF-001, then (5) STAT-BEAM-001 after resolving its parameter suffix and (6) FEM-TET4-H-001 after fixing its plan, output root and criteria. Only ALG-PROJ-001 is algebraic-only; cases 2–4 invoke analysis routes. The catalog sections below are grouped by topic and are not themselves an execution order. The existing 2-DOF test is same-backend consistency unless an independently derived scalar characteristic-polynomial oracle is added and reviewed.

## Standard case record

Each case records purpose, formulation/domain, model, oracle, method, observables, acceptance, dependencies, cost, current test status, and exclusions. Exact contract thresholds apply only when the test, domain, observable, and convention match. Missing criteria remain CRITERION_TO_REVIEW.

## First campaign candidates

### ALG-PROJ-001 — structured symmetric modal projection

- **Purpose/domain:** Verify the symmetric projected stiffness computation against the dense bilinear form for a symmetric input. Algebraic implementation check for the WP04 projection path; it is not an FEM or modal validation.
- **Model/oracle:** Test-owned matrices and basis; dense Phi-transpose K Phi provides the explicit comparison oracle.
- **Source/test/contract:** `src/solveur/core/analyses/modal_basis_numerics.py`; `tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form`; WP04 contract `../wp04_modal_basis_damping_contract.json`.
- **Method/measure:** Run only the exact nodeid; record source and test hashes; retain the test’s comparison and refusal assertions.
- **Acceptance:** Existing assertion is the criterion; do not add a new tolerance. Check the WP04 symmetry branch behavior in its other four tests as a separate approved scope.
- **Status/cost:** EXISTING_TEST; low.
- **Command proposal:** `python -m pytest -q tests/unit/test_modal_symmetric_projection.py::test_structured_symmetric_projection_matches_dense_bilinear_form`
- **Risks/exclusions:** Uses an algebraic fixture, not independent physical data; no solve of a structural model.

### MODAL-DISCRETE-001 — spring-mass natural frequency

- **Purpose/domain:** Check discrete spring/mass assembly and modal frequency against a closed-form eigenfrequency.
- **Model/oracle:** Existing scalar/small model in the test; omega equals sqrt(k/m) under its documented constraints and units.
- **Source/test/contract:** `src/solveur/elements/discrete.py`; `tests/unit/test_discrete_entities.py::test_spring_mass_frequency_matches_closed_form`; shared contracts `../wp01_shared_contracts.md`.
- **Method/measure:** Exact node only. Record natural frequency, units, effective k and m, and mode normalization if exposed.
- **Acceptance:** Existing test assertion. No new tolerance proposed.
- **Status/cost:** EXISTING_TEST; low.
- **Command proposal:** `python -m pytest -q tests/unit/test_discrete_entities.py::test_spring_mass_frequency_matches_closed_form`
- **Risks/exclusions:** Small discrete model does not qualify continuum elements or every mass/spring connection.

### STAT-BEAM-001 — Timoshenko cantilever reference

- **Purpose/domain:** Check the BEAM2 static cantilever response in the test’s Timoshenko regime.
- **Model/oracle:** Existing Timoshenko analytical tip response; finite-element interpolation and shear regime must match the test contract.
- **Source/test/contract:** `src/solveur/elements/beam/beam2.py`; test function `tests/unit/test_beam2_element.py::test_beam2_cantilever_matches_timoshenko_tip_solution`; read `tests/unit/test_beam2_element.py` for parameter IDs before freezing a nodeid.
- **Method/measure:** Resolve its parameter suffix during a later approved static source/collection workflow; record geometry, section, loads, units, tip displacement, reaction and energy if asserted.
- **Acceptance:** Existing assertion only; any additional observable is CRITERION_TO_REVIEW.
- **Status/cost:** PARTIAL_COVERAGE; low.
- **Command proposal:** Not exact until the parameter suffix is established. Do not use the unparameterized function target as a final manifest nodeid.
- **Risks/exclusions:** A one-element/reference case does not prove mesh convergence or all slenderness regimes.

### FEM-TET4-H-001 — representative multi-mesh static convergence

- **Purpose/domain:** Demonstrate a real spatial refinement trend for a finite, smooth static observable on a TET4 cantilever/block, with fixed boundary, load resultants, units and sampling.
- **Model/oracle:** Prefer a reference with a known regime and quantify reference error separately from discretization. Keep stress probes away from singular supports/load edges or use a fixed finite sampling region.
- **Source/test/contract:** The runnable multi-level utility is `src/solveur/verification/tet4_structured_convergence.py::run_structured_tet4_study`, exported by `src/solveur/api/__init__.py`; planning tests are `tests/unit/test_tet4_structured_convergence.py`. Related historical/verification candidates include `tests/verification/test_wp04_c_tet4_structural.py` and `tests/verification/test_tet10_structural_convergence_vnv.py`. The utility defaults to a large four-level sequence, so an explicitly smaller plan is needed for the proposed local case.
- **Method/measure:** Fix nested mesh levels, DOF count, solver, load resultant, tip displacement, reactions, energy, and the observable at each level. Capture raw per-level data.
- **Acceptance:** Use the exact bound and observable in the selected contract/report, or mark CRITERION_TO_REVIEW. Do not invent an order or error threshold.
- **Status/cost:** EXISTING_BENCHMARK; the public utility can run the study, but no approved local parameter set or exact pytest campaign node is selected; medium. A dedicated test wrapper may still be useful for durable nodeid-based execution.
- **Command proposal:** `python -c "from solveur.api import StructuredTet4ConvergencePlan, run_structured_tet4_study; run_structured_tet4_study('qualification/0_2_12/wp12_local_vv_evidence/TET4-H-001/run-001', plan=StructuredTet4ConvergencePlan(base_nx=2, base_ny=1, base_nz=1, refinement_factors=(1, 2, 4)), solver_backend='matrix_free')"` — proposed only; the output root and parameters require Owner approval. The utility has implementation defaults for relative-error and residual limits; those defaults must be reviewed as acceptance criteria before interpreting its internal PASS/FAIL. `test_timoshenko_reference_and_convergence_metrics` only checks reference/metric logic and is not evidence that a mesh study ran.
- **Risks/exclusions:** Cost scales with mesh levels and solver; no stress convergence at mathematical singularities; does not imply other element families converge.

### MODAL-2DOF-001 — coupled analytical eigenproblem

- **Purpose/domain:** Check eigenvalues, mass normalization and projected operators for a coupled two-DOF modal system.
- **Model/oracle:** The existing test uses SciPy `eigh` for expected eigenvalues, while the production route uses SciPy `eigh` as well. This is a same-backend consistency check, not an independent eigenvalue oracle. To claim an independent oracle, derive the coefficients of `det(K − lambda M)=a lambda^2+b lambda+c` from the fixed 2×2 input matrices and evaluate its quadratic roots independently, or add an equivalent scalar-formula assertion in a future approved change.
- **Source/test/contract:** `src/solveur/core/analyses/modal_basis.py`; `tests/unit/test_modal_basis_damping.py::test_analytical_coupled_two_dof_eigenproblem_and_projected_operators`; `../wp04_modal_basis_damping_contract.json`.
- **Method/measure:** Exact node only; record eigenvalues/frequencies, residual, orthogonality, basis identity, and K/M projected operators.
- **Acceptance:** Existing test assertions and frozen WP04 criteria; do not claim independent validation until the separate characteristic-polynomial oracle is implemented and reviewed. Related tolerances are listed in the contract, not redefined here.
- **Status/cost:** EXISTING_TEST; low.
- **Command proposal:** `python -m pytest -q tests/unit/test_modal_basis_damping.py::test_analytical_coupled_two_dof_eigenproblem_and_projected_operators`
- **Risks/exclusions:** A 2-DOF oracle does not validate sparse large-scale eigensolvers or continuum modal accuracy.

### DYN-SDOF-001 — undamped free vibration with modal Newmark

- **Purpose/domain:** Check initial projection and modal Newmark time stepping for an undamped single-degree oscillator.
- **Model/oracle:** Closed-form u(t)=u0 cos(omega t) + v0 sin(omega t)/omega.
- **Source/test/contract:** `src/solveur/core/analyses/modal_newmark.py`; `tests/unit/test_modal_newmark.py::test_sdof_free_undamped_matches_analytic_solution_and_initial_projection`; `../wp06_modal_newmark_contract.json`.
- **Method/measure:** Exact node; retain timestep, initial state, time history and the test’s error measure.
- **Acceptance:** Frozen assertion/criterion from WP06; temporal refinement is a separate node and campaign.
- **Status/cost:** EXISTING_TEST; low.
- **Command proposal:** `python -m pytest -q tests/unit/test_modal_newmark.py::test_sdof_free_undamped_matches_analytic_solution_and_initial_projection`
- **Risks/exclusions:** Does not establish nonlinear transient, arbitrary forcing, or mesh/time joint convergence.

## Further cases by family

### ELM-PATCH-001 — affine element/solid patch

- **Purpose/domain:** Check shape functions, Jacobian validity, rigid modes, and constant-strain reproduction for selected TET4/TET10/HEX8/HEX20/WEDGE6 kernels.
- **Oracle:** Affine displacement field yields its constant small strain; algebraic rigid modes and geometry identities are independently calculated.
- **Entry points:** `tests/unit/test_tet10_element.py::test_tet10_patch_test_reproduces_affine_strain_and_energy`; `tests/unit/test_hex8_element.py::test_hex8_affine_field_has_constant_strain_at_all_gauss_points`; `tests/unit/test_hex20_element.py::test_hex20_affine_field_is_exact_at_all_gauss_points`; `tests/unit/test_wedge6_kernel.py::test_constant_strain_tension_compression_and_shear`.
- **Acceptance/status/cost:** Use each test’s own assertions; EXISTING_TEST; low per element. This is element-level verification, not a general assembly benchmark.

### ELM-SHELL-001 — MITC3/MITC4 basic invariants

- **Purpose/domain:** Verify shell kinematics, rigid motion, assumed strain, mass, and shell-specific dynamic condensation in the declared element scope.
- **Entry points:** `tests/unit/test_mitc3_element.py::test_membrane_affine_field_is_recovered_exactly`; `tests/unit/test_mitc3_element.py::test_expanded_operator_reproduces_constant_bending_exactly`; `tests/unit/test_mitc4_dynamics.py::test_mitc4_modal_solver_returns_physical_modes_and_reduction_audit`.
- **Acceptance/status/cost:** Criteria belong to their contracts/review records; PARTIAL_COVERAGE; low to medium. Shell laminate assemblies and larger mesh behavior require distinct cases.

### DYN-DIRECT-001 — direct Newmark SDOF

- **Purpose/domain:** Independently check full-order Newmark against a closed-form oscillator under a frozen load and damping model.
- **Entry points:** `tests/unit/test_dynamic_controls.py::test_multicomponent_newmark_response_obeys_superposition` is a linearity check, not the analytic oracle; select a direct Newmark analytic test only after verifying its exact file/node. Existing verification sources include `src/solveur/verification/code_aster_beam2_newmark.py`.
- **Acceptance/status/cost:** CRITERION_TO_REVIEW for a dedicated exact analytic direct-route case; NEW_TEST_REQUIRED or exact existing-node discovery; low.

### HARM-REDUCED-001 — reduced complex response

- **Purpose/domain:** Verify modal impedance, amplitude/phase, resonance refusal, truncation diagnostics, and the restricted full-basis comparison.
- **Entry points:** `tests/unit/test_reduced_harmonic.py::test_reduced_impedance_matches_independent_analytical_sdof_amplitude_and_phase`; `tests/unit/test_reduced_harmonic.py::test_full_basis_reduced_harmonic_matches_direct_rayleigh_route_and_zero_hz`.
- **Acceptance/status/cost:** WP05 frozen oracle where applicable; EXISTING_TEST; low. The shared operator/assembler means route comparison is not independent physical validation.

### BASE-ACCEL-001 — uniform support acceleration

- **Purpose/domain:** Check full-mass base forcing, signs, frames, relative/absolute response and unavailable reactions on the bounded modal routes.
- **Entry point:** `tests/unit/test_wp07_uniform_base_acceleration.py::test_harmonic_base_sdof_matches_independent_full_free_equation_and_absolute_frames`.
- **Acceptance/status/cost:** WP07 contract; EXISTING_TEST; low. Do not generalize to arbitrary support motion.

### D02-STRESS-001 — dynamic stress recovery

- **Purpose/domain:** Check sign, units, complex phase, complete vs truncated basis behavior, and selected-state recovery for supported solids.
- **Entry point:** `tests/unit/test_wp_d02_dynamic_stress.py::test_tet4_complex_harmonic_stress_matches_independent_affine_reference`.
- **Acceptance/status/cost:** WP-D02 bounded contract and recorded decision; EXISTING_TEST; low to medium. No shells, beams, nonlinear/contact recovery, or universal accuracy claim.

### NL-J2-001 — material-point J2 identities and cyclic history

- **Purpose/domain:** Separate constitutive point updates from assembly/Newton behavior. Check hydrostatic inactivity, pure shear return, and state transaction identities.
- **Entry points:** `tests/unit/test_nonlinear_constitutive_vv.py::test_hydrostatic_loading_does_not_activate_j2`; `tests/unit/test_nonlinear_constitutive_vv.py::test_pure_shear_activates_j2_and_returns_to_the_surface`; `tests/unit/test_nonlinear_checkpoint.py::test_nonlinear_restart_matches_continuous_cyclic_solution`.
- **Acceptance/status/cost:** Existing WP08–WP10 criteria; EXISTING_TEST; low to medium. Does not close the global tangent or arbitrary mesh gaps.

### CONTACT-001 — normal/friction contact identities

- **Purpose/domain:** Check unilateral KKT/equilibrium, Coulomb slip/dissipation, restart and explicit refusals.
- **Entry points:** `tests/unit/test_frictionless_contact.py::test_compression_contact_satisfies_kkt_conditions_and_global_equilibrium`; `tests/unit/test_frictional_contact.py::test_frictional_contact_slides_at_the_coulomb_bound_and_dissipates`; `tests/unit/test_frictional_contact.py::test_updated_search_with_friction_is_explicitly_unsupported`.
- **Acceptance/status/cost:** C01/C02 boundaries remain binding; EXISTING_TEST; medium. Must preserve C01 negative evidence and C02 AR/N03 only. No general finite-slip claim.

### ROTOR-001 — signed-spin QEP and Campbell traceability

- **Purpose/domain:** Check disk gyroscopic matrix, signed-speed term, complex roots/residual, serialization, and branch ambiguity reporting.
- **Entry points:** `tests/unit/test_rotating_disk_gyro.py::test_disk_mass_and_unit_speed_gyro_blocks_match_contract`; `tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual`; `tests/unit/test_rotating_qep.py::test_gyro04_signed_spin_reverses_pencil_term_but_preserves_unordered_frequencies`; `tests/unit/test_campbell.py::test_campbell_sweep_reuses_one_model_and_serializes_complex_source_results`.
- **Acceptance/status/cost:** v0.2.11 contract criteria for historical reproduction; EXPERIMENTAL; medium for the targeted tests, high for full mesh/speed sweeps. The 100 rad/s ambiguity stays visible; tests on the current candidate are not yet run.

### PERF-BASELINE-001 — bounded resource characterization

- **Purpose/domain:** Measure elapsed time, peak memory, matrix nnz, factorization count, and output size on fixed models at a few approved sizes.
- **Entry points:** `tests/unit/test_solver_backend.py::test_linear_solver_resource_estimate_keeps_dense_cost_visible`; `tests/unit/test_newmark_factorization_benchmark.py` is a benchmark test file; nonlinear timing sources include `qualification/0_2_12/wp09_performance_characterization.md` and `wp10_performance_characterization.md`.
- **Acceptance/status/cost:** No general performance threshold is frozen for WP12; EXISTING_CHARACTERIZATION plus new measurement protocol required; medium to high. Freeze machine, repetitions, warm-up, thread controls, and stop criteria before data collection.

## Future command policy

The command strings shown in the first six fiches are examples only. They are not execution authorization. Future use requires Owner acceptance of [LOCAL_VV_POLICY_PROPOSAL.md](LOCAL_VV_POLICY_PROPOSAL.md), exact nodeids, and a separate per-wave decision. Never invoke an entire directory or suite as a substitute for a selected case.
