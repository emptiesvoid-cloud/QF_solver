"""Create non-authorized manifests for the first 24-case HEX8-SRI lot.

This builder writes source/controller identities and preparation metadata only.
It never imports or calls the convergence FEM driver, performs assembly, runs
pytest, or creates preflight receipts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PLAN_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PLAN_DIR / "first_convergence_24" / "drafts"
MATRIX_SOURCE = ROOT / "investigations/hex8_sri_equilibrium_20261026/NEXT_CAMPAIGN_MATRIX.csv"
CAMPAIGN_ID = "HEX8-SRI-CONVERGENCE-24-2026-10-27"
ARTIFACT_ROOT = "E:/QFSolverAgents/hex8sri-runs/HEX8-SRI-CONVERGENCE-24-2026-10-27-owner-authorized"
THREADS = {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}
PROPOSED_CRITERIA = {
    "free_residual_relative_max": 1.0e-7,
    "force_closure_relative_max": 1.0e-6,
    "moment_closure_relative_max": 1.0e-6,
    "energy_identity_relative_max": 1.0e-8,
    "last_two_levels_mean_UZ_relative_change_max": 0.02,
    "last_two_levels_energy_relative_change_max": 0.02,
    "finest_level_independent_3d_mean_UZ_relative_error_max": 0.05,
    "finest_level_independent_3d_energy_relative_error_max": 0.05,
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_new(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
    return sha256_bytes(payload)


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def controller_source_fingerprint(nodeid: str) -> str:
    runner_path = ROOT / "scripts/development_autonomous.py"
    spec = importlib.util.spec_from_file_location("hex8sri_first_campaign_fingerprint", runner_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the source-fingerprint implementation")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module._worktree_source_fingerprint(ROOT, nodeid)


def source_inventory(nodeid: str) -> dict[str, str]:
    listed = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "src/solveur",
            "experiments",
            "tests",
            "pyproject.toml",
            "pytest.ini",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    target_module = nodeid.split("::", maxsplit=1)[0]
    selected: set[str] = set()
    for raw in listed.stdout.split(b"\0"):
        if not raw:
            continue
        relative = Path(raw.decode("utf-8").replace("\\", "/"))
        name = relative.as_posix()
        if (
            name.startswith("src/solveur/")
            and relative.suffix == ".py"
            or name.startswith("experiments/")
            and relative.suffix == ".py"
            or name == target_module
            or name in {"tests/conftest.py", "tests/unit/conftest.py", "pyproject.toml", "pytest.ini"}
        ):
            selected.add(name)
    if target_module not in selected:
        raise RuntimeError(f"test module not inventoried: {target_module}")
    return {name: sha256_bytes((ROOT / name).read_bytes()) for name in sorted(selected)}


def load_selected_rows() -> list[dict[str, str]]:
    with MATRIX_SOURCE.open(newline="", encoding="utf-8") as stream:
        all_rows = list(csv.DictReader(stream))
    selected = [
        row
        for row in all_rows
        if float(row["poisson_ratio"]) in (0.3, 0.4999)
        and row["mesh_elements_xyz"] in {"4x2x2", "8x4x4", "16x8x8", "32x16x16"}
    ]
    if len(selected) != 24:
        raise RuntimeError(f"expected exactly 24 selected rows, found {len(selected)}")
    return selected


def case_id_for(row: dict[str, str]) -> str:
    return row["test_nodeid_proposal"].split("[", maxsplit=1)[1][:-1].replace("-nu_", "_nu_").replace("-", "_")


def _case_geometry(row: dict[str, str]) -> dict[str, Any]:
    nx, ny, nz = (int(value) for value in row["mesh_elements_xyz"].split("x"))
    return {
        "dimensions_L_y_z_m": [20.0, 1.0, 1.0],
        "divisions_xyz": [nx, ny, nz],
        "element_count": int(row["element_count"]),
        "node_count": int(row["node_count"]),
        "dof_count": int(row["dof_count"]),
        "fixed_dof_count": int(row["fixed_dof_count"]),
        "free_dof_count": int(row["free_dof_count"]),
        "element_aspect_ratio_xyz": [10.0, 1.0, 1.0],
    }


def _budgets(row: dict[str, str]) -> dict[str, Any]:
    return {
        "timeout_seconds": int(row["wall_budget_seconds"]),
        "rss_soft_limit_mib": int(row["memory_budget_mib"]),
        "process_tree_limit": 8,
        "output_total_limit_mib": 16,
        "output_stream_limit_mib": 8,
        "temporary_limit_mib": 512,
        "archive_size_limit_mib": 256,
        "minimum_free_disk_mib": 2048,
        "attempts_per_nodeid": 1,
        "initial_campaign_max_attempts": 24,
        "blas_thread_environment": THREADS,
        "budget_semantics": {
            "rss_process_temporary_archive": "sampled soft observations, not OS quotas",
            "captured_output": "controller-enforced byte caps",
            "wall_timeout": "watchdog process-tree termination, best effort",
        },
    }


def build_case_manifest(
    row: dict[str, str],
    *,
    source_head: str,
    fingerprint: str,
    inventory: dict[str, str],
    controller_hashes: dict[str, str],
    controller_identity: dict[str, str],
    common_sha: str,
) -> dict[str, Any]:
    nodeid = row["test_nodeid_proposal"]
    case_id = case_id_for(row)
    formulation = row["formulation"]
    poisson_ratio = float(row["poisson_ratio"])
    mesh = _case_geometry(row)
    operators = {
        "hex8_standard": {
            "element_type": "Hex8Element",
            "operator": "complete 2x2x2 Gauss integration",
        },
        "sri_historical": {
            "element_type": "HistoricalHex8SRIElement",
            "operator": "frozen parent-source central volumetric expression without weight 8",
            "historical_source_commit": "2aa994f34900f39bef8df9db5fb025157fb694bb",
        },
        "sri_corrected": {
            "element_type": "Hex8SRIElement",
            "operator": "corrected central volumetric integration with weight 8",
        },
    }
    return {
        "schema": "qfsolver-hex8-sri-structural-case-v2",
        "campaign_id": CAMPAIGN_ID,
        "case_id": case_id,
        "execution_authorized": False,
        "execution_state": "PREPARED_NOT_AUTHORIZED",
        "do_not_execute": True,
        "criteria_status": "PROPOSED_REQUIRES_OWNER_FREEZE",
        "qualification": "NOT_APPLICABLE_DEVELOPMENT_ONLY",
        "qualification_promotion": "PROHIBITED",
        "science_branch": "research/hex8-sri-equilibrium",
        "science_source_commit": source_head,
        "source_fingerprint_sha256": fingerprint,
        "source_files_sha256": inventory,
        "controller_registration_id": "hex8sri",
        "controller_code_sha256": controller_hashes,
        "controller_identity": controller_identity,
        "controller_identity_status": "PROVISIONAL_CURRENT_CONTROLLER_REQUIRES_EXTENSION",
        "common_problem": {"path": "common_problem.json", "sha256": common_sha},
        "exact_nodeid": nodeid,
        "formulation": {"id": formulation, **operators[formulation]},
        "poisson_ratio": poisson_ratio,
        "mesh": mesh,
        "material": {"young_modulus_pa": 1.0e6, "poisson_ratio": poisson_ratio},
        "loading": {
            "loaded_face": "x=20 m",
            "uniform_traction_pa": [0.0, 0.0, -1.0],
            "face_area_m2": 1.0,
            "resultant_force_n": [0.0, 0.0, -1.0],
            "resultant_moment_about_origin_nm": [-0.5, 20.0, 0.0],
            "consistent_q1_surface_weights": True,
        },
        "boundary_conditions": {"fixed_face": "x=0", "fixed_components": ["UX", "UY", "UZ"]},
        "oracle": {
            "timoshenko_trend_only": True,
            "independent_3d_reference": "NOT_IMPLEMENTED_OR_QUALIFIED",
            "precision_gate_enabled": False,
        },
        "proposed_criteria": PROPOSED_CRITERIA,
        "frozen_criteria": None,
        "budgets": _budgets(row),
        "attempt_number": 1,
        "retry_allowed": False,
        "execution_artifact_root": ARTIFACT_ROOT,
        "state_artifact_format": "compressed NPZ containing CSR K, mesh, F, u, residuals, reactions, strains and Jacobians",
        "state_artifact_excludes": "per-element 24x24 stiffness stack",
        "preflight_status": "NOT_RUN_CONTROLLER_REGISTRATION_REQUIRED",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controller-runner-sha256", required=True)
    parser.add_argument("--controller-plugin-sha256", required=True)
    parser.add_argument("--controller-policy-sha256", required=True)
    parser.add_argument("--controller-branch", required=True)
    parser.add_argument("--controller-head", required=True)
    args = parser.parse_args()
    if git("branch", "--show-current") != "research/hex8-sri-equilibrium":
        raise RuntimeError("convergence drafts must be built on the dedicated science branch")
    source_status = git(
        "status", "--porcelain", "--", "src/solveur", "experiments", "tests", "pyproject.toml", "pytest.ini"
    )
    if source_status:
        raise RuntimeError(
            f"source and test files must be committed and clean before freezing drafts:\n{source_status}"
        )

    sys.path.insert(0, str(ROOT))
    from experiments.hex8_sri_equilibrium.campaign_spec import convergence_nodeid

    rows = load_selected_rows()
    first_nodeid = rows[0]["test_nodeid_proposal"]
    expected_nodeid = convergence_nodeid("hex8_standard", 0.3, (4, 2, 2))
    if first_nodeid != expected_nodeid:
        raise RuntimeError(f"campaign matrix nodeid drift: {first_nodeid} != {expected_nodeid}")
    source_head = git("rev-parse", "HEAD")
    fingerprint = controller_source_fingerprint(first_nodeid)
    inventory = source_inventory(first_nodeid)
    controller_hashes = {
        "runner": args.controller_runner_sha256,
        "pytest_plugin": args.controller_plugin_sha256,
        "policy": args.controller_policy_sha256,
    }
    controller_identity = {
        "branch": args.controller_branch,
        "head": args.controller_head,
        "runner_sha256": args.controller_runner_sha256,
        "pytest_plugin_sha256": args.controller_plugin_sha256,
        "policy_sha256": args.controller_policy_sha256,
    }
    if any(
        len(controller_hashes[key]) != 64 or any(ch not in "0123456789abcdef" for ch in controller_hashes[key])
        for key in ("runner", "pytest_plugin", "policy")
    ):
        raise ValueError("controller identities must be lowercase 64-character SHA-256 values")
    if controller_identity["branch"] != "codex/hex8sri-controller-registration":
        raise ValueError("controller branch must name the dedicated HEX8-SRI registration branch")
    if len(controller_identity["head"]) != 40 or any(
        ch not in "0123456789abcdef" for ch in controller_identity["head"]
    ):
        raise ValueError("controller HEAD must be a lowercase 40-character Git commit")

    common = {
        "schema": "qfsolver-hex8-sri-convergence-common-v1",
        "campaign_id": CAMPAIGN_ID,
        "status": "PREPARED_NOT_AUTHORIZED",
        "source_identity": {
            "branch": "research/hex8-sri-equilibrium",
            "source_commit": source_head,
            "source_fingerprint_sha256": fingerprint,
            "source_files_sha256": inventory,
        },
        "controller_identity": controller_identity,
        "model": {
            "dimensions_L_y_z_m": [20.0, 1.0, 1.0],
            "young_modulus_pa": 1.0e6,
            "poisson_ratios": [0.3, 0.4999],
            "fixed_face": "x=0, all translations",
            "loaded_face": "x=20 m",
            "traction_pa": [0.0, 0.0, -1.0],
            "loaded_area_m2": 1.0,
            "resultant_force_n": [0.0, 0.0, -1.0],
            "resultant_moment_about_origin_nm": [-0.5, 20.0, 0.0],
            "mean_loaded_face_uz": "Q1 consistent surface-area integral / area; not arithmetic node mean",
        },
        "formulations": ["hex8_standard", "sri_historical", "sri_corrected"],
        "meshes_xyz": [[4, 2, 2], [8, 4, 4], [16, 8, 8], [32, 16, 16]],
        "attempts_per_case": 1,
        "retry_allowed": False,
        "total_cases": 24,
        "timoshenko_reference": {
            "shear_factor_5_over_6_abs_tip_deflection_mm": {"0.3": 32.0624, "0.4999": 32.0719952},
            "cowper_rectangular_factor_abs_tip_deflection_mm": {"0.3": 32.0612, "0.4999": 32.0699956},
            "use": "scale/sign/trend only; not a 3-D error gate",
        },
        "independent_3d_reference": {
            "status": "NOT_IMPLEMENTED_OR_QUALIFIED",
            "proposed_family": "mixed displacement-pressure P2/P1 tetrahedral linear elasticity in an independent FEM code",
            "environment": "backend absent from current interpreter; source/version/container not frozen",
            "uncertainty_target_relative": 0.005,
        },
        "proposed_criteria": PROPOSED_CRITERIA,
        "criteria_status": "OWNER_FREEZE_REQUIRED_BEFORE_EXECUTION",
        "preflight_status": "NOT_RUN_CONTROLLER_REGISTRATION_REQUIRED",
    }
    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    common_bytes = json_bytes(common)
    common_sha = write_new(output_dir / "common_problem.json", common_bytes)
    manifest_shas: dict[str, str] = {}
    output_rows: list[dict[str, str]] = []
    for row in rows:
        case_id = case_id_for(row)
        nodeid = row["test_nodeid_proposal"]
        if controller_source_fingerprint(nodeid) != fingerprint:
            raise RuntimeError("source fingerprint unexpectedly varies across the shared test module")
        manifest = build_case_manifest(
            row,
            source_head=source_head,
            fingerprint=fingerprint,
            inventory=inventory,
            controller_hashes=controller_hashes,
            controller_identity=controller_identity,
            common_sha=common_sha,
        )
        name = f"manifest_{case_id}.json"
        digest = write_new(output_dir / name, json_bytes(manifest))
        manifest_shas[name] = digest
        output_row = dict(row)
        output_row["case_id"] = case_id
        output_row["campaign_status"] = "PREPARED_NOT_AUTHORIZED"
        output_row["entry_status"] = "IMPLEMENTED_UNREGISTERED"
        output_row["source_fingerprint_sha256"] = fingerprint
        output_row["manifest_sha256"] = digest
        output_row["preflight_status"] = "NOT_RUN_CONTROLLER_REGISTRATION_REQUIRED"
        output_row["independent_reference_status"] = "NOT_IMPLEMENTED_OR_QUALIFIED"
        output_rows.append(output_row)

    registration_request = {
        "schema": "qfsolver-hex8sri-controller-registration-request-v1",
        "status": "PREPARED_NOT_AUTHORIZED",
        "controller_registration_id": "hex8sri",
        "requires_controller_extension": True,
        "preserve_existing_scopes_and_six_hex8sri_bindings": True,
        "science_source_commit": source_head,
        "science_source_fingerprint_sha256": fingerprint,
        "controller_identity_provisional": controller_identity,
        "exact_nodeids": [row["test_nodeid_proposal"] for row in output_rows],
        "manifest_map": {
            row["test_nodeid_proposal"]: {
                "path": f"investigations/hex8_sri_equilibrium_20261026/campaign_preparation/first_convergence_24/drafts/manifest_{row['case_id']}.json",
                "sha256": row["manifest_sha256"],
            }
            for row in output_rows
        },
        "per_node_budgets": {row["test_nodeid_proposal"]: _budgets(row) for row in rows},
        "preflights": "NOT_RUN; official controller currently rejects the new nodeids and budget shape",
        "execution_authorized": False,
    }
    registration_sha = write_new(output_dir / "registration_request.json", json_bytes(registration_request))

    matrix_path = output_dir / "FIRST_CAMPAIGN_MATRIX.csv"
    fieldnames = list(output_rows[0])
    matrix_bytes_file = matrix_path.open("x", newline="", encoding="utf-8")
    with matrix_bytes_file as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)
    matrix_sha = sha256_bytes(matrix_path.read_bytes())
    request_lines = [
        "# Décision Owner demandée — préparation du premier lot de convergence",
        "",
        "**Statut : `PREPARED_NOT_AUTHORIZED`. Cette demande ne couvre aucun calcul FEM.**",
        "",
        f"- Branche scientifique : `research/hex8-sri-equilibrium`; HEAD `{source_head}`.",
        f"- Fingerprint scientifique : `{fingerprint}`.",
        f"- Contrôleur actuel (provisoire) : `{controller_identity['branch']}` à `{controller_identity['head']}`.",
        f"- Runner SHA-256 `{controller_hashes['runner']}`, plugin `{controller_hashes['pytest_plugin']}`, policy `{controller_hashes['policy']}`.",
        f"- Campagne : `{CAMPAIGN_ID}`, {len(output_rows)} cas, une tentative par nodeid, aucun retry.",
        "",
        "## Décision sollicitée",
        "",
        "Autoriser Configuration à proposer et vérifier, sur sa branche dédiée, une extension minimale du scope HEX8-SRI pour ces 24 nodeids, puis à produire un collect-only officiel par nodeid après succès de ses contrôles. L’extension doit préserver D01/C01/E01, les six inscriptions historiques, les préflights légitimes et le verrou FEM. Le runner transmettra le chemin du manifeste exclusivement depuis l’entrée enregistrée via `QF_DEV_MANIFEST_PATH` et vérifiera son SHA-256.",
        "",
        "Cette décision ne transforme aucun manifeste en autorisé et ne lance pas les tests. Après extension revue, les manifests et préflights seront liés aux nouvelles identités contrôleur; une demande Owner distincte portera sur les exécutions scientifiques et les critères gelés.",
        "",
        "## Cas et SHA-256 des manifests brouillons",
        "",
        "| Cas | Nodeid exact | Mesh / ν / formulation | Budget proposé | SHA-256 manifest |",
        "|---|---|---|---|---|",
    ]
    for row in output_rows:
        budget = _budgets(row)
        request_lines.append(
            "| `{case_id}` | `{nodeid}` | `{mesh}` / `{nu}` / `{formulation}` | `"
            "{timeout}s, {rss} MiB RSS souple` | `{sha}` |".format(
                case_id=row["case_id"],
                nodeid=row["test_nodeid_proposal"],
                mesh=row["mesh_elements_xyz"],
                nu=row["poisson_ratio"],
                formulation=row["formulation"],
                timeout=budget["timeout_seconds"],
                rss=budget["rss_soft_limit_mib"],
                sha=row["manifest_sha256"],
            )
        )
    request_lines.extend(
        [
            "",
            "## État des preuves",
            "",
            f"`common_problem.json` SHA-256 `{common_sha}`; `registration_request.json` SHA-256 `{registration_sha}`; `FIRST_CAMPAIGN_MATRIX.csv` SHA-256 `{matrix_sha}`.",
            "Tous les manifests portent `execution_authorized=false`, `do_not_execute=true` et `criteria_status=PROPOSED_REQUIRES_OWNER_FREEZE`. Aucun préflight n’existe.",
            "",
        ]
    )
    write_new(output_dir / "OWNER_DECISION_REQUEST.md", "\n".join(request_lines).encode("utf-8"))
    readme = (
        "# Première campagne HEX8-SRI de convergence\n\n"
        "Tous les manifests de ce dossier sont préparation uniquement (`execution_authorized=false`, `do_not_execute=true`). "
        "Le contrôleur courant n’inscrit pas les 24 nodeids; aucun préflight n’a été produit. "
        "Les identités contrôleur sont provisoires et devront être recalculées après l’extension approuvée.\n\n"
        f"Source HEAD: `{source_head}`\n\nFingerprint scientifique: `{fingerprint}`\n\n"
        f"Cases: 24; SHA common_problem: `{common_sha}`; SHA registration_request: `{registration_sha}`; SHA matrix: `{matrix_sha}`.\n\n"
        "Voir [la demande de décision Owner](OWNER_DECISION_REQUEST.md) et [la demande d’extension contrôleur](../CONTROLLER_EXTENSION_REQUEST.md).\n"
    )
    write_new(output_dir / "README.md", readme.encode("utf-8"))

    evidence_hashes = {
        name: sha256_bytes((output_dir / name).read_bytes())
        for name in sorted(
            [
                "common_problem.json",
                "registration_request.json",
                "FIRST_CAMPAIGN_MATRIX.csv",
                "OWNER_DECISION_REQUEST.md",
                "README.md",
                *manifest_shas,
            ]
        )
    }
    sums = "".join(f"{digest}  {name}\n" for name, digest in evidence_hashes.items())
    sums_sha = write_new(output_dir / "SHA256SUMS.txt", sums.encode("utf-8"))
    print(
        json.dumps(
            {
                "campaign_id": CAMPAIGN_ID,
                "case_count": len(output_rows),
                "science_source_commit": source_head,
                "source_fingerprint_sha256": fingerprint,
                "common_problem_sha256": common_sha,
                "registration_request_sha256": registration_sha,
                "matrix_sha256": matrix_sha,
                "sha256sums_file_sha256": sums_sha,
                "preflight_status": "NOT_RUN_CONTROLLER_REGISTRATION_REQUIRED",
                "execution_authorized": False,
                "output_dir": str(output_dir),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
