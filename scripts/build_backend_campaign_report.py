"""Aggregate the reproducible 0.2.2 alpha backend evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from solveur.io.evidence_verifier import EvidenceBundleVerifier

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "qualification" / "benchmarks" / "qf_solver_0_2_2_backend_campaign"


def main() -> int:
    static = _load(ROOT / "qualification/benchmarks/qf_solver_0_2_2_multi_million_campaign_docker/campaign.json")
    graph = _load(OUTPUT / "graph_2m_r2/summary.json")
    graph_r4 = _load(OUTPUT / "graph_2m_r4/summary.json")
    matrix_free = _load(OUTPUT / "matrix_free_100k/summary.json")
    comparison = _load(OUTPUT / "backend_comparison_1k/backend_comparison.json")
    modal_100k = _load(OUTPUT / "modal_100k_r2/modal_large.json")
    modal_1k = _load(OUTPUT / "modal_1k/modal_large.json")
    newmark_2m = _load(OUTPUT / "newmark_2m_r2/transient_large.json")
    newmark_1k = _load(OUTPUT / "newmark_1k/transient_large.json")
    modal_limit = _load(OUTPUT / "modal_2m_resource_limit/attempt.json")

    graph_time_r2 = float(graph.get("assembly_time_seconds", 0.0)) + float(graph.get("solve_time_seconds", 0.0))
    graph_time_r4 = float(graph_r4.get("assembly_time_seconds", 0.0)) + float(graph_r4.get("solve_time_seconds", 0.0))
    graph_efficiency = graph_time_r2 / max(2.0 * graph_time_r4, 1.0e-30)
    static_scaling = static.get("strong_scaling", [])
    static_efficiency = {
        str(int(item.get("target_dofs", 0))): float(item.get("strong_efficiency", 0.0))
        for item in static_scaling
        if isinstance(item, dict)
    }
    checks = {
        "static_contiguous": static.get("qualification_status") == "PASS_BOUNDED_DOCKER",
        "static_graph": graph.get("audit_status") == "PASS" and graph_r4.get("audit_status") == "PASS" and graph_efficiency >= 0.6,
        "matrix_free_bounded": matrix_free.get("audit_status") == "PASS" and matrix_free.get("solver", {}).get("converged", False),
        "backend_comparison": comparison.get("status") == "PASS",
        "modal_bounded": modal_100k.get("status") == "PASS" and modal_1k.get("status") == "PASS",
        "newmark_multi_million": newmark_2m.get("status") == "PASS",
        "evidence_manifests": all(
            _manifest_pass(path)
            for path in (
                "graph_2m_r2/evidence_manifest.json",
                "graph_2m_r4/evidence_manifest.json",
                "matrix_free_100k/evidence_manifest.json",
                "modal_100k_r2/evidence_manifest.json",
                "modal_1k/evidence_manifest.json",
                "newmark_2m_r2/evidence_manifest.json",
                "newmark_1k/evidence_manifest.json",
            )
        ),
    }
    payload: dict[str, Any] = {
        "schema_version": 1,
        "campaign_id": "QF-SOLVER-0.2.2-ALPHA-BACKEND-001",
        "status": "PASS_BOUNDED_BACKEND_CAMPAIGN" if all(checks.values()) else "OPEN",
        "scope_status": "development",
        "checks": checks,
        "image": {
            "name": "qf-solver-large:0.2.0",
            "digest": "sha256:f2a7931d0543ee142ce67847bb91bf59350a947d5d4874bfe7be43b6848a49c8",
        },
        "evidence": {
            "static_contiguous": "../qf_solver_0_2_2_multi_million_campaign_docker/campaign.json",
            "graph_2m": {"r2": graph, "r4": graph_r4},
            "matrix_free_100k": matrix_free,
            "backend_comparison_1k": {
                "status": comparison.get("status"),
                "backends_completed": comparison.get("backends_completed", []),
                "comparisons": comparison.get("comparisons", []),
            },
            "modal_100k": modal_100k,
            "modal_1k": modal_1k,
            "newmark_2m": newmark_2m,
            "newmark_1k": newmark_1k,
            "modal_2m_resource_limit": modal_limit,
        },
        "acceptance": {
            "static_strong_scaling_efficiency": {"2m": static_efficiency.get("2000000", 0.0), "4m": static_efficiency.get("4000000", 0.0)},
            "graph_strong_scaling_efficiency_2m": graph_efficiency,
            "modal_100k_max_relative_residual": float(modal_100k.get("max_relative_residual", 0.0)),
            "modal_1k_max_relative_residual": float(modal_1k.get("max_relative_residual", 0.0)),
            "newmark_2m_relative_residual_max": float(newmark_2m.get("relative_residual_norm_max", 0.0)),
            "newmark_1k_relative_residual_max": float(newmark_1k.get("relative_residual_norm_max", 0.0)),
            "matrix_free_100k_relative_residual": float(matrix_free.get("solver", {}).get("relative_residual", 0.0)),
        },
        "limitations": [
            "La preuve est executee dans une image Docker epinglee, sur une seule configuration hote.",
            "Le statique couvre 2M et 4M DDL ; le Newmark couvre 2M DDL avec PETSc/GAMG.",
            "Le modal SLEPc est demontre jusqu a 107811 DDL ; le shift-invert direct 2M a ete tue par la limite de ressources.",
            "Le matrix-free est demontre a 107811 DDL ; la tentative 1M reste une limite de performance.",
            "Les resultats restent development jusqu a la revue Owner et ne constituent pas une promotion stable.",
        ],
    }
    _write(OUTPUT / "campaign.json", payload)
    _write_markdown(OUTPUT / "campaign.md", payload)
    print(f"BACKEND CAMPAIGN: {payload['status']}")
    return 0 if payload["status"] == "PASS_BOUNDED_BACKEND_CAMPAIGN" else 1


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest_pass(relative_path: str) -> bool:
    return EvidenceBundleVerifier().verify(OUTPUT / relative_path).status == "PASS"


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    evidence = payload["evidence"]
    acceptance = payload["acceptance"]
    lines = [
        "# Campagne backend 0.2.2 alpha",
        "",
        f"Statut technique : **{payload['status']}**. Le statut de maturite reste **development** jusqu a la revue Owner.",
        "",
        "## Preuves fermees dans le perimetre borne",
        "",
        f"- Statique PETSc contigu : campagne 2M/4M DDL, efficacites fortes `{acceptance['static_strong_scaling_efficiency']['2m']:.3f}` et `{acceptance['static_strong_scaling_efficiency']['4m']:.3f}`.",
        f"- Statique PETSc graphe/PT-Scotch : 2M DDL, efficacite forte `{acceptance['graph_strong_scaling_efficiency_2m']:.3f}`.",
        f"- Matrix-free : `{evidence['matrix_free_100k']['ndof']}` DDL, residu relatif `{acceptance['matrix_free_100k_relative_residual']:.3e}`.",
        f"- Comparaison SciPy/matrix-free/PETSc : statut `{evidence['backend_comparison_1k']['status']}`, trois backends completes.",
        f"- Modal SLEPc : `{evidence['modal_100k']['ndof']}` DDL, trois modes, residu relatif maximal `{acceptance['modal_100k_max_relative_residual']:.3e}`.",
        f"- Newmark PETSc/GAMG : `{evidence['newmark_2m']['ndof']}` DDL, `{evidence['newmark_2m']['steps']}` pas, residu relatif maximal `{acceptance['newmark_2m_relative_residual_max']:.3e}`.",
        "",
        "## Limites explicitement conservees",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["limitations"])
    lines.extend(
        [
            "",
            "Les manifestes d evidence sont verifies dans chaque dossier de campagne. Les comparaisons numeriques ne constituent pas une qualification des formulations FEM ni une decision de release.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
