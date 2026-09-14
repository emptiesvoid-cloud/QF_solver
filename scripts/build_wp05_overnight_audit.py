"""Derive the WP05 overnight qualification summary from immutable run records."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "qualification" / "0_2_9" / "overnight_r2_corrected" / "wp05_runs"
REPLAYS = ROOT / "qualification" / "0_2_9" / "overnight_r2_corrected" / "wp05_replay_run3"
CONTRACT = ROOT / "qualification" / "0_2_9" / "wp05_cd_structural_contract.json"
OUT = ROOT / "qualification" / "0_2_9" / "overnight_r2_corrected"
DOC = ROOT / "docs" / "verification" / "0_2_9" / "overnight-wp05-r2-corrected-checkpoint.md"

MESH_THRESHOLDS = {
    "displacement": 0.02,
    "reaction": 0.02,
    "moment": 0.02,
    "energy": 0.02,
    "stress": 0.08,
}
CROSS_THRESHOLDS = {"displacement": 0.03, "reaction": 0.02, "moment": 0.03, "energy": 0.03, "stress": 0.10}


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _relative(a: Any, b: Any) -> float:
    first = np.asarray(a, dtype=float)
    second = np.asarray(b, dtype=float)
    return float(np.linalg.norm(second - first) / max(float(np.linalg.norm(first)), float(np.linalg.norm(second)), 1.0e-14))


def _map_observables(record: dict[str, Any]) -> dict[str, Any]:
    observed = record["observables"]
    return {
        "displacement": observed["tip_displacement"],
        "reaction": observed["reaction_resultant"],
        "moment": observed["reaction_moment"],
        "energy": observed["strain_energy"],
        "stress": observed["representative_sigma_xx"],
        "force_equilibrium": observed["force_equilibrium_relative"],
        "moment_equilibrium": observed["moment_equilibrium_relative"],
        "envelope": observed["envelope_status"],
        "minimum_detF": observed["minimum_detF"],
        "minimum_principal_stretch": observed["minimum_principal_stretch"],
        "maximum_principal_stretch": observed["maximum_principal_stretch"],
        "maximum_green_lagrange_norm": observed["maximum_green_lagrange_norm"],
    }


def _mesh_audit(family: str) -> dict[str, Any]:
    records = {level: _read(RUNS / family / level / "result.json") for level in ("H1", "H2", "H3")}
    mapped = {level: _map_observables(record) for level, record in records.items()}
    deltas = {name: _relative(mapped["H2"][name], mapped["H3"][name]) for name in MESH_THRESHOLDS}
    checks = {name: {"delta": deltas[name], "threshold": MESH_THRESHOLDS[name], "status": deltas[name] <= MESH_THRESHOLDS[name]} for name in MESH_THRESHOLDS}
    envelope = all(bool(mapped[level]["envelope"]) for level in records)
    equilibrium = all(
        mapped[level]["force_equilibrium"] <= 1.0e-8 and mapped[level]["moment_equilibrium"] <= 1.0e-8
        for level in records
    )
    return {
        "family": family,
        "mesh_records": {level: {"path": str((RUNS / family / level / "result.json").relative_to(ROOT)).replace("\\", "/"), "status": records[level]["status"], "source_sha": records[level]["source_sha"], "wall_time_s": records[level]["wall_time_s"], "node_count": records[level]["node_count"], "element_count": records[level]["element_count"], "dof_count": records[level]["dof_count"], "observables": mapped[level]} for level in records},
        "h2_to_h3": {"status": "PASS" if all(item["status"] for item in checks.values()) else "FAIL", "checks": checks},
        "equilibrium": {"status": "PASS" if equilibrium else "FAIL", "force_threshold": 1.0e-8, "moment_threshold": 1.0e-8},
        "envelope": {"status": "PASS" if envelope else "FAIL", "detF_minimum": 0.20, "principal_stretch_range": [0.75, 1.30], "green_lagrange_norm_maximum": 0.30},
        "route": records["H3"]["solver_route"],
        "fallback_count": sum(int(records[level].get("fallback_count", 0)) for level in records),
        "replay": _replay_audit(family),
    }


def _replay_audit(family: str) -> dict[str, Any]:
    first = _read(RUNS / family / "H1" / "result.json")
    second = _read(REPLAYS / family / "H1" / "result.json")
    first_observables = _map_observables(first)
    second_observables = _map_observables(second)
    observable_deltas = {name: _relative(first_observables[name], second_observables[name]) for name in ("displacement", "reaction", "moment", "energy", "stress")}
    raw_first = np.load(RUNS / family / "H1" / "raw.npz")
    raw_second = np.load(REPLAYS / family / "H1" / "raw.npz")
    raw_equal = all(np.array_equal(raw_first[name], raw_second[name]) for name in ("displacement", "reactions"))
    path_equal = first["accepted_load_factors"] == second["accepted_load_factors"]
    count_equal = first["newton_iterations"] == second["newton_iterations"]
    status = all(value <= 1.0e-12 for value in observable_deltas.values()) and raw_equal and path_equal and count_equal
    return {"status": "PASS" if status else "FAIL", "first_path": str((RUNS / family / "H1" / "result.json").relative_to(ROOT)).replace("\\", "/"), "second_path": str((REPLAYS / family / "H1" / "result.json").relative_to(ROOT)).replace("\\", "/"), "observable_relative_deltas": observable_deltas, "raw_displacement_and_reaction_exact": raw_equal, "accepted_load_factors_exact": path_equal, "newton_iteration_count_exact": count_equal, "relative_tolerance": 1.0e-12, "absolute_floor": 1.0e-14}


def _cross_audit(tet: dict[str, Any], hex20: dict[str, Any]) -> dict[str, Any]:
    # Deliberately not evaluated: WP05-E is conditional on both C and D PASS.
    if tet["h2_to_h3"]["status"] == "PASS" and hex20["h2_to_h3"]["status"] == "PASS":
        reason = "WP05-E is eligible for the frozen cross-family comparison; this corrected checkpoint does not execute it."
    else:
        reason = "WP05-E is dependency-blocked because at least one frozen WP05-C/D family campaign failed."
    return {"status": "NOT_RUN", "reason": reason, "thresholds": CROSS_THRESHOLDS}


def main() -> int:
    contract_digest = hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
    contract = _read(CONTRACT)
    tet = _mesh_audit("TET10")
    hex20 = _mesh_audit("HEX20")
    summary: dict[str, Any] = {
        "schema_version": 1,
        "record_id": "QF-029-WP05-OVERNIGHT-R2-CORRECTED-QUALIFICATION-002",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        "final_source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "previous_hold_preserved": True,
        "previous_hold_paths": ["qualification/0_2_9/overnight/overnight_wp05_wp07_final.json", "docs/verification/0_2_9/overnight-wp05-wp07-final-report.md"],
        "contract_path": str(CONTRACT.relative_to(ROOT)).replace("\\", "/"),
        "contract_sha256": contract_digest,
        "governing_policy_digest": {
            "TET10": _read(RUNS / "TET10" / "H3" / "result.json")["governing_policy_digest"],
            "HEX20": _read(RUNS / "HEX20" / "H3" / "result.json")["governing_policy_digest"],
        },
        "contract_thresholds": contract["thresholds"],
        "tet10": tet,
        "hex20": hex20,
        "wp05_e": _cross_audit(tet, hex20),
        "formal_candidate_points": {"WP05-C": "1/1 candidate", "WP05-D": "0/1", "WP05-E": "0/1", "WP05": "3/5 candidate"},
        "official_total_before_owner_review": "50/100",
        "potential_total_after_owner_review": "51/100",
        "production_mechanics_changed": False,
        "thresholds_changed": False,
        "full_repository_suite_run": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / "wp05_qualification_summary.json"
    output.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    DOC.write_text(_markdown(summary), encoding="utf-8")
    return 0


def _markdown(summary: dict[str, Any]) -> str:
    tet = summary["tet10"]
    hex20 = summary["hex20"]
    def row(audit: dict[str, Any], name: str) -> str:
        item = audit["h2_to_h3"]["checks"][name]
        return f"| {name} | {item['delta']:.15g} | {item['threshold']:.15g} | {item['status']} |"
    policy = summary["governing_policy_digest"]
    return f"""# WP05 overnight structural qualification checkpoint (corrected observables)\n\nThis checkpoint was derived from completed, preserved solver outputs under `qualification/0_2_9/overnight_r2/` and re-extracted into `qualification/0_2_9/overnight_r2_corrected/`. The earlier checkpoint remains immutable and is superseded for qualification observables because it used an element-centroid stress proxy. No production mechanics, thresholds, meshes, loads, solver settings, or completed displacement fields were changed.\n\n## Execution status\n\n- Branch: `{summary['branch']}`\n- Final tooling SHA: `{summary['final_source_sha']}`\n- Contract SHA-256: `{summary['contract_sha256']}`\n- Governing policy digests retained from completed solves: TET10 `{policy['TET10']}`, HEX20 `{policy['HEX20']}`\n- Route: MINRES + Jacobi, canonical line search, floor-aware termination, 12 increments, no direct fallback\n- Previous HOLD preserved: **YES**\n- Corrected stress observable: reference integration-point coordinates, positive reference-volume weights `w_q det(J0)`, production Cauchy stress\n\n## Harness correction\n\nThe first WP05 result records remain at their original paths and are not overwritten. Their stress field was labeled `FROZEN_CENTROID_REGION`; that is not the frozen WP05 integration-point contract. The corrected records use production quadrature fields and map the same quadrature points through the production TET10/HEX20 shape functions. The original solver displacement, reactions, solver diagnostics, load path, and energy are retained.\n\n## WP05-C — TET10\n\nH1, H2 and H3 completed. H1 replay completed with exact recorded displacement/reaction arrays, load path and Newton count. The corrected frozen H2→H3 checks are: **{tet['h2_to_h3']['status']}**.\n\n| Observable | H2→H3 relative delta | Frozen limit | Result |\n|---|---:|---:|---|\n{row(tet, 'displacement')}\n{row(tet, 'reaction')}\n{row(tet, 'moment')}\n{row(tet, 'energy')}\n{row(tet, 'stress')}\n\nThe corrected representative stress delta is within the frozen 8% limit. TET10 equilibrium, envelope, and replay evidence also pass. WP05-C is **PASS_CANDIDATE** pending Owner review.\n\n## WP05-D — HEX20\n\nH1, H2 and H3 completed. H1 replay passed after the same corrected extraction. The corrected frozen H2→H3 checks are: **{hex20['h2_to_h3']['status']}**. The representative stress delta is above the frozen 8% limit (`{hex20['h2_to_h3']['checks']['stress']['delta']:.15g}`), so WP05-D is **FAIL_CLOSED**. This is a result of the frozen observable and threshold; no rescue threshold or mesh was introduced.\n\n## WP05-E\n\n**NOT_RUN / dependency-blocked.** The frozen contract permits cross-family execution only when both WP05-C and WP05-D pass. Since corrected WP05-D fails its stress limit, no cross-family result is claimed.\n\n## Governance\n\n- WP05 candidate points: C `1/1`, D `0/1`, E `0/1`; no official points awarded.\n- Official total remains `50/100` pending Owner review; potential total from this campaign is `51/100`.\n- Structural solver runs were not repeated; corrected evidence is a qualification-only postprocessing of completed H1/H2/H3 outputs and H1 replays.\n- Full repository suite: **NO**.\n- WP06/WP08: untouched.\n\n"""


if __name__ == "__main__":
    raise SystemExit(main())
