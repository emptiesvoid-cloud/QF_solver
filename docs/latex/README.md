---
doc_id: DOC-LATEX-BUILD-001
revision: 0.1
status: draft
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Construction du manuel technique LaTeX

Le manuel est compose a partir du registre
`qualification/documentation_review_pages.json` et des pages Markdown
controlees. Pandoc produit une source LaTeX unique, puis MiKTeX compile le
PDF. Les matrices et equations restent vectorielles dans le document final.

Le PDF accepte reste un artefact de sortie. Sa decision Owner est conservee
dans le registre controle, separement du PDF genere.

Commande recommandee depuis la racine du projet :

```powershell
python .\scripts\build_technical_pages_pdf.py
```

Pour eviter de recalculer les preuves documentaires deja generees :

```powershell
python .\scripts\build_technical_latex.py --skip-assets `
  --output .\output\pdf\dossier_technique_elements_methodes_owner_review_latex.pdf
```

Artefacts :

- source composee temporaire : `tmp/pdfs/qf_solver_manual.tex` ;
- style controle : `docs/latex/qf_solver_header.tex` ;
- PDF : `output/pdf/dossier_technique_elements_methodes_owner_review_latex.pdf` ;
- controle de pagination : `output/pdf/dossier_technique_page_counts.json`.

Artefact candidat courant : `277` pages, SHA-256
`ec06c572e27c45d2d1159c3eef2a0ed84eadda4adfc3a28e009c3eb7b36d1708`.
La trame de decision demeure
`qualification/reviews/technical_manual_content_closure_pending_2026-08-01.json`.

La source LaTeX composee est locale et ignoree par Git. Pandoc peut y inscrire
des chemins absolus propres a la machine de construction ; elle ne fait donc
jamais partie d'une archive publique.

Prerequis externes : Pandoc et MiKTeX avec `pdflatex`. Le paquet Python
`svglib` convertit les schemas SVG en PDF vectoriels lisibles par pdfLaTeX.
Les executables sont recherches dans `PATH`, puis dans les installations
utilisateur portables connues. Une installation non standard peut etre
declaree sans modifier le code :

```powershell
$env:QF_SOLVER_PANDOC = "chemin-vers-pandoc"
$env:QF_SOLVER_PDFLATEX = "chemin-vers-pdflatex"
```
