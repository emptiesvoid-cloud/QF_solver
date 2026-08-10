import hashlib
import json
import subprocess
import sys
from pathlib import Path

from solveur.api import load_model, save_evidence, solve_model, verify_evidence


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def write_model(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "analysis": "linear_static",
                "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
                "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
                "materials": {"steel": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3}},
                "fixed_dofs": [
                    {"node": 0, "dofs": ["UX", "UY", "UZ"]},
                    {"node": 2, "dofs": ["UX", "UY", "UZ"]},
                    {"node": 3, "dofs": ["UX", "UY", "UZ"]},
                ],
                "loads": [{"node": 1, "dof": "UX", "value": 1000.0}],
            }
        ),
        encoding="utf-8",
    )


def test_public_api_saves_evidence_bundle_with_manifest(tmp_path: Path):
    model_path = tmp_path / "model.json"
    evidence_dir = tmp_path / "evidence"
    write_model(model_path)
    model = load_model(model_path)
    result = solve_model(model)
    paths = save_evidence(model, result, evidence_dir, input_path=model_path)
    assert paths["results"].exists()
    assert paths["audit"].exists()
    assert paths["mesh_report"].exists()
    assert paths["manifest"].exists()

    summary = json.loads(paths["qualification_summary"].read_text(encoding="utf-8"))
    assert summary["status"] == "PASS"
    assert summary["verification_profile"] == "engineering"
    assert summary["maturity"]["overall"] == "stable"

    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert manifest["manifest_schema_version"] == 2
    assert manifest["solver"]["version"]
    assert manifest["source"]["revision"]
    assert manifest["runtime"]["python"]["version"]
    assert "name" in manifest["runtime"]["blas"]
    assert manifest["locked_environments"]
    assert manifest["command_line"]
    assert manifest["input_sha256"] == sha256_file(paths["input"])
    assert manifest["traceability"]["scope"] == "tet4-linear-static"
    assert manifest["traceability"]["status"] == "PASS"
    assert manifest["analysis"] == "linear_static"
    assert manifest["qualification_summary"]["status"] == "PASS"
    assert manifest["file_count"] == len(manifest["files"])
    manifest_files = {entry["role"]: entry for entry in manifest["files"]}
    required = {"input", "results", "audit", "mesh_report", "solver_settings", "qualification_summary"}
    assert required <= set(manifest_files)
    assert manifest_files["input"]["sha256"] == sha256_file(paths["input"])
    assert manifest_files["results"]["size_bytes"] == paths["results"].stat().st_size
    verification = verify_evidence(evidence_dir)
    assert verification.status == "PASS"
    assert verification.checked_file_count == manifest["file_count"]
    assert verification.errors == ()

    result_data = json.loads(paths["results"].read_text(encoding="utf-8"))
    assert result_data["qualification_summary"]["evidence_level"] == "engineering_review"
    audit_text = paths["audit"].read_text(encoding="utf-8")
    assert "Profil verification" in audit_text
    assert "Maturite" in audit_text
    assert "Verdict global" in audit_text


def test_cli_evidence_writes_bundle_with_manifest(tmp_path: Path):
    model_path = tmp_path / "model.json"
    evidence_dir = tmp_path / "cli_evidence"
    write_model(model_path)
    evidence = subprocess.run(
        [
            sys.executable,
            "main_solveur.py",
            "evidence",
            "--input",
            str(model_path),
            "--output",
            str(evidence_dir),
            "--verification-profile",
            "strict",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert evidence.returncode == 0
    assert "EVIDENCE STATUS: PASS" in evidence.stdout
    summary = json.loads((evidence_dir / "qualification_summary.json").read_text(encoding="utf-8"))
    assert summary["verification_profile"] == "strict"
    assert summary["evidence_level"] == "strict_review"
    assert (evidence_dir / "input.json").exists()
    assert (evidence_dir / "audit.md").exists()

    manifest = json.loads((evidence_dir / "evidence_manifest.json").read_text(encoding="utf-8"))
    assert manifest["verification_profile"] == "strict"
    assert manifest["source_input_path"] == str(model_path.resolve())
    assert any(entry["role"] == "results" for entry in manifest["files"])

    verify = subprocess.run(
        [
            sys.executable,
            "main_solveur.py",
            "verify-evidence",
            "--input",
            str(evidence_dir),
            "--json-report",
            str(tmp_path / "verify_report.json"),
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert verify.returncode == 0
    assert "EVIDENCE VERIFY STATUS: PASS" in verify.stdout
    verify_report = json.loads((tmp_path / "verify_report.json").read_text(encoding="utf-8"))
    assert verify_report["status"] == "PASS"


def test_evidence_verification_fails_when_artifact_is_modified(tmp_path: Path):
    model_path = tmp_path / "model.json"
    evidence_dir = tmp_path / "evidence"
    write_model(model_path)
    model = load_model(model_path)
    result = solve_model(model)
    save_evidence(model, result, evidence_dir, input_path=model_path)

    result_path = evidence_dir / "results.json"
    result_path.write_text(result_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    report = verify_evidence(evidence_dir)
    assert report.status == "FAIL"
    assert any("sha256 mismatch" in error or "size mismatch" in error for error in report.errors)

    completed = subprocess.run(
        [sys.executable, "main_solveur.py", "verify-evidence", "--input", str(evidence_dir)],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 4
    assert "EVIDENCE VERIFY STATUS: FAIL" in completed.stdout


def test_evidence_verifier_keeps_manifest_v1_read_compatibility(tmp_path: Path):
    artifact = tmp_path / "result.json"
    artifact.write_text('{"status": "PASS"}', encoding="utf-8")
    manifest = {
        "manifest_schema_version": 1,
        "file_count": 1,
        "files": [
            {
                "role": "result",
                "path": artifact.name,
                "size_bytes": artifact.stat().st_size,
                "sha256": sha256_file(artifact),
            }
        ],
    }
    (tmp_path / "evidence_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    report = verify_evidence(tmp_path)
    assert report.status == "PASS"
    assert report.checked_file_count == 1


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
