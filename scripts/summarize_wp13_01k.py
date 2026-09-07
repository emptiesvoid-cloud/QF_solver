"""Validate and seal the targeted connected MVP evidence (no numerical solves)."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qualification/0_2_8/wp13_01k_runtime"
START = "b5db3ab50ade0db9887c3d92d8a5eb72362cbb54"
FREEZE = "1b21d695b236e6835cf5a952b2e41db7f17c8e1b"
CONTRACT = "qualification/0_2_8/wp13_01k_contract.json"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def evidence_hash(path):
    value = path.read_bytes()
    if path.suffix in {".json", ".py"}:
        value = value.replace(b"\r\n", b"\n")
    return hashlib.sha256(value).hexdigest()


def main():
    # Compare parsed contract because Windows checkout line endings differ from Git blobs.
    contract = json.loads((ROOT / CONTRACT).read_text())
    assert contract == json.loads(git("show", f"{FREEZE}:{CONTRACT}"))
    assert not git("diff", "--name-only", "--diff-filter=MDR", START).strip()
    labels = ["small_serial", "small_mpi1", "small_mpi2_contract", "small_mpi4",
              "stage_a_mpi1", "stage_a_mpi2", "stage_a_mpi4",
              "stage_b_mpi2", "stage_b_mpi4", "stage_b_replay1", "stage_b_replay2"]
    runs = {}
    for label in labels:
        data = json.loads((OUT / (label+".json")).read_text())
        pre = json.loads((OUT / (label+"_pre.json")).read_text())
        assert data["status"] == "PASS" and all(data["gates"].values()), label
        assert data["contract_sha256"] == hashlib.sha256((ROOT / CONTRACT).read_bytes()).hexdigest()
        assert all(pre["gates"].values()), label
        assert (OUT / (label+".npz")).is_file()
        runs[label] = {"ndof": data["result"]["ndof"],
                       "rank_count": data["result"]["rank_count"],
                       "equilibrium": data["equilibrium_normal"],
                       "residual": data["result"]["free_residual_relative"],
                       "energy_error": data["result"]["energy_identity_relative"],
                       "runtime_seconds": data["result"]["runtime_seconds"],
                       "peak_memory_MiB_per_rank_max": data["result"]["peak_memory_mb"],
                       "iterations": data["result"]["iterations"]}
    comparisons = {}
    for label in ["small_partition", "small_rank_partition", "stage_a_partition",
                  "stage_b_partition", "stage_b_replay"]:
        data = json.loads((OUT / (label+".json")).read_text())
        assert data["pass"], label
        comparisons[label] = data
    data = json.loads((OUT / "stage_b_mpi2.json").read_text())
    pre = json.loads((OUT / "stage_b_mpi2_pre.json").read_text())
    files = sorted(OUT.iterdir()) + [ROOT / CONTRACT] + [ROOT / "scripts" / name for name in
            ["run_wp13_01k_mvp.py", "check_wp13_01k_comparison.py", "summarize_wp13_01k.py"]]
    evidence = {
        "work_package": "WP13-01K", "start_sha": START,
        "pre_run_contract_sha": FREEZE, "contract_id": contract["contract_id"],
        "status": "PASS_CONNECTED_MVP_50K", "ready_for_final_owner": True,
        "contract_changed_after_results": False,
        "runtime_environment": {
            "image": "qf-solver-large:0.2.0",
            "image_id": "sha256:9efd68c16474925744fabf507c9de6018b71738887921e27e53701bd22ae45de",
            "PETSc": "3.25.1", "petsc4py": "3.25.1", "mpi4py": "4.1.2", "MPI": "MPICH 5.0.1",
            "docker_cpus": 12, "docker_memory_bytes": 50458107904,
            "OPENBLAS_NUM_THREADS": 1, "OMP_NUM_THREADS": 1,
            "run_command": "mpiexec -n <ranks> python scripts/run_wp13_01k_mvp.py --case <case> --label <label>",
            "serial_command": "python scripts/run_wp13_01k_mvp.py --case small --backend serial --label small_serial"},
        "runs": runs, "comparisons": comparisons,
        "largest_conditioning": pre, "largest_interfaces": data["interfaces"],
        "largest_partition": data["partition"],
        "largest_force_defect_N": data["force_defect_N"],
        "largest_force_defect_fsum_N": data["force_defect_fsum_N"],
        "largest_nnz": data["result"]["preallocation"]["matgetinfo"]["nz_used_sum"],
        "largest_family_counts": data["result"]["family_counts"],
        "conditioning_comparison": {
            "old_aspect": 3332, "new_max_pairwise_edge_aspect": pre["max_aspect_ratio"],
            "old_entry_magnitude_ratio": 5.59e25, "new_entry_magnitude_ratio": pre["stiffness_entry_ratio"],
            "old_equilibrium_approx": 6.7e-10, "new_equilibrium": data["equilibrium_normal"],
            "interpretation": "Consistent with reduced roundoff amplification, not causal proof: shape, load path and discretization differ. Entry ratios include near-zero cancellation entries and are NOT matrix condition numbers. New diagonal ratio and affine-Jacobian condition are more meaningful bounded proxies."},
        "runner_evaluator_correction": {
            "original_record_preserved": "wp13_01k_runtime/small_mpi2.json",
            "original_verdict": "FAIL: cross_rank only; every physical gate passed",
            "bug": "Evaluator required each family pair to have a cross-rank face (all), although the frozen contract requires nonzero cross-rank faces and ghosts overall.",
            "correction": "Evaluate total cross-rank face count >0 AND ghost count >0, exactly as frozen. No partition/model/threshold changed. New rerun saved under small_mpi2_contract; original retained.",
            "limitations": "Small MPI-2 crosses WEDGE6/HEX8 only. Both interface pairs cross ranks at 9768 and 50844 DOF. Owner should explicitly review this evaluator correction."},
        "limitations": [
            "Candidate technical claim only; separate final Owner approval required.",
            "Compact synthetic elbow, linear static, isotropic material, tested 50844 DOF MPI-2/4 only.",
            "Direct LU iteration count 1 is not an iterative scaling claim; three direct solves include two fixed residual corrections.",
            "No structural MPI gather of K/connectivity; input model and partition metadata replicated on each rank; global solution scatter and result gathers remain.",
            "Interface continuity uses unique shared DOFs and independent family force transfer, not a separate halo-only displacement API.",
            "Runtime reports assembly/solve region of existing runner; excludes precheck, independent interface postprocessing, startup and evidence serialization.",
            "ru_maxrss maximum across ranks captured at assembly/solve completion; not entire-process postprocessing peak; units MiB.",
            "No 150k/300k runs, no 1M connected claim, no maturity promotion."],
        "claim_supported": "Bounded connected compact-elbow TET4/WEDGE6/HEX8 linear-static PETSc/MPI runtime confirmation at 50844 DOF on 2/4 ranks, with two additional MPI-2 numerical replays; pending Owner review.",
        "integrity": {"historical_results_changed": False,"evidence_0_2_7_changed": False,
                      "numerical_source_changed": False,"formulation_changed": False,"gates_changed": False},
        "targeted_checks": "11 accepted solves plus preserved evaluator-failure run; prechecks, interface forces, partition and replay checks; Ruff and compileall",
        "full_test_suite": "DEFERRED_TO_WP13_FINAL_GATE",
        "hash_policy": "SHA256, text CRLF normalized to LF; NPZ raw bytes. Per-run contract_sha256 is original runtime byte hash.",
        "sha256_files": {p.relative_to(ROOT).as_posix(): evidence_hash(p) for p in files}}
    (OUT.parent / "wp13_01k_execution.json").write_text(json.dumps(evidence,indent=2)+"\n")
    print(json.dumps({"status": evidence["status"], "accepted_runs": len(runs), "integrity": "PASS"}))


if __name__ == "__main__":
    main()
