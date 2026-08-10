"""Build the MITC4 modal mechanical review as local HTML and PDF."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from build_mitc4_transient_review import _default_edge, _print_pdf, _render_html
from mitc4.mesh import MeshFactory


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MARKDOWN = ROOT / "docs" / "verification" / "revue_mitc4_modale.md"
DEFAULT_OUTPUT = ROOT / "results" / "reviews"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--edge", type=Path, default=_default_edge())
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    review_assets = ROOT / "docs" / "assets" / "reviews"
    review_assets.mkdir(parents=True, exist_ok=True)
    _plot_setup(review_assets / "mitc4_modal_review_setup.png")
    html_path = output / "revue_mitc4_modale.html"
    pdf_path = output / "revue_mitc4_modale.pdf"
    html_path.write_text(
        _render_html(
            args.input.resolve(),
            document_title="Revue mecanique MITC4 modale",
        ),
        encoding="utf-8",
    )
    _print_pdf(args.edge, html_path, pdf_path)
    published = review_assets / pdf_path.name
    shutil.copy2(pdf_path, published)
    print(f"Markdown: {args.input.resolve()}")
    print(f"PDF: {published}")
    return 0


def _plot_setup(path: Path) -> None:
    size = 32
    mesh = MeshFactory.rectangular_plate(size, size, 1.0, 1.0)
    nodes = mesh.nodes[:, :2].copy()
    nodes[:, 1] += 0.5
    figure, axis = plt.subplots(figsize=(8.0, 7.2))
    figure.patch.set_facecolor("white")
    axis.set_facecolor("white")
    for quad in mesh.quads:
        polygon = nodes[np.r_[quad, quad[0]]]
        axis.plot(polygon[:, 0], polygon[:, 1], color="#71838b", linewidth=0.38)
    edge = (
        np.isclose(nodes[:, 0], 0.0)
        | np.isclose(nodes[:, 0], 1.0)
        | np.isclose(nodes[:, 1], 0.0)
        | np.isclose(nodes[:, 1], 1.0)
    )
    axis.scatter(nodes[:, 0], nodes[:, 1], s=4, color="#263238", zorder=3)
    axis.scatter(
        nodes[edge, 0], nodes[edge, 1], marker="s", s=25,
        facecolors="none", edgecolors="#1565c0", linewidths=1.0,
        label="quatre bords: UZ=0",
    )
    axis.text(
        0.02, -0.12,
        "Correlation externe: UX=UY=RZ=0 sur tous les noeuds; RX/RY libres; aucune charge",
        transform=axis.transAxes, fontsize=8.5,
    )
    axis.set(
        xlabel="x [m]", ylabel="y [m]", aspect="equal",
        title="Plaque modale simplement appuyee - maillage 32x32 identique",
        xlim=(-0.03, 1.03), ylim=(-0.03, 1.03),
    )
    axis.legend(loc="upper right", fontsize=8)
    figure.tight_layout()
    figure.savefig(path, dpi=180, bbox_inches="tight", facecolor="white", transparent=False)
    plt.close(figure)


if __name__ == "__main__":
    raise SystemExit(main())
