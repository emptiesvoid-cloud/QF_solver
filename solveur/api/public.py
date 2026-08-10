"""Stable Python API for loading, checking and solving models."""

from __future__ import annotations

from pathlib import Path

from solveur.benchmarks.runner import BenchmarkRunner
from solveur.benchmarks.demonstrations import DemonstrationDescriptor, DemonstrationRunner
from solveur.benchmarks.types import BenchmarkDescriptor, BenchmarkRun
from solveur.core.analysis import available_methods
from solveur.core.audit import ModelInspector, SolverAudit
from solveur.core.model import FiniteElementModel
from solveur.core.qualification import enforce_qualification_policy, qualification_summary
from solveur.core.router import AnalysisRouter
from solveur.io.audit_markdown import AuditMarkdownWriter
from solveur.io.csv_writer import CsvResultWriter
from solveur.io.evidence_verifier import EvidenceBundleVerifier, EvidenceVerificationReport
from solveur.io.evidence_writer import EvidenceBundleWriter
from solveur.io.json_reader import JsonModelReader
from solveur.io.json_writer import JsonResultWriter
from solveur.io.model_writer import JsonModelWriter
from solveur.io.vtu_writer import VtuResultWriter
from solveur.large.audit import LargeAuditReport
from solveur.large.audit import inspect_large_model as _inspect_large_model
from solveur.large.benchmark import benchmark_large_model as _benchmark_large_model
from solveur.large.campaign import run_large_scale_campaign as _run_large_scale_campaign
from solveur.large.generator import generate_tet4_block as _generate_tet4_block
from solveur.large.distributed_model import load_distributed_large_model as _load_distributed_large_model
from solveur.large.generator import recommended_block_for_dofs as _recommended_block_for_dofs
from solveur.large.io import convert_model_to_large as _convert_model_to_large
from solveur.large.io import load_large_model as _load_large_model
from solveur.large.model import LargeModel
from solveur.large.optimization import analyze_large_scaling as _analyze_large_scaling
from solveur.large.optimization import run_large_preconditioner_campaign as _run_large_preconditioner_campaign
from solveur.large.profiling import parse_petsc_log_view as _parse_petsc_log_view
from solveur.large.profiling import write_petsc_profile_report as _write_petsc_profile_report
from solveur.large.postprocess import postprocess_large_tet4 as _postprocess_large_tet4
from solveur.large.qualification import qualify_large_tet4_pipeline as _qualify_large_tet4_pipeline
from solveur.large.readiness import check_large_readiness as _check_large_readiness
from solveur.large.readiness import write_large_readiness_report as _write_large_readiness_report
from solveur.large.runtime import collect_runtime_environment as _collect_runtime_environment
from solveur.large.runtime import write_runtime_environment as _write_runtime_environment
from solveur.large.solver import LargeSolveResult
from solveur.large.solver import solve_large_model as _solve_large_model
from solveur.large.tuning import analyze_petsc_tuning as _analyze_petsc_tuning
from solveur.large.verification import LargeQualificationVerification
from solveur.large.verification import save_large_verification_report as _save_large_verification_report
from solveur.large.verification import verify_large_qualification as _verify_large_qualification
from solveur.mesh.validation import MeshReport, MeshValidator
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.mesh.gmsh_types import GmshImportResult
from solveur.verification.campaign import QualificationCampaignRunner
from solveur.verification.contact_campaign import ContactVerificationCampaign
from solveur.verification.linear_solver_comparison import write_linear_solver_comparison
from solveur.verification.mitc4_campaign import Mitc4ValidationCampaign
from solveur.verification.traceability import QualificationReadiness
from solveur.verification.traceability import qualification_readiness as _qualification_readiness
from solveur.verification.torsion_stress_probe import TorsionStressProbeRunner
from solveur.verification.vnv_runner import VnvStudyRunner
from solveur.verification.vnv_benchmark_import import CantileverBenchmarkVnvImporter
from solveur.verification.vnv_torsion_import import TorsionBenchmarkVnvImporter
from solveur.verification.vnv_types import VnvStudyRun


DEFAULT_QUALIFICATION_CAMPAIGN = Path(__file__).resolve().parents[2] / "qualification" / "campaign.json"


def load_model(path: str | Path) -> FiniteElementModel:
    """Load a finite element model from a JSON file."""
    return JsonModelReader().read(path)


def import_gmsh_model(
    mesh_path: str | Path,
    setup_path: str | Path,
    *,
    repair_tetra_orientation: bool = False,
) -> GmshImportResult:
    """Import a MSH 4.1 mesh and companion mechanical setup."""
    return GmshModelImporter().import_model(
        mesh_path,
        setup_path,
        repair_tetra_orientation=repair_tetra_orientation,
    )


def check_mesh(model: FiniteElementModel) -> MeshReport:
    """Run mandatory mesh and model consistency checks."""
    return MeshValidator().validate(model)


def inspect_model(model: FiniteElementModel, *, detail: str = "summary") -> SolverAudit:
    """Return a white-box audit of dofs, matrices, loads and constraints."""
    return ModelInspector().inspect(model, detail=detail)


def solve_model(model: FiniteElementModel, *, enforce_policy: bool = True) -> object:
    """Validate and solve a model, enforcing its verification profile by default."""
    result = AnalysisRouter().solve(model)
    return enforce_qualification_policy(result, model) if enforce_policy else result


def run_contact_verification(output_dir: str | Path) -> dict[str, object]:
    """Run the public internal V1 normal and frictional contact evidence suite."""
    return ContactVerificationCampaign(output_dir).run()


def run_linear_solver_verification(output_dir: str | Path) -> dict[str, object]:
    """Run the controlled SPD and nonsymmetric sparse-solver comparison."""
    return write_linear_solver_comparison(output_dir)


def assess_result(result: object, model: FiniteElementModel | None = None) -> dict[str, object]:
    """Return the qualification verdict without raising a policy error."""
    return qualification_summary(result, model)


def save_evidence(
    model: FiniteElementModel,
    result: object,
    directory: str | Path,
    *,
    input_path: str | Path | None = None,
) -> dict[str, Path]:
    """Save a reproducible evidence bundle for one solved model."""
    return EvidenceBundleWriter().write(model=model, result=result, directory=directory, input_path=input_path)


def verify_evidence(path: str | Path) -> EvidenceVerificationReport:
    """Verify an evidence bundle against its manifest fingerprints."""
    return EvidenceBundleVerifier().verify(path)


def save_result(result: object, path: str | Path) -> None:
    """Save a solve result as JSON."""
    JsonResultWriter().write(result, path)


def save_model(model: FiniteElementModel, path: str | Path) -> None:
    """Save a finite-element input model as strict JSON."""
    JsonModelWriter().write(model, path)


def list_benchmarks() -> tuple[BenchmarkDescriptor, ...]:
    """List the controlled, reproducible meshed benchmark catalog."""
    return BenchmarkRunner().list()


def run_benchmark(
    identifier: str,
    output_dir: str | Path,
    *,
    profile: str = "engineering",
) -> BenchmarkRun:
    """Run one catalogued benchmark and persist its traceable artifacts."""
    return BenchmarkRunner().run(identifier, output_dir, profile=profile)


def list_demonstrations(
    *, family: str | None = None, method: str | None = None, maturity: str | None = None
) -> tuple[DemonstrationDescriptor, ...]:
    """List documented demonstrations available from the Python library."""
    return DemonstrationRunner().list(family=family, method=method, maturity=maturity)


def run_demonstration(
    identifier: str, output_dir: str | Path, *, profile: str = "engineering"
) -> object:
    """Run a documented demonstration through its controlled benchmark runner."""
    return DemonstrationRunner().run(identifier, output_dir, profile=profile)


def run_vnv_study(study_path: str | Path, output_dir: str | Path) -> VnvStudyRun:
    """Compare normalized solver results and write a traceable Markdown V&V report."""
    return VnvStudyRunner().run(study_path, output_dir)


def import_cantilever_vnv_study(
    output_dir: str | Path,
    *,
    source_dir: str | Path | None = None,
    overwrite: bool = False,
) -> Path:
    """Create a TET4 cantilever V&V study from controlled benchmark artifacts."""
    return CantileverBenchmarkVnvImporter().import_study(output_dir, source_dir=source_dir, overwrite=overwrite)


def import_torsion_vnv_study(
    output_dir: str | Path,
    *,
    source_dir: str | Path | None = None,
    overwrite: bool = False,
) -> Path:
    """Create a TET4 torsion V&V study from controlled benchmark artifacts."""
    return TorsionBenchmarkVnvImporter().import_study(output_dir, source_dir=source_dir, overwrite=overwrite)


def run_torsion_stress_probe(output_dir: str | Path, *, overwrite: bool = False) -> dict[str, object]:
    """Run the controlled four-times-finer TET4 torsion stress probe."""
    return TorsionStressProbeRunner().run(output_dir, overwrite=overwrite)


def run_mitc4_validation(output_dir: str | Path, *, quick: bool = False) -> dict[str, object]:
    """Generate MITC4 static, modal and Newmark V&V evidence."""
    return Mitc4ValidationCampaign(output_dir, quick=quick).run()


def save_audit_markdown(result_or_audit: object, path: str | Path) -> None:
    """Save a white-box audit or audited result as a Markdown report."""
    AuditMarkdownWriter().write(result_or_audit, path)


def save_result_csv(result: object, directory: str | Path, model: FiniteElementModel | None = None) -> dict[str, Path]:
    """Save static result tables as CSV files."""
    return CsvResultWriter().write(result, directory, model)


def save_result_vtu(result: object, model: FiniteElementModel, path: str | Path) -> None:
    """Save a static result as an ASCII VTU file for ParaView."""
    VtuResultWriter().write(result, model, path)


def list_methods() -> dict[str, tuple[str, ...]]:
    """List supported analysis methods."""
    return available_methods()


def run_qualification_campaign(manifest_path: str | Path, output_dir: str | Path) -> dict[str, object]:
    """Run a qualification campaign manifest and write evidence outputs."""
    return QualificationCampaignRunner().run(manifest_path, output_dir)


def run_qualification_case(
    identifier: str,
    output_dir: str | Path,
    *,
    manifest_path: str | Path = DEFAULT_QUALIFICATION_CAMPAIGN,
) -> dict[str, object]:
    """Run one named official qualification case and write its evidence bundle."""
    return QualificationCampaignRunner().run_case(manifest_path, identifier, output_dir)


def qualification_readiness(scope: str, registry_path: str | Path | None = None) -> QualificationReadiness:
    """Evaluate traceability and evidence readiness for one progressive scope."""
    if registry_path is None:
        return _qualification_readiness(scope)
    return _qualification_readiness(scope, registry_path)


def load_large_model(path: str | Path) -> LargeModel:
    """Load a large-scale TET4 model from HDF5 or NPZ."""
    return _load_large_model(path)


def load_distributed_large_model(
    path: str | Path,
    *,
    partition_strategy: str = "contiguous",
    graph_partitioner: str = "ptscotch",
) -> object:
    """Load the rank-owned HDF5 partition for a PETSc/MPI solve."""
    return _load_distributed_large_model(
        path,
        partition_strategy=partition_strategy,
        graph_partitioner=graph_partitioner,
    )


def convert_model_to_large(input_path: str | Path, output_path: str | Path) -> LargeModel:
    """Convert a standard JSON model to the large-scale disk format."""
    return _convert_model_to_large(input_path, output_path)


def inspect_large_model(model: LargeModel) -> LargeAuditReport:
    """Return an aggregated large-model audit."""
    return _inspect_large_model(model)


def solve_large_model(
    model: LargeModel,
    output_dir: str | Path | None = None,
    *,
    solver_backend: str = "scipy",
    preconditioner: str = "jacobi",
    chunk_size: int = 4096,
    matrix_format: str = "baij",
) -> LargeSolveResult:
    """Solve a large-scale linear-static TET4 model."""
    return _solve_large_model(
        model,
        output_dir=output_dir,
        solver_backend=solver_backend,
        preconditioner=preconditioner,
        chunk_size=chunk_size,
        parameters={"matrix_format": matrix_format},
    )


def generate_large_tet4_block(path: str | Path, *, nx: int, ny: int, nz: int, **kwargs: object) -> LargeModel:
    """Generate a structured large-scale TET4 block model."""
    return _generate_tet4_block(path, nx=nx, ny=ny, nz=nz, **kwargs)


def recommended_large_block(target_dofs: int) -> tuple[int, int, int]:
    """Return near-cubic block dimensions for a target number of dofs."""
    return _recommended_block_for_dofs(target_dofs)


def benchmark_large_model(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    solver_backend: str = "scipy",
    preconditioner: str | None = None,
    chunk_size: int = 4096,
    matrix_format: str = "baij",
    partition_strategy: str = "contiguous",
    graph_partitioner: str = "ptscotch",
    restart_from: str | Path | None = None,
) -> dict[str, object]:
    """Run a large-model benchmark and write reproducible evidence artifacts."""
    return _benchmark_large_model(
        input_path,
        output_dir,
        solver_backend=solver_backend,
        preconditioner=preconditioner,
        chunk_size=chunk_size,
        matrix_format=matrix_format,
        partition_strategy=partition_strategy,
        graph_partitioner=graph_partitioner,
        restart_from=restart_from,
    )


def run_large_scale_campaign(
    output_dir: str | Path,
    *,
    targets: tuple[int, ...] = (100_000, 1_000_000, 3_000_000),
    solver_backend: str = "petsc",
    preconditioner: str | None = None,
    chunk_size: int = 4096,
    execute: bool = False,
    stop_on_failure: bool = True,
) -> dict[str, object]:
    """Plan or execute a traceable multi-size large TET4 campaign."""
    return _run_large_scale_campaign(
        output_dir,
        targets=targets,
        solver_backend=solver_backend,
        preconditioner=preconditioner,
        chunk_size=chunk_size,
        execute=execute,
        stop_on_failure=stop_on_failure,
    )


def run_large_preconditioner_campaign(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    preconditioners: tuple[str, ...] = ("gamg", "hypre"),
    chunk_size: int = 4096,
    matrix_format: str = "baij",
    displacement_tolerance: float = 1.0e-8,
    partition_strategy: str = "contiguous",
    graph_partitioner: str = "ptscotch",
) -> dict[str, object]:
    """Compare PETSc preconditioners with file-backed displacement checks."""
    return _run_large_preconditioner_campaign(
        input_path,
        output_dir,
        preconditioners=preconditioners,
        chunk_size=chunk_size,
        matrix_format=matrix_format,
        displacement_tolerance=displacement_tolerance,
        partition_strategy=partition_strategy,
        graph_partitioner=graph_partitioner,
    )


def analyze_large_scaling(
    benchmark_paths: tuple[str | Path, ...],
    output_dir: str | Path,
    *,
    mode: str,
    weak_work_tolerance: float = 0.10,
    efficiency_warning_threshold: float = 0.60,
) -> dict[str, object]:
    """Analyze completed benchmarks as a strong- or weak-scaling campaign."""
    return _analyze_large_scaling(
        benchmark_paths,
        output_dir,
        mode=mode,
        weak_work_tolerance=weak_work_tolerance,
        efficiency_warning_threshold=efficiency_warning_threshold,
    )


def parse_petsc_log_view(path: str | Path) -> dict[str, object]:
    """Parse a PETSc ``-log_view ascii_info_detail`` performance profile."""
    return _parse_petsc_log_view(path)


def write_petsc_profile_report(
    profile_paths: tuple[str | Path, ...],
    output_dir: str | Path,
    *,
    labels: tuple[str, ...] | None = None,
) -> dict[str, object]:
    """Compare PETSc profiles and write JSON, Markdown and evidence manifest."""
    return _write_petsc_profile_report(profile_paths, output_dir, labels=labels)


def analyze_petsc_tuning(
    benchmark_paths: tuple[str | Path, ...],
    output_dir: str | Path,
    *,
    topologies: tuple[str, ...],
    presets: tuple[str, ...],
    displacement_tolerance: float = 1.0e-8,
) -> dict[str, object]:
    """Compare independently executed PETSc tuning runs across topologies."""
    return _analyze_petsc_tuning(
        benchmark_paths,
        output_dir,
        topologies=topologies,
        presets=presets,
        displacement_tolerance=displacement_tolerance,
    )


def postprocess_large_model(
    model_path: str | Path,
    displacement_path: str | Path,
    output_dir: str | Path,
    *,
    chunk_size: int = 65_536,
    resume: bool = False,
    overwrite: bool = False,
    max_chunks: int | None = None,
) -> dict[str, object]:
    """Recover large TET4 fields by bounded-memory chunks with checkpointing."""
    return _postprocess_large_tet4(
        model_path,
        displacement_path,
        output_dir,
        chunk_size=chunk_size,
        resume=resume,
        overwrite=overwrite,
        max_chunks=max_chunks,
    )


def qualify_large_tet4_pipeline(
    output_dir: str | Path,
    *,
    target_dofs: int = 1_000_000,
    nx: int | None = None,
    ny: int | None = None,
    nz: int | None = None,
    solver_backend: str = "petsc",
    preconditioner: str | None = None,
    chunk_size: int = 4096,
    **kwargs: object,
) -> dict[str, object]:
    """Generate, solve, audit, benchmark and verify a large TET4 qualification case."""
    return _qualify_large_tet4_pipeline(
        output_dir,
        target_dofs=target_dofs,
        nx=nx,
        ny=ny,
        nz=nz,
        solver_backend=solver_backend,
        preconditioner=preconditioner,
        chunk_size=chunk_size,
        **kwargs,
    )


def check_large_readiness(
    output_dir: str | Path,
    *,
    target_dofs: int = 1_000_000,
    nx: int | None = None,
    ny: int | None = None,
    nz: int | None = None,
    solver_backend: str = "petsc",
    chunk_size: int = 4096,
) -> dict[str, object]:
    """Check dependencies and sizing before a large TET4 qualification run."""
    return _check_large_readiness(
        output_dir,
        target_dofs=target_dofs,
        nx=nx,
        ny=ny,
        nz=nz,
        solver_backend=solver_backend,
        chunk_size=chunk_size,
    )


def save_large_readiness(report: dict[str, object], output_dir: str | Path) -> dict[str, Path]:
    """Write large-readiness JSON and Markdown reports."""
    return _write_large_readiness_report(report, output_dir)


def collect_large_runtime_environment(metadata: dict[str, object] | None = None) -> dict[str, object]:
    """Collect Python, platform and dependency metadata for a large-scale run."""
    return _collect_runtime_environment(metadata)


def save_large_runtime_environment(
    output_dir: str | Path,
    metadata: dict[str, object] | None = None,
) -> Path:
    """Write a runtime traceability report for a large-scale evidence directory."""
    return _write_runtime_environment(output_dir, metadata)


def verify_large_qualification(
    path: str | Path,
    *,
    target_dofs: int = 1_000_000,
    max_solver_residual: float = 1.0e-6,
) -> LargeQualificationVerification:
    """Verify a completed large-scale qualification evidence directory."""
    return _verify_large_qualification(path, target_dofs=target_dofs, max_solver_residual=max_solver_residual)


def save_large_verification(
    report: LargeQualificationVerification,
    *,
    json_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> dict[str, Path]:
    """Write JSON and/or Markdown reports for large qualification verification."""
    return _save_large_verification_report(report, json_path=json_path, markdown_path=markdown_path)
