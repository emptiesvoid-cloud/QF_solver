"""Evidence-only completion of the archived WP13-02C3 modal-coordinate fields."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "qualification/0_2_8/wp13_02c3_harmonic_final"
ARCHIVE_PATH = OUTPUT_DIR / "wp13_02c3_harmonic_arrays.npz"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"


def digest(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    with np.load(ARCHIVE_PATH, allow_pickle=False) as source:
        arrays = {key: np.asarray(source[key]) for key in source.files}
    complex_coordinate = np.asarray(arrays["modal_coordinate_complex"], dtype=np.complex128)
    arrays["modal_coordinate_amplitude"] = np.abs(complex_coordinate).astype(np.float64)
    arrays["modal_coordinate_phase"] = np.angle(complex_coordinate).astype(np.float64)
    temporary = ARCHIVE_PATH.with_name(ARCHIVE_PATH.stem + ".evidence_tmp.npz")
    np.savez_compressed(temporary, **arrays)
    temporary.replace(ARCHIVE_PATH)
    array_manifest = manifest["digests"]["arrays"]
    for key in ("modal_coordinate_amplitude", "modal_coordinate_phase"):
        array_manifest[key] = {
            "shape": list(arrays[key].shape),
            "dtype": str(arrays[key].dtype),
            "sha256": digest(arrays[key]),
        }
    manifest["modal_coordinate"]["amplitude"] = {
        "array_key": "modal_coordinate_amplitude",
        "derived_from": "abs(modal_coordinate_complex)",
    }
    manifest["modal_coordinate"]["phase"] = {
        "array_key": "modal_coordinate_phase",
        "derived_from": "angle(modal_coordinate_complex)",
    }
    for comparison in manifest["replay_comparison"]["comparisons"]:
        if "iterations" not in comparison["fields_compared"]:
            comparison["fields_compared"].append("iterations")
    manifest["digests"]["archive_sha256"] = file_digest(ARCHIVE_PATH)
    manifest["evidence_postprocessing"] = {
        "kind": "derived modal amplitude/phase from archived complex coordinate",
        "numerical_run": False,
        "solver_called": False,
        "source_array": "modal_coordinate_complex",
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("WP13-02C3 modal evidence completed without numerical run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
