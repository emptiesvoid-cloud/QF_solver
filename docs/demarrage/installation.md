---
doc_id: DOC-START-001
revision: 0.2
status: draft
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# Installation

## Installation depuis PyPI

Apres publication de la release :

```powershell
python -m pip install qf-solver==0.2.5a0
qf-solver --version
```

La distribution standard ne rend pas PETSc, SLEPc ou MPI obligatoires.

## Installation depuis le depot

Pour executer les exemples et les tests :

```powershell
python -m pip install -e ".[test]"
qf-solver --version
qf-solver methods
```

Extras optionnels :

```powershell
python -m pip install -e ".[mesh]"  # import Gmsh et benchmarks
python -m pip install -e ".[docs]"  # documentation et figures
python -m pip install -e ".[hpc]"   # PETSc/SLEPc/MPI si disponibles
```

## Smoke test

```powershell
qf-solver check-mesh --input .\examples\tet4_static.json
qf-solver solve --input .\examples\tet4_static.json --output .\results\tet4.json
```

API publique minimale :

```python
from qf_solver import check_mesh, load_model, save_result, solve_model

model = load_model("examples/tet4_static.json")
check_mesh(model)
result = solve_model(model)
save_result(result, "results/tet4.json")
```

Les imports documentes pour les nouvelles integrations passent par
`qf_solver`. Les imports `solveur.*` sont internes ou de compatibilite.

## Documentation locale

```powershell
python -m pip install -e ".[docs]"
python .\scripts\build_docs.py --profile engineering
python .\scripts\build_technical_latex.py
```

Le second script produit le dossier PDF si Pandoc et MiKTeX/LaTeX sont
disponibles. Les versions de reference sont dans `requirements/`.
