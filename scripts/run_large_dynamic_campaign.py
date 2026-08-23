"""Run reproducible large TET4 modal or Newmark evidence in Docker/MPI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from solveur.io.evidence_verifier import EvidenceBundleVerifier
from solveur.large.dynamic import solve_large_modal, solve_large_newmark
from solveur.large.distributed_model import load_distributed_large_model
from solveur.large.io import load_large_model
from solveur.large.evidence import write_large_manifest
from solveur.large.runtime import write_runtime_environment


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--analysis", choices=("modal", "transient_dynamic"), required=True)
    parser.add_argument("--modes", type=int, default=6)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--dt", type=float, default=1.0e-4)
    parser.add_argument("--chunk-size", type=int, default=4096)
    parser.add_argument("--matrix-format", choices=("baij", "aij"), default="baij")
    parser.add_argument("--preconditioner", default="gamg")
    parser.add_argument("--tol", type=float, default=1.0e-8)
    parser.add_argument("--max-it", type=int, default=10_000)
    args = parser.parse_args()

    comm = _mpi_comm()
    rank = int(comm.rank) if comm is not None else 0
    if rank == 0:
        args.output.mkdir(parents=True, exist_ok=True)
        write_runtime_environment(
            args.output,
            {
                "kind": "large_dynamic_campaign",
                "analysis": args.analysis,
                "input": args.input.name,
                "modes": args.modes,
                "steps": args.steps,
                "dt": args.dt,
                "chunk_size": args.chunk_size,
                "matrix_format": args.matrix_format,
                "preconditioner": args.preconditioner,
            },
        )
    if comm is not None:
        comm.Barrier()
        model = load_distributed_large_model(args.input, comm)
    else:
        model = load_large_model(args.input)

    if args.analysis == "modal":
        summary = solve_large_modal(
            model,
            mode_count=args.modes,
            chunk_size=args.chunk_size,
            matrix_format=args.matrix_format,
            tolerance=args.tol,
            max_iterations=args.max_it,
        )
        filename = "modal_large.json"
        heading = "Grande campagne modale TET4"
    else:
        summary = solve_large_newmark(
            model,
            steps=args.steps,
            time_step=args.dt,
            chunk_size=args.chunk_size,
            matrix_format=args.matrix_format,
            preconditioner=args.preconditioner,
            tolerance=args.tol,
            max_iterations=args.max_it,
        )
        filename = "transient_large.json"
        heading = "Grande campagne Newmark TET4"

    if rank == 0:
        summary_path = args.output / filename
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        markdown_path = args.output / filename.replace(".json", ".md")
        markdown_path.write_text(_markdown(heading, summary), encoding="utf-8")
        manifest_path = write_large_manifest(
            args.output,
            {
                "kind": "large_dynamic_evidence",
                "analysis": args.analysis,
                "ndof": int(summary["ndof"]),
                "backend": summary["backend"],
                "scope_status": "development",
            },
        )
        verification = EvidenceBundleVerifier().verify(manifest_path)
        print(f"LARGE {args.analysis.upper()} STATUS: {summary['status']}")
        print(f"ddl: {summary['ndof']}")
        print(f"output directory: {args.output}")
        print(f"evidence verification: {verification.status}")
        return 0 if summary["status"] == "PASS" and verification.status == "PASS" else 1
    return 0


def _markdown(heading: str, summary: dict[str, object]) -> str:
    lines = [
        f"# {heading}",
        "",
        f"Statut technique : **{summary['status']}**. Le périmètre reste **development** jusqu'à la revue Owner.",
        "",
        f"- DDL : `{summary['ndof']}`",
        f"- Éléments : `{summary['element_count']}`",
        f"- Backend : `{summary['backend']}`",
        f"- MPI : `{summary['mpi_size']}` rang(s)",
        f"- Assemblage : `{float(summary['assembly_time_seconds']):.3f}` s",
        f"- Résolution : `{float(summary['solve_time_seconds']):.3f}` s",
    ]
    if summary["analysis"] == "modal":
        lines += [
            f"- Modes convergés : `{summary['converged_modes']}/{summary['mode_count']}`",
            f"- Résidu modal relatif maximal : `{float(summary['max_relative_residual']):.3e}`",
            "- Formulation de masse : `consistent_tet4`.",
        ]
    else:
        lines += [
            f"- Pas de temps : `{float(summary['time_step_seconds']):.3e}` s",
            f"- Pas Newmark : `{summary['steps']}`",
            f"- Résidu final : `{float(summary['residual_norm_final']):.3e}`",
            f"- Résidu maximal : `{float(summary['residual_norm_max']):.3e}`",
            f"- Résidu relatif maximal : `{float(summary['relative_residual_norm_max']):.3e}`",
            "- Matrice effective réutilisée : `K + 1/(beta*dt^2)*M`.",
        ]
    lines += [
        "",
        "## Limites",
        "",
        "Cette preuve couvre le modèle TET4 généré, le backend PETSc/SLEPc disponible dans l'image d'exécution et la configuration MPI indiquée. Elle ne constitue pas une qualification universelle des grands modèles ni des autres éléments.",
        "",
    ]
    return "\n".join(lines)


def _mpi_comm():
    try:
        from mpi4py import MPI
    except ImportError:
        return None
    comm = MPI.COMM_WORLD
    return comm if comm.size > 1 else None


if __name__ == "__main__":
    raise SystemExit(main())
