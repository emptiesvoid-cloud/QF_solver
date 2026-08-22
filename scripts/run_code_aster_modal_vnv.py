"""Run and normalize the same-mesh MITC4/Code_Aster modal correlation."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.verification.mitc4_modal_external import STUDY_ID, Mitc4CodeAsterModalStudy
from solveur.verification.mitc4_modal_plate import TEN_MODE_ORDERS
from solveur.version import DISPLAY_NAME


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "qualification" / "vnv" / "external" / "code_aster_modal" / "plate_modal.comm.template"
IMAGE = "simvia/code_aster@sha256:4629a21a109309bb97fbdc27d750445cc869e151e2e2ed6290f69539614e4435"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mesh-size", type=int, default=32)
    parser.add_argument("--skip-run", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    _write_inputs(output, args.mesh_size)
    if not args.skip_run:
        _run_code_aster(output)
    summary = _normalize(output, args.mesh_size)
    _publish_controlled_reference(output)
    print(f"{STUDY_ID}: {summary['status']}")
    return 0 if summary["status"] in {"PASS_EXTERNAL_CORRELATION", "WARNING"} else 1


def _write_inputs(output: Path, size: int) -> None:
    node_count = (size + 1) ** 2
    (output / "plate_modal.mail").write_text(_mesh_text(size), encoding="ascii")
    template = TEMPLATE.read_text(encoding="utf-8")
    (output / "plate_modal.comm").write_text(
        template.replace("__NODE_COUNT__", str(node_count)), encoding="utf-8"
    )
    (output / "plate_modal.export").write_text(
        "\n".join(
            [
                "P time_limit 900", "P memory_limit 4096", "P ncpus 1", "P mpi_nbcpu 1",
                "F comm /work/plate_modal.comm D 1",
                "F mail /work/plate_modal.mail D 20", "",
            ]
        ),
        encoding="ascii",
    )


def _mesh_text(size: int) -> str:
    if size < 4:
        raise ValueError("mesh size must be at least 4")
    lines = ["TITRE", "MITC4 modal same-mesh Code_Aster correlation", "FINSF", "COOR_3D"]
    for j in range(size + 1):
        for i in range(size + 1):
            node = j * (size + 1) + i + 1
            lines.append(f"N{node} {i / size:.16g} {j / size - 0.5:.16g} 0.0")
    lines.extend(["FINSF", "QUAD4"])
    for j in range(size):
        for i in range(size):
            element = j * size + i + 1
            n1 = j * (size + 1) + i + 1
            lines.append(f"M{element} N{n1} N{n1 + 1} N{n1 + size + 2} N{n1 + size + 1}")
    lines.extend(["FINSF", "GROUP_MA", "PLATE", *(f"M{i}" for i in range(1, size * size + 1)), "FINSF"])
    all_nodes = list(range(1, (size + 1) ** 2 + 1))
    edge = sorted(
        set(range(1, size + 2))
        | set(range(size * (size + 1) + 1, (size + 1) ** 2 + 1))
        | set(range(1, (size + 1) ** 2 + 1, size + 1))
        | set(range(size + 1, (size + 1) ** 2 + 1, size + 1))
    )
    for name, nodes in (("NALL", all_nodes), ("EDGE", edge)):
        lines.extend(["GROUP_NO", name, *(f"N{node}" for node in nodes), "FINSF"])
    lines.append("FIN")
    return "\n".join(lines) + "\n"


def _run_code_aster(output: Path) -> None:
    profile = (
        "/opt/spack/opt/spack/linux-zen/code-aster-18.1.0-"
        "owafurl325k3dbxls3s645zyfmvakxsg"
    )
    serial = (
        f"export RUNASTER_ROOT={profile}; source {profile}/share/aster/profile.sh; "
        "export PYTHONPATH=$(find /opt/spack/opt/spack/linux-zen -type d "
        "-path '*/lib/python3.11/site-packages' | paste -sd: -):${PYTHONPATH:-}; "
        "export LD_LIBRARY_PATH=$(find /opt/spack/opt/spack/linux-zen -type d "
        "\\( -name lib -o -name lib64 \\) | paste -sd: -):${LD_LIBRARY_PATH:-}; "
        "python3 /work/plate_modal.comm --last "
        "--link=F::mail::/work/plate_modal.mail::D::20 "
        "--memory 4096 --tpmax 900 --numthreads 1"
    )
    command = [
        "docker", "run", "--rm", "-v", f"{output}:/work", "--workdir", "/work",
        "--entrypoint", "/bin/bash", IMAGE, "-c", serial,
    ]
    completed = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=1200, check=False,
    )
    (output / "code_aster_stdout.log").write_text(completed.stdout, encoding="utf-8")
    (output / "code_aster_stderr.log").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        tail = "\n".join((completed.stdout + completed.stderr).splitlines()[-40:])
        raise RuntimeError(f"Code_Aster failed with exit code {completed.returncode}:\n{tail}")
    if not (output / "code_aster_modal_raw.json").is_file():
        raise RuntimeError("Code_Aster completed without code_aster_modal_raw.json")
    for pattern in ("fort.*", "glob.*", "vola.*"):
        for transient in output.glob(pattern):
            transient.unlink(missing_ok=True)


def _normalize(output: Path, mesh_size: int) -> dict[str, Any]:
    full = Mitc4CodeAsterModalStudy(mesh_size=mesh_size).run(output / "code_aster_modal_raw.json")
    internal_status = full["status"]
    full["internal_verdict"] = internal_status
    full["maturity"] = "verified_development_external_correlation"
    full["status"] = (
        "PASS_EXTERNAL_CORRELATION" if internal_status == "PASS" else "FAIL"
    )
    plot_data = full.pop("_plot_data")
    full["solver"] = {"name": "Code_Aster", "version": "18.1.0", "formulation": "DKT/DKQ"}
    full["container"] = {"image": IMAGE}
    full["inputs_sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.glob("plate_modal.*"))
    }
    write_json_file(output / "summary.json", full)
    _plot_frequencies(full, output / f"{STUDY_ID}-frequencies.png")
    _plot_modes(plot_data, mesh_size, output / f"{STUDY_ID}-modes.png")
    (output / f"{STUDY_ID}.md").write_text(_markdown(full), encoding="utf-8")
    write_json_file(
        output / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "source": _portable_source_state(),
            "files": discovered_file_entries(
                output, lambda _: "mitc4_modal_code_aster_vnv", exclude_names=("vnv_manifest.json",)
            ),
        },
    )
    return full


def _portable_source_state() -> dict[str, Any]:
    source = git_source_state(ROOT)
    source["repository"] = DISPLAY_NAME
    return source


def _publish_controlled_reference(output: Path) -> None:
    reference = TEMPLATE.parent / "reference"
    reference.mkdir(parents=True, exist_ok=True)
    names = (
        "code_aster_modal_raw.json",
        "summary.json",
        f"{STUDY_ID}-frequencies.png",
        f"{STUDY_ID}-modes.png",
        f"{STUDY_ID}.md",
        "vnv_manifest.json",
    )
    for name in names:
        shutil.copy2(output / name, reference / name)
    assets = ROOT / "docs" / "assets" / "reviews"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        output / f"{STUDY_ID}-frequencies.png",
        assets / "mitc4_modal_code_aster_frequencies.png",
    )
    shutil.copy2(
        output / f"{STUDY_ID}-modes.png",
        assets / "mitc4_modal_code_aster_modes.png",
    )


def _plot_frequencies(summary: dict[str, Any], path: Path) -> None:
    labels = [f"({order[0]},{order[1]})" for order in summary["mode_orders"]]
    x = np.arange(len(labels))
    width = 0.25
    figure, axis = plt.subplots(figsize=(8.0, 4.6))
    for offset, (name, values, color) in enumerate(
        (
            ("Navier", summary["frequencies_hz"]["navier"], "#495057"),
            ("QF_solver MITC4", summary["frequencies_hz"]["qf_solver"], "#087f5b"),
            ("Code_Aster DKQ", summary["frequencies_hz"]["code_aster"], "#c92a2a"),
        )
    ):
        axis.bar(x + (offset - 1) * width, values, width=width, label=name, color=color)
    axis.set_xticks(x, labels, rotation=35, ha="right")
    axis.set(
        xlabel="famille modale",
        ylabel="frequence [Hz]",
        title=(
            f"Plaque {summary['model']['mesh'][0]}x{summary['model']['mesh'][1]} "
            "- comparaison des dix premiers modes"
        ),
    )
    axis.grid(True, axis="y", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _plot_modes(data: dict[str, Any], size: int, path: Path) -> None:
    nodes = np.asarray(data["nodes"], dtype=float)
    sources = (
        ("Navier", np.asarray(data["navier_shapes"])),
        ("QF_solver MITC4", np.asarray(data["qf_shapes"])),
        ("Code_Aster DKQ", np.asarray(data["code_aster_shapes"])),
    )
    navier = sources[0][1]
    mode_orders = tuple(TEN_MODE_ORDERS)
    figure, axes = plt.subplots(3, len(mode_orders), figsize=(20.0, 6.5), sharex=True, sharey=True)
    for row, (source_name, shapes) in enumerate(sources):
        displayed = _comparable_shapes(shapes, navier)
        for column, order in enumerate(mode_orders):
            values = displayed[:, column].reshape((size + 1, size + 1))
            limit = max(float(np.max(np.abs(values))), 1.0e-30)
            axes[row, column].contourf(
                nodes[:, 0].reshape((size + 1, size + 1)),
                (nodes[:, 1] + 0.5).reshape((size + 1, size + 1)),
                values, levels=np.linspace(-limit, limit, 21), cmap="RdBu_r",
            )
            axes[row, column].set_title(f"{source_name} {order}", fontsize=9)
            axes[row, column].set_aspect("equal")
    figure.suptitle("Formes propres transverses comparees - amplitudes normalisees")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _comparable_shapes(shapes: np.ndarray, navier: np.ndarray) -> np.ndarray:
    result = np.zeros_like(shapes)
    for group in ((0,), (1, 2), (3,), (4, 5), (6, 7), (8, 9)):
        if len(group) == 1:
            index = group[0]
            vector = shapes[:, index]
            sign = 1.0 if float(np.dot(vector, navier[:, index])) >= 0.0 else -1.0
            result[:, index] = sign * vector / max(
                float(np.max(np.abs(vector))), 1.0e-30
            )
            continue
        basis, _ = np.linalg.qr(shapes[:, group])
        for index in group:
            projected = basis @ (basis.T @ navier[:, index])
            result[:, index] = projected / max(
                float(np.max(np.abs(projected))), 1.0e-30
            )
    return result


def _markdown(summary: dict[str, Any]) -> str:
    rows = []
    for index, order in enumerate(summary["mode_orders"]):
        navier = summary["frequencies_hz"]["navier"][index]
        qf = summary["frequencies_hz"]["qf_solver"][index]
        aster = summary["frequencies_hz"]["code_aster"][index]
        qf_aster = summary["metrics"]["qf_code_aster_frequency_differences"][index]
        rows.append(
            f"| {tuple(order)} | {navier:.6f} | {qf:.6f} | {aster:.6f} | {100*qf_aster:.3f} % |"
        )
    mac = summary["metrics"]["qf_code_aster_mac"]
    return "\n".join(
        [
            f"# {STUDY_ID}", "", f"Statut automatique : **{summary['status']}**.", "",
            "## Frequences", "",
            "| Mode | Navier [Hz] | QF_solver [Hz] | Code_Aster [Hz] | Ecart QF/Aster |",
            "| --- | ---: | ---: | ---: | ---: |", *rows, "",
            "## Formes", "",
            f"- MAC mode (1,1): `{mac['mode_11']:.8f}`;",
            f"- MAC sous-espace (1,2)/(2,1): `{mac['subspace_12_21']:.8f}`;",
            f"- MAC mode (2,2): `{mac['mode_22']:.8f}`;",
            f"- MAC sous-espace (1,3)/(3,1): `{mac['subspace_13_31']:.8f}`;",
            f"- MAC sous-espace (2,3)/(3,2): `{mac['subspace_23_32']:.8f}`;",
            f"- MAC sous-espace (1,4)/(4,1): `{mac['subspace_14_41']:.8f}`.", "",
            f"![Frequences]({STUDY_ID}-frequencies.png)", "",
            f"![Formes propres]({STUDY_ID}-modes.png)", "",
            "## Limites", "",
            *[f"- {item}" for item in summary["limitations"]], "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
