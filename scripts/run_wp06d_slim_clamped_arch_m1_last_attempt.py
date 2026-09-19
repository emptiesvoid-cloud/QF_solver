"""Final isolated WP06-D M1 attempt with adaptive arc length and direct refinement.

This runner is diagnostic-only.  It reuses the frozen M1 geometry and loads,
keeps the physical and verification thresholds unchanged, and writes to a new
output directory.  The optional numerical controls are deliberately enabled
only for this experiment and are recorded in the resulting evidence.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REUSED_RUNNER = ROOT / "scripts/run_wp06d_slim_clamped_arch_m1_long_qmean_diagnostic.py"
OUT = ROOT / "qualification/0_2_9/wp06d_slim_clamped_arch_m1_last_attempt_20260919"
MESH_DIR = OUT / "mesh"
CASE_DIR = OUT / "case"
MESH_PATH = MESH_DIR / "rise_span_0_05_M1.npz"
BASE_RUNNER = ROOT / "scripts/run_wp06d_low_strain_exploratory.py"
MESH_GENERATOR = ROOT / "scripts/wp06d_candidate_mesh_audit.py"
EXPECTED_BRANCH = "codex/wp06-score-requalification"
EXPECTED_HEAD = "20bf2c784d87ddae5f43f423adda687fb2db7b4e"

EXPERIMENTAL_POLICY = {
    "adaptive_arc_length": True,
    "arc_length_growth_factor": 1.25,
    "arc_length_shrink_factor": 0.5,
    "arc_length_grow_below_iterations": 6,
    "arc_length_shrink_above_iterations": 16,
    "experimental_direct_refinement_steps": 3,
}


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _is_ancestor(ancestor: str, descendant: str = "HEAD") -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=ROOT,
        capture_output=True,
    ).returncode == 0


def _import_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
    temporary.replace(path)


def _prepare_base(r1: Any, original_prepare_base: Any) -> Any:
    base = original_prepare_base()
    original_prepare_modules = base._prepare_modules

    def prepare_modules() -> tuple[Any, Any]:
        generator, runner = original_prepare_modules()
        original_build_model = runner._build_model

        def build_model(*args: Any, **kwargs: Any) -> Any:
            model, constrained, support_nodes, center_node = original_build_model(*args, **kwargs)
            model.analysis.parameters.update(EXPERIMENTAL_POLICY)
            return model, constrained, support_nodes, center_node

        runner._build_model = build_model
        return generator, runner

    base._prepare_modules = prepare_modules
    return base


def _finalize(r1: Any) -> None:
    case_path = OUT / "case/case_result.json"
    final_path = OUT / "campaign_final.json"
    metadata_path = OUT / "campaign_metadata.json"
    definition_path = OUT / "benchmark_definition.json"
    case = json.loads(case_path.read_text(encoding="utf-8"))
    final = json.loads(final_path.read_text(encoding="utf-8"))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    definition = json.loads(definition_path.read_text(encoding="utf-8"))
    failed = case.get("status") == "SOLVE_FAILED" or case.get("solver_error") is not None
    classification = "SOLVE_FAILED_DIAGNOSTIC_ONLY" if failed else "COMPLETED_DIAGNOSTIC_ONLY"
    runner_hash = _hash(Path(__file__).resolve())
    reused_hash = _hash(REUSED_RUNNER)
    current_head = _git("rev-parse", "HEAD")
    definition.update(
        {
            "record_id": "QF-WP06D-SLIM-CLAMPED-ARCH-M1-LAST-ATTEMPT-DIAGNOSTIC",
            "status": "DIAGNOSTIC_CANDIDATE_NOT_FROZEN_FORMAL_CONTRACT",
            "scope": (
                "one final M1 diagnostic only; adaptive arc-length and direct iterative "
                "refinement enabled; no M2/M3, independent reference, replay, formal "
                "requalification, or score change"
            ),
            "experimental_policy": dict(EXPERIMENTAL_POLICY),
            "relation_to_prior_runs": {
                "prior_r2_output": "qualification/0_2_9/wp06d_slim_clamped_arch_m1_long_qmean_20260919_r2",
                "prior_artifacts_modified": False,
                "fresh_from_zero": True,
            },
        }
    )
    _write_json(definition_path, definition)
    metadata.update(
        {
            "status_classification_corrected": True,
            "formal_requalification_authorized": False,
            "experimental_policy": dict(EXPERIMENTAL_POLICY),
            "execution_head": current_head,
            "last_attempt_runner_sha256": runner_hash,
            "reused_long_runner_sha256": reused_hash,
        }
    )
    _write_json(metadata_path, metadata)
    final.update(
        {
            "status": classification,
            "classification": classification,
            "execution_runner_sha256": runner_hash,
            "reused_diagnostic_runner_sha256": reused_hash,
            "benchmark_definition_sha256": _hash(definition_path),
            "case_result_sha256": _hash(case_path),
            "execution_head": current_head,
            "experimental_policy": dict(EXPERIMENTAL_POLICY),
            "fresh_from_zero": True,
            "formal_requalification_claimed": False,
            "m2_run": False,
            "m3_run": False,
            "reference_run": False,
            "replay_run": False,
        }
    )
    _write_json(final_path, final)
    source_paths = (Path(__file__).resolve(), REUSED_RUNNER, BASE_RUNNER, MESH_GENERATOR)
    entries: list[dict[str, Any]] = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "campaign_integrity_manifest.json":
            entries.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "sha256": _hash(path),
                    "size_bytes": path.stat().st_size,
                }
            )
    for path in source_paths:
        entries.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": _hash(path),
                "size_bytes": path.stat().st_size,
            }
        )
    _write_json(
        OUT / "campaign_integrity_manifest.json",
        {
            "schema_version": 1,
            "algorithm": "sha256",
            "manifest_excludes_itself": True,
            "execution_head": current_head,
            "files": entries,
        },
    )


def main() -> int:
    if _git("branch", "--show-current") != EXPECTED_BRANCH:
        raise SystemExit("Refusing run: unexpected diagnostic branch.")
    if not _is_ancestor(EXPECTED_HEAD):
        raise SystemExit("Refusing run: source HEAD is not descended from the reviewed M1 base.")
    if OUT.exists():
        raise SystemExit(f"Refusing to overwrite existing output: {OUT}")
    execution_head = _git("rev-parse", "HEAD")
    r1 = _import_module("wp06d_long_qmean_r1_for_last_attempt", REUSED_RUNNER)
    r1.OUT = OUT
    r1.MESH_DIR = MESH_DIR
    r1.CASE_DIR = CASE_DIR
    r1.MESH_PATH = MESH_PATH
    r1.BASE_RUNNER = BASE_RUNNER
    r1.MESH_GENERATOR = MESH_GENERATOR
    r1.EXPECTED_BRANCH = EXPECTED_BRANCH
    r1.EXPECTED_HEAD = execution_head
    original_prepare_base = r1._prepare_base
    r1._prepare_base = lambda: _prepare_base(r1, original_prepare_base)
    try:
        result = r1.main()
    finally:
        r1._prepare_base = original_prepare_base
    if OUT.exists() and (OUT / "case/case_result.json").exists():
        _finalize(r1)
    return int(result)


if __name__ == "__main__":
    raise SystemExit(main())
