"""Verify and render the frozen WP12-S local evidence without importing QF Solver."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import html
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parent
MANIFEST_PATH = PACKAGE / "WP12_S_QUANTITATIVE_MANIFEST.json"
EXPECTED_MANIFEST_SHA256 = "df8c1401a122d18be270ba25bbd0f77c92ede5ff667d9fe4b87da62c10745d9c"
EXPECTED_CASES = (
    "ALG-PROJ-QUANT-001",
    "MODAL-DISCRETE-QUANT-001",
    "MODAL-2DOF-QUANT-001",
    "DYN-SDOF-QUANT-001",
    "MODAL-2DOF-POLY-001",
    "STAT-BEAM-UY-001",
    "STAT-BEAM-UZ-001",
    "FEM-TET4-H-001",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_evidence() -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Path]]:
    raw_manifest = MANIFEST_PATH.read_bytes()
    manifest_sha = hashlib.sha256(raw_manifest).hexdigest()
    if manifest_sha != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError(f"WP12-S manifest changed: {manifest_sha}")
    manifest = json.loads(raw_manifest.decode("utf-8"))
    if tuple(case["case_id"] for case in manifest["cases"]) != EXPECTED_CASES:
        raise RuntimeError("manifest case order or identity differs from the approved eight-case scope")

    evidence_root = Path(manifest["evidence_root"]).resolve(strict=True)
    campaign_root = evidence_root / manifest["campaign_id"]
    decision_index_path = campaign_root / "_owner_decisions" / "index.json"
    decision_index = json.loads(decision_index_path.read_text(encoding="utf-8"))
    if decision_index["manifest_sha256"] != manifest_sha or len(decision_index["decisions"]) != len(EXPECTED_CASES):
        raise RuntimeError("Owner decision index does not bind the approved manifest and eight cases")
    indexed_decisions = {item["case_id"]: item for item in decision_index["decisions"]}

    receipts: dict[str, dict[str, Any]] = {}
    receipt_paths: dict[str, Path] = {}
    for case in manifest["cases"]:
        case_id = case["case_id"]
        run_dirs = [path for path in (campaign_root / case_id).iterdir() if path.is_dir()]
        if len(run_dirs) != 1:
            raise RuntimeError(f"{case_id}: expected exactly one execution directory, found {len(run_dirs)}")
        run_dir = run_dirs[0]
        receipt_path = run_dir / "receipt.json"
        receipt_raw = receipt_path.read_bytes()
        receipt = json.loads(receipt_raw.decode("utf-8"))
        receipt_sha = hashlib.sha256(receipt_raw).hexdigest()
        sidecar = json.loads((run_dir / "receipt.sha256.json").read_text(encoding="utf-8"))
        if sidecar.get("sha256") != receipt_sha:
            raise RuntimeError(f"{case_id}: receipt sidecar mismatch")
        if receipt.get("manifest_sha256") != manifest_sha or receipt.get("case_id") != case_id:
            raise RuntimeError(f"{case_id}: receipt identity mismatch")
        decision_path = campaign_root / "_owner_decisions" / f"{case_id}.json"
        decision_sha = _sha256(decision_path)
        if decision_sha != indexed_decisions.get(case_id, {}).get("sha256"):
            raise RuntimeError(f"{case_id}: Owner decision hash does not match the decision index")
        if receipt.get("owner_decision_sha256") != decision_sha:
            raise RuntimeError(f"{case_id}: receipt does not bind its case-specific Owner decision")
        for phase in ("identities_before", "identities_after"):
            observed_identities = receipt.get(phase, {})
            for key in ("science", "runner", "tests"):
                declared = manifest["identities"][key]
                observed = observed_identities.get(key, {})
                if any(observed.get(field) != declared.get(field) for field in ("commit", "tree")):
                    raise RuntimeError(f"{case_id}: {phase}.{key} identity mismatch")
        expected_source = (
            Path(manifest["identities"]["science"]["path"]) / "src" / "solveur" / "__init__.py"
        ).resolve()
        if Path(receipt["source_import"]["solveur_file"]).resolve() != expected_source:
            raise RuntimeError(f"{case_id}: solveur import origin mismatch")
        if receipt.get("nodeid") != case["nodeid"] or receipt.get("selected_nodeids") != [case["nodeid"]]:
            raise RuntimeError(f"{case_id}: exact node selection mismatch")
        observable = receipt["numeric_observables"]
        payload = observable.get("payload")
        if (
            observable.get("status") != "EXPOSED_JSON"
            or not isinstance(payload, dict)
            or payload.get("schema") != case["numeric_payload_schema"]
            or payload.get("case_id") != case_id
        ):
            raise RuntimeError(f"{case_id}: structured payload is absent or mismatched")
        for item in receipt["output_hashes"]:
            output_path = run_dir / item["path"]
            if not output_path.is_file() or _sha256(output_path) != item["sha256"]:
                raise RuntimeError(f"{case_id}: output hash mismatch: {item['path']}")

        junit = ET.parse(run_dir / "junit.xml").getroot()
        testcases = list(junit.iter("testcase"))
        expected_name = case["nodeid"].split("::", maxsplit=1)[1]
        if len(testcases) != 1 or testcases[0].get("name") != expected_name:
            raise RuntimeError(f"{case_id}: JUnit does not contain exactly the approved node")
        junit_failed = testcases[0].find("failure") is not None
        if junit_failed != (receipt.get("status") == "FAIL"):
            raise RuntimeError(f"{case_id}: JUnit and receipt classifications disagree")

        results = list((campaign_root / "_attempts").glob(f"{case_id}-result-*.json"))
        if len(results) != 1:
            raise RuntimeError(f"{case_id}: expected exactly one recorded attempt")
        result = json.loads(results[0].read_text(encoding="utf-8"))
        if result.get("receipt_sha256") != receipt_sha or result.get("status") != receipt.get("status"):
            raise RuntimeError(f"{case_id}: attempt ledger result does not bind its receipt")

        receipts[case_id] = receipt
        receipt_paths[case_id] = receipt_path
    return manifest, receipts, receipt_paths


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


def _svg_header(title: str, width: int, height: int, description: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        "<style>text{font-family:Arial,sans-serif;fill:#17212b}.title{font-size:22px;font-weight:bold}.label{font-size:13px}.small{font-size:11px}.axis{stroke:#3d4d5c;stroke-width:1}.grid{stroke:#d8dee5;stroke-width:1}.blue{stroke:#1677b8;fill:#1677b8}.orange{stroke:#e28a18;fill:#e28a18}.red{stroke:#bb3333;fill:#bb3333}.green{stroke:#17834a;fill:#17834a}</style>",
        f"<title>{_esc(title)}</title>",
        f"<desc>{_esc(description)}</desc>",
        f'<text class="title" x="24" y="34">{_esc(title)}</text>',
    ]


def _text(lines: list[str], x: float, y: float, text: str, css: str = "label", anchor: str = "start") -> None:
    lines.append(f'<text class="{css}" x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}">{_esc(text)}</text>')


def _polyline(lines: list[str], points: list[tuple[float, float]], css: str, width: float = 2.0) -> None:
    coordinates = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    lines.append(f'<polyline class="{css}" fill="none" stroke-width="{width:.2f}" points="{coordinates}"/>')


def _dot(lines: list[str], x: float, y: float, css: str, radius: float = 4.0) -> None:
    lines.append(f'<circle class="{css}" cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}"/>')


def _save_svg(path: Path, lines: list[str]) -> None:
    lines.append("</svg>")
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(lines) + "\n")


def _figure_modal_discrete(path: Path, values: dict[str, Any]) -> None:
    value = values["frequency_computed_cycles_per_consistent_time_unit"]
    reference = values["frequency_reference_cycles_per_consistent_time_unit"]
    lines = _svg_header(
        "MODAL-DISCRETE-QUANT-001 — spring/mass frequency",
        760,
        360,
        "Computed and closed-form frequency coincide at the displayed precision. Units are not declared by the source test.",
    )
    left, right, top, bottom = 100.0, 700.0, 95.0, 265.0
    low, high = min(value, reference) - 0.15, max(value, reference) + 0.15
    for i in range(4):
        yv = low + (high - low) * i / 3
        y = bottom - (yv - low) / (high - low) * (bottom - top)
        lines.append(f'<line class="grid" x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}"/>')
        _text(lines, left - 10, y + 4, f"{yv:.4f}", "small", "end")
    lines.append(f'<line class="axis" x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}"/>')
    lines.append(f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{bottom}"/>')
    y = bottom - (value - low) / (high - low) * (bottom - top)
    for x, css in ((310.0, "orange"), (490.0, "blue")):
        _dot(lines, x, y, css, 7)
    _text(lines, 310, bottom + 25, "Analytical", "label", "middle")
    _text(lines, 490, bottom + 25, "QF Solver", "label", "middle")
    _text(lines, 400, 82, f"Both = {value:.15g} cycles per consistent time unit", "label", "middle")
    _text(lines, 400, 325, "Relative error = 0; source does not declare physical units.", "small", "middle")
    _save_svg(path, lines)


def _figure_modal_roots(path: Path, values: dict[str, Any]) -> None:
    actual = values["computed_eigenvalues"]
    reference = values["expected_eigenvalues_from_scalar_polynomial"]
    lines = _svg_header(
        "MODAL-2DOF-POLY-001 — independent scalar roots",
        800,
        430,
        "Scalar characteristic-polynomial roots and computed eigenvalues agree within the listed relative errors. The test result is FAIL because a separate projected-stiffness assertion uses zero absolute tolerance for off-diagonal entries.",
    )
    left, right, top, bottom = 100.0, 750.0, 100.0, 300.0
    low, high = 0.0, 12.5
    for i in range(6):
        val = low + (high - low) * i / 5
        y = bottom - (val - low) / (high - low) * (bottom - top)
        lines.append(f'<line class="grid" x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}"/>')
        _text(lines, left - 10, y + 4, f"{val:.1f}", "small", "end")
    x_values = [290.0, 560.0]
    for index, (calc, ref) in enumerate(zip(actual, reference, strict=True)):
        y_calc = bottom - calc / high * (bottom - top)
        y_ref = bottom - ref / high * (bottom - top)
        _dot(lines, x_values[index] - 9, y_ref, "orange", 6)
        _dot(lines, x_values[index] + 9, y_calc, "blue", 6)
        _text(lines, x_values[index], bottom + 24, f"Mode {index + 1}", "label", "middle")
        _text(lines, x_values[index], y_calc - 13, f"{calc:.12g}", "small", "middle")
    lines.append(f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{bottom}"/>')
    lines.append(f'<line class="axis" x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}"/>')
    _dot(lines, 175, 350, "orange", 5)
    _text(lines, 188, 354, "Scalar polynomial reference", "small")
    _dot(lines, 385, 350, "blue", 5)
    _text(lines, 398, 354, "Computed eigenvalue", "small")
    _text(
        lines,
        400,
        395,
        "Test status: FAIL — projected K off-diagonal ≈ −4.44×10⁻¹⁶; asserted atol=0.",
        "small",
        "middle",
    )
    _save_svg(path, lines)


def _figure_newmark(path: Path, values: dict[str, Any]) -> None:
    times = values["times_s"]
    computed = values["displacement_computed_m_or_consistent_length"]
    analytic = values["displacement_analytic_m_or_consistent_length"]
    errors = [abs(a - b) for a, b in zip(computed, analytic, strict=True)]
    lines = _svg_header(
        "DYN-SDOF-QUANT-001 — Newmark modal free vibration",
        900,
        610,
        "One dt=0.00005 s run, 80 integration steps. Analytic frequency is derived from the prepared FE mass and stiffness operators. This does not establish time-step convergence.",
    )
    left, right = 95.0, 860.0
    top1, bottom1, top2, bottom2 = 95.0, 335.0, 420.0, 540.0
    ymin = min(min(computed), min(analytic)) - 0.00008
    ymax = max(max(computed), max(analytic)) + 0.00008
    for i in range(5):
        val = ymin + (ymax - ymin) * i / 4
        y = bottom1 - (val - ymin) / (ymax - ymin) * (bottom1 - top1)
        lines.append(f'<line class="grid" x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}"/>')
    points_calc = []
    points_exact = []
    for t, calc, exact in zip(times, computed, analytic, strict=True):
        x = left + (t / times[-1]) * (right - left)
        points_calc.append((x, bottom1 - (calc - ymin) / (ymax - ymin) * (bottom1 - top1)))
        points_exact.append((x, bottom1 - (exact - ymin) / (ymax - ymin) * (bottom1 - top1)))
    _polyline(lines, points_exact, "orange", 2.4)
    _polyline(lines, points_calc, "blue", 1.6)
    lines.append(f'<line class="axis" x1="{left}" y1="{bottom1}" x2="{right}" y2="{bottom1}"/>')
    lines.append(f'<line class="axis" x1="{left}" y1="{top1}" x2="{left}" y2="{bottom1}"/>')
    _text(lines, 95, 76, "Displacement (length units as provided)", "label")
    _text(lines, 290, 76, "Analytical", "small")
    lines.append('<line class="orange" x1="270" y1="72" x2="284" y2="72" stroke-width="2.4"/>')
    _text(lines, 385, 76, "QF Solver", "small")
    lines.append('<line class="blue" x1="365" y1="72" x2="379" y2="72" stroke-width="2.4"/>')
    emax = max(errors) or 1.0
    error_points = []
    for t, err in zip(times, errors, strict=True):
        x = left + (t / times[-1]) * (right - left)
        error_points.append((x, bottom2 - err / emax * (bottom2 - top2)))
    for i in range(4):
        y = top2 + (bottom2 - top2) * i / 3
        lines.append(f'<line class="grid" x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}"/>')
    _polyline(lines, error_points, "red", 1.8)
    lines.append(f'<line class="axis" x1="{left}" y1="{bottom2}" x2="{right}" y2="{bottom2}"/>')
    lines.append(f'<line class="axis" x1="{left}" y1="{top2}" x2="{left}" y2="{bottom2}"/>')
    _text(lines, 95, 397, "Absolute error (same length units)", "label")
    _text(lines, 475, 580, "Time (s): 0–0.004; 80 steps; β=0.25, γ=0.5; one time step only.", "small", "middle")
    _save_svg(path, lines)


def _figure_beam(path: Path, uy: dict[str, Any], uz: dict[str, Any]) -> None:
    cases = [("UY/RZ", uy), ("UZ/RY", uz)]
    lines = _svg_header(
        "BEAM2 — one-element Timoshenko comparison",
        820,
        430,
        "Relative displacement and rotation errors for two principal bending planes of one straight uniform BEAM2 cantilever. This is not a mesh-convergence or 3-D validation study.",
    )
    left, right, top, bottom = 105.0, 770.0, 100.0, 300.0
    max_err = max(item[1]["displacement_relative_error"] for item in cases) * 1.15
    max_err = max(max_err, max(item[1]["rotation_relative_error"] for item in cases) * 1.15)
    for i in range(5):
        val = max_err * i / 4
        y = bottom - val / max_err * (bottom - top)
        lines.append(f'<line class="grid" x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}"/>')
        _text(lines, left - 10, y + 4, f"{val:.1e}", "small", "end")
    xs = {"UY/RZ": 290.0, "UZ/RY": 590.0}
    for label, item in cases:
        x = xs[label]
        for offset, key, css in (
            (-25, "displacement_relative_error", "blue"),
            (25, "rotation_relative_error", "orange"),
        ):
            val = item[key]
            y = bottom - val / max_err * (bottom - top)
            _dot(lines, x + offset, y, css, 7)
            _text(lines, x + offset, y - 12, f"{val:.2e}", "small", "middle")
        _text(lines, x, bottom + 25, label, "label", "middle")
    lines.append(f'<line class="axis" x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}"/>')
    lines.append(f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{bottom}"/>')
    _dot(lines, 260, 360, "blue", 5)
    _text(lines, 273, 364, "Displacement relative error", "small")
    _dot(lines, 475, 360, "orange", 5)
    _text(lines, 488, 364, "Rotation relative error", "small")
    _text(lines, 420, 402, "One straight, uniform BEAM2 element per case; tolerance 1e−12.", "small", "middle")
    _save_svg(path, lines)


def _figure_tet4(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = _svg_header(
        "FEM-TET4-H-001 — bounded refinement characterization",
        920,
        650,
        "Three mesh levels show tip-face UZ and relative error against a 1-D beam diagnostic. The utility returned WARNING; this is not asymptotic convergence or physical validation.",
    )
    left, right = 105.0, 870.0
    top1, bottom1, top2, bottom2 = 105.0, 345.0, 430.0, 560.0
    dofs = [row["dofs"] for row in rows]
    xlo, xhi = math.log10(min(dofs)), math.log10(max(dofs))
    vals = [row["tip_uz_m"] for row in rows]
    ref = rows[0]["reference_tip_uz_m"]
    ylo, yhi = min(vals + [ref]) * 1.08, 0.0
    points = []
    for row in rows:
        x = left + (math.log10(row["dofs"]) - xlo) / (xhi - xlo) * (right - left)
        y = bottom1 - (row["tip_uz_m"] - ylo) / (yhi - ylo) * (bottom1 - top1)
        points.append((x, y))
    for i in range(5):
        yv = ylo + (yhi - ylo) * i / 4
        y = bottom1 - (yv - ylo) / (yhi - ylo) * (bottom1 - top1)
        lines.append(f'<line class="grid" x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}"/>')
        _text(lines, left - 10, y + 4, f"{yv:.2e}", "small", "end")
    _polyline(lines, points, "blue", 2.2)
    yref = bottom1 - (ref - ylo) / (yhi - ylo) * (bottom1 - top1)
    lines.append(
        f'<line class="orange" x1="{left}" y1="{yref:.2f}" x2="{right}" y2="{yref:.2f}" stroke-width="2" stroke-dasharray="6,4"/>'
    )
    for x, y in points:
        _dot(lines, x, y, "blue", 5)
    lines.append(f'<line class="axis" x1="{left}" y1="{bottom1}" x2="{right}" y2="{bottom1}"/>')
    lines.append(f'<line class="axis" x1="{left}" y1="{top1}" x2="{left}" y2="{bottom1}"/>')
    _text(lines, 105, 82, "Tip-face UZ (m); dashed line = 1-D Euler–Bernoulli/Timoshenko diagnostic", "label")
    _text(lines, 480, 385, "Degrees of freedom (log scale)", "small", "middle")
    x_values = [left + (math.log10(n) - xlo) / (xhi - xlo) * (right - left) for n in dofs]
    for x, row in zip(x_values, rows, strict=True):
        _text(lines, x, bottom1 + 18, str(row["dofs"]), "small", "middle")
    errors = [row["relative_error"] for row in rows]
    residuals = [row["relative_residual"] for row in rows]
    max_error = max(errors) * 1.1
    max_residual = max(residuals) * 1.2
    error_points = []
    residual_points = []
    for x, error, residual in zip(x_values, errors, residuals, strict=True):
        error_points.append((x, bottom2 - error / max_error * (bottom2 - top2)))
        residual_points.append((x, bottom2 - residual / max_residual * (bottom2 - top2)))
    for i in range(4):
        y = top2 + (bottom2 - top2) * i / 3
        lines.append(f'<line class="grid" x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}"/>')
    _polyline(lines, error_points, "red", 2.0)
    _polyline(lines, residual_points, "green", 2.0)
    for x, y in error_points:
        _dot(lines, x, y, "red", 4)
    for x, y in residual_points:
        _dot(lines, x, y, "green", 4)
    lines.append(f'<line class="axis" x1="{left}" y1="{bottom2}" x2="{right}" y2="{bottom2}"/>')
    _text(lines, 105, 415, "Relative error to beam diagnostic and solver residual", "label")
    _text(lines, 220, 600, "Red: relative reference error", "small")
    _text(lines, 475, 600, "Green: relative residual", "small")
    _text(lines, 710, 600, "Helper status: WARNING", "small")
    _text(
        lines,
        480,
        630,
        "Three levels characterize refinement only; no asymptotic order or 3-D validation claimed.",
        "small",
        "middle",
    )
    _save_svg(path, lines)


def _run_id(receipt: dict[str, Any]) -> str:
    return str(receipt["run_id"])


def main() -> int:
    manifest, receipts, receipt_paths = _load_evidence()
    decisions_index = Path(manifest["evidence_root"]) / manifest["campaign_id"] / "_owner_decisions" / "index.json"
    approval_index = json.loads(decisions_index.read_text(encoding="utf-8"))
    stamp = approval_index["approved_at_utc"].replace("-", "").replace(":", "").replace("+00:00", "Z")
    output_dir = PACKAGE / "results" / f"{manifest['campaign_id']}-{stamp}"
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(exist_ok=False)

    all_rows: list[dict[str, Any]] = []
    for case_id in EXPECTED_CASES:
        receipt = receipts[case_id]
        payload = receipt["numeric_observables"]["payload"]["values"]
        receipt_path = receipt_paths[case_id]
        receipt_sha = _sha256(receipt_path)
        if case_id == "ALG-PROJ-QUANT-001":
            observed = payload["projected_structured"]
            reference = payload["projected_dense"]
            errors = {
                "max_abs": payload["max_absolute_difference"],
                "relative_frobenius": payload["relative_frobenius_error"],
            }
            criterion = "exact symmetry; np.allclose rtol=atol=2e-16"
            interpretation = "Algebraic identity for the recorded synthetic operators; not FEM validation."
        elif case_id == "MODAL-DISCRETE-QUANT-001":
            observed = {
                "k_effective": payload["k_effective"],
                "m_effective": payload["m_effective"],
                "frequency": payload["frequency_computed_cycles_per_consistent_time_unit"],
            }
            reference = {"frequency": payload["frequency_reference_cycles_per_consistent_time_unit"]}
            errors = {
                "relative_frequency": payload["relative_frequency_error"],
                "relative_modal_residual": payload["relative_modal_residual"],
            }
            criterion = "frequency relative tolerance 1e-12; relative modal residual <1e-12"
            interpretation = "Analytical spring/mass check; source does not declare physical units."
        elif case_id == "MODAL-2DOF-QUANT-001":
            observed = {
                "eigenvalues": payload["eigenvalues"],
                "frequencies_hz": payload["frequencies_hz"],
                "projected_mass": payload["projected_mass"],
                "projected_stiffness": payload["projected_stiffness"],
            }
            reference = {"eigenvalues_same_scipy_backend": payload["eigenvalue_reference_scipy_same_backend"]}
            errors = {
                "mass_orthogonality_frobenius": payload["mass_orthogonality_frobenius_error"],
                "max_modal_relative_residual": max(payload["modal_relative_residuals"]),
                "reconstructed_stiffness_frobenius": payload["reconstructed_stiffness_frobenius_error"],
            }
            criterion = "same-backend eigenvalue rtol/atol 1e-12; projected-operator rtol/atol 1e-11"
            interpretation = "Same-SciPy-backend consistency; not an independent modal oracle."
        elif case_id == "DYN-SDOF-QUANT-001":
            observed = {
                "final_displacement": payload["displacement_computed_m_or_consistent_length"][-1],
                "max_absolute_error": payload["max_absolute_error"],
                "rms_absolute_error": payload["rms_absolute_error"],
                "samples": len(payload["times_s"]),
            }
            reference = {
                "final_analytic_displacement": payload["displacement_analytic_m_or_consistent_length"][-1],
                "frequency_source": payload["analytic_frequency_source"],
            }
            errors = {
                "max_error_over_initial_amplitude": payload["max_error_over_initial_amplitude"],
                "rms_error_over_rms_analytic": payload["rms_error_over_rms_analytic"],
                "energy_drift_max": payload["relative_energy_drift_max"],
                "initial_projection_mass_error": payload["initial_projection_relative_mass_error"],
                "reduced_equilibrium_error": payload["reduced_equilibrium_max_relative_error"],
            }
            criterion = "final displacement rtol=2e-4 atol=1e-9; initial projection <1e-12; reduced equilibrium <1e-7"
            interpretation = "One-dt Newmark check with frequency derived from prepared FE K/M; no time convergence."
        elif case_id == "MODAL-2DOF-POLY-001":
            observed = {
                "computed_eigenvalues": payload["computed_eigenvalues"],
                "relative_eigenvalue_errors": payload["relative_eigenvalue_errors"],
            }
            reference = {
                "scalar_polynomial_eigenvalues": payload["expected_eigenvalues_from_scalar_polynomial"],
                "coefficients": payload["characteristic_coefficients_rational"],
            }
            errors = {
                "relative_eigenvalue_errors": payload["relative_eigenvalue_errors"],
                "modal_relative_residuals": payload["modal_relative_residuals"],
                "mass_orthogonality_frobenius": payload["mass_orthogonality_frobenius_error"],
                "projected_stiffness_offdiagonal_abs_from_junit": 4.4408921e-16,
            }
            criterion = "scalar eigenvalue relative tolerance 1e-10; residual and mass-orthogonality limits 1e-8; additional projected-K assertion rtol=1e-10 atol=0"
            interpretation = "Overall test FAIL: projected-K off-diagonals about -4.44e-16 are compared with exact zero at atol=0; scalar roots themselves meet their stated error limits. Preserve FAIL."
        elif case_id in {"STAT-BEAM-UY-001", "STAT-BEAM-UZ-001"}:
            observed = {
                "plane": payload["plane"],
                "displacement_m": payload["displacement_computed_m"],
                "rotation_rad": payload["rotation_computed_rad"],
            }
            reference = {
                "displacement_timoshenko_m": payload["displacement_timoshenko_reference_m"],
                "rotation_timoshenko_rad": payload["rotation_timoshenko_reference_rad"],
            }
            errors = {
                "displacement_absolute_m": payload["displacement_absolute_error_m"],
                "displacement_relative": payload["displacement_relative_error"],
                "rotation_absolute_rad": payload["rotation_absolute_error_rad"],
                "rotation_relative": payload["rotation_relative_error"],
            }
            criterion = "existing one-element Timoshenko displacement and rotation relative tolerance 1e-12"
            interpretation = "One straight uniform BEAM2 cantilever; not mesh convergence or 3-D validation."
        else:
            rows = payload["rows"]
            observed = [
                {
                    "factor": row["factor"],
                    "elements": row["elements"],
                    "nodes": row["nodes"],
                    "dofs": row["dofs"],
                    "tip_uz_m": row["tip_uz_m"],
                }
                for row in rows
            ]
            reference = {
                "beam_diagnostic_tip_uz_m": payload["reference"]["tip_uz_m"],
                "type": payload["reference"]["type"],
            }
            errors = {
                "relative_error_to_beam_diagnostic": [row["relative_error"] for row in rows],
                "relative_residuals": [row["relative_residual"] for row in rows],
                "reported_observed_orders_not_asymptotic": payload["observed_orders"],
            }
            criterion = "characterization-only: expected mesh counts and finite outputs; no physical or asymptotic convergence threshold"
            interpretation = (
                "Helper WARNING; reference error remains 66.7% on finest mesh. No asymptotic order or 3-D validation."
            )
        all_rows.append(
            {
                "case_id": case_id,
                "run_id": _run_id(receipt),
                "nodeid": receipt["nodeid"],
                "pytest_status": receipt["status"],
                "observable_status": receipt["numeric_observables"]["status"],
                "computed": json.dumps(observed, ensure_ascii=False, separators=(",", ":")),
                "reference": json.dumps(reference, ensure_ascii=False, separators=(",", ":")),
                "errors": json.dumps(errors, ensure_ascii=False, separators=(",", ":")),
                "criterion": criterion,
                "scientific_interpretation": interpretation,
                "receipt_sha256": receipt_sha,
                "raw_receipt": f"evidence://{manifest['campaign_id']}/{case_id}/{receipts[case_id]['run_id']}/receipt.json",
                "figure": "",
            }
        )

    q1_q4 = [row for row in all_rows if row["case_id"] in EXPECTED_CASES[:4]]
    _write_csv(output_dir / "Q1_Q4_EXECUTED_RESULTS.csv", list(q1_q4[0]), q1_q4)
    _write_csv(output_dir / "WP12_S_ALL_CASE_RESULTS.csv", list(all_rows[0]), all_rows)

    tet4_payload = receipts["FEM-TET4-H-001"]["numeric_observables"]["payload"]["values"]
    _write_csv(output_dir / "FEM-TET4-H-001-levels.csv", list(tet4_payload["rows"][0]), tet4_payload["rows"])
    dyn_values = receipts["DYN-SDOF-QUANT-001"]["numeric_observables"]["payload"]["values"]
    dynamic_rows = [
        {
            "time_s": time_value,
            "displacement_computed": computed,
            "displacement_analytic": analytic,
            "absolute_error": abs(computed - analytic),
        }
        for time_value, computed, analytic in zip(
            dyn_values["times_s"],
            dyn_values["displacement_computed_m_or_consistent_length"],
            dyn_values["displacement_analytic_m_or_consistent_length"],
            strict=True,
        )
    ]
    _write_csv(output_dir / "DYN-SDOF-QUANT-001-history.csv", list(dynamic_rows[0]), dynamic_rows)

    q2 = receipts["MODAL-DISCRETE-QUANT-001"]["numeric_observables"]["payload"]["values"]
    q5 = receipts["MODAL-2DOF-POLY-001"]["numeric_observables"]["payload"]["values"]
    beam_uy = receipts["STAT-BEAM-UY-001"]["numeric_observables"]["payload"]["values"]
    beam_uz = receipts["STAT-BEAM-UZ-001"]["numeric_observables"]["payload"]["values"]
    figures = output_dir / "figures"
    figures.mkdir(exist_ok=False)
    _figure_modal_discrete(figures / "modal-discrete-frequency.svg", q2)
    _figure_modal_roots(figures / "modal-2dof-independent-roots.svg", q5)
    _figure_newmark(figures / "newmark-sdof-history.svg", dyn_values)
    _figure_beam(figures / "beam2-timoshenko-two-planes.svg", beam_uy, beam_uz)
    _figure_tet4(figures / "tet4-refinement-characterization.svg", tet4_payload["rows"])

    inventory = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file():
            inventory.append({"path": path.relative_to(output_dir).as_posix(), "sha256": _sha256(path)})
    renderer = Path(__file__).resolve()
    index = {
        "schema": "qf-wp12-s-derived-results-index-v1",
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "campaign_id": manifest["campaign_id"],
        "authorization_issued_at_utc": approval_index["approved_at_utc"],
        "rendered_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "raw_evidence_location": "External local archive declared by the frozen manifest; omitted here to avoid recording a machine-specific path.",
        "available_reproduction_renderer": {
            "path": "../../render_results.py",
            "sha256": _sha256(renderer),
            "note": "Current renderer for reconstructing the indexed data from the verified receipts; it is not asserted to be the exact source revision that originally produced these artifacts.",
        },
        "source_receipts": {
            case_id: {"run_id": receipts[case_id]["run_id"], "sha256": _sha256(receipt_paths[case_id])}
            for case_id in EXPECTED_CASES
        },
        "scientific_execution": "COMPLETED_FOR_EIGHT_AUTHORIZED_CASES; one pytest FAIL preserved",
        "qualification_status": "NOT_ASSIGNED; PYTEST_PASS_ONLY IS NOT AN ORACLE OR WP12 VERDICT",
        "index_excluded_from_its_own_inventory": True,
        "files": inventory,
    }
    (output_dir / "RESULTS_INDEX.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "output_directory": str(output_dir),
                "case_count": len(all_rows),
                "figures": 5,
                "manifest_sha256": EXPECTED_MANIFEST_SHA256,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
