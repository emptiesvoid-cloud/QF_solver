from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from research.j16.harmonic_plotting import plot_harmonic_response


def replay_archived_plot(input_json: Path, output_png: Path, manifest_path: Path) -> dict[str, Any]:
    """Plot archived J15 rows without changing the source archive or statuses."""
    raw_input = input_json.read_bytes()
    payload = json.loads(raw_input)
    rows = payload.get("frequency_rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("archived site_data must contain non-empty frequency_rows")
    if output_png.exists() or manifest_path.exists():
        raise FileExistsError("replay output already exists; choose a new output path")

    qf_rows = [
        {
            "frequency_hz": row.get("frequency_hz"),
            "qf_route_status": row.get("qf_route_status"),
            "diagnostic_center_uz_amplitude_mm": row.get("diagnostic_center_uz_amplitude_mm"),
            "diagnostic_center_uz_phase_degrees": row.get("diagnostic_center_uz_phase_degrees"),
        }
        for row in rows
    ]
    reference_rows = [
        {
            "frequency_hz": row.get("frequency_hz"),
            "navier_uz_amplitude_mm": row.get("reference_uz_amplitude_mm"),
            "navier_uz_phase_degrees": row.get("reference_uz_phase_degrees"),
        }
        for row in rows
    ]
    exact_probe = payload.get("diagnostics", {}).get("exact_navier_peak_probe")
    if not isinstance(exact_probe, dict):
        raise ValueError("archived site_data is missing diagnostics.exact_navier_peak_probe")
    required_probe_fields = (
        "frequency_hz",
        "qf_route_status",
        "diagnostic_center_uz_amplitude_mm",
        "diagnostic_center_uz_phase_degrees",
        "navier_center_uz_amplitude_mm",
        "navier_center_uz_phase_degrees",
    )
    missing_probe_fields = [field for field in required_probe_fields if field not in exact_probe]
    if missing_probe_fields:
        raise ValueError(
            "archived site_data diagnostics.exact_navier_peak_probe is missing required fields: "
            + ", ".join(missing_probe_fields)
        )
    qf_rows.append(
        {
            "frequency_hz": exact_probe.get("frequency_hz"),
            "qf_route_status": exact_probe.get("qf_route_status"),
            "diagnostic_center_uz_amplitude_mm": exact_probe.get("diagnostic_center_uz_amplitude_mm"),
            "diagnostic_center_uz_phase_degrees": exact_probe.get("diagnostic_center_uz_phase_degrees"),
        }
    )
    reference_rows.append(
        {
            "frequency_hz": exact_probe.get("frequency_hz"),
            "navier_uz_amplitude_mm": exact_probe.get("navier_center_uz_amplitude_mm"),
            "navier_uz_phase_degrees": exact_probe.get("navier_center_uz_phase_degrees"),
        }
    )
    paired_rows = sorted(zip(qf_rows, reference_rows, strict=True), key=lambda pair: pair[0]["frequency_hz"])
    qf_rows = [pair[0] for pair in paired_rows]
    reference_rows = [pair[1] for pair in paired_rows]
    statuses = [row["qf_route_status"] for row in qf_rows]
    if any(not isinstance(status, str) for status in statuses):
        raise ValueError("archived frequency row is missing qf_route_status")

    output_png.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    plot_harmonic_response(qf_rows, reference_rows, output_png)
    output_bytes = output_png.read_bytes()
    manifest = {
        "schema": "qfsolver-j16-j15-plot-replay-v1",
        "classification": "ARCHIVED_EXPLORATORY_DATA_REPLOT_NO_SOLVER_CALL",
        "source_attempt_id": payload.get("original_run", {}).get("attempt_id"),
        "source_run_status": payload.get("original_run", {}).get("runner_state"),
        "postprocess_id": payload.get("postprocess_id"),
        "input_artifact": input_json.name,
        "input_sha256_raw": hashlib.sha256(raw_input).hexdigest(),
        "frequency_count": len(rows),
        "dense_frequency_count": len(rows),
        "additional_probe_count": 1,
        "additional_probe_frequency_hz": exact_probe.get("frequency_hz"),
        "plotted_point_count": len(qf_rows),
        "route_status_counts": dict(sorted(Counter(statuses).items())),
        "rejected_points_are_marked": True,
        "output_artifact": output_png.name,
        "output_bytes": len(output_bytes),
        "output_sha256_raw": hashlib.sha256(output_bytes).hexdigest(),
        "historical_status_policy": "Input rows and original J15 PYTEST_FAILED status are not changed or promoted.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    arguments = parser.parse_args()
    result = replay_archived_plot(arguments.input, arguments.output, arguments.manifest)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
