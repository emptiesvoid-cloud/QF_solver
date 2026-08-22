"""Build the MITC4 transient mechanical review as local HTML and PDF."""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
from pathlib import Path

import markdown
import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.compat.mitc4.mesh import MeshFactory


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MARKDOWN = ROOT / "docs" / "verification" / "revue_mitc4_transitoire.md"
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
    setup = review_assets / "mitc4_transient_review_setup.png"
    setup.parent.mkdir(parents=True, exist_ok=True)
    _plot_setup(setup)
    external_source = (
        ROOT
        / "results"
        / "VNV-MITC4-NEWMARK-CODEASTER-DKQ-005"
        / "code-aster-newmark-comparison.png"
    )
    external_published = review_assets / "mitc4_code_aster_newmark.png"
    if external_source.is_file():
        shutil.copy2(external_source, external_published)
    html_path = output / "revue_mitc4_transitoire.html"
    pdf_path = output / "revue_mitc4_transitoire.pdf"
    html_path.write_text(_render_html(args.input.resolve()), encoding="utf-8")
    _print_pdf(args.edge, html_path, pdf_path)
    published_pdf = review_assets / pdf_path.name
    published_pdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pdf_path, published_pdf)
    print(f"Markdown: {args.input.resolve()}")
    print(f"PDF: {pdf_path}")
    print(f"Published PDF: {published_pdf}")
    return 0


def _default_edge() -> Path:
    candidates = (
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    )
    return next((path for path in candidates if path.is_file()), candidates[0])


def _plot_setup(path: Path) -> None:
    mesh = MeshFactory.rectangular_plate(8, 8, 10.0, 10.0)
    nodes = mesh.nodes[:, :2]
    nodes[:, 1] += 5.0
    figure, axis = plt.subplots(figsize=(8.2, 7.2))
    figure.patch.set_facecolor("white")
    axis.set_facecolor("white")
    for quad in mesh.quads:
        polygon = nodes[np.r_[quad, quad[0]]]
        axis.plot(polygon[:, 0], polygon[:, 1], color="#607078", linewidth=0.65)
    axis.scatter(nodes[:, 0], nodes[:, 1], s=8, color="#263238", zorder=3)
    edge = (
        np.isclose(nodes[:, 0], 0.0)
        | np.isclose(nodes[:, 0], 10.0)
        | np.isclose(nodes[:, 1], 0.0)
        | np.isclose(nodes[:, 1], 10.0)
    )
    axis.scatter(
        nodes[edge, 0], nodes[edge, 1], marker="s", s=34,
        facecolors="none", edgecolors="#1565c0", linewidths=1.2,
        label="bords: UZ bloque",
    )
    center = int(np.argmin(np.linalg.norm(nodes - np.asarray([5.0, 5.0]), axis=1)))
    axis.annotate(
        "Fz(t) = 100 g(t) N",
        xy=nodes[center], xytext=(6.4, 7.4),
        arrowprops={"arrowstyle": "-|>", "color": "#c62828", "lw": 2.2},
        color="#c62828", fontsize=10, fontweight="bold",
    )
    axis.scatter(*nodes[center], s=58, color="#c62828", zorder=4, label="charge et sondes UZ/S11")
    axis.text(
        0.02, -0.13,
        "Tous noeuds: UX=UY=RZ=0 | bords horizontaux: RY=0 | bords verticaux: RX=0",
        transform=axis.transAxes, fontsize=9,
    )
    axis.set(
        xlabel="x [m]", ylabel="y [m]", aspect="equal",
        title="Plaque NAFEMS 13H - maillage MITC4 8x8 - chargement transitoire central",
        xlim=(-0.4, 10.4), ylim=(-0.4, 10.4),
    )
    axis.grid(False)
    axis.legend(loc="upper left", fontsize=8)
    figure.tight_layout()
    figure.savefig(path, dpi=180, bbox_inches="tight", facecolor="white", transparent=False)
    plt.close(figure)


def _render_html(
    markdown_path: Path,
    *,
    document_title: str = "Revue MITC4 transitoire",
) -> str:
    text = markdown_path.read_text(encoding="utf-8")
    if text.startswith("---"):
        text = text.split("---", 2)[-1]
    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists"],
    )
    body = re.sub(
        r'src="([^"]+)"',
        lambda match: f'src="{html.escape(_image_uri(markdown_path.parent, match.group(1)))}"',
        body,
    )
    title = html.escape(document_title)
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>{title}</title>
<style>
@page {{ size: A4; margin: 16mm 14mm 17mm; }}
body {{ font-family: Arial, sans-serif; color: #172126; font-size: 9.2pt; line-height: 1.38; }}
h1 {{ color: #123b4a; font-size: 22pt; border-bottom: 3px solid #0b7285; padding-bottom: 6px; }}
h2 {{ color: #0b5668; font-size: 15pt; border-bottom: 1px solid #9bbbc3; margin-top: 22px; }}
h3 {{ color: #244c56; font-size: 11.5pt; }}
table {{ width: 100%; border-collapse: collapse; margin: 8px 0 13px; font-size: 8.2pt; break-inside: avoid; }}
th {{ background: #dfeff2; color: #153a43; }}
th, td {{ border: 1px solid #9eb2b7; padding: 4px 5px; vertical-align: top; }}
tr:nth-child(even) td {{ background: #f5f8f9; }}
img {{ display: block; max-width: 96%; max-height: 225mm; margin: 10px auto 16px; break-inside: avoid; }}
code {{ font-family: Consolas, monospace; color: #7a2430; background: #f3f3f3; padding: 1px 3px; }}
pre {{ background: #f3f6f7; border-left: 3px solid #0b7285; padding: 8px; white-space: pre-wrap; font-size: 7.6pt; break-inside: avoid; }}
li {{ margin-bottom: 3px; }}
p {{ orphans: 3; widows: 3; }}
</style></head><body>{body}</body></html>"""


def _image_uri(base: Path, value: str) -> str:
    if value.startswith(("http://", "https://", "data:")):
        return value
    return (base / value).resolve().as_uri()


def _print_pdf(edge: Path, html_path: Path, pdf_path: Path) -> None:
    if not edge.is_file():
        raise FileNotFoundError(f"Microsoft Edge was not found at {edge}")
    command = [
        str(edge), "--headless=new", "--disable-gpu", "--allow-file-access-from-files",
        "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", html_path.as_uri(),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    if completed.returncode != 0 or not pdf_path.is_file():
        raise RuntimeError(
            f"PDF rendering failed ({completed.returncode}): {completed.stderr[-1000:]}"
        )
    if pdf_path.stat().st_size < 50_000 or not pdf_path.read_bytes().startswith(b"%PDF"):
        raise RuntimeError("Generated PDF is missing or unexpectedly small")


if __name__ == "__main__":
    raise SystemExit(main())
