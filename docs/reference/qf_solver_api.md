---
doc_id: DOC-REF-API-003
revision: 1.0
status: controlled_candidate
applicable_version: 0.2.8
reviewer: ""
approver: ""
---

# `qf_solver` public API contract

This page is the concise contract for the Python surface exported by
`qf_solver`. New integrations should use this namespace. Implementation
modules and private names under `solveur` are not public API.

The contract is additive for the 0.2.x line. A symbol marked `PROVISIONAL` is
importable and supported for the current documented use, but its signature or
result schema may be refined in a later minor release. No symbol in the
`qf_solver` facade is currently marked `DEPRECATED`.

## Primary workflow

The supported model workflow is:

```python
from qf_solver import check_mesh, load_model, save_result, solve_model

model = load_model("examples/tet4_static.json")
report = check_mesh(model)
if report.status == "FAIL":
    raise RuntimeError(report.errors)
result = solve_model(model)
save_result(result, "result.json")
```

### `load_model`

```python
load_model(path: str | Path) -> FiniteElementModel
```

- `path`: JSON model file path, as `str` or `pathlib.Path`.
- Returns a `FiniteElementModel`.
- Raises `InputValidationError` for an unreadable, malformed, duplicate-key,
  or schema-invalid input.
- The reader preserves the documented JSON model schema and does not solve the
  model.
- Stability: `STABLE`.

### `check_mesh`

```python
check_mesh(model: FiniteElementModel) -> MeshReport
```

- `model`: model returned by `load_model` or constructed with the public model
  type.
- Returns a `MeshReport` with `status` equal to `PASS`, `WARNING`, or `FAIL`,
  plus `errors`, `warnings`, and diagnostic `details`.
- Mesh and boundary-condition problems are reported in the result; callers
  should not proceed when `status == "FAIL"`.
- Stability: `STABLE`.

### `solve_model`

```python
solve_model(model: FiniteElementModel, *, enforce_policy: bool = True) -> object
```

- `model`: validated finite-element model.
- `enforce_policy`: when `True` (the default), apply the model's documented
  verification profile before returning the result.
- Returns the analysis result object. Its existing result methods, including
  `to_dict()`, are preserved by the 0.2.x API.
- Raises `InputValidationError` or `MeshValidationError` for invalid input,
  `NumericalConvergenceError` for a failed numerical method, and
  `QualificationGateError` when a completed result is rejected by its active
  verification profile. Runtime/backend failures may raise
  `InfrastructureError`.
- Stability: `STABLE`.

### `save_result`

```python
save_result(result: object, path: str | Path) -> None
```

- `result`: result object returned by `solve_model`.
- `path`: JSON output path, as `str` or `pathlib.Path`.
- Returns `None` after writing a finite JSON result.
- Raises `InputValidationError` when a result exposing `to_dict()` cannot be
  serialized as finite JSON; an object without `to_dict()` is ordinary caller
  misuse and raises `AttributeError`. Filesystem errors remain ordinary
  `OSError` failures.
- Stability: `STABLE`.

## Stability categories

- `STABLE`: intended for new integrations in the 0.2.x compatibility line.
- `PROVISIONAL`: public and tested, but tied to benchmark, V&V, large-model,
  or campaign workflows whose result schemas may evolve.
- `DEPRECATED`: retained for compatibility and not recommended for new code.

The legacy `solveur` top-level namespace, the `solveur-ef` console entry point,
and the `main_solveur.py` launcher are compatibility paths. They are marked for
removal in 0.3.0 by the existing version contract. They are not re-exported as
deprecated symbols from `qf_solver`; use `qf_solver` and `qf-solver` instead.

## Export inventory

The following inventory is generated from the current `qf_solver.__all__`.
The displayed signatures are normative for this development baseline; the
return annotation is the documented return type where one is available.

### Stable symbols

- `__version__` — `str` package version; `STABLE`.
- `assess_result(result: object, model: FiniteElementModel | None = None) -> dict[str, object]` — return a non-raising qualification summary; `STABLE`.
- `ExitCode(*values)` — stable CLI exit-code enum; `STABLE`.
- `InfrastructureError` — missing runtime, dependency, or external backend; `STABLE`.
- `InputValidationError` — invalid input file or schema; `STABLE`.
- `MeshValidationError` — invalid mesh, connectivity, or boundary conditions; `STABLE`.
- `NumericalConvergenceError(message: str, *, reason: NonlinearFailureReason | None = None, diagnostics: dict[str, Any] | None = None) -> None` — numerical failure with diagnostics; `STABLE`.
- `QualificationGateError(message: str, *, result: object | None = None, summary: dict[str, Any] | None = None) -> None` — verification-profile rejection; `STABLE`.
- `RunVerdict(*values)` — stable run-verdict enum; `STABLE`.
- `ConstraintTerm(node: int, dof: str, coefficient: float) -> None` — one linear-constraint term; `STABLE`.
- `FiniteElementModel(nodes: np.ndarray, elements: list[ElementDefinition], materials: dict[str, dict[str, Any]], fixed_dofs: list[BoundaryCondition] = <factory>, loads: list[NodalLoad] = <factory>, distributed_loads: list[DistributedLoad] = <factory>, springs: list[SpringDefinition] = <factory>, concentrated_masses: list[ConcentratedMass] = <factory>, multipoint_constraints: list[LinearConstraint] = <factory>, rbe2: list[Rbe2Definition] = <factory>, rbe3: list[Rbe3Definition] = <factory>, contacts: list[FrictionlessContact] = <factory>, analysis: AnalysisSettings = <factory>, schema_version: int = 1, units: dict[str, str] = <factory>, verification_profile: str = 'engineering') -> None` — in-memory model; `STABLE`.
- `LinearConstraint(terms: tuple[ConstraintTerm, ...], value: float = 0.0, name: str = '') -> None` — linear multi-point constraint; `STABLE`.
- `Rbe2Definition(master: int, slaves: tuple[int, ...], tie_rotations: bool = False, name: str = '') -> None` — rigid-body RBE2 definition; `STABLE`.
- `Rbe3Definition(reference: int, independents: tuple[tuple[int, float], ...], dofs: tuple[str, ...] = ('UX', 'UY', 'UZ', 'RX', 'RY', 'RZ'), mode: str = 'rigid_body_projection', name: str = '') -> None` — weighted RBE3 definition; `STABLE`.
- `MeshQualityThresholds(tet_min_signed_volume: float = 1e-14, tet_min_quality: float = 0.05, tet_min_radius_ratio: float = 0.05, tet_max_aspect_ratio: float = 20.0, tet_min_relative_volume: float = 0.0001, tet10_max_mid_edge_deviation_ratio: float = 0.05, tet10_min_sampled_jacobian: float = 1e-14, tet10_min_jacobian_ratio: float = 0.05, mitc4_max_aspect_ratio: float = 10.0, mitc4_max_planarity_ratio: float = 0.001, mitc4_min_angle_degrees: float = 30.0, mitc4_max_angle_degrees: float = 150.0, mitc4_max_warpage_degrees: float = 5.0, mitc3_max_aspect_ratio: float = 10.0, mitc3_min_angle_degrees: float = 20.0, mitc3_max_angle_degrees: float = 140.0, mitc3_min_relative_area: float = 1e-08) -> None` — mesh-quality thresholds; `STABLE`.
- `MeshValidator(thresholds: MeshQualityThresholds | None = None) -> None` — reusable validator; `STABLE`.
- `OrthotropicLamina(E1: float, E2: float, nu12: float, G12: float, density: float = 0.0, G13: float | None = None, G23: float | None = None) -> None` — orthotropic lamina material record; `STABLE`.
- `check_mesh(model: FiniteElementModel) -> MeshReport` — mesh and model consistency report; `STABLE`.
- `import_gmsh_model(mesh_path: str | Path, setup_path: str | Path, *, repair_tetra_orientation: bool = False) -> GmshImportResult` — import MSH 4.1 plus setup; `STABLE`.
- `inspect_model(model: FiniteElementModel, *, detail: str = 'summary') -> SolverAudit` — white-box model audit; `STABLE`.
- `list_methods() -> dict[str, tuple[str, ...]]` — list available analysis methods; `STABLE`.
- `load_model(path: str | Path) -> FiniteElementModel` — load a JSON finite-element model; `STABLE`.
- `save_audit_markdown(result_or_audit: object, path: str | Path) -> None` — write an audit report; `STABLE`.
- `save_evidence(model: FiniteElementModel, result: object, directory: str | Path, *, input_path: str | Path | None = None) -> dict[str, Path]` — write a reproducible evidence bundle; `STABLE`.
- `save_model(model: FiniteElementModel, path: str | Path) -> None` — write strict model JSON; `STABLE`.
- `save_result(result: object, path: str | Path) -> None` — write result JSON; `STABLE`.
- `save_result_csv(result: object, directory: str | Path, model: FiniteElementModel | None = None) -> dict[str, Path]` — write result tables; `STABLE`.
- `save_result_vtu(result: object, model: FiniteElementModel, path: str | Path) -> None` — write an ASCII VTU result; `STABLE`.
- `solve_model(model: FiniteElementModel, *, enforce_policy: bool = True) -> object` — solve through the public router; `STABLE`.
- `verify_evidence(path: str | Path) -> EvidenceVerificationReport` — verify evidence fingerprints; `STABLE`.

### Provisional symbols

The following symbols are public but scoped to large-model, benchmark,
campaign, profiling, or V&V workflows. Their signatures and current return
types are explicit below; their result schemas are not a general solver
stability guarantee. They may raise the stable typed errors above, plus
workflow-specific `OSError`, `ValueError`, or backend errors when an external
tool or artifact is unavailable.

- `analyze_large_scaling(benchmark_paths: tuple[str | Path, ...], output_dir: str | Path, *, mode: str, weak_work_tolerance: float = 0.1, efficiency_warning_threshold: float = 0.6) -> dict[str, object]` — large scaling analysis; `PROVISIONAL`.
- `analyze_petsc_tuning(benchmark_paths: tuple[str | Path, ...], output_dir: str | Path, *, topologies: tuple[str, ...], presets: tuple[str, ...], displacement_tolerance: float = 1e-08) -> dict[str, object]` — PETSc tuning comparison; `PROVISIONAL`.
- `StructuredTet4ConvergencePlan(base_nx: int = 20, base_ny: int = 4, base_nz: int = 4, refinement_factors: tuple[int, ...] = (1, 2, 4, 8), decomposition: str = 'six', load_distribution: str = 'tributary') -> None` — structured TET4 study plan; `PROVISIONAL`.
- `benchmark_large_model(input_path: str | Path, output_dir: str | Path, *, solver_backend: str = 'scipy', preconditioner: str | None = None, chunk_size: int = 4096, matrix_format: str = 'baij', partition_strategy: str = 'contiguous', graph_partitioner: str = 'ptscotch', restart_from: str | Path | None = None) -> dict[str, object]` — large-model benchmark; `PROVISIONAL`.
- `collect_large_runtime_environment(metadata: dict[str, object] | None = None) -> dict[str, object]` — runtime metadata; `PROVISIONAL`.
- `check_large_readiness(output_dir: str | Path, *, target_dofs: int = 1000000, nx: int | None = None, ny: int | None = None, nz: int | None = None, solver_backend: str = 'petsc', chunk_size: int = 4096, memory_budget_bytes: int | None = None) -> dict[str, object]` — large-run readiness report; `PROVISIONAL`.
- `convert_model_to_large(input_path: str | Path, output_path: str | Path) -> LargeModel` — convert a model to large-model storage; `PROVISIONAL`.
- `generate_large_tet4_block(path: str | Path, *, nx: int, ny: int, nz: int, **kwargs: object) -> LargeModel` — generate a large TET4 block; `PROVISIONAL`.
- `generate_large_tet4_cantilever(path: str | Path, *, nx: int, ny: int, nz: int, **kwargs: object) -> LargeModel` — generate a large TET4 cantilever; `PROVISIONAL`.
- `inspect_large_model(model: LargeModel) -> LargeAuditReport` — audit large-model structure; `PROVISIONAL`.
- `import_cantilever_vnv_study(output_dir: str | Path, *, source_dir: str | Path | None = None, overwrite: bool = False) -> Path` — import controlled cantilever V&V artifacts; `PROVISIONAL`.
- `import_torsion_vnv_study(output_dir: str | Path, *, source_dir: str | Path | None = None, overwrite: bool = False) -> Path` — import controlled torsion V&V artifacts; `PROVISIONAL`.
- `list_benchmarks() -> tuple[BenchmarkDescriptor, ...]` — list benchmark descriptors; `PROVISIONAL`.
- `list_demonstrations(*, family: str | None = None, method: str | None = None, maturity: str | None = None) -> tuple[DemonstrationDescriptor, ...]` — list demonstration descriptors; `PROVISIONAL`.
- `load_large_model(path: str | Path) -> LargeModel` — load large-model storage; `PROVISIONAL`.
- `load_distributed_large_model(path: str | Path, *, partition_strategy: str = 'contiguous', graph_partitioner: str = 'ptscotch') -> object` — load a distributed partition; `PROVISIONAL`.
- `load_mixed_results_hdf5(path: str | Path, *, families: tuple[str, ...] | list[str] | None = None, fields: tuple[str, ...] | list[str] | None = None, region_id: int | None = None) -> dict[str, object]` — read family-aware mixed HDF5 results with optional family, field, and region selectors; `PROVISIONAL`.
- `read_inp(path: str | Path) -> InpImportResult` — import the bounded Abaqus/CalculiX `.inp` subset; `PROVISIONAL`.
- `parse_petsc_log_view(path: str | Path) -> dict[str, object]` — parse PETSc log output; `PROVISIONAL`.
- `postprocess_large_model(model_path: str | Path, displacement_path: str | Path, output_dir: str | Path, *, chunk_size: int = 65536, resume: bool = False, overwrite: bool = False, max_chunks: int | None = None) -> dict[str, object]` — post-process a large result; `PROVISIONAL`.
- `qualify_large_tet4_pipeline(output_dir: str | Path, *, target_dofs: int = 1000000, nx: int | None = None, ny: int | None = None, nz: int | None = None, solver_backend: str = 'petsc', preconditioner: str | None = None, chunk_size: int = 4096, **kwargs: object) -> dict[str, object]` — run the large TET4 qualification pipeline; `PROVISIONAL`.
- `qualification_readiness(scope: str, registry_path: str | Path | None = None) -> QualificationReadiness` — evaluate evidence readiness; `PROVISIONAL`.
- `recommended_large_block(target_dofs: int) -> tuple[int, int, int]` — recommend a large block shape; `PROVISIONAL`.
- `run_large_scale_campaign(output_dir: str | Path, *, targets: tuple[int, ...] = (100000, 1000000, 3000000), solver_backend: str = 'petsc', preconditioner: str | None = None, chunk_size: int = 4096, memory_budget_bytes: int | None = None, execute: bool = False, stop_on_failure: bool = True) -> dict[str, object]` — execute or plan large-scale targets; `PROVISIONAL`.
- `run_large_preconditioner_campaign(input_path: str | Path, output_dir: str | Path, *, preconditioners: tuple[str, ...] = ('gamg', 'hypre'), chunk_size: int = 4096, matrix_format: str = 'baij', displacement_tolerance: float = 1e-08, partition_strategy: str = 'contiguous', graph_partitioner: str = 'ptscotch') -> dict[str, object]` — compare large-model preconditioners; `PROVISIONAL`.
- `run_qualification_campaign(manifest_path: str | Path, output_dir: str | Path) -> dict[str, object]` — execute a qualification manifest; `PROVISIONAL`.
- `run_qualification_case(identifier: str, output_dir: str | Path, *, manifest_path: str | Path = DEFAULT_QUALIFICATION_CAMPAIGN) -> dict[str, object]` — execute one named qualification case; `PROVISIONAL`.
- `run_release_vv(output_dir: str | Path, *, registry_path: str | Path | None = None, execute_campaign: bool = False, campaign_manifest: str | Path | None = None) -> dict[str, object]` — build release V&V readiness artifacts; `PROVISIONAL`.
- `run_benchmark(identifier: str, output_dir: str | Path, *, profile: str = 'engineering') -> BenchmarkRun` — execute one catalogued benchmark; `PROVISIONAL`.
- `run_demonstration(identifier: str, output_dir: str | Path, *, profile: str = 'engineering') -> object` — execute one documented demonstration; `PROVISIONAL`.
- `run_contact_verification(output_dir: str | Path) -> dict[str, object]` — run the contact evidence suite; `PROVISIONAL`.
- `run_linear_solver_verification(output_dir: str | Path) -> dict[str, object]` — run sparse-solver comparisons; `PROVISIONAL`.
- `run_mitc4_validation(output_dir: str | Path, *, quick: bool = False) -> dict[str, object]` — generate MITC4 validation evidence; `PROVISIONAL`.
- `run_torsion_stress_probe(output_dir: str | Path, *, overwrite: bool = False) -> dict[str, object]` — run the controlled torsion stress probe; `PROVISIONAL`.
- `run_structured_tet4_study(output_dir: str | Path, *, plan: StructuredTet4ConvergencePlan | None = None, length: float = 4.0, width: float = 0.4, height: float = 0.4, young: float = 70000000000.0, poisson: float = 0.3, total_load: float = -1.0, relative_limit: float = 0.01, residual_limit: float = 1e-08, chunk_size: int = 8192, maxiter: int = 10000, solver_backend: str = 'matrix_free', preconditioner: str = 'gamg', study_id: str = 'VNV-TET4-STRUCTURED-FLEXION-001', container_image: str | None = None, container_digest: str | None = None) -> dict[str, Any]` — run a structured TET4 V&V study; `PROVISIONAL`.
- `run_vnv_study(study_path: str | Path, output_dir: str | Path) -> VnvStudyRun` — compare normalized study results; `PROVISIONAL`.
- `save_large_readiness(report: dict[str, object], output_dir: str | Path) -> dict[str, Path]` — persist large-readiness artifacts; `PROVISIONAL`.
- `save_large_runtime_environment(output_dir: str | Path, metadata: dict[str, object] | None = None) -> Path` — persist runtime metadata; `PROVISIONAL`.
- `save_large_verification(report: LargeQualificationVerification, *, json_path: str | Path | None = None, markdown_path: str | Path | None = None) -> dict[str, Path]` — persist large qualification verification; `PROVISIONAL`.
- `save_mixed_results_hdf5(path: str | Path, model: object, results: object, *, reactions: object | None = None, source_sha: str, metadata: dict[str, object] | None = None) -> Path` — write family-aware mixed HDF5 results; `PROVISIONAL`.
- `solve_large_model(model: LargeModel, output_dir: str | Path | None = None, *, solver_backend: str = 'scipy', preconditioner: str = 'jacobi', chunk_size: int = 4096, matrix_format: str = 'baij') -> LargeSolveResult` — solve a large-model representation; `PROVISIONAL`.
- `mixed_results_semantic_digest(path: str | Path) -> str` — digest logical family-aware mixed-result content; `PROVISIONAL`.
- `verify_large_qualification(path: str | Path, *, target_dofs: int = 1000000, max_solver_residual: float = 1e-06) -> LargeQualificationVerification` — verify large qualification evidence; `PROVISIONAL`.
- `write_petsc_profile_report(profile_paths: tuple[str | Path, ...], output_dir: str | Path, *, labels: tuple[str, ...] | None = None) -> dict[str, object]` — write PETSc profile reports; `PROVISIONAL`.

## Public CLI boundary

The supported console command is `qf-solver`. It exposes the documented model,
mesh, result, evidence, import, benchmark, V&V, and large-model commands. The
legacy `solveur-ef` entry point and `main_solveur.py` launcher remain available
for 0.2.x compatibility and emit the existing deprecation warning. No CLI
path is promoted to a certification or universal-validation claim by this
contract.

For the overview and compatibility boundary, see
[`api_stability.md`](api_stability.md). The active capability limits remain in
the [0.2.8 consolidated registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/consolidated_registry.json)
and linked mixed-workflow/capability records.

The cross-registry public orientation is maintained by the
[0.2.8 capability index](../capabilities/index.md).
