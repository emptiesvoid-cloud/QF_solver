---
doc_id: DOC-START-001
revision: 0.1
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Installation locale

Depuis la racine du depot:

```powershell
python -m pip install -e ".[test]"
qf-solver --version
qf-solver methods
```

Pour importer Gmsh et executer les benchmarks structures:

```powershell
python -m pip install -e ".[mesh]"
qf-solver benchmarks
```

Pour regenerer les documents Markdown, figures et manifestes:

```powershell
python -m pip install -e ".[docs]"
python .\scripts\build_docs.py --profile engineering
python .\scripts\build_technical_latex.py
```

La premiere commande regenere les preuves documentaires. La seconde genere le
PDF lorsque Pandoc et MiKTeX/LaTeX sont disponibles. Aucune interface web, CDN
ou telemetrie n'est requise.

## Baselines

La baseline standard verrouille NumPy, SciPy et Matplotlib. La baseline
documentation verrouille les outils de generation de figures et PDF. Un
changement de version doit etre traite comme une modification de
l'environnement de production de preuve.
