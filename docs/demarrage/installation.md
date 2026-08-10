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

Pour construire le site hors ligne:

```powershell
python -m pip install -e ".[docs]"
python .\scripts\build_docs.py --profile engineering
python .\scripts\serve_docs.py
```

Le lanceur demarre un serveur limite a la boucle locale et ouvre le navigateur
systeme. Arreter le serveur avec `Ctrl+C`. Toutes les ressources necessaires au site sont servies
depuis le poste local, sans CDN, telemetrie ou appel reseau d'execution.

Diagnostic sans ouverture du navigateur :

```powershell
python .\scripts\serve_docs.py --check
```

## Baselines

La baseline standard verrouille NumPy, SciPy et Matplotlib. La baseline
documentation verrouille MkDocs Material, ses extensions Markdown et les
outils de controle du site. Un changement de version doit etre traite comme
une modification de l'environnement de production de preuve.
