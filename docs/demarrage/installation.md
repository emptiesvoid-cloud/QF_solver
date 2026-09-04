---
doc_id: DOC-START-001
revision: 0.2
status: draft
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# Installation

## Current stable release

The stable `0.2.7` release is available from the `v0.2.7` Git tag. PyPI
publication remains a separate owner-controlled action. Install the tagged
source for local reproduction:

```powershell
git clone https://github.com/emptiesvoid-cloud/QF_solver.git
Set-Location QF_solver
git checkout v0.2.7
python -m pip install -e ".[test]"
qf-solver --version
```

The release truth and evidence heads are recorded in
`qualification/0_2_7/manifest.json`.

## Published parent package

The published parent package is available from PyPI as `qf-solver==0.2.6a0`:

```powershell
python -m pip install qf-solver==0.2.6a0
qf-solver --version
```

La distribution standard ne rend pas PETSc, SLEPc ou MPI obligatoires.

## 0.2.6a0 tagged parent source release

The `0.2.6a0` release is available from Git at tag `v0.2.6a0`. Install the
exact tagged source when a reproducible checkout is required:

```powershell
git clone https://github.com/emptiesvoid-cloud/QF_solver.git
Set-Location QF_solver
git checkout v0.2.6a0
python -m pip install -e ".[test]"
qf-solver --version
```

The tagged release state is identified by qualification snapshot
`93561c2c0ae1c173deb81e47c3fa3852643275cb` and release source snapshot
`e839373b6aef291a93292186d7553ba5cd12af55`. The qualification snapshot is
historical evidence and is distinct from the tagged source snapshot.

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
