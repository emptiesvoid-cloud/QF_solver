"""Large-scale model CLI commands."""

from __future__ import annotations

import argparse
import json
from typing import Any

from solveur.api.public import (
    analyze_petsc_tuning,
    analyze_large_scaling,
    benchmark_large_model,
    check_large_readiness,
    convert_model_to_large,
    generate_large_tet4_block,
    inspect_large_model,
    load_large_model,
    load_distributed_large_model,
    postprocess_large_model,
    qualify_large_tet4_pipeline,
    recommended_large_block,
    run_large_scale_campaign,
    run_large_preconditioner_campaign,
    save_large_readiness,
    save_large_verification,
    save_result,
    solve_large_model,
    verify_large_qualification,
    write_petsc_profile_report,
)
from solveur.core.errors import ExitCode


def command_convert_model(args: argparse.Namespace) -> int:
    model = convert_model_to_large(args.input, args.output)
    print("CONVERT MODEL STATUS: PASS")
    print(f"output: {args.output}")
    print(f"nodes: {model.node_count}")
    print(f"elements: {model.element_count}")
    return 0


def command_inspect_large(args: argparse.Namespace) -> int:
    model = load_large_model(args.input)
    audit = inspect_large_model(model)
    save_result(audit, args.output)
    print(f"INSPECT LARGE STATUS: {audit.status}")
    print(f"output: {args.output}")
    return int(ExitCode.INPUT_OR_MESH if audit.status == "FAIL" else ExitCode.ACCEPTED)


def command_solve_large(args: argparse.Namespace) -> int:
    model = (
        load_distributed_large_model(
            args.input,
            partition_strategy=args.partition_strategy,
            graph_partitioner=args.graph_partitioner,
        )
        if args.solver_backend == "petsc" and _mpi_size() > 1
        else load_large_model(args.input)
    )
    preconditioner = args.preconditioner or ("gamg" if args.solver_backend == "petsc" else "jacobi")
    result = solve_large_model(
        model,
        output_dir=args.output,
        solver_backend=args.solver_backend,
        preconditioner=preconditioner,
        chunk_size=args.chunk_size,
        matrix_format=args.matrix_format,
    )
    if _reporting_rank(result.backend):
        print(f"SOLVE LARGE STATUS: {result.status}")
        print(f"backend: {result.backend}")
        print(f"output directory: {args.output}")
        print(f"summary: {result.output_files.get('summary', '')}")
    return 0 if result.status == "PASS" else 1


def command_generate_large(args: argparse.Namespace) -> int:
    nx, ny, nz = _large_block_dimensions(args)
    model = generate_large_tet4_block(
        args.output,
        nx=nx,
        ny=ny,
        nz=nz,
        length=args.length,
        height=args.height,
        depth=args.depth,
        young=args.young,
        poisson=args.poisson,
        density=args.density,
        total_load=args.total_load,
        material=_large_material_from_json(args.material_json),
    )
    print("GENERATE LARGE STATUS: PASS")
    print(f"output: {args.output}")
    print(f"cells: {nx} {ny} {nz}")
    print(f"nodes: {model.node_count}")
    print(f"elements: {model.element_count}")
    print(f"ddl: {model.ndof}")
    return 0


def _large_material_from_json(path: object) -> dict[str, Any] | None:
    if path is None:
        return None
    source = path if hasattr(path, "read_text") else None
    if source is None:
        raise ValueError("--material-json must be a readable JSON file path.")
    try:
        material = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid --material-json file {source}: {exc}") from exc
    if not isinstance(material, dict):
        raise ValueError("--material-json must contain one JSON object.")
    return material


def command_benchmark_large(args: argparse.Namespace) -> int:
    result = benchmark_large_model(
        args.input,
        args.output,
        solver_backend=args.solver_backend,
        preconditioner=args.preconditioner,
        chunk_size=args.chunk_size,
        matrix_format=args.matrix_format,
        partition_strategy=args.partition_strategy,
        graph_partitioner=args.graph_partitioner,
        restart_from=args.restart_from,
    )
    if _reporting_rank(str(result["backend"])):
        print(f"BENCHMARK LARGE STATUS: {result['status']}")
        print(f"backend: {result['backend']}")
        print(f"ddl: {result['ndof']}")
        print(f"output directory: {args.output}")
        print(f"evidence manifest: {result['evidence_manifest']}")
        print(f"evidence verification: {result['evidence_verification']['status']}")
    return 0 if result["status"] == "PASS" and result["evidence_verification"]["status"] == "PASS" else 1


def command_large_campaign(args: argparse.Namespace) -> int:
    result = run_large_scale_campaign(
        args.output,
        targets=tuple(args.targets),
        solver_backend=args.solver_backend,
        preconditioner=args.preconditioner,
        chunk_size=args.chunk_size,
        execute=args.execute,
        stop_on_failure=not args.continue_on_failure,
    )
    print(f"LARGE CAMPAIGN STATUS: {result['status']}")
    print(f"mode: {result['mode']}")
    print(f"backend: {result['backend']}")
    print(f"targets: {' '.join(str(value) for value in result['targets'])}")
    print(f"output directory: {args.output}")
    print(f"report: {result['markdown_report']}")
    print(f"evidence verification: {result['evidence_verification']['status']}")
    if result["status"] in {"PASS", "PLANNED"}:
        return int(ExitCode.ACCEPTED)
    if result["status"] == "BLOCKED":
        return int(ExitCode.INFRASTRUCTURE_FAILURE)
    return int(ExitCode.QUALIFICATION_REJECTED)


def command_large_preconditioners(args: argparse.Namespace) -> int:
    result = run_large_preconditioner_campaign(
        args.input,
        args.output,
        preconditioners=tuple(args.preconditioners),
        chunk_size=args.chunk_size,
        matrix_format=args.matrix_format,
        displacement_tolerance=args.displacement_tolerance,
        partition_strategy=args.partition_strategy,
        graph_partitioner=args.graph_partitioner,
    )
    if _reporting_rank("petsc"):
        print(f"LARGE PRECONDITIONERS STATUS: {result['status']}")
        print(f"preconditioners: {' '.join(str(value) for value in result['preconditioners'])}")
        print(f"output directory: {args.output}")
    return int(ExitCode.ACCEPTED if result["status"] == "PASS" else ExitCode.QUALIFICATION_REJECTED)


def command_large_scaling_report(args: argparse.Namespace) -> int:
    result = analyze_large_scaling(
        tuple(args.inputs),
        args.output,
        mode=args.mode,
        weak_work_tolerance=args.weak_work_tolerance,
        efficiency_warning_threshold=args.efficiency_warning_threshold,
    )
    print(f"LARGE SCALING STATUS: {result['status']}")
    print(f"mode: {result['mode']}")
    print(f"minimum efficiency: {result['minimum_efficiency']:.6g}")
    print(f"output directory: {args.output}")
    return int(ExitCode.ACCEPTED)


def command_petsc_profile_report(args: argparse.Namespace) -> int:
    result = write_petsc_profile_report(
        tuple(args.inputs),
        args.output,
        labels=tuple(args.labels) if args.labels is not None else None,
    )
    print(f"PETSC PROFILE STATUS: {result['status']}")
    print(f"profiles: {len(result['profiles'])}")
    print(f"output directory: {args.output}")
    print(f"evidence manifest: {result['evidence_manifest']}")
    return int(ExitCode.ACCEPTED)


def command_petsc_tuning_report(args: argparse.Namespace) -> int:
    result = analyze_petsc_tuning(
        tuple(args.inputs),
        args.output,
        topologies=tuple(args.topologies),
        presets=tuple(args.presets),
        displacement_tolerance=args.displacement_tolerance,
    )
    print(f"PETSC TUNING STATUS: {result['status']}")
    print(f"runs: {len(result['runs'])}")
    print(f"default change recommended: {result['default_policy_change_recommended']}")
    print(f"output directory: {args.output}")
    print(f"evidence manifest: {result['evidence_manifest']}")
    return int(ExitCode.ACCEPTED if result["status"] == "PASS" else ExitCode.QUALIFICATION_REJECTED)


def command_postprocess_large(args: argparse.Namespace) -> int:
    result = postprocess_large_model(
        args.input,
        args.displacements,
        args.output,
        chunk_size=args.chunk_size,
        resume=args.resume,
        overwrite=args.overwrite,
        max_chunks=args.max_chunks,
    )
    print(f"POSTPROCESS LARGE STATUS: {result['status']}")
    print(f"processed elements: {result['processed_element_count']}/{result['element_count']}")
    print(f"result file: {result['result_file']}")
    print(f"checkpoint: {result['checkpoint_file']}")
    return int(ExitCode.ACCEPTED)


def command_large_readiness(args: argparse.Namespace) -> int:
    dimensions = _optional_large_block_dimensions(args)
    report = check_large_readiness(
        args.output,
        target_dofs=args.target_dofs,
        nx=dimensions[0] if dimensions is not None else None,
        ny=dimensions[1] if dimensions is not None else None,
        nz=dimensions[2] if dimensions is not None else None,
        solver_backend=args.solver_backend,
        chunk_size=args.chunk_size,
    )
    paths = save_large_readiness(report, args.output)
    print(f"LARGE READINESS STATUS: {report['status']}")
    print(f"backend: {report['backend']}")
    print(f"ddl estime: {report['sizing']['ndof']}")
    print(f"json report: {paths['json']}")
    print(f"markdown report: {paths['markdown']}")
    for item in report["checks"]:
        if item["status"] != "PASS":
            print(f"{item['status']}: {item['id']} {item['detail']}")
    return 0 if report["status"] in {"PASS", "WARNING"} else 1


def command_qualify_large(args: argparse.Namespace) -> int:
    dimensions = _optional_large_block_dimensions(args)
    summary = qualify_large_tet4_pipeline(
        args.output,
        target_dofs=args.target_dofs,
        nx=dimensions[0] if dimensions is not None else None,
        ny=dimensions[1] if dimensions is not None else None,
        nz=dimensions[2] if dimensions is not None else None,
        solver_backend=args.solver_backend,
        preconditioner=args.preconditioner,
        chunk_size=args.chunk_size,
        length=args.length,
        height=args.height,
        depth=args.depth,
        young=args.young,
        poisson=args.poisson,
        density=args.density,
        total_load=args.total_load,
    )
    print(f"QUALIFY LARGE STATUS: {summary['status']}")
    print(f"backend: {summary['backend']}")
    print(f"ddl cible: {summary['target_dofs']}")
    print(f"ddl obtenu: {summary['actual_dofs']}")
    print(f"output directory: {args.output}")
    print(f"summary: {summary['summary_path']}")
    print(f"evidence manifest: {summary['evidence_manifest']}")
    return int(ExitCode.ACCEPTED if summary["status"] == "PASS" else ExitCode.QUALIFICATION_REJECTED)


def command_verify_large(args: argparse.Namespace) -> int:
    report = verify_large_qualification(
        args.input,
        target_dofs=args.target_dofs,
        max_solver_residual=args.max_solver_residual,
    )
    save_large_verification(report, json_path=args.json_report, markdown_path=args.markdown)
    print(f"VERIFY LARGE STATUS: {report.status}")
    print(f"input: {args.input}")
    if args.json_report is not None:
        print(f"json report: {args.json_report}")
    if args.markdown is not None:
        print(f"markdown report: {args.markdown}")
    for item in report.checks:
        if item["status"] != "PASS":
            print(f"{item['status']}: {item['id']} {item['detail']}")
    return int(ExitCode.ACCEPTED if report.status == "PASS" else ExitCode.QUALIFICATION_REJECTED)


def _large_block_dimensions(args: argparse.Namespace) -> tuple[int, int, int]:
    if args.target_dofs is not None:
        return recommended_large_block(args.target_dofs)
    values = (args.nx, args.ny, args.nz)
    if any(value is None for value in values):
        raise ValueError("Provide either --target-dofs or all of --nx --ny --nz.")
    return int(args.nx), int(args.ny), int(args.nz)


def _optional_large_block_dimensions(args: argparse.Namespace) -> tuple[int, int, int] | None:
    values = (args.nx, args.ny, args.nz)
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise ValueError("Provide all of --nx --ny --nz, or omit them and use --target-dofs.")
    return int(args.nx), int(args.ny), int(args.nz)


def _reporting_rank(backend: str) -> bool:
    if backend != "petsc":
        return True
    try:
        from mpi4py import MPI
    except ImportError:
        return True
    return MPI.COMM_WORLD.rank == 0


def _mpi_size() -> int:
    try:
        from mpi4py import MPI
    except ImportError:
        return 1
    return int(MPI.COMM_WORLD.size)
