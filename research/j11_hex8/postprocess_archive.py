"""Normalize the alpha-zero keys in a preserved J11 HEX8 result archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


ALPHA_ZERO_REQUIRED_KEYS = (
    "coordinates_alpha_0_m",
    "global_stiffness_alpha_0_n_per_m",
    "qf_sri_kernel_numpy_direct_displacement_alpha_0_m",
    "scaled_displacement_alpha_0_m",
    "scipy_displacement_alpha_0_m",
    "qf_sri_numpy_direct_reactions_alpha_0_n",
    "qf_sri_numpy_direct_free_residual_alpha_0_n",
    "mpmath_displacement_alpha_0_m",
)
ALPHA_INDEXED_PREFIXES = (
    "coordinates",
    "global_stiffness",
    "qf_sri_kernel_numpy_direct_displacement",
    "scaled_displacement",
    "scipy_displacement",
    "qf_sri_numpy_direct_reactions",
    "qf_sri_numpy_direct_free_residual",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _arrays_bitwise_equal(left: np.ndarray, right: np.ndarray) -> bool:
    return left.dtype == right.dtype and left.shape == right.shape and left.tobytes(order="C") == right.tobytes(order="C")


def normalize_alpha_zero_keys(arrays: dict[str, np.ndarray]) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Map the accidental `_alpha_134_` suffix to alpha zero without changing array values."""
    normalized = {name: np.asarray(value) for name, value in arrays.items()}
    aliases = sorted(name for name in normalized if "_alpha_134_" in name)
    expected_aliases = {f"{prefix}_alpha_134_{suffix}" for prefix, suffix in (
        ("coordinates", "m"),
        ("global_stiffness", "n_per_m"),
        ("qf_sri_kernel_numpy_direct_displacement", "m"),
        ("scaled_displacement", "m"),
        ("scipy_displacement", "m"),
        ("qf_sri_numpy_direct_reactions", "n"),
        ("qf_sri_numpy_direct_free_residual", "n"),
        ("mpmath_displacement", "m"),
    )}
    if set(aliases) != expected_aliases:
        raise ValueError("The source archive does not contain the exact known alpha-134 key set")

    duplicates_equal: list[str] = []
    mapping: dict[str, str] = {}
    for source_name in aliases:
        target_name = source_name.replace("_alpha_134_", "_alpha_0_", 1)
        source_value = normalized[source_name]
        if target_name in normalized:
            if not _arrays_bitwise_equal(source_value, normalized[target_name]):
                raise ValueError(f"Alias collision has unequal values: {source_name} -> {target_name}")
            duplicates_equal.append(target_name)
            del normalized[source_name]
        else:
            normalized[target_name] = source_value
            del normalized[source_name]
        mapping[source_name] = target_name

    missing = sorted(set(ALPHA_ZERO_REQUIRED_KEYS) - set(normalized))
    if missing:
        raise ValueError(f"Normalized alpha-zero archive is missing required fields: {missing}")
    if any("_alpha_134_" in name for name in normalized):
        raise ValueError("An accidental alpha-134 key remains after normalization")
    for alpha in (1, 2, 3):
        for prefix in ALPHA_INDEXED_PREFIXES:
            suffix = "n_per_m" if prefix == "global_stiffness" else (
                "n" if prefix.startswith("qf_sri_numpy_direct_") else "m"
            )
            expected = f"{prefix}_alpha_{alpha}_{suffix}"
            if expected not in normalized:
                raise ValueError(f"Archive is missing expected alpha-{alpha} field: {expected}")
    metadata = {
        "key_mapping": mapping,
        "identical_collision_targets_preserved": sorted(set(duplicates_equal)),
        "fem_or_metrics_recomputed": False,
        "interpretation": "Only NPZ keys were normalized. Array dtypes, shapes and byte values are preserved; the original archive remains unchanged.",
    }
    return normalized, metadata


def _write_npz_atomic(path: Path, arrays: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
        temporary = Path(stream.name)
        np.savez_compressed(stream, **{name: arrays[name] for name in sorted(arrays)})
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def normalize_archive(
    input_path: Path,
    output_path: Path,
    *,
    contract_path: Path,
    result_json_path: Path,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract_sha = _canonical_sha256(contract_path)
    expected_input_sha = contract["inputs"]["runner_output_npz_sha256_raw"]
    if _sha256(input_path) != expected_input_sha:
        raise ValueError("Source NPZ does not match the frozen post-processing contract")
    if _sha256(result_json_path) != contract["inputs"]["runner_result_json_sha256_raw"]:
        raise ValueError("Source result JSON does not match the frozen post-processing contract")
    result = json.loads(result_json_path.read_text(encoding="utf-8"))
    if result.get("execution_status") != "COMPLETED_EXPLORATORY":
        raise ValueError("The source runner result is not the expected exploratory completion")
    if result.get("nodeid") != contract["source_run"]["nodeid"]:
        raise ValueError("The source result nodeid differs from the post-processing contract")
    if result.get("source_head") != contract["source_run"]["source_head"]:
        raise ValueError("The source result head differs from the post-processing contract")
    for item in contract["source_identity"]:
        if _canonical_sha256(Path(__file__).resolve().parents[2] / item["path"]) != item["canonical_sha256"]:
            raise ValueError(f"Post-processing source differs from the frozen contract: {item['path']}")
    with np.load(input_path, allow_pickle=False) as archive:
        arrays = {name: np.asarray(archive[name]) for name in archive.files}
    normalized, details = normalize_alpha_zero_keys(arrays)
    _write_npz_atomic(output_path, normalized)
    return {
        "schema": "qf-j11-hex8-archive-key-normalization-v1",
        "contract_id": contract["contract_id"],
        "contract_sha256_canonical": contract_sha,
        "source_run": contract["source_run"],
        "source_npz_sha256_raw": _sha256(input_path),
        "source_result_json_sha256_raw": _sha256(result_json_path),
        "normalized_npz_sha256_raw": _sha256(output_path),
        "source_execution_status_preserved": result["execution_status"],
        "postprocess_status": "COMPLETED_DETERMINISTIC_KEY_NORMALIZATION",
        **details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--result-json", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args()
    result = normalize_archive(
        args.input,
        args.output,
        contract_path=args.contract,
        result_json_path=args.result_json,
    )
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
