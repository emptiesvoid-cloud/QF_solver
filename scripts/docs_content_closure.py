"""Validate and publish the technical-content closure evidence."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from solveur.io.manifest import sha256


REGISTRY = Path("qualification/technical_content_coverage.json")
MATRIX = Path("qualification/element_analysis_matrix.json")


def load_and_validate_coverage(project_root: str | Path) -> dict[str, Any]:
    """Load the controlled registry and reject incomplete or misleading coverage."""
    root = Path(project_root).resolve()
    payload = json.loads((root / REGISTRY).read_text(encoding="utf-8"))
    matrix = json.loads((root / MATRIX).read_text(encoding="utf-8"))
    if int(payload.get("schema_version", 0)) != 1:
        raise RuntimeError("Technical-content coverage schema_version must be 1.")
    accepted_kinds = set(payload["policy"]["accepted_oracle_kinds"])
    expected = {
        (family, analysis)
        for family, family_data in matrix["families"].items()
        for analysis, declaration in family_data.items()
        if analysis != "evidence" and declaration["status"] != "unsupported"
    }
    pairs = payload.get("element_analysis_pairs", [])
    observed = {(row["family"], row["analysis"]) for row in pairs}
    duplicates = len(observed) != len(pairs)
    if duplicates or observed != expected:
        missing = sorted(expected - observed)
        unexpected = sorted(observed - expected)
        raise RuntimeError(f"Element-analysis coverage mismatch; missing={missing}, unexpected={unexpected}.")
    ids = [str(row["id"]) for row in pairs]
    if len(set(ids)) != len(ids):
        raise RuntimeError("Technical-content pair identifiers must be unique.")
    for row in pairs:
        declaration = matrix["families"][row["family"]][row["analysis"]]
        if row["status"] != declaration["status"]:
            raise RuntimeError(f"Status drift for {row['id']}: {row['status']} != {declaration['status']}.")
        oracle = row["oracle"]
        if oracle["kind"] not in accepted_kinds:
            raise RuntimeError(f"Unknown oracle kind for {row['id']}: {oracle['kind']}.")
        if oracle["kind"] == "gap_documented":
            if oracle.get("status") != "gap_documented" or len(str(oracle.get("note", ""))) < 30:
                raise RuntimeError(f"Documented gap {row['id']} needs an explicit non-pass explanation.")
        elif oracle.get("status") != "available":
            raise RuntimeError(f"Available oracle {row['id']} has inconsistent status.")
        _require_paths(root, oracle.get("evidence", []), f"oracle {row['id']}")
    loading_families = {str(row["family"]) for row in payload.get("loading_contracts", [])}
    if loading_families != set(matrix["families"]):
        raise RuntimeError("Every element family must have one explicit loading contract.")
    for row in payload["loading_contracts"]:
        _require_paths(root, [row["documentation"], *row["tests"]], f"loading contract {row['family']}")
        if not row.get("supports"):
            raise RuntimeError(f"Loading contract {row['family']} has no supported action.")
    for row in payload.get("method_correlations", []):
        _require_paths(root, [row["evidence"]], f"method {row['method']}")
    for row in payload.get("published_assets", []):
        _require_paths(root, [row["source"]], f"published asset {row['target']}")
    return payload


def publish_technical_content_closure(
    project_root: str | Path,
    generated_root: str | Path,
    asset_root: str | Path,
) -> dict[str, Any]:
    """Publish coverage tables and controlled external comparison figures."""
    root = Path(project_root).resolve()
    generated = Path(generated_root).resolve()
    assets = Path(asset_root).resolve() / "content_closure"
    generated.mkdir(parents=True, exist_ok=True)
    assets.mkdir(parents=True, exist_ok=True)
    payload = load_and_validate_coverage(root)
    artifacts: list[dict[str, Any]] = []
    for row in payload["published_assets"]:
        source = root / row["source"]
        target = assets / row["target"]
        shutil.copy2(source, target)
        artifacts.append(_artifact(target, row["caption"], assets))
    dynamic_sources = (
        (
            root / "qualification/external_reference_digests/code_aster_beam2_newmark_summary.json",
            assets / "beam2_code_aster_dynamic.png",
            "BEAM2",
        ),
        (
            root / "qualification/external_reference_digests/code_aster_discrete_summary.json",
            assets / "discrete_code_aster_dynamic.png",
            "Ressort et masse concentree",
        ),
    )
    for source, target, title in dynamic_sources:
        _plot_external_dynamic_comparison(source, target, title)
        artifacts.append(_artifact(target, f"{title}: QF_solver et Code_Aster.", assets))
    markdown_path = generated / "technical_content_coverage.md"
    markdown_path.write_text(_markdown(payload, artifacts), encoding="utf-8")
    gaps = [row["id"] for row in payload["element_analysis_pairs"] if row["oracle"]["kind"] == "gap_documented"]
    report = {
        "schema_version": 1,
        "status": "PASS_DOCUMENTATION",
        "pair_count": len(payload["element_analysis_pairs"]),
        "loading_contract_count": len(payload["loading_contracts"]),
        "method_count": len(payload["method_correlations"]),
        "documented_vnv_gaps": gaps,
        "mechanical_pass_inferred_from_gaps": False,
        "artifacts": artifacts,
        "markdown": markdown_path.name,
        "markdown_sha256": sha256(markdown_path),
    }
    (generated / "technical_content_coverage_summary.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def _require_paths(root: Path, values: list[str], label: str) -> None:
    if not values:
        raise RuntimeError(f"{label} has no evidence path.")
    missing = [value for value in values if not (root / value).is_file()]
    if missing:
        raise RuntimeError(f"Missing files for {label}: {missing}.")


def _artifact(path: Path, caption: str, asset_root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(asset_root).as_posix(),
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "caption": caption,
    }


def _plot_external_dynamic_comparison(summary_path: Path, output: Path, title: str) -> None:
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    transient = data.get("newmark", data.get("transient"))
    harmonic = data["harmonic"]
    qf_history, reference_history = _history_vectors(transient)
    dt = float(transient["time_step_s"])
    time = dt * np.arange(1, qf_history.size + 1, dtype=float)
    frequencies = np.asarray(harmonic["frequencies_hz"], dtype=float)
    qf_harmonic, reference_harmonic = _harmonic_vectors(harmonic)
    if not (
        np.all(np.isfinite(qf_history))
        and np.all(np.isfinite(reference_history))
        and np.all(np.isfinite(qf_harmonic))
        and np.all(np.isfinite(reference_harmonic))
    ):
        raise RuntimeError(f"External dynamic comparison contains non-finite values: {summary_path}.")
    figure, axes = plt.subplots(2, 1, figsize=(9.4, 8.0))
    axes[0].plot(time, qf_history, color="#0072B2", linewidth=2.0, label="QF_solver")
    axes[0].plot(time, reference_history, color="#D55E00", linewidth=1.5, linestyle="--", label="Code_Aster")
    axes[0].set_xlabel("Temps [s]")
    axes[0].set_ylabel("Deplacement sonde [m]")
    axes[0].set_title("Historique Newmark sur le meme pas de temps")
    axes[0].grid(True, color="#d5dadd", linewidth=0.6)
    axes[0].legend()
    axes[1].semilogy(frequencies, np.maximum(np.abs(qf_harmonic), 1.0e-30), "o-", color="#0072B2", label="QF_solver")
    axes[1].semilogy(
        frequencies,
        np.maximum(np.abs(reference_harmonic), 1.0e-30),
        "s--",
        color="#D55E00",
        label="Code_Aster",
    )
    axes[1].set_xlabel("Frequence [Hz]")
    axes[1].set_ylabel("Amplitude [m]")
    axes[1].set_title("Reponse harmonique sur les memes frequences")
    axes[1].grid(True, which="both", color="#d5dadd", linewidth=0.6)
    axes[1].legend()
    figure.suptitle(f"{title} - correlation externe synchronisee", fontsize=13)
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=190, bbox_inches="tight")
    plt.close(figure)


def _history_vectors(data: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    qf_key = next(key for key in data if key.startswith("qf_") and isinstance(data[key], list))
    ref_key = next(key for key in data if key.startswith("code_aster_") and isinstance(data[key], list))
    qf = np.asarray(data[qf_key], dtype=float)
    reference = np.asarray(data[ref_key], dtype=float)
    if qf.ndim != 1 or qf.shape != reference.shape or qf.size < 10:
        raise RuntimeError("Transient external histories must be matching one-dimensional arrays.")
    return qf, reference


def _harmonic_vectors(data: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    qf_key = next(key for key in data if key.startswith("qf_") and isinstance(data[key], list))
    ref_key = next(key for key in data if key.startswith("code_aster_") and isinstance(data[key], list))
    return _complex_vector(data[qf_key]), _complex_vector(data[ref_key])


def _complex_vector(values: list[Any]) -> np.ndarray:
    converted = [complex(*value) if isinstance(value, list) else complex(value) for value in values]
    return np.asarray(converted, dtype=complex)


def _markdown(payload: dict[str, Any], artifacts: list[dict[str, Any]]) -> str:
    pairs = payload["element_analysis_pairs"]
    gaps = [row for row in pairs if row["oracle"]["kind"] == "gap_documented"]
    lines = [
        "## Couverture technique regeneree",
        "",
        "Cette table ferme la lacune documentaire en distinguant une preuve disponible d'un ecart V&V documente.",
        "Un ecart documente n'est jamais transforme en validation mecanique.",
        "",
        f"- couples element-analyse declares : **{len(pairs)}** ;",
        f"- contrats de chargement : **{len(payload['loading_contracts'])}** ;",
        f"- methodes correlees : **{len(payload['method_correlations'])}** ;",
        f"- ecarts V&V explicites : **{len(gaps)}**.",
        "",
        "### Contrats de chargement",
        "",
        "| Famille | Actions supportees | Documentation |",
        "| --- | --- | --- |",
    ]
    for row in payload["loading_contracts"]:
        lines.append(f"| {row['family']} | {', '.join(row['supports'])} | `{row['documentation']}` |")
    lines.extend(
        [
            "",
            "### Couples element-analyse et oracles",
            "",
            "| Couple | Statut mecanique conserve | Oracle | Etat de preuve | Conclusion bornee |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in pairs:
        oracle = row["oracle"]
        lines.append(
            f"| {row['family']} / {row['analysis']} | `{row['status']}` | {oracle['kind']} | "
            f"`{oracle['status']}` | {oracle['note']} |"
        )
    lines.extend(
        [
            "",
            "### Correlation des methodes",
            "",
            "| Methode | Base de comparaison | Preuve |",
            "| --- | --- | --- |",
        ]
    )
    for row in payload["method_correlations"]:
        lines.append(f"| `{row['method']}` | {row['oracle']} | `{row['evidence']}` |")
    lines.extend(["", "### Vues comparees et convergences", ""])
    for artifact in artifacts:
        lines.extend(
            [
                f"![{artifact['caption']}](../assets/generated/content_closure/{artifact['path']}){{ .result-figure }}",
                "",
                f"*{artifact['caption']} Empreinte SHA-256 : `{artifact['sha256']}`.*",
                "",
            ]
        )
    lines.extend(["### Ecarts V&V maintenus ouverts", ""])
    for row in gaps:
        lines.append(f"- **{row['id']}** : {row['oracle']['note']}")
    lines.extend(
        [
            "",
            "Ces ecarts ne bloquent pas la lisibilite du manuel, mais interdisent toute extrapolation de maturite.",
        ]
    )
    return "\n".join(lines) + "\n"


def finite_plot_data(path: str | Path) -> bool:
    """Small public test helper used to reject empty generated comparison PNGs."""
    target = Path(path)
    return target.is_file() and target.stat().st_size > 10_000 and math.isfinite(float(target.stat().st_size))
