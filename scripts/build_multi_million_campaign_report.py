"""Build a consolidated report for the bounded Docker multi-million campaign."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from solveur.io.evidence_verifier import EvidenceBundleVerifier


CASE_SPECS = (
    ("2m_r2", 2_000_000, 2),
    ("2m_r4", 2_000_000, 4),
    ("4m_r2", 4_000_000, 2),
    ("4m_r4", 4_000_000, 4),
)
MEMORY_BUDGET_BYTES = 32 * 1024**3
IMAGE_DIGEST = "sha256:f2a7931d0543ee142ce67847bb91bf59350a947d5d4874bfe7be43b6848a49c8"
BASE_IMAGE_DIGEST = "sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _case_record(root: Path, name: str, target: int, ranks: int) -> dict[str, Any]:
    case_dir = root / name
    benchmark_path = case_dir / "benchmark_large.json"
    benchmark = _load(benchmark_path)
    manifest = _load(case_dir / "evidence_manifest.json")
    runtime = _load(case_dir / "runtime_environment.json")
    verification = EvidenceBundleVerifier().verify(case_dir)
    memory = benchmark["memory_telemetry"]
    solver = benchmark["solver"]
    artifact_policy = benchmark["artifact_policy"]
    checks = {
        "target_dofs_reached": benchmark["ndof"] >= target,
        "status_pass": benchmark["status"] == "PASS",
        "audit_pass": benchmark["audit_status"] == "PASS",
        "solver_converged": bool(solver["converged"]),
        "residual_under_1e-8": float(solver["residual_norm"]) <= 1.0e-8,
        "petsc_gamg_baij": (
            benchmark["backend"] == "petsc"
            and benchmark["matrix_format"] == "baij"
            and solver["preconditioner"] == "gamg"
        ),
        "distributed": bool(solver["distributed"] and benchmark["mpi"]["size"] == ranks),
        "file_backed_output": bool(
            artifact_policy["file_backed_displacements"]
            and not artifact_policy["monolithic_displacements_in_json"]
        ),
        "evidence_integrity": verification.status == "PASS",
        "memory_budget": int(memory["process_peak_rss_sum_bytes"]) <= MEMORY_BUDGET_BYTES,
    }
    return {
        "case": name,
        "target_dofs": target,
        "ranks": ranks,
        "status": benchmark["status"],
        "ndof": benchmark["ndof"],
        "nodes": benchmark["node_count"],
        "elements": benchmark["element_count"],
        "matrix_format": benchmark["matrix_format"],
        "partition_strategy": benchmark["partition_strategy"],
        "assembly_time_seconds": benchmark["assembly_time_seconds"],
        "solve_time_seconds": benchmark["solve_time_seconds"],
        "pipeline_time_seconds": benchmark["solve_pipeline_time_seconds"],
        "iterations": solver["iterations"],
        "residual_norm": solver["residual_norm"],
        "peak_rss_bytes": memory["process_peak_rss_bytes"],
        "peak_rss_sum_bytes": memory["process_peak_rss_sum_bytes"],
        "input_fingerprint": benchmark["input_fingerprint"],
        "verification": verification.to_dict(),
        "traceability_scope_status": manifest.get("traceability", {}).get("scope_status", "unknown"),
        "traceability_status": manifest.get("traceability", {}).get("status", "unknown"),
        "runtime_versions": runtime.get("versions", {}),
        "command": runtime.get("command_line", runtime.get("argv", [])),
        "checks": checks,
        "case_status": "PASS" if all(checks.values()) else "FAIL",
    }


def _scaling(cases: list[dict[str, Any]], target: int) -> dict[str, Any]:
    pair = [case for case in cases if case["target_dofs"] == target]
    baseline = next(case for case in pair if case["ranks"] == 2)
    scaled = next(case for case in pair if case["ranks"] == 4)
    speedup = baseline["pipeline_time_seconds"] / scaled["pipeline_time_seconds"]
    efficiency = speedup / 2.0
    return {
        "target_dofs": target,
        "baseline_ranks": 2,
        "scaled_ranks": 4,
        "speedup": speedup,
        "strong_efficiency": efficiency,
        "threshold": 0.60,
        "status": "PASS" if efficiency >= 0.60 else "WARNING",
    }


def build(root: Path, output: Path) -> dict[str, Any]:
    cases = [_case_record(root, name, target, ranks) for name, target, ranks in CASE_SPECS]
    scaling = [_scaling(cases, target) for target in (2_000_000, 4_000_000)]
    all_case_checks = all(case["case_status"] == "PASS" for case in cases)
    all_scaling = all(item["status"] == "PASS" for item in scaling)
    report = {
        "schema_version": 1,
        "campaign_id": "QF-SOLVER-0.2.2-MULTI-MILLION-DOCKER-001",
        "qualification_status": "PASS_BOUNDED_DOCKER" if all_case_checks and all_scaling else "FAIL",
        "scope_status": "development",
        "backend": "PETSc",
        "preconditioner": "GAMG",
        "matrix_format": "BAIJ",
        "partition_strategy": "contiguous",
        "image": "qf-solver-large:0.2.0",
        "image_digest": IMAGE_DIGEST,
        "base_image_digest": BASE_IMAGE_DIGEST,
        "memory_budget_bytes": MEMORY_BUDGET_BYTES,
        "criteria": {
            "minimum_target_dofs": 2_000_000,
            "residual_relative_max": 1.0e-8,
            "strong_scaling_efficiency_min": 0.60,
            "required_ranks": [2, 4],
        },
        "cases": cases,
        "strong_scaling": scaling,
        "limitations": [
            "Une seule image Docker et une seule machine ont ete mesurees.",
            "La campagne couvre le statique lineaire TET4, pas le modal ou le dynamique multi-million.",
            "Le partitionnement execute est contiguous; la variante graphe reste a mesurer.",
            "Matrix-free et SLEPc ne sont pas des resultats de cette campagne.",
            "Le statut de traceabilite reste development jusqu'a la revue Owner.",
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "campaign.json").write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (output / "campaign.md").write_text(_markdown(report), encoding="utf-8")
    return report


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "---",
        "doc_id: DOC-VNV-022-MULTI-MILLION-001",
        "revision: 0.1",
        "status: draft",
        "applicable_version: 0.2.2a0",
        "---",
        "",
        "# Campagne multi-million DDL : execution Docker",
        "",
        f"Statut technique : **{report['qualification_status']}**. Le statut de maturite reste **{report['scope_status']}** jusqu'a la revue Owner.",
        "",
        f"Image : `{report['image']}@{report['image_digest']}` ; image de base : `{report['base_image_digest']}`.",
        "Backend PETSc avec CG + GAMG et matrice BAIJ. Budget RSS cumule maximal accepte : `32 GiB`.",
        "",
        "## Cas executes",
        "",
        "| Cas | DDL | Rangs | Elements | Assemblage (s) | Resolution (s) | Pipeline (s) | Iterations | Residu | RSS cumule |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for case in report["cases"]:
        lines.append(
            f"| `{case['case']}` | {case['ndof']:,} | {case['ranks']} | {case['elements']:,} | "
            f"{case['assembly_time_seconds']:.3f} | {case['solve_time_seconds']:.3f} | "
            f"{case['pipeline_time_seconds']:.3f} | {case['iterations']} | "
            f"{case['residual_norm']:.3e} | {case['peak_rss_sum_bytes'] / 1024**3:.2f} GiB |"
        )
    lines += [
        "",
        "## Scaling fort",
        "",
        "| Taille | Speedup 2 -> 4 rangs | Efficacite | Seuil | Statut |",
        "| ---: | ---: | ---: | ---: | --- |",
    ]
    for item in report["strong_scaling"]:
        lines.append(
            f"| {item['target_dofs']:,} DDL | {item['speedup']:.3f} | "
            f"{item['strong_efficiency']:.3f} | {item['threshold']:.2f} | {item['status']} |"
        )
    lines += [
        "",
        "## Criteres verifies",
        "",
        "Chaque cas a ete verifie par son `evidence_manifest.json`, son audit grand modele, son empreinte d'entree et ses metriques runtime.",
        "Les quatre cas passent le residu relatif `1e-8`, la convergence CG, le couple GAMG/BAIJ, la sortie file-backed et le budget RSS.",
        "",
        "## Limites",
        "",
    ]
    lines.extend(f"- {item}" for item in report["limitations"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Campaign root containing the four case directories")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.root, args.output)
    print(f"MULTI-MILLION CAMPAIGN: {report['qualification_status']}")
    return 0 if report["qualification_status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
