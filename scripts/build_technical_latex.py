"""Build the QF_solver technical Owner-review manual with native LaTeX."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "qualification" / "documentation_review_pages.json"
HEADER = ROOT / "docs" / "latex" / "qf_solver_header.tex"
TEX_OUTPUT = ROOT / "tmp" / "pdfs" / "qf_solver_manual.tex"
PDF_OUTPUT = ROOT / "output" / "pdf" / "dossier_technique_elements_methodes_revision_0_3_candidate.pdf"
WORK = ROOT / "tmp" / "pdfs" / "qf_solver_manual"
IMAGE_PATTERN = re.compile(r"(!\[[^\]]*\]\()([^)]*)(\)(?:\{[^}]*\})?)")
SNIPPET_PATTERN = re.compile(r'--8<--\s+"([^"]+)"')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PDF_OUTPUT)
    parser.add_argument("--tex-output", type=Path, default=TEX_OUTPUT)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--skip-assets", action="store_true")
    args = parser.parse_args()
    build_manual(
        output=args.output.resolve(),
        tex_output=args.tex_output.resolve(),
        registry=args.registry.resolve(),
        rebuild_assets=not args.skip_assets,
    )
    print(f"LaTeX: {args.tex_output.resolve()}")
    print(f"PDF: {args.output.resolve()}")
    return 0


def build_manual(*, output: Path, tex_output: Path, registry: Path, rebuild_assets: bool) -> None:
    payload = json.loads(registry.read_text(encoding="utf-8"))
    if rebuild_assets:
        _rebuild_documentation_assets()
    WORK.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    tex_output.parent.mkdir(parents=True, exist_ok=True)
    markdown = WORK / "qf_solver_manual.md"
    markdown.write_text(_compose_markdown(payload), encoding="utf-8")
    _run_pandoc(markdown, tex_output)
    built_pdf = _run_pdflatex(tex_output)
    shutil.copy2(built_pdf, output)
    _validate_pdf(output, payload)


def _rebuild_documentation_assets() -> None:
    command = [
        os.fspath(_python()),
        os.fspath(ROOT / "scripts" / "build_docs.py"),
        "--profile",
        "engineering",
    ]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if completed.returncode != 0:
        # The manual can still be rebuilt from controlled existing evidence.
        print("WARNING: documentation assets were not fully regenerated.")
        print((completed.stderr or completed.stdout)[-2000:])


def _compose_markdown(payload: dict) -> str:
    pages = payload["pages"]
    policy = payload.get("policy", {})
    revision = str(policy.get("candidate_revision", "validated"))
    status = str(policy.get("candidate_status", "controlled"))
    title_block = r"""\begin{titlepage}
\centering
\vspace*{22mm}
{\Huge\bfseries\color{QFBlue} QF\_solver\par}
\vspace{7mm}
{\LARGE Dossier technique - elements et methodes\par}
\vspace{12mm}
{\large Version applicable 0.2.0 - revision documentaire __REVISION__\par}
\vspace{18mm}
\begin{qfwarning}
Etat : __STATUS__. Une demonstration documentee ne vaut pas qualification.
Cette revision candidate ne modifie ni le PDF 0.2.0 deja valide, ni la
maturite mecanique des elements et methodes.
\end{qfwarning}
\vfill
{\large Document genere depuis les sources techniques et les preuves numeriques\par}
\end{titlepage}

\tableofcontents
\clearpage
"""
    blocks = [
        title_block.replace("__REVISION__", _tex_escape(revision)).replace(
            "__STATUS__", _tex_escape(status)
        )
    ]
    for entry in (item for item in pages if item["kind"] == "element"):
        blocks.extend(_entry_blocks(entry))
    for entry in (item for item in pages if item["kind"] == "method"):
        blocks.extend(_entry_blocks(entry))
    blocks.extend(
        [
            "# Annexes transverses\n",
            "## Grille d’Owner review\n",
            """Une décision doit être enregistrée séparément pour chaque fiche. Une
acceptation documentaire ne modifie pas seule la maturité mécanique ou numérique.

```text
OWNER-REVIEW-DOC <doc_id>
Q1 Geometrie, DDL, reperes et signes : OUI/NON
Q2 Formulation, integration et algorithme : OUI/NON
Q3 Exemple, maillage, charges et blocages : OUI/NON
Q4 Resultats, figure, invariants et convergence : OUI/NON
Q5 Limites, references et tracabilite : OUI/NON
DECISION accepted | accepted_with_recommendations | changes_required
COMMENTS:
```

Owner : ...............................................................

Date : ..................................................................

Signature : .............................................................
""",
        ]
    )
    return "\n\n".join(blocks)


def _entry_blocks(entry: dict) -> list[str]:
    source_path = ROOT / entry["path"]
    title, source = _prepare_source(source_path, heading_shift=0)
    metadata = (
        "\\qfmeta"
        f"{{{_tex_escape(entry['kind'])}}}"
        f"{{{_tex_escape(entry['current_maturity'])}}}"
        f"{{{_tex_escape(entry['review_status'])}}}"
        f"{{{_tex_escape(entry['qualification_effect'])}}}"
    )
    blocks = [f"# {entry['id']} - {title}\n\n{metadata}\n\n{source}"]
    for appendix in entry.get("appendices", []):
        appendix_path = ROOT / appendix
        appendix_title, appendix_source = _prepare_source(appendix_path, heading_shift=1)
        blocks.append(
            "\\clearpage\n\n"
            f"## {appendix_title}\n\n"
            f"{appendix_source}"
        )
    return blocks


def _prepare_source(path: Path, *, heading_shift: int) -> tuple[str, str]:
    source = _strip_frontmatter(path.read_text(encoding="utf-8"))
    source = SNIPPET_PATTERN.sub(lambda match: _snippet(match.group(1)), source)
    lines = source.splitlines()
    title = path.stem.replace("_", " ")
    body: list[str] = []
    title_found = False
    for line in lines:
        if not title_found and line.startswith("# "):
            title = line[2:].strip()
            title_found = True
            continue
        if heading_shift and line.startswith("#"):
            hashes, separator, text = line.partition(" ")
            if separator and set(hashes) == {"#"}:
                line = "#" * min(len(hashes) + heading_shift, 5) + " " + text
        body.append(line)
    source = "\n".join(body)
    source = _resolve_images(source, path.parent)
    source = _break_long_code_paths(source)
    source = source.replace("<span class=\"maturity experimental\">experimental</span>", "**Maturité : experimental.**")
    source = re.sub(r"<p class=\"result-caption\">(.*?)</p>", r"*\1*", source, flags=re.DOTALL)
    return title, source


def _break_long_code_paths(source: str) -> str:
    def replacement(match: re.Match[str]) -> str:
        value = match.group(1)
        if len(value) < 16 or not any(separator in value for separator in ("/", "\\", "-", "_")):
            return match.group(0)
        if "{" in value or "}" in value:
            return match.group(0)
        return rf"\path{{{value}}}"

    return re.sub(r"`([^`\n]+)`", replacement, source)


def _strip_frontmatter(source: str) -> str:
    if not source.startswith("---"):
        return source
    parts = source.split("---", 2)
    return parts[2].lstrip() if len(parts) == 3 else source


def _snippet(raw_path: str) -> str:
    path = ROOT / raw_path
    return path.read_text(encoding="utf-8") if path.is_file() else f"**Snippet absent : `{raw_path}`**"


def _resolve_images(source: str, directory: Path) -> str:
    def replacement(match: re.Match[str]) -> str:
        raw = match.group(2).split()[0].strip("<>")
        if raw.startswith(("http://", "https://", "data:")):
            return match.group(0)
        image = (directory / raw).resolve()
        if not image.is_file():
            return f"**Figure absente : `{image.name}`**"
        if image.suffix.lower() == ".svg":
            image = _convert_svg(image)
        return match.group(1) + image.as_posix() + ")"

    return IMAGE_PATTERN.sub(replacement, source)


def _convert_svg(source: Path) -> Path:
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
    target = WORK / "assets" / f"{source.stem}-{digest}.pdf"
    if target.is_file():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        from reportlab.graphics import renderPDF
        from svglib.svglib import svg2rlg

        drawing = svg2rlg(os.fspath(source))
        if drawing is None:
            raise RuntimeError("SVG parser returned no drawing")
        renderPDF.drawToFile(drawing, os.fspath(target))
    except Exception as exc:  # pragma: no cover - environment-specific fallback
        raise RuntimeError(f"Cannot convert SVG figure {source}: {exc}") from exc
    return target


def _run_pandoc(markdown: Path, tex_output: Path) -> None:
    command = [
        os.fspath(_pandoc()),
        os.fspath(markdown),
        "--from=markdown+tex_math_dollars+tex_math_single_backslash+raw_tex+pipe_tables+link_attributes+fenced_code_blocks",
        "--to=latex",
        "--standalone",
        "--top-level-division=chapter",
        "--number-sections",
        "--toc-depth=2",
        "--metadata=lang:fr-FR",
        "--variable=documentclass:report",
        "--variable=classoption:openany",
        "--variable=papersize:a4",
        "--variable=fontsize:10pt",
        f"--include-in-header={HEADER.as_posix()}",
        f"--output={tex_output.as_posix()}",
    ]
    _checked_run(command, "Pandoc conversion")


def _run_pdflatex(tex_output: Path) -> Path:
    build_dir = WORK / "latex-build"
    build_dir.mkdir(parents=True, exist_ok=True)
    command = [
        os.fspath(_pdflatex()),
        "--enable-installer",
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-output-directory={build_dir.as_posix()}",
        tex_output.as_posix(),
    ]
    _checked_run(command, "LaTeX pass 1")
    _checked_run(command, "LaTeX pass 2")
    result = build_dir / f"{tex_output.stem}.pdf"
    if not result.is_file():
        raise RuntimeError("pdflatex did not create the expected PDF.")
    return result


def _checked_run(command: list[str], label: str) -> None:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if completed.returncode != 0:
        log = (completed.stdout + "\n" + completed.stderr)[-8000:]
        raise RuntimeError(f"{label} failed:\n{log}")


def _validate_pdf(output: Path, payload: dict) -> None:
    reader = PdfReader(output)
    if len(reader.pages) < 80:
        raise RuntimeError(f"Technical manual is unexpectedly short: {len(reader.pages)} pages.")
    texts = [page.extract_text() or "" for page in reader.pages]
    raw_markers = (r"\\begin{", r"\\frac", r"\\mathbf", "begin case")
    defects = [
        {"page": index + 1, "marker": marker}
        for index, text in enumerate(texts)
        for marker in raw_markers
        if marker.lower() in text.lower()
    ]
    if defects:
        raise RuntimeError(f"Unrendered LaTeX commands remain in PDF: {defects[:8]}")
    _write_page_count_report(output, payload, texts)


def _write_page_count_report(output: Path, payload: dict, texts: list[str]) -> None:
    compact_texts = [re.sub(r"\s+", "", text) for text in texts]
    starts = {}
    for entry in payload["pages"]:
        marker = re.sub(r"\s+", "", entry["id"])
        occurrences = [index for index, text in enumerate(compact_texts) if marker in text]
        starts[entry["id"]] = max(occurrences) if occurrences else -1
    report = {"schema_version": 2, "pdf": output.name, "elements": []}
    pages = payload["pages"]
    for index, entry in enumerate(pages):
        minimum = entry.get("minimum_pdf_pages")
        if minimum is None:
            continue
        start = starts[entry["id"]]
        later = [starts[item["id"]] for item in pages[index + 1 :] if starts[item["id"]] > start]
        end = min(later) if later else len(texts)
        count = max(end - start, 0)
        report["elements"].append(
            {"id": entry["id"], "pages": count, "minimum": minimum, "status": "PASS" if count >= minimum else "FAIL"}
        )
    report_name = (
        f"{output.stem}_page_counts.json"
        if "candidate" in output.stem
        else "dossier_technique_page_counts.json"
    )
    report_path = output.with_name(report_name)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    failures = [row for row in report["elements"] if row["status"] != "PASS"]
    if failures:
        raise RuntimeError(f"Element PDF page contracts failed: {failures}")


def _pandoc() -> Path:
    command = _configured_tool("QF_SOLVER_PANDOC", "pandoc")
    if command is not None:
        return command
    data_root = _user_data_root()
    if data_root is None:
        raise RuntimeError("Pandoc is unavailable. Add it to PATH or set QF_SOLVER_PANDOC.")
    package_root = data_root / "Microsoft" / "WinGet" / "Packages"
    candidates = sorted(package_root.glob("JohnMacFarlane.Pandoc_*/*/pandoc.exe"))
    if not candidates:
        raise RuntimeError("Pandoc is unavailable. Add it to PATH or set QF_SOLVER_PANDOC.")
    return candidates[-1]


def _pdflatex() -> Path:
    command = _configured_tool("QF_SOLVER_PDFLATEX", "pdflatex")
    if command is not None:
        return command
    data_root = _user_data_root()
    if data_root is None:
        raise RuntimeError("pdflatex is unavailable. Add it to PATH or set QF_SOLVER_PDFLATEX.")
    candidate = data_root / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64" / "pdflatex.exe"
    if not candidate.is_file():
        raise RuntimeError("pdflatex is unavailable. Add it to PATH or set QF_SOLVER_PDFLATEX.")
    return candidate


def _configured_tool(variable: str, executable: str) -> Path | None:
    configured = os.environ.get(variable)
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file():
            return candidate
        raise RuntimeError(f"{variable} does not point to an existing file: {candidate}")
    command = shutil.which(executable)
    return Path(command) if command else None


def _user_data_root() -> Path | None:
    try:
        from platformdirs import user_data_path
    except ModuleNotFoundError:
        return None
    return Path(user_data_path())


def _python() -> Path:
    import sys

    return Path(sys.executable)


def _tex_escape(value: str) -> str:
    return value.replace("_", r"\_\allowbreak{}").replace("&", r"\&")


if __name__ == "__main__":
    raise SystemExit(main())
