---
doc_id: DOC-REF-001
revision: 0.1
status: draft technique
applicable_version: 0.2.0
reviewer: ""
approver: ""
---

# Interfaces CLI et API

## Commandes principales

```powershell
qf-solver methods
qf-solver check-mesh --input model.json
qf-solver solve --input model.json --output result.json
qf-solver evidence --input model.json --output evidence_dir
qf-solver verify-evidence --input evidence_dir
qf-solver import-mesh --mesh model.msh --setup model.setup.json --output model.json
qf-solver benchmarks
qf-solver benchmark --case BM-SOL-TET4-PATCH-001 --output results/benchmarks
qf-solver vnv-compare --study study.json --output results/vnv
qf-solver verify-contact --output results/contact_v1 --json-report results/contact_v1.json
qf-solver vnv-import-benchmark --case BM-SOL-CANTILEVER-001 --output VNV-TET4-CANTILEVER-ANALYTIC-001
qf-solver vnv-import-benchmark --case BM-SOL-TET4-TORSION-001 --output VNV-TET4-TORSION-ANALYTIC-001
qf-solver verify-all --profile engineering --json-report results/verify_all_engineering.json
```

`verify-all --json-report` ecrit un verdict machine-readable contenant le
profil, le scope, chaque commande executee et son code de retour. Le rapport
est ecrit egalement si une commande echoue, afin de rendre la campagne
rejouable et auditable hors du flux console.

La forme portable est `python -m solveur.cli.main`. Les anciens noms
`solveur-ef` et `main_solveur.py` ne sont que des alias deprecies jusqu'a
0.3.0 et ecrivent un avertissement sur `stderr`.

Codes de sortie:

| Code | Sens |
| ---: | --- |
| 0 | Calcul ou verification accepte |
| 2 | Entree ou maillage invalide |
| 3 | Singularite, non-convergence ou resultat non fini |
| 4 | Refus de la politique de qualification |
| 5 | Environnement ou dependance indisponible |

`--debug` active explicitement la trace Python. Sans cette option, la CLI
retourne un diagnostic court adapte a l'automatisation.

## API Python stable

```python
from qf_solver import (
    check_mesh,
    import_gmsh_model,
    list_benchmarks,
    load_model,
    run_benchmark,
    run_contact_verification,
    run_vnv_study,
    import_cantilever_vnv_study,
    import_torsion_vnv_study,
    save_evidence,
    save_result,
    solve_model,
)

model = load_model("model.json")
mesh = check_mesh(model)
result = solve_model(model)
save_result(result, "result.json")
save_evidence(model, result, "evidence", input_path="model.json")

imported = import_gmsh_model("model.msh", "model.setup.json")
cases = list_benchmarks()
benchmark = run_benchmark(cases[0].identifier, "results/benchmarks")
contact_vnv = run_contact_verification("results/contact_v1")
vnv = run_vnv_study("study.json", "results/vnv")
study = import_cantilever_vnv_study("VNV-TET4-CANTILEVER-ANALYTIC-001")
torsion = import_torsion_vnv_study("VNV-TET4-TORSION-ANALYTIC-001")
```

Le parsing reste dans `io`, la logique mecanique dans `core/elements` et
l'interface publique dans `solveur.api`. Le code appelant ne doit pas importer
les classes internes pour obtenir un resultat courant.

## Grand modele

```python
from qf_solver import load_large_model, solve_large_model

model = load_large_model("model.h5")
result = solve_large_model(model, "result_large", solver_backend="petsc", preconditioner="gamg")
```

Le backend large refuse explicitement MITC4, TET10, dynamique, modal et
non-lineaire dans son perimetre v1.
