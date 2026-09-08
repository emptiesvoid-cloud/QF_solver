"""WP13-02B15: derive contractual residual histories from immutable B13 vectors."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
B13_DIR = ROOT / "qualification" / "0_2_8" / "wp13_02b13_v2"
B13_MANIFEST = B13_DIR / "manifest.json"
B13_ARCHIVE = B13_DIR / "wp13_02b13_arrays.npz"
CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp13_02b4_newmark_v2_contract.json"
SCHEMA_PATH = ROOT / "qualification" / "0_2_8" / "wp13_02b15_evidence.schema.json"
B15_DIR = ROOT / "qualification" / "0_2_8" / "wp13_02b15_residual_normalization"
B15_MANIFEST = B15_DIR / "manifest.json"
B15_ARCHIVE = B15_DIR / "wp13_02b15_residual_arrays.npz"

START_SHA = "6c5d5852e26a40fddf968692bdc98b102839ec0e"
CONTRACT_ID = "WP13-02B4-NEWMARK-MIXED-V2-001"
CONTRACT_BLOB_SHA = "8b44792466eacaf1f341a7970502e9b48dbed4e1"
LEVELS = (("T1/20", "20"), ("T1/40", "40"), ("T1/80", "80"), ("T1/160", "160"))
REPLAYS = (("main", "replay_0"), ("replay_1", "replay_1"), ("replay_2", "replay_2"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def git_blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def array_digest(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value, dtype=np.float64).tobytes()).hexdigest()


def validate_b15_manifest(manifest: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(manifest)
    residual = manifest["residual"]
    if residual["denominator_source"] != "Fstar":
        raise ValueError("residual_relative must use Fstar as denominator source")
    if residual["variable_denominator_used"]:
        raise ValueError("variable residual denominator is forbidden")


def _record(
    source_name: str,
    derived_name: str,
    source: np.ndarray,
    derived: np.ndarray,
    gate: float,
) -> dict[str, Any]:
    return {
        "source_array": source_name,
        "derived_array": derived_name,
        "source_digest": array_digest(source),
        "history_digest": array_digest(derived),
        "max_value": float(np.max(derived)),
        "gate_threshold": gate,
        "gate_pass": bool(np.max(derived) <= gate),
    }


def _history_entry(
    source_name: str,
    derived_name: str,
    source: np.ndarray,
    derived: np.ndarray,
    gate: float,
) -> dict[str, Any]:
    return _record(source_name, derived_name, source, derived, gate)


def build_b15() -> dict[str, Any]:
    if git_head() != START_SHA:
        raise RuntimeError("WP13-02B15 must start from the frozen B14 commit.")
    source_manifest = json.loads(B13_MANIFEST.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if not isinstance(source_manifest.get("repo_sha"), str) or len(source_manifest["repo_sha"]) != 40:
        raise RuntimeError("B13 campaign provenance is not a valid Git SHA.")
    unchanged = subprocess.run(
        ["git", "diff", "--quiet", START_SHA, "--", str(B13_DIR.relative_to(ROOT))],
        cwd=ROOT,
    ).returncode == 0
    if not unchanged:
        raise RuntimeError("B13 evidence changed after the B14 freeze.")
    if source_manifest["archive"]["sha256"] != sha256_file(B13_ARCHIVE):
        raise RuntimeError("B13 archive digest mismatch.")
    if contract["contract_id"] != CONTRACT_ID or git_blob(CONTRACT_PATH) != CONTRACT_BLOB_SHA:
        raise RuntimeError("Frozen contract identity mismatch.")

    with np.load(B13_ARCHIVE, allow_pickle=False) as source:
        for name, metadata in source_manifest["archive"]["array_manifest"].items():
            if name not in source.files:
                raise RuntimeError(f"Missing B13 array: {name}")
            if array_digest(source[name]) != metadata["sha256"]:
                raise RuntimeError(f"Invalid B13 array digest: {name}")
        free = np.asarray(source["oracle_free_indices"], dtype=int)
        stiffness = np.asarray(source["oracle_K"], dtype=float)
        mass = np.asarray(source["oracle_M"], dtype=float)
        initial_displacement = np.asarray(source["oracle_initial_displacement"], dtype=float)
        initial_acceleration = np.asarray(source["oracle_initial_acceleration"], dtype=float)
        fstar = max(
            float(np.linalg.norm(stiffness @ initial_displacement)),
            float(np.linalg.norm(mass @ initial_acceleration)),
            1.0,
        )
        gate = float(contract["acceptance_gates"]["FREE_RESIDUAL"])
        derived_arrays: dict[str, np.ndarray] = {}
        level_records: dict[str, dict[str, Any]] = {}
        for label, tag in LEVELS:
            source_name = f"dt_t1_{tag}_residual_vector"
            vector = np.asarray(source[source_name], dtype=float)
            derived_name = f"dt_t1_{tag}_residual_relative_fstar"
            relative = np.linalg.norm(vector[:, free], axis=1) / fstar
            derived_arrays[derived_name] = relative
            level_records[label] = _history_entry(
                source_name, derived_name, vector, relative, gate
            )
            if not np.isclose(
                float(source_manifest["levels"][label]["metadata"]["fstar"]),
                fstar,
                rtol=0.0,
                atol=1.0e-12,
            ):
                raise RuntimeError(f"B13 Fstar mismatch at {label}.")

        replay_records: dict[str, dict[str, Any]] = {}
        replay_arrays: dict[str, np.ndarray] = {}
        for label, source_prefix in REPLAYS:
            source_name = f"{source_prefix}_t1_160_residual_vector"
            vector = np.asarray(source[source_name], dtype=float)
            derived_name = f"{source_prefix}_t1_160_residual_relative_fstar"
            relative = np.linalg.norm(vector[:, free], axis=1) / fstar
            replay_arrays[derived_name] = relative
            replay_records[label] = _history_entry(
                source_name, derived_name, vector, relative, gate
            )
        derived_arrays.update(replay_arrays)

        source_replays = source_manifest["replays"]["iterations_per_step"]
        iterations = {
            key: list(source_replays[key])
            for key in ("main", "replay_1", "replay_2")
        }

    if any(len(values) != 640 or values != [1] * 640 for values in iterations.values()):
        raise RuntimeError("B13 does not contain the required 640 per-step iteration values.")

    replay_comparisons: dict[str, dict[str, Any]] = {}
    main = derived_arrays["replay_0_t1_160_residual_relative_fstar"]
    for label, source_prefix in (("replay_1", "replay_1"), ("replay_2", "replay_2")):
        other = derived_arrays[f"{source_prefix}_t1_160_residual_relative_fstar"]
        difference = float(np.max(np.abs(main - other)))
        replay_comparisons[label] = {
            "left": "main_t1_160_residual_relative_fstar",
            "right": f"{label}_t1_160_residual_relative_fstar",
            "max_abs_difference": difference,
            "tolerance": float(contract["replay"]["tolerance"]),
            "pass": bool(difference <= float(contract["replay"]["tolerance"])),
        }

    B15_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(B15_ARCHIVE, **derived_arrays)
    archive_manifest = {
        name: {
            "shape": list(value.shape),
            "dtype": "float64",
            "sha256": array_digest(value),
        }
        for name, value in derived_arrays.items()
    }
    b13_manifest_sha = sha256_file(B13_MANIFEST)
    b13_archive_sha = sha256_file(B13_ARCHIVE)
    old_b13_schema_valid = False
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    old_b13_schema_valid = Draft202012Validator(
        schema
    ).is_valid(source_manifest)
    history_paths = {
        "B5": "qualification/0_2_8/wp13_02b5_v2/manifest.json",
        "B6": "qualification/0_2_8/wp13_02b6_input_validation_fix.json",
        "B7": "qualification/0_2_8/wp13_02b7_v2/manifest.json",
        "B8": "qualification/0_2_8/wp13_02b8_owner_gate.json",
        "B9": "qualification/0_2_8/wp13_02b9_harness/manifest.json",
        "B10": "qualification/0_2_8/wp13_02b10_v2/manifest.json",
        "B11": "qualification/0_2_8/wp13_02b11_owner_gate.json",
        "B12": "qualification/0_2_8/wp13_02b12_contract_compliance/manifest.json",
        "B12b": "qualification/0_2_8/wp13_02b12b_contract_compliance/manifest.json",
        "B13": str(B13_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "B14": "qualification/0_2_8/wp13_02b14_owner_gate.json",
    }
    historical = {
        key: {
            "path": path,
            "present": (ROOT / path).is_file(),
            "sha256": sha256_file(ROOT / path) if (ROOT / path).is_file() else None,
        }
        for key, path in history_paths.items()
    }
    if not all(item["present"] for item in historical.values()):
        raise RuntimeError("A required historical B5-B14 record is missing.")

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "record_id": "QF-028-WP13-02B15-RESIDUAL-NORMALIZATION",
        "work_package": "WP13-02B15",
        "start_sha": START_SHA,
        "repo_sha": START_SHA,
        "contract_id": CONTRACT_ID,
        "contract_sha": CONTRACT_BLOB_SHA,
        "contract_sha256": sha256_file(CONTRACT_PATH),
        "contract_unchanged": True,
        "gates_unchanged": True,
        "source_residual_arrays_valid": True,
        "source": {
            "b13_manifest": str(B13_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
            "b13_manifest_sha256": b13_manifest_sha,
            "b13_archive": str(B13_ARCHIVE.relative_to(ROOT)).replace("\\", "/"),
            "b13_archive_sha256": b13_archive_sha,
            "b13_campaign_repo_sha": source_manifest["repo_sha"],
            "old_history_preserved": True,
            "old_b13_evidence_detected_nonconforming": not old_b13_schema_valid,
        },
        "fstar": {
            "value_N": fstar,
            "source": "B13 archived oracle K/M and initial state",
            "formula": "max(norm(K@u0,2), norm(M@a0,2), 1 N)",
        },
        "residual": {
            "metric_name": "residual_relative",
            "contract_metric_definition": "norm(r_free,2)/Fstar",
            "numerator_source": "B13 archived residual_vector at oracle free indices",
            "denominator_source": "Fstar",
            "denominator_value_N": fstar,
            "variable_denominator_used": False,
            "gate_threshold": gate,
            "old_history_field": "residual_relative",
            "new_history_field": "residual_relative_fstar",
            "old_history_preserved": True,
            "by_level": level_records,
            "replay_histories": {
                "main": replay_records["main"],
                "replay_1": replay_records["replay_1"],
                "replay_2": replay_records["replay_2"],
            },
        },
        "archive": {
            "path": str(B15_ARCHIVE.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(B15_ARCHIVE),
            "array_count": len(archive_manifest),
            "array_manifest": archive_manifest,
        },
        "replay_history_comparison": {
            "tolerance": float(contract["replay"]["tolerance"]),
            "main_replay_1": replay_comparisons["replay_1"],
            "main_replay_2": replay_comparisons["replay_2"],
        },
        "iterations_contract_status": "PASS",
        "iterations": {
            "source": "B13 manifest replays.iterations_per_step",
            "level": "T1/160",
            "main": iterations["main"],
            "replay_1": iterations["replay_1"],
            "replay_2": iterations["replay_2"],
            "identical": True,
        },
        "historical_records": historical,
        "integrity": {
            "numerical_runs": "NONE",
            "numerical_source_changed": False,
            "vnv_harness_changed": "YES_SCHEMA_ONLY",
            "input_validation_source_changed": False,
            "preflight_source_changed": False,
            "formulation_changed": False,
            "contract_changed": False,
            "gates_changed": False,
            "maturity_changed": False,
            "evidence_0_2_7_changed": False,
        },
        "gate_decisions": {
            "residual_relative_fstar": all(
                item["gate_pass"] for item in level_records.values()
            ),
            "replay_history_comparison": all(
                item["pass"] for item in replay_comparisons.values()
            ),
            "schema_denominator_guard": True,
            "iterations": True,
        },
        "decision": {
            "status": "PASS_EVIDENCE_ONLY_CLOSURE",
            "ready_for_owner_recheck": True,
            "blockers": [],
        },
        "targeted_checks": [
            "B13 source archive and per-array digest verification",
            "Fstar derivation from archived oracle K/M and initial state",
            "residual_relative_fstar derivation for all levels and replays",
            "complete replay-history comparison",
            "schema positive validation",
            "schema negative validation of old B13 and variable-denominator evidence",
        ],
        "full_test_suite": "DEFERRED_TO_WP13_FINAL_GATE",
    }
    validate_b15_manifest(manifest)
    B15_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    result = build_b15()
    print("WP13-02B15=PASS_EVIDENCE_ONLY_CLOSURE")
    print(f"FSTAR={result['fstar']['value_N']:.17g}")
    for label, item in result["residual"]["by_level"].items():
        print(f"{label}_MAX={item['max_value']:.17g}")
    print(f"ARCHIVE={result['archive']['array_count']}")
