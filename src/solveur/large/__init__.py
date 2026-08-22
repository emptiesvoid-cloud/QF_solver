"""Large-scale finite element model path."""

from solveur.large.benchmark import benchmark_large_model
from solveur.large.audit import inspect_large_model
from solveur.large.campaign import run_large_scale_campaign
from solveur.large.generator import generate_tet4_block, generate_tet4_cantilever_block, recommended_block_for_dofs
from solveur.large.distributed_model import DistributedLargeModel, load_distributed_large_model
from solveur.large.io import convert_model_to_large, load_large_model, save_large_model
from solveur.large.model import LargeModel
from solveur.large.optimization import analyze_large_scaling, run_large_preconditioner_campaign
from solveur.large.profiling import parse_petsc_log_view, write_petsc_profile_report
from solveur.large.postprocess import postprocess_large_tet4
from solveur.large.qualification import qualify_large_tet4_pipeline
from solveur.large.readiness import check_large_readiness, write_large_readiness_report
from solveur.large.runtime import collect_runtime_environment, write_runtime_environment
from solveur.large.solver import solve_large_model
from solveur.large.tuning import PETSC_TUNING_PRESETS, analyze_petsc_tuning
from solveur.large.verification import verify_large_qualification

__all__ = [
    "LargeModel",
    "PETSC_TUNING_PRESETS",
    "DistributedLargeModel",
    "benchmark_large_model",
    "analyze_large_scaling",
    "analyze_petsc_tuning",
    "check_large_readiness",
    "collect_runtime_environment",
    "convert_model_to_large",
    "generate_tet4_block",
    "generate_tet4_cantilever_block",
    "inspect_large_model",
    "load_large_model",
    "load_distributed_large_model",
    "parse_petsc_log_view",
    "postprocess_large_tet4",
    "qualify_large_tet4_pipeline",
    "recommended_block_for_dofs",
    "run_large_scale_campaign",
    "run_large_preconditioner_campaign",
    "save_large_model",
    "solve_large_model",
    "verify_large_qualification",
    "write_runtime_environment",
    "write_large_readiness_report",
    "write_petsc_profile_report",
]
