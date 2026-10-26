"""Build a provenance index and plots from the six existing HEX8-SRI archives.

This offline report builder only reads manifests, controller receipts, JSON
sidecars, and NPZ arrays. It does not import solveur/campaign code and has no
assembly, solve, modal, or eigenvalue path.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import sys
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.hex8_sri_equilibrium.archive_audit import (  # noqa: E402
    load_npz_arrays,
    recompute_archived_state,
    sha256_file,
)


CAMPAIGN_DIR = Path("investigations/hex8_sri_equilibrium_20261026/campaign_preparation")
CAMPAIGN_ID = "HEX8-SRI-CANTILEVER-6-2026-10-26"
CASE_ORDER = (
    "hex8_standard_nu_0p3",
    "sri_historical_nu_0p3",
    "sri_corrected_nu_0p3",
    "hex8_standard_nu_0p4999",
    "sri_historical_nu_0p4999",
    "sri_corrected_nu_0p4999",
)
FORMULATION_LABELS = {
    "hex8_standard": "HEX8 standard",
    "sri_historical": "SRI historique",
    "sri_corrected": "SRI corrigé",
}


class EvidenceError(RuntimeError):
    """Raised when an archive cannot be linked or verified without guessing."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot read JSON evidence {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"JSON evidence is not an object: {path}")
    return value


def _logical_path(path: Path, root: Path, namespace: str) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise EvidenceError(f"evidence path escapes its declared root: {path}") from exc
    return f"{namespace}/{relative.as_posix()}"


def _same_number(left: Any, right: Any) -> bool:
    try:
        return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=0.0)
    except (TypeError, ValueError):
        return False


def _find_run_record(run_store: Path, case_id: str, manifest_sha: str) -> tuple[Path, dict[str, Any]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in run_store.glob("worktrees/hex8sri/dev-*/attempt-0001/run.json"):
        record = _read_json(path)
        binding = record.get("case_manifest")
        if isinstance(binding, dict) and binding.get("case_id") == case_id and binding.get("sha256") == manifest_sha:
            matches.append((path, record))
    if len(matches) != 1:
        raise EvidenceError(f"expected one runner record for {case_id}/{manifest_sha}, found {len(matches)}")
    return matches[0]


def _validate_and_collect(
    repo_root: Path,
    controller_root: Path,
    archive_root: Path,
    run_store: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    repo_root = repo_root.resolve()
    controller_root = controller_root.resolve()
    archive_root = archive_root.resolve()
    run_store = run_store.resolve()
    campaign_dir = repo_root / CAMPAIGN_DIR
    expected_files = {
        f"{kind}_{case}_attempt-001.{suffix}"
        for case in CASE_ORDER
        for kind, suffix in (("sidecar", "json"), ("state", "npz"))
    }
    present_files = {path.name for path in archive_root.iterdir() if path.is_file()}
    if present_files != expected_files:
        raise EvidenceError(
            f"archive inventory differs: missing={sorted(expected_files - present_files)}, "
            f"unexpected={sorted(present_files - expected_files)}"
        )

    runner_path = controller_root / "scripts/development_autonomous.py"
    policy_path = controller_root / "development_autonomous_policy.json"
    plugin_path = controller_root / "scripts/development_autonomous_pytest_plugin.py"
    controller_identity = {
        "branch": "codex/hex8sri-controller-registration",
        "runner_sha256": sha256_file(runner_path),
        "policy_sha256": sha256_file(policy_path),
        "pytest_plugin_sha256": sha256_file(plugin_path),
    }
    cases: list[dict[str, Any]] = []
    inventory: dict[str, dict[str, Any]] = {}

    def add_evidence(
        path: Path, root: Path, namespace: str, kind: str, expected_sha: str | None = None
    ) -> dict[str, Any]:
        if not path.is_file():
            raise EvidenceError(f"MISSING_ARTIFACT: {path}")
        actual_sha = sha256_file(path)
        if expected_sha is not None and actual_sha != expected_sha:
            raise EvidenceError(f"INTEGRITY_MISMATCH: {path}, expected {expected_sha}, got {actual_sha}")
        logical = _logical_path(path, root, namespace)
        entry = {"ref": logical, "kind": kind, "bytes": path.stat().st_size, "sha256": actual_sha}
        existing = inventory.get(logical)
        if existing is not None and existing != entry:
            raise EvidenceError(f"conflicting evidence index entry for {logical}")
        inventory[logical] = entry
        return entry

    source_file_hashes_seen: dict[str, str] = {}
    for case_id in CASE_ORDER:
        manifest_path = campaign_dir / f"manifest_{case_id}.json"
        manifest = _read_json(manifest_path)
        manifest_sha = sha256_file(manifest_path)
        if manifest.get("case_id") != case_id or manifest.get("campaign_id") != CAMPAIGN_ID:
            raise EvidenceError(f"manifest identity mismatch for {case_id}")
        if manifest.get("execution_authorized") is not True or manifest.get("do_not_execute") is not False:
            raise EvidenceError(f"authorized campaign manifest flags mismatch for {case_id}")

        manifest_item = add_evidence(manifest_path, repo_root, "science", "authorized_manifest", manifest_sha)
        problem_relative = Path(manifest["common_problem"]["path"])
        problem_path = (manifest_path.parent / problem_relative).resolve()
        problem_item = add_evidence(
            problem_path,
            campaign_dir,
            "science_campaign_preparation",
            "common_problem",
            manifest["common_problem"]["sha256"],
        )
        for relative, expected_sha in manifest.get("source_files_sha256", {}).items():
            source_path = (repo_root / relative).resolve()
            add_evidence(source_path, repo_root, "science", "fingerprinted_source", expected_sha)
            prior = source_file_hashes_seen.setdefault(relative, expected_sha)
            if prior != expected_sha:
                raise EvidenceError(f"inconsistent source hash inventory for {relative}")

        run_path, run = _find_run_record(run_store, case_id, manifest_sha)
        if run.get("state") != "PASS" or run.get("attempt") != 1 or run.get("return_code") != 0:
            raise EvidenceError(f"runner status/attempt mismatch for {case_id}")
        if run.get("target") != [manifest.get("exact_nodeid")]:
            raise EvidenceError(f"runner nodeid mismatch for {case_id}")
        run_provenance = run.get("controller_provenance", {})
        run_sha = run_provenance.get("sha256", {})
        if (
            run_sha.get("runner") != controller_identity["runner_sha256"]
            or run_sha.get("policy") != controller_identity["policy_sha256"]
            or run_sha.get("pytest_plugin") != controller_identity["pytest_plugin_sha256"]
        ):
            raise EvidenceError(f"controller provenance mismatch for {case_id}")
        if run.get("source_fingerprint") != manifest.get("source_fingerprint_sha256"):
            raise EvidenceError(f"source fingerprint mismatch for {case_id}")

        attempt_dir = run_path.parent
        run_item = add_evidence(run_path, run_store, "controller_runs", "runner_record")
        log_items: list[dict[str, Any]] = []
        for output in run.get("output_inventory", []):
            relative = Path(str(output["path"]))
            output_path = (attempt_dir / "output" / relative).resolve()
            log_items.append(add_evidence(output_path, run_store, "controller_runs", "captured_log", output["sha256"]))

        receipt_path = Path(run["preflight_receipt"]["path"]).resolve()
        receipt = _read_json(receipt_path)
        receipt_hash = sha256_file(receipt_path)
        if receipt_hash != run["preflight_receipt"]["sha256"]:
            raise EvidenceError(f"preflight receipt hash link mismatch for {case_id}")
        if (
            receipt.get("state") != "PREFLIGHT_PASS"
            or receipt.get("bodies_executed") is not False
            or receipt.get("target") != manifest.get("exact_nodeid")
            or receipt.get("source_fingerprint") != manifest.get("source_fingerprint_sha256")
            or receipt.get("case_manifest", {}).get("sha256") != manifest_sha
        ):
            raise EvidenceError(f"preflight receipt binding mismatch for {case_id}")
        receipt_item = add_evidence(receipt_path, run_store, "controller_runs", "preflight_receipt", receipt_hash)
        receipt_checksum_path = receipt_path.with_name("preflight.sha256.json")
        checksum = _read_json(receipt_checksum_path)
        if checksum.get("sha256") != receipt_hash:
            raise EvidenceError(f"preflight receipt sidecar checksum mismatch for {case_id}")
        receipt_checksum_item = add_evidence(
            receipt_checksum_path, run_store, "controller_runs", "preflight_receipt_checksum"
        )

        sidecar_path = archive_root / f"sidecar_{case_id}_attempt-001.json"
        state_path = archive_root / f"state_{case_id}_attempt-001.npz"
        sidecar = _read_json(sidecar_path)
        sidecar_hash = sha256_file(sidecar_path)
        state_hash = sha256_file(state_path)
        sidecar_manifest = sidecar.get("manifest_identity", {})
        sidecar_state = sidecar.get("state_artifact", {})
        if sidecar_manifest.get("sha256") != manifest_sha:
            raise EvidenceError(f"sidecar manifest hash mismatch for {case_id}")
        if Path(sidecar_manifest.get("path", "")).resolve() != manifest_path.resolve():
            raise EvidenceError(f"sidecar manifest path mismatch for {case_id}")
        if sidecar_state.get("sha256") != state_hash:
            raise EvidenceError(f"sidecar state hash mismatch for {case_id}")
        if Path(sidecar_state.get("path", "")).resolve() != state_path.resolve():
            raise EvidenceError(f"sidecar state path mismatch for {case_id}")
        if sidecar.get("science_identity", {}).get("source_fingerprint_sha256") != manifest.get(
            "source_fingerprint_sha256"
        ):
            raise EvidenceError(f"sidecar scientific fingerprint mismatch for {case_id}")
        if sidecar.get("controller_identity", {}).get("runner_sha256") != controller_identity["runner_sha256"]:
            raise EvidenceError(f"sidecar runner hash mismatch for {case_id}")

        sidecar_item = add_evidence(sidecar_path, archive_root, "archive", "run_sidecar", sidecar_hash)
        state_item = add_evidence(state_path, archive_root, "archive", "state_npz", state_hash)
        arrays = load_npz_arrays(state_path)
        recomputed = recompute_archived_state(arrays)
        observed = sidecar["observables"]
        comparisons = {
            "free_residual_l2_N": observed["free_residual_l2_N"],
            "support_reaction_resultant_N": observed["support_reaction_resultant_N"],
            "force_closure_N": observed["force_closure_N"],
            "moment_closure_Nm": observed["moment_closure_Nm"],
            "internal_energy_J": observed["internal_energy_J"],
            "external_load_work_J": observed["external_load_work_J"],
            "energy_defect_J": observed["energy_defect_J"],
            "condition_number_2_Kff": observed["condition_number_2_Kff"],
        }
        diffs: dict[str, float] = {}
        exact_recomputation = True
        for name, archived_value in comparisons.items():
            actual_value = recomputed[name]
            if isinstance(archived_value, list):
                error = float(np.max(np.abs(np.asarray(actual_value) - np.asarray(archived_value)), initial=0.0))
                same = error == 0.0
            else:
                error = abs(float(actual_value) - float(archived_value))
                same = _same_number(actual_value, archived_value)
            diffs[name] = error
            exact_recomputation = exact_recomputation and same

        normalized_energy_from_archive = abs(float(observed["energy_defect_J"])) / max(
            abs(float(observed["external_load_work_J"])), np.finfo(float).tiny
        )
        # The legacy field used max(|W|, 1.0), so its value has units of energy
        # for this campaign and is not a dimensionless relative error.
        recorded_energy_field_matches_correct_relative = _same_number(
            observed.get("energy_defect_normalized"), normalized_energy_from_archive
        )

        run_identity = run.get("identity", {})
        science_identity = sidecar.get("science_identity", {})
        if (
            science_identity.get("head") != run_identity.get("head")
            or science_identity.get("branch") != run_identity.get("branch")
            or science_identity.get("source_fingerprint_sha256") != run.get("source_fingerprint")
        ):
            raise EvidenceError(f"run/sidecar source identities differ for {case_id}")
        if run.get("preflight_receipt", {}).get("sha256") != receipt_item["sha256"]:
            raise EvidenceError(f"run/preflight direct hash binding mismatch for {case_id}")

        cases.append(
            {
                "case_id": case_id,
                "manifest": manifest,
                "manifest_evidence": manifest_item,
                "common_problem_evidence": problem_item,
                "run": run,
                "run_evidence": run_item,
                "captured_log_evidence": log_items,
                "preflight": receipt,
                "preflight_evidence": receipt_item,
                "preflight_checksum_evidence": receipt_checksum_item,
                "sidecar": sidecar,
                "sidecar_evidence": sidecar_item,
                "state_evidence": state_item,
                "recomputed": recomputed,
                "recomputation_absolute_differences": diffs,
                "recomputation_matches_stored_precision": exact_recomputation,
                "correct_energy_identity_relative": normalized_energy_from_archive,
                "recorded_energy_normalized_field_matches_dimensionless_value": recorded_energy_field_matches_correct_relative,
            }
        )

    for relative, kind in (
        (Path("investigations/hex8_sri_equilibrium_20261026/report.md"), "prior_research_report"),
        (
            Path("investigations/hex8_sri_equilibrium_20261026/compare_element_operators.py"),
            "prior_element_operator_analysis_script",
        ),
        (
            Path("investigations/hex8_sri_equilibrium_20261026/operator_comparison_results.json"),
            "prior_element_operator_analysis_result",
        ),
    ):
        add_evidence(repo_root / relative, repo_root, "science", kind)

    analytic_test_archive = repo_root / ".codex/development-runs/standard/unit/dev-hex8-sri-quadrature"
    if not analytic_test_archive.is_dir():
        raise EvidenceError(f"MISSING_ARTIFACT: analytic test archive {analytic_test_archive}")
    for path in sorted(item for item in analytic_test_archive.rglob("*") if item.is_file()):
        add_evidence(path, repo_root, "science", "analytic_test_attempt_evidence")

    provenance = {
        "campaign_id": CAMPAIGN_ID,
        "science_fingerprint": cases[0]["manifest"].get("source_fingerprint_sha256"),
        "science_run_identity": cases[0]["sidecar"].get("science_identity"),
        "controller_identity": cases[0]["sidecar"].get("controller_identity"),
        "controller_current_code_hashes": controller_identity,
        "archive_file_count": len(present_files),
        "archive_inventory_status": "PASS_EXACTLY_SIX_SIDECARS_AND_SIX_NPZ_STATES",
        "runner_has_direct_sidecar_or_state_sha_bindings": False,
        "linkage_limit": (
            "run.json binds the exact preflight receipt hash and manifest hash, but does not contain sidecar/state hashes; "
            "run-to-sidecar association is reconstructed from the unique nodeid, manifest SHA, science fingerprint, "
            "controller identity, and sidecar state path/hash."
        ),
        "spectral_eigenvalue_postprocessing": "NOT_RUN_BY_REPORT_BUILDER",
        "files": sorted(inventory.values(), key=lambda item: item["ref"]),
        "cases": cases,
    }
    return cases, provenance


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_results_csv(path: Path, cases: list[dict[str, Any]]) -> None:
    columns = (
        "case_id",
        "formulation",
        "poisson_ratio",
        "signed_mean_loaded_face_UZ_m",
        "displacement_l2_m",
        "max_abs_gauss_strain_dimensionless",
        "internal_energy_J",
        "external_load_work_J",
        "energy_defect_J",
        "recomputed_energy_identity_relative",
        "free_residual_l2_N",
        "relative_free_residual",
        "support_reaction_resultant_x_N",
        "support_reaction_resultant_y_N",
        "support_reaction_resultant_z_N",
        "force_closure_l2_N",
        "force_closure_relative",
        "moment_closure_l2_Nm",
        "moment_closure_relative",
        "condition_number_2_Kff",
        "assembly_seconds",
        "solve_seconds",
        "controller_elapsed_seconds",
        "controller_peak_rss_bytes",
        "run_state",
        "energy_defect_gate",
        "force_moment_gate",
        "spatial_convergence_gate",
        "manifest_sha256",
        "preflight_id",
        "preflight_sha256",
        "runner_record_sha256",
        "sidecar_sha256",
        "state_npz_sha256",
        "recomputation_matches_stored_precision",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for case in cases:
            sidecar = case["sidecar"]
            observable = sidecar["observables"]
            run = case["run"]
            row: dict[str, Any] = {
                "case_id": case["case_id"],
                "formulation": sidecar["case"]["formulation"],
                "poisson_ratio": sidecar["case"]["poisson_ratio"],
                "signed_mean_loaded_face_UZ_m": observable["signed_mean_loaded_face_UZ_m"],
                "displacement_l2_m": observable["displacement_l2_m"],
                "max_abs_gauss_strain_dimensionless": float(
                    np.max(np.abs(np.asarray(observable["gauss_strain_dimensionless"])))
                ),
                "internal_energy_J": observable["internal_energy_J"],
                "external_load_work_J": observable["external_load_work_J"],
                "energy_defect_J": observable["energy_defect_J"],
                "recomputed_energy_identity_relative": case["correct_energy_identity_relative"],
                "free_residual_l2_N": observable["free_residual_l2_N"],
                "relative_free_residual": observable["relative_free_residual"],
                "support_reaction_resultant_x_N": observable["support_reaction_resultant_N"][0],
                "support_reaction_resultant_y_N": observable["support_reaction_resultant_N"][1],
                "support_reaction_resultant_z_N": observable["support_reaction_resultant_N"][2],
                "force_closure_l2_N": observable["force_closure_l2_N"],
                "force_closure_relative": observable["force_closure_relative"],
                "moment_closure_l2_Nm": observable["moment_closure_l2_Nm"],
                "moment_closure_relative": observable["moment_closure_relative"],
                "condition_number_2_Kff": observable["condition_number_2_Kff"],
                "assembly_seconds": observable["timing_seconds"]["assembly"],
                "solve_seconds": observable["timing_seconds"]["solve"],
                "controller_elapsed_seconds": run["elapsed_seconds"],
                "controller_peak_rss_bytes": run["peak_rss_bytes"],
                "run_state": run["state"],
                "energy_defect_gate": sidecar["criteria_verdicts"]["energy_defect"],
                "force_moment_gate": sidecar["criteria_verdicts"]["force_and_moment_closure"],
                "spatial_convergence_gate": sidecar["criteria_verdicts"]["spatial_convergence"],
                "manifest_sha256": case["manifest_evidence"]["sha256"],
                "preflight_id": case["preflight"]["preflight_id"],
                "preflight_sha256": case["preflight_evidence"]["sha256"],
                "runner_record_sha256": case["run_evidence"]["sha256"],
                "sidecar_sha256": case["sidecar_evidence"]["sha256"],
                "state_npz_sha256": case["state_evidence"]["sha256"],
                "recomputation_matches_stored_precision": case["recomputation_matches_stored_precision"],
            }
            writer.writerow(row)


def _write_pairwise_matrix_differences(path: Path, archive_root: Path, cases: list[dict[str, Any]]) -> None:
    """Compare only archived global matrices and displacement vectors; never assemble or solve."""

    lookup = {
        (case["sidecar"]["case"]["formulation"], float(case["sidecar"]["case"]["poisson_ratio"])): case
        for case in cases
    }
    formulations = ("hex8_standard", "sri_historical", "sri_corrected")
    labels = {
        "hex8_standard": "HEX8 standard",
        "sri_historical": "SRI historique",
        "sri_corrected": "SRI corrigé",
    }
    pairs = ((formulations[0], formulations[1]), (formulations[0], formulations[2]), (formulations[1], formulations[2]))
    columns = (
        "comparison_basis",
        "poisson_ratio",
        "formulation_a",
        "formulation_b",
        "global_K_frobenius_difference",
        "global_K_relative_to_a",
        "displacement_l2_difference_m",
        "displacement_relative_to_a",
        "source_a_state_sha256",
        "source_b_state_sha256",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for poisson_ratio in (0.3, 0.4999):
            for formulation_a, formulation_b in pairs:
                case_a = lookup[(formulation_a, poisson_ratio)]
                case_b = lookup[(formulation_b, poisson_ratio)]
                arrays_a = load_npz_arrays(archive_root / f"state_{case_a['case_id']}_attempt-001.npz")
                arrays_b = load_npz_arrays(archive_root / f"state_{case_b['case_id']}_attempt-001.npz")
                stiffness_a = np.asarray(arrays_a["K"], dtype=float)
                stiffness_b = np.asarray(arrays_b["K"], dtype=float)
                displacement_a = np.asarray(arrays_a["u_m"], dtype=float)
                displacement_b = np.asarray(arrays_b["u_m"], dtype=float)
                matrix_difference = float(np.linalg.norm(stiffness_b - stiffness_a, ord="fro"))
                displacement_difference = float(np.linalg.norm(displacement_b - displacement_a))
                writer.writerow(
                    {
                        "comparison_basis": "POSTPROCESS_ARCHIVED_K_AND_U_ONLY",
                        "poisson_ratio": poisson_ratio,
                        "formulation_a": labels[formulation_a],
                        "formulation_b": labels[formulation_b],
                        "global_K_frobenius_difference": matrix_difference,
                        "global_K_relative_to_a": matrix_difference
                        / max(float(np.linalg.norm(stiffness_a, ord="fro")), np.finfo(float).tiny),
                        "displacement_l2_difference_m": displacement_difference,
                        "displacement_relative_to_a": displacement_difference
                        / max(float(np.linalg.norm(displacement_a)), np.finfo(float).tiny),
                        "source_a_state_sha256": case_a["state_evidence"]["sha256"],
                        "source_b_state_sha256": case_b["state_evidence"]["sha256"],
                    }
                )


def _write_figures(path: Path, cases: list[dict[str, Any]]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    styles = {
        "hex8_standard": ("HEX8 standard", "#3366cc", "o"),
        "sri_historical": ("SRI historique", "#dd4477", "s"),
        "sri_corrected": ("SRI corrigé", "#109618", "^"),
    }
    formulations = ("hex8_standard", "sri_historical", "sri_corrected")
    poisson = (0.3, 0.4999)
    lookup = {
        (case["sidecar"]["case"]["formulation"], case["sidecar"]["case"]["poisson_ratio"]): case for case in cases
    }

    figure, axis = plt.subplots(figsize=(8.2, 4.8), constrained_layout=True)
    x = np.arange(len(poisson), dtype=float)
    width = 0.23
    for index, formulation in enumerate(formulations):
        label, color, marker = styles[formulation]
        values = [
            abs(lookup[(formulation, nu)]["sidecar"]["observables"]["signed_mean_loaded_face_UZ_m"]) * 1000.0
            for nu in poisson
        ]
        axis.bar(x + (index - 1) * width, values, width, label=label, color=color, alpha=0.86)
        axis.plot(x + (index - 1) * width, values, marker=marker, color="black", linewidth=0.0)
    axis.set_xticks(x, ("ν = 0,3", "ν = 0,4999"))
    axis.set_ylabel("Déplacement moyen chargé |UZ| (mm)")
    axis.set_title("Réponse archivée sur un maillage 4 × 2 × 2")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(frameon=False)
    figure.savefig(path / "loaded_face_displacement.svg", format="svg")
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(8.2, 4.8), constrained_layout=True)
    for formulation in formulations:
        label, color, marker = styles[formulation]
        values = [lookup[(formulation, nu)]["sidecar"]["observables"]["condition_number_2_Kff"] for nu in poisson]
        axis.plot(poisson, values, marker=marker, color=color, linewidth=1.8, label=label)
    axis.set_yscale("log")
    axis.set_xlabel("Coefficient de Poisson ν")
    axis.set_ylabel("cond₂(Kff), matrice archivée")
    axis.set_title("Conditionnement des six états archivés")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend(frameon=False)
    figure.savefig(path / "condition_number.svg", format="svg")
    plt.close(figure)
    for svg_path in path.glob("*.svg"):
        svg_lines = svg_path.read_text(encoding="utf-8").splitlines()
        svg_path.write_text("\n".join(line.rstrip() for line in svg_lines) + "\n", encoding="utf-8")


def build_report(
    *, repo_root: Path, controller_root: Path, archive_root: Path, run_store: Path, output_dir: Path
) -> dict[str, Any]:
    """Validate evidence and write derived reports outside the frozen archives."""

    repo_root = Path(repo_root).resolve()
    archive_root = Path(archive_root).resolve()
    run_store = Path(run_store).resolve()
    output_dir = Path(output_dir).resolve()
    if output_dir == archive_root or output_dir.is_relative_to(archive_root):
        raise EvidenceError("consolidated output must remain outside the original campaign archive")
    if output_dir == run_store or output_dir.is_relative_to(run_store):
        raise EvidenceError("consolidated output must remain outside the controller run store")

    cases, evidence = _validate_and_collect(repo_root, controller_root, archive_root, run_store)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "EVIDENCE_INDEX.json", evidence)
    _write_results_csv(output_dir / "SIX_CASES_RESULTS.csv", cases)
    _write_pairwise_matrix_differences(output_dir / "FORMULATION_PAIRWISE_DIFFERENCES.csv", archive_root, cases)
    _write_figures(output_dir / "figures", cases)
    sums = "".join(f"{item['sha256']}  {item['ref']}\n" for item in evidence["files"])
    (output_dir / "SHA256SUMS.txt").write_text(sums, encoding="utf-8")
    return evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--controller-root", type=Path, required=True)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--run-store", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / CAMPAIGN_DIR.parent / "consolidated")
    args = parser.parse_args(argv)
    try:
        evidence = build_report(
            repo_root=args.repo_root,
            controller_root=args.controller_root,
            archive_root=args.archive_root,
            run_store=args.run_store,
            output_dir=args.output_dir,
        )
    except EvidenceError as exc:
        print(f"EVIDENCE_AUDIT_REFUSED: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "state": evidence["archive_inventory_status"],
                "case_count": len(evidence["cases"]),
                "file_count": len(evidence["files"]),
                "output_dir": str(args.output_dir.resolve()),
                "spectral_eigenvalue_postprocessing": evidence["spectral_eigenvalue_postprocessing"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
