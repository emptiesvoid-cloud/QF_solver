"""Command line interface for the generic finite element solver."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from solveur.cli import benchmark as benchmark_cli
from solveur.cli import large as large_cli
from solveur.cli import mesh as mesh_cli
from solveur.cli import standard as standard_cli
from solveur.cli import vnv as vnv_cli
from solveur.cli import verification as verification_cli
from solveur.core.errors import ExitCode, SolverError
from solveur.core.qualification import PROFILES
from solveur.verification.traceability import QUALIFICATION_SCOPES
from solveur.version import DISPLAY_NAME, LEGACY_CLI, __version__, legacy_entrypoint_warning


class SolverCli:
    """Thin CLI layer that delegates business logic to the API."""

    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog=DISPLAY_NAME, description="QF_solver finite element solver CLI.")
        parser.add_argument("--version", action="version", version=f"{DISPLAY_NAME} {__version__}")
        parser.add_argument("--debug", action="store_true", help="show Python tracebacks for diagnostic use")
        sub = parser.add_subparsers(dest="command")

        solve = sub.add_parser("solve", help="solve a JSON finite element model")
        solve.add_argument("--input", required=True, type=Path)
        solve.add_argument("--output", required=True, type=Path)
        solve.add_argument(
            "--analysis",
            choices=("linear_static", "modal", "nonlinear_static", "transient_dynamic", "harmonic_response"),
            default=None,
        )
        solve.add_argument("--method", default=None)
        solve.add_argument("--png", type=Path, default=None)
        solve.add_argument("--scale", type=float, default=1.0)
        solve.add_argument("--audit-md", type=Path, default=None)
        solve.add_argument("--csv-dir", type=Path, default=None)
        solve.add_argument("--vtu", type=Path, default=None)
        solve.add_argument("--evidence-dir", type=Path, default=None)
        solve.add_argument("--audit-gate", choices=("none", "fail", "warning"), default="none")
        solve.add_argument("--verification-profile", choices=PROFILES, default=None)
        solve.add_argument("--strict-schema", action="store_true", help="accepted for explicit v1 strict JSON validation")
        solve.set_defaults(func=standard_cli.command_solve)

        check = sub.add_parser("check-mesh", help="validate a JSON model mesh")
        check.add_argument("--input", required=True, type=Path)
        check.add_argument("--json-report", type=Path, default=None)
        check.add_argument("--verification-profile", choices=PROFILES, default=None)
        check.add_argument("--strict-schema", action="store_true", help="accepted for explicit v1 strict JSON validation")
        check.set_defaults(func=standard_cli.command_check_mesh)

        inspect = sub.add_parser("inspect", help="write a white-box audit for a JSON model")
        inspect.add_argument("--input", required=True, type=Path)
        inspect.add_argument("--output", type=Path, default=None)
        inspect.add_argument("--markdown", type=Path, default=None)
        inspect.add_argument("--audit-gate", choices=("none", "fail", "warning"), default="none")
        inspect.add_argument("--detail", choices=("summary", "values"), default="summary")
        inspect.add_argument("--verification-profile", choices=PROFILES, default=None)
        inspect.add_argument("--strict-schema", action="store_true", help="accepted for explicit v1 strict JSON validation")
        inspect.set_defaults(func=standard_cli.command_inspect)

        evidence = sub.add_parser("evidence", help="solve a model and write a reproducible evidence bundle")
        evidence.add_argument("--input", required=True, type=Path)
        evidence.add_argument("--output", required=True, type=Path)
        evidence.add_argument("--verification-profile", choices=PROFILES, default=None)
        evidence.add_argument("--strict-schema", action="store_true", help="accepted for explicit v1 strict JSON validation")
        evidence.set_defaults(func=standard_cli.command_evidence)

        import_mesh = sub.add_parser("import-mesh", help="import a Gmsh MSH 4.1 mesh and companion setup")
        import_mesh.add_argument("--mesh", required=True, type=Path)
        import_mesh.add_argument("--setup", required=True, type=Path)
        import_mesh.add_argument("--output", required=True, type=Path)
        import_mesh.add_argument("--report", type=Path, default=None)
        import_mesh.add_argument("--repair-tetra-orientation", action="store_true")
        import_mesh.set_defaults(func=mesh_cli.command_import_mesh)

        benchmarks = sub.add_parser("benchmarks", help="list controlled meshed mechanical benchmarks")
        benchmarks.add_argument("--json", action="store_true", help="write the catalog as JSON")
        benchmarks.set_defaults(func=benchmark_cli.command_benchmarks)

        benchmark = sub.add_parser("benchmark", help="run one controlled meshed benchmark")
        benchmark.add_argument("--case", required=True)
        benchmark.add_argument("--output", required=True, type=Path)
        benchmark.add_argument("--verification-profile", choices=PROFILES, default="engineering")
        benchmark.set_defaults(func=benchmark_cli.command_benchmark)

        vnv_compare = sub.add_parser(
            "vnv-compare",
            help="compare normalized QF_solver and reference results and write a Markdown study",
        )
        vnv_compare.add_argument("--study", required=True, type=Path)
        vnv_compare.add_argument("--output", required=True, type=Path)
        vnv_compare.add_argument(
            "--require-approval",
            action="store_true",
            help="return code 4 while the owner decision is still pending",
        )
        vnv_compare.set_defaults(func=vnv_cli.command_vnv_compare)

        vnv_import = sub.add_parser(
            "vnv-import-benchmark",
            help="create a V&V study with PNG and VTU evidence from a controlled benchmark",
        )
        vnv_import.add_argument(
            "--case",
            required=True,
            choices=("BM-SOL-CANTILEVER-001", "BM-SOL-TET4-TORSION-001"),
        )
        vnv_import.add_argument("--output", required=True, type=Path)
        vnv_import.add_argument("--source", type=Path, default=None)
        vnv_import.add_argument("--overwrite", action="store_true")
        vnv_import.set_defaults(func=vnv_cli.command_vnv_import_benchmark)

        convert = sub.add_parser("convert-model", help="convert JSON model to large HDF5/NPZ format")
        convert.add_argument("--input", required=True, type=Path)
        convert.add_argument("--output", required=True, type=Path)
        convert.set_defaults(func=large_cli.command_convert_model)

        inspect_large = sub.add_parser("inspect-large", help="write an aggregated audit for a large model")
        inspect_large.add_argument("--input", required=True, type=Path)
        inspect_large.add_argument("--output", required=True, type=Path)
        inspect_large.set_defaults(func=large_cli.command_inspect_large)

        solve_large = sub.add_parser("solve-large", help="solve a large-scale linear static TET4 model")
        solve_large.add_argument("--input", required=True, type=Path)
        solve_large.add_argument("--output", required=True, type=Path)
        solve_large.add_argument("--solver-backend", choices=("petsc", "scipy", "matrix_free"), default="petsc")
        solve_large.add_argument("--preconditioner", default=None)
        solve_large.add_argument("--chunk-size", type=int, default=4096)
        solve_large.add_argument("--matrix-format", choices=("baij", "aij"), default="baij")
        solve_large.add_argument("--partition-strategy", choices=("contiguous", "graph"), default="contiguous")
        solve_large.add_argument("--graph-partitioner", default="ptscotch")
        solve_large.set_defaults(func=large_cli.command_solve_large)

        generate_large = sub.add_parser("generate-large-tet4-block", help="generate a structured large TET4 block")
        generate_large.add_argument("--output", required=True, type=Path)
        generate_large.add_argument("--nx", type=int, default=None)
        generate_large.add_argument("--ny", type=int, default=None)
        generate_large.add_argument("--nz", type=int, default=None)
        generate_large.add_argument("--target-dofs", type=int, default=None)
        generate_large.add_argument("--length", type=float, default=1.0)
        generate_large.add_argument("--height", type=float, default=1.0)
        generate_large.add_argument("--depth", type=float, default=1.0)
        generate_large.add_argument("--young", type=float, default=210.0e9)
        generate_large.add_argument("--poisson", type=float, default=0.3)
        generate_large.add_argument("--density", type=float, default=7800.0)
        generate_large.add_argument(
            "--material-json",
            type=Path,
            default=None,
            help="JSON file describing one supported large-scale linear solid material",
        )
        generate_large.add_argument("--total-load", type=float, default=1000.0)
        generate_large.set_defaults(func=large_cli.command_generate_large)

        benchmark_large = sub.add_parser("benchmark-large", help="solve a large model and write benchmark evidence")
        benchmark_large.add_argument("--input", required=True, type=Path)
        benchmark_large.add_argument("--output", required=True, type=Path)
        benchmark_large.add_argument("--solver-backend", choices=("petsc", "scipy", "matrix_free"), default="scipy")
        benchmark_large.add_argument("--preconditioner", default=None)
        benchmark_large.add_argument("--chunk-size", type=int, default=4096)
        benchmark_large.add_argument("--matrix-format", choices=("baij", "aij"), default="baij")
        benchmark_large.add_argument("--partition-strategy", choices=("contiguous", "graph"), default="contiguous")
        benchmark_large.add_argument("--graph-partitioner", default="ptscotch")
        benchmark_large.add_argument("--restart-from", type=Path, default=None)
        benchmark_large.set_defaults(func=large_cli.command_benchmark_large)

        large_campaign = sub.add_parser("large-campaign", help="plan or execute a multi-size large TET4 campaign")
        large_campaign.add_argument("--output", required=True, type=Path)
        large_campaign.add_argument("--targets", nargs="+", type=int, default=[100_000, 1_000_000, 3_000_000])
        large_campaign.add_argument("--solver-backend", choices=("petsc", "scipy", "matrix_free"), default="petsc")
        large_campaign.add_argument("--preconditioner", default=None)
        large_campaign.add_argument("--chunk-size", type=int, default=4096)
        large_campaign.add_argument("--memory-budget-mb", type=int, default=None)
        large_campaign.add_argument("--execute", action="store_true")
        large_campaign.add_argument("--continue-on-failure", action="store_true")
        large_campaign.set_defaults(func=large_cli.command_large_campaign)

        large_pc = sub.add_parser("large-preconditioners", help="compare PETSc preconditioners on one model")
        large_pc.add_argument("--input", required=True, type=Path)
        large_pc.add_argument("--output", required=True, type=Path)
        large_pc.add_argument("--preconditioners", nargs="+", default=["gamg", "hypre"])
        large_pc.add_argument("--chunk-size", type=int, default=4096)
        large_pc.add_argument("--matrix-format", choices=("baij", "aij"), default="baij")
        large_pc.add_argument("--displacement-tolerance", type=float, default=1.0e-8)
        large_pc.add_argument("--partition-strategy", choices=("contiguous", "graph"), default="contiguous")
        large_pc.add_argument("--graph-partitioner", default="ptscotch")
        large_pc.set_defaults(func=large_cli.command_large_preconditioners)

        large_scaling = sub.add_parser("large-scaling-report", help="analyze completed strong/weak scaling runs")
        large_scaling.add_argument("--inputs", nargs="+", required=True, type=Path)
        large_scaling.add_argument("--output", required=True, type=Path)
        large_scaling.add_argument("--mode", choices=("strong", "weak"), required=True)
        large_scaling.add_argument("--weak-work-tolerance", type=float, default=0.10)
        large_scaling.add_argument("--efficiency-warning-threshold", type=float, default=0.60)
        large_scaling.set_defaults(func=large_cli.command_large_scaling_report)

        petsc_profile = sub.add_parser("petsc-profile-report", help="parse and compare PETSc log_view profiles")
        petsc_profile.add_argument("--inputs", nargs="+", required=True, type=Path)
        petsc_profile.add_argument("--labels", nargs="+", default=None)
        petsc_profile.add_argument("--output", required=True, type=Path)
        petsc_profile.set_defaults(func=large_cli.command_petsc_profile_report)

        petsc_tuning = sub.add_parser("petsc-tuning-report", help="compare PETSc tuning runs across topologies")
        petsc_tuning.add_argument("--inputs", nargs="+", required=True, type=Path)
        petsc_tuning.add_argument("--topologies", nargs="+", required=True)
        petsc_tuning.add_argument("--presets", nargs="+", required=True)
        petsc_tuning.add_argument("--output", required=True, type=Path)
        petsc_tuning.add_argument("--displacement-tolerance", type=float, default=1.0e-8)
        petsc_tuning.set_defaults(func=large_cli.command_petsc_tuning_report)

        postprocess_large = sub.add_parser(
            "postprocess-large", help="recover TET4 fields by checkpointed bounded-memory chunks"
        )
        postprocess_large.add_argument("--input", required=True, type=Path)
        postprocess_large.add_argument("--displacements", required=True, type=Path)
        postprocess_large.add_argument("--output", required=True, type=Path)
        postprocess_large.add_argument("--chunk-size", type=int, default=65_536)
        postprocess_large.add_argument("--resume", action="store_true")
        postprocess_large.add_argument("--overwrite", action="store_true")
        postprocess_large.add_argument("--max-chunks", type=int, default=None)
        postprocess_large.set_defaults(func=large_cli.command_postprocess_large)

        readiness = sub.add_parser("large-readiness", help="check dependencies and sizing before a large TET4 run")
        readiness.add_argument("--output", required=True, type=Path)
        readiness.add_argument("--target-dofs", type=int, default=1_000_000)
        readiness.add_argument("--nx", type=int, default=None)
        readiness.add_argument("--ny", type=int, default=None)
        readiness.add_argument("--nz", type=int, default=None)
        readiness.add_argument("--solver-backend", choices=("petsc", "scipy", "matrix_free"), default="petsc")
        readiness.add_argument("--chunk-size", type=int, default=4096)
        readiness.add_argument("--memory-budget-mb", type=int, default=None)
        readiness.set_defaults(func=large_cli.command_large_readiness)

        qualify_large = sub.add_parser("qualify-large", help="generate, solve and verify a large TET4 case")
        qualify_large.add_argument("--output", required=True, type=Path)
        qualify_large.add_argument("--target-dofs", type=int, default=1_000_000)
        qualify_large.add_argument("--nx", type=int, default=None)
        qualify_large.add_argument("--ny", type=int, default=None)
        qualify_large.add_argument("--nz", type=int, default=None)
        qualify_large.add_argument("--solver-backend", choices=("petsc", "scipy", "matrix_free"), default="petsc")
        qualify_large.add_argument("--preconditioner", default=None)
        qualify_large.add_argument("--chunk-size", type=int, default=4096)
        qualify_large.add_argument("--memory-budget-mb", type=int, default=None)
        qualify_large.add_argument("--length", type=float, default=1.0)
        qualify_large.add_argument("--height", type=float, default=1.0)
        qualify_large.add_argument("--depth", type=float, default=1.0)
        qualify_large.add_argument("--young", type=float, default=210.0e9)
        qualify_large.add_argument("--poisson", type=float, default=0.3)
        qualify_large.add_argument("--density", type=float, default=7800.0)
        qualify_large.add_argument("--total-load", type=float, default=1000.0)
        qualify_large.set_defaults(func=large_cli.command_qualify_large)

        verify_large = sub.add_parser("verify-large", help="verify a completed large qualification evidence directory")
        verify_large.add_argument("--input", required=True, type=Path)
        verify_large.add_argument("--target-dofs", type=int, default=1_000_000)
        verify_large.add_argument("--max-solver-residual", type=float, default=1.0e-6)
        verify_large.add_argument("--json-report", type=Path, default=None)
        verify_large.add_argument("--markdown", type=Path, default=None)
        verify_large.set_defaults(func=large_cli.command_verify_large)

        verify_evidence_parser = sub.add_parser("verify-evidence", help="verify an evidence bundle manifest")
        verify_evidence_parser.add_argument("--input", required=True, type=Path)
        verify_evidence_parser.add_argument("--json-report", type=Path, default=None)
        verify_evidence_parser.set_defaults(func=verification_cli.command_verify_evidence)

        verify = sub.add_parser("verify", help="run existing MITC4 verification")
        verify.add_argument("--quick", action="store_true")
        verify.set_defaults(func=verification_cli.command_verify)

        verify_tet10 = sub.add_parser("verify-tet10", help="run analytical TET10 mechanical verification")
        verify_tet10.add_argument("--json-report", type=Path, default=None)
        verify_tet10.set_defaults(func=verification_cli.command_verify_tet10)

        verify_contact = sub.add_parser("verify-contact", help="run the internal V1 normal and frictional contact studies")
        verify_contact.add_argument("--output", required=True, type=Path)
        verify_contact.add_argument("--json-report", type=Path, default=None)
        verify_contact.set_defaults(func=verification_cli.command_verify_contact)

        verify_all = sub.add_parser("verify-all", help="run project quality and verification commands")
        verify_all.add_argument("--profile", choices=PROFILES, default="engineering")
        verify_all.add_argument("--scope", choices=QUALIFICATION_SCOPES, default="tet4-linear-static")
        verify_all.add_argument("--json-report", type=Path, default=None)
        verify_all.set_defaults(func=verification_cli.command_verify_all)

        readiness = sub.add_parser("qualification-readiness", help="check requirement traceability for one scope")
        readiness.add_argument("--scope", choices=QUALIFICATION_SCOPES, default="tet4-linear-static")
        readiness.add_argument("--registry", type=Path, default=None)
        readiness.add_argument("--json-report", type=Path, default=None)
        readiness.set_defaults(func=verification_cli.command_qualification_readiness)

        maturity = sub.add_parser(
            "maturity-promotion",
            help="audit evidence readiness for the controlled maturity-promotion plan",
        )
        maturity.add_argument(
            "--output",
            type=Path,
            default=Path("results/maturity_promotion_0_2_1"),
        )
        maturity.add_argument(
            "--plan",
            type=Path,
            default=Path("qualification/maturity_promotion_0_2_1.json"),
        )
        maturity.add_argument(
            "--matrix",
            type=Path,
            default=Path("qualification/element_analysis_matrix.json"),
        )
        maturity.add_argument(
            "--coverage",
            type=Path,
            default=Path("qualification/technical_content_coverage.json"),
        )
        maturity.add_argument(
            "--criteria",
            type=Path,
            default=Path("qualification/maturity_criteria_0_2_1.json"),
        )
        maturity.add_argument("--fail-on-blocking", action="store_true")
        maturity.set_defaults(func=verification_cli.command_maturity_promotion)

        owner_review = sub.add_parser(
            "owner-review-check",
            help="validate one Owner/external review record without changing maturity",
        )
        owner_review.add_argument("--input", required=True, type=Path)
        owner_review.add_argument("--scope", default=None)
        owner_review.add_argument("--require-decision", action="store_true")
        owner_review.add_argument("--target-maturity", default=None, choices=("stable", "owner_accepted", "experimental", "research"))
        owner_review.add_argument("--json-report", type=Path, default=None)
        owner_review.set_defaults(func=verification_cli.command_owner_review_check)

        qualify = sub.add_parser("qualify", help="run a qualification campaign manifest")
        qualify.add_argument("--manifest", type=Path, default=Path("qualification/campaign.json"))
        qualify.add_argument("--output", type=Path, default=Path("results/qualification_campaign"))
        qualify.set_defaults(func=verification_cli.command_qualify)

        release_vv = sub.add_parser(
            "release-vv",
            help="build the release-level verification and validation readiness package",
        )
        release_vv.add_argument("--output", required=True, type=Path)
        release_vv.add_argument("--registry", type=Path, default=None)
        release_vv.add_argument("--execute-campaign", action="store_true")
        release_vv.add_argument(
            "--fail-on-warning",
            action="store_true",
            help="return code 4 when readiness warnings remain",
        )
        release_vv.set_defaults(func=verification_cli.command_release_vv)

        methods = sub.add_parser("methods", help="list available analysis methods")
        methods.set_defaults(func=standard_cli.command_methods)
        return parser

    def run(self, argv: Sequence[str] | None = None) -> int:
        parser = self.build_parser()
        raw_args = list(argv) if argv is not None else sys.argv[1:]
        debug_requested = "--debug" in raw_args
        raw_args = [value for value in raw_args if value != "--debug"]
        args = parser.parse_args(raw_args)
        args.debug = debug_requested
        if args.command is None:
            parser.print_help()
            return 0
        try:
            return int(args.func(args))
        except SolverError as exc:
            if args.debug:
                raise
            print(f"ERROR[{type(exc).__name__}]: {exc}", file=sys.stderr)
            return int(exc.exit_code)
        except (FileNotFoundError, ValueError) as exc:
            if args.debug:
                raise
            print(f"ERROR[InputValidationError]: {exc}", file=sys.stderr)
            return int(ExitCode.INPUT_OR_MESH)
        except ImportError as exc:
            if args.debug:
                raise
            print(f"ERROR[InfrastructureError]: {exc}", file=sys.stderr)
            return int(ExitCode.INFRASTRUCTURE_FAILURE)
        except RuntimeError as exc:
            if args.debug:
                raise
            print(f"ERROR[NumericalConvergenceError]: {exc}", file=sys.stderr)
            return int(ExitCode.NUMERICAL_FAILURE)

def main(argv: Sequence[str] | None = None) -> int:
    return SolverCli().run(argv)


def legacy_main(argv: Sequence[str] | None = None) -> int:
    """Compatibility entry point retained until QF_solver 0.3.0."""
    print(legacy_entrypoint_warning(LEGACY_CLI), file=sys.stderr)
    return main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
